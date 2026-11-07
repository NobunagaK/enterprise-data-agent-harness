# F4 batch evaluation — executed checks

Date: 2026-11-07. Environment: Windows 11, Python 3.11.15, isolated venv with current
unlocked dependencies (not `uv sync --frozen`). Backend only; no frontend or remote model.

## Commands and results

```bash
PYTHONPATH=backend/src python -m pytest \
  tests/unit/test_harness.py tests/unit/test_harness_contracts.py \
  tests/unit/test_harness_batch.py -q
# 83 passed

ruff check  <changed files>
# All checks passed
ruff format --check <changed files>
# 5 files already formatted

mypy --config-file pyproject.toml \
  harness/cases.py harness/batch.py harness/batch_models.py \
  harness/batch_store.py api/harness_batches.py
# Success: no issues found in 5 source files
```

Harness tests: 73 before this branch (Sprint 1 + shared contracts) + 10 new batch tests.

The existing migration regression test upgrades to `head` twice; it now also asserts that
`harness_batches` exists after migration `007`, and that an earlier row survives.

## Covered behaviour

- bundled case set: 10 cases, unique IDs, versioned dataset, expected-status mix
  (2 passed / 4 failed / 4 unverifiable);
- duplicate case IDs and unknown case fields are rejected;
- unsafe or missing case-set IDs never touch the filesystem;
- every case gets its own `run_id` and carries its `case_id`;
- a middle failure (`RuntimeError`) is recorded as `error` and the later case completes;
- a middle timeout is recorded as `timeout` and the later case completes;
- batch snapshots persist and reload, and list by conversation;
- `expected_status` is not part of `RunRequest`;
- API: 201 + full counts, read-back by ID, list; 422 for unknown fields/unsafe IDs;
  404 for a missing case set or conversation.

## Not run / not claimed

- React batch panel (not implemented in this PR);
- Playwright or any browser flow for batches;
- full backend suite and MCP transport tests (local venv lacks the DataHub stack);
- Windows CI and Docker build (remote);
- any real-model execution. `agent_generated` cases would need provider credentials and a
  spending cap; nothing here claims a model accuracy result.
- interrupted-process recovery: a killed batch leaves `state="running"` in the last
  snapshot. This is stated as a limitation, not tested as a success path.
