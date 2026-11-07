"""Validated inputs shared by HTTP and future batch callers."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from analytics_agent.harness.models import RunSource


class GrowthParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    store_id: Literal["demo-store"] = "demo-store"
    previous_year: Literal[2024] = 2024
    current_year: Literal[2025] = 2025


class RunRequest(BaseModel):
    """Only advertise executable capabilities; extend with each feature PR.

    claimed_value is deliberately a string: malformed numerical claims are
    classified by the validator, rather than coerced through a binary float.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: RunSource = "test_injected"
    claimed_value: str = Field(default="10", max_length=64)
    conversation_id: str | None = None
    case_id: str | None = Field(default=None, min_length=1, max_length=128)
    rule_id: Literal["growth_rate"] = "growth_rate"
    dataset_version: Literal["sales-v1"] = "sales-v1"
    unit: Literal["percent"] = "percent"
    parameters: GrowthParameters = Field(default_factory=GrowthParameters)
