from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from analytics_agent.db.base import get_session
from analytics_agent.harness import store
from analytics_agent.harness.contracts import RunRequest
from analytics_agent.harness.models import Run
from analytics_agent.harness.service import ConversationNotFound, run_case

router = APIRouter(prefix="/api/harness", tags=["harness"])


@router.post("/runs", response_model=Run, status_code=201)
async def create_run(body: RunRequest, session: AsyncSession = Depends(get_session)):
    try:
        return await run_case(body, session)
    except ConversationNotFound:
        raise HTTPException(404, "Conversation not found")


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
