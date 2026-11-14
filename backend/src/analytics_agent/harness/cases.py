"""Versioned case-set definitions for batch evaluation.

Case definitions are evaluation data, not model input: ``expected_status`` is
never mapped into ``RunRequest``. Only identity, selectors and the injected
claim reach the single-run boundary.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from analytics_agent.harness.contracts import (
    RUN_REQUEST,
    GrowthParameters,
    RunRequest,
    TotalParameters,
    default_growth_rule,
)
from analytics_agent.harness.models import RunSource, ValidationStatus

CASE_SET_DIR = Path(__file__).resolve().parent / "case_sets"
CASE_SET_ID_PATTERN = r"^[a-z0-9][a-z0-9-]{0,63}$"
CASE_SET_ID = re.compile(CASE_SET_ID_PATTERN)
MAX_CASES = 20


class CaseSetNotFound(LookupError):
    """The requested bundled case set does not exist."""


class CaseMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str = Field(min_length=1, max_length=128)
    claimed_value: str = Field(max_length=64)
    dataset_version: Literal["sales-v1"] = "sales-v1"
    source: RunSource = "test_injected"
    expected_status: ValidationStatus | None = None
    note: str | None = Field(default=None, max_length=200)

    def to_request(self, conversation_id: str | None) -> RunRequest:
        return RUN_REQUEST.validate_python(
            {
                **self.model_dump(exclude={"expected_status", "note"}),
                "conversation_id": conversation_id,
            }
        )


class CaseDefinition(CaseMetadata):
    """Original growth-only constructor remains compatible for batch callers."""

    rule_id: Literal["growth_rate"] = "growth_rate"
    unit: Literal["percent"] = "percent"
    parameters: GrowthParameters = Field(default_factory=GrowthParameters)


class TotalCaseDefinition(CaseMetadata):
    rule_id: Literal["sales_total"] = "sales_total"
    unit: Literal["CNY_cent"] = "CNY_cent"
    parameters: TotalParameters = Field(default_factory=TotalParameters)


EvaluationCase = Annotated[
    CaseDefinition | TotalCaseDefinition,
    Field(discriminator="rule_id"),
    BeforeValidator(default_growth_rule),
]


class CaseSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_set_id: str = Field(pattern=CASE_SET_ID_PATTERN, max_length=64)
    version: str = Field(min_length=1, max_length=32)
    dataset_version: Literal["sales-v1"]
    cases: list[EvaluationCase] = Field(min_length=1, max_length=MAX_CASES)

    @model_validator(mode="after")
    def _check_cases(self) -> CaseSet:
        ids = [case.case_id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate case_id in case set")
        mismatched = [
            case.case_id for case in self.cases if case.dataset_version != self.dataset_version
        ]
        if mismatched:
            raise ValueError(f"case dataset_version mismatch: {', '.join(mismatched)}")
        return self


class CaseSetSummary(BaseModel):
    """Selection metadata; evaluation labels and claims stay in the case file."""

    case_set_id: str
    version: str
    dataset_version: str
    case_count: int
    rule_ids: list[str]
    sources: list[RunSource]


def list_case_sets() -> list[CaseSetSummary]:
    """Describe the bundled, validated case sets without executing any case."""
    summaries = []
    for path in sorted(CASE_SET_DIR.glob("*.json")):
        case_set = load_case_set(path.stem)
        summaries.append(
            CaseSetSummary(
                case_set_id=case_set.case_set_id,
                version=case_set.version,
                dataset_version=case_set.dataset_version,
                case_count=len(case_set.cases),
                rule_ids=sorted({case.rule_id for case in case_set.cases}),
                sources=sorted({case.source for case in case_set.cases}),
            )
        )
    return summaries


def load_case_set(case_set_id: str) -> CaseSet:
    """Load a bundled case set by ID. The ID is restricted to a safe slug."""
    if not CASE_SET_ID.fullmatch(case_set_id):
        raise CaseSetNotFound(case_set_id)
    path = CASE_SET_DIR / f"{case_set_id}.json"
    if not path.is_file():
        raise CaseSetNotFound(case_set_id)
    case_set = CaseSet.model_validate(json.loads(path.read_text(encoding="utf-8")))
    if case_set.case_set_id != case_set_id:
        raise CaseSetNotFound(case_set_id)
    return case_set
