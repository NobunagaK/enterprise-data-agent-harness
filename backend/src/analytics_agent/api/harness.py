from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from analytics_agent.db.base import get_session
from analytics_agent.db.models import Conversation
from analytics_agent.harness import store
from analytics_agent.harness.models import Run
from analytics_agent.harness.runner import execute

router = APIRouter(prefix="/api/harness", tags=["harness"])


class RunRequest(BaseModel):
    source: Literal["test_injected", "agent_generated"] = "test_injected"
    claimed_value: str = Field(default="10", max_length=64)
    conversation_id: str | None = None


@router.post("/runs", response_model=Run, status_code=201)
async def create_run(body: RunRequest, session: AsyncSession = Depends(get_session)):
    if body.conversation_id and await session.get(Conversation, body.conversation_id) is None:
        raise HTTPException(404, "Conversation not found")
    run = Run(source=body.source, conversation_id=body.conversation_id)
    await store.save(session, run)
    await execute(run, body.claimed_value)
    await store.save(session, run)
    return run


@router.get("/runs", response_model=list[Run])
async def list_runs(
    conversation_id: str | None = None, session: AsyncSession = Depends(get_session)
):
    return await store.list_runs(session, conversation_id)


@router.get("/runs/{run_id}", response_model=Run)
async def get_run(run_id: str, session: AsyncSession = Depends(get_session)):
    run = await store.get(session, run_id)
    if run is None:
        raise HTTPException(404, "Run not found")
    return run
