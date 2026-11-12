# Sprint 2 CI stability repair

Date: 2026-11-12 (Asia/Shanghai). Base: `main@67153cd`.
Scope: test timing and browser CI provisioning. No application code, numerical
tolerance, expected result, supported workload or production timeout is changed.

## Observed failures

- [Windows job 130648782882](https://github.com/NobunagaK/enterprise-data-agent-harness/actions/runs/43056934453/job/130648782882):
  86 passed, 1 failed. The final-save regression imposed a 0.3-second deadline on
  every case. Healthy case `a` timed out (reported duration 439 ms), so the test
  failed before establishing the intended storage-failure behavior.
- [Playwright job 130648782832](https://github.com/NobunagaK/enterprise-data-agent-harness/actions/runs/43056934453/job/130648782832):
  Ubuntu package installation failed with `Temporary failure resolving
  'azure.archive.ubuntu.com'`. The browser tests did not start. This was an
  environment provisioning failure, not a browser assertion failure.

## Changes and rationale

Storage-failure scenarios now run without a case deadline. The actual timeout
scenario still uses `asyncio.wait_for` against a deliberately blocked execution,
with a five-second test budget to accommodate healthy SQL/database work on CI.
The test additionally records `CancelledError` and checks that cancelled run IDs
are exactly the initially persisted IDs retained by the batch. Existing checks
for repeated IDs, initial/final-save failures and earlier/later reports remain.
The five seconds is a test setting, not a new NFR or production default.

The E2E job uses the official `mcr.microsoft.com/playwright:v1.59.1-noble` image,
matching `frontend/pnpm-lock.yaml`. Browsers and system libraries are preinstalled,
so the job no longer runs `playwright install --with-deps` or contacts Ubuntu APT
mirrors to provision Chromium. The complete Playwright test command is unchanged.
Windows/E2E jobs have 10/15-minute job limits so a stalled check cannot run for
hours. Failures remain failures; no test retry or `continue-on-error` is added.

Maintenance: update the image version together with the locked Playwright package.
The image still needs registry connectivity; it does not remove all network
dependencies or guarantee that a registry outage cannot occur.

## Verification

Fresh cloud Linux / Python 3.12 checks:

- Controlled reproduction before repair: delay healthy cases `a` and `c` by
  400 ms in a temporary pytest fixture wrapping `runner.execute`; the original
  final-save regression fails with a healthy case classified as `timeout`.
- After repair, the same delay applied to the lifecycle file: **4 passed**.
- Harness suite (`test_harness.py`, `test_harness_contracts.py`,
  `test_harness_batch.py`, `test_harness_batch_lifecycle.py`): **87 passed**.
- Ruff lint/format and diff whitespace checks passed. Workflow YAML parsed;
  image version matches the installed-package version in the lockfile, and the
  full browser test command is retained.
- Local Docker image download was blocked with `Forbidden`; no local container
  pass is claimed. The PR is initially draft so GitHub can validate Windows and
  the actual browser container. Record remote results on the PR before marking
  it ready for review; do not substitute historical checks for the new head.

This repair does not close #19 (production timeout/resource policy), #20 (trace
status evidence), #21 (source-override regressions), or #11/#12 acceptance work.
No human review, meeting or real-model experiment is implied by these tests.

---

# 中文：Sprint 2 CI 稳定性修复

日期：2026-11-12（北京时间）；基线：`main@67153cd`。
范围仅为测试计时及浏览器 CI 环境，不修改应用代码、业务容差、预期结果、支持范围或生产超时。

Windows 日志为 86 通过、1 失败：保存失败测试给每个案例都设了 0.3 秒截止时间，
正常案例也被误判超时。Playwright 日志显示 Ubuntu 软件源 DNS 解析失败，
安装依赖失败后测试尚未开始。原始日志链接见英文部分。

保存失败场景现在不设置案例截止时间；真实超时场景仍阻塞执行并由 wait_for 实际取消，
测试预算为 5 秒，额外断言取消的运行编号与保留的已保存编号完全一致。
保留前后报告、重复运行、初态/终态保存失败等断言。5 秒只用于测试，不是新增业务性能承诺。

E2E 改用与锁文件匹配的官方 Playwright 1.59.1 Noble 镜像，复用预装浏览器及系统库，
不再运行依赖 Ubuntu 软件源的安装步骤，完整浏览器测试命令不变。
Windows/E2E 作业分别设置 10/15 分钟上限，不忽略错误、不增加测试重试。
后续升级 Playwright 时应同时升级镜像；镜像仓库网络仍是运行依赖。

本次本地验证：给正常案例加入 400 毫秒延迟后，旧测试复现失败；修复后相同条件下
生命周期 4 项通过；Harness 87 项通过；Ruff、格式、差异空白及工作流结构/版本检查通过。
云环境拉取镜像返回 Forbidden，未声称本地容器验证通过。
先用草稿 PR 验证真实 GitHub Windows/容器 CI，远程结果记录在 PR，通过后再转正式评审。
不使用旧提交的测试冒充新验证；不自动关闭其他技术债或验收 Issues，不代填人工评审。
