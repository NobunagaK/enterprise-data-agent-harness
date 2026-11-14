# Sprint 2 F4: selectable mixed-rule cases

This increment completes the mixed-rule case-set follow-up in
[the F2 design](sprint2-verification-f2.md). The batch service continues to call
the shared single-run service, which executes the existing fixed SQL and
validates captured evidence. The numerical formulas and units are unchanged.

## Bundled cases and selection

| Case set | Cases | Rules | Expected summary |
|---|---:|---|---|
| `sprint2-sales-v1`, version `1` | 10 | `growth_rate` | 2 passed, 4 failed, 4 unverifiable |
| `sprint2-sales-mixed-v1`, version `1` | 8 | `growth_rate`, `sales_total` | 3 passed, 2 failed, 3 unverifiable |

Both sets use `sales-v1` and fixed `test_injected` claims. The original set and
the default POST request remain unchanged. The mixed set includes the inclusive
0.01 percentage-point growth boundary, an out-of-tolerance growth value, a total
of 11000 CNY cents, a one-cent discrepancy, fractional cents and malformed
claims. Amounts remain integral CNY cents; validation uses the existing Decimal
rules. `expected_status` remains evaluation metadata and never enters a run
request or the model input.

`GET /api/harness/batches/case-sets` returns validated selection metadata:
`case_set_id`, `version`, `dataset_version`, `case_count`, `rule_ids`, `sources`.
It reads bundled JSON files without executing cases or writing to the database;
it does not return claims or evaluation labels. Register this route before
`/{batch_id}`. The existing POST accepts the selected `case_set_id`.

The React batch panel loads this catalog, defaults to the original set and
shows the rule names, case count and claim source. Its run button is disabled
until a valid selection is available. A catalog error leaves persisted history
accessible. Each displayed batch retains its own case-set ID/version even when
the input selection changes. Individual reports reuse the existing result card
and execution trace, including SQL and evidence links.

## Verification and acceptance boundaries

`tests/unit/test_harness_mixed_cases.py` checks discovery without execution,
actual SQL execution through the API, distinct persisted run/evidence identities,
rule-specific units, expected-result matching, and batch retrieval. A controlled
middle-case SQL failure must produce `tool_error`, preserve earlier reports and
allow later cases to finish. A completed batch means all cases produced outcomes;
it does not mean that every numerical claim passed.

`tests/e2e/harness-batch.spec.ts` exercises the original default, mixed selection,
summary counts, a failed total's SQL/evidence trace, page-reload persistence,
and history access during a catalog error. Execution results are recorded on the
PR after checks finish. These fixed-case checks do not establish live-provider
acceptance or a native Windows full-application demonstration.

---

# 中文版本：Sprint 2 功能④混合案例集选择

本增量完成[功能②设计](sprint2-verification-f2.md)中约定的混合案例集接入。
批次继续调用共同单次运行服务，执行现有固定 SQL、捕获证据并验证，不改变数值公式及单位。

原 `sprint2-sales-v1` 的 10 条增长率案例和默认请求保持兼容，预期为 2 通过、4 失败、4 无法验证。
新增 `sprint2-sales-mixed-v1`，版本为 `1`，包含 8 条增长率/销售总额案例，
预期为 3 通过、2 失败、3 无法验证。两组均使用 `sales-v1` 数据和固定测试声明，
不是实际模型生成的输出。案例覆盖增长率 0.01 个百分点的包含边界、边界外数值、
11000 分总额、一分钱误差、非整数分及格式错误；继续以人民币分保存金额、使用 Decimal 计算。
`expected_status` 仅用于评测，不进入运行请求或模型输入。

新增 `GET /api/harness/batches/case-sets` 返回案例集编号、版本、数据版本、条数、规则及来源。
读取目录不执行案例、不写数据库、不返回声明或预期标签；路由位于 `/{batch_id}` 之前。
React 批次面板从该接口加载选择项，默认选中原案例集；有效选项加载后才允许运行。
界面明确显示固定测试声明来源；目录加载失败时仍可查看已保存的历史。
切换下一次运行的选项不会改写当前报告的案例集编号或版本。
失败案例沿用现有结果卡片与执行轨迹，能够查看 SQL 和关联证据。

后端专项测试覆盖真实 SQL、汇总、独立运行/证据编号、规则单位、持久化及读取，
并模拟中间一次 SQL 错误，检查工具错误被单独统计、前序报告保留、后续案例继续执行。
批次“已完成”表示各案例已产生结果，不等于所有声明都通过验证。
浏览器测试覆盖原默认集、混合选择、失败总额的 SQL/证据、刷新后恢复及目录失败时读取历史。
实际执行结果在检查完成后记录于 PR；这些检查不代表真实模型或 Windows 完整应用演示验收。
