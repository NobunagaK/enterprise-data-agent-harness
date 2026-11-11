from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal, Self
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

RunSource = Literal["test_injected", "agent_generated"]
ValidationStatus = Literal["passed", "failed", "unverifiable", "tool_error"]
ValueUnit = Literal["percent", "CNY_cent"]
RuleId = Literal["growth_rate", "sales_total"]


def identifier() -> str:
    return str(uuid4())


class Claim(BaseModel):
    evidence_id: str
    claimed_value: str = Field(max_length=64)
    unit: str = "percent"
    store_id: str = "demo-store"
    previous_year: int = 2024
    current_year: int = 2025
    # Total claims name one period; old growth claims omit this field.
    year: int | None = Field(default=None, exclude_if=lambda value: value is None)


class Evidence(BaseModel):
    id: str = Field(default_factory=identifier)
    run_id: str
    step_id: str
    sql: str
    columns: list[str]
    rows: list[dict]
    truncated: bool = False
    dataset_version: str = "sales-v1"
    amount_unit: str = "CNY_cent"


class ValidationResult(BaseModel):
    status: ValidationStatus
    reason: str
    rule_version: str = "growth_rate-v2"
    unit: ValueUnit = "percent"
    tolerance: str | None = None
    difference: str | None = None
    # Legacy growth-only aliases; null for amount results.
    tolerance_pp: str | None = None
    expected_value: str | None = None
    expected_display: str | None = None
    claimed_value: str | None = None
    difference_pp: str | None = None

    @model_validator(mode="after")
    def normalize_comparison(self) -> Self:
        if self.unit == "percent":
            if self.tolerance is None:
                self.tolerance = self.tolerance_pp if self.tolerance_pp is not None else "0.01"
            if self.tolerance_pp is None:
                self.tolerance_pp = self.tolerance
            if self.difference is None:
                self.difference = self.difference_pp
            if self.difference_pp is None:
                self.difference_pp = self.difference
            if self.tolerance != self.tolerance_pp or self.difference != self.difference_pp:
                raise ValueError("Conflicting growth comparison aliases")
        elif (
            self.tolerance is None
            or self.tolerance_pp is not None
            or self.difference_pp is not None
            or self.rule_version.startswith("growth_rate")
        ):
            raise ValueError("Amount results require their own rule/tolerance and no pp aliases")
        for value in (self.tolerance, self.difference):
            if value is not None:
                try:
                    number = Decimal(value)
                except InvalidOperation as exc:
                    raise ValueError(
                        "Comparison values must be finite nonnegative decimals"
                    ) from exc
                if not number.is_finite() or number < 0:
                    raise ValueError("Comparison values must be finite nonnegative decimals")
        return self


class TokenUsage(BaseModel):
    input_tokens: int | None = Field(default=None, ge=0, strict=True)
    output_tokens: int | None = Field(default=None, ge=0, strict=True)


class Step(BaseModel):
    id: str = Field(default_factory=identifier)
    kind: Literal["query", "claim", "validation", "model", "tool", "answer", "context"]
    status: Literal["running", "completed", "error", "skipped"] = "completed"
    duration_ms: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    error: str | None = None
    parent_step_id: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    token_usage: TokenUsage | None = None


class Run(BaseModel):
    # Missing version means an original Sprint 1 snapshot. New service runs use 2.
    schema_version: Literal[1, 2] = 1
    id: str = Field(default_factory=identifier)
    conversation_id: str | None = None
    case_id: str | None = None
    rule_id: RuleId = "growth_rate"
    dataset_version: str = "sales-v1"
    source: RunSource
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    state: Literal["running", "completed", "error"] = "running"
    model: str | None = None
    answer: str | None = None
    answer_truncated: bool = False
    steps: list[Step] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    claim: Claim | None = None
    result: ValidationResult | None = None
