# PR #3 issue backfill drafts

Prepared 2026-11-03 (Asia/Shanghai), after merge. **These are drafts, not GitHub Issues.** Creation returned HTTP 410 because Issues is disabled; enabling via CLI returned Forbidden. No issue numbers, assignments or closure events have been invented. Enable Settings → General → Features → Issues, create these records, then close only entries with completed dispositions.

Source: [Haoyu Shen’s actual review](https://github.com/NobunagaK/enterprise-data-agent-harness/pull/3#issuecomment-6581142937), ff43916 vs aee4f2c. Original Windows measurements belong to that review, not this backfill. Evidence: [acceptance](../sprint1-acceptance.md), [contract](../design/sprint1-evaluation-contract.md), commits 6e63f43, 95b7abe and 341515d.

## [PR #3 §1] Close SQLite fixture connections

Intended state: Closed after creation.

6e63f43 explicitly closes the fixture connection and removes cleanup suppression. Linux success/error cleanup tests passed; final Windows verification remains separate.

## [PR #3 §2] Protect fixture cleanup with regression tests

Intended state: Closed after creation.

6e63f43 adds successful/failing query tests asserting closed connections and no temporary artifacts. Tests ran on Linux.

## [PR #3 §3] Restore Ruff formatting gate

Intended state: Closed after creation.

6e63f43 fixes formatting; final acceptance records 95 files passing format check.

## [PR #3 §4] Handle nonfinite Decimal evidence without raising

Intended state: Closed after creation.

6e63f43 checks finiteness before conversion; Infinity, NaN and signaling NaN return tool_error/evidence_type_drift.

## [PR #3 §5] Cover bool and fractional float evidence; document classification

Intended state: Closed after creation.

Tests cover bool and fractional floats. The evaluation contract documents bool as tool_error; growth_rate-v2 records changed evidence semantics.

## [PR #3 §6] Define numpy scalar support boundary

Intended state: Closed after creation.

The evaluation contract limits supported input to Python scalars; numpy is outside Sprint 1. This closes the scope question, not a claim of numpy support.

## [PR #3 §7] Link current implementation and portable reproduction instructions

Intended state: Closed after creation.

341515d adds acceptance evidence and portable uv run python -m pytest commands; earlier document statements are labeled historical.

## [PR #3 §2 / follow-up] Verify final cleanup revision on Windows

Intended state: Open.

Run Harness tests on merged main on Windows. Record OS/Python/commit and verify no fixture directories remain after successful and failing queries. Windows CI was added but no passing result has been established. Suggested owners D/F; no assignment acceptance is asserted.

## [PR #3 §Out of scope] Verify remote-provider workflow and independent acceptance

Intended state: Open.

F-05: first model tool invocation executes fixed SQL; arbitrary SQL is excluded. Configure provider and budget, then preserve actual remote results; obtain F independent acceptance. No credentials or human acceptance are currently evidenced. Suggested A/B/D/F coordination.

## Other referenced concerns

F-01 retains the owner-confirmed inclusive 0.01pp tolerance (counterexamples protected); F-06 has guarded 300-second lazy reconciliation. CI now also targets sprint1/harness and includes Windows Harness tests. These are documented dispositions, not new reviewer approvals. Enabling Issues remains blocked by repository settings/access in this session. Historical commit titles are preserved; follow-up commits correct the implementation.

---

# 中文：PR #3 Issue 补录草稿

本文件是合并后补录草稿，尚未创建任何 GitHub Issue。创建返回 410（Issues 未启用），CLI 启用请求返回 Forbidden。请先启用仓库 Issues，再逐条创建，已完成项核对证据后关闭；不倒填时间，不编造编号、指派或完成事件。原 Windows 数据属于 Haoyu Shen 对旧提交的评审。

- 原评审 1：显式关闭连接并取消异常抑制，Linux 测试通过，Windows 复测另列。 预期状态：创建后关闭。

- 原评审 2：已补成功/异常路径的连接关闭与无残留测试。 预期状态：创建后关闭。

- 原评审 3：格式已修复，最终 95 文件格式检查通过。 预期状态：创建后关闭。

- 原评审 4：非有限数值在转换前检查，返回工具错误。 预期状态：创建后关闭。

- 原评审 5：已补 bool/浮点分金额测试，契约和规则版本记录分类变化。 预期状态：创建后关闭。

- 原评审 6：契约明确 Python 标量边界，不声称支持 numpy。 预期状态：创建后关闭。

- 原评审 7：验收文档补当前版本与跨平台命令，旧记录标明历史快照。 预期状态：创建后关闭。

- 原评审 2 / follow-up：待 D/F 在 Windows 对最终版本复测并记录无残留证据，未冒充已完成。 预期状态：保持开放。

- 原评审 Out of scope：模型范围已澄清，但真实调用和独立验收仍待完成。 预期状态：保持开放。

其余引用项：F-01 按用户约定保留容差；F-06 已补过期协调；CI 已扩展分支与 Windows 测试，但未声称远程执行通过。原始提交标题不重写，修复通过后续提交说明。
