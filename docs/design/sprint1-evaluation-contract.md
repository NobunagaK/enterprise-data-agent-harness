# Sprint 1 evaluation contract

Decision date: 2026-11-03 (Asia/Shanghai). The repository owner reaffirmed the numerical contract and authorized fixing the review findings, acceptance and merge. This records that instruction, not a team meeting or peer approval.

- Scope: demo-store, CNY integer cents, 2024/2025, actual fixed SQL, captured evidence, structured growth claim, persisted report and existing React UI. Arbitrary chat answers and model-authored SQL are excluded.
- Growth uses Decimal and unrounded cross-multiplication; absolute tolerance is **0.01 percentage points inclusive**. No relative or display-grid tolerance. Claims 33.3 for 3→4, 28.6 for 7→9 and -18.2 for 11000→9000 fail this numerical contract; this is not an assertion that a rounded natural-language answer is generally incorrect. Models must supply sufficient precision. Display rounding never changes the decision. Rule growth_rate-v2 records the changed evidence-type policy; old reports retain their stored version.
- Python int and finite losslessly integral Decimal/float amounts are accepted. None is unverifiable; fractional cents are unverifiable; bool, foreign scalars and nonfinite values are tool_error/evidence_type_drift. numpy scalars are not part of the supported interface. Unsupported units/scope and broken evidence links are unverifiable, never passed.
- Report expected_value is a Decimal quotient at precision 60, not an exact representation of a repeating rational. Classification uses cross-multiplication. Display value, unrounded quotient, absolute difference and tolerance are visible.
- Model mode starts with no evidence. Its first query_demo_sales invocation executes fixed SQL; later calls reuse evidence in the same run. It cannot choose arbitrary SQL. A local model double verifies orchestration only, not real-provider accuracy.
- A running report older than 300 seconds is reconciled on GET/list to error/tool_error(stale_running). started_at is preserved; finished_at records detection, not an invented crash time. Conditional snapshot updates protect concurrently saved results. This is lazy reconciliation, not background monitoring or Agent checkpoint recovery.
- Evaluation counts must be split by test_injected vs agent_generated, and local doubles vs remote calls. Report total attempted, passed, failed, unverifiable, tool_error and still-running separately. Numerical agreement denominator is passed+failed only; broken links remain in attempted and unverifiable counts. Never drop errors from execution-completeness reporting. No real-model detection/false-positive rate is claimed from injected cases.

## Review disposition

| Finding | Disposition |
|---|---|
| F-01 tolerance | Preserve the explicitly confirmed contract; regression counterexamples added; widening rejected for Sprint 1 |
| F-02 explanation | Show unrounded quotient and difference alongside display value and tolerance |
| F-03 evidence types | PR #3 plus finite/bool/fraction tests; Python-scalar boundary explicit |
| F-04 denominators | Counting contract above; no fabricated benchmark rates |
| F-05 model scope | First tool invocation executes fixed SQL; no arbitrary model SQL; remote accuracy unverified |
| F-06 stale running | Lazy 300-second reconciliation with conditional update and persistence tests |
| F-07 process trace | Existing PR #1/#3 and actual review links are evidence; no retroactive Issues/meetings/hours fabricated |
| F-08 contract file | This document |
| F-09 Windows cleanup | Explicit connection closing, no suppression, success/error cleanup tests; Windows CI added |

---

# 中文版本

决定日期：2026-11-03（北京时间）。仓库负责人已重申数值约定并授权处理评审、验收和合并；这不代表团队会议或新增人工批准。

范围保持固定店铺、人民币分、2024/2025、真实固定 SQL、捕获证据、结构化声明、持久化及现有 React 页面。容差保持 **0.01 个百分点，包含边界**，不采用相对容差或显示网格比较。3→4 声明 33.3 等反例按本契约失败，不代表所有自然语言近似回答都错误。模型需提供足够精度。证据类型政策改变后使用 growth_rate-v2；旧报告保留原版本。

仅支持 Python int、有限且整数的 Decimal/float；None 和分以下小数无法验证；bool、外来类型及非有限数值为工具错误。numpy 标量不属于当前接口。缺失/跨运行证据不能通过。

未按展示位数舍入的计算值仍受 Decimal 60 位精度限制，循环小数不是精确有理数；判定使用交叉相乘。页面显示计算值、显示值、差值和容差。

模型首次调用工具执行固定 SQL，后续复用同次证据，不支持自由 SQL。替身测试不能代表真实服务准确性。

超过 300 秒仍 running 的报告在读取时转为 stale_running 工具错误，保留开始时间，结束时间表示发现时刻。条件更新避免覆盖并发完成结果；这是惰性协调，不是后台监控或 Agent 断点恢复。

统计必须区分测试注入、模型来源、替身及真实调用；分别报告尝试总数、四种判定和仍在运行数。数值一致性分母仅为 passed+failed；关联失败仍计入尝试总数及无法验证，不丢弃工具错误来美化完成率。不报告未经真实实验的检出率。

评审处置：F-01 保留用户约定并补反例；F-02 补解释；F-03 补类型处理；F-04 明确统计；F-05 澄清模型范围；F-06 补过期处理；F-07 使用真实 PR 证据而不补造过程；F-08 建立本文；F-09 显式关闭连接并补成功/失败清理测试和 Windows CI。
