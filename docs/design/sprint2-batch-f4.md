# Sprint 2 F4: batch evaluation (v1)

Status: implementation proposal for peer review; not an accepted increment.
Base: `sprint2/shared-contracts` (PR #14), itself based on `main@8359a46`.
Owner: Zikai He. Reviewers: Zefeng Chen (rule/boundary reuse, no duplicated formula),
Haoyu Shen (run/step identity, no fabricated trace).

## 1. Scope

In:

- load a bundled, versioned case set (`harness/case_sets/<case_set_id>.json`);
- run every case sequentially through `service.run_case`, one dedicated session per case;
- isolate per-case failures and timeouts, and continue with later cases;
- summarise attempted / completed / passed / failed / unverifiable / tool_error / timeout / error;
- persist one batch snapshot after every case (`harness_batches`, migration 007);
- expose `POST/GET /api/harness/batches`.

Out (explicitly):

- the React batch panel (`HarnessBatchPanel.tsx`) — follow-up PR;
- background scheduling, queues, retry/resume; the POST is synchronous;
- mixed-rule batches: `RunRequest` still accepts `growth_rate` only, so a case set is
  growth-only until F2 extends the shared request contract;
- a hard timeout that stops a worker thread. `case_timeout_s` wraps `run_case` in
  `asyncio.wait_for`; it releases the request but cannot kill a thread already running.

## 2. Data contracts

`CaseDefinition` (evaluation data, never model input):

| field | meaning |
|---|---|
| `case_id` | case definition identity, 1–128 chars, unique inside the set |
| `claimed_value` | injected claim string, ≤64 chars, never coerced to float |
| `rule_id` / `dataset_version` / `unit` | selectors; currently `growth_rate` / `sales-v1` / `percent` |
| `parameters` | `store_id`, `previous_year`, `current_year` (same `GrowthParameters` as the API) |
| `source` | `test_injected` (default) or `agent_generated`; carried into the run |
| `expected_status` | optional evaluation label; **never copied into `RunRequest`** |

`Batch` / `CaseOutcome` / `BatchCounts`:

- every case ends in exactly one `state`: `completed`, `timeout` or `error`;
- a `completed` case may still be `passed`, `failed`, `unverifiable` or `tool_error`;
- `expected_status` is compared only after the run and recorded as `matches_expected`;
- counts: `attempted = completed + timeout + error`, and
  `completed = passed + failed + unverifiable + tool_error`.

## 3. Execution semantics

- `run_batch(case_set, session_factory, conversation_id=None, case_timeout_s=None)`.
- Each case opens its own session because `service.run_case` commits; a case failure
  therefore cannot roll back a previously committed run.
- Exceptions from `run_case` become `CaseOutcome(state="error", reason="case_error",
  error_type=<class name>)`; `asyncio.TimeoutError` becomes `state="timeout"`.
- The batch snapshot is written after every case, so a crash keeps the completed prefix.
  A hard process kill leaves the last snapshot `state="running"`; callers must not read
  that as success. Reconciliation of interrupted batches is a follow-up (the single-run
  `stale_running` rule does not apply to batches).
- Storage failures propagate: a batch never claims a saved result it could not persist.

## 4. Persistence and API

- Table `harness_batches` (`id`, `conversation_id`, `created_at`, `report`), migration
  `007` with down_revision `006`; `006` is untouched.
- `POST /api/harness/batches` `{case_set_id?, conversation_id?, case_timeout_s?}` →
  201 with the completed batch. Unknown fields and unsafe case-set IDs are 422;
  missing case set or conversation is 404.
- `GET /api/harness/batches?conversation_id=` → latest 20 snapshots;
  `GET /api/harness/batches/{id}` → one snapshot.
- The request has no arbitrary SQL, expected answer or case-file path. Case sets are
  server-side resources selected by a slug.

## 5. Non-functional requirements

- **Reliability (NFR-01):** a middle `error` or `timeout` must not stop later cases.
  Evidence: `test_middle_case_failure_does_not_block_later_cases`,
  `test_case_timeout_is_recorded_and_later_cases_continue`; both assert the later case
  completes and the batch becomes `partial`.
- **Modifiability (NFR-02):** the batch module contains no validation formula; it calls
  `service.run_case`. Adding a rule stays inside F2 and does not touch `batch.py`.
  Evidence: no arithmetic in `batch.py`; the summary only counts `result.status`.

## 6. Known limitations

1. Synchronous execution: 10 injected cases complete in well under a second, but
   `agent_generated` cases are bounded by the existing 60 s model timeout each. A 20-case
   model batch can therefore hold an HTTP request for a long time; background execution is
   required before that becomes a supported workflow.
2. `case_timeout_s` releases the request but does not stop a running worker thread; the
   corresponding run may stay `running` until the single-run stale rule marks it.
3. The snapshot is rewritten in full after every case; acceptable at ≤20 cases, not a
   scalable event store.
4. No UI yet; the API is the acceptance surface for this PR.
5. `source` is carried from the case definition, not from the HTTP caller; a UI must not
   be allowed to override it later, otherwise the injected/model split is polluted.
