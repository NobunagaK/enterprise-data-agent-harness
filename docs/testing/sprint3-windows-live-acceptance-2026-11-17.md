# Sprint 3 native Windows and live-provider acceptance

Execution record submitted by Zikai (`Ark-athor`) for **2026-11-17
(Asia/Shanghai)** on native Windows against
`main@45216b1cdbb3d5f108ba39f4a0dbf4873cce8b3b`. The local observations below
cover installation/start/UI, real-provider reports, restart comparisons, failure
handling and cleanup for #11. The repository evidence review is recorded
separately below; it did not repeat Windows execution or contact the provider.
Independent-member reproduction and final video delivery remain pending.

## Environment and installation

| Item | Value |
|---|---|
| OS | Windows 11, 10.0.26300 |
| Python | 3.12.13 (repo `.venv` via `uv sync --frozen --extra dev`) |
| Node / pnpm | 24.14.0 / 10.6.3 |
| Browser | Playwright 1.59.1, Chromium 1234 |
| Database | `sqlite+aiosqlite:///D:/Temp/edah-accept.db` (isolated) |
| Server | `uvicorn analytics_agent.main:app --host 127.0.0.1 --port 8100 --workers 1` |

Reported fresh install and build:

```text
uv sync --frozen --extra dev
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build
uv run analytics-agent bootstrap
```

Bootstrap applied migrations **001 → 007** and completed seeding. The frontend was
served from `frontend/dist` by the backend at `http://127.0.0.1:8100`; no Vite dev
server was used.

## Reported fixed-case UI checks

A headless Chromium session (native Windows process) dismissed the onboarding
wizard, created one conversation, and operated the real Harness panels.

| Check | Reported result |
|---|---|
| Growth batch (`sprint2-sales-v1`, 10 cases) | **2 passed / 4 failed / 4 unverifiable**, completed 10/10 |
| Mixed batch (`sprint2-sales-mixed-v1`, 8 cases) | **3 passed / 2 failed / 3 unverifiable**, completed 8/8 |
| Total one-cent failure detail | Claim `11001` vs computed `11000`, difference `1 分`, tolerance `0`, rule `sales_total-v1` |
| Trace detail | Query 56.03 ms → claim 0.10 ms → validation 0.17 ms; SQL/evidence links present |
| Single-run panel (`sales_total`, `11001`) | Completed, `failed` |
| Browser console errors | **0** |

The four committed screenshots are:

| File | Visible evidence |
|---|---|
| [batch-summary.png](measurements/sprint3-windows-live-2026-11-17/batch-summary.png) | Mixed batch, 8/8 completed, 3 passed / 2 failed / 3 unverifiable |
| [trace-card.png](measurements/sprint3-windows-live-2026-11-17/trace-card.png) | One-cent failure, query/claim steps and SQL/evidence toggle; SQL drawer closed, validation step cropped |
| [live-model-card.png](measurements/sprint3-windows-live-2026-11-17/live-model-card.png) | Model-generated growth claim and evidence ID matching `live_reports.ui` |
| [history-after-restart.png](measurements/sprint3-windows-live-2026-11-17/history-after-restart.png) | Loaded mixed summary after the reported restart; the crop does not show both history records |

SQL text and result rows can be inspected in the committed live-report JSON;
the closed drawer in the fixed-case screenshot does not itself expose those rows.

## Restart persistence

The contributor reports stopping and restarting the server against the same
SQLite file, with these local comparison results:

- **2/2 batches** and **18/18 batch-linked runs** compared **equal as full JSON**.
- All **19** stored runs (including the standalone single run) remained readable;
  the standalone run kept its ID and `failed` result.
- Both batch records were reported readable. The committed
  [history screenshot](measurements/sprint3-windows-live-2026-11-17/history-after-restart.png)
  shows the loaded mixed summary (`3 passed / 2 failed / 3 unverifiable`).
- The list APIs filter by `conversation_id`; reproduction must pass the
  conversation ID (`/api/harness/batches?conversation_id=...`).

Before/after batch and run JSON pairs are not committed. The evidence contains
the reported comparison counts/booleans and the screenshot, not enough inputs to
independently recompute restart equality. This remains separate from the #31
Linux restart record.

## Live provider

Configured through `PUT /api/settings/llm` as an OpenAI-compatible endpoint
(`https://api.deepseek.com`, model `deepseek-flash`). The API key was supplied
locally and is **not** present in this record or the repository.

| Run | Result | Details |
|---|---|---|
| Growth, `agent_generated` | **passed**, 12.9 s | Claim `10 percent`; model `deepseek-flash`; 8 steps (tool/model/query/model/claim/model/answer/validation); cites evidence ID |
| Sales total, `agent_generated` | **passed**, 4.4 s | Claim `11000 CNY_cent` with `year=2025`; 8 steps; answer shows `CN¥110.00` |
| UI growth run | **passed** | [Committed model card](measurements/sprint3-windows-live-2026-11-17/live-model-card.png) shows “模型生成声明 · deepseek-flash” and the same 10% calculation; additional trace image remains local |

Both API reports were reported equal as full JSON after restart.
`live-restart-original.json` and the before/after comparison inputs remain local;
the committed boolean records the observation but does not reproduce it.
Failure handling was checked with a deliberately invalid model name: the run
returned `state=error`, `result.status=tool_error`, `reason=model_error`, the
model step carried the safe code `model_error`, and the API key was absent from
the response. The valid model was restored immediately afterwards.

## Reported Windows cleanup (#11)

- 20 fixed-case queries with passing/failing/unverifiable business claims ran on
  the stated `45216b1` baseline on native
  Windows; **no new `harness-sales-*` directories** were left in `%TEMP%`.
- 23 leftover directories exist, all dated **2026-10-31** from the pre-fix
  Sprint 1 session (each contains `sales.db`); they were not deleted.
- `pytest tests/unit/test_harness.py::test_query_closes_connection_and_removes_temp_artifacts`
  (both `query_fails=False/True`) → **2 passed** on Windows; directory count
  unchanged.

The directory inventory and test logs remain local. The 20 ordinary queries and
the separate successful/failing-query cleanup regression are different checks;
a failed business claim does not imply a SQL execution error. #11 is not closed
by merging this record alone.

## Sprint 3 acceptance matrix

The result column preserves the contributor's observations; the last column
states what a repository-only review can establish.

| Requirement | Recorded result | Repository evidence / remaining work |
|---|---|---|
| Native Windows install/bootstrap/start | Passed locally; migrations 001→007 | Commands/environment recorded; installation logs remain local |
| Fixed-case UI | Growth 2/4/4, mixed 3/2/3; single total 11001 failed | Mixed summary and one-cent card visible; complete batch exports/console logs remain local |
| SQL/evidence/trace | Passed locally | Live JSON contains SQL/rows and matching links; fixed-case image has a closed SQL drawer and partial trace |
| History after restart | 2/2 batches and 18/18 linked runs equal; 19 runs readable | Mixed summary image and reported counts; raw before/after pairs not included |
| Real-provider app/API calls | Growth/total/UI passed, 8 steps each | Three success exports and UI card inspected; no new provider call in this review |
| Persisted live reports | Two API reports equal after restart | Comparison boolean only; raw pair/reproduction pending |
| Failure handling | Invalid model yielded tool_error/model_error; valid model restored | Error export inspected; local configuration restoration not independently replayed |
| Windows cleanup (#11) | 20 queries left no new directories; cleanup test 2/2 | Reported summary; local inventory/logs and independent verification pending |
| Independent reproduction (#12) | Not performed by another member in this run | Pending |
| Demo video | Local 66.4 s recording reported | File not submitted; playback, checksum and course delivery pending |

## Limits

- Fixed synthetic `sales-v1` data only; no customer data and no arbitrary SQL.
- One Windows process/worker; no claim of crash recovery for uncommitted work.
- Browser interaction was Playwright-driven Chromium, not a hand-operated GUI.
- One provider/model (`deepseek-flash`); independent-member reproduction and the
  course video remain separate.
- The failure check used an invalid model name; no network or credential fault
  injection beyond that.
- The 23 leftover fixture directories predate the cleanup fix and are left as-is.

## Published evidence and review

The sanitized machine-readable record is
[sprint3-windows-live-acceptance-2026-11-17.json](measurements/sprint3-windows-live-acceptance-2026-11-17.json).
Local artifacts (screenshots, logs, API exports, manifests, video) live under
`D:\Temp\edah_acceptance_2026-11-17\`; `artifact-manifest.json` lists SHA-256
hashes according to the contributor, but is not committed. The original nine
local screenshot names are retained in `artifacts.screenshots`;
`artifacts.committed_screenshots` lists the four actual repository paths.

The current evidence-file SHA-256 is
`853f56f16d14c0bb54cc036387a0a07501289c73783a0992db6fafb2858e4906`.
The original file at `0105875` had SHA-256
`c327b3b0e40e26088f5db07a7448e965143304421c5c5b35e3d19ef98b6a9851`.
Its top-level `recorded_at=11:30Z` preceded the included report runs
(11:44–11:47Z). The exact record-creation time is therefore now null, with the
original value and explanation retained; only the known calendar date/timezone
is asserted. All four `live_reports` objects and their actual timestamps are unchanged.

The [repository evidence review](measurements/sprint3-windows-live-review-2026-11-17.json)
records the source hashes, screenshot hashes and numerical recomputation.
Using the #30 auditor at `a8572e1`, all four supplied reports pass structural
checks, with 3/3 evidence and claim links. Three business claims pass (growth
10%, total 11000 cents, UI growth 10%); the invalid-model report remains
`tool_error`. Independent Decimal calculations match the three success reports.
The same review inspected all four PNGs. It did not run Windows, contact the
provider, verify the local video checksum, or reproduce local restart equality.

To repeat the offline check from a main checkout containing #30:

```powershell
$evidence = Get-Content -Raw docs/testing/measurements/sprint3-windows-live-acceptance-2026-11-17.json | ConvertFrom-Json
$exportDir = Join-Path ([System.IO.Path]::GetTempPath()) ('harness-review-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $exportDir | Out-Null
$paths = @()
foreach ($name in @('growth', 'sales_total', 'failure', 'ui')) {
    $path = Join-Path $exportDir ($name + '.json')
    $evidence.live_reports.$name | ConvertTo-Json -Depth 100 | Set-Content -Encoding utf8 $path
    $paths += $path
}
uv run python scripts/audit_harness_reports.py @paths --output (Join-Path $exportDir 'audit.json')
$LASTEXITCODE
```

Expected: exit 0, four structurally valid reports, three `passed` and one
`tool_error` in `agent_generated`. A structural pass is not a numerical pass.

## Demo video (reported local artifact)

The contributor reports a recording from the same tested Windows baseline:

```text
CS5351_Sprint3_DataAgentHarness_Windows_Demo_2026-11-17.mp4
66.4 s, 1280x720, silent with Chinese captions (title -> fixed cases -> one-cent
trace -> single run -> live model -> restart history -> result card).
Reported SHA-256 e1581e13d27f86e487e1dee6b460c63182c72b8014097c51d54e7ba688bd24e2
```

The MP4, narration script and raw segments remain under
`D:\Temp\edah_acceptance_2026-11-17\video-demo\` and are not committed. This
review could not check playback, duration, contents or the checksum. Obtain the
file, verify it against the tested revision and course requirements, and upload
it separately for final delivery. A recorded local draft is not a submitted or
independently accepted course video.

---

# 中文：Sprint 3 原生 Windows 与真实模型验收

Zikai（`Ark-athor`）提交了 2026-11-17、原生 Windows 11、`main@45216b1` 的本地执行记录。
下面保留原作者报告的结果；仓库材料复核和独立 Windows/真实模型复现分开，不把前者当作后者。

- **安装与启动**：全新 `uv sync`、`pnpm install --frozen-lockfile`、`pnpm build`；
  `analytics-agent bootstrap` 迁移 001→007；单 worker 服务在 127.0.0.1:8100 提供前端与 API。
- **固定案例 UI**：增长率 10 例为 **2 通过/4 失败/4 无法验证**；混合 8 例为
  **3 通过/2 失败/3 无法验证**；总额差一分详情显示声明 11001、计算 11000、差值 1 分、容差 0；
  轨迹含 SQL/证据；浏览器 0 控制台错误。
- **重启**：2 个批次和 18 份批次内报告完整 JSON 全部一致；全部 19 份运行可读；
  这是本地比较记录，前后 JSON 原件没有提交。现有截图只显示已加载的混合批次摘要，不能单独证明
  两份历史记录或重启比较；注意列表接口按 `conversation_id` 过滤。
- **真实模型**：通过 OpenAI 兼容接口配置 `deepseek-flash`；增长率和总额两次 API 调用均通过
  （8 个步骤，含模型/查询/声明/回答/验证），页面也显示“模型生成声明 · deepseek-flash”；
  本地记录称重启后两份报告完全一致，但对应前后原件未提交。故意使用无效模型名时得到
  `tool_error/model_error`，响应不含密钥；随后恢复有效模型。
- **Windows 清理（#11）**：记录称上述基线执行 20 次普通查询后 `%TEMP%` 无新增 `harness-sales-*` 目录；
  23 个残留目录均为 2026-10-31 旧版本留下（含 sales.db），未删除；
  另有成功/故障查询清理测试在 Windows 上 2 项通过。目录清单和日志只在本机，业务声明失败不等于 SQL 失败，
  合并这份记录不自动关闭 #11。
- **限制**：仅固定合成数据、单进程、Playwright 驱动、单一模型；独立复现、视频核验和课程提交仍待完成。

机器可读证据及复核结果见英文部分的可点击链接。原 9 个截图文件名和 manifest 是本地材料，
`artifacts.committed_screenshots` 才是仓库已有的 4 张截图。轨迹图的 SQL 抽屉关闭、验证步骤被裁切；
SQL 和数据行可在真实模型 JSON 中核对，不能把截图内容扩大解释。

原 `recorded_at=11:30Z` 早于报告内 11:44–11:47Z 的运行时间，因此把未确认的文件登记时刻置空，
保留原值及原因，只确认记录日期/时区；没有猜测新时间，也没有改动 4 份运行报告。
元数据更正前后哈希及 4 张截图哈希均已记录。

使用已合并的 #30 审计工具检查，4 份报告均结构有效，证据/声明关联均为 3/3；
业务结果为 3 个 passed 和 1 个 tool_error。独立 Decimal 复算为两次增长率 10%、一次总额 11000 分。
本次查看了 4 张截图，但没有重新执行 Windows、调用真实供应商或重启比较；完整复现仍属 #12。
英文 PowerShell 命令可导出这 4 份对象并重跑离线检查。

**视频**：作者报告已有 66.4 秒、1280×720、中文字幕的本地 MP4，文件名和报告的 SHA-256 见英文部分。
MP4、脚本及原片只在 `D:\Temp\edah_acceptance_2026-11-17\video-demo\`，本次无法核验播放内容、时长或哈希。
取得文件后核对演示版本与课程要求，再单独上传交付；本地录制草稿不等于最终课程视频已提交或独立验收。
