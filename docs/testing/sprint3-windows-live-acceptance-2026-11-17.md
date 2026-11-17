# Sprint 3 native Windows and live-provider acceptance

Recorded **2026-11-17 (Asia/Shanghai)** on a native Windows machine against
`main@45216b1cdbb3d5f108ba39f4a0dbf4873cce8b3b`. This covers the Sprint 3 handoff
tasks: complete Windows installation/start/UI, persisted real-provider reports,
failure handling, and the Windows cleanup evidence for #11. It is not a substitute
for independent-member reproduction or the final course video.

## Environment and installation

| Item | Value |
|---|---|
| OS | Windows 11, 10.0.26300 |
| Python | 3.12.13 (repo `.venv` via `uv sync --frozen --extra dev`) |
| Node / pnpm | 24.14.0 / 10.6.3 |
| Browser | Playwright 1.59.1, Chromium 1234 |
| Database | `sqlite+aiosqlite:///D:/Temp/edah-accept.db` (isolated) |
| Server | `uvicorn analytics_agent.main:app --host 127.0.0.1 --port 8100 --workers 1` |

Fresh install and build:

```text
uv sync --frozen --extra dev
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build
uv run analytics-agent bootstrap
```

Bootstrap applied migrations **001 → 007** and completed seeding. The frontend was
served from `frontend/dist` by the backend at `http://127.0.0.1:8100`; no Vite dev
server was used.

## Fixed-case UI acceptance

A headless Chromium session (native Windows process) dismissed the onboarding
wizard, created one conversation, and operated the real Harness panels.

| Check | Result |
|---|---|
| Growth batch (`sprint2-sales-v1`, 10 cases) | **2 passed / 4 failed / 4 unverifiable**, completed 10/10 |
| Mixed batch (`sprint2-sales-mixed-v1`, 8 cases) | **3 passed / 2 failed / 3 unverifiable**, completed 8/8 |
| Total one-cent failure detail | Claim `11001` vs computed `11000`, difference `1 分`, tolerance `0`, rule `sales_total-v1` |
| Trace detail | Query 56.03 ms → claim 0.10 ms → validation 0.17 ms; SQL/evidence links present |
| Single-run panel (`sales_total`, `11001`) | Completed, `failed` |
| Browser console errors | **0** |

Screenshots (under `measurements/sprint3-windows-live-2026-11-17/`):
`batch-summary.png` (mixed batch), `trace-card.png` (one-cent failure with SQL/evidence),
`live-model-card.png` (model-generated claim), `history-after-restart.png` (reloaded history).

## Restart persistence

The server was stopped and restarted against the same SQLite file.

- **2/2 batches** and **18/18 batch-linked runs** compared **equal as full JSON**.
- All **19** stored runs (including the standalone single run) remained readable;
  the standalone run kept its ID and `failed` result.
- The reloaded UI showed both batch records and the mixed summary
  (`3 passed / 2 failed / 3 unverifiable`) — `06-history-after-restart.png`.
- The list APIs filter by `conversation_id`; reproduction must pass the
  conversation ID (`/api/harness/batches?conversation_id=...`).

## Live provider

Configured through `PUT /api/settings/llm` as an OpenAI-compatible endpoint
(`https://api.deepseek.com`, model `deepseek-flash`). The API key was supplied
locally and is **not** present in this record or the repository.

| Run | Result | Details |
|---|---|---|
| Growth, `agent_generated` | **passed**, 12.9 s | Claim `10 percent`; model `deepseek-flash`; 8 steps (tool/model/query/model/claim/model/answer/validation); cites evidence ID |
| Sales total, `agent_generated` | **passed**, 4.4 s | Claim `11000 CNY_cent` with `year=2025`; 8 steps; answer shows `CN¥110.00` |
| UI growth run | **passed** | Card shows “模型生成声明 · deepseek-flash” and the same 10% calculation — `05c-live-model-card.png` / `05d-live-model-trace.png` |

Both API reports survived a server restart with **full JSON equality**
(`live-restart-original.json` / comparison fields in the sanitized evidence).
Failure handling was checked with a deliberately invalid model name: the run
returned `state=error`, `result.status=tool_error`, `reason=model_error`, the
model step carried the safe code `model_error`, and the API key was absent from
the response. The valid model was restored immediately afterwards.

## Windows cleanup evidence (#11)

- 20 successful/failed fixed-case queries were executed on final main on native
  Windows; **no new `harness-sales-*` directories** were left in `%TEMP%`.
- 23 leftover directories exist, all dated **2026-10-31** from the pre-fix
  Sprint 1 session (each contains `sales.db`); they were not deleted.
- `pytest tests/unit/test_harness.py::test_query_closes_connection_and_removes_temp_artifacts`
  (both `query_fails=False/True`) → **2 passed** on Windows; directory count
  unchanged.

## Sprint 3 acceptance matrix

| Requirement | Evidence in this record | Status |
|---|---|---|
| Native Windows install, bootstrap, start | Fresh `uv sync` + `pnpm` + build; migrations 001→007; Uvicorn on 8100 | Passed |
| Operate the UI for both rules and mixed batches | Growth 2/4/4; mixed 3/2/3; single total 11001 failed; 0 console errors | Passed |
| SQL/evidence/trace inspection | One-cent card and trace screenshots; query/claim/validation steps | Passed |
| History after restart | 2/2 batches + 18/18 batch runs equal; 19 runs readable; UI history | Passed |
| Real provider through app/API | Growth and sales-total `agent_generated` passed; UI model card; 8 steps | Passed |
| Persisted live reports | Both API reports full JSON equal after restart | Passed |
| Failure handling | Invalid model → `tool_error/model_error`; no key leak; model restored | Passed |
| Windows cleanup (#11) | 20 queries, no new `harness-sales-*` dirs; cleanup test 2/2 | Passed |
| Independent reproduction (#12) | Not performed by another member in this run | Pending |
| Demo video | 66.4 s local MP4 from the accepted commit | Recorded |

## Limits

- Fixed synthetic `sales-v1` data only; no customer data and no arbitrary SQL.
- One Windows process/worker; no claim of crash recovery for uncommitted work.
- Browser interaction was Playwright-driven Chromium, not a hand-operated GUI.
- One provider/model (`deepseek-flash`); independent-member reproduction and the
  course video remain separate.
- The failure check used an invalid model name; no network or credential fault
  injection beyond that.
- The 23 leftover fixture directories predate the cleanup fix and are left as-is.

## Reproducible evidence

The sanitized machine-readable record is
`docs/testing/measurements/sprint3-windows-live-acceptance-2026-11-17.json`.
Local artifacts (screenshots, logs, API exports, manifests, video) live under
`D:\Temp\edah_acceptance_2026-11-17\`; `artifact-manifest.json` lists SHA-256
hashes for every file. The sanitized evidence hash is
`c327b3b0e40e26088f5db07a7448e965143304421c5c5b35e3d19ef98b6a9851`.

---

# 中文：Sprint 3 原生 Windows 与真实模型验收

2026-11-17 在原生 Windows 11 上，针对 `main@45216b1` 完成。

- **安装与启动**：全新 `uv sync`、`pnpm install --frozen-lockfile`、`pnpm build`；
  `analytics-agent bootstrap` 迁移 001→007；单 worker 服务在 127.0.0.1:8100 提供前端与 API。
- **固定案例 UI**：增长率 10 例为 **2 通过/4 失败/4 无法验证**；混合 8 例为
  **3 通过/2 失败/3 无法验证**；总额差一分详情显示声明 11001、计算 11000、差值 1 分、容差 0；
  轨迹含 SQL/证据；浏览器 0 控制台错误。
- **重启**：2 个批次和 18 份批次内报告完整 JSON 全部一致；全部 19 份运行可读；
  刷新后 UI 仍显示两批历史。注意列表接口按 `conversation_id` 过滤。
- **真实模型**：通过 OpenAI 兼容接口配置 `deepseek-flash`；增长率和总额两次 API 调用均通过
  （8 个步骤，含模型/查询/声明/回答/验证），页面也显示“模型生成声明 · deepseek-flash”；
  重启后两份报告仍完全一致。故意使用无效模型名时得到
  `tool_error/model_error`，响应不含密钥；随后恢复有效模型。
- **Windows 清理（#11）**：最终版本执行 20 次查询后 `%TEMP%` 无新增 `harness-sales-*` 目录；
  23 个残留目录均为 2026-10-31 旧版本留下（含 sales.db），未删除；
  查询清理测试在 Windows 上 2 项通过。
- **限制**：仅固定合成数据、单进程、Playwright 驱动、单一模型；独立复现和课程视频另行完成。

机器可读证据见同目录 `sprint3-windows-live-acceptance-2026-11-17.json`；本地截图、日志、
API 导出和哈希清单在 `D:\Temp\edah_acceptance_2026-11-17\`。

## Demo video (local artifact)

Recorded from the accepted commit on the same Windows machine:

```text
CS5351_Sprint3_DataAgentHarness_Windows_Demo_2026-11-17.mp4
66.4 s, 1280x720, silent with Chinese captions (title -> fixed cases -> one-cent
trace -> single run -> live model -> restart history -> result card).
SHA-256 e1581e13d27f86e487e1dee6b460c63182c72b8014097c51d54e7ba688bd24e2
```

The MP4, its narration script and the raw segments stay under
`D:\Temp\edah_acceptance_2026-11-17\video-demo\` and are intentionally not
committed; the course submission can upload the MP4 separately. The video shows
the accepted `main@45216b1` build and matching reports; it does not add new
features or claim live-provider independence.
