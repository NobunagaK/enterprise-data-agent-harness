"""Versioned case-set definitions for batch evaluation.

Case definitions are evaluation data, not model input: ``expected_status`` is
never mapped into ``RunRequest``. Only identity, selectors and the injected
claim reach the single-run boundary.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from analytics_agent.harness.contracts import GrowthParameters, RunRequest
from analytics_agent.harness.models import RunSource, ValidationStatus

CASE_SET_DIR = Path(__file__).resolve().parent / "case_sets"
CASE_SET_ID_PATTERN = r"^[a-z0-9][a-z0-9-]{0,63}$"
CASE_SET_ID = re.compile(CASE_SET_ID_PATTERN)
MAX_CASES = 20


class CaseSetNotFound(LookupError):
    """The requested bundled case set does not exist."""


class CaseDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str = Field(min_length=1, max_length=128)
    claimed_value: str = Field(max_length=64)
    rule_id: Literal["growth_rate"] = "growth_rate"
    dataset_version: Literal["sales-v1"] = "sales-v1"
    unit: Literal["percent"] = "percent"
    source: RunSource = "test_injected"
    parameters: GrowthParameters = Field(default_factory=GrowthParameters)
    expected_status: ValidationStatus | None = None
    note: str | None = Field(default=None, max_length=200)

    def to_request(self, conversation_id: str | None) -> RunRequest:
        return RunRequest(
            source=self.source,
            claimed_value=self.claimed_value,
            conversation_id=conversation_id,
            case_id=self.case_id,
            rule_id=self.rule_id,
            dataset_version=self.dataset_version,
            unit=self.unit,
            parameters=self.parameters,
        )


class CaseSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_set_id: str = Field(pattern=CASE_SET_ID_PATTERN, max_length=64)
    version: str = Field(min_length=1, max_length=32)
    dataset_version: Literal["sales-v1"]
    cases: list[CaseDefinition] = Field(min_length=1, max_length=MAX_CASES)

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
