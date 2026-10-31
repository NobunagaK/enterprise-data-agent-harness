import json
from decimal import Decimal

import pytest
from analytics_agent.api.harness import router
from analytics_agent.db.base import get_session
from analytics_agent.db.models import Base
from analytics_agent.harness import runner, store
from analytics_agent.harness.models import Claim, Evidence, Run
from analytics_agent.harness.validation import validate_growth
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def evidence(run_id="run-1", previous=10000, current=11000):
    return Evidence(
        id="e-1",
        run_id=run_id,
        step_id="s-1",
        sql=runner.SALES_SQL,
        columns=["store_id", "year", "currency", "amount_cents"],
        rows=[
            {"store_id": "demo-store", "year": 2024, "currency": "CNY", "amount_cents": previous},
            {"store_id": "demo-store", "year": 2025, "currency": "CNY", "amount_cents": current},
        ],
    )


@pytest.mark.parametrize(
    "previous,current,claimed,status",
    [
        (10000, 11000, "10", "passed"),
        (10000, 11000, "18.7", "failed"),
        (10000, 11000, "10.01", "passed"),
        (10000, 11000, "10.0100001", "failed"),
        (10000, 11000, "9.99", "passed"),
        (10000, 11000, "10.02", "failed"),
        (10000, 9000, "-10", "passed"),
        (10000, 0, "-100", "passed"),
        (0, 11000, "10", "unverifiable"),
        (None, 11000, "10", "unverifiable"),
        (-10000, 11000, "10", "unverifiable"),
        (10000, -1, "10", "unverifiable"),
        (10000, 11000, "NaN", "unverifiable"),
        (10000, 11000, "Infinity", "unverifiable"),
        (10000, 11000, "ten", "unverifiable"),
        (10000, 11000, "1e999999", "unverifiable"),
    ],
)
def test_acceptance_values(previous, current, claimed, status):
    result = validate_growth(
        "run-1",
        Claim(evidence_id="e-1", claimed_value=claimed),
        [evidence(previous=previous, current=current)],
    )
    assert result.status == status
    if previous == 10000 and current == 11000 and status != "unverifiable":
        assert Decimal(result.expected_value) == Decimal("10")
        assert result.expected_display == "10.00"


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"run_id": "other-run"}, "evidence_not_found_or_wrong_run"),
        ({"id": "other-evidence"}, "evidence_not_found_or_wrong_run"),
        ({"truncated": True}, "truncated_evidence"),
        ({"amount_unit": "USD_cent"}, "unsupported_unit"),
        ({"rows": []}, "missing_or_ambiguous_periods"),
    ],
)
def test_evidence_guards(change, reason):
    result = validate_growth(
        "run-1",
        Claim(evidence_id="e-1", claimed_value="10"),
        [evidence().model_copy(update=change)],
    )
    assert result.status == "unverifiable"
    assert result.reason == reason


def test_scope_units_and_missing_claim():
    claim = Claim(evidence_id="e-1", claimed_value="10")
    assert validate_growth("run-1", None, [evidence()]).reason == "missing_claim"
    for update in [{"unit": "ratio"}, {"store_id": "other"}, {"current_year": 2026}]:
        assert (
            validate_growth("run-1", claim.model_copy(update=update), [evidence()]).status
            == "unverifiable"
        )
    for key, value in [("currency", "USD"), ("year", 2024), ("store_id", "other")]:
        item = evidence()
        item.rows[1][key] = value
        assert validate_growth("run-1", claim, [item]).reason == "evidence_scope_mismatch"


def test_rounding_does_not_change_comparison():
    result = validate_growth(
        "run-1", Claim(evidence_id="e-1", claimed_value="33.34"), [evidence(previous=3, current=4)]
    )
    assert result.status == "passed"
    assert result.expected_display == "33.33"
    assert Decimal(result.expected_value) != Decimal(result.expected_display)


async def test_real_query_path(monkeypatch):
    calls = []
    original = runner.SQLAlchemyQueryEngine._run_query

    def capture(self, sql, limit=None):
        calls.append(sql)
        return original(self, sql, limit)

    monkeypatch.setattr(runner.SQLAlchemyQueryEngine, "_run_query", capture)
    run = await runner.execute(Run(source="test_injected"), "18.7")
    assert calls == [runner.SALES_SQL]
    assert run.state == "completed"
    assert run.result.status == "failed"
    assert run.evidence[0].rows[0]["amount_cents"] == 10000
    assert run.evidence[0].rows[1]["amount_cents"] == 11000
    assert run.claim.evidence_id == run.evidence[0].id
    assert run.evidence[0].step_id == run.steps[0].id
    assert run.finished_at is not None


async def test_validator_error_is_not_claim_failure(monkeypatch):
    def broken(*args):
        raise ValueError("do-not-leak-this-secret")

    monkeypatch.setattr(runner, "validate_growth", broken)
    run = await runner.execute(Run(source="test_injected"))
    assert run.state == "error"
    assert run.result.status == "tool_error"
    assert run.result.reason == "validator_error"
    assert "do-not-leak" not in run.model_dump_json()


async def test_query_error(monkeypatch):
    monkeypatch.setattr(
        runner.SQLAlchemyQueryEngine, "_run_query", lambda *a, **kw: {"error": "secret"}
    )
    run = await runner.execute(Run(source="test_injected"))
    assert run.result.reason == "query_failed"
    assert run.state == "error"
    assert not run.evidence


async def test_agent_missing_claim_and_timeout(monkeypatch):
    async def no_claim(run):
        return None

    monkeypatch.setattr(runner, "collect_agent_claim", no_claim)
    run = await runner.execute(Run(source="agent_generated"))
    assert run.result.reason == "missing_claim"

    async def timed_out(run):
        raise TimeoutError

    monkeypatch.setattr(runner, "collect_agent_claim", timed_out)
    run = await runner.execute(Run(source="agent_generated"))
    assert run.result.status == "tool_error"
    assert run.result.reason == "run_timeout"


async def test_real_agent_loop_with_local_model_double(monkeypatch):
    """Exercise tool orchestration, not a remote model accuracy claim."""
    from analytics_agent.agent import llm

    class ToolModel(FakeMessagesListChatModel):
        def bind_tools(self, tools, **kwargs):
            return self

        async def _agenerate(self, messages, **kwargs):
            if len(messages) > 2:
                for message in reversed(messages):
                    if getattr(message, "name", "") == "query_demo_sales":
                        item = json.loads(message.content)
                        self.responses[1].tool_calls[0]["args"]["evidence_id"] = item["id"]
                        break
            return await super()._agenerate(messages, **kwargs)

    model = ToolModel(
        responses=[
            AIMessage(
                content="", tool_calls=[{"name": "query_demo_sales", "args": {}, "id": "q1"}]
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "submit_growth_claim",
                        "args": {
                            "evidence_id": "filled-from-tool",
                            "claimed_value": "10",
                            "unit": "percent",
                        },
                        "id": "c1",
                    }
                ],
            ),
            AIMessage(content="Sales grew 10%."),
        ]
    )
    monkeypatch.setattr(llm, "get_llm", lambda **kw: model)
    run = await runner.execute(Run(source="agent_generated"))
    assert run.result.status == "passed"
    assert len(run.evidence) == 1
    assert run.answer == "Sales grew 10%."
    assert not run.answer_truncated


def test_migration_preserves_existing_rows_and_is_repeatable(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from analytics_agent.config import settings
    from sqlalchemy import create_engine, inspect, text

    path = tmp_path / "migration.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite+aiosqlite:///{path}")
    config = Config("alembic.ini")
    command.upgrade(config, "005")
    engine = create_engine(f"sqlite:///{path}")
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO settings (key, value, updated_at) VALUES ('keep', 'original', CURRENT_TIMESTAMP)"
            )
        )
    command.upgrade(config, "head")
    command.upgrade(config, "head")
    assert "harness_runs" in inspect(engine).get_table_names()
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT value FROM settings WHERE key='keep'")) == "original"
    engine.dispose()


async def test_api_and_persistence(tmp_path):
    url = f"sqlite+aiosqlite:///{tmp_path / 'harness.db'}"
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def sessions():
        async with factory() as session:
            yield session

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_session] = sessions
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/harness/runs", json={"claimed_value": "18.7"})
        assert response.status_code == 201
        report = response.json()
        assert report["result"]["status"] == "failed"
        assert (await client.get(f"/api/harness/runs/{report['id']}")).json() == report
        assert (await client.get("/api/harness/runs")).json()[0] == report
        assert (await client.get("/api/harness/runs/missing")).status_code == 404
        assert (
            await client.post("/api/harness/runs", json={"conversation_id": "missing"})
        ).status_code == 404
        assert (
            await client.post("/api/harness/runs", json={"source": "forged"})
        ).status_code == 422
    await engine.dispose()
    # Reconnect using a new engine/session, with no in-memory report state.
    reopened = create_async_engine(url)
    async with async_sessionmaker(reopened)() as session:
        restored = await store.get(session, report["id"])
        assert restored.model_dump(mode="json") == report
    await reopened.dispose()

@pytest.mark.parametrize("amount", [Decimal(10000), 10000.0])
def test_integral_numeric_type_variants_are_accepted(amount):
    item = evidence()
    item.rows[0]["amount_cents"] = amount
    result = validate_growth("run-1", Claim(evidence_id="e-1", claimed_value="10"), [item])
    assert result.status == "passed"


def test_foreign_amount_type_is_tool_error_not_missing_data():
    item = evidence()
    item.rows[0]["amount_cents"] = "10000"
    result = validate_growth("run-1", Claim(evidence_id="e-1", claimed_value="10"), [item])
    assert result.status == "tool_error"
    assert result.reason == "evidence_type_drift"


def test_fractional_cent_is_unverifiable():
    item = evidence()
    item.rows[0]["amount_cents"] = Decimal("10000.5")
    result = validate_growth("run-1", Claim(evidence_id="e-1", claimed_value="10"), [item])
    assert result.status == "unverifiable"
    assert result.reason == "non_integral_amount"

