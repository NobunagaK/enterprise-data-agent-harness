"""F2 acceptance: real SQL + independent expected values; no live model claims."""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from analytics_agent.api.harness import router
from analytics_agent.db.base import get_session
from analytics_agent.db.models import Base
from analytics_agent.harness import batch, runner, store
from analytics_agent.harness.cases import CaseDefinition, CaseSet, TotalCaseDefinition
from analytics_agent.harness.contracts import RUN_REQUEST, GrowthRunRequest, SalesTotalRunRequest
from analytics_agent.harness.models import Claim, Evidence, Run
from analytics_agent.harness.rules import RULES, TOTAL_SQL
from analytics_agent.harness.service import run_case
from analytics_agent.harness.validation import validate_growth, validate_total
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def total_evidence(amount=11000):
    return Evidence(
        id="total-e",
        run_id="r",
        step_id="q",
        sql=TOTAL_SQL,
        columns=["store_id", "year", "currency", "amount_cents"],
        rows=[{"store_id": "demo-store", "year": 2025, "currency": "CNY", "amount_cents": amount}],
    )


def total_claim(value="11000", **updates):
    return Claim(evidence_id="total-e", claimed_value=value, unit="CNY_cent", year=2025).model_copy(
        update=updates
    )


@pytest.mark.parametrize(
    "amount,value,status,reason",
    [
        (11000, "11000", "passed", "within_tolerance"),
        (11000, "11000.0", "passed", "within_tolerance"),
        (11000, "1.1e4", "passed", "within_tolerance"),
        (11000, "11001", "failed", "outside_tolerance"),
        (11000, "10999", "failed", "outside_tolerance"),
        (11000, "110", "failed", "outside_tolerance"),
        (11000, "-1", "failed", "outside_tolerance"),
        (0, "0", "passed", "within_tolerance"),
        (None, "0", "unverifiable", "missing_or_invalid_amount"),
        (-1, "-1", "unverifiable", "negative_amount_unsupported"),
        (11000, "11000.01", "unverifiable", "non_integral_claim"),
        (11000, "11000." + "0" * 55 + "1", "unverifiable", "non_integral_claim"),
        (11000, "1e-999999", "unverifiable", "non_integral_claim"),
        (11000, "NaN", "unverifiable", "invalid_claim_value"),
        (11000, "sNaN", "unverifiable", "invalid_claim_value"),
        (11000, "Infinity", "unverifiable", "invalid_claim_value"),
        (11000, "1e999999", "unverifiable", "invalid_claim_value"),
        (11000, "eleven thousand", "unverifiable", "invalid_claim_value"),
        (11000, "", "unverifiable", "invalid_claim_value"),
        (11000.0, "11000", "passed", "within_tolerance"),
        (Decimal("11000"), "11000", "passed", "within_tolerance"),
        (Decimal("11000.5"), "11000", "unverifiable", "non_integral_amount"),
        (True, "1", "tool_error", "evidence_type_drift"),
        ("11000", "11000", "tool_error", "evidence_type_drift"),
        (float("nan"), "11000", "tool_error", "evidence_type_drift"),
        (Decimal("sNaN"), "11000", "tool_error", "evidence_type_drift"),
        (9007199254740993, "9007199254740993", "passed", "within_tolerance"),
        (9007199254740993, "9007199254740992", "failed", "outside_tolerance"),
    ],
)
def test_total_numerical_contract(amount, value, status, reason):
    result = validate_total("r", total_claim(value), [total_evidence(amount)])
    assert (result.status, result.reason) == (status, reason)
    assert result.unit == "CNY_cent" and result.tolerance == "0"
    assert result.rule_version == "sales_total-v1"
    assert result.tolerance_pp is result.difference_pp is None
    if status in ("passed", "failed"):
        assert Decimal(result.expected_value) == Decimal(amount)
        assert Decimal(result.difference) == abs(Decimal(value) - Decimal(amount))


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"id": "unknown"}, "evidence_not_found_or_wrong_run"),
        ({"run_id": "another-run"}, "evidence_not_found_or_wrong_run"),
        ({"truncated": True}, "truncated_evidence"),
        ({"amount_unit": "CNY_yuan"}, "unsupported_unit"),
        ({"dataset_version": "sales-v2"}, "unsupported_dataset"),
        ({"rows": []}, "missing_or_ambiguous_periods"),
    ],
)
def test_total_evidence_identity_and_completeness(change, reason):
    result = validate_total("r", total_claim(), [total_evidence().model_copy(update=change)])
    assert result.status == "unverifiable" and result.reason == reason


@pytest.mark.parametrize(
    "change",
    [
        {"unit": "percent"},
        {"unit": "CNY_yuan"},
        {"store_id": "other"},
        {"year": None},
        {"year": 2024},
    ],
)
def test_total_claim_scope(change):
    assert validate_total("r", total_claim(**change), [total_evidence()]).status == "unverifiable"


@pytest.mark.parametrize(
    "key,value", [("year", 2024), ("year", "2025"), ("store_id", "other"), ("currency", "USD")]
)
def test_total_evidence_scope(key, value):
    item = total_evidence()
    item.rows[0][key] = value
    assert validate_total("r", total_claim(), [item]).reason == "evidence_scope_mismatch"


def test_total_missing_and_ambiguous_inputs():
    assert validate_total("r", None, [total_evidence()]).reason == "missing_claim"
    item = total_evidence()
    assert (
        validate_total("r", total_claim(), [item, item]).reason == "evidence_not_found_or_wrong_run"
    )
    item.rows.append(dict(item.rows[0]))
    assert validate_total("r", total_claim(), [item]).reason == "missing_or_ambiguous_periods"


@pytest.mark.parametrize(
    "value,status",
    [
        ("10.01", "passed"),
        ("9.99", "passed"),
        ("10.01" + "0" * 57 + "1", "failed"),
        ("9.98" + "9" * 60, "failed"),
    ],
)
def test_growth_long_decimal_does_not_round_into_tolerance(value, status):
    item = total_evidence()
    item.rows.insert(
        0, {"store_id": "demo-store", "year": 2024, "currency": "CNY", "amount_cents": 10000}
    )
    assert len(value) <= 64
    claim = Claim(evidence_id=item.id, claimed_value=value)
    assert validate_growth("r", claim, [item]).status == status
    item.dataset_version = "sales-v2"
    assert validate_growth("r", claim, [item]).reason == "unsupported_dataset"


@pytest.fixture
async def sessions(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'f2.db'}")
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


async def test_total_http_real_sql_and_persistence(client, monkeypatch):
    calls = []
    original = runner.SQLAlchemyQueryEngine._run_query

    def capture(self, sql, limit=None):
        calls.append(sql)
        return original(self, sql, limit)

    monkeypatch.setattr(runner.SQLAlchemyQueryEngine, "_run_query", capture)
    response = await client.post(
        "/api/harness/runs",
        json={
            "rule_id": "sales_total",
            "case_id": "total-off-by-one",
            "claimed_value": "11001",
            "parameters": {"year": 2025, "store_id": "demo-store"},
            "unit": "CNY_cent",
        },
    )
    assert response.status_code == 201
    report = response.json()
    assert calls == [TOTAL_SQL]
    assert report["state"] == "completed" and report["result"]["status"] == "failed"
    assert report["result"]["expected_value"] == "11000"
    assert report["result"]["difference"] == "1"
    assert report["result"]["difference_pp"] is None
    assert report["claim"]["year"] == 2025
    item = report["evidence"][0]
    assert len(item["rows"]) == 1 and item["rows"][0]["amount_cents"] == 11000
    assert report["claim"]["evidence_id"] == item["id"]
    assert item["run_id"] == report["id"] and item["step_id"] == report["steps"][0]["id"]
    assert (await client.get(f"/api/harness/runs/{report['id']}")).json() == report
    assert (await client.get("/api/harness/runs")).json()[0] == report


@pytest.mark.parametrize(
    "body",
    [
        {"rule_id": "sales_total", "unit": "percent"},
        {"rule_id": "growth_rate", "unit": "CNY_cent"},
        {"rule_id": "sales_total", "parameters": {"previous_year": 2024}},
        {"rule_id": "growth_rate", "parameters": {"year": 2025}},
        {"rule_id": "sales_total", "parameters": {"year": 2024}},
        {"rule_id": "sales_total", "parameters": {"store_id": "other"}},
        {"rule_id": "sales_total", "claimed_value": 11000},
        {"rule_id": "sales_total", "dataset_version": "sales-v2"},
        {"rule_id": "sales_total", "sql": "SELECT 11000"},
        {"rule_id": "sales_total", "expected_status": "passed"},
        {"rule_id": "sales_total", "tolerance": "1"},
    ],
)
async def test_rule_specific_input_rejected_before_query(client, body):
    assert (await client.post("/api/harness/runs", json=body)).status_code == 422
    assert (await client.get("/api/harness/runs")).json() == []


def test_request_discriminator_defaults_and_immutability():
    assert isinstance(RUN_REQUEST.validate_python({}), GrowthRunRequest)
    request = RUN_REQUEST.validate_python({"rule_id": "sales_total"})
    assert isinstance(request, SalesTotalRunRequest)
    with pytest.raises(ValidationError):
        request.parameters.year = 2024
    schema = RUN_REQUEST.json_schema()
    assert schema["discriminator"]["propertyName"] == "rule_id"
    assert set(schema["discriminator"]["mapping"]) == {"growth_rate", "sales_total"}


@pytest.mark.parametrize("failure", ["query", "validation", "model", "missing_claim", "timeout"])
async def test_total_error_paths_keep_amount_metadata(monkeypatch, failure):
    if failure == "query":
        monkeypatch.setattr(
            runner.SQLAlchemyQueryEngine, "_run_query", lambda *a, **kw: {"error": "secret"}
        )
    elif failure == "validation":

        def broken(*args):
            raise RuntimeError("secret")

        monkeypatch.setitem(RULES, "sales_total", replace(RULES["sales_total"], validate=broken))
    else:

        async def collect(run):
            if failure == "timeout":
                raise TimeoutError("secret")
            if failure == "model":
                raise RuntimeError("secret")

        monkeypatch.setattr(runner, "collect_agent_claim", collect)
    source = "test_injected" if failure in ("query", "validation") else "agent_generated"
    run = await runner.execute(Run(rule_id="sales_total", source=source), "11000")
    assert run.result.status == ("unverifiable" if failure == "missing_claim" else "tool_error")
    assert run.result.unit == "CNY_cent" and run.result.tolerance == "0"
    assert run.result.tolerance_pp is run.result.difference_pp is None
    assert "secret" not in run.model_dump_json()
    if failure == "query":
        assert not run.evidence


async def test_total_stale_report_keeps_units(sessions):
    run = Run(
        source="test_injected",
        rule_id="sales_total",
        started_at=datetime.now(UTC) - timedelta(seconds=301),
    )
    async with sessions() as session:
        await store.save(session, run)
    async with sessions() as session:
        restored = await store.get(session, run.id)
    assert restored.result.reason == "stale_running"
    assert restored.result.unit == "CNY_cent" and restored.result.tolerance_pp is None


@pytest.mark.parametrize(
    "unit,value,status",
    [
        ("CNY_cent", "11000", "passed"),
        ("percent", "11000", "unverifiable"),
        ("CNY_cent", "11001", "failed"),
    ],
)
async def test_total_agent_tools_with_local_model_double(
    monkeypatch, sessions, unit, value, status
):
    """An orchestration test double is not a real-provider acceptance result."""
    from analytics_agent.agent import llm

    class ToolModel(FakeMessagesListChatModel):
        def bind_tools(self, tools, **kwargs):
            assert {t.name for t in tools} == {"query_demo_sales", "submit_total_claim"}
            return self

        async def _agenerate(self, messages, **kwargs):
            for message in reversed(messages):
                if getattr(message, "name", "") == "query_demo_sales":
                    item = json.loads(message.content)
                    self.responses[1].tool_calls[0]["args"]["evidence_id"] = item["id"]
                    break
            return await super()._agenerate(messages, **kwargs)

    model = ToolModel(
        responses=[
            AIMessage(content="", tool_calls=[{"name": "query_demo_sales", "args": {}, "id": "q"}]),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "submit_total_claim",
                        "args": {
                            "evidence_id": "from-query",
                            "claimed_value": value,
                            "unit": unit,
                        },
                        "id": "c",
                    }
                ],
            ),
            AIMessage(content=f"Total: {value} {unit}."),
        ]
    )
    monkeypatch.setattr(llm, "get_llm", lambda **kw: model)
    async with sessions() as session:
        run = await run_case(
            SalesTotalRunRequest(source="agent_generated", claimed_value="99999"), session
        )
    assert run.result.status == status and run.claim.claimed_value == value
    assert run.claim.unit == unit and run.source == "agent_generated"
    assert run.answer == f"Total: {value} {unit}."
    assert run.claim.evidence_id == run.evidence[0].id


async def test_mixed_rule_contract_uses_existing_batch_and_store(sessions):
    cases = [
        CaseDefinition(case_id="growth", claimed_value="10.01", expected_status="passed"),
        TotalCaseDefinition(case_id="total-wrong", claimed_value="11001", expected_status="failed"),
        TotalCaseDefinition(
            case_id="total-invalid", claimed_value="11000.1", expected_status="unverifiable"
        ),
        TotalCaseDefinition(case_id="total", claimed_value="11000", expected_status="passed"),
    ]
    case_set = CaseSet(
        case_set_id="mixed-test", version="1", dataset_version="sales-v1", cases=cases
    )
    case_set = CaseSet.model_validate_json(case_set.model_dump_json())
    for case in case_set.cases:
        assert "expected_status" not in case.to_request(None).model_dump()
    report = await batch.run_batch(case_set, sessions)
    assert report.state == "completed" and len(report.outcomes) == 4
    assert (report.counts.passed, report.counts.failed, report.counts.unverifiable) == (2, 1, 1)
    assert all(item.matches_expected for item in report.outcomes)
    for case, outcome in zip(cases, report.outcomes, strict=True):
        async with sessions() as session:
            run = await store.get(session, outcome.run_id)
        assert run.rule_id == case.rule_id and run.case_id == case.case_id
        assert run.result.unit == case.unit
        assert run.evidence[0].run_id == run.id
