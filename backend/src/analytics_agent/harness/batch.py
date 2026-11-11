"""Sequential batch evaluation over a versioned case set.

Isolation contract: every case runs through ``service.run_case`` in its own
session (that function commits), and every failure is captured as an outcome so
later cases still run. A batch is persisted after each case, so a crash keeps
the completed prefix and marks the batch ``partial`` on the next read only if a
case itself failed; an interrupted process leaves the last saved snapshot with
``state="running"``, which callers must not read as success.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytics_agent.harness import batch_store
from analytics_agent.harness.batch_models import Batch, BatchCounts, CaseOutcome
from analytics_agent.harness.cases import CaseSet, EvaluationCase
from analytics_agent.harness.service import ConversationNotFound, run_case

RESULTS = ("passed", "failed", "unverifiable", "tool_error")


def _now() -> datetime:
    return datetime.now(UTC)


def new_batch(case_set: CaseSet, conversation_id: str | None) -> Batch:
    return Batch(
        id=str(uuid4()),
        case_set_id=case_set.case_set_id,
        case_set_version=case_set.version,
        conversation_id=conversation_id,
        state="running",
        started_at=_now(),
    )


def count_outcomes(outcomes: list[CaseOutcome]) -> BatchCounts:
    counts = BatchCounts(attempted=len(outcomes))
    for outcome in outcomes:
        if outcome.state == "timeout":
            counts.timeout += 1
        elif outcome.state == "error":
            counts.error += 1
        else:
            counts.completed += 1
            if outcome.result_status == "passed":
                counts.passed += 1
            elif outcome.result_status == "failed":
                counts.failed += 1
            elif outcome.result_status == "unverifiable":
                counts.unverifiable += 1
            elif outcome.result_status == "tool_error":
                counts.tool_error += 1
    return counts


def _matches(case: EvaluationCase, status: str | None) -> bool | None:
    if case.expected_status is None or status is None:
        return None
    return status == case.expected_status


async def _run_one(
    case: EvaluationCase,
    session_factory: async_sessionmaker[AsyncSession],
    conversation_id: str | None,
    case_timeout_s: float | None,
) -> CaseOutcome:
    persisted_run_id: str | None = None

    def remember_run(run_id: str) -> None:
        nonlocal persisted_run_id
        persisted_run_id = run_id

    try:
        async with session_factory() as session:
            request = case.to_request(conversation_id)
            if case_timeout_s is None:
                run = await run_case(request, session, on_persisted=remember_run)
            else:
                run = await asyncio.wait_for(
                    run_case(request, session, on_persisted=remember_run), timeout=case_timeout_s
                )
    except TimeoutError:
        return CaseOutcome(
            case_id=case.case_id,
            state="timeout",
            run_id=persisted_run_id,
            reason="case_timeout",
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

    status = run.result.status if run.result else None
    return CaseOutcome(
        case_id=case.case_id,
        state="completed",
        run_id=run.id,
        result_status=status,
        reason=run.result.reason if run.result else None,
        expected_status=case.expected_status,
        matches_expected=_matches(case, status),
    )


async def _persist(batch: Batch, session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        await batch_store.save(session, batch)


async def run_batch(
    case_set: CaseSet,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    conversation_id: str | None = None,
    case_timeout_s: float | None = None,
    persist: bool = True,
) -> Batch:
    """Run every case in order. Storage failures propagate; case failures do not."""
    batch = new_batch(case_set, conversation_id)
    if persist:
        await _persist(batch, session_factory)

    for case in case_set.cases:
        started = perf_counter()
        outcome = await _run_one(case, session_factory, conversation_id, case_timeout_s)
        outcome.duration_ms = int((perf_counter() - started) * 1000)
        batch.outcomes.append(outcome)
        batch.counts = count_outcomes(batch.outcomes)
        if persist:
            await _persist(batch, session_factory)

    batch.finished_at = _now()
    batch.state = (
        "completed"
        if batch.outcomes and all(item.state == "completed" for item in batch.outcomes)
        else "partial"
    )
    if persist:
        await _persist(batch, session_factory)
    return batch
