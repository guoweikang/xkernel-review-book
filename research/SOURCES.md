# 来源与检索台账

首次检索日期：2026-10-27；归档日期：2026-10-27。
条目编号用于后续引用。阅读状态按本轮实际证据记录；“章节核对”不表示全文逐页审阅。
原始副本及获取失败项见 [evidence/manifest.json](evidence/manifest.json)。

## 论文和评估研究

### 2026-10-29 历史意见与规则自动化

| ID | 来源 | 阅读范围 | 主要边界 |
| --- | --- | --- | --- |
| P29 | [Auto-SCAT，EMSE 27:28 (2022)，online 2021-12-11](https://doi.org/10.1007/s10664-021-10076-4)；[作者 PDF](https://mdipenta.github.io/files/Auto_SCAT_EMSE.pdf)；[oracle 记录](https://zenodo.org/records/4399225) | 作者稿 §3–7 定向方法、评价与局限；出版方书目；工件元数据 | 选择已有 Checkstyle 检查，不合成新 checker；分类/配置精度不是免审覆盖；未复现 |
| T10 | [Bugbot Learned Rules 公告](https://cursor.com/blog/bugbot-learning)；[changelog](https://cursor.com/changelog/04-08-26)；[官方文档](https://cursor.com/docs/bugbot) | 公告正文、机制与指标；文档规则及加载限制小节 | 产品资料而非论文；反馈学习审查指令；无工具覆盖免审验证 |

分析与实际查询：[Auto-SCAT](notes/2026-10-29-auto-scat-analysis.md)、[Bugbot](notes/2026-10-29-bugbot-learned-rules-analysis.md)。
已保存作者 PDF、三份 Cursor HTML 和 Zenodo 元数据；出版方 HTML 本地下载失败，网页书目仍通过检索工具核实。
未下载 Oracle.txt，未运行产品、Checkstyle、Rust lint 或任何实验。

### 既有来源

| ID | 来源 | 本轮阅读范围 | 支撑问题 |
| --- | --- | --- | --- |
| P01 | [SourcererCC: Scaling Code Clone Detection to Big Code](https://arxiv.org/abs/1512.06448) | 作者摘要及官方仓库说明 | token 克隆和索引化召回基线 |
| P02 | [RepoCoder](https://arxiv.org/abs/2303.12570)；[EMNLP 2023 正文](https://aclanthology.org/2023.emnlp-main.151.pdf) | 摘要与方法概述 | 仓库级检索增强已有工作；任务是补全 |
| P03 | [GraphCoder](https://arxiv.org/abs/2406.07003) | v2 摘要 | 代码上下文图和粗到细检索 |
| P04 | [Recommending Clones for Refactoring Using Design, Context, and History](https://cormack.uwaterloo.ca/~migod/papers/2014/icsme14-wei.pdf) | 作者 PDF 的摘要、引言与问题定义 | 设计/上下文/历史参与可重构性判断已有先例 |
| P05 | [LAURA](https://yuxiazhang-bit.github.io/papers/ASE25_LAURA.pdf) | 作者 PDF 的方法、评估/消融表及重复代码案例 | 检索增强 review、评论价值评价 |
| P06 | [How the Misuse of a Dataset Harmed Semantic Clone Detection](https://arxiv.org/html/2505.04311v1) | 作者正文及摘要核对；未复验原样本 | BigCloneBench 语义标签有效性的警示；统计范围见研究笔记 |
| P07 | [Semantic Code Clone Detection: Are We There Yet?](https://arxiv.org/abs/2606.25272) | 预印本摘要 | 分布迁移与捷径学习风险；不是本项目实测 |
| P08 | [Tricorder: Building a Program Analysis Ecosystem](https://research.google.com/pubs/archive/43322.pdf) | 作者 PDF 检索片段，特别是 effective false positives | 开发者可行动性与工作流成本 |
| P09 | [SWE-Refactor](https://arxiv.org/html/2602.03712v1) | v1 摘要、任务与验证指标 §3.1–3.2、附录 A；未复现 | 仓库级复合重构评估；给定目标与操作，不等同自主发现抽象机会；附录发布链接待补 |
| P10 | [RefactorBench](https://arxiv.org/abs/2503.07832) | 作者摘要，ICLR 2025 camera-ready 标记；尚未核对全文协议 | 多文件、组合任务与状态跟踪；不能拿其摘要成功率作为本项目基线 |
| P11 | [Wrangler / Incremental Code Clone Detection and Elimination](https://www.cs.kent.ac.uk/pubs/2011/3087/content.pdf) | 引言、§4–7 指定段落及表 1；专题 W1 | 公共函数、实例替换、克隆类与增量检测 |
| P12 | [The pragmatics of clone detection and elimination](https://arxiv.org/pdf/1703.10860) | 方法、§4、§5 选定案例及 §6；专题 W2 | 工业抽象选择、过度参数化与职责边界 |
| P13 | [Stitch / Top-Down Synthesis for Library Learning](https://arxiv.org/html/2211.16605v2) | §2、§3.1、§6.1–6.2 及高阶扩展指定段落；专题 W3 | 语料级抽象学习；压缩目标与维护价值不同 |
| P14 | [REM / Adventure of a Lifetime](https://verse-lab.org/papers/rem-oopsla23.pdf) | 方法概述、实现、§4 与 §6；专题 W4 | Rust 抽取的所有权、控制流与生命周期修复 |
| P15 | [REM2.0 / Refactoring and Equivalence in Rust](https://arxiv.org/html/2601.19207v1) | 架构、§4.6、§5.4–5.5 指定段落和表格；专题 W5 | Rust 抽取与受限子集验证；预印本，未审查证明 |
| P16 | [Assessing the Refactorability of Software Clones，TSE 2015](https://users.encs.concordia.ca/~nikolaos/publications/TSE_2015.pdf)；[作者工件页](https://users.encs.concordia.ca/~nikolaos/TSE_2015/) | §3.3.4、§3.4 相关段落、§3.5、§5.2、§5.4.6；工件页 | 依赖/前置条件重构；序列化契约失败及作者修正 |
| P17 | [babble，POPL 2023](https://cseweb.ucsd.edu/~npolikarpova/publications/popl23.pdf) | 概述、§2、§5 近似搜索、§6 设计和定性评价指定段落 | 等价理论、反统一、库选择代价；未审查证明/运行 |
| P18 | [E-Stitch，EGRAPHS 2026](https://pldi26.sigplan.org/details/egraphs-2026-papers/7/E-Stitch-Top-Down-Library-Learning-for-E-Graphs) | 官方工作坊摘要；附件未取回 | e-graph 上的自顶向下库学习；正文待查 |
| P19 | [ReGAL，ICML 2024，v2](https://arxiv.org/abs/2401.16467v2) | 作者摘要与检索返回的正文概述片段 | 执行反馈下的抽象改进；详细方法待精读 |
| P20 | [LILO，ICLR 2024，v4](https://arxiv.org/abs/2310.19791v4) | 作者摘要与检索返回的引言片段 | 合成、压缩、自动命名/文档；详细评测待精读 |
| P21 | [Refactoring Codebases through Library Design，v3](https://arxiv.org/abs/2506.11058v3) | 主线共同阅读、附录 A/E 正文；未完整审计或复现 | Librarian/MiniCode、多文件共享库、MDL/偏好；发表核查见共同笔记 |

P21 共同精读更新（2026-10-28）：已完成问题定义、方法、指标、人类评价与主要结果
的主线阅读及附录 A；非全部附录审计，未复现。版本仍为 v3。发表状态核查、
待核对数字及讨论见 [共同精读 01](notes/2026-10-27-librarian-reading-01.md)。

### 2026-10-28 历史偏好定向查新

| ID | 来源 | 实际阅读范围 | 与研究的关系 |
| --- | --- | --- | --- |
| P22 | [CodeTaste，2026 v1](https://arxiv.org/html/2603.04177v1) | §2–3、§4.1、§4.4、附录 A.4 列表；未复现 | 历史多文件人工重构与规则化对齐评价，含 Rust 仓库 |
| P23 | [Themis，2026 v1](https://arxiv.org/html/2605.00754v1)；[作者数据卡](https://huggingface.co/datasets/project-themis/Themis-CodePreference) | §3、§4.1、B.3 指定段落及数据卡 | 已合入未回退提交、分维偏好、混合意图过滤与隔离协议 |
| P24 | [Learning Code Preference via Synthetic Evolution，2024 v2](https://arxiv.org/abs/2410.03837v2)；[作者页](https://llm-code-preference.github.io/) | 论文摘要、作者页方法和评价；未完整读 PDF | CodeFavor/CodePrefBench，commit 合成偏好与独立多维验证 |
| P25 | [CROP 作者工件页](https://crop-repo.github.io/) | About、结构与数据说明；未下载大型数据包 | 评审理由、中间版本、放弃变更与完整代码快照 |
| P26 | [When Do You Repeat Yourself?，TechDebt 2026](https://doi.org/10.1145/3794915.3795783) | 旁支核对出版方检索正文 §3–5/7；直接访问受阻，非完整 PDF 精读 | Linux 去重的接受与拒绝，研究者介入，不是自然历史偏好数据集 |
| P27 | [OpenStack 重构评审研究，2022](https://arxiv.org/abs/2203.14404) | 旁支核对方法、§4.2/表 4、工件说明；主代理核对摘要 | 评审决策理由，Abandoned 不等于设计低质量 |
| P28 | [Quick remedy commits，EMSE](https://doi.org/10.1007/s10664-021-10051-z) | 旁支核对摘要、引言及印刷页 19–21；未审计工件 | 回退造成的挖掘噪声，不能将回退一律作为技术负例 |

对照、搜索词及下一篇精读建议见
[历史偏好定向查新](notes/2026-10-28-historical-preference-prior-work.md)。
P26–P28 的访问边界、方法和查询词见
[重构决策旁支](notes/2026-10-28-refactoring-decisions-sidecar.md)。

P16–P21 的技术谱系、失败记录、实际查询与阅读限制见
[基础调研第二批](notes/2026-10-27-foundations-02.md)。本批没有运行基线或收集真实案例。

P11–P15 的详细阅读范围、评估边界、查询词及未核对部分统一保存在
[公共抽象专题](notes/2026-10-27-abstraction-prior-work.md)，其中 W1–W5 顺次对应 P11–P15。
阶段 A 第一批进一步回查上述本地原文，阅读范围、页码和章节增量见
[最近邻技术矩阵](notes/2026-10-27-nearest-method-matrix.md) §1；未新增外部来源或运行作者工件。

2026-10-27 科研规划补充：P07 阅读扩展至 v1 正文中的 §VII 有效性威胁，
作者明确变换无形式化语义保证、实验限于 BigCloneBench；保留此前摘要副本，另存正文。
P09 的 v1 附录 A 仍写待发布，不能把摘要中的发布声明当作已验证可用的数据集。

解读统一见 [初步研究](notes/2026-10-27-initial-research.md)，避免把摘要里的工具结果
当成 X-Kernel 上的效果。P06 对抽样 WT3/T4 的统计不能外推整个 BigCloneBench。

## 专利公开文本

权项、公开/授权对应和具体重合见 [专利证据表](prior-art/2026-10-27-patents.md)。
下列阅读版本不能替代其他版本的权利要求或当前法律状态。

| ID | 阅读版本 | 本轮阅读范围 |
| --- | --- | --- |
| A01 | [CN121255180A](https://patents.google.com/patent/CN121255180A/zh) | 公开本权1–6及出版信息；复用元数据与多因素排序 |
| A02 | [CN119848881A](https://patents.google.com/patent/CN119848881A/zh) | 公开本权1、3–6及出版信息；增量代码检索增强评审 |
| A03 | [US20110246968A1](https://patents.google.com/patent/US20110246968A1/en) | 公开本权1–6、10–11及出版信息；克隆、改进潜力及排序 |
| A04 | [US20070050343A1](https://patents.google.com/patent/US20070050343A1/en) | 公开本权1、9–10、12–13及出版信息；语义描述符与索引 |
| A05 | [US9519464B2](https://patents.google.com/patent/US9519464B2/en) | 授权本权1、3、6、8–9及出版信息；代码推荐知识库 |
| A06 | [US20250362905A1](https://patents.google.com/patent/US20250362905A1/en) | 2025-11-27 申请公开本，权1–11及指定说明书段落；语言模型生成公共块与差异块 |

本轮扩展 A03/A05 至全部权1–20，新增 A06；独立/从属限定、说明书与权项的区分见
[公共抽象专利对照](prior-art/2026-10-27-abstraction-claims.md)。该笔记 S1/S2/S3 分别对应
A05/A03/A06；未完成同族/版本演变或法律状态核查。

同申请对应版本线索：A02 的 [CN119848881B](https://patents.google.com/patent/CN119848881B/zh)，
A03 的 [US9110769B2](https://patents.google.com/patent/US9110769B2/en)，
A04 的 [US8566789B2](https://patents.google.com/patent/US8566789B2/en)，
A05 的 [US20150378692A1](https://patents.google.com/patent/US20150378692A1/en)。
未完成这些版本的逐项权项演变比较，不重复算作五组之外的新发明。

## 工具、协议与产业资料

| ID | 来源 | 阅读范围与用途 |
| --- | --- | --- |
| T01 | [SourcererCC 仓库](https://github.com/Mondego/SourcererCC) | README；机械克隆基线 |
| T02 | [SCIP 协议](https://github.com/scip-code/scip) | README；符号导航事实底座 |
| T03 | [Sourcegraph precise navigation](https://sourcegraph.com/docs/code-navigation/precise-code-navigation) | 官方支持表，Rust/rust-analyzer |
| T04 | [jscpd semantic clones](https://jscpd.dev/guides/semantic-clones) | 官方说明，实验性能力与相关性误报 |
| T05 | [jscpd boundaries](https://jscpd.dev/guides/boundaries) | 官方规则与示例；边界检查近似工作 |
| T06 | [jscpd embedding benchmark](https://jscpd.dev/project/benchmarks/embedding-models) | 官方概要及阈值说明；未复现实验 |
| T07 | [SonarQube 2025.1 指标](https://docs.sonarsource.com/sonarqube-server/2025.1/user-guide/code-metrics/metrics-definition) | 官方整体/新增代码指标；不当作语义判断 |
| T08 | [Software Engineering at Google: Static Analysis](https://abseil.io/resources/swe-book/html/ch20.html) | 作者关于增量分析与可行动性的章节 |
| T09 | [xerj 固定快照](https://github.com/xerj-org/xerj/tree/2b67a883ab43cd2146199968f537912c0bee3b9d) | 源码及官方文档，未安装运行；具体文件和行号见两份 xerj 笔记 |

T09 的完整临时浅克隆位于 `/tmp/xerj-research-20261027`，不是持久证据的唯一来源。
evidence 中保存关键固定版本源码/文档；完整仓库可由固定 SHA 再定位。

## 保留线索：尚未充分阅读，不用于确定性结论

| ID | 来源 | 后续用途 |
| --- | --- | --- |
| L01 | [CodeXGLUE](https://github.com/microsoft/CodeXGLUE) | 看过检索摘要中的克隆分类/检索任务说明；后续核对数据协议 |
| L02 | [GPTCloneBench](https://arxiv.org/abs/2308.13963) | 检索摘要线索；候选语义/跨语言基准，需核对生成数据偏差 |
| L03 | [SemanticCloneBench](https://clones.usask.ca/pubfiles/articles/Omari_SemanticClonesBenchIWSC2020.pdf) | 检索线索；候选基准 |
| L04 | [On the Use of Deep Learning Models for Semantic Clone Detection](https://arxiv.org/abs/2412.14739) | 检索摘要线索；模型稳健性与变换实验 |
| L05 | [RLCoder](https://arxiv.org/abs/2407.19487) | 检索摘要线索；检索器学习，与 review 任务有距离 |
| L06 | [Repoformer](https://arxiv.org/abs/2403.10059) | 检索摘要线索；选择性检索 |
| L07 | [US20260093607A1](https://patents.google.com/patent/US20260093607A1/en) | 检索摘要线索；测试工件语义复用，未做权项分析 |
| L08 | [SourcererCC-I](https://arxiv.org/abs/1603.01661) | 检索摘要线索；开发中实时克隆发现 |

## 检索过程留痕

以下为本会话实际使用的主要查询，保存方法和范围，不声称是全部搜索返回页面的原始转储。
未采信的论坛和二手聚合页不作为技术结论证据；其引出的有效线索已尽量回溯作者或官方来源。

| 批次 | 主要查询或入口 | 结果去向 |
| --- | --- | --- |
| 方法与数据集 | `semantic code clone detection BigCloneBench CodeXGLUE clone detection benchmark` | P06/P07、L01–L04 |
| 产业 review | `Google Tricorder code review duplicate code detection clone`；`site.research.google Tricorder building program analysis ecosystem code review false positives` | P08、T08 |
| 克隆基线 | `site.github.com SourcererCC token clone detector`；`site.arxiv.org SourcererCC scaling code clone detection big code` | P01、T01、L08 |
| 仓库检索 | `site.arxiv.org RepoCoder repository level code completion iterative retrieval generation` | P02/P03、L05/L06 |
| 重构可行性 | `site.arxiv.org code clone detection refactoring opportunities not all clones should be refactored` | P04 |
| Rust 索引 | `site.sourcegraph.com SCIP rust analyzer semantic indexing rust` | T02/T03 |
| 重复率与增量 | `site.docs.sonarsource.com duplication pull request new code duplication metrics` | T07 |
| 语义和 review | `site.arxiv.org "code duplication" "review" "LLM"`；`site.jscpd.dev "boundaries" "semantic"` | P05、T04–T06 |
| 专利初检 | `patent semantic code duplication detection software reuse recommendation`；`source code semantic indexing reuse recommendation`；`code clone detection incremental changes review`；`code review incremental claims` | A01–A05、L07；权项核对见专利笔记 |
| 用户提供项目 | `https://github.com/xerj-org/xerj`，随后浅克隆、固定 HEAD 和源码搜索 | T09、tools/xerj 两份笔记 |
| 科研规划补充 | `site.arxiv.org code clone refactoring benchmark evaluation semantic clones dataset 2025 2026`；`site.conf.researchr.org refactoring large language models behavior preservation benchmark 2025` | P09/P10；重新核对 P06/P07；其余搜索命中未作为结论证据 |

## 本地项目证据

- X-Kernel 快照：`43b5f35d4a7bc6a0fa766d4fd3654844bb66e028`。
- [现有复用审查](../../review/guidelines.md)、[CG-041](../../../code-guidelines/CG-041-reuse-safe-boundary-abstractions.md)、
  [驱动边界](../../driver-subsystem-boundaries.md)。这些相对链接指向当前工作树，历史内容应以快照读取。
- 不把此前已交付的 CG-047 当作本研究产物；它提供 Kconfig/feature 背景，但不是复用检测实现。
