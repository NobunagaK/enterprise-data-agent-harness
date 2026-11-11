# Sprint 2 F2: sales evidence verification

This increment implements the F2 extension agreed in `docs/sprint2.md`. It does
not mark the whole Sprint 2 accepted. Baseline: `main@67153cd`.

## Executable scope and acceptance

Both rules use the fixed synthetic `sales-v1` data and the application's real
SQLAlchemy SQL tool. No arbitrary SQL, uploaded database, free-text extraction,
or ordinary-chat answer validation is introduced.

| Rule | Scope | Unit / tolerance | Acceptance examples |
|---|---|---|---|
| `growth_rate` | demo-store, 2024 → 2025 | percent / inclusive 0.01 percentage points | 10 and 10.01 pass; 18.7 fails; zero denominator is unverifiable |
| `sales_total` | demo-store, 2025 | integer CNY cents / exactly 0 cents | 11000 passes; 11001 fails; 11000.1 is unverifiable |

The total query computes `SUM(amount_cents)` over the two 2025 records (5000 and
6000 cents). Evidence must match the run, reference, dataset, store, year and
currency and be untruncated and unambiguous. Missing amounts, unsupported scope,
negative sales evidence and fractional cents are unverifiable. Engine type drift
and execution exceptions are tool errors. A negative integral **claim** can be
compared and fails against a nonnegative total; negative sales **evidence** is
outside the supported business scope. Decimal scientific notation is accepted
when it denotes an integral cent amount. Claims remain strings, are limited to
64 characters and finite magnitudes up to 1e20. No automatic yuan/cent conversion
or rounding of fractional-cent claims occurs.

Growth keeps its formula and inclusive tolerance. Comparison precision is now
100 decimal digits, sufficient for the 64-character claim and SQLite integer
amounts. A reproduced main-branch defect accepted
`10.010000000000000000000000000000000000000000000000000000000001`;
the new regression correctly fails it. Display rounding never decides acceptance.

## HTTP and Python contract

`POST /api/harness/runs` accepts a union discriminated by `rule_id`. Missing
`rule_id` still selects growth, so `{ "claimed_value": "10.01" }` remains valid.
Unknown rules, incompatible parameters/units, JSON numeric claims, custom SQL,
custom tolerance and expected outcomes are rejected with HTTP 422 before execution.

```json
{
  "rule_id": "sales_total",
  "case_id": "total-off-by-one",
  "dataset_version": "sales-v1",
  "source": "test_injected",
  "claimed_value": "11001",
  "unit": "CNY_cent",
  "parameters": { "store_id": "demo-store", "year": 2025 }
}
```

Python callers now construct `GrowthRunRequest(...)` or
`SalesTotalRunRequest(...)`, or parse JSON with
`RUN_REQUEST.validate_python(payload)`. `RunRequest` is the union type annotation,
not a callable model class. All repository callers are migrated. HTTP growth
requests and the frontend `createHarnessRun(...)` wrapper remain compatible.
Requests and their nested parameters remain frozen; session ownership is unchanged.

Totals add `Claim.year=2025`; growth snapshots omit the absent field. Existing
completed snapshots are read without rewriting their stored JSON. New reports
continue using schema version 2. Total results always use `sales_total-v1`,
`CNY_cent`, tolerance `"0"`, and null percentage aliases, including missing claims,
query/model/validator errors, timeout and stale-running reconciliation.

## Implementation and integration

- `harness/rules.py` describes the SQL, units, fixed claim scope, model question,
  tool name and pure validator for each rule. The runner executes this definition.
- `harness/validation.py` owns numerical checks and common amount parsing; it
  performs no I/O. `rule_result` creates rule-aware outcome metadata.
- `contracts.py` and `frontend/src/api/harness.ts` expose rule-specific requests.
- `cases.py` accepts growth and total case definitions. The existing
  `CaseDefinition(...)` growth constructor is preserved. Mixed-rule integration
  tests run through existing `batch.run_batch` without changing its orchestration
  or aggregation logic; only its type annotations change. Expected outcomes are
  kept in evaluation data and never forwarded to the model.
- Persistence schema and save/CAS logic are unchanged. Stale-report reconciliation
  uses `rule_result` so an interrupted total never becomes a percentage result.
- The existing React panel becomes **销售证据验证 · Sprint 2** and offers both rules.
  SQL, evidence, source labels and persisted history remain visible.

The bundled F4 set `sprint2-sales-v1` remains the original ten growth cases. This
PR supplies the mixed-rule contract and regression evidence; publishing/selecting
an expanded bundled mixed-rule set remains F4 follow-up. F3 trace PRs must retain
this rule dispatch when integrating their runner changes. No human review or
approval is inferred from automated tests.

## Verification performed for this increment

Local Linux / Python 3.12 / system Chromium:

| Check | Result |
|---|---|
| Harness regression, including 71 new F2 cases | 158 passed |
| `pytest tests/unit tests/integration/test_mcp_transports.py -q` | 512 passed (506 unit, 6 integration) |
| `pnpm --dir frontend test` | 62 passed |
| `pnpm --dir frontend build` | passed |
| Ruff lint and formatting; mypy | passed; 108 formatted files / 77 typed source files |
| `pnpm --dir frontend lint` | no errors; 7 existing warnings |
| Full Playwright suite using `HARNESS_CHROMIUM_PATH=/usr/bin/chromium` | 38 passed |

The new browser scenario exercises total pass, one-cent failure, fractional-cent
unverifiable, actual SQL, history reload and return to growth. Backend tests also
cover wrong/cross-run/duplicate evidence, missing/invalid data, unit and period
mismatch, exact large integers, model/SQL/validator errors, stale results, mixed
batches and legacy snapshots. Windows CI includes the new test module; remote
results must be read on this PR, not inferred from the local run.

Configured-provider total execution is wired through the existing LLM adapter,
with `query_demo_sales` and `submit_total_claim`. Local model doubles verify tool
orchestration and ensure injected values are ignored in `agent_generated` mode.
No live provider call or native Windows full-stack acceptance is claimed.

Remaining Sprint 2 code integration must be completed before the final document
pass. At that point, remind the team to complete the Sprint 2 requirements/design,
test evidence, remaining debt/risks and completion summary using actual records.
The final demonstration video is prepared after the demonstration version passes
acceptance. No meetings, contributions or approvals are fabricated.

---

# 中文版本：Sprint 2 功能②销售证据验证

本增量实现 `docs/sprint2.md` 约定的功能②扩展，基线为 `main@67153cd`，不代表整个 Sprint 2 已验收。

## 范围与判定

保留固定 `sales-v1` 合成数据和应用真实 SQL 工具，不增加任意 SQL、任意聊天验证或自由文本提取。

- `growth_rate`：demo-store，2024→2025；Decimal 计算，0.01 个百分点容差，包含边界。
- `sales_total`：demo-store，2025 年；SQL 对 5000 分和 6000 分求和，得到 11000 分；零分容差。
- 总额声明 11000 通过、11001 失败、11000.1 无法验证；不自动换算元/分，不将小数分舍入为整数。
- 证据必须匹配运行、引用、数据版本、门店、年份和币种；截断、缺失、歧义或不支持的业务数据无法验证。
- 引擎类型异常、SQL/模型/验证器执行异常单独返回工具错误。负数整数声明可比较并判失败；负销售额证据超出支持范围。
- 声明保持字符串，最多 64 字符、有限且绝对值不超过 1e20；科学计数法表达整数分时可比较。

已复现原增长率实现会把略超上边界的长小数字符串误判通过。比较精度提升至 100 位并增加回归，
原公式、包含边界的容差和独立展示舍入均保留。

## 接口与兼容

请求按 `rule_id` 区分联合类型，缺省仍为增长率。英文部分给出了可直接使用的总额 JSON 请求。
规则与单位/参数不匹配、数字型 JSON 声明、未知规则、自定义 SQL/容差/预期结果，在执行前返回 422。

Python 调用改用 `GrowthRunRequest(...)`、`SalesTotalRunRequest(...)` 或
`RUN_REQUEST.validate_python(payload)`；`RunRequest` 现在是类型注解，不能再当作类构造。
仓库内调用点已更新。原 HTTP 请求、前端三参数封装、不可变参数和专用 session 约定保持兼容。

总额声明增加 `year=2025`；增长率不输出空的 year 字段。已完成旧快照读取不改写原 JSON，
新报告继续使用 schema version 2。总额的正常、无法验证、工具错误、超时和过期报告都使用
`sales_total-v1`、`CNY_cent`、零容差，百分点别名为空。

## 代码与接入

`rules.py` 描述规则 SQL、单位、声明范围、模型任务和验证函数；`validation.py` 负责纯数值判定。
现有 React 面板更新为“销售证据验证 · Sprint 2”，可以切换增长率与总额。

案例契约已支持混合规则，测试通过现有批次入口执行，批次编排与统计算法未改，只扩展类型注解。
存储表结构、保存及并发更新逻辑未改，过期报告改用按规则生成结果的函数，避免金额被误标为百分比。

原内置批次仍为十个增长率案例；发布、选择新版混合案例集属于功能④后续接入。
功能③合并时需要保留本次 runner 的规则分派。自动测试不代表人工评审或批准。

## 本次验证与剩余工作

本地 Linux：Harness 158 项通过（新增功能② 71 项）；后端单元与 MCP 集成共 512 项通过；
前端 62 项通过；完整浏览器测试 38 项通过；构建、Ruff、mypy 通过，前端 lint 无错误、保留 7 条原有警告。
浏览器验证了总额通过、差一分失败、小数分无法验证、真实 SQL、刷新后历史保留和切回增长率。
Windows CI 已加入新测试文件，实际远程结果以 PR 为准。

真实模型入口已接入现有适配器，模型替身验证了工具编排和忽略测试注入值的行为；未宣称真实供应商调用、
Windows 整套实机验收已完成。

按当前协作要求，先完成剩余 Sprint 2 代码集成，再提醒团队补齐本轮需求设计、测试证据、技术债/风险及
完成总结。文档只采用真实记录，不补造会议、贡献或批准。演示版本验收通过后再制作正式视频。
