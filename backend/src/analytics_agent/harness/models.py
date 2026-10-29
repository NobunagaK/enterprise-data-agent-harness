from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def identifier() -> str:
    return str(uuid4())


class Claim(BaseModel):
    evidence_id: str
    claimed_value: str = Field(max_length=64)
    unit: str = "percent"
    store_id: str = "demo-store"
    previous_year: int = 2024
    current_year: int = 2025


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
    status: Literal["passed", "failed", "unverifiable", "tool_error"]
    reason: str
    rule_version: str = "growth_rate-v1"
    tolerance_pp: str = "0.01"
    expected_value: str | None = None
    expected_display: str | None = None
    claimed_value: str | None = None
    difference_pp: str | None = None


class Step(BaseModel):
    id: str = Field(default_factory=identifier)
    kind: Literal["query", "claim", "validation"]
    status: Literal["completed", "error"] = "completed"
    duration_ms: float = 0
    error: str | None = None


class Run(BaseModel):
    id: str = Field(default_factory=identifier)
    conversation_id: str | None = None
    source: Literal["test_injected", "agent_generated"]
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
