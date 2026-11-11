"""Regressions for PR #15's real pool starvation and orphan-report findings."""

import asyncio

import pytest
from analytics_agent.api.harness_batches import get_batch_session_factory, router
from analytics_agent.db.base import get_session
from analytics_agent.db.models import Base, Conversation
from analytics_agent.harness import batch as batch_module
from analytics_agent.harness import runner, store
from analytics_agent.harness.cases import CaseDefinition, CaseSet
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
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
