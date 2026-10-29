# Sprint 1 Team Task Plan / 团队任务分工

Version: 0.2 · Prepared: 2026-10-30 (Asia/Shanghai) · Status: assignments confirmed by Zefeng Chen; estimates remain provisional.

Member mapping: A = Zefeng Chen; B = Rui Wen; C = Zikai He; D = Haoyu Shen; E = Ziyi Sun; F = Xuanyu Lu.
A owns requirements/integration; D owns independent testing; F owns final independent acceptance.

## 1. Purpose and current position

Deliver and independently accept one fixed sales case: actual SQL → captured evidence →
growth validation → persisted report → existing React UI.

The first implementation was AI-assisted under the user's direction and was pushed as
commit `494388a` on `sprint1/harness`. This does not establish member acceptance or peer
review. PR creation/merge status has not been verified. The earlier handoff in
[sprint1.md](../sprint1.md) is historical; its statement about not having pushed describes
that earlier stage.

Zefeng Chen confirmed the A–F assignments on 2026-10-30. A leads requirements and code integration; F owns final independent acceptance, supported by D’s independent tests. This supersedes the earlier proposal that A would perform independent acceptance. Assignment does not establish completed work or individual member acknowledgement. Review pairings and estimates remain proposals.
The Sprint dates, GitHub handles, availability, and PR URL remain TBD.

## 2. Roles and proposed remaining work

Estimates are productive hours for remaining Sprint 1 work, not hours already spent.
The initial planning suggestion totals 42 person-hours; the team must re-estimate it
before using it as a burndown baseline. Do not backdate these estimates.

| Member | Primary responsibility | Concrete tasks and deliverables | Proposed reviewer | Estimate |
|---|---|---|---|---:|
| A · Zefeng Chen | Coordination, requirements and code integration | Confirm scope; direct and understand AI-assisted implementation; submit PRs and integrate feedback; organize review/retrospective and merge readiness | B reviews integration; F independently accepts | 6 h |
| B · Rui Wen | Architecture and backend integration | Review data flow, API, migration and persistence; record rationale and alternatives; assess interrupted runs and lifecycle coupling; implement justified fixes | C · Zikai He | 6 h |
| C · Zikai He | Numerical validation | Review Decimal, units, tolerance, evidence association and unsupported inputs; propose counterexamples and implement necessary validator fixes | D · Haoyu Shen | 8 h |
| D · Haoyu Shen | Test engineering | Independently design edge/error cases; run and extend tests; examine cross-run isolation and restoration; distinguish baseline defects from regressions | C for tests; F for acceptance conclusions | 8 h |
| E · Ziyi Sun | React integration and usability | Review source labels, states, evidence expansion and history; test conversation switching and error feedback; fix confirmed UI issues | F · Xuanyu Lu | 6 h |
| F · Xuanyu Lu | Independent acceptance, reproduction and evidence coordination | Independently run the full acceptance checklist; reproduce on another machine; verify instructions; maintain registers with technical owners and aggregate members’ actual records | D checks acceptance evidence; B checks reproduction; A checks process records | 8 h |

These are primary responsibilities, not exclusive ownership. Every member should explain
their technical findings and participate in review. Documentation or review counts as
contribution only when actually performed; AI-generated code is not automatically six
members' work. No equal contribution percentage is assumed.

## 3. Ready-to-create task backlog

These are local planning IDs, not existing GitHub Issue numbers. Issue/PR links and dates
must be filled when the activities actually occur. Owners follow the confirmed assignments. Task dates and estimates still need scheduling; none of the tasks below is asserted complete. The existing implementation is input to this work.

| ID | Owner | Work and dependencies | Definition of done | Hours |
|---|---|---|---|---:|
| S1-T01 | A · Zefeng Chen | Team scope/availability discussion; no dependency | Record participants, confirmed requirements, exclusions, actual dates and assignments | 2 |
| S1-T02 | B · Rui Wen | Architecture and persistence review; after T01 | Review notes covering interfaces, migration, alternatives and risks; issues for findings | 4 |
| S1-T03 | C · Zikai He | Rule and evidence review; after T01 | Hand-checked examples and counterexamples; correct issues or document disposition | 5 |
| S1-T04 | D · Haoyu Shen | Independent automated test review; after T01, alongside T03 | Reproducible commands/results; missing cases added without weakening expected values | 5 |
| S1-T05 | E · Ziyi Sun | UI acceptance and code review; after T01 | Pass/fail, source labels, errors, history and switching checked; screenshots/findings | 4 |
| S1-T06 | F · Xuanyu Lu | Independent installation and reproduction; after T01 | OS/tool versions, exact commit, commands and observed outcomes recorded | 4 |
| S1-T07 | B · Rui Wen | B's targeted integration fixes and retest; after T02 findings | Peer-reviewed fix or explicit no-fix decision with reason | 2 |
| S1-T08 | C · Zikai He | C's rule fixes and cross-review; after T03/T04 | Fixes tested and reviewed by D; review D's test changes | 3 |
| S1-T09 | D · Haoyu Shen | Regression and review closure; after fixes | Identify resolved/open findings and rerun affected checks | 3 |
| S1-T10 | E · Ziyi Sun | UI fixes and retest; after T05 findings | Fixes reviewed by F; no claim that untouched UI was tested | 2 |
| S1-T11 | F · Xuanyu Lu | Update risks, reproduction guide and process evidence | Technical owners verify register; actual evidence links present | 2 |
| S1-T12 | A · Zefeng Chen | Integrate reviewed fixes and organize review/retrospective; after core fixes | F’s acceptance recorded; peer findings resolved or disposition agreed; remaining items and Sprint 2 actions recorded | 4 |
| S1-T13 | F · Xuanyu Lu | Final independent acceptance; after T06 and core fixes, before merge decision | Actual checklist outcomes on the reviewed commit; D reviews evidence; no self-approval of authored fixes | 2 |

Fix estimates are planning allowances, not an instruction to manufacture changes. If no
fix is needed, update remaining estimates and record the evidence supporting that decision.
Real-model configuration/acceptance is an explicit unresolved dependency: A selects a
service and spending cap; B verifies configuration; D checks results; F independently accepts and records reproduction.
Estimate it separately once those prerequisites are known rather than hiding it in completed work.

## 4. Collaboration and review workflow

1. Review the existing `sprint1/harness` implementation in a PR against the team's fork
   `main`. Running and reviewing a branch does not require pushing to it.
2. Prefer merging the reviewed baseline before parallel follow-up work. Then create one
   branch per task from current `main`, such as `sprint1/S1-T04-tests`.
3. If follow-up work must start before baseline merge, branch from `sprint1/harness` and
   target that branch in its PR; document the dependency and coordinate with A.
4. Each PR links its Issue, rationale, commands/results and risks. A reviewer other than
   the change author inspects it; no one approves their own change as peer review.
5. A checks acceptance and unresolved findings before merge. Suggested branch protection:
   require a peer approval and relevant checks when repository settings support this.

Hold at least one standing meeting weekly, following Week 1 pp. 4–5. Each member supplies
completed work, next work, and blockers. Dates are agreed by the team, not invented here.
Review demonstrates the increment; retrospective records what to improve about the process.

## 5. Evidence and workload templates

Task update:

```text
Task ID / member:
Date and commit:
Actual productive hours this update:
Remaining estimated hours:
Outcome / Issue / PR / test evidence:
Blocker or scope change:
Next action and agreed due date:
```

Maintain actual hours separately from remaining estimates. F aggregates remaining hours
into dated burndown snapshots, A checks scope changes, and each member supplies their own
values. Do not use commit count, code lines, or the proposal's 42 hours as actual contribution.
Record member acknowledgement, availability and dates during the first real team discussion. The lead’s assignment confirmation does not replace this discussion.

## 6. Sprint exit gate

- Accepted numerical rules and data scope remain documented.
- Fixed-case acceptance, errors, evidence isolation and restoration have evidence.
- Relevant changed code has peer review and justified dispositions of findings.
- Real-model execution is tested, or its unmet prerequisite and any scope deferral are
  explicitly agreed and reported; do not claim complete original acceptance if untested.
- Known upstream failure and remaining debt/risks have owners and decisions.
- Independent acceptance, weekly activity evidence and retrospective are actual records.

Related documents: [requirements/design](../design/sprint1-requirements-design.md),
[debt/risk register](sprint1-debt-risk-register.md).

---

# 中文版本

版本 0.2；编制日期：2026-10-30（北京时间）；状态：Zefeng Chen 已确认人员分配；估算仍待核实。

成员对应：A = Zefeng Chen；B = Rui Wen；C = Zikai He；D = Haoyu Shen；E = Ziyi Sun；F = Xuanyu Lu。
A 负责需求与代码集成，D 负责独立测试，F 负责最终独立验收。

## 1. 目标与真实进度

本轮目标：固定销售案例的真实 SQL → 捕获证据 → 增长率验证 → 持久化报告 → 原有 React 界面。
首版由用户指导、AI 协助实现，已作为 `494388a` 推送到 `sprint1/harness`。
这不代表成员已验收或评审；PR 是否已创建、合并尚未核实。原开发说明中的“尚未推送”属于当时交接快照。

Zefeng Chen 于 2026-10-30 确认 A–F 分工：A 负责需求与代码集成，F 负责最终独立验收，D 提供独立测试。此安排替代先前由 A 独立验收的提案。负责人已确定不代表工作完成或每位成员已亲自确认接受。评审配对与工时仍为建议。
GitHub 账号、可投入时间、Sprint 起止日期、PR 地址仍待填写。

## 2. 已确认的六人分工

以下为剩余 Sprint 1 工作的建议工时，共 42 人时，不是历史投入。团队重新估算确认后，才可成为燃尽图起点。

| 成员 | 主要职责 | 具体工作与产物 | 建议评审人 | 估算 |
|---|---|---|---|---:|
| A · Zefeng Chen | 协调、需求与代码集成 | 确认范围；组织并理解 AI 辅助实现；提交 PR、整合反馈；组织评审、回顾与合并检查 | B 审查集成；F 独立验收 | 6 小时 |
| B · Rui Wen | 架构及后端集成 | 检查数据流、API、迁移、持久化；记录方案取舍；评估中断状态和内部接口依赖；修复确认的问题 | C · Zikai He | 6 小时 |
| C · Zikai He | 数值验证 | 检查 Decimal、单位、容差、证据关联和不支持输入；提出反例；修复验证逻辑 | D · Haoyu Shen | 8 小时 |
| D · Haoyu Shen | 测试工程 | 独立设计边界/异常案例；补测试；检查跨运行隔离和恢复；区分上游问题与回归 | C 审查测试；F 审查验收结论 | 8 小时 |
| E · Ziyi Sun | React 与交互 | 检查来源标记、状态、证据展开、历史记录、会话切换和错误提示；修复已确认问题 | F · Xuanyu Lu | 6 小时 |
| F · Xuanyu Lu | 独立验收、复现与证据协调 | 独立执行完整验收；另一台机器复现；核查说明；与技术负责人维护登记，汇总成员真实记录 | D 核查验收证据；B 审查复现；A 审查过程记录 | 8 小时 |

职责不排他，也不代表其他人不能写代码。每个人应能解释自己的技术判断；文档和评审只有实际完成才计入贡献。
不能将 AI 生成的代码自动平分为六人工作，也不预设六人的贡献比例相同。

## 3. 可直接转为 Issues 的任务

以下是本地规划编号，不是已经创建的 GitHub Issue。负责人按已确认分工安排；实际日期、Issue 和 PR 链接发生后填写，未声明任何任务已完成。

| 编号 | 建议负责人 | 工作及依赖 | 完成条件 | 工时 |
|---|---|---|---|---:|
| S1-T01 | A · Zefeng Chen | 组织范围及成员可用时间讨论 | 真实参与者、需求、非目标、日期、分工有记录 | 2 |
| S1-T02 | B · Rui Wen | T01 后审查架构与存储 | 有接口、迁移、备选方案和风险审查；发现项建 Issue | 4 |
| S1-T03 | C · Zikai He | T01 后审查规则与证据 | 手算示例、反例及问题处理决定可追溯 | 5 |
| S1-T04 | D · Haoyu Shen | T01 后独立检查测试，与 T03 并行 | 可复现结果；补遗漏案例，不降低预期标准 | 5 |
| S1-T05 | E · Ziyi Sun | T01 后进行 UI 验收与评审 | 检查通过/失败、来源、异常、历史及切换；保留发现 | 4 |
| S1-T06 | F · Xuanyu Lu | T01 后独立安装复现 | 记录系统/工具版本、commit、命令及实际结果 | 4 |
| S1-T07 | B · Rui Wen | 根据 T02 发现修复集成问题 | 有经评审修复，或有依据的无需修复决定 | 2 |
| S1-T08 | C · Zikai He | 根据 T03/T04 修复并交叉评审 | D 评审修复；C 评审 D 的测试变更 | 3 |
| S1-T09 | D · Haoyu Shen | 修复后回归与关闭评审项 | 明确已解决/未解决项，重跑受影响检查 | 3 |
| S1-T10 | E · Ziyi Sun | 根据 T05 修复及复测 | F 评审；未测部分不能声称已验证 | 2 |
| S1-T11 | F · Xuanyu Lu | 更新风险、复现说明与过程证据 | 技术负责人核对登记表；附真实证据链接 | 2 |
| S1-T12 | A · Zefeng Chen | 集成经评审的修复，组织成果评审与回顾 | 收集 F 的验收结论；发现项有处理决定；记录未完成项及下轮行动 | 4 |
| S1-T13 | F · Xuanyu Lu | T06 及核心修复后、合并决定前独立验收 | 对评审版本记录实际结果，D 核查证据；不自审自己编写的修复 | 2 |

修复工时只是预留，不要求为了贡献制造改动。没有问题时据实调整估算并说明依据。
真实模型仍是明确的待解决依赖：A 选服务与费用上限，B 核实配置，D 检查结果，F 独立验收并记录复现。
明确前提后单独估算此项，不能悄悄算成已完成。

## 4. 协作规则

1. 首版 `sprint1/harness` 向团队 fork 的 `main` 提 PR；成员拉取运行和评审不需要向该分支推送。
2. 优先完成首版评审合并，然后从最新 `main` 按任务建分支，如 `sprint1/S1-T04-tests`。
3. 若必须提前开发，从 `sprint1/harness` 建分支，PR 暂指向它，写清依赖并与 A 协调。
4. PR 关联任务、理由、测试及风险；变更作者以外的成员评审，自己审核自己不算同伴评审。
5. A 检查验收与未解决项后再合并；仓库支持时建议开启同伴批准和检查要求。

依据 Week 1 第 4–5 页，每周至少一次站会，记录各人已完成、下一步、阻塞。
日期由真实讨论确定；Review 展示增量，Retrospective 反思过程并确定改进行动。

## 5. 成员更新模板

```text
任务编号／成员：
日期和 commit：
本次实际有效投入小时：
剩余估算小时：
成果／Issue／PR／测试证据：
阻塞或范围变化：
下一步及约定截止时间：
```

实际投入与剩余估算分开记录。F 汇总燃尽数据，A 核查范围变化，成员本人提供数值。
不能把提交次数、代码行数或建议的 42 小时当作真实贡献。第一次真实讨论中记录成员本人接受安排、可用时间和日期；组长确认分工不代替真实讨论。

## 6. Sprint 结束检查

- 已确认的规则和范围仍有文档；固定案例、异常、隔离及恢复有证据。
- 代码经过同伴评审，发现项有处理依据。
- 真实模型完成验证，或明确记录外部阻塞和经同意的延期；未测不能宣称原定验收全部完成。
- 上游缺陷、债务和风险有负责人及决定。
- 独立验收、每周活动和回顾均有真实记录。

配套：[需求与设计](../design/sprint1-requirements-design.md)、[技术债与风险](sprint1-debt-risk-register.md)。
