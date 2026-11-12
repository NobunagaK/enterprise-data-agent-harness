# Sprint 2 F3 backend trace integration

This extends Haoyu's original PR #17, preserving its commits, and integrates
F2 at `2a2a58c` from PR #23. Both PRs remain reviewable; integration does not
imply that #23 has already merged into main. Merge dependency: #23 before #17.

## Observable events

- Query, claim recording, validation, and answer recording explicitly enter
  `running`, then finish with UTC timestamps and monotonic elapsed milliseconds.
- Model setup is a `tool` step. Configuration or agent-construction failure uses
  `model_configuration_error`; it does not invent a provider model invocation.
- Provider model callbacks create one `model` step per observed call. Usage is
  copied only from nonnegative integer provider metadata. Missing values stay
  null; a reported zero is retained. No hidden reasoning, prompts, credentials,
  inferred tokens, or fictional context retrieval/retries are recorded.
- Failed model callbacks use `model_error` or `model_cancelled`. Started calls
  lacking a terminal callback are closed at the execution boundary.
- The outer model deadline remains 60 seconds. A deadline expiry returns
  `run_timeout` even if the provider callback reports model cancellation.
- Execution cancellation closes observed in-memory events and propagates. The
  shared service still does not claim it saved a final cancelled snapshot;
  an initial persisted report can remain running until existing stale detection.

F2 rule dispatch, monetary units and error metadata are retained. False numerical
claims are completed validations with a failed result, not execution failures.
Legacy snapshot defaults and storage JSON are not rewritten.

## Review findings and repairs

The original `a64e809` was reproduced with local controlled doubles:

1. A failing `get_llm` produced `execution_error` and `steps=[]`. A measured setup
   event now identifies that failure with a safe code.
2. A second cancellation during `query_worker` cleanup returned while the owned
   thread was still active. Cleanup now shields and drains through repeated
   cancellation before propagating it, consuming any worker exception safely.

Draining guarantees cleanup only for a worker that eventually terminates. It
cannot forcibly kill a stuck thread or guarantee a hard wall-clock deadline.
Issue #19 remains a separate budget/resource-termination requirement.

Claim recording is now a measured operation: it becomes completed only after
constructing the claim. This replaces the original implicit completed default
for the instantaneous event and supplies producer-level evidence for issue #20.

## Validation

Local Python 3.12 on Linux:

- Harness: 191 passed, including 33 trace tests (2 original + 31 added).
- Trace tests observe live query/validation/claim states, success and errors,
  configuration/setup failure, repeated cancellation with successful/failed
  workers, actual timeout expiry, missing provider terminal callbacks, partial
  and invalid usage, interleaved model calls, both F2 rules and persisted links.
- Actual LangChain orchestration uses local model doubles; this is not a live
  provider or independent human acceptance claim.
- Ruff lint/format and mypy passed (110 formatted files / 78 source files).
- Full backend/browser and Windows CI results are recorded on the final PR head.

The F3 frontend is handled separately in #18. Full native Windows application
acceptance and live-provider validation remain distinct from automated CI.

## Timeout attribution review follow-up

Haoyu's review of `12856cc` reproduced an immediate provider `TimeoutError`
being reported as expiry of the whole 60-second model budget. The same issue
also affected configuration timeouts and missing model terminal callbacks.

The runner now owns an `asyncio.timeout` context and checks its `expired()`
state. Only expiry of that context produces `run_timeout`. An internal provider
timeout retains `model_error`; a configuration timeout retains
`model_configuration_error`. External cancellation still propagates, and the
production budget remains 60 seconds. This does not add hard worker termination.

Six new regressions cover both rules and three internal failure paths. All six
failed before the repair and pass afterward. The older deadline regression now
waits for actual deadline expiry instead of raising a synthetic `TimeoutError`.
Existing real-expiry and external-cancellation tests remain in place.

Local recheck: 551 backend/MCP tests passed, including 197 Harness tests;
Ruff lint/format and mypy passed. Remote checks apply to the updated PR head.

---

# 中文版本：Sprint 2 功能③后端轨迹接入

保留 Haoyu 的 #17 原始提交，接入 #23 的功能②提交 `2a2a58c`，不代表 #23 已进入 main。
合并依赖顺序为 #23 → #17；前端轨迹继续由 #18 提供。

查询、声明记录、验证和答案记录显式经历 running 与终态，时间使用 UTC，耗时使用单调时钟。
模型配置/构建作为 tool 步骤，失败使用安全码 model_configuration_error，不伪造模型调用。
实际模型回调产生 model 步骤，只记录供应商报告的非负整数 Token；缺失为空，真实报告的零保留。
不记录隐藏推理、凭据、提示词或虚构的上下文检索、重试。

已开始但没有终态回调的模型步骤会在边界关闭。60 秒模型限制不变；实际超时保持 run_timeout，
不会被内部 model_cancelled 覆盖。执行取消仍向调用者传播，不宣称最终取消快照已保存；
初始快照可能继续显示运行中，直到已有过期检测生效。旧报告及功能②的金额单位、规则分派保持兼容。

原提交已实际复现两项问题：模型配置失败无步骤；重复取消时线程未结束而执行边界已退出。
现已补安全配置事件，并在重复取消下持续等待受控工作线程结束、读取其异常后再传递取消。
等待线程结束不等于强制终止卡死线程，也不保证硬截止时间；Issue #19 继续单独跟踪。
声明记录改为实际计时，构造完成后才标 completed，并补查询、验证和声明执行中的状态测试，对应 #20。

本地 Harness 191 项通过，其中轨迹测试 33 项（原有 2 项＋新增 31 项）；Ruff、格式与 mypy 通过。
覆盖两条规则、成功/失败、取消/超时、配置异常、Token 缺失/非法值、真实编排替身与持久化关联。
完整后端、浏览器及 Windows CI 的最终结果记录在 PR；替身测试不代表真实供应商或人工独立验收。

## 超时归因评审修复

Haoyu 对 `12856cc` 的评审复现了模型立即抛出 TimeoutError，却显示整次运行超过
60 秒的问题；配置超时和缺失模型结束回调也存在同类误判。

执行器现持有 asyncio.timeout 上下文并检查 expired()，只有本层截止时间实际到期才
返回 run_timeout。供应商内部超时保留 model_error，配置超时保留 model_configuration_error。
外部取消仍传播，生产模型预算仍为 60 秒，不增加强制终止工作线程的承诺。

新增两种规则、三条内部错误路径共 6 项回归，修复前全部失败，修复后全部通过。
原截止时间测试改为等待实际到期，保留现有真实超时及外部取消测试。
本地本轮后端/MCP 551 项通过，其中 Harness 197 项；Ruff、格式及 mypy 通过。
远程检查以更新后的 PR 提交为准。
