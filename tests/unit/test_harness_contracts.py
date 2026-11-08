"""Public-boundary regression tests; synthetic data, no remote model claims."""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from analytics_agent.api.harness import router
from analytics_agent.db.base import get_session
from analytics_agent.db.models import Base, HarnessRun
from analytics_agent.harness import runner, store
from analytics_agent.harness.contracts import RunRequest
from analytics_agent.harness.models import Run, Step, TokenUsage, ValidationResult
from analytics_agent.harness.service import ConversationNotFound, run_case
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

LEGACY = Path(__file__).parents[1] / "fixtures/harness/sprint1-run.json"


@pytest.fixture
async def sessions(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'contracts.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def client(sessions):
    app = FastAPI()
    app.include_router(router)

    async def get_test_session():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def test_batch_caller_uses_public_service_with_distinct_runs(sessions):
    async with sessions() as session:
        first = await run_case(RunRequest(case_id="growth-wrong", claimed_value="18.7"), session)
        second = await run_case(
            RunRequest(case_id="growth-boundary", claimed_value="10.01"), session
        )
    assert first.id != second.id
    for report, expected in [(first, "failed"), (second, "passed")]:
        assert report.schema_version == 2
        assert report.state == "completed"
        assert report.result.status == expected
        assert report.result.unit == "percent"
        assert report.result.tolerance == report.result.tolerance_pp == "0.01"
        assert report.result.difference == report.result.difference_pp
        assert report.claim.evidence_id == report.evidence[0].id
        assert report.evidence[0].run_id == report.id
        assert report.evidence[0].step_id == report.steps[0].id
        assert report.evidence[0].rows[1]["amount_cents"] == 11000
        async with sessions() as reopened:
            assert await store.get(reopened, report.id) == report
    assert first.case_id == "growth-wrong"
    assert second.case_id == "growth-boundary"


async def test_legacy_and_explicit_requests_have_same_numerical_behavior(client):
    legacy = await client.post("/api/harness/runs", json={"claimed_value": "10.01"})
    explicit = await client.post(
        "/api/harness/runs",
        json={
            "case_id": "boundary",
            "rule_id": "growth_rate",
            "dataset_version": "sales-v1",
            "unit": "percent",
            "parameters": {"store_id": "demo-store", "previous_year": 2024, "current_year": 2025},
            "source": "test_injected",
            "claimed_value": "10.01",
        },
    )
    assert legacy.status_code == explicit.status_code == 201
    a, b = legacy.json(), explicit.json()
    assert a["result"] == b["result"]
    assert a["result"]["status"] == "passed"
    assert b["case_id"] == "boundary"
    assert (await client.get(f"/api/harness/runs/{b['id']}")).json() == b


@pytest.mark.parametrize(
    "body",
    [
        {"rule_id": "sales_total"},
        {"dataset_version": "sales-v2"},
        {"unit": "CNY_cent"},
        {"unit": "ratio"},
        {"parameters": {"store_id": "another-store"}},
        {"parameters": {"current_year": 2026}},
        {"parameters": {"currency": "USD"}},
        {"timeout_seconds": 1},
        {"expected_status": "passed"},
        {"claimed_value": 10.01},
        {"case_id": ""},
    ],
)
async def test_unimplemented_or_misspelled_inputs_rejected_before_execution(client, body):
    response = await client.post("/api/harness/runs", json=body)
    assert response.status_code == 422
    assert (await client.get("/api/harness/runs")).json() == []


async def test_malformed_claim_remains_unverifiable_not_request_error(client):
    response = await client.post("/api/harness/runs", json={"claimed_value": "not-a-number"})
    assert response.status_code == 201
    assert response.json()["result"]["status"] == "unverifiable"


async def test_missing_conversation_consistent_for_service_and_http(sessions, client):
    async with sessions() as session:
        with pytest.raises(ConversationNotFound):
            await run_case(RunRequest(conversation_id="missing"), session)
    assert (
        await client.post("/api/harness/runs", json={"conversation_id": "missing"})
    ).status_code == 404
    assert (await client.get("/api/harness/runs")).json() == []


async def test_old_snapshot_reads_without_rewriting_original_json(sessions, client):
    raw = LEGACY.read_text()
    old = json.loads(raw)
    async with sessions() as session:
        session.add(HarnessRun(id=old["id"], created_at=datetime.now(UTC), report=raw))
        await session.commit()
    response = await client.get(f"/api/harness/runs/{old['id']}")
    assert response.status_code == 200
    report = response.json()
    assert report["schema_version"] == 1
    assert report["case_id"] is None
    assert report["result"]["tolerance"] == old["result"]["tolerance_pp"]
    assert report["result"]["difference"] == old["result"]["difference_pp"]
    assert report["steps"][0]["token_usage"] is None
    for key in ["claim", "evidence", "source", "state", "started_at", "finished_at"]:
        assert report[key] == old[key]
    async with sessions() as session:
        assert (await session.get(HarnessRun, old["id"])).report == raw


async def test_cancellation_does_not_become_saved_success(sessions, monkeypatch):
    async def cancel(*args):
        raise asyncio.CancelledError

    monkeypatch.setattr(runner, "execute", cancel)
    async with sessions() as session:
        with pytest.raises(asyncio.CancelledError):
            await run_case(RunRequest(case_id="cancelled"), session)
    async with sessions() as session:
        rows = (await session.scalars(select(HarnessRun))).all()
        assert len(rows) == 1
        report = Run.model_validate_json(rows[0].report)
        assert report.state == "running"
        assert report.result is None


async def test_final_save_failure_is_not_reported_as_persisted_success(sessions, monkeypatch):
    original = store.save

    async def fail_final(session, run):
        if run.finished_at is not None:
            raise RuntimeError("storage unavailable")
        await original(session, run)

    monkeypatch.setattr(store, "save", fail_final)
    async with sessions() as session:
        with pytest.raises(RuntimeError, match="storage unavailable"):
            await run_case(RunRequest(), session)


def test_amount_result_contract_has_no_percentage_aliases():
    result = ValidationResult(
        status="failed",
        reason="outside_tolerance",
        rule_version="sales_total-v1",
        unit="CNY_cent",
        tolerance="0",
        difference="1",
        expected_value="11000",
        expected_display="11000",
        claimed_value="11001",
    )
    assert result.tolerance_pp is None
    assert result.difference_pp is None
    assert ValidationResult.model_validate_json(result.model_dump_json()) == result
    with pytest.raises(ValidationError):
        ValidationResult(status="passed", reason="example", unit="CNY_cent")
    with pytest.raises(ValidationError):
        ValidationResult(status="passed", reason="example", tolerance="0.02", tolerance_pp="0.01")


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-0.01", "not-a-number"])
def test_invalid_comparison_metadata_rejected(value):
    with pytest.raises(ValidationError):
        ValidationResult(status="failed", reason="example", difference=value)


def test_trace_can_express_unavailable_metrics_without_zeroes():
    step = Step(kind="model", status="running")
    assert step.duration_ms is None
    assert step.token_usage is None
    assert step.finished_at is None
    with pytest.raises(ValidationError):
        Step(kind="query", duration_ms=float("nan"))
    with pytest.raises(ValidationError):
        TokenUsage(input_tokens=-1)
    with pytest.raises(ValidationError):
        TokenUsage(input_tokens=True)
    with pytest.raises(ValidationError):
        Run(source="test_injected", schema_version=99)
