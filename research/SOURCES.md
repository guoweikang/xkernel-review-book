# 来源与检索台账

首次检索日期：2026-10-27；归档日期：2026-10-27。
条目编号用于后续引用。阅读状态按本轮实际证据记录；“章节核对”不表示全文逐页审阅。
原始副本及获取失败项见 [evidence/manifest.json](evidence/manifest.json)。

## 论文和评估研究

### 2026-11-11 InMap原文与固定工件

后续：[评分静态审计](notes/2026-11-11-inmap-scoring-audit.md)、[Lucene实际组件实验](notes/2026-11-11-lucene-scoring-runtime.md)、[历史版本及文件级许可核查](notes/2026-11-11-inmap-history-preflight.md)。Lucene8.6.2实际依赖来自Maven Central，记录下载URL、仓库SHA1与本地SHA256；运行查询解释纠正了“默认similarity决定全部子句分数”的潜在误解。未把这一组件实验登记为InMap复现。

INMAP-SAC21：Sinkala、Herold，InMap: Automated Interactive Code-to-Architecture Mapping，SAC 2021，DOI 10.1145/3412841.3442124。[作者稿](https://www.diva-portal.org/smash/get/diva2:1552606/FULLTEXT01.pdf)及[工件](https://git.cs.kau.se/zipasink/InMap)已取得部分本地归档，URL、字节数和hash见[工件记录](notes/2026-11-11-reflexion-artifact-readiness.md)。已定向阅读§3–5并静态核对反馈入口；固定工件版本晚于论文，未运行，不称数值复现。见[执行前检查](notes/2026-11-11-inmap-execution-preflight.md)和[评价边界](notes/2026-11-11-inmap-label-boundary.md)。RM-FSE95后续已补读§3、§6并完成有限定义重实现，见[精读](notes/2026-11-11-reflexion-confirmation-reading.md)，不再仅停留在初始摘要阅读状态。

### 2026-11-11 职责归属与架构一致性入口

RM-FSE95：Murphy、Notkin、Sullivan，Software Reflexion Models: Bridging the Gap Between Source and High-Level Models，FSE 1995。[作者全文](https://www.cs.ubc.ca/~murphy/papers/rm/reflexion_model_fse95.pdf)已下载（275008字节），SHA-256登记于证据manifest。定向阅读摘要、引言和§2 NetBSD案例；形式化定义及其余实验仍待精读，未运行RMTool。经典方法作为新分支起点，不能替代最近邻调研。ArchUnit仅核查官方指南介绍与规则入口，未安装运行。下一步见[执行安排](notes/2026-11-11-next-research-execution.md)。

### 2026-11-11 BigClone基准接入

固定BigCloneEval `6d393ec8adb1d71493d09881ba520659b6c2c68e` 的说明／Makefile／matcher及BigCloneBench `37f6c7141dac914d7eb13c09a967c6ce1a821f91`说明，Git blob校验归档。实际探测两个官方分享入口只取得HTML前缀，未下载数据集或运行基准；见[接入预检](notes/2026-11-11-discovery-benchmark-preflight.md)。

### 2026-11-09 文档检索实现基线

核查scikit-learn 1.7官方TF-IDF文档与1.7.2源码，采用固定版本公开实现；[方法依据](notes/2026-11-09-tfidf-baseline-reference.md)与[实际运行](notes/2026-11-09-doc-tfidf-first-run.md)分列。此次是简单文档检索基线，不是注释LDA论文复现；未报告语义准确率。

### 2026-11-09 相似性与文档语义定向检索

后续已对注释辅助检测v1的§II-B、III–V和表I/II做[正文精读](notes/2026-11-09-comment-clone-method-reading.md)，PDF和提取文本归档；其余条目仍保持下述摘要级状态。另核查LDA经典JMLR 2003书目／摘要，未审计推导或实现。

新增检索CodeSearchNet、CodeBERT、GraphCodeBERT、注释辅助克隆检测、RepliComment及2026鲁棒性预印本；本轮主要为摘要／书目核查，不能记为全文精读或复现。版本、来源、捕获路径与方法取舍见[研究路线](notes/2026-11-09-similarity-research-route.md)。注释辅助检测及跨领域序列比对已有先例，不以“加入rustdoc”或“借用DNA相似算法”本身主张创新。

### 2026-11-05 跨项目取样来源

固定ArceOS `8d2e6f97efc4a67359b99db5e519a55b7067b524` 与StarryOS `2e075accf4fb0aefdd1d252ebd9ccf29727d9923`。
官方仓库、谱系来源及读取边界见[范围记录](notes/2026-11-05-cross-project-scope.md)与[谱系记录](notes/2026-11-05-cross-project-lineage.md)。
四份capture manifest在evidence/runs中逐项登记URL与哈希；本轮不将源码捕获算作算法验证。

### 2026-11-05 原任务与评价器对齐

P01补核§3.5、§4表1/3/4/5及相关筛选、抽样段落，见[原任务审计](notes/2026-11-05-p01-original-task-audit.md)。
T12固定版README核对输入位置格式、参考筛选、CoverageMatcher；P01固定树补读方法前端及配置，三份源码归档。
见[评价接入与限制](notes/2026-11-05-scc-evaluation-alignment.md)。文件级冒烟已运行，方法前端、评价器和论文结果均未运行复现。

### 2026-11-05 候选发现基线补读

P01 归档实际为 arXiv v1，已直接核对 §2、§3.1–3.4、§4.3–4.4 及 §5 的指定机制与评估段落，
见 [token 基线边界](notes/2026-11-05-candidate-token-baseline.md)。不把 token 阈值准确率当成
功能重复或安全重构准确率；未运行工具、未核查当前 Rust 支持。

### 2026-11-05 失败反馈与错误拒绝

| ID | 来源 | 阅读范围 | 边界 |
| --- | --- | --- | --- |
| P30 | [Detecting Overly Strong Preconditions in Refactoring Engines，TSE 44(5), 2018](https://leopoldomt.github.io/assets/pdf/2018-tse.pdf) | 摘要、§3.2、§4.1、oracle 有效性威胁 | 实验中禁用条件以测试重构器，不是生产免检；测试 oracle 有盲区，未复现 |
| P31 | [Kayak: Safe Semantic Refactoring to Java Streams，v1](https://arxiv.org/html/1712.07388v1) | 问题定义与 §5 合成、验证、异常/终止边界 | 特定 Java Stream 模型的 CEGIS，非通用 Rust 重构证明 |

检索与取舍见 [定向查新](notes/2026-11-05-feedback-and-rejection-prior-work.md)。三份新归档含 P19 完整 v2 HTML，
不覆盖原摘要副本；未执行作者工件。牛津 precondition inference 页面 403，不纳入已读正文来源。
P19 阅读状态已从摘要推进到 §3.2–3.3、附录 A.2–A.3、Algorithm 1 与表9/13 的定向核查，
见 [ReGAL 反馈记录](notes/2026-11-05-regal-feedback.md)；未审计实现或完整实验。

### 2026-11-05 P16 前置条件精读

直接读取已归档作者 PDF 的 §3 概述、§3.3.4、§3.4.1–3.4.3、§3.5，逐项核对八条前置条件、
求值顺序例子及作者对替代编码成本的讨论。未形式化审查公式或运行工具。
见 [P16 精读](notes/2026-11-05-p16-preconditions-reading.md)；旧版本工具边界不外推为最新能力。
另直接复核 §5.2、§5.4.6 的样本分母、序列化修正和并发未验证边界，见
[验证审计](notes/2026-11-05-p16-validation-audit.md)；未运行工具或审查原始结果工件。

### 2026-11-04 A4 定向复核

本轮未新增来源编号。P04 已读取归档作者 PDF 的 III.E/F、Table II 及有效性威胁中历史标签段落，
明确平衡采样、部分人工特征及历史重构偏差；未复现。P21 v3 §5 与 P15 v1 §4.6 在线复核，
未检查最新工具实现。具体范围和研究取舍见 [A4 收敛记录](notes/2026-11-04-a4-research-convergence.md)。

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
| P01 | [SourcererCC: Scaling Code Clone Detection to Big Code](https://arxiv.org/abs/1512.06448v1) | 摘要；2026-11-05 补读 §2、§3.1–3.4 与指定评估/威胁段落 | token 克隆和索引化召回基线；非功能等价，未复现 |
| P02 | [RepoCoder](https://arxiv.org/abs/2303.12570)；[EMNLP 2023 正文](https://aclanthology.org/2023.emnlp-main.151.pdf) | 摘要与方法概述 | 仓库级检索增强已有工作；任务是补全 |
| P03 | [GraphCoder](https://arxiv.org/abs/2406.07003) | v2 摘要 | 代码上下文图和粗到细检索 |
| P04 | [Recommending Clones for Refactoring Using Design, Context, and History](https://cormack.uwaterloo.ca/~migod/papers/2014/icsme14-wei.pdf) | 摘要、引言、问题定义；2026-11-04 补核 III.E/F、Table II 及历史标签有效性威胁 | 设计/上下文/历史推荐已有；下采样、人工特征与标签偏差，未复现 |
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

2026-11-05 新增 T11：[Jenkins 构建 3885](https://jenkins.openkylin.top/job/x-kernel-ci-test/3885/)
及其 `artifact/artifacts/facts/` 下双平台 status/manifest、aarch64 klazy 样本。五份原始文件登记哈希；
校验范围见 [执行准备](notes/2026-11-05-execution-readiness.md)，未下载全量、未验证语义正确性。
三项目官方仓库与固定 HEAD 的定向身份调查见 [Rust OS 记录](notes/2026-11-05-rust-os-identities.md)，
包含滚动 README 与固定 SHA 读取的区别；未保存整仓副本或完整许可证审计。

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

- [基线复现矩阵](notes/2026-11-05-baseline-reproduction-matrix.md)、
  [SourcererCC/Wrangler准备核查](notes/2026-11-05-scc-wrangler-reproduction-readiness.md)、
  [Librarian准备核查](notes/2026-11-05-librarian-reproduction-readiness.md)：官方仓库固定SHA及任务/环境差异，尚未运行。
- T12：[BigCloneEval官方评价器](https://github.com/jeffsvajlenko/BigCloneEval)，
  本轮固定`6d393ec8adb1d71493d09881ba520659b6c2c68e`，仅ReadMe归档，未下载基准数据库。

- [模块路径官方规则](notes/2026-11-05-module-path-rules.md)与
  [v2模块映射实现](notes/2026-11-05-module-mapping-workflow.md)：官方Reference/Cargo Book、
  固定树57声明、18项路径案例和3项门禁反例；文件候选不作为编译语义真值。

- [四 crate 单位清单](notes/2026-11-05-multi-crate-unit-inventory.md)：固定树88文件、
  syn v2输出、15个适配样例及解析器失败负向检查；记录在 evidence/inventory，不是检测效果证据。

- [结构化解析验证](notes/2026-11-05-structured-parser-check.md)及
  [syn 接口边界](notes/2026-11-05-syn-interface-boundaries.md)：
  固定依赖源码、14个构造输入、5个固定源码文件；工具源码/锁文件和机器可读结果保留。

- [Rust 单位定位探针](notes/2026-11-05-rust-unit-location-probe.md)：
  本机 rust-analyzer 1.95.0 的版本/帮助/实际解析输出，以及固定 klazy 源码和 T11 制品。
  结果含七个构造输入、五个源文件及关联失败记录，不是新论文或检测效果评估。

- CI 3885 固定树 `7e3ac94431a0dbb376d2fc8d85098deeff1bba09`：
  [源码关联及字段核查](notes/2026-11-05-facts-source-alignment.md)、
  [配置生成与可恢复边界](notes/2026-11-05-facts-config-provenance.md)。
  对应材料盘点和 klazy 样本核查结果保存在 `research/evidence/inventory/`；
  这是固定源码和既有制品的检查，不是新论文证据或重复检测实验。

- X-Kernel 快照：`43b5f35d4a7bc6a0fa766d4fd3654844bb66e028`。
- [现有复用审查](../../review/guidelines.md)、[CG-041](../../../code-guidelines/CG-041-reuse-safe-boundary-abstractions.md)、
  [驱动边界](../../driver-subsystem-boundaries.md)。这些相对链接指向当前工作树，历史内容应以快照读取。
- 不把此前已交付的 CG-047 当作本研究产物；它提供 Kconfig/feature 背景，但不是复用检测实现。
