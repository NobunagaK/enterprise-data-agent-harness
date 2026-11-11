"""Validated inputs shared by HTTP and future batch callers."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, TypeAdapter

from analytics_agent.harness.models import RunSource


class GrowthParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    store_id: Literal["demo-store"] = "demo-store"
    previous_year: Literal[2024] = 2024
    current_year: Literal[2025] = 2025


class CommonRequest(BaseModel):
    """Only advertise executable capabilities; extend with each feature PR.

    claimed_value is deliberately a string: malformed numerical claims are
    classified by the validator, rather than coerced through a binary float.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: RunSource = "test_injected"
    claimed_value: str = Field(default="10", max_length=64)
    conversation_id: str | None = None
    case_id: str | None = Field(default=None, min_length=1, max_length=128)
    dataset_version: Literal["sales-v1"] = "sales-v1"


class GrowthRunRequest(CommonRequest):
    rule_id: Literal["growth_rate"] = "growth_rate"
    unit: Literal["percent"] = "percent"
    parameters: GrowthParameters = Field(default_factory=GrowthParameters)


class TotalParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    store_id: Literal["demo-store"] = "demo-store"
    year: Literal[2025] = 2025


class SalesTotalRunRequest(CommonRequest):
    rule_id: Literal["sales_total"] = "sales_total"
    claimed_value: str = Field(default="11000", max_length=64)
    unit: Literal["CNY_cent"] = "CNY_cent"
    parameters: TotalParameters = Field(default_factory=TotalParameters)


def default_growth_rule(value: Any) -> Any:
    """Keep original JSON requests valid without weakening rule discrimination."""
    if isinstance(value, dict) and "rule_id" not in value:
        return {**value, "rule_id": "growth_rate"}
    return value


RunRequest = Annotated[
    GrowthRunRequest | SalesTotalRunRequest,
    Field(discriminator="rule_id"),
    BeforeValidator(default_growth_rule),
]
RUN_REQUEST: TypeAdapter[RunRequest] = TypeAdapter(RunRequest)
