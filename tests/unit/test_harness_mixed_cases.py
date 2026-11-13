"""Bundled mixed cases: discovery, actual SQL, persisted evidence and isolation."""

import pytest
from analytics_agent.api import harness_batches
from analytics_agent.db.base import get_session
from analytics_agent.db.models import Base
from analytics_agent.harness import batch_store, runner, store
from analytics_agent.harness.cases import load_case_set
from analytics_agent.harness.rules import RULES
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

MIXED_ID = "sprint2-sales-mixed-v1"


@pytest.fixture
async def sessions(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'mixed.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def client(sessions):
    app = FastAPI()
    app.include_router(harness_batches.router)

    async def get_test_session():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[harness_batches.get_batch_session_factory] = lambda: sessions
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def test_catalog_describes_both_sets_without_executing_or_disclosing_labels(
    client, sessions, monkeypatch
):
    async def unexpected_execution(*args, **kwargs):
        pytest.fail("Catalog discovery must not execute cases")

    monkeypatch.setattr(harness_batches, "run_batch", unexpected_execution)
    response = await client.get("/api/harness/batches/case-sets")
    assert response.status_code == 200
    catalog = {item["case_set_id"]: item for item in response.json()}
    assert set(catalog) == {"sprint2-sales-v1", MIXED_ID}
    assert catalog["sprint2-sales-v1"]["case_count"] == 10
    assert catalog["sprint2-sales-v1"]["rule_ids"] == ["growth_rate"]
    assert catalog[MIXED_ID] == {
        "case_set_id": MIXED_ID,
        "version": "1",
        "dataset_version": "sales-v1",
        "case_count": 8,
        "rule_ids": ["growth_rate", "sales_total"],
        "sources": ["test_injected"],
    }
    for item in response.json():
        assert not {"cases", "claimed_value", "expected_status", "note"} & item.keys()
    async with sessions() as session:
        assert await batch_store.list_batches(session, None) == []
        assert await store.list_runs(session, None) == []


async def test_mixed_api_executes_sql_and_persists_rule_specific_evidence(client, sessions):
    response = await client.post("/api/harness/batches", json={"case_set_id": MIXED_ID})
    assert response.status_code == 201
    payload = response.json()
    assert payload["state"] == "completed"
    assert payload["case_set_id"] == MIXED_ID and payload["case_set_version"] == "1"
    assert payload["counts"] == {
        "attempted": 8,
        "completed": 8,
        "passed": 3,
        "failed": 2,
        "unverifiable": 3,
        "tool_error": 0,
        "timeout": 0,
        "error": 0,
    }
    assert all(item["matches_expected"] is True for item in payload["outcomes"])
    assert len({item["run_id"] for item in payload["outcomes"]}) == 8
    evidence_ids = set()
    async with sessions() as session:
        for case, outcome in zip(load_case_set(MIXED_ID).cases, payload["outcomes"], strict=True):
            request = case.to_request(None)
            assert "expected_status" not in request.model_dump()
            run = await store.get(session, outcome["run_id"])
            assert run is not None and run.state == "completed"
            assert run.rule_id == case.rule_id and run.case_id == case.case_id
            assert run.source == "test_injected" and run.model is None
            assert run.result.unit == case.unit
            assert run.result.status == case.expected_status
            evidence = run.evidence[0]
            evidence_ids.add(evidence.id)
            assert evidence.sql == RULES[case.rule_id].sql
            assert evidence.run_id == run.id
            assert evidence.amount_unit == "CNY_cent"
            assert evidence.rows and run.claim.evidence_id == evidence.id
            assert any(step.id == evidence.step_id and step.kind == "query" for step in run.steps)
        assert len(evidence_ids) == 8
    fetched = await client.get(f"/api/harness/batches/{payload['id']}")
    assert fetched.json() == payload
    listed = await client.get("/api/harness/batches")
    assert listed.json() == [payload]


async def test_mixed_middle_query_error_keeps_earlier_and_later_reports(
    client, sessions, monkeypatch
):
    real_query = runner.query_sales

    def query_with_failure(run):
        if run.case_id == "total-exact":
            raise RuntimeError("controlled middle-case SQL failure")
        return real_query(run)

    monkeypatch.setattr(runner, "query_sales", query_with_failure)
    response = await client.post("/api/harness/batches", json={"case_set_id": MIXED_ID})
    assert response.status_code == 201
    payload = response.json()
    assert payload["counts"] == {
        "attempted": 8,
        "completed": 8,
        "passed": 2,
        "failed": 2,
        "unverifiable": 3,
        "tool_error": 1,
        "timeout": 0,
        "error": 0,
    }
    outcomes = payload["outcomes"]
    assert outcomes[4]["case_id"] == "total-exact"
    assert outcomes[4]["result_status"] == "tool_error"
    assert outcomes[4]["matches_expected"] is False
    assert all(item["matches_expected"] for item in outcomes[:4] + outcomes[5:])
    async with sessions() as session:
        runs = [await store.get(session, item["run_id"]) for item in outcomes]
        assert all(run is not None and run.result is not None for run in runs)
        assert runs[0].result.status == "passed"
        assert runs[4].result.status == "tool_error"
        assert runs[5].result.status == "failed"
        assert runs[-1].result.status == "unverifiable"
