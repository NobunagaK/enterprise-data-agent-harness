# Sprint 2 F3 trace performance evidence

This records an actual offline measurement on 2026-11-12, not a human acceptance
record or a response-time SLA. The production trace implementation is unchanged
by this PR. The benchmark and its raw samples make the remaining F3 performance
question reproducible.

## What is measured

1. **F3 version increment:** compare F2 commit
   `c0eeaedf665b1b435ef92526c8b0677e2acf07fb` with F3/main commit
   `55cd6497f18612fb7869f0c0fb95cf6271a4003c`. The baseline already records minimal
   query/validation traces. This comparison includes enhanced metadata and
   execution-boundary changes; it is not an all-tracing-on/off experiment.
   Each timed operation executes the fixed case's actual SQLite SQL, numerical
   validation and full report JSON serialization. Provider calls, HTTP and report
   database writes are excluded.
2. **One claim-recording helper:** in the same candidate process, compare direct
   claim assignment with `recorded_claim`, using the same Run/Claim construction.
   This isolates step construction/timestamps for one claim, not total agent cost.

Only fixed `test_injected` cases are used. The two numerical rules each cover
passed, failed and unverifiable outcomes. Workers use separate source checkouts
but the same Python environment. Each case has 10 warmup pairs and 100 measured
pairs, with alternating baseline/candidate order and no simultaneous execution.
Claim samples each average 1,000 operations, also using 10 warmups and 100 pairs.
Every SQL sample checks identical business results, SQL/rows and valid evidence
links; mismatches fail the command before producing a report.

Durations use `perf_counter_ns`. The report preserves signed differences and raw
samples, nearest-rank P95, and a paired bootstrap mean-difference interval
(2,000 resamples, seed 5351). These intervals describe the captured samples;
systematic machine noise and process placement are not eliminated by bootstrapping.

## Recorded result

Final-script measurement: **2026-11-12 14:33:14 UTC**. Linux 6.18.57 x86_64,
glibc 2.41, 3 logical CPUs, Python 3.12.14; Pydantic 2.13.1, SQLAlchemy 2.0.49,
LangChain 1.2.15 and LangGraph 1.1.6. No other test suite was run concurrently.
Local async sockets were permitted, as in backend testing; a preliminary invocation
inside the restricted execution sandbox timed out and produced no result artifact.

| Fixed case | Result | Baseline mean ms | F3 mean ms | Paired delta ms | Delta % | Bootstrap 95% interval ms |
|---|---|---:|---:|---:|---:|---:|
| growth-boundary | passed | 4.826 | 4.966 | +0.139 | +2.89% | [+0.059, +0.224] |
| growth-failed | failed | 4.677 | 4.715 | +0.037 | +0.79% | [-0.137, +0.248] |
| growth-invalid | unverifiable | 4.622 | 4.498 | -0.124 | -2.68% | [-0.210, -0.052] |
| total-exact | passed | 4.723 | 4.588 | -0.135 | -2.86% | [-0.294, +0.083] |
| total-failed | failed | 5.039 | 4.838 | -0.201 | -3.99% | [-1.168, +0.704] |
| total-invalid | unverifiable | 4.663 | 4.584 | -0.079 | -1.70% | [-0.256, +0.076] |

All six business/evidence comparisons passed. The median serialized snapshot grew
by **151 bytes** per case. The version deltas range from -0.201 to +0.139 ms, and four
intervals include zero. This does not establish a general speedup, zero tracing
cost, or a production latency guarantee. Small SQL/thread scheduling differences
can outweigh the recording increment, and the two versions also differ in their
execution boundary.

The isolated claim helper measured **3.339 microseconds** for direct assignment
versus **6.673 microseconds** with recording: an added **3.334 microseconds per
claim**, paired bootstrap 95% interval **[3.266, 3.391] microseconds**. This is the
most directly isolated recording measurement here; it excludes SQL, model calls,
report persistence and the rest of a trace.

The complete [raw JSON](measurements/sprint2-trace-overhead-2026-11-12.json) contains all
samples, medians/P95, dependency versions and exact source/script SHA-256 hashes.
Do not substitute these Linux results for native Windows application acceptance
or live-model latency. CI runs only a correctness smoke test, with no noisy
performance threshold. Re-measure after material trace or dependency changes.

## Reproduction and checks

From a checkout containing this script, with Git and uv available, create unused
sibling checkout paths and run these commands (also valid in PowerShell):

```text
git worktree add --detach ../s2-trace-baseline c0eeaedf665b1b435ef92526c8b0677e2acf07fb
git worktree add --detach ../s2-trace-candidate 55cd6497f18612fb7869f0c0fb95cf6271a4003c
uv sync --frozen --extra dev
uv run python scripts/benchmark_harness_trace.py --baseline ../s2-trace-baseline --candidate ../s2-trace-candidate --output trace-overhead.json
uv run pytest tests/unit/test_trace_benchmark.py -q
```

Defaults are 100 samples, 10 warmups and 1,000 claim operations per sample. Source
checkouts must have clean tracked Harness files. The worker asserts that it loaded
the requested checkout, and the parent bounds worker responses to 30 seconds and
closes processes/pipes on exit. No API key is needed.

Actual Linux checks: **560 backend/MCP tests passed**, including **9 benchmark
tests**; Ruff lint/format passed for the new script and tests. Regression tests
check negative deltas, quantiles, invalid samples, broken evidence links and a real two-worker SQL smoke
run. A separate Windows smoke job exercises this command's process/path behavior;
its actual result is recorded on the PR rather than assumed here.

---

# 中文版本：Sprint 2 功能③轨迹性能证据

本文件记录 2026-11-12 的实际离线测量。本 PR 增加可复现脚本、原始数据和测试，
不改动生产轨迹逻辑，不代表成员已验收，也不作响应时间承诺。

测量分两部分：第一部分比较 F2 的 c0eeaed 与 F3/main 的 55cd649，计入真实 SQLite SQL、
数值验证及完整报告 JSON 序列化。旧版已经有基础查询/验证轨迹，因此这不是“全部轨迹开/关”对照，
差异还包含执行边界的调整。第二部分在同一候选进程比较直接赋值声明与 recorded_claim，
隔离单条声明的步骤构造、时间戳等记录成本。两者均不调用真实模型，也不计入 HTTP 和报告数据库写入。

两个规则各包含通过、失败、无法验证案例，来源均为固定 test_injected 声明。每例预热 10 对、
正式测量 100 对，轮流交换先后顺序；声明微基准每个样本执行 1,000 次。
每次核对业务结果、实际 SQL/行数据和证据关联，一旦不一致即失败。保留有正负号的差值、全部原始样本、
P95 及 2,000 次配对 bootstrap 的 95% 区间，不把负差值删成零，也不把波动包装成稳定收益。

最终脚本测量时间为 UTC 14:33:14，环境为 Linux x86_64、3 个逻辑 CPU、Python 3.12.14，
详细依赖版本、提交和源码哈希见原始 JSON。测量期间未并行运行测试；受限沙箱中的一次预备调用超时，
未产生结果，成功运行使用与后端测试一致的本地异步 socket 权限。

上表完整流程均值约 4.50–4.97 毫秒；相对旧版差值为 -0.201 至 +0.139 毫秒，六组中四组区间包含零。
这些数据不能证明普遍提速或轨迹没有成本。每例报告 JSON 的中位大小增加 151 字节。
更直接的声明记录微基准从 3.339 微秒增加到 6.673 微秒，单条平均增加 **3.334 微秒**，
95% 区间为 **[3.266, 3.391] 微秒**；这个值仅适用于该辅助函数，不能直接代表整个 Agent。

复现命令见上方，兼容 PowerShell，无需模型 API Key。Linux 本次后端/MCP 共 **560 项通过**，
其中新增基准测试 **9 项**；脚本与测试的 Ruff 检查通过。新增 Windows CI 只检查脚本可运行与结果正确性，
不设置容易受机器波动影响的性能阈值。完整 Windows 应用和真实模型延迟仍须独立验收。
