"""Paired, offline F3 measurements; run with the project's Python environment.

Example: python scripts/benchmark_harness_trace.py --baseline /path/to/f2
    --candidate /path/to/f3 --output /tmp/trace-overhead.json
Only fixed test_injected cases are executed. No provider or database credentials
are used. Workers import each checkout in a separate process with the same venv.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import random
import statistics
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter_ns

CASES = [
    ("growth-boundary", "growth_rate", "10.01", "passed"),
    ("growth-failed", "growth_rate", "10.02", "failed"),
    ("growth-invalid", "growth_rate", "ten", "unverifiable"),
    ("total-exact", "sales_total", "11000", "passed"),
    ("total-failed", "sales_total", "11001", "failed"),
    ("total-invalid", "sales_total", "11000.1", "unverifiable"),
]


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)]


def summarize(before: list[float], after: list[float]) -> dict:
    if (
        len(before) != len(after)
        or len(before) < 2
        or any(not math.isfinite(x) or x <= 0 for x in before + after)
    ):
        raise ValueError("Need at least two positive, paired timing samples")
    delta = [b - a for a, b in zip(before, after, strict=True)]
    rng = random.Random(5351)
    bootstraps = [statistics.mean(rng.choices(delta, k=len(delta))) for _ in range(2000)]
    return {
        "samples": len(before),
        "baseline_mean_ms": statistics.mean(before),
        "candidate_mean_ms": statistics.mean(after),
        "baseline_median_ms": statistics.median(before),
        "candidate_median_ms": statistics.median(after),
        "baseline_p95_ms": percentile(before, 0.95),
        "candidate_p95_ms": percentile(after, 0.95),
        "paired_mean_delta_ms": statistics.mean(delta),
        "paired_median_delta_ms": statistics.median(delta),
        "mean_delta_percent": 100 * statistics.mean(delta) / statistics.mean(before),
        "paired_mean_delta_bootstrap_95_ms": [
            percentile(bootstraps, 0.025),
            percentile(bootstraps, 0.975),
        ],
        "raw_baseline_ms": before,
        "raw_candidate_ms": after,
    }


def business_signature(run) -> dict:
    """Exclude volatile identity/timing while checking actual evidence links."""
    signature = {
        "rule_id": run.rule_id,
        "source": run.source,
        "state": run.state,
        "model": run.model,
        "answer": run.answer,
        "claim": run.claim.model_dump(exclude={"evidence_id"}) if run.claim else None,
        "result": run.result.model_dump() if run.result else None,
        "claim_linked": bool(
            run.claim and any(item.id == run.claim.evidence_id for item in run.evidence)
        ),
        "evidence": [
            {
                **item.model_dump(exclude={"id", "run_id", "step_id"}),
                "run_linked": item.run_id == run.id,
                "step_linked": any(
                    step.id == item.step_id and step.kind == "query" for step in run.steps
                ),
            }
            for item in run.evidence
        ],
    }
    if (
        not signature["claim_linked"]
        or not signature["evidence"]
        or any(not item["run_linked"] or not item["step_linked"] for item in signature["evidence"])
    ):
        raise ValueError("Benchmark case has broken evidence links")
    return signature


def revision(root: Path) -> dict:
    prefix = ["git", "-C", str(root)]
    sha = subprocess.check_output([*prefix, "rev-parse", "HEAD"], text=True).strip()
    if subprocess.run(
        [*prefix, "diff", "--quiet", "HEAD", "--", "backend/src/analytics_agent/harness"],
        check=False,
    ).returncode:
        raise ValueError(f"Harness source has uncommitted changes: {root}")
    digest = hashlib.sha256()
    source = root / "backend/src/analytics_agent/harness"
    for path in sorted(source.glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return {"commit": sha, "harness_sha256": digest.hexdigest()}


def worker(root: Path) -> None:
    sys.path.insert(0, str(root / "backend/src"))
    from analytics_agent.harness import runner
    from analytics_agent.harness.models import Claim, Run

    if not Path(runner.__file__).resolve().is_relative_to(root.resolve()):
        raise RuntimeError("Worker loaded the wrong source checkout")
    print(json.dumps({"ready": True, "revision": revision(root)}), flush=True)
    with asyncio.Runner() as loop:
        for line in sys.stdin:
            request = json.loads(line)
            if request["mode"] == "run":
                run = Run(schema_version=2, source="test_injected", rule_id=request["rule_id"])
                started = perf_counter_ns()
                loop.run(runner.execute(run, request["value"]))
                encoded = run.model_dump_json()
                elapsed = perf_counter_ns() - started
                result = {
                    "elapsed_ms": elapsed / 1_000_000,
                    "snapshot_bytes": len(encoded.encode()),
                    "trace_steps": len(run.steps),
                    "business": business_signature(run),
                }
            elif request["mode"] == "claim":
                from analytics_agent.harness.trace import recorded_claim

                def create_claim():
                    return Claim(evidence_id="fixed-evidence", claimed_value="10")

                iterations = request["iterations"]
                started = perf_counter_ns()
                for _ in range(iterations):
                    run = Run(source="test_injected")
                    if request["record"]:
                        recorded_claim(run, create_claim)
                    else:
                        run.claim = create_claim()
                elapsed = perf_counter_ns() - started
                assert run.claim == create_claim()
                assert len(run.steps) == (1 if request["record"] else 0)
                result = {"elapsed_ms": elapsed / iterations / 1_000_000}
            else:
                raise ValueError("Unknown measurement mode")
            print(json.dumps(result, allow_nan=False), flush=True)


class Worker:
    def __init__(self, root: Path, temporary: Path):
        self.resources = ExitStack()
        # ExitStack owns this handle across requests and closes it with the worker.
        self.log = self.resources.enter_context(tempfile.TemporaryFile(mode="w+"))  # noqa: SIM115
        env = dict(
            os.environ, ANALYTICS_AGENT_CONFIG_DIR=str(temporary), DATAHUB_TELEMETRY_ENABLED="false"
        )
        try:
            self.process = subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), "--worker", str(root)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=self.log,
                text=True,
                env=env,
            )
        except BaseException:
            self.resources.close()
            raise
        self.reader = ThreadPoolExecutor(max_workers=1)
        try:
            self.metadata = self.read()
        except BaseException:
            self.close()
            raise

    def read(self) -> dict:
        try:
            line = self.reader.submit(self.process.stdout.readline).result(timeout=30)
            if not line:
                self.log.seek(0)
                raise RuntimeError("Benchmark worker exited: " + self.log.read()[-2000:])
            return json.loads(line)
        except BaseException:
            if self.process.poll() is None:
                self.process.kill()
            raise

    def measure(self, request: dict) -> dict:
        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()
        return self.read()

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.reader.shutdown(wait=True)
        self.process.stdin.close()
        self.process.stdout.close()
        self.resources.close()


def benchmark(
    baseline: Path, candidate: Path, samples: int, warmups: int, claim_iterations: int
) -> dict:
    results = []
    with tempfile.TemporaryDirectory(prefix="harness-trace-benchmark-") as temporary:
        left = Worker(baseline, Path(temporary) / "baseline")
        try:
            right = Worker(candidate, Path(temporary) / "candidate")
            try:
                for name, rule, value, expected in CASES:
                    before, after, sizes_before, sizes_after = [], [], [], []
                    request = {"mode": "run", "rule_id": rule, "value": value}
                    for index in range(warmups + samples):
                        # Counterbalance order; never run both measurements concurrently.
                        if index % 2:
                            b, a = right.measure(request), left.measure(request)
                        else:
                            a, b = left.measure(request), right.measure(request)
                        if (
                            a["business"] != b["business"]
                            or a["business"]["result"]["status"] != expected
                        ):
                            raise ValueError(f"Business/evidence equivalence failed for {name}")
                        if index >= warmups:
                            before.append(a["elapsed_ms"])
                            after.append(b["elapsed_ms"])
                            sizes_before.append(a["snapshot_bytes"])
                            sizes_after.append(b["snapshot_bytes"])
                    results.append(
                        {
                            "case_id": name,
                            "rule_id": rule,
                            "expected_status": expected,
                            "business_equivalent": True,
                            **summarize(before, after),
                            "baseline_snapshot_bytes_median": statistics.median(sizes_before),
                            "candidate_snapshot_bytes_median": statistics.median(sizes_after),
                        }
                    )
                before, after = [], []
                for index in range(warmups + samples):
                    request = {"mode": "claim", "iterations": claim_iterations}
                    if index % 2:
                        b = right.measure({**request, "record": True})
                        a = right.measure({**request, "record": False})
                    else:
                        a = right.measure({**request, "record": False})
                        b = right.measure({**request, "record": True})
                    if index >= warmups:
                        before.append(a["elapsed_ms"])
                        after.append(b["elapsed_ms"])
                return {
                    "schema_version": 1,
                    "measured_at_utc": datetime.now(UTC).isoformat(),
                    "environment": {
                        "os": platform.platform(),
                        "machine": platform.machine(),
                        "python": platform.python_version(),
                        "logical_cpus": os.cpu_count(),
                        "dependencies": {
                            name: importlib.metadata.version(name)
                            for name in ["pydantic", "sqlalchemy", "langchain", "langgraph"]
                        },
                    },
                    "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    "baseline": left.metadata["revision"],
                    "candidate": right.metadata["revision"],
                    "samples_per_case": samples,
                    "warmups_per_case": warmups,
                    "workload": "Fixed test_injected SQL + validation + snapshot JSON; no provider, HTTP or report DB writes",
                    "case_comparisons": results,
                    "claim_recording": {
                        "iterations_per_sample": claim_iterations,
                        **summarize(before, after),
                    },
                    "limitations": [
                        "Version comparison includes F3 recording and execution-boundary changes; baseline already has minimal tracing.",
                        "Claim microbenchmark isolates recorded_claim only, including step construction/timestamps; it is not full-agent overhead.",
                        "Signed deltas and bootstrap intervals describe this environment; no universal SLA or speedup is inferred.",
                    ],
                }
            finally:
                right.close()
        finally:
            left.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--warmups", type=int, default=10)
    parser.add_argument("--claim-iterations", type=int, default=1000)
    args = parser.parse_args()
    if args.worker:
        worker(args.worker.resolve())
        return
    if not args.baseline or not args.candidate or not args.output:
        parser.error("--baseline, --candidate and --output are required")
    if args.samples < 2 or args.warmups < 0 or args.claim_iterations < 1:
        parser.error("Need samples >= 2, warmups >= 0 and claim-iterations >= 1")
    for root in (args.baseline, args.candidate):
        if not (root / "backend/src/analytics_agent/harness/runner.py").is_file():
            parser.error(f"Not a Harness checkout: {root}")
    result = benchmark(
        args.baseline.resolve(),
        args.candidate.resolve(),
        args.samples,
        args.warmups,
        args.claim_iterations,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Saved {len(CASES)} paired case measurements to {args.output}")


if __name__ == "__main__":
    main()
