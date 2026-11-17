# Sprint 2 delivery and handoff

Recorded on **2026-11-17 (Asia/Shanghai)**. Code baseline:
[`main@45216b1`](https://github.com/NobunagaK/enterprise-data-agent-harness/commit/45216b1cdbb3d5f108ba39f4a0dbf4873cce8b3b).
All three prototype features are integrated and fixed-case acceptance passed.
Final native-Windows application, live-provider and course demonstration
acceptance remain separate. This updates the earlier partial integration plan;
the original decisions remain in the designs and Git history.

## Delivered scope

Fixed sales cases → actual SQL → captured evidence → Decimal verification →
persisted reports → the existing React UI. This does not validate arbitrary chat
answers. Amounts are integer CNY cents; growth tolerance is **0.01 percentage
points, inclusive**; totals use exact cent equality. `passed`, `failed`,
`unverifiable` and `tool_error` remain distinct, as do `test_injected` and
`agent_generated` claims.

| Feature / original lead | Delivered increment | Evidence |
|---|---|---|
| F2 / Zefeng | Two rules, rule-specific contracts/units, evidence association, exact Decimal boundary | [F2 design](design/sprint2-verification-f2.md), #23 |
| F3 / Haoyu | Observable steps, SQL/evidence links, safe errors, timing/known usage, React traces, scoped overhead measurement | [trace](design/sprint2-trace-f3.md), [UI](design/sprint2-trace-ui-f3.md), [measurement](testing/sprint2-trace-performance.md), #17/#18/#28 |
| F4 / Zikai | Versioned/mixed case sets, isolated sessions, summaries/history, budgets and interruption states | [mixed cases](design/sprint2-mixed-case-sets.md), [budgets](design/sprint2-batch-budgets.md), #15/#16/#25/#26/#27 |

Original feature ownership is not an assertion that each person wrote every
integration fix. Actual authors/reviews remain on GitHub; no hours or meetings
are inferred. Deploy one worker and one replica per database; support 1–20
bundled cases, default case/batch budgets 60/300 seconds, maxima 120/600 seconds.
Cancellation waits for owned workers and actual session closure; cleanup may
exceed the budget. Hard thread killing, distributed ownership, arbitrary SQL and
enterprise expansion are outside this prototype scope.

## Completion evidence and documents

- [User stories, acceptance criteria and NFRs](design/sprint2-requirements-acceptance.md)
- [Integrated test/runtime evidence](testing/sprint2-integrated-acceptance.md)
- [Actual reviews, code quality and retrospective observations](process/sprint2-review-quality-retrospective.md)
- [Debt and risk register](process/sprint2-debt-risk-register.md)
- [Shared contracts](design/sprint2-shared-contracts.md)

Fresh cloud results: **594 backend/MCP**, **78 frontend**, **44 browser** tests
passed, plus build/Ruff/mypy. Final main has **9 successful CI jobs**, including
**231 Windows Harness** and **9 Windows benchmark** tests. Actual HTTP execution
generated 18 reports and a separate expired batch; all 18 reports and 3 batches
were unchanged after a server-process restart. Older per-feature counts remain
historical evidence, not results from this run.

## Sprint 3 deliverables, in order

| Task | Reviewable completion evidence |
|---|---|
| Review latest #30 against final main | Current-head review/CI, source-export protection and documented structural-check limits; #29 was replaced by #30 |
| Run the full application on native Windows | OS/Python/Node/commit, installation/bootstrap/start, both rules, mixed batch, SQL/evidence, history after restart, logs/screenshots |
| Verify a configured real provider | Sanitized actual application/API reports, model/source identity, SQL/evidence/result links, persisted/reloaded reports and observed failure handling; address #12 |
| Reconcile final acceptance matrix | Independent expected results, four categories, failure isolation, budget/cancellation limits, legacy reads, separate fixed/model populations; label fault injection |
| Finish delivery documentation | Evidence for #11/#12, remaining debt, reproducible setup and exact demonstration commit |
| Record the video after acceptance | Demonstrate the accepted Windows version and matching reports; no new enterprise features required |

A newcomer can take a bounded Windows reproduction or evidence/document review.
Repository merge authority depends on GitHub permissions and branch rules, not
the original feature allocation. Team/course membership is agreed separately;
new access does not establish earlier contributions. Missing historical standup,
effort or burndown records are not fabricated.

---

# 中文：Sprint 2 交付与交接

记录日期：**2026-11-17（北京时间）**，基线 `main@45216b1`。三个原型功能已集成，固定案例验收通过；
完整 Windows 应用、真实模型和课程演示验收仍单独完成。本文件更新早期局部计划，原决定保留在设计和 Git 历史。

范围为固定销售案例、实际 SQL、证据、Decimal 验证、报告持久化和原 React 页面，不验证普通聊天任意答案。
金额保存人民币整数分；增长率容差 0.01 个百分点、包含边界；总额精确相等。四类结果及测试/模型来源始终分开。

功能②原负责人 Zefeng：两条规则、接口/单位、证据关联、精确边界。功能③原负责人 Haoyu：可观察步骤、
SQL/证据、状态/时间/已知用量、React 轨迹和限定范围的性能测量。功能④原负责人 Zikai：版本化混合案例、
独立 session、汇总/历史、预算和中断状态。此分工不代表每项后续修补均由本人独自完成，实际作者/评审以 GitHub 为准。

每数据库单 worker/单副本，支持 1–20 例，默认单例/整批 60/300 秒，上限 120/600 秒。
等待所拥有的线程和实际连接关闭后才保存终态；协作取消的清理可超预算，不扩展硬杀线程、分布式归属或任意 SQL。

上方链接提供用户故事/NFR、验收、评审/代码质量/回顾、技术债和共同接口。
本次后端/MCP **594 项**、前端 **78 项**、浏览器 **44 项**及构建/静态检查通过；最终 main **9 个 CI 作业通过**，
其中 Windows Harness **231 项**、基准 **9 项**。实际 HTTP 生成的 18 份报告和 3 个批次在服务重启后内容完全一致。

Sprint 3 顺序：①评审 #30 最新版本；②原生 Windows 完整安装、迁移、启动、UI 和重启复现；
③真实模型经应用/API 调用及持久化重读，补 #12 证据；④独立核对案例预期、错误隔离、预算/取消、旧报告与来源；
⑤补 #11/#12、技术债和交付说明；⑥验收后录制匹配提交的 Windows 视频。

新成员可承担有具体交付物的 Windows 复现或证据/文档检查。合并权由 GitHub 权限和分支规则决定，
团队/课程成员资格另行确认。新增权限不等于过去参与开发，缺失的站会、工时和燃尽数据不补造。
