# Sprint 2 F4: batch budgets and interruption semantics

This closes the prototype execution-boundary work tracked in #19. It extends the
existing synchronous, sequential batch runner and retains one session per case.
The supported workload is a bundled case set of 1–20 cases in one server process.

## NFR-01: story and limits

As an evaluator, I want a batch to stop starting new cases when its budget expires
and to retain the results already obtained, so an interrupted evaluation cannot
be mistaken for a successful complete run.

| Setting | Default | Accepted values | Meaning |
|---|---:|---|---|
| `case_timeout_s` | 60 seconds | greater than 0, at most 120; or null | Cancel one case at its execution boundary; null uses only the enclosing batch budget and existing model limit |
| `batch_timeout_s` | 300 seconds | greater than 0, at most 600 | Cancel the batch execution boundary, including normal snapshot writes; stop dispatching later cases |

These are configurable prototype defaults, not school-mandated limits or measured
response-time guarantees. The single-run model deadline remains 60 seconds.
Both HTTP requests and Python callers reject non-finite, nonpositive or excessive
budgets. Existing request fields and `case_timeout_s=null` remain accepted.

Cancellation is cooperative. The parent owns separate tasks for case execution
and normal metadata writes, cancels each once, then shields and drains it even
if the parent is cancelled repeatedly.
The existing query worker similarly drains its thread before returning. Cleanup
and final database writes can outlast the budget; a permanently stuck thread
cannot be forcibly killed. This synchronous prototype does not introduce a
background queue, remote cancel API, retry/resume, or a hard response-time SLA.
Closing a browser tab is not a promise that server execution has been cancelled.

## Outcomes and persistence

- A per-case deadline produces `state=timeout`, reason `case_timeout`; later cases
  continue while the batch budget allows. An internal `TimeoutError` without
  expiry of that deadline is an execution error, not a fabricated budget expiry.
- Batch expiry produces `state=timed_out`, reason `batch_timeout`. The active case
  is `timeout` unless a terminal result was already confirmed; remaining cases
  are `skipped`, with no run ID, validation result or expected-result match.
- External task cancellation produces `state=cancelled`, with an active
  `cancelled` case and subsequent `skipped` cases, then propagates cancellation.
- Confirmed outcomes are preserved, including when cancellation occurs during
  session cleanup or batch persistence. Terminal batch writes are shielded from
  repeated cancellation. A failed write is never returned as successful storage.
  If a cancellation snapshot cannot be saved, cancellation still propagates and
  the last durable snapshot remains available for later interruption diagnosis.
- A cancelled/timed-out single run may retain only its initial snapshot; the
  batch reports that execution state separately. The UI identifies such details
  as the last saved snapshot instead of claiming complete execution evidence.

New batches use JSON schema version 2, adding the case-ID plan, budgets, deadline,
active case and stop reason. Schema version 1 snapshots remain readable. No
database migration is required. Existing four validation categories are unchanged.
`attempted = completed + timeout + error + cancelled + interrupted`; skipped cases
are excluded. For a terminal v2 batch, `attempted + skipped = planned cases`.
The new count fields are omitted when zero for compatibility with old responses.

For an expired persisted `running` batch without an active owner in this server
process, GET/list return a read-only `interrupted` projection. Its active case is
marked `interrupted` (execution outcome unconfirmed), and the remaining planned
cases are `skipped`. A dispatched/active marker does not prove SQL completed.
The projection does not invent a finish time, rewrite the stored JSON, or assert
that a worker was killed. Current local cleanup remains `running` until it ends.
Legacy records without a deadline cannot safely be inferred to have expired.

## Acceptance evidence

The lifecycle tests cover a genuinely blocked middle case and whole-batch expiry;
preserved earlier reports and an unstarted tail; repeated cancellation during
worker draining, initial metadata cleanup and final persistence; failed terminal writes; internal timeout
attribution; invalid budgets; concurrent batch isolation; and read-only expired
snapshots, including timezone handling and legacy compatibility. Frontend tests
cover the new summaries, and a browser fixture verifies interruption display and
disabled detail links for unexecuted/unconfirmed cases. Browser fixtures validate
presentation; actual cancellation/SQL/persistence are exercised by backend tests.

Actual commands and results are recorded on this PR. Review the defaults and soft
deadline guarantees as part of #19 acceptance. Live-provider and complete native
Windows application acceptance remain separate work.

---

# 中文版本：Sprint 2 功能④批次预算与中断语义

本增量收尾 #19 中课程原型的执行边界，沿用同步、串行、每例独立 session 的实现。
支持范围为单服务进程运行 1–20 条内置案例。

用户故事：评测者希望批次到期后不再启动新案例，并保留已有结果，避免把中断评测误认为全部成功。
默认单例 60 秒、整批 300 秒，可分别配置为大于 0 且不超过 120/600 秒；单例可显式设为 null，
此时仍受整批预算和原有模型期限约束。HTTP 与 Python 调用均校验预算，拒绝非有限数、负数、零及超限值。
这些是可调整的原型默认值，不是学校规定的数值，也不是已测得的响应时间承诺。

到期会请求协作取消，随后等待所拥有的任务、线程及 session 完成清理，再保存批次终态。
连续取消不会让执行边界提前退出或中断终态写入；清理和数据库操作可能超过预算。
永久卡死线程无法被强制终止；关闭网页不保证取消服务端任务。本轮保持同步小批量原型范围。

单例到期标记 timeout，后续案例在整批预算内继续；内部自行抛出的 TimeoutError 不冒充期限到期。
整批到期标记 timed_out，当前未完成案例标记 timeout，其余标记 skipped；外部任务取消则标记
cancelled，并继续向调用方传播取消。已经确认的结果保留；未执行案例没有运行编号、数值结果或匹配结论。
取消时如果数据库无法保存终态，不声称写入成功；原有快照仍可用于后续中断诊断。
单例详情可能只有初态快照，界面会明确提示这一限制。

新批次 JSON 版本为 2，记录案例计划、预算、截止时间、当前案例及停止原因；旧版本仍可读取，无需迁移。
通过、失败、无法验证、工具错误四类数值结果保持不变。attempted 不计 skipped；终态已尝试数加未执行数等于计划数。
读取已过期且本进程没有活动执行者的 running 快照时，只返回 interrupted 投影：当前案例结果未确认，
后续案例未执行。不虚构完成时间、不改写原 JSON、不宣称线程已被杀死；旧记录没有期限时不猜测已过期。

测试覆盖真实整批超时、前序报告保留、尾部不启动、工作线程/终态保存期间的重复取消、存储失败、内部超时归因、
非法预算、并发批次隔离、时区及旧快照兼容；前端和浏览器另行检查状态展示。浏览器使用状态夹具，
真实取消、SQL 和持久化由后端测试验证。实际命令及结果记录于 PR，默认预算和协作取消边界交由成员评审。
