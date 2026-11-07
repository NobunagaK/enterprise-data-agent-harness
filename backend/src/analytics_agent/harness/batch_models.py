"""Persistence models for batch evaluation runs."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from analytics_agent.harness.models import ValidationStatus

CaseState = Literal["completed", "timeout", "error"]
BatchState = Literal["running", "completed", "partial", "error"]


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


class Batch(BaseModel):
    schema_version: Literal[1] = 1
    id: str
    case_set_id: str
    case_set_version: str
    conversation_id: str | None = None
    state: BatchState = "running"
    started_at: datetime
    finished_at: datetime | None = None
    outcomes: list[CaseOutcome] = Field(default_factory=list)
    counts: BatchCounts = Field(default_factory=BatchCounts)
