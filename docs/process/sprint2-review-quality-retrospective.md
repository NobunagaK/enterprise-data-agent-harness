# Sprint 2 reviews, quality and retrospective observations

Recorded 2026-11-17, `main@45216b1`; this consolidates actual PR activity and
[fresh integrated checks](../testing/sprint2-integrated-acceptance.md).
It is not a reconstructed meeting or a working-hours/contribution estimate.

## Delivery trace

| PR | Delivered change | Merged commit |
|---|---|---|
| #14 | Shared contracts/service boundary | `ce9ba39` |
| #15 | Initial versioned batch evaluation | `f57e630` |
| #16 | Connection ownership / failed-run references | `67153cd` |
| #22 | Windows timing / Playwright provisioning | `4e82e14` |
| #23 | F2 total rule / exact growth boundary | `0946143` |
| #17 / #18 | F3 collection / UI integration | `7fb043b` / `55cd649` |
| #25 | Source override/preservation tests | `92cfec7` |
| #26 | Mixed case selection | `1cb63c1` |
| #28 | Offline trace measurement | `536877a` |
| #27 | Budgets, interruption, actual close ordering | `45216b1` |

PR numbers refer to [this repository's PRs](https://github.com/NobunagaK/enterprise-data-agent-harness/pulls?q=is%3Apr).
Their actual authors and review limits remain authoritative. Historical test
counts are not added to the current integrated totals.

## Actual closing reviews

| Revision | Zikai (`Ark-athor`) | Haoyu (`shenhyuu`) |
|---|---|---|
| #26 `cbce052` | [Approved](https://github.com/NobunagaK/enterprise-data-agent-harness/pull/26#pullrequestreview-5887676394), 3 Windows mixed tests | [Comment](https://github.com/NobunagaK/enterprise-data-agent-harness/pull/26#pullrequestreview-5894350537), 3 tests, no actionable defect |
| #28 `ade7629` | [Approved](https://github.com/NobunagaK/enterprise-data-agent-harness/pull/28#pullrequestreview-5887676756), 9 Windows benchmark tests | [Comment](https://github.com/NobunagaK/enterprise-data-agent-harness/pull/28#pullrequestreview-5894351661), 9 tests and recomputation of seven summaries |
| #27 `8c46e3e` | [Approved](https://github.com/NobunagaK/enterprise-data-agent-harness/pull/27#pullrequestreview-5935863427), 45 Windows batch/lifecycle tests | [Comment](https://github.com/NobunagaK/enterprise-data-agent-harness/pull/27#pullrequestreview-5936730260), 45 tests, prior P2 fixed, no new actionable defect |

The [earlier #27 P2](https://github.com/NobunagaK/enterprise-data-agent-harness/pull/27#pullrequestreview-5894351066)
showed that waiting for the outer task did not guarantee SQLAlchemy's detached
close had released the connection. The repaired revision owns actual close tasks
and adds four real single-connection regressions. Deployment/default-budget
comments were addressed in README. The owner authorized merging after latest-main
integration checks. Haoyu's Comments are substantive reviews, not `APPROVED`
events; a second approval is not invented.

## Code quality and tradeoffs

| Concern | Concrete evidence | Limit |
|---|---|---|
| Separation / modifiability | Pure Decimal validation, rule registry, shared service, separate batch/storage/UI; second rule reused the execution path | One fixed-rule extension, not a general plugin framework |
| Reduced coupling | Batch uses shared service; expected labels remain evaluation data; common run/step/evidence identities | Shared-contract changes still need integration checks |
| Resource correctness | `_session` owns actual close; `_finish` drains tasks before terminal persistence | Explicit lifecycle complexity; permanently stuck threads cannot be killed |
| Effective tests | Exact boundaries, cross-run evidence, actual SQLite, source overrides and single-connection fault regressions | Counts do not prove coverage percentage or absence of defects |
| Reproducibility | Locked inputs, Windows jobs, prebuilt browser container, exact revisions/tree | CI is not native Windows UI acceptance |
| Static checks | Ruff/mypy/TypeScript/ESLint/build passed | Existing 7 ESLint warnings and large chunks remain debt |
| Measurement | #28 raw samples, paired deltas, exact commits | Version differences include execution-boundary changes; no live-provider latency claim |

## Retrospective observations and actions

1. Own cancellation through actual cleanup. Keep all four close-order regressions;
   the P2 reproduction found a failure the earlier passing suite did not cover.
2. Isolate the intended test failure. #22/follow-ups removed tiny deadlines from
   healthy storage-error scenarios while retaining actual blocked-case expiry;
   do not weaken assertions or silently retry failures.
3. Associate review evidence with the revision. Old approvals did not establish
   review of the new close fix; verify the final tree and keep history separate.
4. Separate implementation from final acceptance. Sprint 3 needs complete Windows
   and persisted real-provider reports before video recording.
5. Finish bounded defects and evidence; do not add distributed scheduling,
   arbitrary SQL or enterprise tenancy.

Historical standup attendance, hours and numerical burndown source data were not
provided for this closeout and are not backfilled. Actual PR/Issue events provide
the development trail. These observations derive from code/tests/reviews, not an
unrecorded retrospective meeting.

---

# 中文：Sprint 2 评审、代码质量与回顾观察

2026-11-17，基线 `main@45216b1`。本文件汇总真实 PR 和集成检查，不补造会议、工时或贡献统计。
上表列出共同接口、批次、连接修复、CI、功能②③、来源隔离、混合案例、测量和预算的实际合并提交。
作者/评审范围以原 PR 为准，历史测试不累计到本次结果。

#26/#28 有 Zikai 正式批准和 Haoyu 实质 Comment；测试分别为 3 项混合案例、9 项基准，
Haoyu 还复算七组统计。#27 旧 P2 指出外层结束不保证实际 close 已归还连接；修复后两人均对
`8c46e3e` 复查并各记录 45 项测试通过。Zikai 批准，Haoyu 用 Comment 确认修复且无新缺陷；
Comment 不改称 Approve，不虚构第二个批准。仓库持有人授权本次合并，之前已完成最新 main 集成检查。

代码质量证据：纯 Decimal、规则注册、共同服务、批次/存储/UI 边界；预期标签不进入执行；
实际清理任务归属；严格边界/真实 SQLite/来源和故障回归；锁文件、跨平台 CI 和静态检查；
保留原始性能样本及范围限制。第二条固定规则不代表任意扩展，测试数不代表覆盖率或无缺陷，
CI 不替代完整 Windows UI；7 条 ESLint 警告和大包提示仍登记。

回顾行动：保留四种清理竞态回归；测试隔离目标故障，不弱化断言；评审明确对应提交；
实际 Windows/模型验收后再录视频；只收尾既定范围，不新增企业功能。
没有提供的历史出勤、工时和燃尽数据不补造；这些观察来自代码/测试/评审，不归属于无记录的会议。
