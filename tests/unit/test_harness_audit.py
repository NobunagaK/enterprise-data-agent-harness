"""Acceptance checks use actual offline SQL and deliberately corrupted exports."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from analytics_agent.harness.audit import audit_run, summarize_runs
from analytics_agent.harness.models import Run, Step
from analytics_agent.harness.runner import execute


@pytest.mark.parametrize(
    "rule,value",
    [
        ("growth_rate", "10"),
        ("growth_rate", "18.7"),
        ("sales_total", "11000"),
        ("sales_total", "11001"),
        ("sales_total", "11000.1"),
    ],
)
async def test_actual_sql_reports_pass_structural_checks(rule, value):
    run = await execute(Run(schema_version=2, source="test_injected", rule_id=rule), value)
    before = run.model_dump_json()
    result = audit_run(run)
    assert result["structurally_valid"], result["issues"]
    assert result["claim_reference_valid"]
    assert run.model_dump_json() == before


@pytest.mark.parametrize(
    "corruption,code",
    [
        ("foreign", "foreign_run_evidence"),
        ("duplicate", "duplicate_evidence_id"),
        ("missing", "invalid_claim_reference"),
        ("cycle", "parent_cycle"),
        ("open", "open_step_in_terminal_run"),
        ("unit", "result_unit_mismatch"),
    ],
)
async def test_corrupt_associations_are_detected(corruption, code):
    run = await execute(Run(schema_version=2, source="test_injected"))
    if corruption == "foreign":
        run.evidence[0].run_id = "other"
    elif corruption == "duplicate":
        run.evidence.append(run.evidence[0].model_copy(deep=True))
    elif corruption == "missing":
        run.claim.evidence_id = "missing"
    elif corruption == "cycle":
        run.steps[0].parent_step_id = run.steps[0].id
    elif corruption == "open":
        run.steps[0].status = "running"
    else:
        run.result.unit = "CNY_cent"
    assert code in {item["code"] for item in audit_run(run)["issues"]}


def test_sources_duplicates_and_empty_denominators_are_explicit():
    injected = Run(source="test_injected", id="duplicate")
    model = Run(source="agent_generated", id="duplicate")
    result = summarize_runs([injected, model])
    assert result["duplicate_run_ids"] == ["duplicate"]
    for group in result["groups"].values():
        assert group["reports"] == 1
        assert group["terminal_reports"] == 0
        assert group["claim_links"] == {"numerator": 0, "denominator": 0}
        assert group["result_counts"] == {"unfinished": 1}


async def test_legacy_measurements_are_not_invented():
    run = await execute(Run(source="test_injected"))
    for step in run.steps:
        step.started_at = step.finished_at = step.duration_ms = None
    assert audit_run(run)["structurally_valid"]
    run.schema_version = 2
    assert "missing_step_measurement" in {item["code"] for item in audit_run(run)["issues"]}


async def test_parent_cycle_and_duplicate_steps_are_not_confirmed_links():
    run = await execute(Run(schema_version=2, source="test_injected"))
    run.steps[0].parent_step_id = run.steps[1].id
    run.steps[1].parent_step_id = run.steps[0].id
    assert "parent_cycle" in {item["code"] for item in audit_run(run)["issues"]}
    run.steps.append(run.steps[0].model_copy(deep=True))
    result = audit_run(run)
    assert result["valid_evidence_count"] == 0
    assert result["claim_reference_valid"] is False


async def test_missing_terminal_metadata_validation_and_naive_times():
    run = await execute(Run(schema_version=2, source="test_injected"))
    run.result = None
    run.finished_at = None
    run.steps = [step for step in run.steps if step.kind != "validation"]
    run.steps[0].finished_at = run.steps[0].finished_at.replace(tzinfo=None)
    codes = {item["code"] for item in audit_run(run)["issues"]}
    assert {
        "missing_terminal_metadata",
        "missing_completed_validation",
        "naive_step_timestamp",
    } <= codes


def test_missing_parent_is_explicit_even_for_nonterminal_report():
    run = Run(source="agent_generated", steps=[Step(kind="model", parent_step_id="absent")])
    assert "invalid_parent_reference" in {item["code"] for item in audit_run(run)["issues"]}


async def test_cli_reports_bad_inputs_without_payload_and_preserves_exports(tmp_path):
    run = await execute(Run(schema_version=2, source="test_injected"))
    original = run.model_dump_json()
    good = tmp_path / "run.json"
    good.write_text(original, encoding="utf-8")
    bad = tmp_path / "bad.json"
    bad.write_text('{"source":"SECRET"}', encoding="utf-8")
    output = tmp_path / "audit.json"
    script = Path(__file__).resolve().parents[2] / "scripts/audit_harness_reports.py"
    command = [sys.executable, str(script), str(good), "--output", str(output)]
    assert subprocess.run(command, capture_output=True).returncode == 0
    assert subprocess.run(command + [str(bad)], capture_output=True).returncode == 1
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["input_count"] == 2
    assert data["input_errors"] == [{"input_index": 1, "code": "invalid_or_unreadable_report"}]
    assert "SECRET" not in output.read_text(encoding="utf-8")
    assert good.read_text(encoding="utf-8") == original
    overwrite = subprocess.run(command[:-1] + [str(good)], capture_output=True)
    assert overwrite.returncode == 2
    assert good.read_text(encoding="utf-8") == original


@pytest.mark.parametrize("alias_kind", ["hardlink", "case_variant"])
async def test_cli_rejects_output_alias_of_input(tmp_path, alias_kind):
    run = await execute(Run(schema_version=2, source="test_injected"))
    original = run.model_dump_json()
    source = tmp_path / "run.json"
    source.write_text(original, encoding="utf-8")
    alias = tmp_path / ("alias.json" if alias_kind == "hardlink" else "RUN.JSON")
    if alias_kind == "hardlink":
        alias.hardlink_to(source)
    elif not alias.exists() or not alias.samefile(source):
        pytest.skip("requires a case-insensitive filesystem")
    script = Path(__file__).resolve().parents[2] / "scripts/audit_harness_reports.py"
    result = subprocess.run(
        [sys.executable, str(script), str(source), "--output", str(alias)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "output must not overwrite an input report" in result.stderr
    assert "Traceback" not in result.stderr
    assert source.read_text(encoding="utf-8") == original


@pytest.mark.parametrize("output_kind", ["missing_parent", "directory"])
async def test_cli_output_write_failure_is_a_clean_error(tmp_path, output_kind):
    run = await execute(Run(schema_version=2, source="test_injected"))
    original = run.model_dump_json()
    source = tmp_path / "run.json"
    source.write_text(original, encoding="utf-8")
    output = tmp_path / "missing" / "audit.json" if output_kind == "missing_parent" else tmp_path
    script = Path(__file__).resolve().parents[2] / "scripts/audit_harness_reports.py"
    result = subprocess.run(
        [sys.executable, str(script), str(source), "--output", str(output)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "unable to write output report" in result.stderr
    assert "Traceback" not in result.stderr
    assert source.read_text(encoding="utf-8") == original


async def test_cli_duplicate_run_ids_fail_acceptance(tmp_path):
    run = await execute(Run(schema_version=2, source="test_injected"))
    original = run.model_dump_json()
    sources = [tmp_path / "first.json", tmp_path / "second.json"]
    for source in sources:
        source.write_text(original, encoding="utf-8")
    output = tmp_path / "audit.json"
    script = Path(__file__).resolve().parents[2] / "scripts/audit_harness_reports.py"
    result = subprocess.run(
        [sys.executable, str(script), *map(str, sources), "--output", str(output)],
        capture_output=True,
    )
    assert result.returncode == 1
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["input_count"] == 2
    assert data["input_errors"] == []
    assert data["duplicate_run_ids"] == [run.id]
    assert all(row["structurally_valid"] and row["terminal"] for row in data["runs"])
    assert all(source.read_text(encoding="utf-8") == original for source in sources)
