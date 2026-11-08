from types import SimpleNamespace
from uuid import uuid4

from analytics_agent.harness.models import Run
from analytics_agent.harness.trace import ModelTrace


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
