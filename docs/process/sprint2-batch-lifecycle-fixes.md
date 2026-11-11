# Batch lifecycle bug fixes / PR #15 follow-up

Date: 2026-11-08 (Asia/Shanghai). Base: `a4cf3f1` on `sprint2/batch`.
These are implementation-side checks, not human approval or Sprint acceptance.

## Findings and repair

Haoyu's actual review requested changes for two reproducible defects:
[pool starvation](https://github.com/NobunagaK/enterprise-data-agent-harness/pull/15#discussion_r4502548284)
and [lost report identity](https://github.com/NobunagaK/enterprise-data-agent-harness/pull/15#discussion_r4502548290).

1. The conversation preflight held a connection while batch persistence requested
   another. A single-connection pool timed out. Preflight now owns a short-lived
   session that closes before execution; every case still owns its own session.
2. Timeouts/final-save failures discarded an already-persisted run ID. The shared
   service now optionally calls `on_persisted(run_id)` synchronously after its initial
   successful commit. Batch error/timeout outcomes retain that identity, without
   claiming a completed result or fabricating an ID after an initial-save failure.
   Original callers using `run_case(request, session)` remain compatible.

## Evidence

New lifecycle regressions before repair: **3 failed, 1 passed**. They reproduce
an actual pool timeout, actual asyncio cancellation after initial persistence,
and final-save failure. After repair all four are included in the passing suite.
Repeated executions verify distinct IDs; earlier/later successful reports remain
readable. Exceptions' private details are not copied into batch output.

Executed on cloud Linux / Python 3.12.14 with isolated configuration and telemetry
disabled; asynchronous/browser checks ran outside the restricted sandbox:

- `.venv/bin/python -m pytest tests/unit tests/integration/test_mcp_transports.py -q`: **441 passed**.
- `pnpm --dir frontend test`: **61 passed**.
- `pnpm --dir frontend build`: passed, retained existing bundle/Browserslist warnings.
- Ruff lint/format: passed (106 files); mypy: passed (76 source files).
- Existing Harness Playwright config with system Chromium: **1 passed**, temporary
  database bootstrapped through migration 007; user databases were not reset.
- Windows CI includes the new regression file; configuration alone is not a pass.

Scope: these two lifecycle bugs. Worker-thread hard cancellation, background
scheduling, mixed rules, source-aware evaluation summaries and complete tracing
remain separate follow-up requirements. The default Step status concern in PR #14
remains a documented producer responsibility; this patch does not claim to resolve
all review suggestions or all possible repository bugs. Real-model acceptance is
not performed. Keep PR #14/#15 review decisions and Issues #11/#12 intact.

## Integration recheck: 2026-11-11 (Asia/Shanghai)

PR #15 has merged, so PR #16 now targets `main`. Integrated `main@f57e630`
into the existing fix branch without conflicts, preserving the shared-contract
clarifications and the new batch browser tests. No runtime changes beyond the
original lifecycle fix were needed.

Fresh local checks on the integrated tree (cloud Linux / Python 3.12):

- Backend/unit + MCP transport suite: **441 passed**, 133 existing warnings.
- Harness browser suite: **2 passed** (batch counts/drill-down/reload and original
  single-run SQL evidence/reload), using system Chromium and an isolated database
  bootstrapped through migration 007. Existing frontend build reused; no frontend
  source changes are introduced by this integration.
- Ruff lint/format: passed, 106 files; mypy: passed, 76 source files.
- Diff whitespace check: passed. New remote CI is tracked on PR #16 separately.

The owner explicitly authorized handling and merging PR #16 after verification
without waiting for Haoyu/Zikai to review again. This is a one-PR authorization,
not an approval submitted on their behalf or a change to other PRs' review rules.

---

# 中文：批次生命周期修复

日期：2026-11-08（北京时间），基于 `sprint2/batch@a4cf3f1`。
来源是 Haoyu 在 PR #15 的实际 Request changes，链接见英文部分。

修复两类问题：会话预检查持有连接造成连接池饥饿；超时或终态保存失败后丢失已保存运行的编号。
预检查现使用短生命周期 session，执行前释放；每案例独立 session 不变。
服务新增可选同步通知 on_persisted，仅在初态提交成功后传出编号，批次在异常时保留关联。
通知不代表执行成功；初态保存失败不伪造编号，原两参数调用保持兼容。

新增测试修复前 3 失败、1 通过；覆盖单连接池、真实异步超时、终态保存失败和初态保存失败。
修复后本次实际后端/MCP 441 通过，前端 61 通过，真实 SQL 浏览器流程 1 通过；格式、lint、类型和构建通过。
测试使用临时数据库迁移至 007，不清空用户数据库；Windows 工作流已加入新文件，远程结果须另查。

本记录不冒充人工批准或 Sprint 验收。工作线程硬取消、后台调度、多规则、来源分组统计及完整轨迹仍需后续工作；
PR #14 的步骤默认状态建议未在本次修改。不宣称全仓库无 bug，也未执行真实模型验收。
保留已有评审和 Issues #11/#12 的状态，修复另行提交评审，不自动合并。

## 2026-11-11 集成复核（北京时间）

#15 已合并，因此 #16 改为面向 main；将 main@f57e630 无冲突集成到原修复分支，
保留共同契约补充和新增批次浏览器测试，运行代码仍为原两项修复。
本次重新执行：后端/MCP 441 通过（保留 133 条原有警告）；浏览器 2 通过，覆盖批次汇总、
失败详情、刷新历史及原单次 SQL 证据流程；Ruff 106 文件、mypy 76 文件及差异空白检查通过。
浏览器使用系统 Chromium、迁移至 007 的独立临时数据库，并复用已有前端构建；本次无前端源码变更。
新远程 CI 在 #16 独立记录。

用户本次明确授权核验后处理并合并 #16，无需等待 Haoyu/Zikai 再次评审；
此授权仅针对 #16，不代替两位提交批准，也不更改其他 PR 的评审规则。
