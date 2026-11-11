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
