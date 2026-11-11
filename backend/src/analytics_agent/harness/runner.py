import asyncio
import json
import sqlite3
import tempfile
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from langchain_core.tools import tool

from analytics_agent.engines.sqlalchemy.engine import SQLAlchemyQueryEngine
from analytics_agent.harness.models import Evidence, Run, Step
from analytics_agent.harness.rules import RULES, SALES_SQL  # noqa: F401 (legacy import)
from analytics_agent.harness.trace import ModelTrace, finish, query_worker, recorded_claim
from analytics_agent.harness.validation import rule_result

MODEL_TIMEOUT_SECONDS = 60

SALES_ROWS = [
    (1, "demo-store", 2024, 4000, "CNY"),
    (2, "demo-store", 2024, 6000, "CNY"),
    (3, "demo-store", 2025, 5000, "CNY"),
    (4, "demo-store", 2025, 6000, "CNY"),
]


def query_sales(run: Run) -> Evidence:
    """Run the fixed synthetic fixture through the application's real SQL tool."""
    sql = RULES[run.rule_id].sql
    started = perf_counter()
    step = Step(kind="query", status="running", started_at=datetime.now(UTC))
    run.steps.append(step)
    try:
        with tempfile.TemporaryDirectory(prefix="harness-sales-") as directory:
            db = Path(directory) / "sales.db"
            with closing(sqlite3.connect(db)) as conn, conn:
                conn.execute(
                    "CREATE TABLE sales_records (id INTEGER PRIMARY KEY, store_id TEXT, year INTEGER, amount_cents INTEGER, currency TEXT)"
                )
                conn.executemany("INSERT INTO sales_records VALUES (?, ?, ?, ?, ?)", SALES_ROWS)
            engine = SQLAlchemyQueryEngine({"url": f"sqlite:///{db}"})
            try:
                query = next(t for t in engine.get_tools() if t.name == "execute_sql")
                output = json.loads(query.invoke({"sql": sql}))
            finally:
                # This synchronous helper owns its engine and runs in a worker thread.
                if engine._engine is not None:
                    engine._engine.dispose()
            if "error" in output:
                raise RuntimeError("query_failed")
            evidence = Evidence(run_id=run.id, step_id=step.id, sql=sql, **output)
            run.evidence.append(evidence)
            return evidence
    except Exception:
        step.status, step.error = "error", "query_failed"
        raise
    finally:
        finish(step, started)


async def collect_agent_claim(run: Run) -> None:
    """A bounded real agent using the app's configured LLM; never invent a claim."""
    from langchain.agents import create_agent

    from analytics_agent.agent.llm import get_llm

    rule = RULES[run.rule_id]
    query_lock = asyncio.Lock()

    @tool
    async def query_demo_sales() -> str:
        """Query actual synthetic sales for the selected task scope, in CNY cents."""
        # Reuse the first captured query; bound evidence size and calls.
        async with query_lock:
            item = run.evidence[0] if run.evidence else await query_worker(query_sales, run)
        return item.model_dump_json()

    @tool(rule.claim_tool)
    async def submit_claim(evidence_id: str, claimed_value: str, unit: str) -> str:
        """Submit the task's calculated value and unit, referencing query_demo_sales evidence."""
        if run.claim is not None:
            return "A claim has already been submitted."
        recorded_claim(run, lambda: rule.claim(evidence_id, claimed_value, unit))
        return "Claim recorded."

    setup_started = perf_counter()
    setup_step = Step(kind="tool", status="running", started_at=datetime.now(UTC))
    run.steps.append(setup_step)
    try:
        llm = get_llm(streaming=False)
        run.model = str(getattr(llm, "model_name", getattr(llm, "model", "configured-model")))
        agent = create_agent(
            model=llm,
            tools=[query_demo_sales, submit_claim],
            system_prompt=(
                f"You analyse synthetic sales. Task: {rule.question} "
                f"Call query_demo_sales, calculate from its rows, then call {rule.claim_tool} "
                f"with the evidence ID, your computed value as a string and unit {rule.unit}. "
                "Do not invent evidence. If unable to calculate, explain why without submitting a claim."
            ),
        )
    except Exception:
        setup_step.status, setup_step.error = "error", "model_configuration_error"
        raise
    finally:
        finish(setup_step, setup_started)
    trace = ModelTrace(run)
    try:
        output = await agent.ainvoke(
            {"messages": [{"role": "user", "content": rule.question}]},
            config={"recursion_limit": 8, "callbacks": [trace]},
        )
    finally:
        # Provider callbacks can be missing on cancellation or transport failure.
        task = asyncio.current_task()
        trace.close_active("model_cancelled" if task and task.cancelling() else "model_error")
    for message in reversed(output["messages"]):
        if getattr(message, "type", "") == "ai" and not getattr(message, "tool_calls", None):
            answer_started = perf_counter()
            answer_step = Step(kind="answer", status="running", started_at=datetime.now(UTC))
            run.steps.append(answer_step)
            content = message.content
            text = (
                content
                if isinstance(content, str)
                else "".join(
                    b.get("text", "")
                    for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                )
            )
            run.answer, run.answer_truncated = text[:8000], len(text) > 8000
            finish(answer_step, answer_started)
            break


async def execute(run: Run, claimed_value: str = "10") -> Run:
    try:
        if run.source == "agent_generated":
            await asyncio.wait_for(collect_agent_claim(run), timeout=MODEL_TIMEOUT_SECONDS)
        else:
            item = await query_worker(query_sales, run)
            recorded_claim(run, lambda: RULES[run.rule_id].claim(item.id, claimed_value))
        started = perf_counter()
        step = Step(kind="validation", status="running", started_at=datetime.now(UTC))
        run.steps.append(step)
        try:
            run.result = RULES[run.rule_id].validate(run.id, run.claim, run.evidence)
        except Exception:
            step.status, step.error = "error", "validator_error"
            raise
        finally:
            finish(step, started)
        run.state = "completed"
    except asyncio.CancelledError:
        # The service still propagates cancellation without claiming a final
        # persisted snapshot; close observable in-memory events before leaving.
        for active in run.steps:
            if active.status == "running":
                active.status, active.error = "error", "run_cancelled"
                active.finished_at = datetime.now(UTC)
        run.state = "error"
        run.result = rule_result(run.rule_id, "tool_error", "run_cancelled")
        run.finished_at = datetime.now(UTC)
        raise
    except Exception as exc:
        # Exception text may include remote URLs or credentials. Store only safe codes.
        reason = "run_timeout" if isinstance(exc, TimeoutError) else "execution_error"
        for active in run.steps:
            if active.status == "running":
                active.status, active.error = "error", reason
                active.finished_at = datetime.now(UTC)
        if not isinstance(exc, TimeoutError) and run.steps and run.steps[-1].error:
            reason = run.steps[-1].error
        run.result = rule_result(run.rule_id, "tool_error", reason)
        run.state = "error"
    run.finished_at = datetime.now(UTC)
    return run
