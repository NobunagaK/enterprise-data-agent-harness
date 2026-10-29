# Sprint 1 Technical Debt and Risk Register / 技术债与风险登记

Version: 0.2 · Prepared: 2026-10-30 (Asia/Shanghai) · Team review pending.
Implementation reference: `494388a`. Owners A–F follow the [team plan](sprint1-team-plan.md) confirmed by Zefeng Chen on 2026-10-30. This does not assert individual member acknowledgement or completed review.

Member mapping: A = Zefeng Chen; B = Rui Wen; C = Zikai He; D = Haoyu Shen; E = Ziyi Sun; F = Xuanyu Lu.
A owns requirements/integration; D owns independent testing; F owns final independent acceptance.

## 1. Classification and handling rules

- Technical debt: an existing implementation shortcut whose future maintenance cost
  grows if left untreated. Record the shortcut, future cost, repayment and decision.
- Risk: an uncertain future event. Record trigger, likelihood, impact and mitigation.
- Defect: observed incorrect behavior, tracked independently whether or not it has a
  debt cause. An external blocker is not automatically technical debt.
- Batch evaluation, additional rules and free-text extraction are deferred features,
  not debt merely because they are absent (Week 6, p. 10).

Priorities: P1 = threatens core acceptance; P2 = plan before affected extension;
P3 = monitor. Likelihood/impact below are initial qualitative estimates, not measurements.
Proposed decisions and estimates are not team-approved commitments or actual hours.

## 2. Technical debt register

| ID | Existing shortcut and evidence | Future cost if retained | Proposed owner / reviewer | Proposed repayment and estimate | Priority / decision gate | Status |
|---|---|---|---|---|---|---|
| TD-01 | runner.py disposes SQLAlchemyQueryEngine through its internal `_engine` reference | Upstream lifecycle changes can break adapter cleanup and duplicate fixes | B / C | Encapsulate cleanup behind an agreed public lifecycle boundary; resource cleanup and failure tests, 2–4 h | P2; before another connector/engine integration | Open; deferral proposed, not approved |
| TD-02 | Initial running report is saved, then final report; no hard-crash reconciliation | Stale runs accumulate; users must diagnose unfinished work manually, increasing support cost | B / D | Define interrupted/expired semantics and reconcile without overwriting active runs; crash/restart test, 4–8 h | P1 if restart recovery is claimed; otherwise P2 before batch work | Open; incomplete state disclosed |

Repayment is done only with a linked change, a regression test and peer verification.
The estimates exclude unexpected upstream changes and must be re-estimated by owners.
TD-02 is about report lifecycle, not reintroducing excluded Agent checkpoint/resume.

## 3. Observed issues and external blockers

| ID | Type / evidence | Current consequence | Owner / reviewer | Next action and closure evidence |
|---|---|---|---|---|
| BUG-01 | Upstream defect: buildUiMessages.test.ts USAGE attachment case failed in baseline and implementation runs; 44 frontend passes / 1 failure | Full frontend suite is not green; validation card browser test passed separately | E / D | Reproduce on baseline, link a separate Issue; fix with focused test or explicitly retain known limitation; not automatically a Sprint 1 blocker |
| BLOCK-01 | Configured provider was OpenAI with no key at last runtime inspection | Remote model acceptance unexecuted; local model double only tests orchestration | A / B | Select service, configure credentials securely and permitted destination, set budget, then run and record remote cases; never put keys in chat/issues/docs |
| GAP-01 | Independent member acceptance/review evidence not supplied | Cannot claim team acceptance, contributions or finished Sprint retrospectively | A / F | Schedule real review and acceptance; attach actual results, decisions and member evidence |

Do not mark BLOCK-01 resolved merely because a key field exists; verify the actual call.
Do not mark GAP-01 resolved by copying implementation-side automated results.

## 4. Risk register

Suggested likelihood and impact use Low/Medium/High. “Before …” entries are decision
gates; calendar deadlines and decision dates must be filled by the team.

| ID | Event and trigger | Likelihood / impact | Proposed owner | Mitigation / contingency | Decision gate / status |
|---|---|---|---|---|---|
| R-01 | Model unavailable or calls fail; first live request lacks valid configuration or returns access/network errors | High / High | A, B | Continue deterministic checks; diagnose exact error; explicitly defer live acceptance if prerequisite remains missing | Before real-model demo; open |
| R-02 | Model omits valid claim or evidence ID; missing_claim/association failures recur | Medium / High | C, D | Retain structured contract and unverifiable status; record failures, do not fabricate claims; limit integration scope | Before declaring model workflow accepted; open |
| R-03 | Report schema changes break historical reads; incompatible fields introduced | Medium / Medium | B, F | Plan schema version/converter and old-report fixtures before incompatible changes; current rule/data versions alone are insufficient | Before schema change; open |
| R-04 | Scope exceeds time; estimates exceed member availability or optional UI/rules displace core checks | Medium / High | A | Freeze optional additions; prioritize core acceptance and re-estimate with team | Every planning/review meeting; open |
| R-05 | Credentials or real data enter traces after expansion beyond synthetic fixture | Low / High | B, E | Keep fixture synthetic; review captured fields, result limits and safe errors; stop sharing affected artifacts if discovered | Before external data integration; open |
| R-06 | Reports overstate quality; injected/local-double cases mixed with real model outcomes | Medium / High | D, A | Separate source and test modes; independent expected values; report denominators, limitations and unrun checks | Before evaluation/report submission; open |
| R-07 | Work cannot be reproduced; another member's setup fails or differs in dependencies/migrations | Medium / Medium | F | Record OS, tools, commit, lockfiles and commands; diagnose environment failures separately from defects | Before independent acceptance; open |
| R-08 | Historical process data are missing; no real weekly estimates/meetings available | High / Medium | F, A | Start honest records now; identify coverage gaps; do not invent historical burndown or hours; consult TA if needed | Before process report; open |
| R-09 | Concurrent direct pushes or self-approval obscure ownership/review | Medium / Medium | A | One task per branch, explicit PR dependency, reviewer other than author; protect main where supported | Before merging follow-up work; open |
| R-10 | Model experiments exceed budget; repeated calls accumulate or spend is unknown | Medium / Medium | A, D | Set provider/model, maximum calls and currency cap before execution; log spend where available and stop at cap | Before any remote experiment; open |

## 5. Stop rules and release decision

Stop optional work and fix the core if any of these occurs:

- An internal exception or foreign evidence yields passed.
- The agreed tolerance or standard answer is silently changed to make a test pass.
- A successful save cannot be reopened, or migration damages existing records.
- A test-injected claim is presented as a real model error.

Pause remote experiments when credentials/access are unresolved, the agreed budget is
reached, or sensitive content appears in output. Retain deterministic development work.
Do not describe the entire Sprint as accepted while required acceptance is still unrun;
any deferral needs an explicit decision and limitation in the report.

Suggested merge gate: independent acceptance of the scoped increment, peer review of
changed code, affected checks passing, and explicit disposition of known issues. Branch
push/PR creation is not the same as Sprint acceptance or production release.

## 6. Review cadence and record template

Review at each weekly standing meeting, after relevant failures/PRs, and before Sprint
closure. Technical owners investigate; F maintains links/status; A coordinates priorities.
Use Open → Investigating → Decision recorded → Resolved, or Deferred with a reason and
next trigger. “Resolved” requires evidence, not a plan alone.

```text
Item ID / type:
Observed date / source / commit:
Owner confirmed on / reviewer:
Trigger / likelihood / impact:
Options considered and estimated repayment cost:
Decision / rationale / decision date:
Agreed due date or next decision gate:
Issue / PR / test / review evidence:
Status and remaining risk:
```

No team decision dates or repayment completion are asserted in this initial register.
Related: [requirements/design](../design/sprint1-requirements-design.md), [run guide](../sprint1.md).

---

# 中文版本

版本 0.2；编制日期：2026-10-30（北京时间）；待团队评审。实现参考 `494388a`。
A–F 对应 Zefeng Chen 于 2026-10-30 确认的[人员分工](sprint1-team-plan.md)，不代表每位成员已亲自确认或完成评审。

成员对应：A = Zefeng Chen；B = Rui Wen；C = Zikai He；D = Haoyu Shen；E = Ziyi Sun；F = Xuanyu Lu。
A 负责需求与代码集成，D 负责独立测试，F 负责最终独立验收。

## 1. 分类与管理规则

- 技术债：已存在的实现捷径会增加未来维护成本，需要说明捷径、未来成本、偿还方案及决定。
- 风险：不确定的未来事件，记录触发条件、概率、影响和缓解措施。
- 缺陷：已观察到的错误行为，独立登记；外部阻塞也不自动属于技术债。
- 批量评测、更多规则、自由文本提取是延期功能，不因为未实现就成为债务（Week 6 第 10 页）。

P1 威胁核心验收，P2 在受影响扩展前处理，P3 持续观察。概率和影响是初步定性估计，不是测量值。
建议方案和估算不是团队已同意的承诺，也不是实际投入。

## 2. 技术债登记

| 编号 | 现有捷径及证据 | 不处理的未来成本 | 建议负责人／评审 | 偿还方案及估算 | 优先级／决定节点 | 状态 |
|---|---|---|---|---|---|---|
| TD-01 | runner.py 通过 `_engine` 内部引用清理 SQLAlchemy 引擎 | 上游生命周期接口变化会造成适配清理失效和重复修改 | B／C | 建立明确公开生命周期边界，补资源清理及失败测试；2–4 小时 | P2；下一数据源/引擎集成前 | 开放，建议延期但未批准 |
| TD-02 | 先保存 running 后保存终态，缺少硬中断协调 | 未结束记录累积，人工诊断和支持成本增长 | B／D | 定义 interrupted/expired 语义，在不覆盖活跃任务的前提下协调状态；崩溃重启测试；4–8 小时 | 若宣称中断恢复则 P1，否则批量工作前 P2 | 开放，已披露未完成状态 |

偿还完成必须有变更、回归测试和同伴验证。估算不含意外上游变化，由负责人复估。
TD-02 管理报告生命周期，不是重新加入已排除的 Agent Checkpoint/Resume。

## 3. 已知问题和外部阻塞

| 编号 | 类型／证据 | 影响 | 建议负责人／评审 | 下一步与关闭证据 |
|---|---|---|---|---|
| BUG-01 | 上游 buildUiMessages.test.ts 的 USAGE 归属失败；基线和实现阶段均观察到，44 通过/1 失败 | 全前端套件未全绿；验证卡片浏览器测试独立通过 | E／D | 在基线复现并建独立 Issue；修复并测试或明确保留局限；不自动认定阻塞 Sprint 1 |
| BLOCK-01 | 最近运行检查为 OpenAI 且无密钥 | 真实模型验收未执行；本地替身只验证编排 | A／B | 选择服务、安全配置凭据及允许的目标、确定预算，再实际运行记录；不要把密钥写入聊天/Issue/文档 |
| GAP-01 | 尚未提供独立验收/同伴评审证据 | 不能宣称团队验收、个人贡献和回顾已完成 | A／F | 组织真实活动并附结果、决定和个人证据 |

密钥字段非空不代表 BLOCK-01 解决，须验证实际调用；复制 AI 自动测试结果不能关闭 GAP-01。

## 4. 风险登记

高/中/低为建议概率和影响；“某活动之前”是决定节点，具体截止日期和决定日期由团队填写。

| 编号 | 事件及触发条件 | 概率／影响 | 建议负责人 | 缓解／应对 | 决定节点／状态 |
|---|---|---|---|---|---|
| R-01 | 模型不可用；首次调用缺配置或出现访问/网络错误 | 高／高 | A、B | 继续确定性测试，诊断具体错误；仍无前提则明确延期真实验收 | 真实模型演示前／开放 |
| R-02 | 模型不提交有效声明/证据 ID；反复出现 missing_claim 或关联失败 | 中／高 | C、D | 保留结构化约定与无法验证状态，记录失败，不代造答案；限制集成范围 | 宣称模型链路通过前／开放 |
| R-03 | 报告不兼容字段导致历史读取失败 | 中／中 | B、F | 变更前设计 schema 版本、转换及旧报告测试；现有规则/数据版本不能替代它 | schema 变更前／开放 |
| R-04 | 估算超出成员时间；可选 UI/规则挤占核心验收 | 中／高 | A | 暂停额外功能，优先验收并共同复估 | 每次计划/评审／开放 |
| R-05 | 从合成场景扩展后，凭据或真实敏感数据进入追踪 | 低／高 | B、E | 保持合成数据，审查采集字段、容量、安全错误；发现泄露停止分享相关产物 | 外部数据接入前／开放 |
| R-06 | 注入/替身测试混入真实模型结果，报告夸大质量 | 中／高 | D、A | 分开来源与模式，独立预期，报告分母、局限、未执行项 | 评测/报告提交前／开放 |
| R-07 | 他人环境不能复现或依赖/迁移不同 | 中／中 | F | 记录系统、工具、commit、锁文件、命令；区分环境与代码问题 | 独立验收前／开放 |
| R-08 | 历史每周估算/会议缺失 | 高／中 | F、A | 从现在如实记录，标明覆盖缺口，不补造燃尽和工时；必要时咨询 TA | 过程报告前／开放 |
| R-09 | 多人直接推同一分支或自行批准导致责任和评审不清 | 中／中 | A | 一任务一分支，PR 依赖明确，作者以外成员评审；支持时保护 main | 后续工作合并前／开放 |
| R-10 | 重复调用或费用未知导致模型预算超支 | 中／中 | A、D | 运行前明确服务/模型、最大次数、币种和费用上限；可获得时记录消费，到上限即停 | 远程实验前／开放 |

## 5. 停止规则和交付决定

出现以下情况，先暂停可选功能并修复核心：

- 内部异常或跨运行证据被判通过。
- 为通过测试悄悄改容差或标准答案。
- 成功保存后不能恢复，或迁移损坏原有记录。
- 将注入声明当作真实模型错误展示。

凭据/访问未解决、达到预算上限、输出出现敏感信息时暂停远程实验，确定性开发仍可继续。
必要验收未执行时不能声称整个 Sprint 已验收；延期必须有明确决定并披露局限。
建议合并条件：约定增量独立验收、同伴评审、相关检查通过、已知问题明确处置。
推送/创建 PR 不等于 Sprint 验收或生产发布。

## 6. 更新频率与记录模板

每周站会、相关失败/PR 之后和 Sprint 关闭前更新。技术负责人调查，F 维护证据与状态，A 协调优先级。
状态建议：开放 → 调查中 → 已记录决定 → 已解决；或注明理由和下次触发条件的延期。
“已解决”必须有证据，不是只有计划。

```text
条目编号／分类：
观察日期／来源／commit：
负责人确认日期／评审人：
触发条件／概率／影响：
备选方案及估算偿还成本：
决定／理由／实际决定日期：
约定截止时间或下次决定节点：
Issue／PR／测试／评审证据：
状态与剩余风险：
```

本初版未填造团队决定日期和偿还完成情况。配套：[需求与设计](../design/sprint1-requirements-design.md)、[运行说明](../sprint1.md)。
