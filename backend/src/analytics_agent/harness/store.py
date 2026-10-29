from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analytics_agent.db.models import HarnessRun
from analytics_agent.harness.models import Run


async def save(session: AsyncSession, run: Run) -> None:
    row = await session.get(HarnessRun, run.id)
    if row is None:
        row = HarnessRun(
            id=run.id,
            conversation_id=run.conversation_id,
            created_at=run.started_at,
            report=run.model_dump_json(),
        )
        session.add(row)
    else:
        row.report = run.model_dump_json()
    await session.commit()


async def get(session: AsyncSession, run_id: str) -> Run | None:
    row = await session.get(HarnessRun, run_id)
    return Run.model_validate_json(row.report) if row else None


async def list_runs(session: AsyncSession, conversation_id: str | None) -> list[Run]:
    query = select(HarnessRun).where(HarnessRun.conversation_id == conversation_id)
    rows = (await session.scalars(query.order_by(HarnessRun.created_at.desc()).limit(20))).all()
    return [Run.model_validate_json(row.report) for row in rows]
