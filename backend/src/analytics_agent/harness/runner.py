import asyncio
import json
import sqlite3
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from langchain_core.tools import tool

from analytics_agent.engines.sqlalchemy.engine import SQLAlchemyQueryEngine
from analytics_agent.harness.models import Claim, Evidence, Run, Step, ValidationResult
from analytics_agent.harness.validation import validate_growth

SALES_ROWS = [
    (1, "demo-store", 2024, 4000, "CNY"),
    (2, "demo-store", 2024, 6000, "CNY"),
    (3, "demo-store", 2025, 5000, "CNY"),
    (4, "demo-store", 2025, 6000, "CNY"),
]
SALES_SQL = """SELECT store_id, year, currency, SUM(amount_cents) AS amount_cents
FROM sales_records
WHERE store_id = 'demo-store' AND currency = 'CNY' AND year IN (2024, 2025)
GROUP BY store_id, year, currency ORDER BY year LIMIT 10"""


def query_sales(run: Run) -> Evidence:
    """Run the fixed synthetic fixture through the application's real SQL tool."""
    started = perf_counter()
    step = Step(kind="query")
    run.steps.append(step)
    try:
        with tempfile.TemporaryDirectory(prefix="harness-sales-", ignore_cleanup_errors=True) as directory:
            db = Path(directory) / "sales.db"
            with sqlite3.connect(db) as conn:
                conn.execute(
                    "CREATE TABLE sales_records (id INTEGER PRIMARY KEY, store_id TEXT, year INTEGER, amount_cents INTEGER, currency TEXT)"
                )
                conn.executemany("INSERT INTO sales_records VALUES (?, ?, ?, ?, ?)", SALES_ROWS)
            engine = SQLAlchemyQueryEngine({"url": f"sqlite:///{db}"})
            try:
                query = next(t for t in engine.get_tools() if t.name == "execute_sql")
                output = json.loads(query.invoke({"sql": SALES_SQL}))
            finally:
                # This synchronous helper owns its engine and runs in a worker thread.
                if engine._engine is not None:
                    engine._engine.dispose()
            if "error" in output:
                raise RuntimeError("query_failed")
            evidence = Evidence(run_id=run.id, step_id=step.id, sql=SALES_SQL, **output)
            run.evidence.append(evidence)
            return evidence
    except Exception:
        step.status, step.error = "error", "query_failed"
        raise
    finally:
        step.duration_ms = round((perf_counter() - started) * 1000, 3)


async def collect_agent_claim(run: Run) -> None:
    """A bounded real agent using the app's configured LLM; never invent a claim."""
    from langchain.agents import create_agent

    from analytics_agent.agent.llm import get_llm

    query_lock = asyncio.Lock()

    @tool
    async def query_demo_sales() -> str:
        """Query actual synthetic sales totals for demo-store in 2024 and 2025, in CNY cents."""
        # Reuse the first captured query; bound evidence size and calls.
        async with query_lock:
            item = run.evidence[0] if run.evidence else await asyncio.to_thread(query_sales, run)
        return item.model_dump_json()

    @tool
    async def submit_growth_claim(evidence_id: str, claimed_value: str, unit: str) -> str:
        """Submit the annual sales growth percentage, referencing query_demo_sales evidence."""
        if run.claim is not None:
            return "A claim has already been submitted."
        run.claim = Claim(evidence_id=evidence_id, claimed_value=claimed_value, unit=unit)
        run.steps.append(Step(kind="claim"))
        return "Claim recorded."

    llm = get_llm(streaming=False)
    run.model = str(getattr(llm, "model_name", getattr(llm, "model", "configured-model")))
    agent = create_agent(
        model=llm,
        tools=[query_demo_sales, submit_growth_claim],
        system_prompt="You analyse synthetic sales. Query demo-store sales for 2024 and 2025 using query_demo_sales, calculate annual growth, then call submit_growth_claim with the evidence ID, your computed value as a string and unit percent. Do not invent evidence. If unable to calculate, explain why without submitting a claim.",
    )
    output = await agent.ainvoke(
        {
            "messages": [
                {"role": "user", "content": "What is the 2025 annual sales growth for demo-store?"}
            ]
        },
        config={"recursion_limit": 8},
    )
    for message in reversed(output["messages"]):
        if getattr(message, "type", "") == "ai" and not getattr(message, "tool_calls", None):
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
            break


async def execute(run: Run, claimed_value: str = "10") -> Run:
    try:
        if run.source == "agent_generated":
            await asyncio.wait_for(collect_agent_claim(run), timeout=60)
        else:
            item = await asyncio.to_thread(query_sales, run)
            run.claim = Claim(evidence_id=item.id, claimed_value=claimed_value)
            run.steps.append(Step(kind="claim"))
        started = perf_counter()
        step = Step(kind="validation")
        run.steps.append(step)
        try:
            run.result = validate_growth(run.id, run.claim, run.evidence)
        except Exception:
            step.status, step.error = "error", "validator_error"
            raise
        finally:
            step.duration_ms = round((perf_counter() - started) * 1000, 3)
        run.state = "completed"
    except Exception as exc:
        # Exception text may include remote URLs or credentials. Store only safe codes.
        reason = "run_timeout" if isinstance(exc, TimeoutError) else "execution_error"
        if run.steps and run.steps[-1].error:
            reason = run.steps[-1].error
        run.result = ValidationResult(status="tool_error", reason=reason)
        run.state = "error"
    run.finished_at = datetime.now(UTC)
    return run
