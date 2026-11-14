"""HTTP surface for batch evaluation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from analytics_agent.db.base import get_session, get_session_factory
from analytics_agent.db.models import Conversation
from analytics_agent.harness import batch_store
from analytics_agent.harness.batch import run_batch
from analytics_agent.harness.batch_models import Batch
from analytics_agent.harness.cases import (
    CASE_SET_ID_PATTERN,
    CaseSetNotFound,
    CaseSetSummary,
    list_case_sets,
    load_case_set,
)

router = APIRouter(prefix="/api/harness/batches", tags=["harness"])


class BatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_set_id: str = Field(default="sprint2-sales-v1", pattern=CASE_SET_ID_PATTERN, max_length=64)
    conversation_id: str | None = None
    case_timeout_s: float | None = Field(default=None, gt=0, le=120)


def get_batch_session_factory():
    """Dependency seam: batches need one session per case."""
    return get_session_factory()


@router.post("", response_model=Batch, status_code=201)
async def create_batch(
    body: BatchRequest,
    factory=Depends(get_batch_session_factory),
):
    if body.conversation_id:
        # Release the preflight connection before batch persistence/case sessions.
        async with factory() as session:
            if await session.get(Conversation, body.conversation_id) is None:
                raise HTTPException(404, "Conversation not found") from None
    try:
        case_set = load_case_set(body.case_set_id)
    except CaseSetNotFound:
        raise HTTPException(404, "Case set not found") from None
    return await run_batch(
        case_set,
        factory,
        conversation_id=body.conversation_id,
        case_timeout_s=body.case_timeout_s,
    )


@router.get("", response_model=list[Batch])
async def list_batches(
    conversation_id: str | None = None, session: AsyncSession = Depends(get_session)
):
    return await batch_store.list_batches(session, conversation_id)


@router.get("/case-sets", response_model=list[CaseSetSummary])
async def get_case_sets():
    return list_case_sets()


@router.get("/{batch_id}", response_model=Batch)
async def get_batch(batch_id: str, session: AsyncSession = Depends(get_session)):
    batch = await batch_store.get(session, batch_id)
    if batch is None:
        raise HTTPException(404, "Batch not found") from None
    return batch
