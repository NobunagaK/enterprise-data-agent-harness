# S1-T03 Review — Numerical Validation and Evidence Association

- **Reviewer:** Zikai He (C) · **Date:** 2026-10-31
- **Reviewed:** `sprint1/harness` @ `494388a` (PR #1) — `harness/validation.py`, `harness/models.py`, `harness/runner.py`, `harness/store.py`, `api/harness.py`, `tests/unit/test_harness.py`, `docs/sprint1.md`, `docs/design/sprint1-requirements-design.md`, `docs/process/sprint1-debt-risk-register.md`
- **Method:** line-by-line read of the rule; hand computation of 12 cases; the rule's arithmetic was re-executed in isolation (Decimal, `prec=60`, same expressions as `validation.py`) to confirm every number below. The harness suite was then **run on Windows 11** (Python 3.11.15, fresh venv, SQLAlchemy 2.x): **26 passed / 4 failed** - the four failures are F-09.
- **AI assistance disclosure:** this review was drafted with an AI coding agent under the reviewer's direction. Every finding, number and code suggestion below must be re-verified by the reviewer before it is treated as an accepted human judgement.

Scope of S1-T03 per the team plan: *Decimal, units, tolerance, evidence association and unsupported inputs; propose counterexamples; implement necessary validator fixes.*

---

## 1. Correct and worth keeping

These were checked and are sound; they should be protected by tests in later sprints.

1. **Integer-cent inputs with Decimal arithmetic.** `previous`/`current` are read as `int` cents and converted once (`validation.py:46`), so no binary float enters the comparison.
2. **Cross-multiplication instead of comparing a rounded quotient.** `abs(actual*previous - numerator) <= 0.01*previous` (`validation.py:70`) is algebraically equivalent to `|actual − expected| ≤ 0.01pp` for `previous > 0`, and avoids a recurring-quotient boundary error. `test_rounding_does_not_change_comparison` (3→4, claim `33.34`) proves the author knew about the recurring case.
3. **Exception paths cannot produce a pass.** `runner.execute` maps every exception to `tool_error` and `state="error"`; `test_validator_error_is_not_claim_failure` additionally asserts the exception text is not persisted. This satisfies the "异常不会计为通过" clause of the reliability NFR at the single-case level.
4. **Evidence is bound to a run.** `e.id == claim.evidence_id and e.run_id == run_id` (`validation.py:18`) blocks cross-run evidence substitution, and `test_evidence_guards` covers both directions.
5. **`test_injected` vs `agent_generated` is a first-class field**, not a comment. This is what makes the Sprint 1 error-rate claim honest.

---

## 2. Findings

Severity uses the register's own scale: **P1** threatens core acceptance, **P2** plan before the affected extension, **P3** monitor.

### F-01 · P1 · A claim rounded to one decimal is reported as `failed` whenever the true rate is not exact

- **Where:** `validation.py:62` (tolerance), `docs/sprint1.md` "Absolute tolerance is 0.01 percentage points, inclusive".
- **Observation (reproduced by re-running the rule's arithmetic):**

| previous | current | exact expected | claim | rule verdict | diff (pp) |
|---|---|---|---|---|---|
| 10000 | 11000 | 10 | `10.01` | passed | 0.01000 |
| 3 | 4 | 33.333333… | `33.34` | passed *(already tested)* | 0.00667 |
| 3 | 4 | 33.333333… | `33.33` | passed | 0.00333 |
| **3** | **4** | **33.333333…** | **`33.3`** | **failed** | 0.03333 |
| **7** | **9** | **28.571428…** | **`28.6`** | **failed** | 0.02857 |
| **11000** | **9000** | **−18.181818…** | **`−18.2`** | **failed** | 0.01818 |

- **Why it matters:** a real LLM asked for a growth rate almost always answers with one or two decimals ("about 33.3%"). Under a 0.01pp absolute tolerance, **any non-terminating growth rate makes a correctly-rounded answer a false failure**. The current fixture (10000→11000 = exactly 10%) hides this completely, so the suite is green and the metric `M2 误报率` will look perfect until the dataset changes — which is exactly what Sprint 2 does.
- **Direction of error:** it never produces a false `passed`, so it does not break the reliability stop-rule. It breaks **false-positive rate**, which is one of the two headline metrics of the project.
- **This is a policy decision, not a coding mistake.** The tolerance is documented and deliberate; the review's point is that its consequence has not been written down anywhere.
- **Options (needs a decision + ADR + evaluation-contract update):**
  - **A. Keep 0.01pp and declare the scope.** Add an explicit precondition: a claim is only comparable when the exact expected rate is representable within the claim's own decimal count; otherwise return `unverifiable(claim_precision_insufficient)`. Cheapest, no metric inflation, but more cases fall into "unverifiable", so `M3` must be re-based.
  - **B. Widen to `max(0.05pp, 0.5% of expected)`.** Accepts one-decimal answers (0.05pp is half a unit at 1 dp). `33.3` → diff 0.0333 ≤ 0.167 → passed.
  - **C. Compare on the display grid.** Round the expected value to the same precision the report shows, then compare. Fixes F-02 at the same time, but silently loosens the rule.
  - **Recommendation: B**, with the tolerance formula written into the evaluation contract, because B keeps "unverifiable" meaning "we could not check" rather than "the answer was formatted differently than we like".

### F-02 · P2 · The displayed expected value is less precise than the value used for the decision

- **Where:** `validation.py:66-68` (`expected_display` quantized to 2 dp, `ROUND_HALF_UP`) vs `validation.py:62` (decision uses full precision).
- **Observation:** for 3→4 the UI shows `33.33` while the rule tests against `33.333333…`. A user who reads "expected 33.33", answers `33.3`, and gets `failed` has no way to explain the verdict from the report. The existing test even asserts `expected_value != expected_display`, so the divergence is intentional but unexplained to the end user.
- **Consequence:** this is the project's core promise — *explain and locate the error*. A verdict that cannot be reproduced from what the report prints is a usability defect in the tool's own deliverable.
- **Proposed fix (small):** print the tolerance and the exact value together, e.g. `expected 33.3333% (displayed 33.33%), claimed 33.3%, diff 0.0333pp, tolerance ±0.167pp`. Requires `tolerance` to be surfaced in `ValidationResult` (it currently only carries the constant string `"0.01"` in `models.py:41`, which will be wrong under F-01 option B).

### F-03 · P2 · A change in the driver's numeric type silently turns every case unverifiable

- **Where:** `validation.py:42` `if type(value) is not int: return unknown("missing_or_invalid_amount")`.
- **Observation:** SQLite `SUM(amount_cents)` returns `int`, so today it works. On Postgres `NUMERIC`, on pandas-backed engines, or if the column type changes, the driver returns `Decimal`/`float` and **every** case becomes `unverifiable` with a reason that reads like "the data was missing". No error, no alarm, detection capability drops to zero while the tool still looks healthy.
- **Same class of risk:** `validation.py:27` hard-codes `demo-store` and `(2024, 2025)`; extending the dataset in Sprint 2 turns `unsupported_scope` into the dominant outcome unless the rule is parameterised.
- **Proposed fix:** accept `int`; accept `Decimal`/`float` only when losslessly integral (`value == int(value)`), converting to `int`; treat any other type as `tool_error("evidence_type_drift")` rather than `unverifiable`. Add one parametrized test per shape. This keeps "unverifiable" meaning *the business evidence is insufficient*, not *our plumbing changed*.

### F-04 · P2 · The metric taxonomy for a broken evidence link is not fixed anywhere

- **Where:** `validation.py:19-20` returns `unverifiable(evidence_not_found_or_wrong_run)`; `docs/sprint1.md` lists it among the unverifiable causes; the project's own acceptance example calls it "证据关联失败".
- **Consequence:** whether a broken link counts in the denominator of **M1 错误检出率** changes the reported number. R-02 in the register anticipates the situation but no document states the rule, and there is no evaluation contract in the repository at all (see F-08).
- **Proposed disposition:** keep `unverifiable`, and state explicitly in the evaluation contract that broken-link cases are reported in their own bucket and excluded from M1's denominator but included in "evidence association correctness". Record as a decision, not as code.

### F-05 · P1 · In real-model mode the model does not execute the SQL; the harness does

- **Where:** `runner.py` `collect_agent_claim` → `query_demo_sales` returns `run.evidence[0]` if it already exists, i.e. the evidence captured by the harness's own `query_sales` call.
- **Observation:** the agent therefore never runs its own query; it is handed the evidence and asked to compute a rate from it. So "real-model mode" validates *arithmetic consistency given evidence*, **not** *whether the agent's own answer agrees with the agent's own query results* — which is the sentence in the project's problem statement.
- **Consequence:** this is an external-validity limit that must be written into `docs/sprint1.md` "Running locally and independent acceptance" step 7 and into the final report, otherwise the evaluation over-claims. R-06 covers the general risk but not this specific mechanism.
- **Proposed disposition for Sprint 1:** document the limitation explicitly (do not silently expand scope). For Sprint 2, let the agent's tool call actually execute and capture its own SQL under the same `run_id`.

### F-06 · P1 · An interrupted run can stay `running` forever, which contradicts the reliability acceptance

- **Where:** `api/harness.py:create_run` persists the run **before** executing it; `docs/process/sprint1-debt-risk-register.md` TD-02 records the shortcut.
- **Review addition:** TD-02 is filed as maintenance debt, but it also breaks the acceptance wording "每个案例均有最终状态". A permanently-`running` record is neither a terminal state nor an error, so it silently disappears from any completeness count. It should be re-labelled **defect + debt**, P1, with a concrete reconciliation rule: on read, any run in `running` older than the configured timeout is normalised to `tool_error(stale_running)` and the original timestamp is preserved.
- **Note:** this is B's code and D's test ownership; raising it here because it is in the same acceptance clause as F-01/F-03.

### F-07 · P3 · Repository settings block the required Issue → PR traceability

- **Observation:** the fork has **Issues disabled** (`has_issues = false`), and PR #1 currently has **0 requested reviewers and 0 review comments**. The course project guide (Week 1 deck, p. 25) requires the issue to record the problem and acceptance criteria, the PR to link code/tests/review, and closing syntax to connect the accepted change back to the requirement.
- **Proposed disposition:** enable Issues (Settings → General → Features) or state in `docs/process/sprint1-team-plan.md` which artefact carries the requirement record. Also protect `main` and require one non-author approval before merge (R-09 already names this risk).

### F-08 · P2 · No evaluation contract exists in the repository

- **Observation:** the course requires the evaluation contract (task, data, baseline, metric, threshold, test cases) to be **frozen before comparison** (Week 1 deck p. 24/p. 29). The repo has requirements, design, debt/risk registers, but no file defining what M1–M6 mean or what passes.
- **Consequence:** F-01 and F-04 cannot be resolved by code alone — they are metric definitions. Without this file, Sprint 2's numbers have no fixed meaning and the report's evaluation section has no source of truth.
- **Proposed disposition:** add `docs/evaluation/contract-v0.1.md` before any Sprint 2 measurement, listing the case set, denominators, thresholds and the tolerance formula chosen in F-01.

### F-09 · P1 · The fixed-case path fails on Windows: the temp SQLite file is still open at cleanup

- **Where:** `runner.py:33` `with tempfile.TemporaryDirectory(prefix="harness-sales-") as directory:`
- **Observation (reproduced):** running the suite on Windows 11 / Python 3.11.15 gives **26 passed, 4 failed**. All four failures are on the `execute()` path: `test_real_query_path`, `test_validator_error_is_not_claim_failure`, `test_real_agent_loop_with_local_model_double`, `test_api_and_persistence`.
- **Root cause:** `query_sales` succeeds - `Evidence` with rows 10000/11000 is appended - then `TemporaryDirectory.__exit__` raises `PermissionError: [WinError 32] ... 'sales.db'` because the SQLite handle is still open. The bare `except Exception` in `query_sales` converts that into `step.error = "query_failed"`, so the run ends `tool_error(query_failed)` **after the evidence was captured**.
- **Consequence:** on Windows the Sprint 1 demo produces zero valid verdicts. It is invisible on Linux/macOS, which is where the reported 30 green tests came from, and `M5 execution completeness` still looks healthy because `tool_error` is a terminal state.
- **Verified fix:** `TemporaryDirectory(prefix="harness-sales-", ignore_cleanup_errors=True)` → **30 passed, 0 failed** on the same machine. A stricter alternative is to dispose the engine and retry the delete, or to build the fixture DB once per process; either way it needs a regression test that exercises the real query path on Windows (D owns the test matrix).
- **Severity:** P1 - the feature is unusable on a supported developer platform, and the failure is silent at the metric level.

---

## 3. Hand-checked case table (S1-T03 deliverable)

`exact` is computed by hand as `(current − previous) / previous × 100`; `rule` is the verdict produced by the reviewed arithmetic.

| # | previous | current | exact | claim | rule | covered by tests? |
|---|---|---|---|---|---|---|
| 1 | 10000 | 11000 | 10 | `10` | passed | yes |
| 2 | 10000 | 11000 | 10 | `18.7` | failed | yes |
| 3 | 10000 | 11000 | 10 | `10.01` | passed | yes |
| 4 | 10000 | 11000 | 10 | `10.02` | failed | yes |
| 5 | 10000 | 9000 | −10 | `−10` | passed | yes |
| 6 | 10000 | 0 | −100 | `−100` | passed | yes |
| 7 | 0 | 11000 | undefined | `10` | unverifiable `zero_denominator` | yes |
| 8 | 10000 | 11000 | 10 | `NaN`/`Infinity`/`ten`/`1e999999` | unverifiable `invalid_claim_value` | yes |
| 9 | 3 | 4 | 33.3333… | `33.34` | passed | yes |
| 10 | 3 | 4 | 33.3333… | `33.33` | passed | **no** |
| 11 | **3** | **4** | **33.3333…** | **`33.3`** | **failed (F-01)** | **no** |
| 12 | **7** | **9** | **28.5714…** | **`28.6`** | **failed (F-01)** | **no** |
| 13 | **11000** | **9000** | **−18.1818…** | **`−18.2`** | **failed (F-01)** | **no** |
| 14 | 10000 | 11000 | 10 | `10`, amount returned as `Decimal(10000)` | unverifiable `missing_or_invalid_amount` (F-03) | **no** |
| 15 | 10000 | 11000 | 10 | `10`, unit `ratio` value `0.1` | unverifiable `unsupported_unit` | partially (`unit: ratio`) |

Rows 11–14 are the counterexamples this review asks the team to decide on.

---

## 4. Proposed tests (paste-ready, follows the existing parametrization style)

```python
@pytest.mark.parametrize(
    "previous,current,claimed,status",
    [
        # F-01: correctly rounded answers on non-terminating rates must not be false failures
        (3, 4, "33.33", "passed"),
        (3, 4, "33.3", "passed"),      # fails today under a 0.01pp absolute tolerance
        (7, 9, "28.6", "passed"),      # fails today
        (11000, 9000, "-18.2", "passed"),  # fails today
    ],
)
def test_rounded_claims_on_recurring_rates(previous, current, claimed, status):
    result = validate_growth(
        "run-1", Claim(evidence_id="e-1", claimed_value=claimed), [evidence(previous, current)]
    )
    assert result.status == status


@pytest.mark.parametrize("amount", [Decimal(10000), 10000.0, True, "10000"])
def test_amount_type_drift_is_not_reported_as_missing_data(amount):
    item = evidence()
    item.rows[0]["amount_cents"] = amount
    result = validate_growth("run-1", Claim(evidence_id="e-1", claimed_value="10"), [item])
    # lossless numeric types should validate; foreign types should be a tool error,
    # never an unverifiable that looks like "the data was missing"
    assert result.status in {"passed", "tool_error"}
```

The first test is expected to be **red until F-01 is decided**; that is the point of filing it now rather than in Sprint 3.

---

## 5. Dispositions to add to the register

| New ID | Type | Severity | Owner / reviewer | Proposed action |
|---|---|---|---|---|
| DEF-01 | Defect (false-failure risk) | P1 | C / D | Decide tolerance (F-01 option B recommended) → ADR + evaluation contract + tests in §4 |
| DEF-02 | Defect (explainability) | P2 | C / B | Surface tolerance and exact expected value in the report (F-02) |
| TD-03 | Debt (silent type drift) | P2 | C / B | Type policy for `amount_cents` + drift test (F-03) |
| DEC-01 | Decision needed | P2 | A / F | Fix metric denominators, incl. broken evidence links (F-04, F-08) |
| LIM-01 | Documented limitation | P1 | A / F | Real-model mode does not execute the model's own SQL (F-05) |
| TD-02 (existing) | Re-label defect + debt | P1 | B / D | Stale `running` reconciliation; ties to completeness acceptance (F-06) |
| DEF-03 | Defect (portability) | P1 | B / D | Windows temp-file lock breaks every run (F-09); verify with `ignore_cleanup_errors=True` and add a Windows regression test |
| PROC-01 | Process gap | P3 | A | Enable Issues / branch protection; add the evaluation contract to the repo (F-07, F-08) |

---

## 6. 中文摘要

这份评审按团队计划里 S1-T03 的范围（Decimal、单位、容差、证据关联、不支持输入）逐行读了 `validation.py`，并用 12 个手算案例复核了判定结果。

**做对的地方**：全程整数分 + Decimal；用交叉相乘避免循环小数在边界上被舍入；异常一律 `tool_error` 且不会外泄异常文本；证据绑定 `run_id`，不能跨运行替换；`test_injected` 与 `agent_generated` 是一等字段。这些都应该保留，并在后续 Sprint 用测试锁住。

**必须团队拍板的问题（F-01，P1）**：容差固定为绝对 0.01 个百分点，导致**任何除不尽的增长率，只要答案保留一位小数就会被判 failed**。我用你们代码里的同一套表达式复现过：3→4（真值 33.3333…%）答 `33.3` → failed；7→9 答 `28.6` → failed；11000→9000 答 `−18.2` → failed。现有 fixture 恰好是 10000→11000（正好 10%），所以测试全绿把这个坑完全遮住了，一进 Sprint 2 换数据集就会变成误报率飙升。它不会造成假通过（方向是安全的），但会直接伤到项目的头号指标。建议在"绝对 0.05pp 或相对 0.5% 取宽者"、"限定 claim 精度"、"按展示精度比较"三个方案里选一个，写进 ADR 与评测契约。

**其余要点**：展示值只有 2 位而判定用全精度，用户无法从报告解释结论（F-02）；驱动一旦返回 Decimal/float，全部案例会静默变成"无法验证"，工具看起来正常但检出能力归零（F-03）；断链算不算进错误检出率的分母没有任何文件写死（F-04）；真实模型模式下 SQL 是 harness 执行的、不是模型执行的，这条限定必须写进文档，否则评估过度声称（F-05）；崩溃后报告永久停在 `running`，与"每个案例必有终态"的验收冲突，建议从纯技术债改判为缺陷+技术债（F-06）；仓库关闭了 Issues、PR 目前 0 评审，且缺少评测契约文件（F-07、F-08）。

另外我在 Windows 上把这套测试真跑了一遍：**26 通过、4 失败**。4 个失败全部来自同一条链——临时 SQLite 文件在 `TemporaryDirectory` 清理时仍被占用（`WinError 32`），异常被 `except` 吞成 `query_failed`，于是每次运行都在"证据已经抓到"之后被判工具错误。Linux 上看不到，所以那 30 个绿灯没暴露它。把清理改成 `ignore_cleanup_errors=True` 后本地 30/30 全绿（F-09）。

第 4 节给了可直接粘贴的测试（其中 F-01 那组在决定之前应该是红的），第 5 节是需要并入登记册的新条目。**以上每条都需要你本人复核后再署名提交。**
