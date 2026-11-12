"""Persistence for batch summaries (one JSON snapshot per batch)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analytics_agent.db.models import HarnessBatch
from analytics_agent.harness.batch_models import Batch, CaseOutcome, count_outcomes

LIST_LIMIT = 20
ACTIVE_BATCH_IDS: set[str] = set()


def visible_snapshot(batch: Batch) -> Batch:
    """Expose expired, unowned snapshots as unconfirmed, without rewriting them.

    The prototype runs in one server process. An active local run may still be
    draining owned work after expiry; never relabel it while that cleanup runs.
    Absence plus an expired deadline does not prove a worker was killed.
    """
    deadline = batch.deadline_at
    if deadline is not None:
        deadline = (
            deadline.replace(tzinfo=UTC) if deadline.tzinfo is None else deadline.astimezone(UTC)
        )
    if (
        batch.state != "running"
        or batch.id in ACTIVE_BATCH_IDS
        or deadline is None
        or deadline > datetime.now(UTC)
    ):
        return batch
    batch = batch.model_copy(deep=True)
    recorded = {outcome.case_id for outcome in batch.outcomes}
    for case_id in batch.case_ids:
        if case_id not in recorded:
            active = case_id == batch.active_case_id
            batch.outcomes.append(
                CaseOutcome(
                    case_id=case_id,
                    state="interrupted" if active else "skipped",
                    reason="execution_unconfirmed",
                )
            )
    batch.state, batch.stop_reason = "interrupted", "execution_unconfirmed"
    batch.counts = count_outcomes(batch.outcomes)
    # No observed finish time or completed run report is invented.
    return batch


async def save(session: AsyncSession, batch: Batch) -> None:
    row = await session.get(HarnessBatch, batch.id)
    payload = batch.model_dump_json()
    if row is None:
        row = HarnessBatch(
            id=batch.id,
            conversation_id=batch.conversation_id,
            created_at=batch.started_at,
            report=payload,
        )
        session.add(row)
    else:
        row.report = payload
    await session.commit()


async def get(session: AsyncSession, batch_id: str) -> Batch | None:
    row = await session.get(HarnessBatch, batch_id)
    return visible_snapshot(Batch.model_validate_json(row.report)) if row else None


async def list_batches(session: AsyncSession, conversation_id: str | None) -> list[Batch]:
    query = select(HarnessBatch).where(HarnessBatch.conversation_id == conversation_id)
    rows = (
        await session.scalars(query.order_by(HarnessBatch.created_at.desc()).limit(LIST_LIMIT))
    ).all()
    return [visible_snapshot(Batch.model_validate_json(row.report)) for row in rows]
