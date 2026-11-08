# Sprint 2 integration plan

Status: scoped planning clarification for PR #14 peer review. This document
records the F2/F4 dependency order and session isolation requirements; it is not
a complete Sprint 2 backlog or evidence of completed feature acceptance.

## 1. Ownership and delivery order

| Owner | Increment | Dependency and acceptance boundary |
|---|---|---|
| Zefeng Chen | Shared contracts and F2 numerical verification | Establish the shared baseline; then implement and test `sales_total` and extend `RunRequest` to a union discriminated by `rule_id`, with rule-specific parameters and units. Preserve existing growth requests and legacy report reads. Haoyu and Zikai review shared-field changes before integration. |
| Zikai He | F4 batch evaluation | The first increment runs only `growth_rate` cases against the current contract. After the F2 extension is reviewed and integrated, add mixed-rule cases and regression tests. Batch orchestration calls the shared service and counts validation outcomes without duplicating formulas. |
| Haoyu Shen | F3 execution traces and evidence display | Develop against the shared report fields; review event/error attribution and the F2 contract extension. Trace work can proceed alongside the first growth-only batch increment. |

Delivery sequence: shared baseline → growth-only F4 increment; F2 rule/contract
extension → mixed-rule F4 increment. Growth-only delivery is an intermediate
milestone and does not satisfy mixed-rule acceptance. Mixing rules must preserve
the distinction between `passed`, `failed`, `unverifiable` and `tool_error`, and
between test-injected and actual model claims.

## 2. Session ownership and required regression evidence

The [shared execution contract](design/sprint2-shared-contracts.md) requires one
dedicated `AsyncSession` per case, even for sequential execution. `run_case`
commits its initial and final snapshots; the batch caller creates and closes the
session on every path. Batch metadata writes use a separate session. Release any
conversation-preflight session before starting case execution.

F4 must demonstrate with regression tests that:

- A middle case failing or timing out after its initial save does not prevent
  earlier committed reports from being read.
- A subsequent case completes and persists using its own fresh session.
- Final-save failure is not presented as a successfully persisted final report.

Cancellation cleanup and hard worker time limits require separate implementation
and evidence; a per-case session or `asyncio.wait_for` alone does not prove them.

## 3. Review and completion

Each author requests substantive review from the other two developers. Reviewers
check the final commit and submit their own approval only when satisfied; a
comment or green CI is not a human approval. Record actual test evidence on the
corresponding feature PR. This documentation change adds no runtime behavior,
does not mark F2/F3/F4 Done, and does not establish real-model acceptance.

---

# 中文版本：Sprint 2 接入计划

状态：针对 PR #14 的局部计划澄清，待同伴评审。本文件记录功能②/④的依赖顺序及 session 隔离要求，
不是完整 Sprint 2 待办清单，也不是功能验收已完成的证据。

## 1. 分工与交付顺序

- Zefeng Chen：共同接口与功能②数值验证。先建立共同基线，再实现并测试 `sales_total`，
  将 `RunRequest` 扩展为以 `rule_id` 区分的联合类型，分别约束参数和单位。
  保持原增长率请求和旧报告兼容；共同字段变更由 Haoyu、Zikai 两人评审后集成。
- Zikai He：功能④批量评估。第一版仅运行 `growth_rate` 案例；功能②扩展通过评审并集成后，
  再加入混合规则案例及回归测试。批次调用共同服务、统计验证结果，不复制公式。
- Haoyu Shen：功能③轨迹采集与证据展示。使用共同报告字段，评审事件/错误归因及功能②契约变更；
  可与第一版增长率批次并行开发。

交付顺序：共同基线 → 功能④增长率批次；功能②规则/契约扩展 → 功能④混合规则批次。
增长率批次只是阶段性交付，不满足混合规则验收。
混合规则仍须区分 passed、failed、unverifiable、tool_error，以及测试注入声明和真实模型声明。

## 2. Session 归属与必需回归证据

[共同执行契约](design/sprint2-shared-contracts.md) 要求每个案例独立使用一个 `AsyncSession`，
串行执行也不例外。`run_case` 提交初态和终态快照；批次调用者在所有路径负责创建和关闭 session。
批次元数据写入使用其他 session；执行案例前先释放会话存在性预检查所用的 session。

功能④必须通过回归测试证明：

- 中间案例在初态保存后失败或超时，不影响读取前序已提交报告。
- 后续案例使用自己的新 session，仍能完成并持久化。
- 终态保存失败不会被展示为已成功保存终态。

取消清理和工作线程硬超时仍需单独实现并提供证据；独立 session 或 `asyncio.wait_for` 本身不能证明这些能力。

## 3. 评审与完成标准

每位作者请另外两位开发者进行实质评审。评审者检查最终提交，确认后自行正式批准；
普通评论和绿色 CI 都不等于人工批准。实际测试证据记录在对应功能 PR 中。
本次文档变更不增加运行行为，不将功能②/③/④标为 Done，也不代表真实模型已验收。
