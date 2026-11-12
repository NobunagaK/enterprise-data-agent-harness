# Shared-contracts implementation verification

Date: 2026-11-07 (Asia/Shanghai). Environment: cloud Linux, Python 3.12.14,
project virtualenv, installed frontend dependencies and system Chromium.
Base: `8359a46827f48936a2e110e939061bff78f11e6f`. These results apply to the
implementation shipped in this PR, not to future F2/F3/F4 implementations.

This record covers implementation verification on Linux. Windows and real-model
experiments are outside these results; review decisions are recorded on the PR.

For Python checks, set `ANALYTICS_AGENT_CONFIG_DIR` to a writable isolated
directory and `DATAHUB_TELEMETRY_ENABLED=false`. Commands below use the existing
`.venv`; a fresh checkout first needs the repository's documented dependency setup.

| Executed command | Observed result |
|---|---|
| `.venv/bin/python -m pytest tests/unit/test_harness.py tests/unit/test_harness_contracts.py -q` | 73 passed: 49 existing Harness cases and 24 new contract cases |
| `.venv/bin/python -m pytest tests/unit tests/integration/test_mcp_transports.py -q` | 427 passed, 49 warnings |
| `.venv/bin/ruff check backend/src tests` | Passed |
| `.venv/bin/ruff format --check backend/src tests` | Passed, 98 files |
| `.venv/bin/mypy backend/src/analytics_agent` | Passed, 70 source files |
| `pnpm --dir frontend test` | 53 passed, including 7 new client/rendering tests |
| `pnpm --dir frontend build` | Typecheck and production build passed |
| `pnpm --dir frontend lint` | 0 errors; 7 warnings in unchanged files |
| `HARNESS_CHROMIUM_PATH=/usr/bin/chromium pnpm --dir frontend exec playwright test --config ../tests/e2e/harness.config.ts` | 1 passed: actual SQL, failed-claim explanation, source label and history after reload |
| `git diff --check` | Passed |

The browser test bootstrapped a fresh temporary SQLite database through migration
006. No user database reset was performed. No dependency/lockfile changes were
needed. The Windows CI job now also selects the new contract tests; a workflow
edit is not evidence that GitHub Actions or Windows execution succeeded.

The sandboxed async run stalled after synchronous tests. A minimal standalone
`asyncio.to_thread` example also completed the worker but failed to resume the
event loop. Those incomplete attempts were terminated. The successful Python
and browser results above were obtained with approved execution outside that
sandbox; no application workaround was added.

Retained warnings: existing Pydantic schema-name collisions, Alembic configuration
deprecations, DataHub SDK experimental warning, MCP deprecations, frontend hook
warnings, stale Browserslist data and bundle-size warning. The full unrelated
browser suite was not rerun. Remote-provider acceptance and independent member
acceptance remain unexecuted; Issues #11 and #12 are not closed by this change.

---

# 中文：共同接口实现验证

日期：2026-11-07（北京时间）。环境：云端 Linux、Python 3.12.14、已有项目虚拟环境及前端依赖、系统 Chromium。
基线为 `8359a46`。结果对应本 PR 的实现，不代表后续三个功能已经完成。

本记录覆盖 Linux 上的实现验证；不包含 Windows 或真实模型实验，评审决定以 PR 记录为准。
复现命令见英文表，Python 检查使用独立可写配置目录并关闭遥测。

本次实际结果：后端/MCP 427 通过；其中 Harness 专项 73 通过（原有 49、新增 24）；
前端 53 通过（新增 7）；真实 SQL 浏览器流程 1 通过；Ruff、类型检查、构建通过。
前端 lint 无错误，保留未改动文件中的 7 个警告。

浏览器测试使用临时数据库并执行已有迁移至 006，没有清空用户数据库，也没有修改依赖或锁文件。
Windows CI 已增加新测试选择，但配置修改不代表远程或 Windows 检查已通过。

沙箱内异步测试曾阻塞；不涉及项目的最小线程示例也无法恢复事件循环。终止未完成尝试后，
经批准在沙箱外运行得到上述通过结果，没有为绕过环境问题修改应用逻辑。

保留上游弃用、SDK、前端 Hook、Browserslist 与包体积警告。本次未重跑全部无关浏览器测试，
未执行真实模型和成员独立验收，不因此关闭 Issues #11、#12。
