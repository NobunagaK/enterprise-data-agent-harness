"""Persistence models for batch evaluation runs."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from analytics_agent.harness.models import ValidationStatus

CaseState = Literal["completed", "timeout", "error", "cancelled", "skipped", "interrupted"]
BatchState = Literal[
    "running", "completed", "partial", "error", "timed_out", "cancelled", "interrupted"
]

DEFAULT_CASE_TIMEOUT_S = 60.0
DEFAULT_BATCH_TIMEOUT_S = 300.0


class BatchBudget(BaseModel):
    """Cooperative execution budgets, including for direct Python callers."""

    case_timeout_s: float | None = Field(
        default=DEFAULT_CASE_TIMEOUT_S, gt=0, le=120, allow_inf_nan=False
    )
    batch_timeout_s: float = Field(
        default=DEFAULT_BATCH_TIMEOUT_S, gt=0, le=600, allow_inf_nan=False
    )


class CaseOutcome(BaseModel):
    """One case inside a batch. A case always ends in exactly one state."""

    case_id: str
    state: CaseState
    run_id: str | None = None
    result_status: ValidationStatus | None = None
    reason: str | None = None
    error_type: str | None = None
    expected_status: ValidationStatus | None = None
    matches_expected: bool | None = None
    duration_ms: int = Field(default=0, ge=0)


class BatchCounts(BaseModel):
    attempted: int = Field(default=0, ge=0)
    completed: int = Field(default=0, ge=0)
    passed: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)
    unverifiable: int = Field(default=0, ge=0)
    tool_error: int = Field(default=0, ge=0)
    timeout: int = Field(default=0, ge=0)
    error: int = Field(default=0, ge=0)
    cancelled: int = Field(default=0, ge=0, exclude_if=lambda value: value == 0)
    skipped: int = Field(default=0, ge=0, exclude_if=lambda value: value == 0)
    interrupted: int = Field(default=0, ge=0, exclude_if=lambda value: value == 0)


class Batch(BaseModel):
    schema_version: Literal[1, 2] = 1
    id: str
    case_set_id: str
    case_set_version: str
    conversation_id: str | None = None
    state: BatchState = "running"
    started_at: datetime
    finished_at: datetime | None = None
    outcomes: list[CaseOutcome] = Field(default_factory=list)
    counts: BatchCounts = Field(default_factory=BatchCounts)
    case_ids: list[str] = Field(default_factory=list)
    deadline_at: datetime | None = None
    case_timeout_s: float | None = None
    batch_timeout_s: float | None = None
    stop_reason: str | None = None
    active_case_id: str | None = None


def count_outcomes(outcomes: list[CaseOutcome]) -> BatchCounts:
    counts = BatchCounts()
    for outcome in outcomes:
        if outcome.state == "skipped":
            counts.skipped += 1
            continue
        counts.attempted += 1
        if outcome.state != "completed":
            setattr(counts, outcome.state, getattr(counts, outcome.state) + 1)
        else:
            counts.completed += 1
            if outcome.result_status is not None:
                setattr(counts, outcome.result_status, getattr(counts, outcome.result_status) + 1)
    return counts
