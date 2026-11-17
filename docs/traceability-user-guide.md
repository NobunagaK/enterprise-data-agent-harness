# Traceability user guide

Trace a validation result to its claim, evidence, SQL and observable execution
steps. The supported tasks are growth and total sales on fixed `sales-v1` data;
this does not validate arbitrary chat answers.

## Page workflow

1. Follow README, run `uv run analytics-agent bootstrap`, and start the application.
2. Expand **销售证据验证 · Sprint 2** in the chat page, select a rule and source,
   then choose **运行验证**.
3. Expand **查看 SQL、证据与执行步骤** to inspect the run ID, status, time,
   duration and safe error codes. Expand **查看对应 SQL 与证据** under the query
   to inspect SQL, returned data, dataset version and claim references.
4. After a batch, choose **查看 <案例编号>** to open its single-run report.

| Fixed claim | Expected result |
|---|---|
| Growth `10` / `18.7` | Passed / failed; inclusive 0.01 percentage-point tolerance |
| Total `11000` / `11001` | Passed / failed; integer CNY cents, zero tolerance |
| Total `11000.1` | Unverifiable; fractional cents are not rounded |

Fixed claims need no model. For a live model, configure an OpenAI-compatible
provider in Settings. The local observation below used `https://api.deepseek.com`
and `deepseek-flash`; keep credentials in local configuration, out of reports,
screenshots and PRs.

## Follow the evidence

Check result/rule version → `Claim.evidence_id` → unique `Evidence.id` → same
`Evidence.run_id = Run.id` → `Evidence.step_id` → unique completed query → SQL,
rows and dataset version. Check source, model and case ID too. `completed` means
execution ended; only `passed` means the claim passed. A failed business claim
may still have a valid trace. Unknown usage/duration remains unknown; missing,
ambiguous or foreign references cannot establish a link.

**Unpublished local observation, not repository-reproducible acceptance:** on
2026-11-17 the original developer's runner called `deepseek-flash`; growth `10%`
and total `11000` cents passed, each with 3 model calls, 1 SQL evidence record and
8 steps, passing the offline structural check. Growth rows were 10000 cents in
2024 and 11000 in 2025, yielding `(11000-10000)/10000×100%=10%`. Original reports
remain on that development machine and are not published. This does not establish
browser or database-persistence acceptance and was not repeated for the fixes.

## Export and inspect

With the application running, open PowerShell at the repository root:

```powershell
$runId = Read-Host 'Enter the complete run ID shown in the page'
$report = Invoke-RestMethod -Uri "http://localhost:8100/api/harness/runs/$runId"
$report | ConvertTo-Json -Depth 100 | Set-Content -Encoding utf8 run.json
uv run python scripts/audit_harness_reports.py run.json --output audit.json
$LASTEXITCODE
```

Supply multiple paths for multiple single-run objects; do not supply an array or
batch JSON. Output cannot overwrite an input, including aliases of the same file.

- Exit `0`: unique, terminal reports passed structural checks.
- Exit `1`: inspect `input_errors`, `duplicate_run_ids` and `runs[].issues`.
- Exit `2`: invalid arguments, file-identity check or output-write failure;
  check output directory and permissions. Input-read failures use exit `1`.

Every supplied run, step and evidence record must retain its nonblank string ID,
and the run must retain its original `started_at`. Missing identities/start data
are input errors; importing never supplies new IDs or the current time. All
provided timestamps need timezones; when both endpoints exist, finish cannot
precede start. Missing legacy/skipped measurements stay optional.

`groups` separates fixed/model claims. `evidence_links` and `claim_links` expose
their valid/total counts; 0/0 is never converted to 100%.

## Troubleshooting and limits

- Reference findings: inspect run/step/evidence IDs; preserve the original report.
- `naive_run_timestamp` / `naive_step_timestamp`: a supplied endpoint has no timezone.
  `reversed_run_timestamps` / `reversed_step_timestamps`: finish precedes start.
- `model_configuration_error`: check local configuration. For `model_error` or
  `query_failed`, inspect the failed step without publishing raw credential-bearing errors.
- History failures: check backend, database and bootstrap. Normal history lists at
  most 20 runs; use all run IDs from batch outcomes for a complete batch.
- SQL and aggregate rows are saved, not the complete temporary source database.
  Missing model/tool parent links do not establish a complete causal graph.
- Offline inspection does not replace numerical validation, planned-case coverage,
  persistence, full Windows UI or live-model failure acceptance.

See [trace acceptance](testing/sprint3-trace-acceptance.md) and the scoped
[trace performance record](testing/sprint2-trace-performance.md).

---

# 中文：可追溯模块使用指南

本模块用于从验证结果追溯声明、引用证据、SQL 及执行步骤。支持固定 `sales-v1` 数据的增长率和销售总额验证，不验证普通聊天中的任意答案。

## 页面操作

1. 按仓库 README 安装依赖，执行 `uv run analytics-agent bootstrap` 后启动应用。
2. 在聊天页展开 **销售证据验证 · Sprint 2**，选择规则和声明来源，点击 **运行验证**。
3. 展开结果卡片的 **查看 SQL、证据与执行步骤**，查看运行 ID、步骤状态、时间、耗时及错误码。
4. 在查询步骤下展开 **查看对应 SQL 与证据**，核对 SQL、返回数据、数据版本和声明引用标记。
5. 批次运行后点击 **查看 <案例编号>**，可进入对应单次报告。

| 固定测试声明 | 预期结果 |
|---|---|
| 增长率 `10` / `18.7` | 通过 / 失败；容差 0.01 个百分点 |
| 总额 `11000` / `11001` | 通过 / 失败；单位为人民币分，零容差 |
| 总额 `11000.1` | 无法验证，不自动舍入 |

固定测试声明无需模型。真实模型需在 Settings 配置 OpenAI 兼容服务：Base URL 为 `https://api.deepseek.com`，模型为 `deepseek-flash`，凭据仅在本机配置，不加入文档、截图或 PR。

## 如何追溯

```text
验证结果及规则版本
  → Claim.evidence_id → 唯一的 Evidence.id
  → Evidence.run_id = Run.id（同次运行）
  → Evidence.step_id → 唯一且已完成的 query 步骤
  → SQL、返回数据和数据版本 → 独立复核计算
```

同时检查来源、模型和案例编号。`completed` 表示执行结束，`passed` 才表示声明通过。业务声明失败的报告仍可以具有完整有效的追溯链。缺失耗时和 Token 保持未知，不补零；引用缺失、歧义或跨运行时不能确认关联。

**未发布的本地观察（非仓库可复现的验收证据）**：2026-11-17 本地通过现有 runner 实际调用 `deepseek-flash`：增长率声明 `10%`、总额声明 `11000` 分均通过；每例包含 3 次模型调用、1 份 SQL 证据，共 8 个步骤，离线结构检查通过。增长率证据为 2024 年 10000 分、2025 年 11000 分，可复核 `(11000-10000)/10000×100%=10%`。原始报告保留在开发机器，未随仓库发布；此记录不代表浏览器或数据库持久化验收。

## 导出与离线检查

应用运行时，在仓库根目录打开 PowerShell：

```powershell
$runId = Read-Host '输入页面中的完整运行 ID'
$report = Invoke-RestMethod -Uri "http://localhost:8100/api/harness/runs/$runId"
$report | ConvertTo-Json -Depth 100 | Set-Content -Encoding utf8 run.json
uv run python scripts/audit_harness_reports.py run.json --output audit.json
$LASTEXITCODE
```

多个报告各存为一个 JSON 对象文件后，可显式传入多个路径。不要传报告数组或批次 JSON，输出不能覆盖输入。脚本只读源报告。

运行及每条步骤、证据必须保留原有非空白字符串 ID，运行必须保留原始 `started_at`。
缺失身份或运行开始时间记入 `input_errors`，不在导入时生成新编号或当前时间。
已提供时间均须带时区，两端都有时结束不得早于开始；旧版/跳过步骤允许缺少的测量仍保持可选。

- 退出码 `0`：所有报告有效、无重复运行、已结束且通过结构检查。
- 退出码 `1`：无效输入、重复运行、未结束或结构问题；查看 `input_errors`、`duplicate_run_ids` 和 `runs[].issues`。
- 退出码 `2`：命令参数错误、文件身份检查失败或输出写入失败；检查输出目录和权限。输入读取失败计入退出码 `1` 的 `input_errors`。

`groups` 按固定声明和模型声明分别汇总；`evidence_links` 为有效证据数/证据总数，`claim_links` 为有效声明引用数/含声明报告数。零分母保留 0/0，不算作 100%。

## 常见问题与边界

- `foreign_run_evidence`、`invalid_query_reference`、`invalid_claim_reference`：核对运行、步骤和证据编号；保留原报告排查，不修改源报告使检查通过。
- `naive_run_timestamp`、`naive_step_timestamp`：已提供的时间缺少时区；`reversed_run_timestamps`、`reversed_step_timestamps`：结束早于开始。
- `model_configuration_error`：检查本机配置；`model_error`、`query_failed`：定位失败步骤，不公开含凭据的原始异常。
- 历史读取失败：检查后端、数据库及 bootstrap。普通历史列表最多 20 条，完整批次应按 outcomes 中的运行编号核对。
- 当前保存 SQL 与聚合结果，不归档临时数据库全部原始明细；模型与工具事件未必有显式父子关系，不据此推断完整调用因果链。
- 离线检查不替代数值验证、缺失计划案例检查、持久化验收或完整 Windows/真实模型异常验收。

详细验收口径见 [S3 轨迹验收说明](testing/sprint3-trace-acceptance.md)，性能范围见 [S2 轨迹性能说明](testing/sprint2-trace-performance.md)。
