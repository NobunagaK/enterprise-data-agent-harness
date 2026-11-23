# Sprint 3 delivery checklist

Status reviewed on 24 November 2026 (Asia/Shanghai). The GitHub baseline was `d7f1f52`. This checklist covers the agreed course prototype and the remaining course submission. Mark a task complete when its evidence is available. A file submitted separately to Canvas can be linked in the private team handoff.

1. **Finish technical acceptance**
   - Review the reproduction and UI fixes, run checks on the accepted revision and record its full commit hash. The [README](../../README.md) contains the course checkout, installation, bootstrap, single-worker startup and a worked example.
   - Complete the native Windows cleanup check on that revision. Record Windows/Python versions, both successful and faulty SQL execution, fixture directory inventories before and after, and the test log. Attach the evidence to [#11](https://github.com/NobunagaK/enterprise-data-agent-harness/issues/11).
   - Have another member reproduce the configured provider flow. Retain sanitized growth and total reports, the observed error case, matching run/evidence IDs and complete API exports before and after restart. Check the saved results and record the reviewer's actual conclusion in [#12](https://github.com/NobunagaK/enterprise-data-agent-harness/issues/12). Start from the [existing Windows and provider record](../testing/sprint3-windows-live-acceptance-2026-11-17.md).
2. **Write the evaluation and maintenance material**
   - Define the developer task being compared, the baseline tool or workflow, the changed behavior, the labeled cases, the measurement conditions and the decision criteria. Keep the fixed sales scope and the [frozen evaluation contract](../design/sprint1-evaluation-contract.md).
   - Count attempted, passed, failed, unverifiable and tool-error cases separately. Give the denominators for error detection, false alarms, verifiability and valid evidence links. Compare actual outputs with independently established expected results. Report overlaps between case sets, unsupported inputs, failures and limitations. Keep fixed claims and live-provider observations in separate populations.
   - Cite the existing [trace performance study and raw measurements](../testing/sprint2-trace-performance.md) for the operations it measured. Record the two NFRs, evidence for failure isolation and the actual changes needed to add the second rule using the [requirements mapping](../design/sprint2-requirements-acceptance.md).
   - Finish the Sprint 3 test/debugging handoff. List test purposes and commands, environments, results and skip reasons. Trace each repaired defect to its reproduction, fix and regression. Link the [offline audit guide](../testing/sprint3-trace-acceptance.md), [user guide](../traceability-user-guide.md), restart evidence, screenshot and remaining debt.
3. **Complete the software-process record**
   - Summarize the three sprints, about two report pages per sprint. Record goals, planned and delivered stories, design decisions, tests, reviews, debts, changes and what the team improved. Link dated Issues, PR discussions, commits and CI jobs.
   - Assemble the real weekly records and remaining-work observations for the whole-project burndown. Identify the unit, dates, scope changes and evidence gaps. Retrieve records from members if available. Mark missing weeks or estimates explicitly. See the [Sprint 2 retrospective](sprint2-review-quality-retrospective.md) and [debt register](sprint2-debt-risk-register.md).
4. **Prepare the final report and individual contributions**
   - Use the IEEE Transactions on Software Engineering format. Target around 10,000 words excluding figures/tables, self-reflections and references. Include an informative title, the team name, each member's name and Student ID, and an abstract of about 150 words.
   - Write the introduction, related work and technical background. Credit the upstream Analytics Agent, distinguish the team's contributions and state the developer problem the Harness addresses.
   - Assemble the solution, three-sprint process, baseline comparison and evaluation, conclusion and references. Walk through a claim, the real SQL result, the verification decision and its trace. Explain architectural choices for reliability and modifiability.
   - Obtain each member's own biography, reflection, actual contributions and supporting evidence. Agree on the relative-contribution statement. Use verified contribution records and the official course roster.
5. **Prepare and submit the presentation, video and code**
   - Prepare slides for the roughly seven-minute presentation. Cover motivation, related work, challenge, contribution, solution, evaluation and limitations.
   - Obtain the reported local Windows MP4 and check playback, version and contents. Demonstrate the accepted end-to-end workflow, including a failed claim and its SQL evidence, and explain a significant process improvement and its reason. Complete the video if either part is missing.
   - Record the final GitHub revision, reproducible setup, report, slides, video and actual submission receipts in the delivery index. The project slides schedule the presentation material for Week 12 and the report and source code for Week 13. Verify actual dates and upload instructions against Canvas.

Course references supplied by the team: *week1-cs5351-project.pdf*, pp. 4–6 (engineering activities and video), 14 and 16–20 (contributions and final deliverables), 24–29 (measurement and evidence). The project-specific scope comes from *数据分析agent.md*, *Agent_Harness_开发计划 2.md* and *SE项目流程清单.pdf*. Fixed growth and total rules, trace inspection and batch evaluation are the accepted implementation.

---

# Sprint 3 待交付清单

核查日期为北京时间 2026 年 11 月 24 日，GitHub 基线为 `d7f1f52`。已在其他地方完成的材料可凭成品或提交回执勾销。

1. **完成最终技术验收**
   - 评审安装说明及界面修复，核对最终版本的检查结果，在复现记录中写完整提交号。
   - **Windows 清理（#11）**：在最终版本各执行一次成功查询与故障查询，保留系统和 Python 版本、测试日志及临时目录前后清单，贴到 Issue。
   - **真实模型和独立复现（#12）**：由另一位成员配置模型，执行增长率、总额及错误案例，保存脱敏报告、关联 ID、重启前后的完整 JSON 和实际验收结论。可复用原有四份报告及截图。
2. **完成正式评估和维护文档**
   - 写清开发者原来如何定位错误、用哪个版本或既有工具作基线、改了什么、用哪些预标注案例和固定条件比较。
   - 列出错误检出、误报、可验证比例、证据关联、批次执行完整性及各自分母。固定注入与真实模型分开统计，保留无法验证、工具错误、两组案例重叠及数据规模限制。引用现有轨迹性能测量并说明适用范围。
   - 写出可靠性、可修改性各自的设计选择、理由和验收证据。补 Sprint 3 自动测试目的、命令、环境、通过及跳过原因、具体调试和回归案例，链接安装、报告导出、故障排查与已知限制。
3. **整理三轮过程与技术债**
   - 每轮约两页，按目标、用户故事、计划与实际、设计取舍、评审及修复、剩余问题、回顾及改进组织，附真实的 Issue、PR、提交及 CI。
   - 查找真实周记录及剩余工作量，注明单位、时间和范围变更，制作全项目燃尽图。有缺失就标明，工时、会议和估算只采用有依据的数据。
   - 更新技术债与风险的处置结果，标注已修复事项、仍需验收事项、接受的单进程及协作超时等原型限制。
4. **定稿课程报告及成员材料**
   - 采用 IEEE TSE 格式，正文约 10,000 词，图表、个人反思和参考文献不计。首页写项目标题、团队名、成员姓名和 Student ID，摘要约 150 词。
   - 完成引言、相关工作、背景、方案、三轮软件过程、评估、结论与参考文献。明确上游与本组贡献，用实际案例贯穿声明、SQL、证据和判定。
   - 按正式成员名单收齐个人简介、本人反思、实际贡献及依据，形成相对贡献说明。
5. **完成展示、视频与提交**
   - 准备约七分钟的展示，涵盖问题、动机、相关工作、技术挑战、方案、创新、评估及局限。
   - 取得成员本机的视频文件，核验可播放性和版本。演示完整程序、失败案例及其 SQL，并解释一项实际的开发过程改进及原因。按已录内容决定补录哪些片段。
   - 汇总最终 GitHub 提交号、运行说明、报告、展示、视频及提交回执。课件安排为第 12 周交展示材料、第 13 周交报告与代码，实际截止时间和上传方式以 Canvas 为准。
