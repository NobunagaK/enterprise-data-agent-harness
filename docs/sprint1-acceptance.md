# Sprint 1 acceptance and review disposition

Date: 2026-11-03 (Asia/Shanghai). Tested code revision: `95b7abe` (plus the documentation-only acceptance record). Base: `aee4f2c`; PR #3 integrated as `e6e3a3d`. Environment: Linux, Python 3.12.14, uv 0.12.23, pnpm 11.25.0, local Chromium.

## Outcome and authority

**Automated acceptance of the fixed deterministic Sprint 1 increment passes.** This record covers engineering checks of the deterministic workflow. Independent member acceptance and real-provider acceptance remain unverified.

Remote-model acceptance remains unexecuted: the restored OpenAI configuration has no API key. No accuracy/detection-rate claim is made. Windows CI coverage was added; the new revision has not been executed on Windows in this Linux environment. Historical Windows results in the reviews are not reused as current results.

## Executed checks

| Command / check | Observed result |
|---|---|
| `uv sync --frozen`; `pnpm --dir frontend install --frozen-lockfile` | Dependencies restored without lockfile changes |
| `python -m pytest tests/unit tests/integration/test_mcp_transports.py -q` (project venv) | **403 passed**, including **49 Harness tests**; 37 upstream warnings |
| `ruff check backend/src tests`; `ruff format --check backend/src tests` | Passed; 95 files formatted |
| `mypy backend/src/analytics_agent` | Passed, 68 source files |
| `pnpm --dir frontend test` | **46 passed**, including the formerly failing USAGE case and a new cross-turn guard |
| `pnpm --dir frontend build` | Typecheck and production build passed; bundle-size warning retained |
| `pnpm --dir frontend lint` | 0 errors, 7 existing warnings |
| `HARNESS_CHROMIUM_PATH=/usr/bin/chromium pnpm --dir frontend exec playwright test --config ../tests/e2e/harness.config.ts` | **1 passed**, real SQL/API, explanation, injected label, reload |
| Same Playwright command with `../tests/e2e/playwright.config.ts` | **36 passed**, full browser regression suite |
| Database restoration | Existing SQLite backed up, migration 005→006 and bootstrap succeeded; migration test preserves a seeded record and is repeatable |
| Running API / restart check during restoration | 10 and 10.01 passed; 18.7 and 10.02 failed; SQL totals 10000/11000 cents; four reports retrieved unchanged after backend restart |

The final candidate additionally tests persisted expiry, live/completed report preservation, concurrent completion protection, actual closed connections and absence of temporary artifacts on successful and failing SQL paths. Local model doubles test orchestration, missing claims and timeouts only. Full browser tests use mock chat and placeholder credentials; unrelated greeting requests attempted by the upstream suite are not real-model acceptance evidence.

## Findings and remaining limitations

See [evaluation contract](design/sprint1-evaluation-contract.md) for F-01–F-09 dispositions and metric denominators. Source evidence: [PR #1 review](https://github.com/NobunagaK/enterprise-data-agent-harness/pull/1#pullrequestreview-5723127763), [PR #3 follow-up review](https://github.com/NobunagaK/enterprise-data-agent-harness/pull/3#issuecomment-6581142937).

- F-01 retains the owner's explicit inclusive 0.01pp contract, with low-precision counterexamples protected by tests. No silent relaxation.
- F-03/F-09 fixes were continued from the existing PR #3, preserving its history; cleanup errors are no longer suppressed. New code is not represented as a human-reviewed revision.
- F-02 explains quotient/difference; F-06 lazily expires running reports after 300 seconds using a conditional write. No background recovery promise.
- BUG-01 USAGE attribution is fixed and regression-tested. Numeric rule version is now growth_rate-v2 because evidence classification changed; persisted historical reports are not rewritten.
- TD-01 internal engine lifecycle coupling and JSON snapshot evolution remain future maintenance debt. Multi-rule extensibility, arbitrary SQL/free-text validation, real-model experiments and independent F sign-off are not claimed complete.
- CI now targets PRs into sprint1/harness as well as main, includes Windows Harness tests and frontend unit tests. Local results do not imply that GitHub Actions ran; remote status must be checked separately.

## Reproduction

From a clean checkout use `uv sync --frozen`, `pnpm --dir frontend install --frozen-lockfile`, then the commands above with `uv run --no-sync` before Python commands. Set `ANALYTICS_AGENT_CONFIG_DIR` to a writable local directory before imports. Run `uv run --no-sync analytics-agent bootstrap` before starting uvicorn. On Windows, use `uv run --no-sync python -m pytest ...` rather than `.venv/bin/pytest`. For browser tests, use installed Playwright Chromium or set HARNESS_CHROMIUM_PATH to the system Chromium path.

---

# 中文版本：Sprint 1 验收与评审处置

日期：2026-11-03（北京时间）。被测代码 `95b7abe`，之后仅添加验收文档；PR #3 以 `e6e3a3d` 集成。环境为 Linux、Python 3.12.14、uv 0.12.23、pnpm 11.25.0、Chromium。

**固定确定性案例的自动验收通过。** 本记录覆盖确定性流程的工程核验；成员独立验收及真实模型验收仍未验证。

本次后端/MCP **403 通过**（含 Harness **49 项**），前端单元 **46 通过**，专项浏览器 **1 通过**、完整浏览器 **36 通过**；lint、格式、类型检查、构建通过。ESLint 保留 7 个原有 warning、构建保留包体积 warning。原 USAGE 归属失败已修复并补跨会话边界测试。

数据库已备份并从 005 升至 006；迁移测试保护旧数据且可重复运行。恢复阶段 API 验证 10/10.01 通过、18.7/10.02 失败，证据 10000/11000 分，四份报告经服务重启可恢复。最终代码另覆盖过期报告、活跃/完成报告保护、并发完成保护、连接显式关闭及成功/失败路径无残留。

F-01 保持用户确认的包含边界 0.01 个百分点；F-02 补数值解释；F-03/F-09 沿原 PR 修复类型与资源清理；F-04/F-08 明确评测契约；F-05 澄清首次工具调用执行固定 SQL；F-06 补 300 秒惰性过期处理；F-07 关联真实评审证据，不补造过程。证据类型政策变化使用 growth_rate-v2，旧报告不改写。

真实 OpenAI 未配置密钥，未执行真实模型验收，不报告准确率/检出率。Windows CI 已加入，但本机没有运行 Windows；历史评审结果不作为当前复测结果。F 的独立签字、内部引擎生命周期接口债务、JSON 版本演进及后续扩展仍如实保留。GitHub CI 是否实际运行须单独核查，不以本地通过替代。

复现命令见英文表；Windows 使用 `uv run --no-sync python -m pytest`。启动前设置可写配置目录、执行 bootstrap，再启动服务。
