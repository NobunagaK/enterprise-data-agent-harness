"""Sequential evaluation with cooperative budgets and durable stop outcomes."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import perf_counter
from typing import Any, TypeVar
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytics_agent.harness import batch_store
from analytics_agent.harness.batch_models import (
    DEFAULT_BATCH_TIMEOUT_S,
    DEFAULT_CASE_TIMEOUT_S,
    Batch,
    BatchBudget,
    CaseOutcome,
    CaseState,
    count_outcomes,
)
from analytics_agent.harness.cases import CaseSet, EvaluationCase
from analytics_agent.harness.service import ConversationNotFound, run_case

RESULTS = ("passed", "failed", "unverifiable", "tool_error")
logger = logging.getLogger(__name__)
T = TypeVar("T")


def _now() -> datetime:
    return datetime.now(UTC)


def new_batch(
    case_set: CaseSet, conversation_id: str | None, budget: BatchBudget | None = None
) -> Batch:
    budget = budget or BatchBudget()
    now = _now()
    return Batch(
        schema_version=2,
        id=str(uuid4()),
        case_set_id=case_set.case_set_id,
        case_set_version=case_set.version,
        conversation_id=conversation_id,
        state="running",
        started_at=now,
        case_ids=[case.case_id for case in case_set.cases],
        case_timeout_s=budget.case_timeout_s,
        batch_timeout_s=budget.batch_timeout_s,
        deadline_at=now + timedelta(seconds=budget.batch_timeout_s),
    )


@dataclass
class CaseProgress:
    case: EvaluationCase
    started: float
    run_id: str | None = None
    outcome: CaseOutcome | None = None


def _matches(case: EvaluationCase, status: str | None) -> bool | None:
    if case.expected_status is None or status is None:
        return None
    return status == case.expected_status


async def _run_one(
    case: EvaluationCase,
    session_factory: async_sessionmaker[AsyncSession],
    conversation_id: str | None,
    case_timeout_s: float | None,
    progress: CaseProgress,
) -> CaseOutcome:
    persisted_run_id: str | None = None

    def remember_run(run_id: str) -> None:
        nonlocal persisted_run_id
        persisted_run_id = run_id
        progress.run_id = run_id

    deadline = asyncio.timeout(case_timeout_s)
    try:
        async with session_factory() as session:
            request = case.to_request(conversation_id)
            async with deadline:
                run = await run_case(request, session, on_persisted=remember_run)
            # Preserve a confirmed terminal report even if cancellation arrives
            # while closing the session or saving the enclosing batch snapshot.
            status = run.result.status if run.result else None
            progress.outcome = CaseOutcome(
                case_id=case.case_id,
                state="completed",
                run_id=run.id,
                result_status=status,
                reason=run.result.reason if run.result else None,
                expected_status=case.expected_status,
                matches_expected=_matches(case, status),
            )
    except TimeoutError:
        return CaseOutcome(
            case_id=case.case_id,
            state="timeout" if deadline.expired() else "error",
            run_id=persisted_run_id,
            reason="case_timeout" if deadline.expired() else "case_error",
            error_type=None if deadline.expired() else "TimeoutError",
            expected_status=case.expected_status,
        )
    except ConversationNotFound:
        return CaseOutcome(
            case_id=case.case_id,
            state="error",
            reason="conversation_not_found",
            run_id=persisted_run_id,
            expected_status=case.expected_status,
        )
    except Exception as exc:  # Case failures are isolated; batch cancellation still propagates.
        return CaseOutcome(
            case_id=case.case_id,
            state="error",
            reason="case_error",
            run_id=persisted_run_id,
            error_type=type(exc).__name__,
            expected_status=case.expected_status,
        )

    assert progress.outcome is not None
    return progress.outcome


async def _persist(batch: Batch, session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        await batch_store.save(session, batch)


async def _drain(task: asyncio.Task) -> bool:
    """Await owned work despite repeated cancellation; return whether interrupted."""
    interrupted = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            interrupted = True
        except Exception:
            break
    return interrupted


async def _owned(operation: Coroutine[Any, Any, T]) -> T:
    task = asyncio.create_task(operation)
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        task.cancel()
        await _drain(task)
        if not task.cancelled():
            task.exception()
        raise


async def _save_terminal(batch: Batch, session_factory: async_sessionmaker[AsyncSession]) -> None:
    task = asyncio.create_task(_persist(batch, session_factory))
    interrupted = await _drain(task)
    task.result()  # A failed write must not look like a successfully saved report.
    if interrupted:
        raise asyncio.CancelledError


def _stop(
    batch: Batch, case_set: CaseSet, progress: CaseProgress | None, state: CaseState, reason: str
) -> None:
    if progress is not None:
        outcome = progress.outcome or CaseOutcome(
            case_id=progress.case.case_id,
            state=state,
            run_id=progress.run_id,
            reason=reason,
            expected_status=progress.case.expected_status,
        )
        outcome.duration_ms = int((perf_counter() - progress.started) * 1000)
        batch.outcomes.append(outcome)
    recorded = {outcome.case_id for outcome in batch.outcomes}
    batch.outcomes.extend(
        CaseOutcome(
            case_id=case.case_id,
            state="skipped",
            reason=reason,
            expected_status=case.expected_status,
        )
        for case in case_set.cases
        if case.case_id not in recorded
    )
    batch.counts = count_outcomes(batch.outcomes)
    batch.stop_reason = reason
    batch.finished_at = _now()
    batch.active_case_id = None


async def run_batch(
    case_set: CaseSet,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    conversation_id: str | None = None,
    case_timeout_s: float | None = DEFAULT_CASE_TIMEOUT_S,
    batch_timeout_s: float = DEFAULT_BATCH_TIMEOUT_S,
    persist: bool = True,
) -> Batch:
    """Stop starting cases on expiry; drain owned work before persisting a stop.

    Budgets request cancellation, not hard worker termination. Cleanup/database
    writes may outlast them. External cancellation is propagated after cleanup.
    """
    budget = BatchBudget(case_timeout_s=case_timeout_s, batch_timeout_s=batch_timeout_s)
    batch = new_batch(case_set, conversation_id, budget)
    progress = None
    deadline = asyncio.timeout(budget.batch_timeout_s)
    batch_store.ACTIVE_BATCH_IDS.add(batch.id)
    try:
        async with deadline:
            if persist:
                await _owned(_persist(batch, session_factory))
            for case in case_set.cases:
                batch.active_case_id = case.case_id
                if persist:
                    await _owned(_persist(batch, session_factory))
                progress = CaseProgress(case, perf_counter())
                outcome = await _owned(
                    _run_one(
                        case, session_factory, conversation_id, budget.case_timeout_s, progress
                    )
                )
                outcome.duration_ms = int((perf_counter() - progress.started) * 1000)
                batch.outcomes.append(outcome)
                progress = None
                batch.active_case_id = None
                batch.counts = count_outcomes(batch.outcomes)
                if persist:
                    await _owned(_persist(batch, session_factory))
            batch.finished_at = _now()
            batch.state = (
                "completed"
                if all(item.state == "completed" for item in batch.outcomes)
                else "partial"
            )
            if persist:
                await _owned(_persist(batch, session_factory))
        return batch
    except TimeoutError:
        if not deadline.expired():
            raise
        batch.state = "timed_out"
        _stop(batch, case_set, progress, "timeout", "batch_timeout")
        if persist:
            await _save_terminal(batch, session_factory)
        return batch
    except asyncio.CancelledError:
        batch.state = "cancelled"
        _stop(batch, case_set, progress, "cancelled", "batch_cancelled")
        if persist:
            try:
                await _save_terminal(batch, session_factory)
            except asyncio.CancelledError:
                pass  # A repeated cancellation still propagates below.
            except Exception:
                logger.warning("Cancelled batch terminal snapshot could not be saved")
        raise
    finally:
        batch_store.ACTIVE_BATCH_IDS.discard(batch.id)
