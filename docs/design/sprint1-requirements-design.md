# Sprint 1 Requirements and Design / 需求与设计

Version: 0.2 · Prepared: 2026-10-30 (Asia/Shanghai).
Numerical scope was approved by the user. Zefeng Chen confirmed member assignments on 2026-10-30; technical peer review and independent acceptance remain pending. Implementation reference: `494388a`;
upstream baseline: `90e34d49742852cd70b8ec506ba0ffaa1fe1bf90`.

Member mapping: A = Zefeng Chen; B = Rui Wen; C = Zikai He; D = Haoyu Shen; E = Ziyi Sun; F = Xuanyu Lu.
A owns requirements/integration; D owns independent testing; F owns final independent acceptance.

## 1. Problem, user, scope

User: a data-analysis Agent developer testing numerical claims. Trigger: an analysis
returns a growth claim that must be checked against actual query evidence. Existing
chat/SQL/trace infrastructure does not by itself establish numerical agreement.
Outcome: a developer can identify a mismatch, inspect its evidence, and reopen the report.

In scope: one synthetic CNY store, annual sales in 2024/2025, a structured growth claim,
one validation rule, a single-case runner, persistence and a React result card.
Out of scope: arbitrary natural-language extraction, arbitrary SQL semantic correctness,
multiple datasets/rules, batch comparison, automatic Agent repair, checkpoint/resume,
production deployment guarantees. Ordinary chat answers are not automatically validated.

Reuse: existing execute_sql tool, get_llm, FastAPI, SQLite/Alembic, chat page and SqlMessage.
New contribution: captured evidence linked to claims and validation results, explicit
non-verifiable/error states, report restoration and a developer acceptance workflow.
Novelty relative to related tools still needs research; module combination alone is not
evidence of originality (Week 1 pp. 10, 19, 24).

## 2. User stories and functional requirements

Priority M = required within the agreed Sprint 1 scope. Implementation presence does not
mean independent acceptance has passed.

| ID | User story / required behavior | Priority | Implementation | Acceptance |
|---|---|---|---|---|
| FR-01 | As a developer, run the fixed case and inspect actual executed SQL/results | M | runner.py → existing execute_sql | AC-01 |
| FR-02 | Link each claim to evidence in the same run; reject missing/foreign evidence | M | models.py, validation.py | AC-07 |
| FR-03 | Compare a growth claim using agreed units and tolerance | M | validation.py | AC-01–04 |
| FR-04 | Distinguish disagreement, insufficient evidence and internal tool errors | M | validation.py, runner.py | AC-05–08 |
| FR-05 | Persist and reopen run, steps, evidence, claim, rule version and result | M | store.py, migration 006, API | AC-09 |
| FR-06 | Show classification, source, values, reasons and expandable SQL in the existing UI | M | HarnessCheck, ValidationResultCard, SqlMessage | AC-02, AC-09 |
| FR-07 | Keep injected and model-generated claims distinct; never invent a missing model claim | M | runner.py, source field | AC-10 |

## 3. Domain rules and data

| Rule | Contract |
|---|---|
| BR-01 | Fixed store demo-store, currency CNY, complete years 2024 and 2025 |
| BR-02 | Integer cents: 2024 records 4000 and 6000; 2025 records 5000 and 6000 |
| BR-03 | Growth = (current − previous) / previous × 100; independent expected value = 10% |
| BR-04 | Previous > 0; current ≥ 0. Zero denominator, missing/null or negative amounts are unverifiable |
| BR-05 | Claim unit percent: 10 means 10%, not 0.1%; absolute tolerance ≤ 0.01 percentage points |
| BR-06 | Decimal and unrounded comparison; ROUND_HALF_UP to two decimals only for display |
| BR-07 | Evidence must be complete, unique for its reference, same run and supported scope/unit |
| BR-08 | Invalid/nonfinite values are unverifiable; computation/execution exceptions are tool_error |

The validator checks fixed output scope and numbers; it does not prove upstream data
truth or arbitrary SQL business semantics. The fixture and fixed aggregation query are
independently checked in tests. Do not change expected values by calling the validator itself.

## 4. Acceptance contract

| ID | Input/action | Expected outcome | Evidence / proposed verifier |
|---|---|---|---|
| AC-01 | 100→110 yuan, claim 10% | passed; expected 10.00%; actual SQL totals 10000/11000 cents | unit + real-query tests; F/D |
| AC-02 | Same evidence, claim 18.7% | failed; SQL and values visible; injected source identified | browser + unit tests; F/E |
| AC-03 | Claims 10.01%, 10.02% | passed, failed respectively | boundary tests; C/D |
| AC-04 | 100→90 claim −10%; 100→0 claim −100% | both passed | unit tests; C/D |
| AC-05 | Previous zero or missing | unverifiable with distinct reason | unit tests; D |
| AC-06 | Negative/invalid amounts, unsupported units/scope or truncated evidence | unverifiable | unit tests; C/D |
| AC-07 | Missing ID or another run's evidence | unverifiable; never borrow unrelated results | isolation tests; B/D |
| AC-08 | Validator/query exception or model timeout | tool_error; no pass; safe error code | fault tests; B/D |
| AC-09 | Read report through a new session, reload UI; upgrade database | report preserved; previous database records preserved | persistence, migration, browser tests; B/F |
| AC-10 | Real model calls query and submits claim; alternatively submits none | agent_generated; result based on captured evidence, or missing_claim | local model-double test exists; remote run pending; F/D |

Independent acceptance status for AC-01–10: not yet recorded. The prior implementation
run reported 30 new backend tests passing, an earlier 383-test backend/MCP run passing
(including 29 then-current new tests), and one new browser test passing. The frontend
suite retained 44 passes and one pre-existing USAGE failure. These are implementation-side
results, not fabricated member acceptance. Use [test_harness.py](../../tests/unit/test_harness.py)
and [harness.spec.ts](../../tests/e2e/harness.spec.ts) as executable evidence.

## 5. Non-functional requirements

| ID | Measurable target | Architectural tactic and tradeoff | Validation/status |
|---|---|---|---|
| NFR-01 Reliability | Tested query/validation exceptions and model timeout never yield passed; successful persisted reports reopen unchanged | Separate execution/result states; exception boundary; 60 s model timeout and recursion limit 8; added state complexity | fault, persistence and migration tests; hard process recovery remains debt |
| NFR-02 Extensibility | Adding a second rule should require only rule implementation, selection/registration and tests, without changing capture/storage/UI core logic | Pure validation contract and module separation; risk of premature abstraction | Sprint 1 establishes boundary; second-rule change experiment in Sprint 2 still required |

Fixed synthetic data, bounded result size and safe error codes are implementation safeguards,
not a claim of production security or a substitute for an evaluated quality requirement.
No latency or availability SLA has been promised. For the six-person team, Week 1 p. 4
requires at least two non-functional requirements with architecture and rationale.

## 6. Architecture and interfaces

```text
React chat page / HarnessCheck
          │ POST /api/harness/runs
          ▼
FastAPI ── runner ── query_sales ── existing SQLAlchemy execute_sql
              │                         │ captured Evidence
              ├─ test claim OR bounded configured Agent
              └─ validate_growth ── ValidationResult
          │
          ▼
store / harness_runs JSON snapshot ── GET API ── ValidationResultCard
```

| Object | Key fields and responsibility |
|---|---|
| Run | id, conversation_id, source, started/finished, state, model, answer, steps/evidence/claim/result |
| Step | id, kind (query/claim/validation), status, duration, safe error code |
| Evidence | id, run_id, step_id, actual SQL, columns/rows, truncation, dataset version, amount unit |
| Claim | evidence_id, claimed_value string, unit, store and comparison years |
| ValidationResult | classification, reason, rule version, tolerance, raw/display expected value and difference |

Execution state is running/completed/error; numerical classification is
passed/failed/unverifiable/tool_error. A completed run may have a failed or unverifiable
claim. Interrupted running records must not be presented as passes.

POST accepts source, claimed_value and optional conversation_id, but no client evidence.
Model mode ignores the injected value. GET /api/harness/runs filters by conversation and
returns the latest 20 reports; GET /api/harness/runs/{id} retrieves a report. Migration 006
adds a report table/index; it does not rewrite existing conversation data.

## 7. Design decisions and alternatives

| ID | Choice | Alternative and reason not selected | Cost/limitation |
|---|---|---|---|
| ADR-01 | Structured claims | Free-text extraction introduces extraction ambiguity before rule correctness is established | Narrow supported input; missing claims unverifiable |
| ADR-02 | Deterministic Decimal rule | LLM-as-judge may fluctuate and cannot independently establish numerical truth | One explicit rule, limited semantics |
| ADR-03 | JSON report in existing DB | Chat TEXT loses structured state; fully normalized trace service adds infrastructure | Schema evolution/querying limitations; explicit versions |
| ADR-04 | Reuse React/SqlMessage | Separate dashboard duplicates UI and expands Sprint scope | Fixed-case collapsible UI rather than automatic inline validation of every answer |
| ADR-05 | Bounded Agent and fixed SQL fixture | Full original chat/DataHub graph increases configuration and integration scope | Does not establish full upstream Agent compatibility |

These decisions document the implemented design; team review is still required. They
apply Week 4 requirements validation, Week 5 architectural reasoning, Week 8 separation
of responsibilities, and Week 3 peer review. They are not proof that all SOLID principles
or all course activities have already been fulfilled.

## 8. Change and acceptance record

For any numerical/scope change: B/C describe impact → A confirms requirement → D updates
independent expected cases → implement and review → rerun checks → update this document
and rule version when behavior changes. Never lower thresholds to conceal a failing test.

```text
Decision ID/date:
Requirement/ADR IDs:
Proposer and reviewer:
Reason and alternatives:
Accepted change / rejected change / deferred:
Affected tests and rule version:
Issue/PR/evidence link:
```

Related: [team plan](../process/sprint1-team-plan.md),
[debt/risk register](../process/sprint1-debt-risk-register.md), [run guide](../sprint1.md).

---

# 中文版本

版本 0.2；编制日期：2026-10-30（北京时间）。数值范围已经用户确认，Zefeng Chen 已于 2026-10-30 确认分工；技术同伴评审及独立验收仍待完成。
实现参考 `494388a`；上游基线 `90e34d49742852cd70b8ec506ba0ffaa1fe1bf90`。

成员对应：A = Zefeng Chen；B = Rui Wen；C = Zikai He；D = Haoyu Shen；E = Ziyi Sun；F = Xuanyu Lu。
A 负责需求与代码集成，D 负责独立测试，F 负责最终独立验收。

## 1. 问题、用户和范围

面向测试数值结论的 Agent 开发者。分析产生增长率声明后，开发者需要核对真实查询证据并定位不一致。
已有聊天、SQL 和追踪设施本身不能证明数值正确。本轮让开发者识别不一致、查看证据并重新打开报告。

范围：一个 CNY 合成店铺、2024/2025 年销售额、结构化增长率声明、一条规则、单案例执行、存储及 React 卡片。
非目标：任意文本提取、任意 SQL 业务正确性、多数据集/规则、批量版本比较、自动修复、Checkpoint/Resume、生产保障。
普通聊天中的任意答案不自动被验证。

复用 execute_sql、get_llm、FastAPI、SQLite/Alembic、聊天页和 SqlMessage。
新增贡献是声明与真实证据的关联验证、明确状态、报告恢复和开发者验收流程。
相关工具比较与创新依据仍待核查，不能仅用模块组合宣称原创（Week 1 第 10、19、24 页）。

## 2. 用户故事与功能需求

M 表示约定 Sprint 1 范围内必须完成；已有实现不等于人工验收通过。

| 编号 | 用户故事／要求 | 优先级 | 实现位置 | 验收 |
|---|---|---|---|---|
| FR-01 | 开发者运行固定案例并查看实际 SQL/结果 | M | runner.py 和原有 execute_sql | AC-01 |
| FR-02 | 声明只关联同一次运行的有效证据 | M | models.py、validation.py | AC-07 |
| FR-03 | 按约定单位和容差比较增长率 | M | validation.py | AC-01–04 |
| FR-04 | 区分数值不符、证据不足和工具异常 | M | validation.py、runner.py | AC-05–08 |
| FR-05 | 保存并恢复运行、步骤、证据、声明、规则版本和判定 | M | store.py、迁移 006、API | AC-09 |
| FR-06 | 原界面显示来源、状态、数值、原因及可展开 SQL | M | HarnessCheck、ValidationResultCard、SqlMessage | AC-02、09 |
| FR-07 | 区分注入与模型声明，不为缺失声明编造答案 | M | runner.py、source 字段 | AC-10 |

## 3. 业务约定

| 编号 | 规则 |
|---|---|
| BR-01 | demo-store、CNY、2024 与 2025 两个完整自然年 |
| BR-02 | 金额整数分，记录分别为 4000+6000 与 5000+6000 |
| BR-03 | `(本期−上期)/上期×100`；独立手算标准答案 10% |
| BR-04 | 上期>0，本期≥0；零分母、缺失/null、负数为无法验证 |
| BR-05 | 10 percent 表示 10%；绝对容差≤0.01 个百分点，含边界 |
| BR-06 | Decimal 计算，未舍入比较；ROUND_HALF_UP 两位小数仅展示 |
| BR-07 | 引用证据唯一、完整、同一运行，且单位和范围受支持 |
| BR-08 | 无效/非有限声明无法验证；执行/计算异常为工具错误 |

验证器检查固定输出范围和数值，不证明源数据真实性或任意 SQL 语义。固定数据和聚合查询有独立预期检查，
不能调用被测验证器本身生成标准答案。

## 4. 验收约定

| 编号 | 输入／操作 | 预期 | 证据／建议核查人 |
|---|---|---|---|
| AC-01 | 100→110 元，声明 10% | 通过；10.00%；SQL 合计 10000/11000 分 | 单元、真实查询；F/D |
| AC-02 | 同证据，声明 18.7% | 失败，显示 SQL/数值与测试注入标记 | 浏览器、单元；F/E |
| AC-03 | 10.01%、10.02% | 分别通过、失败 | 边界测试；C/D |
| AC-04 | 100→90 声明−10%；100→0 声明−100% | 都通过 | 单元；C/D |
| AC-05 | 上期零或缺失 | 无法验证，原因区分 | 单元；D |
| AC-06 | 负值/无效金额、不支持单位/范围、截断 | 无法验证 | 单元；C/D |
| AC-07 | ID 不存在或跨运行证据 | 无法验证，不误用其他结果 | 隔离测试；B/D |
| AC-08 | 验证/查询异常或模型超时 | 工具错误，不通过；安全错误码 | 故障测试；B/D |
| AC-09 | 新数据库会话读取、网页刷新、迁移升级 | 报告恢复；原有数据不丢失 | 持久化、迁移、浏览器；B/F |
| AC-10 | 模型查询并提交声明，或没有声明 | 模型来源；按实际证据判定，或 missing_claim | 本地替身已有，真实调用待测；F/D |

以上人工验收均尚无完成记录。此前实现方结果：新增后端 30 项通过；较早一次后端/MCP 共 383 项通过
（其中包含当时的 29 项新增测试）；新增浏览器 1 项通过。原前端 44 通过、1 个原有 USAGE 失败。
这些不能替代成员独立验收。可执行证据见英文段落中的测试文件链接。

## 5. 非功能需求

| 编号 | 可验收目标 | 架构措施与代价 | 状态 |
|---|---|---|---|
| NFR-01 可靠性 | 被测查询/验证异常和模型超时不能通过；成功持久化记录原样恢复 | 执行与判定分离、异常边界、60 秒模型超时、递归上限 8；增加状态复杂度 | 已有故障/恢复/迁移测试；硬中断恢复仍是债务 |
| NFR-02 可扩展性 | 第二条规则只新增规则实现、选择/注册及测试，不改采集/存储/UI 核心逻辑 | 纯验证契约与模块分离；避免过早抽象 | Sprint 1 建立边界，Sprint 2 仍需实际新增规则验证 |

合成数据、限量结果和安全错误码是实现措施，不代表生产安全认证或第三项已验收质量属性。
未承诺性能/可用性 SLA。六人团队按 Week 1 第 4 页需至少两项非功能需求及架构理由。

## 6. 架构与接口

流程：聊天页 → POST API → runner → 原有 SQL 工具 → 捕获 Evidence → 固定声明或受限 Agent
→ validate_growth → ValidationResult → 数据库存储 → GET API → 验证卡片。

| 对象 | 主要字段及职责 |
|---|---|
| Run | ID、会话、来源、起止、状态、模型、回答、步骤/证据/声明/结果 |
| Step | ID、query/claim/validation 类型、状态、耗时、安全错误码 |
| Evidence | ID、run_id、step_id、实际 SQL、列/行、截断、数据版本、金额单位 |
| Claim | evidence_id、字符串数值、单位、店铺、比较年份 |
| ValidationResult | 状态、原因、规则版本、容差、原始/展示计算值、差值 |

运行状态是 running/completed/error；验证状态是 passed/failed/unverifiable/tool_error。
运行完成仍可能验证失败或无法验证，中断记录不能显示通过。
POST 只接受来源、声明值及可选会话 ID，不接受客户端证据；模型模式忽略注入数值。
GET 列表按会话返回最近 20 项；按 ID 可读取单条。迁移 006 新增表和索引，不改写旧会话。

## 7. 设计决策

| 编号 | 选择 | 未选方案及原因 | 代价 |
|---|---|---|---|
| ADR-01 | 结构化声明 | 自由文本提取过早引入额外歧义 | 范围窄，缺失声明无法验证 |
| ADR-02 | 确定性 Decimal 规则 | 模型裁判有波动，不能独立证明数值真值 | 仅一条明确规则，语义有限 |
| ADR-03 | 现有 DB 中保存 JSON 报告 | 聊天文本丢失结构；完整事件服务增加基础设施 | 版本升级和复杂查询需后续设计 |
| ADR-04 | 复用 React 和 SqlMessage | 独立仪表盘重复 UI、扩大范围 | 固定案例折叠区，不自动验证每条聊天 |
| ADR-05 | 受限 Agent 和固定 SQL | 完整聊天/DataHub 图增加配置与集成范围 | 不证明全量上游兼容性 |

这些说明已实现方案，仍需团队评审。对应 Week 4 需求验证、Week 5 架构推理、Week 8 职责分离、Week 3 同伴评审，
不能据此声称所有设计原则和课程活动已完成。

## 8. 变更与验收记录

数值/范围变更：B/C 说明影响 → A 确认 → D 更新独立标准案例 → 实现与评审 → 重测 → 更新文档及行为对应规则版本。
禁止为了通过测试降低标准。

```text
决定编号／日期：
需求／ADR 编号：
提出人／评审人：
理由及备选方案：
接受／拒绝／延期：
受影响测试和规则版本：
Issue／PR／证据链接：
```

配套：[任务分工](../process/sprint1-team-plan.md)、[技术债与风险](../process/sprint1-debt-risk-register.md)、[运行说明](../sprint1.md)。
