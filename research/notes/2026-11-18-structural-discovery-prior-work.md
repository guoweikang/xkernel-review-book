# 结构/API 使用发现的最近邻：Aroma、MAPO、PAM

日期：2026-11-18。范围：三种原方法的原论文与作者工件审计；不是实现、复现或效果实验。不新增第四篇，不改主线程已冻结的调用集合 TFIDF/cosine + 词法相邻特征消融。检索、原件和身份保存在本地`research/evidence/runs/2026-11-18-structural-discovery-sources-01/`下的`lookup.json`、`sources.json`、`checksums.sha256`；这些原始档案未由book发布为下载链接。

## 结论先行

- **Aroma 最接近局部结构候选检索**：局部变量归一化、树上下文与变量使用上下文，让局部片段不必与整个函数有高词元重合；随后剪枝、重排、聚类、求交。但不是语义等价检索，对 API 名称仍有依赖。
- **MAPO 最接近“把相同 API 用法组织成可浏览模式”**：API 调用序列、调用者名称与类名相似度、簇内频繁子序列；它甚至希望同一模式的多个证据容易找到，不是简单丢掉同族结果。
- **PAM 最值得借鉴的是冗余评价**：统计模型解释调用序列，倾向保留有联合解释力的模式，并直接测量较大模式包含较小模式的冗余。它不是 API 集合 cosine，更不是已有 Rust 工具。
- 三者都不能把“检索出共同局部机制”直接升级为“应抽取/移动/共享”或“重构有收益”。其原实验主要针对代码补全、用法学习、模式出现/覆盖；没有给我们的职责边界真值。

下文的本地路径均相对于 `research/evidence/runs/2026-11-18-structural-discovery-sources-01/`；PDF 原件优先，文本提取版用于定位，不以模型摘要代替原文。

## 1. Aroma（OOPSLA 2019）

来源：[作者论文](https://people.eecs.berkeley.edu/~ksen/papers/aroma.pdf)，本地 `aroma.pdf` / `aroma-paper.txt`，§3.1–3.3、§4–5、§7；[官方工件](https://github.com/facebookresearch/aroma-paper-artifacts/tree/e8d8beeb99255d8929874c156fd65aac74d21508)，固定 commit `e8d8beeb99255d8929874c156fd65aac74d21508`。

**表示和检索。** §3 使用简化解析树；局部变量替换为统一标记，但全局变量和方法名保留。特征包含 token、parent、sibling、相邻同一局部变量的使用上下文。轻量检索后对方法剪枝、重排，再构造建议。这里的“变量使用相邻”不是任意词法相邻调用，也不是已验证的数据流。官方 `aroma-ConvertJava.java.txt` 使用 JavaLexer/JavaParser；`aroma-similar.py.txt` 的 `counter_vectorize` 使用 binary CountVectorizer。**不能称主线程 TFIDF/cosine 为 Aroma 复现**：缺少树特征、query-conditioned pruning、重排及受约束求交；即使共同使用稀疏表示，也不是方法身份相同。

**真实聚类/去重。** §3.3.3（印刷页152:14–15）允许簇重叠。簇须同时满足：共同片段有足够 query 扩展、剪枝后的共同特征仍接近首个片段；实验阈值分别1.5、0.9。从单元组逐步扩展，按首个候选索引升序、簇长度降序排列；与先前元组 Jaccard 相似度超过0.5的元组被删，再对簇求交保留 query 内容。它不是语义 family 标注或每 family 固定配额。
- 论文该段有一句“not too similar”与紧接的“very similar”解释张力；保留原文，不把它擅自修成另一算法。
- 官方 `get_completions3`（`aroma-similar.py.txt` 约689–750行）检查阈值、按首索引/长度排序，再比较候选索引 Counter 的重叠，受 `top_n` 限制；代码比较的是此前 `acc` 中元组，不仅已接受输出。公开参考代码和论文叙述不可假定逐步完全等价。
- §4.1另在建库时按项目、文件、方法的 hash 去掉重复；这是不同层次的重复控制，不能解释为语义家族去重。

**评价到底测什么。** §5用从已入库方法取出的连续/非连续5行查询检索原方法；Recall@1 为99.1%/98.3%。这不是 held-out family，也不是低词元相似的独立机制标签。§4的64个 StackOverflow 查询评审建议类别，§7报告开发者使用意见；有参与者认为普通搜索已足够。没有单独量化“簇抑制后发现了多少独立职责家族”的实验。

**工件/数据与 Rust。** README 公布5339个 Java Android 仓库的固定版本列表、64个查询；不是完整可直接再分发的语料，建议片段因法律原因未直接共享。`aroma-test.sh.txt` 给出 Maven Java转JSON及 Python检索入口。论文提到其他语言上的内部实现，不等于公开 Rust 前端。当前核查范围未见 Rust parser/绑定适配；本批未构建运行，历史依赖可用性未知。

## 2. MAPO（ECOOP 2009，不混用2006版本）

来源：[作者论文](https://taoxiease.github.io/publications/ecoop09-mapo.pdf)，本地 `mapo.pdf` / `mapo-paper.txt`；另一作者站 `mapo-author.pdf` 字节hash相同。重点§4.1–4.3、§5.1–5.3、§6。

**表示。** §4.1基于 Eclipse JDT，从第三方 API 调用提取序列，含构造、cast等；分支产生路径，循环近似为零次/一次；不判定条件间依赖，会含不可行路径，还会内联非第三方方法。这远多于词法相邻 token。
**聚类。** §4.2将调用方法名、类名按大小写拆词并用编辑距离比较；第三项是被调用 API 集合 Jaccard，三项平均后做 Matlab 层次聚类。簇内 SPAM 频繁子序列，以模式作为关联源码的索引。这并不消除 API 身份依赖：不同 API 实现同一机制时，集合项未必相似。

**真实防重复策略和目标。**
- §4.1针对 method overweight/common-path overweight：先选最长路径，再贪心选覆盖最多尚未覆盖 API 调用的路径，直到覆盖全部调用；减少单个多分支方法的序列数量偏置。不是最终候选 family 配额。
- §5.2明确讨论“尽快找到不同用法”和“尽快找到同用法第二个实例”的冲突，采用模式索引组织而不是简单剔除同族。
- §5.3表3有关闭 selection/inlining/clustering 的消融；测第一/第二个匹配所需检查片段数和频繁序列总数。它支持评价浏览负担，不是我们语义家族预算实验的已验证规则。
- §5.1用20个 GEF项目（约141K LOC），support=0.7来自初始经验；§6六名参与者、六个补全任务、固定时间下的 API相关错误评价，仍不是重构收益或职责真值。

**工件与 Rust。** 原文指定 Java/JDT、Matlab、SPAM；没有已核验 Rust 前端。本轮没有确认到 ECOOP2009原作者可运行分发或完整评测包。猜测的作者项目路径返回404，只说明该路径失败，不证明工具从未公开。PAM仓库虽有 MAPO代码，README及论文明确这是后来的从零重实现，不能标作原版MAPO。原论文项目清单可作追溯入口，但版本/历史链接可恢复性尚未知。

## 3. PAM（FSE 2016）

来源：[作者论文](https://people.maths.ox.ac.uk/fowkes/papers/fse2016.pdf)，本地 `pam.pdf` / `pam-paper.txt`，§3–5，尤其§4.6、§5 RQ1–3与图2–4；[官方实现](https://github.com/mast-group/api-mining/tree/f8829c3b699356bfdfc3648e11ffecadd3300ca6)，commit `f8829c3b699356bfdfc3648e11ffecadd3300ca6`。

**机制与冗余。** 用子序列交织生成客户端调用序列，EM/structural EM学习模式和概率；按概率排序，最后去掉单元素模式。模式覆盖解释倾向避免无关联的拼接，不是对候选做一个固定余弦阈值聚类；也不保证一个语义family只出一个模式。论文强调泛化/具体模式可以并存，冗余为零不是必然最佳。

**可复用评价定义（不是职责标签）。**
- sequence precision：输出模式中，在金标准序列中作为子序列出现的比例。
- sequence recall：金标准序列中，包含至少一个输出模式的比例。
- redundancy：对每个模式，数其他更大模式中有多少包含它，再取平均；按输出排名前k绘图。
- RQ2图3报告PAM该均值约0.5且低于比较方法；这测子序列包含冗余，不等于跨模块语义family覆盖，不能把0.5当我们的验收阈值。
- RQ1按 Client **文件**随机约50/50切分，报告69% test-set precision；不是按项目/机制family留出。RQ3对开发者示例的覆盖分析也不能让“示例没有”成为错误标签。

**工件/前端/数据。** `pam-README.txt` 提供 Maven/JAR 与 `apimining.pam.main.PAM` 入口，输入 ARFF（fqCaller/fqCalls，空格分隔调用序列），输出带概率模式。公开 API序列和源文件包路径在 `pam-tree-selected.json`：train/netty.arff、client_files.tar.xz、example_files.tar.xz、namespaces.tar.xz、test/train文件清单；本批只查元数据，未下载大包、未运行测试。README称包含17个库的数据；公开存在不等于已在本机跑通。
- `pam-extractor.java.txt` 的 APICallExtractor 是Java提取器，硬编码历史本地目录，通过 APICallVisitor 提取；不是开箱即用Rust CLI。论文§3只近似解析全限定名，并明确省去super调用、cast等，不能继承MAPO前端的全部能力。
- README称提取为best-effort，需额外namespace资料应付通配导入。若将Rust序列送入，绑定、trait方法、宏/cfg、别名以及隐式Drop等仍需明确处理策略；这些是迁移缺口，不是本批新前端开发建议。
- 归档了作者MAPO重实现的 `APICallClustererMAPO.java`，只用于辨别身份；它不是ECOOP2009原工件。测试树有 SequenceMiningTest，但本批未运行，也未把历史CI徽章当当前通过证据。

## 与既有 SourcererCC、冻结消融的差距

SourcererCC以token重合的克隆候选为目标；Aroma论文§5.2.1在局部查询找原方法任务上按默认0.7阈值比较SCC，报告其连续/非连续查询recall为12.2%/7.7%；作者明确无法给SCC结果排序，因此这不是Recall@1。这是特定粒度/任务比较，不支持普遍宣称SCC弱，也不代表本repo Rust token化和预算条件已相同。

Aroma的§5.2.2–5.2.3还直接比较了结构特征TFIDF/cosine与关键词TFIDF。它们是论文的比较条件，不是Aroma主流水线；主线程调用集合/词法相邻表示也不等于这两个条件，不能借同一个相似度名字声称已有复现。

调用集合TFIDF/cosine可以问“忽略大量非调用词元后是否多发现候选”；词法相邻特征可问“增加局部顺序线索是否改变候选”。它没有Aroma的树/变量上下文、MAPO的路径和簇内挖掘、PAM的序列生成模型。三篇既不为该表示背书，也不否定它作为独立、明确命名的低成本消融。

“同一家族占满预算”最接近的原证据是Aroma元组重叠抑制和PAM包含冗余曲线，但都没有现成的本repo职责family标签。**不修改事前冻结的排序或配额。** 后续若另行授权，可把重复占位率、独立来源数、子序列包含冗余与人工界定family覆盖分开报告；事后自制family规则不得变真值，不能见结果后按有利规则去重。原方法的阈值也不应直接移植。

## 交接与未核实项

本批实际执行：本地lookup、原文阅读、官方小源码读取、PDF下载/解析与hash；无依赖安装、构建、模型或重型运行。成功下载3篇PDF（另有MAPO同hash镜像），失败/截断尝试留在 `downloads.json`。文本归档经过UTF-8工具传输及末尾换行规范化；其hash是归档文本身份，不冒充远端原字节；PDF是原始下载字节。

主线程可分别检查Aroma的Java→JSON→Python入口与PAM的现成ARFF入口，但当前Rust候选冻结消融不需先移植二者。未核实：现代环境可构建性、原MAPO可运行包、Rust正确绑定前端、公开语料的全部历史版本可恢复性、以及任何重构收益。Skill要求的独立后台代理在当前可用工具中无spawn入口，本批为直接原文审计，不冒称已独立复核。按用户要求不改catalog/PROGRESS，不宣称完成全书集成验证。
