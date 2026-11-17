"""Audit explicitly supplied single-run JSON exports without modifying them."""

import argparse
import json
from pathlib import Path

from analytics_agent.harness.audit import summarize_runs
from analytics_agent.harness.models import Run
from pydantic import ValidationError


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_intermixed_args()
    try:
        collision = any(
            args.output.resolve() == path.resolve()
            or (args.output.exists() and path.exists() and args.output.samefile(path))
            for path in args.reports
        )
    except OSError:
        parser.error("unable to check output file identity")
    if collision:
        parser.error("output must not overwrite an input report")
    runs = []
    errors = []
    for index, path in enumerate(args.reports):
        try:
            runs.append(Run.model_validate_json(path.read_text(encoding="utf-8-sig")))
        except (OSError, UnicodeError, ValidationError, ValueError):
            # Do not expose model text, SQL, credentials or validation input payloads.
            errors.append({"input_index": index, "code": "invalid_or_unreadable_report"})
    result = summarize_runs(runs)
    result["input_count"] = len(args.reports)
    result["input_errors"] = errors
    try:
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except OSError:
        parser.error("unable to write output report; check directory and permissions")
    return int(
        bool(
            errors
            or result["duplicate_run_ids"]
            or any(not row["structurally_valid"] or not row["terminal"] for row in result["runs"])
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
