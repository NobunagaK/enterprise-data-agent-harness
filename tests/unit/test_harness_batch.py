"""Batch evaluation: case loading, isolation, aggregation and persistence."""

import pytest
from analytics_agent.api.harness_batches import get_batch_session_factory
from analytics_agent.api.harness_batches import router as batches_router
from analytics_agent.db.base import get_session
from analytics_agent.db.models import Base
from analytics_agent.harness import batch as batch_module
from analytics_agent.harness import batch_store
from analytics_agent.harness.cases import (
    CaseDefinition,
    CaseSet,
    CaseSetNotFound,
    load_case_set,
)
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.fixture
async def sessions(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'batch.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def client(sessions):
    app = FastAPI()
    app.include_router(batches_router)

    async def get_test_session():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_batch_session_factory] = lambda: sessions
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


def mini(*cases: CaseDefinition) -> CaseSet:
    return CaseSet(
        case_set_id="mini",
        version="1",
        dataset_version="sales-v1",
        cases=list(cases),
    )


def case(case_id: str, claimed: str, expected: str | None = None) -> CaseDefinition:
    return CaseDefinition(case_id=case_id, claimed_value=claimed, expected_status=expected)


def test_bundled_case_set_is_versioned_and_unique():
    case_set = load_case_set("sprint2-sales-v1")
    ids = [item.case_id for item in case_set.cases]
    assert len(case_set.cases) == 10
    assert len(ids) == len(set(ids))
    assert {item.dataset_version for item in case_set.cases} == {"sales-v1"}
    expected = [item.expected_status for item in case_set.cases]
    assert expected.count("passed") == 2
    assert expected.count("failed") == 4
    assert expected.count("unverifiable") == 4


def test_case_set_rejects_duplicate_ids_and_unknown_fields():
    with pytest.raises(ValidationError):
        mini(case("dup", "10"), case("dup", "11"))
    with pytest.raises(ValidationError):
        CaseDefinition(case_id="x", claimed_value="10", expected_answer="10")


def test_loader_rejects_unsafe_or_missing_ids():
    for bad in ("../sprint2-sales-v1", "Sprint2", "nope", ""):
        with pytest.raises(CaseSetNotFound):
            load_case_set(bad)


async def test_batch_runs_every_case_with_distinct_runs(sessions):
    case_set = mini(
        case("a", "10", "passed"),
        case("b", "18.7", "failed"),
        case("c", "ten", "unverifiable"),
    )
    batch = await batch_module.run_batch(case_set, sessions)

    assert [item.state for item in batch.outcomes] == ["completed"] * 3
    assert [item.case_id for item in batch.outcomes] == ["a", "b", "c"]
    assert len({item.run_id for item in batch.outcomes}) == 3
    assert [item.result_status for item in batch.outcomes] == [
        "passed",
        "failed",
        "unverifiable",
    ]
    assert all(item.matches_expected for item in batch.outcomes)
    assert batch.counts.model_dump() == {
        "attempted": 3,
        "completed": 3,
        "passed": 1,
        "failed": 1,
        "unverifiable": 1,
        "tool_error": 0,
        "timeout": 0,
        "error": 0,
    }
    assert batch.state == "completed"


async def test_middle_case_failure_does_not_block_later_cases(sessions, monkeypatch):
    real = batch_module.run_case
    seen: list[str] = []

    async def flaky(request, session):
        seen.append(request.case_id)
        if request.case_id == "b":
            raise RuntimeError("simulated storage failure")
        return await real(request, session)

    monkeypatch.setattr(batch_module, "run_case", flaky)
    batch = await batch_module.run_batch(
        mini(case("a", "10"), case("b", "10"), case("c", "10")), sessions
    )

    assert seen == ["a", "b", "c"]
    assert [item.state for item in batch.outcomes] == ["completed", "error", "completed"]
    assert batch.outcomes[1].reason == "case_error"
    assert batch.outcomes[1].error_type == "RuntimeError"
    assert batch.outcomes[2].run_id is not None
    assert batch.counts.completed == 2 and batch.counts.error == 1
    assert batch.state == "partial"


async def test_case_timeout_is_recorded_and_later_cases_continue(sessions, monkeypatch):
    real = batch_module.run_case

    async def slow(request, session):
        if request.case_id == "b":
            raise TimeoutError
        return await real(request, session)

    monkeypatch.setattr(batch_module, "run_case", slow)
    batch = await batch_module.run_batch(
        mini(case("a", "10"), case("b", "10"), case("c", "10")),
        sessions,
        case_timeout_s=0.5,
    )

    assert [item.state for item in batch.outcomes] == ["completed", "timeout", "completed"]
    assert batch.outcomes[1].reason == "case_timeout"
    assert batch.counts.timeout == 1
    assert batch.state == "partial"


async def test_batch_snapshot_is_persisted_and_listed(sessions):
    batch = await batch_module.run_batch(mini(case("a", "10", "passed")), sessions)
    async with sessions() as session:
        loaded = await batch_store.get(session, batch.id)
        listed = await batch_store.list_batches(session, None)

    assert loaded is not None
    assert loaded.id == batch.id
    assert loaded.counts == batch.counts
    assert [item.case_id for item in loaded.outcomes] == ["a"]
    assert [item.id for item in listed] == [batch.id]


def test_expected_status_never_reaches_the_run_request():
    request = case("a", "10", "passed").to_request(None)
    assert request.case_id == "a"
    assert not hasattr(request, "expected_status")


async def test_batch_api_runs_bundled_set_and_reads_it_back(client):
    created = await client.post("/api/harness/batches", json={})
    assert created.status_code == 201
    payload = created.json()
    assert payload["case_set_id"] == "sprint2-sales-v1"
    assert payload["counts"]["attempted"] == 10
    assert payload["counts"]["completed"] == 10
    assert payload["counts"]["passed"] == 2
    assert payload["counts"]["failed"] == 4
    assert payload["counts"]["unverifiable"] == 4
    assert payload["state"] == "completed"

    fetched = await client.get(f"/api/harness/batches/{payload['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == payload["id"]

    listed = await client.get("/api/harness/batches")
    assert [item["id"] for item in listed.json()] == [payload["id"]]


async def test_batch_api_rejects_unknown_fields_and_sets(client):
    assert (await client.post("/api/harness/batches", json={"case_timeout": 1})).status_code == 422
    assert (
        await client.post("/api/harness/batches", json={"case_set_id": "../x"})
    ).status_code == 422
    assert (
        await client.post("/api/harness/batches", json={"case_set_id": "missing"})
    ).status_code == 404
    assert (
        await client.post("/api/harness/batches", json={"conversation_id": "missing"})
    ).status_code == 404
