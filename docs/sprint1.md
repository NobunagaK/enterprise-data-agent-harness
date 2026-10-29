# Sprint 1: Sales Growth Evidence Validation

The English development guide appears first. The Chinese version follows below.

## Confirmed scope

The user approved this plan in the project conversation and will act as the independent
acceptance reviewer. Independent acceptance has not yet been performed.
Baseline commit: `90e34d49742852cd70b8ec506ba0ffaa1fe1bf90`.

As an Agent developer, I want to check whether a claim agrees with actual SQL results
in a fixed sales scenario and inspect the query and calculation when it does not.
A pass establishes numerical consistency, not the business correctness of arbitrary SQL.

- One store, `demo-store`; currency CNY; complete calendar years 2024 and 2025.
- Amounts are integer CNY cents. Fixture records total 4000+6000 and 5000+6000,
  equivalent to 100 and 110 yuan.
- Growth is `(current - previous) / previous * 100`. Previous sales must be positive;
  current sales may be zero. Negative amounts are outside this sprint's scope.
- A claim of `10` with unit `percent` means 10%. Absolute tolerance is 0.01 percentage
  points, inclusive.
- Calculations use Decimal. Cross-multiplication avoids recurring-decimal boundary
  errors in classification. Two-decimal ROUND_HALF_UP rounding is for display only.
- Missing data, a zero denominator, unsupported units or scope, truncation, and
  evidence from another run produce `unverifiable`.
- Tool exceptions produce `tool_error`, separately from numerical disagreement (`failed`).
- `test_injected` and `agent_generated` claims are labeled separately. Injected errors
  must not be used as evidence of a real model's error rate.

## Implementation and reuse

The implementation reuses the existing SQLAlchemyQueryEngine `execute_sql` tool,
`get_llm` configuration, FastAPI, SQLite/Alembic, React chat page, and SqlMessage component.

The new `harness` package contains data contracts, actual query capture, a pure growth
validation function, a single-case runner, and report storage. The chat page provides
a collapsible section labeled “销售增长率验证 · Sprint 1” (Sales Growth Validation).
Ordinary chat messages are not automatically validated: this is a fixed-case entry point,
not an extractor for arbitrary analysis results.

Data flow: Run → existing SQL tool → Evidence(run_id, step_id) → Claim → pure rule
→ persisted report → React.

Fixed-test mode makes no model calls. Real-model mode uses the configured model and a
bounded LangChain Agent with only `query_demo_sales` and `submit_growth_claim` tools.
It is not a full regression of the original chat graph: it does not use DataHub, charts,
or arbitrary SQL. If the model submits no claim, validation returns `missing_claim`;
the implementation does not invent an answer on its behalf.

SQL and query results are captured during execution; models cannot upload replacement
evidence. The fixed aggregate contains at most two rows. Text answers are limited to
8000 characters with an explicit truncation flag. Service exceptions store safe error
codes rather than exception text that might expose credentials.

## Design rationale and non-functional requirements

1. Reliability: execution state and validation status are separate. Query or validator
   errors cannot produce a pass. Model execution has a 60-second timeout and an Agent
   recursion limit of 8. Tests cover errors and timeouts. Batch-case isolation belongs
   to Sprint 2.
2. Extensibility: the pure validator receives Claim/Evidence and returns ValidationResult
   without model or storage access. Only one rule exists today. A second rule and rule
   registration in Sprint 2 will test this design in practice; full extensibility
   acceptance is not yet claimed.

Storage uses a new `harness_runs` table with JSON report snapshots containing rule and
dataset versions, through the existing database and migration workflow. Unlike embedding
reports in chat TEXT, this preserves separate states and complete evidence. It is smaller
than a fully normalized event store, but future cross-run searches will need additional
indexes or structure. Lists return the latest 20 reports by creation time; individual
reports remain available by ID. `conversation_id` groups reports without cascading deletion
when a conversation is removed, preserving experimental evidence. There is no report
deletion control in the current UI.

## Running locally and independent acceptance

From the repository root, with environment dependencies already installed:

```bash
export UV_CACHE_DIR=/workspace/.cache/uv
export ANALYTICS_AGENT_CONFIG_DIR=/workspace/.analytics-agent
export DATAHUB_TELEMETRY_ENABLED=false
uv run --no-sync analytics-agent bootstrap
pnpm --dir frontend build
uv run --no-sync uvicorn analytics_agent.main:app --host 127.0.0.1 --port 8100
```

On your own computer, replace the two `/workspace` configuration paths with writable
local paths, or use the project's defaults. Open the running service in your local
browser. Without a configured model, dismiss the initial setup wizard and use the fixed
case that requires no model.

The independent reviewer should record the execution date, version, expected and actual
results, and any issues:

1. Expand “销售增长率验证 · Sprint 1”; submit a fixed-test claim of 10; expect passed.
2. Submit 18.7; expect failed, a computed value of 10.00%, and a test-injected label.
3. Submit 10.01 and 10.02; expect passed and failed, respectively.
4. Expand the evidence; check SQL and totals of 10000/11000 cents, and independently
   calculate `(110 - 100) / 100 * 100 = 10`.
5. Refresh and reopen the section; reports should remain. They should also survive a
   backend restart.
6. Run automated tests for zero denominators, missing evidence, negative amounts,
   cross-run references, and internal errors.
7. Use real-model mode only after configuring a service. Preserve generated claims and
   results; an unexecuted check must not be reported as passed.

```bash
.venv/bin/pytest tests/unit/test_harness.py -q
.venv/bin/pytest tests/unit tests/integration/test_mcp_transports.py -q
pnpm --dir frontend build
# Use an installed Chromium, or omit the variable for Playwright's installed browser.
HARNESS_CHROMIUM_PATH=/usr/bin/chromium pnpm --dir frontend exec playwright test --config ../tests/e2e/harness.config.ts
```

HTTP endpoints:

- `POST /api/harness/runs`: source, claimed_value, optional conversation_id.
- `GET /api/harness/runs`: optional conversation_id filter.
- `GET /api/harness/runs/{id}`: retrieve one report.

Clients do not supply evidence. Real-model mode ignores `claimed_value`. Database
persistence failures fail the request rather than being presented as a successful save.

## Evaluation contract and current evidence

This sprint evaluates classification, evidence association, and restoration on fixed
acceptance cases, not real-model error detection rates. Expected values come from the
independent calculations above and explicit test assertions, never from the validator
being tested. Automated coverage includes unit tests, the real SQL tool, HTTP endpoints,
restoration through a new database connection, and browser interaction.

A local model double tests Agent tool orchestration; it does not establish remote-model
accuracy. Execution results are reported in the project conversation. Independent
acceptance and remote-model testing remain outstanding.

The upstream `buildUiMessages.test.ts` USAGE association failure was already observed
during baseline setup. The frontend suite reproduced 44 passes and one failure; no test
was removed or its expectation changed to hide the failure.

## Technical debt, risks, and stop rules

| Item | Impact and treatment | Status |
|---|---|---|
| Query adapter uses an internal engine reference for cleanup | Upstream changes may require coordinated edits; introduce a consistent public lifecycle interface later | Design debt; team owner unassigned |
| Hard process interruption may leave a running report | Never counted as passed; displayed as incomplete. Add recovery or expiry reconciliation to limit future diagnosis costs | Reliability debt; team owner unassigned |
| JSON snapshots have no upgrade converter | Rule/data versions exist; incompatible schema changes will require compatibility migrations | Future compatibility risk |
| Model service is not configured | Continue deterministic tests; exclude real-model results from completed checks | External prerequisite awaiting user configuration |
| Upstream usage test failure | Track separately from validation; do not expand this change to conceal it | Known defect |

If structured model claims are unreliable, preserve an unverifiable outcome. If core
acceptance fails, fix it before adding UI features or rules. Batching, additional rules,
and automatic free-text extraction are future features, not automatically technical debt.

## Collaboration evidence boundaries

Work completed so far consists of AI-assisted implementation and automated testing.
No member meetings, hours, burndown data, or reviews have been fabricated. At the time
of this implementation handoff, no commit, push, or GitHub PR has been made. GitHub
collaboration follows the user's instructions after reviewing the code in chat.
The team must record actual owners, remaining estimates, weekly meetings, peer reviews,
and the Sprint retrospective as those activities occur.

---

# 中文版本：Sprint 1 销售增长率证据验证

## 已确认的范围

用户已在对话中确认本方案，并担任独立验收人；成员验收尚未执行。
基线提交：`90e34d49742852cd70b8ec506ba0ffaa1fe1bf90`。

作为 Agent 开发者，我希望在固定销售案例中查看声明与实际 SQL 结果是否一致，
并在不一致时找到查询和计算依据。这里的“通过”仅证明数值一致，不证明任意 SQL 的业务正确性。

- 单店铺 demo-store、CNY、完整自然年 2024 与 2025。
- 金额为人民币分的整数。固定记录为 4000+6000 与 5000+6000，即 100 元与 110 元。
- `(本期－上期)/上期×100`；上期必须大于零，本期可以为零；负金额不在本轮范围。
- 声明 `10` 的单位是 percent，表示 10%。容差为绝对误差 0.01 个百分点，含边界。
- Decimal 计算；判定通过交叉相乘避免循环小数边界误差；两位小数 ROUND_HALF_UP 仅用于展示。
- 缺失、零分母、单位/范围不符、截断、跨运行证据均为 unverifiable。
- 工具异常为 tool_error，与数值不符的 failed 分开。
- test_injected 与 agent_generated 分开标记，不能用注入错误证明真实模型错误率。

## 实现与复用

复用原有 SQLAlchemyQueryEngine 的 execute_sql 工具、模型配置 get_llm、FastAPI、
SQLite/Alembic、React 聊天页面及 SqlMessage 组件。

新增独立 harness 模块：数据契约、实际查询捕获、增长率纯函数、单案例执行和报告存储。
通过聊天页的“销售增长率验证 · Sprint 1”折叠区操作。普通聊天消息不自动被验证，
本轮采用固定案例入口，而非对任意分析结果进行抽取。

数据流：运行 → 原项目 SQL 工具 → Evidence(run_id, step_id) → Claim → 纯规则 → 持久报告 → React。

固定测试模式不调用模型；真实模型模式使用配置中的模型和一个受限 LangChain Agent，
只有 query_demo_sales 与 submit_growth_claim 两个工具。它不是原聊天图的全功能回归，
不使用 DataHub、图表或任意 SQL。模型不提交声明时返回 missing_claim，不代替模型生成答案。
查询返回值和 SQL 在执行时捕获，模型不能上传替代证据。最多保存两行固定聚合结果，
文本回答最多保存 8000 字符并标记截断；服务异常只保存安全错误码。

## 设计理由与非功能需求

1. 可靠性：执行状态与验证状态独立；查询/验证异常不能产生 passed；模型调用 60 秒超时、
   Agent recursion_limit=8。测试覆盖错误与超时。批量案例隔离在 Sprint 2 实现。
2. 可扩展性：验证纯函数只接收 Claim/Evidence，返回 ValidationResult，不访问模型或存储。
   当前只有一条规则；第二规则及注册机制待 Sprint 2 用实际变更检验，不声称已完成全部扩展性验收。

存储选择：新增 harness_runs 表，报告保存版本化 JSON 快照，复用现有数据库和迁移流程。
与将验证报告塞进普通聊天 TEXT 相比，可保留独立状态和完整证据；与完整关系化事件库相比，
本轮实现较小，但后续跨运行检索需扩展索引/结构。报告按创建时间取最近 20 条，单条仍可按 ID 读取。
conversation_id 仅用于归组；保留报告不随聊天删除而删除，以便实验追溯，界面当前无删除入口。

## 本地运行与独立验收

从仓库根目录（已有环境依赖）：

```bash
export UV_CACHE_DIR=/workspace/.cache/uv
export ANALYTICS_AGENT_CONFIG_DIR=/workspace/.analytics-agent
export DATAHUB_TELEMETRY_ENABLED=false
uv run --no-sync analytics-agent bootstrap
pnpm --dir frontend build
uv run --no-sync uvicorn analytics_agent.main:app --host 127.0.0.1 --port 8100
```

在自己的电脑中，将两个 `/workspace` 配置路径改为可写的本地目录，或者沿用项目默认配置。
启动后用本地浏览器访问服务。未配置模型时可关闭首次设置向导，使用无需模型的固定案例。

独立验收人请记录执行日期、版本、预期/实际结果和问题：

1. 展开“销售增长率验证 · Sprint 1”，固定测试输入 10，预期通过。
2. 输入 18.7，预期失败，计算值 10.00%，并显示“测试注入声明”。
3. 输入 10.01 与 10.02，分别预期通过和失败。
4. 展开证据，核对 SQL 与 10000/11000 分，手算 `(110－100)/100×100=10`。
5. 刷新页面，必要时重新展开折叠区，记录仍在。重启后端后也应恢复。
6. 运行自动测试，查看零分母、缺失证据、负值、跨运行引用与内部异常等用例。
7. 模型模式仅在实际配置服务后操作；保留生成声明及对应结果，未运行不能计为通过。

```bash
.venv/bin/pytest tests/unit/test_harness.py -q
.venv/bin/pytest tests/unit tests/integration/test_mcp_transports.py -q
pnpm --dir frontend build
# 使用已安装 Chromium；也可省略变量使用 Playwright 安装的浏览器
HARNESS_CHROMIUM_PATH=/usr/bin/chromium pnpm --dir frontend exec playwright test --config ../tests/e2e/harness.config.ts
```

HTTP 接口：POST /api/harness/runs（source、claimed_value、可选 conversation_id），
GET /api/harness/runs（可选 conversation_id），GET /api/harness/runs/{id}。
客户端不提供证据；真实模型模式忽略 claimed_value。数据库持久化失败会使请求失败，
不能显示为“保存成功”。

## 评测约定与当前证据

本轮衡量的是固定验收案例中的判定、关联与恢复正确性；不报告真实模型检出率。
标准答案来自上述手算与显式测试预期，不能调用验证函数产生预期值。
自动测试包括单元、真实 SQL 工具、HTTP API、新连接恢复及浏览器操作。
本地模型替身测试验证 Agent 工具编排，不等于远程模型准确性验证。

当前运行结果在本次聊天中报告；独立验收与远程模型测试仍待完成。
已有上游前端测试 buildUiMessages.test.ts 的 USAGE 归属失败在基线环境配置时已存在，
本次复现为 44 通过、1 失败；没有通过删除测试或改变预期掩盖它。

## 技术债、风险与停止规则

| 项目 | 影响/处理 | 状态 |
|---|---|---|
| 查询适配层使用现有引擎内部资源引用做清理 | 上游接口变动需同步调整；后续统一公开生命周期接口 | 设计债，待团队分配负责人 |
| 进程硬中断可能留下 running 报告 | 不会误记通过；目前显示未完成。后续加入任务恢复/过期状态协调，避免增加诊断成本 | 可靠性债，待团队分配负责人 |
| JSON 快照尚无升级转换器 | 本轮有规则/数据版本；新增不兼容字段时需要兼容迁移 | 未来兼容风险 |
| 模型服务未配置 | 固定测试继续；真实模型结果不计入完成项 | 外部前提待用户配置 |
| 上游 usage 测试失败 | 与新增验证无关，独立记录，不借本轮扩大修改范围 | 已知缺陷 |

若模型无法稳定提交结构化声明，保留无法验证状态；若核心验收失败，先修复再增加界面或规则。
批量、多规则、自动自然语言提取为后续功能，不把它们伪装成技术债。

## 协作记录边界

本次已完成的是 AI 协助实现和自动测试。没有替成员创建已完成的会议、工时、燃尽数据或评审。
没有提交/推送，也没有创建 GitHub PR。用户检查聊天中的代码后，再按其指示进入 GitHub 协作。
实际任务负责人、剩余工时、每周会议、PR 同伴评审和 Sprint 回顾由团队按真实活动补充。
