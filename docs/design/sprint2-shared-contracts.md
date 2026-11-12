# Sprint 2 shared contracts

Status: implementation proposal for peer review, not a completed Sprint 2 acceptance.
Base: `main@8359a46827f48936a2e110e939061bff78f11e6f`.
Owner: Zefeng Chen. Reviewers: Haoyu Shen and Zikai He;
this names the requested review roles, not recorded approvals.

## 1. Scope and ownership

This increment exposes the existing single-case workflow to both HTTP and future
batch callers. It establishes report versioning, unit-aware result fields and
nullable trace metadata. It does not implement sales-total execution, additional
datasets, batch scheduling, complete trace collection, retry/resume, or arbitrary
chat/SQL verification. No database migration or dependency change is required.

| Owner | Next feature | Shared boundary |
|---|---|---|
| Zefeng | F2: additional rules and explanations | `Claim`, `Evidence`, `ValidationResult`; existing pure signature `validate_growth(run_id, claim, evidence)` |
| Haoyu | F3: actual execution events and trace UI | `Run.steps`, `Step`, `TokenUsage`, `Evidence.step_id` |
| Zikai | F4: case loading, batch execution, storage and UI | `RunRequest`, `service.run_case`, `Run.case_id`, individual report retrieval |

Do not copy validation logic into the batch module. Do not add batch aggregation
to the runner. Changes to shared fields require a focused PR reviewed by both
other developers. Feature branches start from main after this PR is merged.

### F2/F4 integration order

The first F4 increment supports `growth_rate` cases only. Mixed-rule batches are
a later increment, not a capability of this shared-contract baseline. Zefeng must
first implement and test F2's `sales_total` execution and extend `RunRequest` to a
union discriminated by `rule_id`, with rule-specific parameters and units. Both
Haoyu and Zikai review that shared-field change before integration. Zikai then
adds mixed-rule case definitions and batch regression tests against the accepted
contract, without copying formulas into batch orchestration. Existing growth
requests and legacy report reads must remain compatible. See the sequencing and
acceptance requirements in [the Sprint 2 integration plan](../sprint2.md).

## 2. Supported input contract

`harness/contracts.py` is the Python input authority. HTTP accepts the same
`RunRequest` at `POST /api/harness/runs`. `frontend/src/api/harness.ts` mirrors its
wire format. Pydantic exposes it in FastAPI's OpenAPI schema.

```json
{
  "source": "test_injected",
  "claimed_value": "10.01",
  "conversation_id": null,
  "case_id": "sales-growth-boundary",
  "rule_id": "growth_rate",
  "dataset_version": "sales-v1",
  "unit": "percent",
  "parameters": {
    "store_id": "demo-store",
    "previous_year": 2024,
    "current_year": 2025
  }
}
```

All fields have defaults; the original `{ "claimed_value": "10.01" } remains valid.
An absent case ID is null. A supplied case ID is a nonempty string of at most 128
characters. It identifies a case definition, not an execution: reruns get new run
IDs. A batch will own its own batch-to-run mapping; `case_id` is not a batch ID.

Supported selectors are deliberately restricted to the example's rule, dataset,
unit and scope. Other rules (including `sales_total`), datasets, scope values,
unknown top-level/nested fields and numerical JSON claims return HTTP 422 before
creating a run. This intentionally tightens the old API's silent extra-field
ignoring. Extend selectors only alongside working implementations and tests.
There is no arbitrary file path, SQL, expected answer or timeout override in this
request. Golden answers belong in independent evaluation data, not model inputs.

`claimed_value` remains a string of at most 64 characters. Malformed numerical
strings still reach the verifier and produce `unverifiable`; no float coercion is
introduced. In `agent_generated` mode this injected-value field is ignored, as in
Sprint 1: only an actually submitted model claim is evaluated.

## 3. Shared execution boundary

```python
from analytics_agent.harness.contracts import RunRequest
from analytics_agent.harness.service import run_case

# Caller supplies a dedicated AsyncSession, separate from unrelated transactions.
report = await run_case(
    RunRequest(case_id="sales-growth-boundary", claimed_value="10.01"),
    session,
)
```

`run_case(request, session) -> Run` checks conversation existence, creates a fresh
version-2 report, commits its initial snapshot, delegates to the existing runner,
and commits the final snapshot. It commits the supplied session, so do not share
that session with unrelated pending writes or concurrent cases. Batch callers use one
new session per case, including sequential cases. Optional keyword-only
`on_persisted(run_id)` is a synchronous notification immediately after the initial
commit, so callers can retain the confirmed report identity if execution later
times out or final persistence fails. It is not a completion notification and
must not perform I/O. Failed initial persistence does not emit a notification. Internal callers
must construct a validated `RunRequest`, not bypass validation with
`model_construct`/unchecked copies. Request objects and their parameters are frozen.

**One case, one session:** F4 must create and close a dedicated `AsyncSession` for
each case, including sequential cases. Never reuse one session across an entire
batch, share it between concurrent cases, or mix it with batch-summary writes.
`run_case` owns its initial/final snapshot commits; the caller owns session
lifetime and cleanup on success, failure and cancellation. Perform any batch
conversation preflight in a short-lived session and release it before running
cases. A case failure must not roll back earlier committed reports. F4 regression
evidence must show that, when a middle case fails or times out after its initial
save, earlier completed reports remain readable and a later case can complete
and persist using a fresh session. Final-save failure must not be reported as a
successfully persisted final report. These are batch acceptance requirements,
not claims that PR #14 implements or has verified batch continuation.

- Missing conversation: `ConversationNotFound`; HTTP translates it to 404.
- Query/model/validator execution failure: existing runner produces `tool_error`.
- Cancellation or persistence failure: propagates to the caller. A final-save
  failure is not a successful persisted report. The initial snapshot may remain.
- HTTP execution is synchronous with the request and returns 201 after final save.
  No background queue, automatic restart or client-disconnect guarantee is added.
- The existing 60-second model timeout remains; a general case timeout and actual
  worker/resource cancellation are F4/F3 follow-up work. Wrapping a thread in
  `asyncio.wait_for` alone does not stop that thread.
- Existing stale-report reconciliation remains unchanged: old running snapshots
  may become `tool_error/stale_running` after 300 seconds when read. Do not create
  queued cases as running or assume this is a recovery mechanism.

`GET /api/harness/runs/{id}` returns one report. The existing list route still
returns at most 20 reports for the selected conversation; it is not an exhaustive
batch query. F4 must store each batch's run IDs and use direct report lookup.

## 4. Identity and state semantics

| Field | Meaning |
|---|---|
| `Run.id` | Unique execution identity; never the case definition ID |
| `Run.case_id` | Optional case definition identity, carried through persistence |
| `Run.rule_id` | Stable rule selector; distinct from implementation `rule_version` |
| `Run.dataset_version` | Dataset version selected for this execution |
| `Evidence.run_id` | Execution that captured the evidence |
| `Evidence.step_id` | Query step that produced the evidence |
| `Claim.evidence_id` | Evidence referenced by this claim |
| `Step.parent_step_id` | Optional enclosing step in the same run, for future instrumentation |

Step IDs are scoped by their containing run; no second trace array is introduced.
Producers must preserve these links. A failed query has a failed step, not fabricated
query evidence. Missing/foreign claim evidence remains a verifier outcome rather
than a request validation failure.

Execution states are `running`, `completed`, `error`. Validation outcomes are
`passed`, `failed`, `unverifiable`, `tool_error`. **Completed does not mean passed.**
A completed numerical check can yield failed or unverifiable. Do not derive
business counts from execution state. A null result is unfinished, never passed.
Batch-level pending/interrupted states and persistence are owned by F4, not added
to the single-run state enum in this change.

## 5. Numerical result and compatibility

Money remains integer CNY cents; calculations remain Decimal. Growth comparison
still uses cross-multiplication with inclusive **0.01 percentage-point** tolerance.
Display rounding never determines pass/fail. The original formula is unchanged.

`ValidationResult` adds `unit`, `tolerance`, `difference` while retaining existing
expected/claimed value fields. All numerical values are decimal strings.

| Result unit | Value meaning | Tolerance/difference meaning | Legacy aliases |
|---|---|---|---|
| `percent` | Percentage value, e.g. `10` means 10% | Percentage points | `tolerance_pp` and `difference_pp` mirror generic fields |
| `CNY_cent` | Integer cents | Cents | Both `_pp` fields must be null |

On reading old results, unit defaults to percent and generic fields are derived
from legacy fields. Growth tolerance defaults to `0.01`. Conflicting aliases are
rejected; writers should use the same decimal-string representation. Tolerance
and difference must be finite and nonnegative. Amount results must explicitly
supply their tolerance and a non-growth rule version; they cannot inherit growth
percentage aliases. Sales-total *result representation* is reserved and tested;
the request still rejects sales-total execution. Integer-cent arithmetic and the
proposed exact amount tolerance of `0` must be implemented/tested in F2.

Report `schema_version` describes report shape, independently of rule/data versions.
A missing schema version reads as 1; new application-service reports use 2. Versions
other than 1/2 are rejected. Reading a completed legacy report adds defaults in
memory/API output but does not rewrite its stored JSON. This is additive semantic
compatibility, not byte-identical API responses. Existing stale reconciliation
still writes a terminal report when appropriate. No bulk migration is performed.

The React card renders result units and unavailable timing correctly. The old
`createHarnessRun(conversationId, source, claimedValue)` wrapper remains available;
new callers use `submitHarnessRun(request)` and `getHarnessRun(runId)`.

## 6. Trace structure, not a claim of full instrumentation

`Step.kind`: query, claim, validation, model, tool, answer, context.
`Step.status`: running, completed, error, skipped. The completed default is retained
for old snapshots; future producers must explicitly start live steps as running.
`duration_ms`, `started_at`, `finished_at`, `parent_step_id`, `token_usage` can be
null. Durations, if provided, must be finite and nonnegative. Token counts must be
nonnegative integers; absent provider counts remain null, not a fabricated zero.
Use actual timestamps and a monotonic clock for elapsed time. Old measured values,
including old zero values, are preserved, not retrospectively reinterpreted.

Current query/validation durations continue to be measured. Additional event
collection, nesting/timestamp consistency and trace UI are Haoyu's follow-up work.
Record only observable events/output, not hidden model reasoning. Do not invent
context retrieval, retries or token counts. Errors must use safe codes, not raw
credential-bearing exception text. Existing source labels remain unchanged;
local model doubles prove orchestration only, not real-provider acceptance.

## 7. Quality requirements and acceptance boundaries

- **NFR-01 Reliability:** future batches continue after an individual case failure
  and retain completed reports. The shared service separates per-run state and
  propagates storage/cancellation failures honestly. Batch continuation and hard
  timeout cleanup are not yet accepted by this PR.
- **NFR-02 Modifiability:** after this boundary is in place, adding total verification
  must not change batch orchestration or report-storage core logic. A small shared
  contract reduces coupling; limited abstractions avoid a premature plugin framework.
  The second-rule extension is the future acceptance evidence, not claimed done here.

Required checks: original Harness regressions; HTTP/service identity and persistence;
unsupported input rejection; old snapshot read without rewrite; cancellation/final-save
failure semantics; unit-aware rendering; unknown metric display; lint/type/build;
existing real-SQL browser flow. The legacy JSON fixture is synthetic compatibility
data, not a fabricated historical human acceptance record.

Review questions: Haoyu checks event/identity/error requirements; Zikai checks calling,
case identity, aggregation semantics and persistence boundaries. Human approval,
Windows rerun and real-model acceptance must not be inferred from local Linux tests.
Existing Issues #11 and #12 remain separate. No auto-merge is authorized by this plan.

---

# 中文版本：Sprint 2 共同接口

状态：已实现并提交评审的接口提案，不代表 Sprint 2 已验收。
基线：`main@8359a46827f48936a2e110e939061bff78f11e6f`。
负责人：Zefeng Chen；评审角色：Haoyu Shen、Zikai He。
角色安排不代表两人已经批准或完成评审。

## 1. 范围与分工

本次复用已有单案例流程，提供 HTTP 与未来批次共用的入口、报告版本、数值单位及可为空的轨迹字段。
不实现总额算法、新数据集、批次调度、完整轨迹采集、重试恢复或任意聊天/SQL验证；不改依赖，不增加数据库迁移。

- Zefeng：功能②，使用 Claim、Evidence、ValidationResult；现有纯验证函数签名为
  `validate_growth(run_id, claim, evidence)`，后续据此扩展规则。
- Haoyu：功能③，在 Run.steps / Step / TokenUsage 中记录实际事件，通过 Evidence.step_id 关联证据。
- Zikai：功能④，构造 RunRequest，调用 service.run_case，保存批次与运行编号的关联。

批次模块不复制验证公式，runner 不处理批次汇总。共同字段变更通过小 PR，由另外两人评审。
本 PR 合并后，各自从更新后的 main 开发。

### 功能②/④接入顺序

功能④第一版只支持 `growth_rate` 案例；混合规则批次属于后续增量，不是当前共同接口已具备的能力。
先由 Zefeng 实现并测试功能②的 `sales_total` 执行，将 `RunRequest` 扩展为以 `rule_id` 区分的联合类型，
分别约束各规则的参数和单位。共同字段变更先由 Haoyu、Zikai 两人评审，再进行集成。
之后由 Zikai 按已接受的契约补充混合规则案例定义和批次回归测试，不在批次编排中复制验证公式。
原有增长率请求和旧报告读取必须保持兼容。顺序及验收要求见 [Sprint 2 接入计划](../sprint2.md)。

## 2. 输入与调用方式

Python 输入定义位于 `harness/contracts.py`，前端类型位于 `frontend/src/api/harness.ts`。
英文部分的 JSON 是可执行请求示例，也可在 FastAPI OpenAPI 中查看。

所有字段有默认值，原请求 `{"claimed_value":"10.01"}` 继续有效。
case_id 可不传；传入时为 1–128 字符的案例定义编号。重复运行同一案例会得到不同 run.id；
case_id 不是批次编号，批次关联由 Zikai 单独保存。

当前仅执行 growth_rate、sales-v1、percent、demo-store、2024→2025。
其他规则（包括 sales_total）、数据集、范围、未知字段及 JSON 数值型声明在执行前返回 HTTP 422。
这是有意收紧旧接口“忽略额外字段”的行为，防止参数未生效却得到看似成功的报告。
新能力应与实现和测试一起开放。不接受任意路径、SQL、预期答案或超时覆盖参数。
预期答案保留在独立评测数据里，不传给模型。

claimed_value 是最多 64 字符的字符串。错误数值字符串仍进入验证器，得到 unverifiable，
不先转换为浮点数。在 agent_generated 模式中，此注入值与原来一样被忽略，只验证实际模型提交的声明。

统一入口为 `await run_case(RunRequest(...), session)`：检查会话、创建版本 2 报告、保存初态、
调用已有 runner、保存终态并返回。该函数会提交 session，调用者必须提供专用 session，
不要与其他待提交业务或并发案例共用；批次即使顺序执行，也必须每个案例新建一个 session。
可选关键字参数 on_persisted(run_id) 在初始提交成功后同步通知运行编号，供调用者在后续超时或
终态保存失败时保留关联。它不是完成通知，不能执行 I/O；初始保存失败不发送通知。
内部调用者必须正常构造已验证的 RunRequest，不能绕过验证。
请求及嵌套参数不可原地修改。

**每个案例一个 session：**功能④必须为每个案例创建并关闭专用 `AsyncSession`，串行案例也不例外。
不能整批复用一个 session，不能在并发案例间共享，也不能混入批次汇总写入。
`run_case` 负责初态/终态快照的提交；调用者负责 session 的生命周期及成功、失败、取消时的清理。
批次会话存在性预检查应使用短生命周期 session，并在执行案例前释放。
单个案例失败不得回滚前序已提交报告。功能④回归证据必须证明：中间案例在初态保存后失败或超时，
前序已完成报告仍可读取，后续案例仍能使用新的 session 完成并持久化。
终态保存失败不能报告为已成功保存终态。这些是批次验收要求，不代表 PR #14 已实现或验证批次继续执行。

- 会话不存在：服务抛 ConversationNotFound，HTTP 转为 404。
- SQL、模型或验证执行异常：已有 runner 返回 tool_error 报告。
- 取消、存储故障：继续抛给调用方，不能假称成功保存；可能只留下初态。
- HTTP 仍在请求中完成执行，最终保存后返回 201，不新增后台队列、自动恢复或断线执行保证。
- 原有模型 60 秒限制保留；通用案例超时和工作线程清理由功能④/③继续实现。
  单纯 asyncio.wait_for 不会停止底层工作线程。
- 原有运行超过 300 秒后读取时惰性标记 stale_running 的行为不变，不等于恢复机制。
  排队中的案例不能提前标记成 running。

单报告使用 GET /api/harness/runs/{id}。原列表接口每个会话最多返回 20 条，不可当作完整批次查询。
批次必须保存自己的运行编号集合，再读取对应详情。

## 3. 关联与状态

run.id 是执行编号；case_id 是案例定义编号；rule_id 是稳定规则标识，rule_version 是算法版本。
Run.dataset_version 标识实际数据版本。Evidence.run_id 指向所属运行，Evidence.step_id 指向查询步骤，
Claim.evidence_id 指向声明引用的证据。Step.parent_step_id 可指向同一运行内的父步骤。
步骤位于所属 Run.steps 内，不再创建第二套轨迹数组。

生产这些记录的代码必须维护关联。SQL 失败只记录失败步骤，不能伪造查询结果。
引用缺失或其他运行的证据由验证器分类，保留原有行为。

执行状态 running / completed / error，与验证结果 passed / failed / unverifiable / tool_error 分开。
**completed 只表示执行完成，不代表声明通过。** result 为 null 表示未完成，不能计为通过。
批次的 pending / interrupted 等状态由功能④另行定义，不在本次扩充单次运行状态。

## 4. 数值与旧报告兼容

人民币分、Decimal、交叉相乘比较、包含边界的 0.01 个百分点容差均不变，展示舍入不参与通过判断。
结果新增 unit / tolerance / difference，原 expected_value、expected_display、claimed_value 保留，
数值字段采用十进制字符串。

- percent：数值是百分比；容差与差值是百分点；原 tolerance_pp / difference_pp 与通用字段一致。
- CNY_cent：数值、容差与差值均以分计；两个 _pp 字段必须为 null，且显式提供非增长率规则版本及容差。

读取旧结果时默认 percent，并从旧字段补齐新字段；增长率容差默认 0.01。
两个字段表达冲突会拒绝，写入方应使用相同的十进制字符串表示。容差与差值必须有限且非负。
总额结果结构及展示已预留和测试，但总额执行仍被拒绝；整数分计算与建议的零容差需在功能②实现和验证。

报告 schema_version 与数据、算法版本不同。缺失时按版本 1 读取，新服务生成版本 2，其他版本拒绝。
读取已完成旧报告只在内存和 API 响应补默认字段，不改写原始存储 JSON；这是语义兼容，
不是 API 响应逐字节相同。原有过期协调仍可能写入终态；不进行批量迁移。

原 createHarnessRun 三参数前端函数保留，新调用方可用 submitHarnessRun(request)、getHarnessRun(runId)。
结果卡片按单位显示，耗时缺失时显示“耗时未记录”。

## 5. 轨迹约定

步骤类型：query / claim / validation / model / tool / answer / context。
步骤状态：running / completed / error / skipped。为兼容旧记录保留 completed 默认值；
新采集器必须显式将执行中步骤设为 running。

duration_ms、started_at、finished_at、parent_step_id、token_usage 可为空。
有耗时时必须有限且非负；Token 数必须为非负整数，供应商不提供时为空，不能补零。
时间戳记录实际时间，耗时使用单调时钟。旧记录中已有的数值（包括零）保留，不追溯改写。

本次保留已有查询/验证耗时，其他事件采集、嵌套及时间一致性、轨迹页面由 Haoyu 实现。
只记录可观察事件与输出，不记录或伪造隐藏模型推理、上下文检索、重试和 Token。
错误使用安全码，不保存可能含凭据的原始异常。来源标签保留；模型替身只证明编排，不代表真实模型验收。

## 6. 非功能需求与评审

NFR-01 可靠性：未来批次应隔离单例错误并保存已完成报告。本次入口隔离单次状态，如实传递取消和保存故障；
批次继续执行及硬超时清理仍是后续验收项。

NFR-02 可修改性：接口建立后，增加总额规则不应修改批次编排和存储核心。
采用小型共享接口减少耦合，同时避免过早引入复杂插件框架；第二条规则的实际接入才是验收证据，不能提前宣称完成。

检查范围：原 Harness 回归、服务/API 关联与存储、拒绝未实现请求、旧快照读取不改写、取消及保存失败、
单位展示、未知指标、静态检查/类型/构建、已有真实 SQL 浏览器流程。
旧 JSON 测试样本是合成兼容数据，不是补造历史人工验收。

Haoyu 重点评审事件、关联和错误；Zikai 重点评审调用、案例编号、汇总语义和持久化边界。
Linux 自动测试不代表人工批准、Windows 复测或真实模型验收。Issues #11、#12 继续独立跟踪。
本次不自动合并。
