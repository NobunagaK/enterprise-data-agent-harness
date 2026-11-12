"""Regressions for PR #15's real pool starvation and orphan-report findings."""

import asyncio
import threading
from datetime import UTC, datetime, timedelta, timezone

import pytest
from analytics_agent.api.harness_batches import get_batch_session_factory, router
from analytics_agent.db.base import get_session
from analytics_agent.db.models import Base, Conversation
from analytics_agent.harness import batch as batch_module
from analytics_agent.harness import batch_store, runner, store
from analytics_agent.harness.batch_models import Batch, BatchBudget, CaseOutcome, count_outcomes
from analytics_agent.harness.cases import CaseDefinition, CaseSet
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def cases():
    return CaseSet(
        case_set_id="lifecycle",
        version="1",
        dataset_version="sales-v1",
        cases=[CaseDefinition(case_id=name, claimed_value="10") for name in ("a", "b", "c")],
    )


@pytest.fixture
async def sessions(tmp_path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'pool.db'}",
        pool_size=1,
        max_overflow=0,
        pool_timeout=0.2,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def test_conversation_batch_releases_preflight_connection(sessions):
    async with sessions() as session:
        session.add(
            Conversation(id="conversation", title="Lifecycle test", engine_name="sqlalchemy")
        )
        await session.commit()
    app = FastAPI()
    app.include_router(router)

    async def dependency():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_session] = dependency
    app.dependency_overrides[get_batch_session_factory] = lambda: sessions
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/harness/batches", json={"conversation_id": "conversation"}
        )
    assert response.status_code == 201
    assert response.json()["counts"]["completed"] == 10


@pytest.mark.parametrize("failure", ["timeout", "final_save", "initial_save"])
async def test_failed_case_retains_only_confirmed_run_and_later_cases_continue(
    sessions, monkeypatch, failure
):
    original_execute, original_save = runner.execute, store.save
    cancelled_run_ids = []

    async def execute(run, value):
        if run.case_id == "b" and failure == "timeout":
            try:
                await asyncio.Event().wait()  # Real cancellation after the initial commit.
            except asyncio.CancelledError:
                cancelled_run_ids.append(run.id)
                raise
        return await original_execute(run, value)

    async def save(session, run):
        if run.case_id == "b" and (
            (failure == "final_save" and run.finished_at is not None) or failure == "initial_save"
        ):
            raise RuntimeError("private storage detail")
        await original_save(session, run)

    monkeypatch.setattr(runner, "execute", execute)
    monkeypatch.setattr(store, "save", save)
    ids = []
    for _ in range(2):  # Repeated case IDs must still identify the correct execution.
        # Storage failures are not performance tests. Only the timeout scenario
        # needs a deadline; allow healthy real SQL/DB work time on Windows CI.
        case_timeout_s = 5 if failure == "timeout" else None
        batch = await batch_module.run_batch(cases(), sessions, case_timeout_s=case_timeout_s)
        first, failed, last = batch.outcomes
        assert first.result_status == last.result_status == "passed"
        assert failed.state == ("timeout" if failure == "timeout" else "error")
        assert failed.result_status is None
        assert "private storage detail" not in batch.model_dump_json()
        async with sessions() as session:
            assert (await store.get(session, first.run_id)).result.status == "passed"
            assert (await store.get(session, last.run_id)).result.status == "passed"
            if failure == "initial_save":
                assert failed.run_id is None
            else:
                assert failed.run_id is not None
                persisted = await store.get(session, failed.run_id)
                assert persisted is not None and persisted.case_id == "b"
                assert persisted.state == "running" and persisted.result is None
                ids.append(failed.run_id)
    if ids:
        assert len(set(ids)) == 2
    if failure == "timeout":
        assert cancelled_run_ids == ids


async def test_whole_batch_expiry_preserves_prefix_and_does_not_start_the_tail(
    sessions, monkeypatch
):
    real_execute = runner.execute
    seen, cancelled = [], []

    async def blocked_middle(run, value):
        seen.append(run.case_id)
        if run.case_id == "b":
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.append(run.id)
                raise
        return await real_execute(run, value)

    monkeypatch.setattr(runner, "execute", blocked_middle)
    report = await batch_module.run_batch(cases(), sessions, case_timeout_s=None, batch_timeout_s=5)
    assert report.state == "timed_out" and report.stop_reason == "batch_timeout"
    assert seen == ["a", "b"]
    assert [item.state for item in report.outcomes] == ["completed", "timeout", "skipped"]
    assert cancelled == [report.outcomes[1].run_id]
    assert report.outcomes[2].run_id is None and report.outcomes[2].matches_expected is None
    assert (
        report.counts.attempted,
        report.counts.completed,
        report.counts.timeout,
        report.counts.skipped,
    ) == (2, 1, 1, 1)
    async with sessions() as session:
        persisted = await batch_store.get(session, report.id)
        assert persisted == report
        assert (await store.get(session, report.outcomes[0].run_id)).result.status == "passed"
        assert len(await store.list_runs(session, None)) == 2
    assert not batch_store.ACTIVE_BATCH_IDS


async def test_repeated_batch_cancellation_drains_worker_and_terminal_write(sessions, monkeypatch):
    entered, release, worker_finished = threading.Event(), threading.Event(), threading.Event()
    saving_terminal, release_save = asyncio.Event(), asyncio.Event()
    real_query, real_save = runner.query_sales, batch_store.save

    def blocked_query(run):
        if run.case_id == "b":
            entered.set()
            release.wait(10)
        result = real_query(run)
        if run.case_id == "b":
            worker_finished.set()
        return result

    async def gated_save(session, batch):
        if batch.state == "cancelled":
            saving_terminal.set()
            await release_save.wait()
        await real_save(session, batch)

    monkeypatch.setattr(runner, "query_sales", blocked_query)
    monkeypatch.setattr(batch_store, "save", gated_save)
    task = asyncio.create_task(batch_module.run_batch(cases(), sessions))
    try:
        assert await asyncio.wait_for(asyncio.to_thread(entered.wait, 5), 6)
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        assert not task.done() and not worker_finished.is_set()
        release.set()
        await asyncio.wait_for(saving_terminal.wait(), 5)
        assert worker_finished.is_set()
        task.cancel()  # Cancel again while the final snapshot is being persisted.
        await asyncio.sleep(0)
        assert not task.done()
        release_save.set()
        with pytest.raises(asyncio.CancelledError):
            await task
    finally:
        release.set()
        release_save.set()
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    async with sessions() as session:
        reports = await batch_store.list_batches(session, None)
        assert len(reports) == 1
        report = reports[0]
        assert report.state == "cancelled" and report.stop_reason == "batch_cancelled"
        assert [item.state for item in report.outcomes] == ["completed", "cancelled", "skipped"]
        assert (report.counts.attempted, report.counts.cancelled, report.counts.skipped) == (
            2,
            1,
            1,
        )
        assert (await store.get(session, report.outcomes[0].run_id)).result.status == "passed"
        # A single-run cancellation still only guarantees its initial snapshot.
        assert report.outcomes[1].run_id is not None
    assert not batch_store.ACTIVE_BATCH_IDS


async def test_cancelled_batch_does_not_claim_a_failed_terminal_save(sessions, monkeypatch):
    entered = asyncio.Event()
    real_execute, real_save = runner.execute, batch_store.save

    async def blocked(run, value):
        if run.case_id == "b":
            entered.set()
            await asyncio.Event().wait()
        return await real_execute(run, value)

    async def failing_save(session, batch):
        if batch.state == "cancelled":
            raise RuntimeError("private database detail")
        await real_save(session, batch)

    monkeypatch.setattr(runner, "execute", blocked)
    monkeypatch.setattr(batch_store, "save", failing_save)
    task = asyncio.create_task(batch_module.run_batch(cases(), sessions))
    try:
        await asyncio.wait_for(entered.wait(), 5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    finally:
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    async with sessions() as session:
        report = (await batch_store.list_batches(session, None))[0]
        assert report.state == "running" and report.finished_at is None
        assert report.outcomes[0].result_status == "passed"
        assert "private database detail" not in report.model_dump_json()


async def test_internal_timeout_error_is_not_budget_expiry(sessions, monkeypatch):
    real = batch_module.run_case

    async def internal_timeout(request, session, **kwargs):
        if request.case_id == "b":
            raise TimeoutError("private provider detail")
        return await real(request, session, **kwargs)

    monkeypatch.setattr(batch_module, "run_case", internal_timeout)
    report = await batch_module.run_batch(cases(), sessions)
    assert [item.state for item in report.outcomes] == ["completed", "error", "completed"]
    assert report.outcomes[1].reason == "case_error"
    assert report.outcomes[1].error_type == "TimeoutError"
    assert report.counts.timeout == 0 and report.counts.error == 1
    assert "private provider detail" not in report.model_dump_json()


@pytest.mark.parametrize(
    "field,value",
    [
        ("case_timeout_s", 0),
        ("case_timeout_s", -1),
        ("case_timeout_s", float("nan")),
        ("case_timeout_s", float("inf")),
        ("case_timeout_s", 121),
        ("batch_timeout_s", 0),
        ("batch_timeout_s", -1),
        ("batch_timeout_s", float("nan")),
        ("batch_timeout_s", float("inf")),
        ("batch_timeout_s", 601),
        ("batch_timeout_s", None),
    ],
)
async def test_invalid_budgets_are_rejected_before_persistence(sessions, field, value):
    from analytics_agent.api.harness_batches import BatchRequest

    with pytest.raises(ValidationError):
        BatchRequest.model_validate({field: value})
    with pytest.raises(ValidationError):
        await batch_module.run_batch(cases(), sessions, **{field: value})
    async with sessions() as session:
        assert await batch_store.list_batches(session, None) == []
        assert await store.list_runs(session, None) == []


async def test_expired_unowned_snapshot_is_read_only_and_marks_unknown_work(sessions, monkeypatch):
    from analytics_agent.db.models import HarnessBatch

    report = batch_module.new_batch(cases(), None)
    report.deadline_at = (datetime.now(UTC) - timedelta(seconds=1)).astimezone(
        timezone(timedelta(hours=8))
    )
    report.active_case_id = "b"
    report.outcomes = [CaseOutcome(case_id="a", state="completed", result_status="passed")]
    report.counts = count_outcomes(report.outcomes)
    async with sessions() as session:
        await batch_store.save(session, report)
        raw_before = (await session.get(HarnessBatch, report.id)).report
        loaded = await batch_store.get(session, report.id)
        assert loaded.state == "interrupted" and loaded.finished_at is None
        assert [item.state for item in loaded.outcomes] == ["completed", "interrupted", "skipped"]
        assert (loaded.counts.attempted, loaded.counts.interrupted, loaded.counts.skipped) == (
            2,
            1,
            1,
        )
        assert (await batch_store.list_batches(session, None))[0] == loaded
        assert (await session.get(HarnessBatch, report.id)).report == raw_before
        monkeypatch.setattr(batch_store, "ACTIVE_BATCH_IDS", {report.id})
        assert (await batch_store.get(session, report.id)).state == "running"


def test_legacy_batches_and_nullable_per_case_budget_remain_compatible():
    report = Batch(
        id="legacy", case_set_id="old", case_set_version="1", started_at=datetime.now(UTC)
    )
    assert batch_store.visible_snapshot(report).state == "running"
    assert report.schema_version == 1 and report.case_ids == []
    budget = BatchBudget(case_timeout_s=None)
    assert budget.case_timeout_s is None and budget.batch_timeout_s == 300


async def test_cancelling_one_batch_keeps_another_batch_intact(sessions, monkeypatch):
    entered = asyncio.Event()
    real_execute = runner.execute

    async def blocked(run, value):
        if run.case_id == "slow":
            entered.set()
            await asyncio.Event().wait()
        return await real_execute(run, value)

    monkeypatch.setattr(runner, "execute", blocked)
    slow = cases().model_copy(
        update={"cases": [CaseDefinition(case_id="slow", claimed_value="10")]}
    )
    task = asyncio.create_task(batch_module.run_batch(slow, sessions))
    try:
        await asyncio.wait_for(entered.wait(), 5)
        completed = await batch_module.run_batch(cases(), sessions)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    finally:
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    async with sessions() as session:
        stored = await batch_store.get(session, completed.id)
        assert stored == completed and stored.state == "completed" and stored.counts.passed == 3
        reports = await batch_store.list_batches(session, None)
        assert len(reports) == 2 and {report.state for report in reports} == {
            "completed",
            "cancelled",
        }


async def test_repeated_cancellation_also_drains_initial_metadata_session(sessions, monkeypatch):
    entered, cleaning, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
    real_save = batch_store.save
    cleaned = []

    async def slow_initial_save(session, batch):
        if batch.state == "running":
            entered.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cleaning.set()
                await release.wait()
                cleaned.append(True)
                raise
        await real_save(session, batch)

    monkeypatch.setattr(batch_store, "save", slow_initial_save)
    task = asyncio.create_task(batch_module.run_batch(cases(), sessions))
    try:
        await asyncio.wait_for(entered.wait(), 5)
        task.cancel()
        await asyncio.wait_for(cleaning.wait(), 5)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done() and not cleaned
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
    finally:
        release.set()
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    assert cleaned == [True]
    async with sessions() as session:
        report = (await batch_store.list_batches(session, None))[0]
        assert (
            report.state == "cancelled"
            and report.counts.skipped == 3
            and report.counts.attempted == 0
        )
        assert await store.list_runs(session, None) == []
