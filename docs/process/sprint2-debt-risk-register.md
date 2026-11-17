# Sprint 2 debt and risk register

Snapshot: 2026-11-17, `main@45216b1`. Delivered fixes, accepted prototype limits
and missing acceptance evidence remain separate. Optional review suggestions are
not relabelled as blocking defects; enterprise expansion is not added to scope.

| Item | Status / evidence | Next action or accepted boundary |
|---|---|---|
| [#19 budgets and cleanup](https://github.com/NobunagaK/enterprise-data-agent-harness/issues/19) | Closed with reviewed #27 and final-main evidence: defaults/caps, synchronous 1–20-case scope, owned close, four real-pool regressions, preserved prefix/honest tail | [Acceptance record](../testing/sprint2-integrated-acceptance.md); closure is within this prototype scope, with no hard-kill guarantee |
| #11 Windows cleanup evidence | Final main Windows Harness 231 and benchmark 9 passed; older Issue text has not been reconciled | Attach exact job/commit/environment and cleanup evidence before closing the original issue; full native Windows UI remains an additional Sprint 3 task |
| #12 real provider / independent acceptance | Open; model doubles covered, #30 records an unpublished local provider observation | Supply sanitized application/API exports and persistence/replay evidence; record actual independent reproduction, not just source labels |
| Process-local ownership / soft deadlines | Accepted, explicit in README/budget design | One worker/replica per database; cleanup/save may exceed budget, closing a tab does not guarantee cancellation; no queue/distributed owner/hard kill |
| #27 optional P3 | Close error may replace active exception; final-write cancellation can conservatively mark a completed batch cancelled; projected outcomes omit expected labels | Keep documented semantics; revisit only for a concrete accepted scenario |
| #26 optional P3 | Corrupt bundled catalog file, future ambiguous labels, extra malformed/collision coverage | Current two sets are validated/tested, history survives catalog failure; revisit on case-set editing/expansion |
| #23 future engine/scope support | Review notes float precision beyond 2^53 and future scope drift; fixed SQLite currently returns INTEGER | Preserve integer-cent/fixed-scope contract; validate new engines before any later expansion |
| #28 measurement limits | Version comparison includes execution-boundary changes; optional raw-unit/revision assertion hardening | Retain caveats/samples; no trace-only end-to-end or live-provider/Windows latency claim |
| Existing frontend warnings | 7 ESLint warnings, 0 errors; large-chunk advisory | Low-priority quality debt, not evidence of a measured performance failure |
| Main protection | GitHub reported main unprotected during closeout | Permissions/PR/status-check rules can be configured separately; no access or rule changes made here |
| Process-record gaps | Actual PR/review trail exists; historical attendance/hours/burndown data not supplied | Preserve real events, do not invent records |

#30 is a separate Sprint 3 acceptance increment; its latest revision needs its
own review and evidence. No tasks are automatically assigned to a newcomer or
the original six-person team; agree concrete deliverables with current members.

---

# 中文：Sprint 2 技术债与风险登记

基线 2026-11-17、`main@45216b1`。区分已修复、接受的原型限制和缺失验收证据；不将可选 P3 改称阻塞缺陷，不增加企业扩展。

- **#19**：经过两人复查的 #27 已解决预算、清理、结果保留和尾部状态；已附最终集成证据，按原型范围关闭，不声称硬终止。
- **#11**：main 的 Windows Harness 231、基准 9 项通过，但旧 Issue 尚未补对应提交/环境/清理证据；完整 Windows UI 另属 Sprint 3。
- **#12**：保持开放；模型替身和未公开报告的本地观察不替代应用/API 导出、持久化重读和实际独立复现。
- **部署边界**：单 worker/单副本、协作取消；清理/保存可超预算，关闭网页不保证取消，无分布式队列和硬终止。
- **#27 可选项**：清理异常诊断、终态写入取消的保守状态、投影预期标签缺失，按具体需求再改。
- **#26 可选项**：损坏文件、未来同形标签和额外目录测试；当前两组已验证，目录失败仍可读取历史。
- **#23 扩展风险**：超大整数浮点和范围漂移；当前固定 SQLite INTEGER/整数分/固定范围不受新引擎假设影响。
- **#28 限制**：保留版本差异、原始单位/样本及离线范围，不泛化为真实模型或 Windows 总耗时。
- **已有警告**：ESLint 7 条、无错误及大包提示是低优先级质量事项，不据此认定性能故障。
- **main 保护**：本次核查未保护，权限和检查规则另行配置，本次未改。
- **过程缺口**：实际 PR/评审保留，缺失的出勤、工时和燃尽数据不补造。

#30 是独立的 Sprint 3 增量，最新版本需另外评审。任务不自动分配给新人或原六人团队，由当前成员确认具体交付物。
