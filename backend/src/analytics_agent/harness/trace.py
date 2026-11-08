"""Observable execution metadata for persisted run reports."""

import asyncio
from datetime import UTC, datetime
from time import perf_counter
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler

from analytics_agent.harness.models import Run, Step, TokenUsage


def finish(step: Step, started: float) -> None:
    step.finished_at = datetime.now(UTC)
    step.duration_ms = round((perf_counter() - started) * 1000, 3)
    if step.status == "running":
        step.status = "completed"


def recorded_claim(run: Run) -> None:
    now = datetime.now(UTC)
    run.steps.append(Step(kind="claim", started_at=now, finished_at=now))


async def query_worker(query, run: Run):
    # Drain the owned worker before cancellation leaves this execution boundary.
    task = asyncio.create_task(asyncio.to_thread(query, run))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        try:
            await task
        except Exception:
            pass
        raise


class ModelTrace(BaseCallbackHandler):
    run_inline = True

    def __init__(self, run: Run):
        self.run = run
        self.active: dict[UUID, tuple[Step, float]] = {}

    def on_chat_model_start(self, serialized, messages, *, run_id, **kwargs):
        step = Step(kind="model", status="running", started_at=datetime.now(UTC))
        self.run.steps.append(step)
        self.active[run_id] = (step, perf_counter())

    def on_llm_end(self, response, *, run_id, **kwargs):
        entry = self.active.pop(run_id, None)
        if entry is None:
            return
        step, started = entry
        finish(step, started)
        generations = response.generations
        if generations and generations[0]:
            message = getattr(generations[0][0], "message", None)
            usage = getattr(message, "usage_metadata", None)
            if usage:
                values = {
                    k: v
                    for k in ("input_tokens", "output_tokens")
                    if type(v := usage.get(k)) is int and v >= 0
                }
                if values:
                    step.token_usage = TokenUsage(**values)

    def on_llm_error(self, error, *, run_id, **kwargs):
        entry = self.active.pop(run_id, None)
        if entry is not None:
            step, started = entry
            step.status, step.error = "error", "model_error"
            finish(step, started)
