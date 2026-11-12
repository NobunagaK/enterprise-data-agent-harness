# Sprint 2 F3 trace presentation

This completes the frontend review work for Haoyu's PR #18, preserving its
original commits. It integrates the tested backend from #17 (`12856cc`) and
F2 from #23. Target is main; merge dependencies are #23 → #17 → #18. These
prerequisite branches have not been declared merged or independently approved.

## Evidence association

The original result card rendered all SQL evidence twice: once through the
trace's run/step filter and once without that filter. A synthetic regression
also reproduced a foreign-run SQL payload appearing through the unfiltered path.
The result card now delegates all evidence presentation to TracePanel.

- Match `Evidence.run_id` to the containing run and `Evidence.step_id` to a
  unique query step. Present each matching record once beneath that step.
- Exclude other-run evidence payloads and show the excluded count.
- Preserve same-run evidence with missing, ambiguous or non-query step references
  in an explicitly unlinked diagnostic section. Do not silently discard it or
  attach it to a guessed step.
- Mark the claim's unique referenced evidence. Missing or duplicate references
  have explicit warnings; they do not become confirmed associations.
- Display parent step identity only when unique in the same run; otherwise mark
  the missing/ambiguous parent. Keep recorded order rather than inventing timings.

The panel displays status, safe error codes, actual timestamps/durations and
provider token metadata. Unknown measurements remain unknown; reported zeros
remain zero. Total results use CNY cents; growth results use percent/percentage
points. Evidence units are displayed from the record, not blindly relabeled.
Legacy reports remain readable. Test-injected versus model-generated labels
remain visible on the result card.

## Verification

Local Linux results on the integrated implementation:

- 14 dedicated trace-panel/result-card regressions passed. The original rendering
  failed the duplicate-SQL and foreign-run regressions before repair.
- All 76 frontend tests passed; TypeScript/build passed; ESLint had no errors
  and the same 7 pre-existing warnings.
- All 41 browser tests passed. Two new real-SQL scenarios verify both rule types,
  failed claims, claim/evidence/query IDs, timings and persistence after reload.
- The batch browser scenario now opens the failed case's linked trace and SQL.
- A clearly labeled synthetic UI fixture checks configuration-error presentation
  without inventing a provider call or token usage. The backend failure itself
  is tested using local doubles in #17; no live provider call is claimed.
- Backend behavior is inherited unchanged from #17: 191 Harness / 545 full backend
  and MCP tests passed there. Remote checks are reported on each PR's latest head.

No native Windows full-stack or human independent acceptance is claimed.
Remaining hard-worker/whole-batch timeout guarantees stay in issue #19. Complete
remaining Sprint 2 code integration before the final Sprint 2 documentation pass;
record only actual work and prepare the formal video after acceptance.

---

# 中文版本：Sprint 2 功能③轨迹界面

保留 Haoyu #18 原始提交，接入已验证的 #17 后端（`12856cc`）和 #23 功能②。
目标为 main，依赖合并顺序 #23 → #17 → #18；不宣称依赖已合并或其他成员已批准。

已用合成数据复现旧卡片重复展示 SQL、外层无条件展示其他运行证据的问题，现统一由 TracePanel 展示：

- 同时匹配运行编号与唯一查询步骤，正确证据只展示一次。
- 排除其他运行的证据内容并提示数量。
- 同运行但缺失/歧义/错误步骤关联的证据单独标为“仅供排查”，不静默丢弃、不猜测关联。
- 明确标出声明引用；引用缺失或不唯一时提示。父步骤也只在本运行内确认。
- 保留实际步骤顺序、状态、安全错误码、时间及 Token；未知值不补零。
- 总额和增长率分别使用分、百分比/百分点；证据单位来自记录本身，旧报告及来源标识保持兼容。

本地 14 项专用轨迹测试、全部前端 76 项、完整浏览器 41 项通过，构建与类型检查通过；
lint 无错误，保留 7 条原有警告。浏览器实际运行两种规则的失败案例并刷新，核对 SQL、声明、证据及步骤编号；
批次页面也验证了打开失败轨迹。配置失败页面采用明确标注的合成快照，实际后端错误由 #17 的本地替身测试覆盖。
后端代码直接继承 #17，其 Harness 191 项、完整后端与 MCP 545 项通过；各 PR 远程结果以最新提交为准。

不宣称真实模型、Windows 整套实机或人工独立验收已完成。硬超时/整批预算仍由 #19 跟踪；
剩余 Sprint 2 代码完成后，再统一提醒补齐本轮文档，并在演示版本验收后制作正式视频。
