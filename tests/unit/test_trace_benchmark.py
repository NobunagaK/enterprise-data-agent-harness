"""Statistical sign/quantiles and real offline benchmark worker regression."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/benchmark_harness_trace.py"
SPEC = importlib.util.spec_from_file_location("trace_benchmark", SCRIPT)
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)


def test_paired_summary_retains_negative_delta_and_nearest_rank_percentile():
    result = benchmark.summarize([10.0, 20.0, 30.0], [9.0, 18.0, 27.0])
    assert result["paired_mean_delta_ms"] == -2
    assert result["mean_delta_percent"] == -10
    assert result["baseline_p95_ms"] == 30
    assert result["paired_mean_delta_bootstrap_95_ms"][1] < 0


@pytest.mark.parametrize(
    "before,after",
    [
        ([], []),
        ([1], [1]),
        ([1, 2], [1]),
        ([0, 1], [1, 2]),
        ([float("nan"), 1], [1, 2]),
        ([1, 2], [1, float("inf")]),
    ],
)
def test_invalid_samples_are_rejected(before, after):
    with pytest.raises(ValueError):
        benchmark.summarize(before, after)


def test_equal_but_broken_evidence_links_cannot_count_as_equivalence():
    from analytics_agent.harness.models import Claim, Run

    run = Run(source="test_injected")
    run.claim = Claim(evidence_id="missing", claimed_value="10")
    with pytest.raises(ValueError, match="broken evidence links"):
        benchmark.business_signature(run)


def test_benchmark_workers_execute_real_sql_with_equivalent_results(tmp_path):
    output = tmp_path / "measurement.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--baseline",
            str(ROOT),
            "--candidate",
            str(ROOT),
            "--samples",
            "2",
            "--warmups",
            "0",
            "--claim-iterations",
            "2",
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text())
    assert len(report["case_comparisons"]) == 6
    assert {case["rule_id"] for case in report["case_comparisons"]} == {
        "growth_rate",
        "sales_total",
    }
    assert {case["expected_status"] for case in report["case_comparisons"]} == {
        "passed",
        "failed",
        "unverifiable",
    }
    assert all(case["business_equivalent"] for case in report["case_comparisons"])
    assert all(len(case["raw_baseline_ms"]) == 2 for case in report["case_comparisons"])
    assert report["baseline"] == report["candidate"]
    assert report["claim_recording"]["samples"] == 2
