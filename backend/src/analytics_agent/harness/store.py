from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from analytics_agent.db.models import HarnessRun
from analytics_agent.harness.models import Run
from analytics_agent.harness.validation import rule_result

STALE_AFTER_SECONDS = 300


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
    return await reconcile(session, row) if row else None


async def list_runs(session: AsyncSession, conversation_id: str | None) -> list[Run]:
    query = select(HarnessRun).where(HarnessRun.conversation_id == conversation_id)
    rows = (await session.scalars(query.order_by(HarnessRun.created_at.desc()).limit(20))).all()
    return [await reconcile(session, row) for row in rows]


async def reconcile(session: AsyncSession, row: HarnessRun) -> Run:
    """Expire abandoned snapshots without overwriting a concurrently saved result."""
    snapshot = row.report
    run = Run.model_validate_json(snapshot)
    now = datetime.now(UTC)
    if run.state != "running" or (now - run.started_at).total_seconds() <= STALE_AFTER_SECONDS:
        return run
    run.state = "error"
    run.finished_at = now  # Detection time; started_at remains unchanged.
    run.result = rule_result(run.rule_id, "tool_error", "stale_running")
    await session.execute(
        update(HarnessRun)
        .where(HarnessRun.id == run.id, HarnessRun.report == snapshot)
        .values(report=run.model_dump_json())
        .execution_options(synchronize_session=False)
    )
    await session.commit()
    await session.refresh(row)
    return Run.model_validate_json(row.report)
