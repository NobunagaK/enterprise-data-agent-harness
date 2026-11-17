# 可追溯模块使用指南

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

- 退出码 `0`：所有报告有效、无重复运行、已结束且通过结构检查。
- 退出码 `1`：无效输入、重复运行、未结束或结构问题；查看 `input_errors`、`duplicate_run_ids` 和 `runs[].issues`。
- 退出码 `2`：命令参数错误、文件身份检查失败或输出写入失败；检查输出目录和权限。输入读取失败计入退出码 `1` 的 `input_errors`。

`groups` 按固定声明和模型声明分别汇总；`evidence_links` 为有效证据数/证据总数，`claim_links` 为有效声明引用数/含声明报告数。零分母保留 0/0，不算作 100%。

## 常见问题与边界

- `foreign_run_evidence`、`invalid_query_reference`、`invalid_claim_reference`：核对运行、步骤和证据编号；保留原报告排查，不修改源报告使检查通过。
- `model_configuration_error`：检查本机配置；`model_error`、`query_failed`：定位失败步骤，不公开含凭据的原始异常。
- 历史读取失败：检查后端、数据库及 bootstrap。普通历史列表最多 20 条，完整批次应按 outcomes 中的运行编号核对。
- 当前保存 SQL 与聚合结果，不归档临时数据库全部原始明细；模型与工具事件未必有显式父子关系，不据此推断完整调用因果链。
- 离线检查不替代数值验证、缺失计划案例检查、持久化验收或完整 Windows/真实模型异常验收。

详细验收口径见 [S3 轨迹验收说明](testing/sprint3-trace-acceptance.md)，性能范围见 [S2 轨迹性能说明](testing/sprint2-trace-performance.md)。
