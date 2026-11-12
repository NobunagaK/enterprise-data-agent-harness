"""Observable execution metadata; no prompts, private errors, or invented tokens."""

import asyncio
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from time import perf_counter
from typing import Any, TypeVar
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler

from analytics_agent.harness.models import Claim, Run, Step, TokenUsage

T = TypeVar("T")


def finish(step: Step, started: float) -> None:
    step.finished_at = datetime.now(UTC)
    step.duration_ms = round((perf_counter() - started) * 1000, 3)
    if step.status == "running":
        step.status = "completed"


def recorded_claim(run: Run, create_claim: Callable[[], Claim]) -> None:
    """Measure recording the structured claim, not unobservable model reasoning."""
    started = perf_counter()
    step = Step(kind="claim", status="running", started_at=datetime.now(UTC))
    run.steps.append(step)
    try:
        run.claim = create_claim()
    except Exception:
        step.status, step.error = "error", "claim_error"
        raise
    finally:
        finish(step, started)


async def query_worker(query: Callable[[Run], T], run: Run) -> T:
    """Drain our worker before propagating even repeated cancellation.

    This guarantees boundary cleanup for a terminating worker, not a hard
    timeout or termination of an uncooperative thread (tracked in issue #19).
    """
    task = asyncio.create_task(asyncio.to_thread(query, run))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        # Retrieve an exception without logging private engine details. The
        # caller's cancellation remains the outcome, even if the worker failed.
        if not task.cancelled():
            task.exception()
        raise


class ModelTrace(BaseCallbackHandler):
    run_inline = True

    def __init__(self, run: Run):
        self.run = run
        self.active: dict[UUID, tuple[Step, float]] = {}

    def on_chat_model_start(
        self, serialized: Any, messages: Any, *, run_id: UUID, **kwargs: Any
    ) -> None:
        step = Step(kind="model", status="running", started_at=datetime.now(UTC))
        self.run.steps.append(step)
        self.active[run_id] = (step, perf_counter())

    def on_llm_end(self, response: Any, *, run_id: UUID, **kwargs: Any) -> None:
        entry = self.active.pop(run_id, None)
        if entry is None:
            return
        step, started = entry
        finish(step, started)
        generations = response.generations
        if generations and generations[0]:
            message = getattr(generations[0][0], "message", None)
            usage = getattr(message, "usage_metadata", None)
            if isinstance(usage, Mapping):
                values = {
                    k: v
                    for k in ("input_tokens", "output_tokens")
                    if type(v := usage.get(k)) is int and v >= 0
                }
                if values:
                    step.token_usage = TokenUsage(**values)

    def on_llm_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        entry = self.active.pop(run_id, None)
        if entry is not None:
            step, started = entry
            reason = (
                "model_cancelled" if isinstance(error, asyncio.CancelledError) else "model_error"
            )
            step.status, step.error = "error", reason
            finish(step, started)

    def close_active(self, reason: str) -> None:
        """Close observed starts even if a provider omitted its terminal callback."""
        for step, started in self.active.values():
            step.status, step.error = "error", reason
            finish(step, started)
        self.active.clear()
