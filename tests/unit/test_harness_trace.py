"""F3 regression tests use local doubles, never live-provider acceptance."""

import asyncio
import threading
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import pytest
from analytics_agent.db.models import Base
from analytics_agent.harness import runner, store
from analytics_agent.harness.contracts import GrowthRunRequest, SalesTotalRunRequest
from analytics_agent.harness.models import Claim, Run
from analytics_agent.harness.rules import RULES
from analytics_agent.harness.service import run_case
from analytics_agent.harness.trace import ModelTrace, query_worker, recorded_claim
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def test_model_trace_records_real_zero_and_unavailable_usage():
    run = Run(source="agent_generated")
    trace = ModelTrace(run)
    for usage in (None, {"input_tokens": 0, "output_tokens": 4}):
        call = uuid4()
        trace.on_chat_model_start({}, [], run_id=call)
        assert run.steps[-1].status == "running"
        response = SimpleNamespace(
            generations=[[SimpleNamespace(message=SimpleNamespace(usage_metadata=usage))]]
        )
        trace.on_llm_end(response, run_id=call)
    assert run.steps[0].token_usage is None
    assert run.steps[1].token_usage.input_tokens == 0
    assert all(step.finished_at and step.duration_ms >= 0 for step in run.steps)


def test_model_error_does_not_persist_exception_text():
    run = Run(source="agent_generated")
    trace = ModelTrace(run)
    call = uuid4()
    trace.on_chat_model_start({}, [], run_id=call)
    trace.on_llm_error(RuntimeError("secret-credential"), run_id=call)
    assert run.steps[0].error == "model_error"
    assert run.steps[0].status == "error"
    assert "secret-credential" not in run.model_dump_json()


def assert_terminal(step, status="completed"):
    assert step.status == status
    assert step.started_at is not None and step.finished_at >= step.started_at
    assert step.duration_ms is not None and step.duration_ms >= 0


@pytest.mark.parametrize("rule,value", [("growth_rate", "10.01"), ("sales_total", "11001")])
@pytest.mark.parametrize("failure", [None, "query", "validation"])
async def test_query_and_validation_producers_start_running(monkeypatch, rule, value, failure):
    run = Run(source="test_injected", rule_id=rule)
    observed = []
    original_query = runner.SQLAlchemyQueryEngine._run_query
    original_validation = RULES[rule].validate

    def query(self, sql, limit=None):
        step = run.steps[-1]
        assert step.kind == "query" and step.status == "running"
        assert step.started_at and step.finished_at is None and step.duration_ms is None
        observed.append("query")
        if failure == "query":
            return {"error": "private-query-detail"}
        return original_query(self, sql, limit)

    def validate(run_id, claim, evidence):
        step = run.steps[-1]
        assert step.kind == "validation" and step.status == "running"
        assert step.started_at and step.finished_at is None and step.duration_ms is None
        observed.append("validation")
        if failure == "validation":
            raise ValueError("private-validator-detail")
        return original_validation(run_id, claim, evidence)

    monkeypatch.setattr(runner.SQLAlchemyQueryEngine, "_run_query", query)
    monkeypatch.setitem(RULES, rule, replace(RULES[rule], validate=validate))
    await runner.execute(run, value)
    assert observed == (["query"] if failure == "query" else ["query", "validation"])
    for step in run.steps:
        assert_terminal(step, "error" if failure == step.kind else "completed")
    if failure:
        assert run.state == "error" and run.result.status == "tool_error"
        assert run.result.reason == ("query_failed" if failure == "query" else "validator_error")
    else:
        assert [step.kind for step in run.steps] == ["query", "claim", "validation"]
        assert run.evidence[0].step_id == run.steps[0].id
    assert run.result.unit == RULES[rule].unit
    assert "private-" not in run.model_dump_json()


@pytest.mark.parametrize("fails", [False, True])
def test_claim_completed_only_after_recording(fails):
    run = Run(source="test_injected")

    def create():
        assert run.claim is None
        assert run.steps[-1].status == "running"
        if fails:
            raise ValueError("private-claim-detail")
        return Claim(evidence_id="e", claimed_value="10")

    if fails:
        with pytest.raises(ValueError):
            recorded_claim(run, create)
        assert run.claim is None
    else:
        recorded_claim(run, create)
        assert run.claim.claimed_value == "10"
    assert_terminal(run.steps[-1], "error" if fails else "completed")
    assert "private-" not in run.model_dump_json()


@pytest.mark.parametrize("rule", ["growth_rate", "sales_total"])
@pytest.mark.parametrize("stage", ["configuration", "agent_setup"])
async def test_model_setup_failure_is_attributed_without_inventing_model_call(
    monkeypatch, rule, stage
):
    import langchain.agents
    from analytics_agent.agent import llm

    def fail(*args, **kwargs):
        raise ValueError("private-model-key")

    if stage == "configuration":
        monkeypatch.setattr(llm, "get_llm", fail)
    else:
        monkeypatch.setattr(llm, "get_llm", lambda **kw: SimpleNamespace(model_name="local-double"))
        monkeypatch.setattr(langchain.agents, "create_agent", fail)
    run = await runner.execute(Run(source="agent_generated", rule_id=rule))
    assert run.state == "error" and run.result.reason == "model_configuration_error"
    assert run.result.unit == RULES[rule].unit
    assert len(run.steps) == 1 and run.steps[0].kind == "tool"
    assert_terminal(run.steps[0], "error")
    assert run.steps[0].token_usage is None
    assert "private-model-key" not in run.model_dump_json()


@pytest.mark.parametrize(
    "usage,expected",
    [
        ({"input_tokens": 0}, (0, None)),
        ({"output_tokens": 0}, (None, 0)),
        ({"input_tokens": True, "output_tokens": -1}, None),
        ({"input_tokens": "9", "output_tokens": 1.5}, None),
        ("invalid-metadata", None),
        ({}, None),
    ],
)
def test_partial_or_invalid_usage_is_not_fabricated(usage, expected):
    run = Run(source="agent_generated")
    trace = ModelTrace(run)
    call = uuid4()
    trace.on_chat_model_start({}, [], run_id=call)
    trace.on_llm_end(
        SimpleNamespace(
            generations=[[SimpleNamespace(message=SimpleNamespace(usage_metadata=usage))]]
        ),
        run_id=call,
    )
    step = run.steps[0]
    assert_terminal(step)
    if expected is None:
        assert step.token_usage is None
    else:
        assert (step.token_usage.input_tokens, step.token_usage.output_tokens) == expected


def test_interleaved_model_calls_and_unknown_callbacks_do_not_cross_runs():
    a, b = Run(source="agent_generated"), Run(source="agent_generated")
    ta, tb = ModelTrace(a), ModelTrace(b)
    a1, a2, b1 = uuid4(), uuid4(), uuid4()
    ta.on_chat_model_start({}, [], run_id=a1)
    tb.on_chat_model_start({}, [], run_id=b1)
    ta.on_chat_model_start({}, [], run_id=a2)
    ta.on_llm_end(SimpleNamespace(generations=[]), run_id=a2)
    ta.on_llm_error(RuntimeError("private"), run_id=b1)  # not this trace's call
    assert b.steps[0].status == "running" and a.steps[0].status == "running"
    ta.close_active("model_error")
    tb.on_llm_end(SimpleNamespace(generations=[]), run_id=b1)
    assert_terminal(a.steps[0], "error")
    assert_terminal(a.steps[1])
    assert_terminal(b.steps[0])
    assert not ta.active and not tb.active


@pytest.mark.parametrize("fail_worker", [False, True])
async def test_repeated_cancellation_drains_owned_worker_before_boundary_exit(fail_worker):
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    run = Run(source="test_injected")

    def query(report):
        entered.set()
        try:
            assert release.wait(5)
            if fail_worker:
                raise ValueError("private-worker-detail")
            report.answer = "worker-finished"
        finally:
            finished.set()

    task = asyncio.create_task(query_worker(query, run))
    try:
        assert await asyncio.to_thread(entered.wait, 3)
        for _ in range(3):
            task.cancel()
            await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert not task.done() and not finished.is_set()
    finally:
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=3)
    assert finished.is_set()
    assert run.answer == (None if fail_worker else "worker-finished")


@pytest.mark.parametrize("mode", ["timeout", "cancel", "error"])
@pytest.mark.parametrize("rule", ["growth_rate", "sales_total"])
async def test_missing_terminal_callback_closes_model_step(monkeypatch, mode, rule):
    import langchain.agents
    from analytics_agent.agent import llm

    started = asyncio.Event()

    class Agent:
        async def ainvoke(self, messages, config):
            trace = config["callbacks"][0]
            trace.on_chat_model_start({}, [], run_id=uuid4())
            started.set()
            if mode == "error":
                raise RuntimeError("private-provider-detail")
            await asyncio.Event().wait()

    monkeypatch.setattr(llm, "get_llm", lambda **kw: SimpleNamespace(model_name="local-double"))
    monkeypatch.setattr(langchain.agents, "create_agent", lambda **kw: Agent())
    if mode == "timeout":
        monkeypatch.setattr(runner, "MODEL_TIMEOUT_SECONDS", 0.05)
    run = Run(source="agent_generated", rule_id=rule)
    task = asyncio.create_task(runner.execute(run))
    await asyncio.wait_for(started.wait(), timeout=2)
    if mode == "cancel":
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    else:
        await task
    assert (
        run.result.reason
        == {"timeout": "run_timeout", "cancel": "run_cancelled", "error": "model_error"}[mode]
    )
    assert run.result.unit == RULES[rule].unit
    model = next(step for step in run.steps if step.kind == "model")
    assert_terminal(model, "error")
    assert model.token_usage is None
    assert "private-" not in run.model_dump_json()
    assert run.finished_at and all(step.status != "running" for step in run.steps)


@pytest.mark.parametrize("rule", ["growth_rate", "sales_total"])
@pytest.mark.parametrize("failure", ["callback", "missing_callback", "configuration"])
async def test_internal_timeout_is_not_the_outer_deadline(monkeypatch, rule, failure):
    import langchain.agents
    from analytics_agent.agent import llm

    def get_model(**kwargs):
        if failure == "configuration":
            raise TimeoutError("private-configuration-timeout")
        return SimpleNamespace(model_name="local-double")

    class Agent:
        async def ainvoke(self, messages, config):
            trace = config["callbacks"][0]
            call = uuid4()
            trace.on_chat_model_start({}, [], run_id=call)
            error = TimeoutError("private-provider-timeout")
            if failure == "callback":
                trace.on_llm_error(error, run_id=call)
            raise error

    monkeypatch.setattr(llm, "get_llm", get_model)
    monkeypatch.setattr(langchain.agents, "create_agent", lambda **kwargs: Agent())
    run = await runner.execute(Run(source="agent_generated", rule_id=rule))
    expected = "model_configuration_error" if failure == "configuration" else "model_error"
    assert run.state == "error" and run.result.status == "tool_error"
    assert run.result.reason == expected
    assert run.result.unit == RULES[rule].unit
    assert run.steps[-1].error == expected
    assert_terminal(run.steps[-1], "error")
    assert run.finished_at and all(step.status != "running" for step in run.steps)
    assert "private-" not in run.model_dump_json()


@pytest.fixture
async def sessions(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'trace.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.parametrize(
    "case_request",
    [GrowthRunRequest(claimed_value="18.7"), SalesTotalRunRequest(claimed_value="11001")],
)
async def test_trace_identity_timing_and_units_survive_storage(sessions, case_request):
    async with sessions() as session:
        run = await run_case(case_request, session)
    async with sessions() as session:
        restored = await store.get(session, run.id)
    assert restored == run
    assert restored.result.status == "failed" and restored.result.unit == case_request.unit
    assert restored.claim.evidence_id == restored.evidence[0].id
    assert restored.evidence[0].run_id == restored.id
    assert restored.evidence[0].step_id == restored.steps[0].id
    for step in restored.steps:
        assert_terminal(step)


@pytest.mark.parametrize("rule,value", [("growth_rate", "10"), ("sales_total", "11000")])
async def test_observed_model_calls_answer_and_evidence_persist(monkeypatch, sessions, rule, value):
    import json

    from analytics_agent.agent import llm
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_core.messages import AIMessage

    class ToolModel(FakeMessagesListChatModel):
        def bind_tools(self, tools, **kwargs):
            return self

        async def _agenerate(self, messages, **kwargs):
            for message in reversed(messages):
                if getattr(message, "name", "") == "query_demo_sales":
                    self.responses[1].tool_calls[0]["args"]["evidence_id"] = json.loads(
                        message.content
                    )["id"]
                    break
            return await super()._agenerate(messages, **kwargs)

    definition = RULES[rule]
    model = ToolModel(
        responses=[
            AIMessage(content="", tool_calls=[{"name": "query_demo_sales", "args": {}, "id": "q"}]),
            AIMessage(
                content="",
                usage_metadata={"input_tokens": 0, "output_tokens": 2, "total_tokens": 2},
                tool_calls=[
                    {
                        "name": definition.claim_tool,
                        "args": {
                            "evidence_id": "from-query",
                            "claimed_value": value,
                            "unit": definition.unit,
                        },
                        "id": "c",
                    }
                ],
            ),
            AIMessage(content="Observed final answer."),
        ]
    )
    monkeypatch.setattr(llm, "get_llm", lambda **kwargs: model)
    request_type = GrowthRunRequest if rule == "growth_rate" else SalesTotalRunRequest
    async with sessions() as session:
        run = await run_case(request_type(source="agent_generated"), session)
    async with sessions() as session:
        restored = await store.get(session, run.id)
    assert restored == run and run.result.status == "passed"
    assert [s.kind for s in run.steps] == [
        "tool",
        "model",
        "query",
        "model",
        "claim",
        "model",
        "answer",
        "validation",
    ]
    for step in run.steps:
        assert_terminal(step)
    models = [step for step in run.steps if step.kind == "model"]
    assert models[0].token_usage is models[2].token_usage is None
    assert models[1].token_usage.input_tokens == 0
    assert models[1].token_usage.output_tokens == 2
    query = next(step for step in run.steps if step.kind == "query")
    assert run.evidence[0].step_id == query.id
    assert run.claim.evidence_id == run.evidence[0].id
    assert run.answer == "Observed final answer."
