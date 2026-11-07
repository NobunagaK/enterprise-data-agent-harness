"""Persistence for batch summaries (one JSON snapshot per batch)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analytics_agent.db.models import HarnessBatch
from analytics_agent.harness.batch_models import Batch

LIST_LIMIT = 20


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
    return Batch.model_validate_json(row.report) if row else None


async def list_batches(session: AsyncSession, conversation_id: str | None) -> list[Batch]:
    query = select(HarnessBatch).where(HarnessBatch.conversation_id == conversation_id)
    rows = (
        await session.scalars(query.order_by(HarnessBatch.created_at.desc()).limit(LIST_LIMIT))
    ).all()
    return [Batch.model_validate_json(row.report) for row in rows]
