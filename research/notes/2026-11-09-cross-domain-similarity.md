# 跨领域序列相似性：Rust 重复候选的用途与边界

日期：2026-11-09。限定一手论文与官方教学材料；不研究代码+文档融合，不运行检测或实验。以下“适配建议”均未验证，也不构成新颖性结论。

## 一手材料与实际阅读深度

| 方法 | 直接阅读与文献事实 | Rust 适配建议及限制（本轮推论） |
| --- | --- | --- |
| Smith–Waterman | Smith、Waterman，*Identification of Common Molecular Subsequences*，JMB 147 (1981), 195–197。实际读 PDF 的 Algorithm、式(1)及 p.196 回溯说明：给定元素分数与 gap 代价，矩阵含零重启，从最大值回溯至零，得到允许插入/删除的最佳局部匹配。[论文原文镜像](https://www.gersteinlab.org/courses/452/10-spring/pdf/sw.pdf) | 可对源码 token/操作序列提供局部对应位置，较整函数全局分数更适合“共享片段+不同外壳”。但最优仅相对于所选表示和分数，不是功能最优；不能随意把锁、错误分支或 Drop 当可忽略 gap。未确定 Rust 的替换分数/gap 参数，也不把一般 gap 递推笼统称作所有实现都具有同一复杂度。 |
| BLAST | 原始 Altschul 等 1990 JMB 215:403–410 PDF 已取得，但为扫描件，文本提取无可读正文，本轮不声称精读算法。实际读 NCBI 官方 *BLAST Basics* 的 What does BLAST do / How and why：高分局部对齐及随机对齐分布模型；同源不保证同功能。[官方教程](https://www.nlm.nih.gov/ncbi/workshops/2023-08_BLAST_evol/blast_basics.html) | 可考虑“先检索短局部线索、再扩展/精排”的候选流水线；此处只是待验证设计，不把本轮未核对的1990参数写成实现依据。不能直接把 Rust token 映射为核酸字符后沿用生物替换矩阵或 E-value；Rust 背景分布、模板频率与目标标签都不同。 |
| MinHash/随机 shingle 摘要 | 实际读 Broder、Glassman、Manasse、Zweig，*Syntactic Clustering of the Web*，SRC-TN-1997-015（1997-07-25）中 Defining similarity、Estimating resemblance and containment，PDF pp.3–6。规范化 token 的连续 shingles 形成去重集合，以随机置换抽样估计相似/包含；固定大小与模数采样的支持范围不同，短文包含于长文的估计会受样本稀少影响。[作者技术报告原文](https://www.microsoft.com/en-us/research/wp-content/uploads/1997/01/src-tn-1997-015.pdf) | 可作低成本候选预筛，而不是序列对齐器。shingle 内保留局部顺序，集合层丢失重复次数与全局排列。Jaccard 低不排除短 helper 被长函数包含，应另区分方向性 containment；不能把普通固定大小 resemblance sketch 自动说成已解决包含检索。未验证摘要大小、误差或检索召回率。 |

MinHash 一栏采用可直接取得的作者技术报告，而非冒称已读 Broder 单作者 *On the resemblance and containment of documents* 全文；本轮也未证明某具体哈希族满足理想随机置换假设。

## 必须保留的直接代码先例：CCDive

已打开[出版方 SciOpen 页面](https://www.sciopen.com/article/10.26599/TST.2024.9010075)，直接核对标题、作者、正式 Abstract 与出版信息（不是页面 AMiner AI 摘要）：Yasir Glani、Luo Ping、Syed Asad Shah、Lin Ke，*CCDive: A Deep Dive into Code Clone Detection Using Local Sequence Alignment*，**Tsinghua Science and Technology 30(4), 1435–1456，2025**，DOI `10.26599/TST.2024.9010075`；页面标示2025-03-03发布。摘要明确将逐层抽象与 Smith–Waterman 局部序列对齐结合，用于代码克隆及变换位置识别。因此“把 DNA/生物序列对齐迁移到代码”不能被表述为我们的新颖点。**本轮仅出版方摘要级核对**，未确认其语言范围、数据划分、分母、参数、工件及 Rust 可复现性；不转述其优于其他方法的摘要主张为已独立验证效果。

## 可进入下一步的有限假设

三者宜分工：shingle 摘要用于候选缩减，局部对齐用于展示共同段和差异段；是否组合、是否优于现有 token 基线仍待检验，而非预定结论。若开展小型评估，应固定源码单位/配置，分开记录“候选召回”“对齐位置可解释性”和“具备共享机制且约束兼容”的人工判断；尤其保留已有委托、不同错误/溢出策略、锁和 Arc/Drop 时序、宏/cfg 差异作为反例。序列高分既不证明替换安全，也不证明维护收益；低分同样不能排除不同写法实现同一功能。本轮没有准确率、性能或Rust支持验证。

## 归档、查询与未核实项

原始 PDF 保存于 `research/evidence/runs/2026-11-09-cross-domain-similarity-01/`；仅归档下载字节，不把下载成功等同全文阅读。SHA256 与实际下载 URL：

- `smith-waterman-1981.pdf`：`30d13d4c1ae7aeffff82f1cf4104e5ac76a582f3548f0506f7481e02337126be`；https://www.gersteinlab.org/courses/452/10-spring/pdf/sw.pdf
- `blast-1990.pdf`：`325dffe5618650582c29484ef843c09f28c2545d0d1df85d6a8d4b9c7ffc93bf`；https://www.cs.cornell.edu/courses/cs628/2004fa/secure/papers/Altschul_et_al_basic_local_alignment_search_tool_BLAST_JMB90.pdf
- `broder-1997-src.pdf`：`e90b472ced977bb629709196bc417687c44396fa2d8e887cff413d4db605a914`；https://www.microsoft.com/en-us/research/wp-content/uploads/1997/01/src-tn-1997-015.pdf

实际搜索词：`Smith Waterman 1981 Identification common molecular subsequences pdf`；`Altschul 1990 Basic local alignment search tool NCBI BLAST`；`Broder 1997 resemblance containment documents minwise pdf`；`Broder resemblance containment documents 1997 pdf cs stanford`。CCDive 直接打开主研究检索后转交的 URL，并非用户提供论文；NCBI 教程直接打开搜索命中的官方 URL。BLAST MPI 镜像网页读取超时，改取 Cornell 原文镜像；SW 网页解析失败但 curl 下载及本地 pdftotext 成功。未归档 CCDive HTML/全文与教程页面，未改原始资料总manifest，未追查当前工具版本。
