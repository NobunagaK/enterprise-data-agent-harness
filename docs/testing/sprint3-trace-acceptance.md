# Sprint 3 trace and evidence acceptance

S2 trace collection, UI and rule dispatch are the baseline. This increment adds
read-only offline inspection of exported `GET /api/harness/runs/{id}` JSON, not
a new report contract or numerical validator. Supply each run as a separate file.

```powershell
uv sync --frozen --extra dev
uv run python scripts/audit_harness_reports.py run-a.json run-b.json --output audit.json
uv run pytest tests/unit/test_harness_audit.py -q
```

Exit 0 means all supplied reports parsed, have unique run IDs, are terminal and
pass the structural checks. Exit 1 means invalid inputs, duplicate runs, running
reports or structural findings; the JSON preserves each finding. Exit 2 means
invalid command arguments. Output must not be an input file. Source exports are
never rewritten. Invalid input payloads, SQL, answers and raw exceptions are not
copied into the summary; identifiers remain available for investigation.

## Frozen scope and denominators

| Check | Acceptance |
|---|---|
| Evidence ownership | Same run, unique evidence ID, unique completed query step |
| Claim reference | Exactly one evidence record, same run and valid query link |
| Parent reference | Unique existing parent, no self-reference or ancestry cycle |
| Terminal reports | Result and finish timestamp present, no running steps |
| Completed execution | Completed validation step, result other than tool_error |
| Error execution | tool_error result; numerical failure alone is not an execution error |
| Measurements | Schema 2 completed/error steps have timestamps and duration; available timestamps ordered and timezone aware |
| Rule unit | growth_rate uses percent; sales_total uses CNY_cent |

Source populations (`test_injected`, `agent_generated`) are always separate.
Evidence-link numerator is valid evidence records and denominator is all evidence
records in that source population. Claim-link numerator is valid claim references
and denominator is reports containing a claim. Zero denominators remain explicit
0/0 counts, never an invented 100%. Structural report count includes running
reports; terminal count is separate. Duplicate run IDs invalidate the command;
group counts remain raw input counts and must not be used as accepted metrics.

Legacy schema 1 reports do not require retroactively invented step measurements.
Missing model usage is allowed; the existing Run parser rejects invalid token
counts, negative durations and unsupported schemas. The tool does not infer
hidden reasoning, retries, model identity, or missing events.

## Acceptance matrix and remaining evidence

| Scenario | Evidence for this increment |
|---|---|
| Both rules, pass/fail/unverifiable | Actual local SQLite runner reports checked in automated tests |
| Foreign/duplicate/missing evidence, cycles, open steps, wrong units | Deliberately corrupted reports in regression tests |
| Invalid input, output overwrite, source separation, duplicate runs | CLI and summary regressions |
| Windows installation, bootstrap, browser/batch/history | Separate manual full-stack acceptance required |
| Configured live model | Separate API run exports required; source label alone is not proof of a live call |
| Failure isolation and second-rule modifiability | Existing S2 integration tests plus final team acceptance evidence |

This is structural checking, not business evidence validity: intentionally invalid
evidence used to test `unverifiable` can produce expected audit findings. Preserve
those findings and interpret them against the frozen case matrix. The tool does
not recompute validation outcomes, prove correct error attribution, calculate
detection/false-positive rates without ground truth, or discover missing planned
cases from supplied files. Use the batch manifest and independent expected
outcomes for those evaluations. It does not certify persistent storage from a
snapshot or establish a universal trace-completeness percentage.

Reuse #28 for trace overhead within its documented offline scope. Do not present
those results as live-model or Windows end-to-end latency. Final Windows UI,
live-provider and independent-member reproduction records must be added from
actual runs; no such acceptance is claimed by this document.

## Local validation record (2026-11-17)

Native Windows / Python 3.12, baseline `origin/main@536877a`:
234 tests passed across audit, core Harness, mixed cases, trace, contracts,
verification, batch lifecycle and trace benchmark modules (17 new audit tests).
Ruff lint/format, mypy for the two new source files and `git diff --check` passed.
The local run reused the existing repository Python environment with this
checkout's `backend/src` on PYTHONPATH. CI installs from the lockfile separately.
Existing Pydantic schema-shadowing and Alembic configuration warnings remained.
