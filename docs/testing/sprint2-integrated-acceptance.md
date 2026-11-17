# Sprint 2 integrated acceptance

Executed **2026-11-17 (Asia/Shanghai)**: fixed-case prototype acceptance with
actual SQL, report persistence and browser integration. This does not declare
final course, native-Windows UI or live-provider acceptance.

## Revision and environment

| Item | Value |
|---|---|
| Main before integration | `536877aeab220e27c0b985a4c9ea28e7cfc1b923` (#26/#28 included) |
| Reviewed #27 head | `8c46e3ee109d71fbaa1c9760acac3f32bbe02c06` |
| Local test merge (local only) | `665196783a4c14238a0cd1a92e1d1018259b9ddc` |
| Final main | `45216b1cdbb3d5f108ba39f4a0dbf4873cce8b3b` |
| Identical integration/main Git tree | `b6a794d7a7635a3b33e61e542dc36673cd9d6085` |
| Cloud | Linux x86_64, Python 3.12.14, Node 24.19.0, pnpm 11.25.0 |
| Dependencies | SQLAlchemy 2.0.49, Pydantic 2.13.1, pytest 9.0.3, LangChain 1.2.15, LangGraph 1.1.6 |
| Browser | Chromium 154.0.8037.57, Playwright 1.59.1 |

The independent checkout reused dependencies after verifying identical Python
and frontend lockfiles/package metadata. `PYTHONPATH` selected that checkout and
the loaded module path was checked. This was not a fresh local installation;
GitHub CI installed dependencies independently. Existing dirty documentation
worktrees were preserved. The cloud main checkout was fast-forwarded after merge.

## Fresh checks

| Local check | Result |
|---|---|
| Backend unit + MCP | **594 passed** (588 + 6), 42.41 s |
| Frontend Vitest | **78 passed**, 8 files |
| Complete configured Playwright suite | **44 passed**, 41.7 s |
| TypeScript/Vite build | Passed; existing large-chunk advisory |
| ESLint | 0 errors, 7 existing warnings |
| Ruff lint / format | Passed, 113 files formatted correctly |
| Mypy | Passed, 78 source files |

Equivalent clean-checkout commands:

```text
uv sync --frozen --extra dev
pnpm --dir frontend install --frozen-lockfile
uv run pytest tests/unit tests/integration/test_mcp_transports.py -q
uv run ruff check backend/src tests scripts/benchmark_harness_trace.py
uv run ruff format --check backend/src tests scripts/benchmark_harness_trace.py
uv run mypy backend/src/analytics_agent
pnpm --dir frontend test
pnpm --dir frontend lint
pnpm --dir frontend build
npx --prefix frontend playwright test --config tests/e2e/playwright.config.ts
```

Use the repository browser setup; cloud set `HARNESS_CHROMIUM_PATH=/usr/bin/chromium`.
The E2E suite mocks chat/model streaming; fixed Harness cases still execute actual
SQL and persistence. Dummy-key greeting retries are not live-provider evidence.

Preliminary attempts are not counted as passes: the restricted sandbox stalled
during async SQLite bootstrap and was stopped; the first normal-environment run
had 593 passes and one benchmark refusal because the temporary merge was
uncommitted. Recording the same tree as a local commit satisfied its provenance
guard. The complete 594-test rerun passed without changing application code or assertions.

All **9 final-main CI jobs passed**, separately from local checks:

| Job | Result |
|---|---|
| [Backend](https://github.com/NobunagaK/enterprise-data-agent-harness/actions/runs/44067971815/job/133986503969) | 588 passed |
| [MCP](https://github.com/NobunagaK/enterprise-data-agent-harness/actions/runs/44067971815/job/133986504371) | 6 passed |
| [Windows Harness](https://github.com/NobunagaK/enterprise-data-agent-harness/actions/runs/44067971815/job/133986503765) | 231 passed |
| [Windows benchmark](https://github.com/NobunagaK/enterprise-data-agent-harness/actions/runs/44067971815/job/133986503734) | 9 passed |
| [Browser](https://github.com/NobunagaK/enterprise-data-agent-harness/actions/runs/44067971815/job/133986503725) | 44 passed |
| [Frontend](https://github.com/NobunagaK/enterprise-data-agent-harness/actions/runs/44067971815/job/133986503808) | 78 tests, build/lint/type checks passed |
| [Backend static](https://github.com/NobunagaK/enterprise-data-agent-harness/actions/runs/44067971815/job/133986503506) | Passed |
| [DataHub integration](https://github.com/NobunagaK/enterprise-data-agent-harness/actions/runs/44067972019) | Passed |
| [Image build](https://github.com/NobunagaK/enterprise-data-agent-harness/actions/runs/44067971790) | Passed |

## Actual HTTP and restart checks

Final main ran against isolated SQLite after explicit `analytics-agent bootstrap`
(migrations through **007**), with one Uvicorn process on port 8100.

1. Read the catalog and POST both bundled sets through the real API.
2. Growth: **10 completed**, 2 passed / 4 failed / 4 unverifiable.
3. Mixed: **8 completed**, 3 passed / 2 failed / 3 unverifiable.
4. GET all **18 distinct runs/evidence IDs**; verify test-injected source, null
   model, rule/unit, actual SQL/rows, same-run evidence, claim reference, completed
   query association and expected-result matches.
5. POST another mixed batch with test-only `batch_timeout_s=0.000001`: actual
   `timed_out`, `batch_timeout`, 0 attempted / 8 skipped. This is not a recommended
   budget or measured response-time guarantee.
6. Stop the server, restart against the same database and compare full JSON:
   **all 18 runs and all 3 batches remained equal**.

The [machine-readable artifact](measurements/sprint2-integrated-acceptance-2026-11-17.json)
includes raw synthetic reports/batches, IDs/hashes, environment and check summaries.
No live model was called by these checks; no credentials or customer data appear.
The canonical SHA-256 of the artifact's `capture.batches` and `capture.runs`,
serialized as an object with those two keys, sorted keys, compact separators and
UTF-8 (`ensure_ascii=False`), is:

`7504f54d4b67ac2df55334e618b6279876ca806063d1f3226e0782b63a2d347a`

Example normal POST `/api/harness/batches`:

```json
{"case_set_id":"sprint2-sales-mixed-v1","case_timeout_s":60,"batch_timeout_s":300}
```

Retrieve `/api/harness/batches/{id}` and each `/api/harness/runs/{run_id}` before
and after restart. This restart occurred after terminal saves; it does not prove
recovery of uncommitted work after a process crash. Closing a tab is not a promise
of server cancellation.

## Fault evidence and limits

- Mixed-case tests deliberately inject a middle SQL failure and verify separate
  tool-error counting plus readable earlier/later reports. Normal HTTP batches
  above contain no injected fault.
- Batch/lifecycle tests cover blocked cases, per-case continuation, whole-batch
  expiry, repeated cancellation, failed terminal writes, concurrent isolation,
  legacy reads and read-only interrupted projections.
- Four close-order regressions use a real one-connection SQLite pool, no overflow,
  and controlled delayed close under expiry/repeated cancellation in case/metadata
  cleanup. They verify release before saving, preserved prefix and unstarted tail.
- Browser interruption display uses response fixtures; actual cancellation and
  SQL/cleanup behavior are established by backend tests.
- #28's earlier performance record keeps its exact version/offline scope. This
  run checks benchmark correctness, not a new overhead measurement.
- Complete Windows installation/UI and actual-provider saved-report acceptance
  remain Sprint 3 tasks. #30's unpublished local provider observation is separate.

---

# 中文：Sprint 2 集成验收

执行日期：**2026-11-17（北京时间）**。范围为固定案例、实际 SQL、持久化和浏览器集成，不代表最终课程、
完整 Windows UI 或真实模型验收。合并前 `536877a`，#27 头 `8c46e3e`，本地测试合并 `6651967`，
最终 main `45216b1`；本地与最终 Git tree 均为 `b6a794d7a7635a3b33e61e542dc36673cd9d6085`。

Linux/Python 3.12.14/Node 24.19.0/pnpm 11.25.0/Chromium 154/Playwright 1.59.1。
确认锁文件/包元数据相同后复用依赖，并核对实际加载路径，不冒充本地全新安装；CI 独立安装。
其他目录原有文档改动保留，主目录在合并后快进。

本次后端/MCP **594（588+6）**、前端 **78**、浏览器 **44** 项通过；构建、Ruff、mypy 通过，
113 个文件格式正确、78 个源码文件类型检查通过。ESLint 0 错误/7 条已有警告，保留大包提示。
预备沙箱调用停在异步数据库初始化后停止；第一次普通环境为 593 通过/1 项基准拒绝未提交目录，
相同代码保存为本地提交后全套 594 项通过，没有改断言或业务代码。假凭据的 greeting 重试不计真实模型验证。

最终 main **9 个 CI 作业全通过**，包括后端 588、MCP 6、Windows Harness 231、Windows 基准 9、
浏览器 44、前端 78、静态检查、DataHub 和镜像；链接与复现命令见英文部分。

独立 SQLite 迁移到 007，单进程启动实际服务。HTTP 原 10 例为 2/4/4，混合 8 例为 3/2/3；
核对 18 个独立运行/证据、来源、单位、SQL 数据和关联。另用测试预算 0.000001 秒触发真实整批到期，
得到 timed_out、0 已尝试/8 未执行。停止服务并使用同库重启后，18 份报告和 3 个批次的完整 JSON 全部一致。
附件含合成数据原始报告、批次、编号/哈希及环境结果，无凭据或客户数据；英文部分说明哈希复核。
重启发生在终态保存后，不宣称崩溃时未提交数据可恢复，也不把关闭网页当作服务端取消。

中间 SQL 故障、真实阻塞、单例继续、整批停止、重复取消、保存故障、并发隔离和旧快照由后端测试证明；
单连接池四种清理竞态属于明确标识的故障注入。浏览器中断展示采用响应夹具。
#28 历史性能保持原范围；完整 Windows UI、真实模型持久化链路和 #30 本地观察的公开证据另行验收。
