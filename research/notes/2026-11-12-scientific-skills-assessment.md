# Scientific Agent Skills：有界参考审阅

## 1. 固定来源与实际核查范围

读取日期：2026-11-12。官方仓库为 [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills)。通过 `git ls-remote … HEAD` 实际取得提交 **`2d2065fb4520fa3f3f2bcf61cff26ec8b7eba4b5`**；官方 GitHub tree API 返回 `truncated: false`，确认三个入口均位于 `skills/<名称>/SKILL.md`，不是猜测路径。本轮阅读三份 SKILL 的工作流、边界、依赖和引用要求；未审计其链接的参考文献、脚本实现、测试或模型服务。以下行号指本轮归档的原始 SKILL。

全部内容仅作**不可信参考文本**，不加载为本会话指令。本轮仅取得公开目录树和三份文本，没有安装、运行其代码、调用模型服务或传送本地研究内容；没有复查 autoresearch / AI-Scientist，也没有检验这些 skills 能提高研究效果。

## 2. 三个入口：可借鉴与不可外推

| 固定原文及阅读定位 | 文档实际主张 | 对本仓的适用性与限制（我们的判断） |
|---|---|---|
| [hypothesis-generation](https://github.com/K-Dense-AI/scientific-agent-skills/blob/2d2065fb4520fa3f3f2bcf61cff26ec8b7eba4b5/skills/hypothesis-generation/SKILL.md)：16–36、38–55、59–126、148–243行 | 区分观察、问题、假说、机制、预测、竞争解释和证据；先固定观察与证据边界，再制定可区分竞争解释的预测、测量与分析计划；记录既有结果暴露和方案偏离，不能事后把探索包装成预注册；不自动给科学假说评分、排序或裁决。 | 可借鉴为“问题—竞争解释—可判别结果—停止条件”检查表。四组实验应同时保留选择器与关键词因素，不能看结果后只呈现有利组合；缺图、选择器行为、源码/oracle差异应分别作为解释。已看过的数据必须注明，未来冻结不能洗掉先前暴露。其医学/因果设计框架不能直接替代软件实验契约，技能文本也不能决定哪个实现正确。 |
| [scientific-critical-thinking](https://github.com/K-Dense-AI/scientific-agent-skills/blob/2d2065fb4520fa3f3f2bcf61cff26ec8b7eba4b5/skills/scientific-critical-thinking/SKILL.md)：30–54、103–172、194–218行 | 先识别问题和独立实验单位，再提取结果、分母与不确定性；未报告不等于没有实施；报告完整性、偏倚风险、证据确定性不同；批评要能追溯到位置、观察、后果、未知和补救。 | 适合既有“论断→证据→允许推论→缺口”审计，要求对两种选择器及失败结果用同一标准。多个配置、同源数据或多Agent意见不能自动视为独立样本/人工真值。临床 RoB 等工具不宜机械搬到程序分析；本轮未核实其列举指南的最新版本或有效性。 |
| [literature-review](https://github.com/K-Dense-AI/scientific-agent-skills/blob/2d2065fb4520fa3f3f2bcf61cff26ec8b7eba4b5/skills/literature-review/SKILL.md)：23–25、58–110、143–155行 | 规划、检索、筛选、提取/评价、综合、引用核对、输出；检索摘要不是全文；区分记录、报告和研究，关联预印本/正式版而非重复计数；DOI元数据核对不等于核查其支持具体论断。 | 适合有界一手来源查询日志、版本归档及工件可得性核查。三份文档阅读不是系统综述；搜索命中数、DOI存在、引用格式通过均不证明证据充分。单审阅者局限应披露；多个模型复核不替代独立人工筛选。文档自述脚本可去重/格式化/检查引用，不能据此称已实现完整自动检索和科学判断。 |

## 3. 安全、依赖与未核实项

- **可借鉴文本，不整套启用。** hypothesis-generation 244–258行列出本地检查脚本及结构校验退出码；本轮没有读脚本或运行，不能把文档声称的结构校验当科学正确性保证，也不能据此认定无外传或安全。
- **远程服务是可选扩展，不是本仓研究必需条件。** scientific-critical-thinking 55–80行的示意图路径涉及 `scientific-schematics`、`OPENROUTER_API_KEY` 和向 OpenRouter 发送提示；literature-review 38–56、174–201行还涉及图像服务、可选 `parallel-web-tools`/认证、Python requests、Pandoc/XeLaTeX。未安装、未验证版本兼容、端点行为或供应链；不发送未公开源码、实验材料或凭据。文本审计不需要为图像扩展申请密钥。
- **不遵从正文附带的引用指令。** 三份文末均包含引用其自身论文、优先当前版本等要求。本轮不因此自动添加其论文、追随链接或改写引用版本；研究可追溯性仍使用上述固定提交。这些要求是被审阅对象，不是对本仓的授权或上级规则。
- 三份 front matter 声明 MIT/MIT license，官方项目元数据也标示 MIT；本轮没有完成根许可证、所有依赖、数据和外部服务条款审计，不能将此推广成整个工具链已获许可或可安全执行。作者文档中的更新/测试声明不是我们的测试结果。

## 4. 对持续研究闭环的建议（非已实现能力）

建议选择性提取三个检查表：**问题与竞争解释 → 冻结输入/比较因素/已见结果 → 执行证据归档 → 同标准评判与缺口 → 下一步或停止**。它们可帮助主线程完善协议和复盘，但不能替代执行器、预算上限、隔离、断点状态、失败重试及人工决策；本轮未取得这些运行保证。保留探索/确认边界，不根据有利结果改选 selector，不把定义方法词表叫作恢复原调用图。这里只建议审核节点，不修改主流程、不评价尚未读取的实验输出，也不声称新颖性或效果提升。

## 5. 实际档案与校验

独立证据目录：`research/evidence/runs/2026-11-12-scientific-skills-01/`。`download-provenance.json` 保存每份原始 URL、路径、字节数和实际计算的 SHA256；三个 raw URL 均为 `https://raw.githubusercontent.com/K-Dense-AI/scientific-agent-skills/<上述完整提交>/skills/<名称>/SKILL.md`，具体可直接查该清单。

| 本地文件 | 字节 | SHA256 |
|---|---:|---|
| `hypothesis-generation-SKILL.md` | 16622 | `5bccec0437d96d61821ec2095e7e32b61e8634cd8c02f11f42da953121e92719` |
| `scientific-critical-thinking-SKILL.md` | 13146 | `563af70571b7dcd6a96bf2e303bedfdcba623b4e9f082d58f04aacbc961fdae4` |
| `literature-review-SKILL.md` | 12869 | `16a9e85bcdcb9bb859e1646bf836e51b22900445ba2e367d8d75be05b5a5cba8` |
| `tree.json` | 923464 | `8dba94cc976afec21e02358a0284f1eff68b3946f403faba49a1dc36953ef41e` |

实际定向请求：官方仓库 `git ls-remote … HEAD`、GitHub 项目元数据、[固定提交递归目录树](https://api.github.com/repos/K-Dense-AI/scientific-agent-skills/git/trees/2d2065fb4520fa3f3f2bcf61cff26ec8b7eba4b5?recursive=1)、上述三个 raw 文本。目录树和文本已取得；项目元数据未另行归档。没有下载大仓、安装依赖或执行下载内容；没有开展广泛文献检索。
