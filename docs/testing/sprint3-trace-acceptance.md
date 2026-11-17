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
invalid command arguments, failed file-identity checks or output-write failures.
Output must not be an input file. Source exports are
never rewritten. Invalid input payloads, SQL, answers and raw exceptions are not
copied into the summary; identifiers remain available for investigation.

Import requires an existing, nonblank string `id` on the run and on every supplied
step/evidence record, plus the run's original `started_at`. Missing or invalid
identities and missing run start metadata are `input_errors`; the auditor never
generates replacement IDs or an import-time start. Schema/rule defaults and
absent legacy step measurements retain their existing compatibility behavior.

## Frozen scope and denominators

| Check | Acceptance |
|---|---|
| Evidence ownership | Same run, unique evidence ID, unique completed query step |
| Claim reference | Exactly one evidence record, same run and valid query link |
| Parent reference | Unique existing parent, no self-reference or ancestry cycle |
| Terminal reports | Result and finish timestamp present, no running steps |
| Completed execution | Completed validation step, result other than tool_error |
| Error execution | tool_error result; numerical failure alone is not an execution error |
| Measurements | Schema 2 completed/error steps have timestamps and duration; every supplied run/step timestamp is timezone aware, with finish >= start whenever both exist |
| Rule unit | growth_rate uses percent; sales_total uses CNY_cent |

Source populations (`test_injected`, `agent_generated`) are always separate.
Evidence-link numerator is valid evidence records and denominator is all evidence
records in that source population. Claim-link numerator is valid claim references
and denominator is reports containing a claim. Zero denominators remain explicit
0/0 counts, never an invented 100%. Structural report count includes running
reports; terminal count is separate. Duplicate run IDs invalidate the command;
group counts remain parsed-input counts and must not be used as accepted metrics.

Legacy schema 1 reports do not require retroactively invented step measurements.
Skipped steps may also omit measurements. A single supplied endpoint still needs
a timezone; different UTC offsets are compared as instants and equal endpoints
are allowed. Findings use `naive_run_timestamp`, `reversed_run_timestamps`,
`naive_step_timestamp` and `reversed_step_timestamps` without rewriting the source.
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

## Initial local validation record (2026-11-17; historical)

Native Windows / Python 3.12, baseline `origin/main@536877a`:
234 tests passed across audit, core Harness, mixed cases, trace, contracts,
verification, batch lifecycle and trace benchmark modules (17 new audit tests).
Ruff lint/format, mypy for the two new source files and `git diff --check` passed.
The local run reused the existing repository Python environment with this
checkout's `backend/src` on PYTHONPATH. CI installs from the lockfile separately.
Existing Pydantic schema-shadowing and Alembic configuration warnings remained.

## Identity/time fix validation (2026-11-17)

On Linux / Python 3.12.14, the added regressions first produced **17 failures,
31 passes and 1 skip** on the previous implementation. After the fix, the same
audit suite produced **48 passes and 1 skip**. The skip requires a case-insensitive
filesystem. The 27 added cases cover missing/blank identities, duplicate error
exports, missing run start metadata, reversed/naive times, partial legacy/skipped
measurements, UTC offsets and equal endpoints; CLI inputs remain byte-for-byte
unchanged, including UTF-8 BOM exports. This does not rerun the historical native
Windows observation or establish live-provider acceptance.

Related Harness regression suites passed **256 tests with 1 skip**, including
the audit suite. Ruff lint/format passed (115 files) and mypy passed (80 source
files, including the CLI). All eight original review probes now produce the
expected exit codes. Re-inspecting the 18 retained #31 exports accepted all 18,
with unchanged business outcomes; this recheck did not rerun their original
HTTP/restart experiment. Latest-main integration remains covered by PR CI.

---

# 中文：Sprint 3 轨迹与证据验收

本增量在 Sprint 2 轨迹、页面和规则分派之上，只读检查
`GET /api/harness/runs/{id}` 的单份 JSON 导出，不新增报告契约或数值验证器。
每个文件保存一个报告，使用英文部分的 PowerShell 命令安装依赖、执行检查和测试。

- 退出码 `0`：所有输入成功解析、运行编号唯一、已结束且通过结构检查。
- 退出码 `1`：无效输入、重复运行、未结束或结构问题；保留具体发现。
- 退出码 `2`：参数、文件身份检查或输出写入错误。输出不得覆盖输入。

导入要求运行及每条步骤/证据都有原有的非空白字符串 `id`，运行也必须提供原始
`started_at`；缺失或无效时记入 `input_errors`，不生成新编号或导入时刻。
不改写原报告，不把 SQL、答案、无效输入内容或原始异常复制到审计摘要。

验收检查：同运行且唯一的证据、唯一已完成查询、声明引用、父节点唯一性及无环；
终态应有结果和结束时间，不能留下 running 步骤。completed 应有完成的验证且不能是
tool_error；error 应是 tool_error。增长率使用 percent，总额使用 CNY_cent。

所有已提供的运行/步骤时间均须有时区；两端都有时结束不得早于开始。
只有一个端点也检查时区，不同时区按实际时刻比较，允许两端相等。
schema 2 的 completed/error 步骤必须有时间和耗时；schema 1 和 skipped 步骤仍可缺少测量。
问题码为 `naive_run_timestamp`、`reversed_run_timestamps`、`naive_step_timestamp`、
`reversed_step_timestamps`。未知 Token/耗时不补零，非法计数、负耗时和不支持的版本由模型校验拒绝。

固定声明与模型声明分组统计。证据关联为有效证据数/证据总数，声明关联为有效引用数/含声明报告数；
零分母保持 0/0。结构有效数与终态数分开；重复运行使命令失败，分组仍为已解析输入的原始计数，
不能当作验收通过指标。

自动测试使用实际本地 SQL 和故意损坏的导出，覆盖两条规则、引用错误、循环、未结束步骤、单位、
输入/输出保护及身份/时间边界。结构检查不重算数值、不证明错误归因，不从缺少计划清单的文件推断
遗漏案例，也不证明持久化或完整轨迹百分比。故意损坏业务证据的无法验证案例可能产生预期结构问题，
应对照固定案例清单保留并解释。性能沿用 #28 的限定离线范围。

历史 Windows 记录为原始增量的 234 项通过（含当时 17 项审计测试），不是本次重跑结果。
本次 Linux/Python 3.12.14 的同一套回归在修复前为 17 失败/31 通过/1 跳过，修复后为
48 通过/1 跳过；新增 27 项覆盖身份、时间及兼容场景，原文件字节保持不变。
相关 Harness 回归合计 256 通过/1 跳过（含审计）；Ruff 的 115 个文件、mypy 的 80 个源码文件通过。
原评审 8 个复现样例退出码均正确，重新检查 #31 保存的 18 份导出全部通过且业务结果不变；
此检查不冒称重做原 HTTP/重启实验。最新 main 的集成检查由 PR CI 执行。
完整 Windows UI、真实模型 API 导出/持久化和独立成员复现仍需实际验收，不由本工具或历史观察替代。
