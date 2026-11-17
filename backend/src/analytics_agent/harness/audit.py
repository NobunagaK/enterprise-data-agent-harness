"""Read-only structural acceptance checks; never reclassify numerical results."""

from collections import Counter

from analytics_agent.harness.models import Run


def audit_run(run: Run) -> dict:
    issues: list[dict] = []

    def flag(code: str, record_id: str | None = None) -> None:
        issues.append({"code": code, "record_id": record_id})

    steps = Counter(step.id for step in run.steps)
    evidence_ids = Counter(item.id for item in run.evidence)
    terminal = run.state != "running"
    for value, count in steps.items():
        if count > 1:
            flag("duplicate_step_id", value)
    for value, count in evidence_ids.items():
        if count > 1:
            flag("duplicate_evidence_id", value)
    for step in run.steps:
        if step.parent_step_id is not None:
            if steps[step.parent_step_id] != 1:
                flag("invalid_parent_reference", step.id)
            else:
                visited = {step.id}
                parent: str | None = step.parent_step_id
                while parent is not None and steps[parent] == 1:
                    if parent in visited:
                        flag("parent_cycle", step.id)
                        break
                    visited.add(parent)
                    parent = next(item for item in run.steps if item.id == parent).parent_step_id
        if terminal and step.status == "running":
            flag("open_step_in_terminal_run", step.id)
        if step.started_at and step.finished_at:
            if step.started_at.utcoffset() is None or step.finished_at.utcoffset() is None:
                flag("naive_step_timestamp", step.id)
            elif step.finished_at < step.started_at:
                flag("reversed_step_timestamps", step.id)
        if (
            run.schema_version == 2
            and step.status in {"completed", "error"}
            and (step.started_at is None or step.finished_at is None or step.duration_ms is None)
        ):
            flag("missing_step_measurement", step.id)
    valid_evidence = 0
    for item in run.evidence:
        query = [step for step in run.steps if step.id == item.step_id]
        valid = True
        if item.run_id != run.id:
            flag("foreign_run_evidence", item.id)
            valid = False
        if len(query) != 1 or query[0].kind != "query" or query[0].status != "completed":
            flag("invalid_query_reference", item.id)
            valid = False
        if evidence_ids[item.id] != 1:
            valid = False
        valid_evidence += valid
    claim_reference_valid = None
    if run.claim is not None:
        matches = [item for item in run.evidence if item.id == run.claim.evidence_id]
        claim_reference_valid = (
            len(matches) == 1
            and matches[0].run_id == run.id
            and steps[matches[0].step_id] == 1
            and any(
                step.id == matches[0].step_id
                and step.kind == "query"
                and step.status == "completed"
                for step in run.steps
            )
        )
        if not claim_reference_valid:
            flag("invalid_claim_reference")
    if terminal and (run.result is None or run.finished_at is None):
        flag("missing_terminal_metadata")
    if run.state == "completed" and not any(
        step.kind == "validation" and step.status == "completed" for step in run.steps
    ):
        flag("missing_completed_validation")
    if run.result is not None:
        expected_unit = "CNY_cent" if run.rule_id == "sales_total" else "percent"
        if run.result.unit != expected_unit:
            flag("result_unit_mismatch")
        if (run.state == "error" and run.result.status != "tool_error") or (
            run.state == "completed" and run.result.status == "tool_error"
        ):
            flag("state_result_mismatch")
    return {
        "run_id": run.id,
        "case_id": run.case_id,
        "source": run.source,
        "rule_id": run.rule_id,
        "schema_version": run.schema_version,
        "state": run.state,
        "result_status": run.result.status if run.result else None,
        "terminal": terminal,
        "evidence_count": len(run.evidence),
        "valid_evidence_count": valid_evidence,
        "claim_reference_valid": claim_reference_valid,
        "issues": issues,
        "structurally_valid": not issues,
    }


def summarize_runs(runs: list[Run]) -> dict:
    """Keep source populations separate and expose every metric's denominator."""
    reports = [audit_run(run) for run in runs]
    duplicate_ids = sorted(
        key for key, count in Counter(run.id for run in runs).items() if count > 1
    )
    groups = {}
    for source in ("test_injected", "agent_generated"):
        rows = [row for row in reports if row["source"] == source]
        claims = [row for row in rows if row["claim_reference_valid"] is not None]
        groups[source] = {
            "reports": len(rows),
            "terminal_reports": sum(row["terminal"] for row in rows),
            "structurally_valid_reports": sum(row["structurally_valid"] for row in rows),
            "evidence_links": {
                "numerator": sum(row["valid_evidence_count"] for row in rows),
                "denominator": sum(row["evidence_count"] for row in rows),
            },
            "claim_links": {
                "numerator": sum(row["claim_reference_valid"] for row in claims),
                "denominator": len(claims),
            },
            "result_counts": dict(Counter(row["result_status"] or "unfinished" for row in rows)),
        }
    return {
        "schema_version": 1,
        "duplicate_run_ids": duplicate_ids,
        "groups": groups,
        "runs": reports,
    }
