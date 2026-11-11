# 研究中汇报：逐页内容与证据

## 01 Rust系统代码：从相似发现到合理重构

研究中汇报 · 以xkernel为主要试验场 · 2026.11.11

### 为什么研究

发现已有实现与功能重叠
减少重复维护与理解成本
守住正确性、性能与代码清晰度

### 本次汇报

研究问题与项目价值
代表论文、数据与评价方法
实际复现进展与下一步尝试

已有材料用于明确研究方向，不提前宣告新方法成功。



- 本地证据：`research/RESEARCH-PLAN.md`
- 本地证据：`research/notes/2026-11-11-evaluation-layers.md`
- 本地证据：`research/notes/2026-11-11-tool-model-boundaries.md`

## 02 为什么值得做：优化机会不只在PR里

对象包括已合入代码的全仓盘点，以及新增代码的增量检查。

### 我们希望发现

已有能力被再次实现
局部机制可以共享
现有公共模块可被复用

### 必须避免误改

不同配置的合法版本
用途相近但契约不同
抽象层增加调用和理解成本

### 预期项目价值

缩小人工查找范围
提供可定位的整改线索
用真实补丁衡量最终收益

价值是待验证的工程收益，不是候选数量越多越好。



- 本地证据：`research/RESEARCH-PLAN.md`
- 本地证据：`research/notes/2026-11-11-evaluation-layers.md`
- 本地证据：`research/notes/2026-11-11-tool-model-boundaries.md`
- 本地证据：`research/evidence/runs/2026-11-09-source-doc-inventory-02/report.json`
- 本地证据：`research/evidence/runs/2026-11-09-doc-tfidf-01/report.json`
- 本地证据：`research/evidence/runs/2026-11-09-doc-tfidf-review-01/report.json`
- 本地证据：`research/notes/2026-11-09-doc-tfidf-review.md`
- 本地证据：`research/notes/2026-11-05-metadata-paired-validation.md`
- 本地证据：`research/notes/2026-11-05-metadata-case-disposition.md`

## 03 把问题拆开，才能设计可验证的研究

相似、功能关系、共享前提和优化收益，是不同问题。

### 发现

哪些函数／模块值得比较？
代码、文档与结构信号
在同预算下能找到什么？

### 确认

是独立实现还是已有委托？
是否存在可共享的局部机制？
类型／配置／副作用允许吗？

### 优化

提取函数、泛型还是保持独立？
行为与性能是否保持？
整体结构是否更清晰？

先生成怀疑清单，再确认与优化；不让一个相似分数包办所有判断。



- 本地证据：`research/RESEARCH-PLAN.md`
- 本地证据：`research/notes/2026-11-11-evaluation-layers.md`
- 本地证据：`research/notes/2026-11-11-tool-model-boundaries.md`

## 04 相关研究地图：发现与重构不能混为一个榜单

按论文解决的任务理解它们，而不是把不同分数横向排序。

### 候选发现

SourcererCC：token克隆
注释研究：主题组检索
评价：克隆／检索命中

### 结构抽象

Wrangler：表达式序列
绑定与反统一约束
输出：公共函数候选

### 共享库设计

Librarian：库＋调用方改写
测试约束与整体质量排序
评价：方案而非克隆数量

我们的研究连接这些环节，但需要分别建立评价依据。



- [Sajnani等，SourcererCC: Scaling Code Clone Detection to Big Code，ICSE 2016（固定v1）](https://arxiv.org/pdf/1512.06448v1)
- 本地证据：`research/notes/2026-11-05-candidate-token-baseline.md`
- 本地证据：`research/evidence/originals/P01-sourcerercc.pdf`
- [Kuttal与Ghosh，Source Code Comments: Overlooked in the Realm of Code Clone Detection，2020](https://arxiv.org/html/2006.14505v1)
- 本地证据：`research/notes/2026-11-09-comment-clone-method-reading.md`
- 本地证据：`research/notes/2026-11-09-comment-clone-artifact-readiness.md`
- [Li与Thompson，Incremental Clone Detection and Elimination for Erlang Programs，2011](https://www.cs.kent.ac.uk/pubs/2011/3087/content.pdf)
- 本地证据：`research/notes/2026-11-05-structural-semantic-candidates.md`
- 本地证据：`research/notes/2026-11-05-scc-wrangler-reproduction-readiness.md`
- [Kovačič等，Refactoring Codebases through Library Design，2025（v3）](https://arxiv.org/html/2506.11058v3)
- 本地证据：`research/notes/2026-10-27-librarian-reading-01.md`
- 本地证据：`research/notes/2026-11-05-librarian-reproduction-readiness.md`
- 本地证据：`research/notes/2026-11-11-librarian-presentation-audit.md`
- 本地证据：`research/evidence/originals/P21-librarian-v3-full.html`

## 05 SourcererCC：为什么适合作为发现基线

原作者方法 · 面向精确与近似代码克隆，重点解决规模化检索。

### 相似度定义

把代码块变成token多重集
保留token频次
共享量 ≥ θ × 较大块长度
不以语句顺序表示执行语义

### 如何减少比较

统一token排序
部分倒排索引召回候选
位置／剩余量上界过滤
过滤针对既定token判据

适合提供廉价、可解释的候选；并不判定行为等价或重构安全。

公式严格判定使用ceil(θ × max(|A|,|B|))；不是Jaccard。算法position是排序后token位置，不是控制流。固定论文v1 §3。

- [Sajnani等，SourcererCC: Scaling Code Clone Detection to Big Code，ICSE 2016（固定v1）](https://arxiv.org/pdf/1512.06448v1)
- 本地证据：`research/notes/2026-11-05-candidate-token-baseline.md`
- 本地证据：`research/evidence/originals/P01-sourcerercc.pdf`

## 06 SourcererCC：作者用了什么数据，效果如何？

原论文结果 · 固定v1 §4，不能当作我们在Rust上的复现成绩。

### 数据与规模

真实克隆：BigCloneBench
构造克隆：Mutation/Injection
扩展性：IJaDataset 2.0
约250MLOC（2.5亿行）

### 分层召回率

BigCloneBench 全部克隆
T1 / T2：100% / 98%
VST3 / ST3：93% / 61%
MT3 / WT3-T4：5% / 0%

### 人工核查

约200万输出中抽390对
355真、35假：precision 91%
三位专家分担核验
不是每对三人独立双重确认

启发：必须看分层结果；词法克隆精度不是功能重复或重构收益精度。

原论文表5 All Clones；表3构造变异基准Java/C/C#的T1–T3均报告100%，不能外推真实弱语法相似。召回类别的语法相似度定义见§4.3；0%是表中报告的取整值。人工precision见§4.4。与本地80%门槛、Rust tokenizer和数据不对齐，因此不做数值复现声明。

- [Sajnani等，SourcererCC: Scaling Code Clone Detection to Big Code，ICSE 2016（固定v1）](https://arxiv.org/pdf/1512.06448v1)
- 本地证据：`research/notes/2026-11-05-candidate-token-baseline.md`
- 本地证据：`research/evidence/originals/P01-sourcerercc.pdf`

## 07 我们复现到哪里：原工具与边界验证

已运行 · 固定SCC源码88314f51…；原算法Java文件未修改。

### 原生冒烟

六个Java文件
先冻结期望，再运行
精确／近似：共3对命中
无关输入与短文件不命中

### 边界验证

七文件、21个无序组合
80%命中，79%不命中
相同64-token文件被排除
相同65-token文件被检出

### 得到的判断

当前参数控制符合预期
相似关系不具传递性
记录被门槛排除的单位
尚未复现论文基准分数

这是原工具运行与判据验证，不是功能重复检测准确率验证。

边界套件预期与实际都是3对；10个组合满足最小长度条件。独立计数器只验证token重叠判据，不是语义oracle。未实测论文吞吐量或峰值内存。

- 本地证据：`research/notes/2026-11-05-scc-native-smoke.md`
- 本地证据：`research/notes/2026-11-05-scc-boundaries-and-goal-gate.md`
- 本地证据：`research/evidence/runs/2026-11-05-scc-native-02/report.json`
- 本地证据：`research/evidence/runs/2026-11-05-scc-boundaries-01/report.json`

## 08 我们做了Rust适配，但没有改变原算法

已运行 · xkernel固定7e3ac944…，kvfs / kspin / klazy / macros。

### 输入范围

88文件、2,180源码单位
有函数体的语法单位
未展开宏、未求值cfg
不是全内核所有配置

### 工具输出

最少65 tokens、阈值80%
812个合格单位 → 156对
329,266次穷举判据比较
输出与token oracle一致

### 解释边界

确认适配管线有可核查输出
不能据此计算语义precision
未运行原论文公开基准
不是原论文实验同条件复现

先验证方法运行正确，再设计公平的语义与工程效果评价。



- 本地证据：`research/evidence/runs/2026-11-05-rust-baseline-corpus-01/report.json`
- 本地证据：`research/evidence/runs/2026-11-05-rust-scc-01/report.json`

## 09 注释研究：自然语言能补充代码信号吗？

原作者方法与数据 · Kuttal / Ghosh，2020；不等同于rustdoc专用方法。

### 处理路线

文件注释 → 清洗 → LDA
按主题组织疑似克隆组
与Java PDG/GRAPLE对照
输出主要是文件级对象

### 数据与标签

JHotDraw：315文件、约27K行
5文件无注释，LDA用310个
学生借助工具建立真值
作者报告该部分投入45小时

### 作者结果：表I

LDA Method 1
Recall 94.86% / Precision 84.21%
LDA Method 2
Recall 28.61% / Precision 88.57%

文档信号值得测试，但先确认这些分数究竟在评价什么。



- [Kuttal与Ghosh，Source Code Comments: Overlooked in the Realm of Code Clone Detection，2020](https://arxiv.org/html/2006.14505v1)
- 本地证据：`research/notes/2026-11-09-comment-clone-method-reading.md`
- 本地证据：`research/notes/2026-11-09-comment-clone-artifact-readiness.md`

## 10 同一论文的两种指标，回答的不是同一个问题

原论文分析 · Method 1看参与克隆的文件；Method 2保留组的匹配。

### Method 1的边界

真实组：{A,B}、{C,D}
预测组：{A,C}、{B,D}
参与文件相同，文件级可满分
但两个预测配对都错误

### 我们的评价选择

发现清单需要对象对标签
同时记录无文档对象覆盖
同单位、同预算下比较
不以文件覆盖代替配对正确性

自构反例用于解释指标，不是作者数据的实际错误；两行主题数也不同。

表I Method 1/2分别用100/105个主题，不能把数值差全部归因于指标。原始组和标签未取得，Method 2匹配细节待澄清。我们的pairwise评价选择是研究设计，尚未完成独立标注实验。

- [Kuttal与Ghosh，Source Code Comments: Overlooked in the Realm of Code Clone Detection，2020](https://arxiv.org/html/2006.14505v1)
- 本地证据：`research/notes/2026-11-09-comment-clone-method-reading.md`
- 本地证据：`research/notes/2026-11-09-comment-clone-artifact-readiness.md`

## 11 文档路线：我们做的是简单基线，不是LDA复现

已运行TF-IDF / cosine；原作者LDA实现与标签包尚未取得。

### 可复用的实现

scikit-learn 1.7.2
固定TF-IDF与cosine
先冻结top20排序规则
两次运行队列一致

### 实际文档覆盖

2,180单位中780有非空文档
1,400缺失或为空
只取直接字面量文档
不继承trait或父模块说明

### 得到的认识

能产生可定位的候选
覆盖只有约35.8%
高分不等于功能等价
文档缺失与角色混淆须评估

保留文档辅助假设；不把替代基线包装成作者LDA成果复现。



- 本地证据：`research/evidence/runs/2026-11-09-source-doc-inventory-02/report.json`
- 本地证据：`research/evidence/runs/2026-11-09-doc-tfidf-01/report.json`
- 本地证据：`research/evidence/runs/2026-11-09-doc-tfidf-review-01/report.json`
- 本地证据：`research/notes/2026-11-09-doc-tfidf-review.md`
- [scikit-learn 1.7 TF-IDF定义与本地参数核查](https://scikit-learn.org/1.7/modules/feature_extraction.html#tfidf-term-weighting)
- 本地证据：`research/notes/2026-11-09-tfidf-baseline-reference.md`
- [Kuttal与Ghosh，Source Code Comments: Overlooked in the Realm of Code Clone Detection，2020](https://arxiv.org/html/2006.14505v1)
- 本地证据：`research/notes/2026-11-09-comment-clone-method-reading.md`
- 本地证据：`research/notes/2026-11-09-comment-clone-artifact-readiness.md`

## 12 Wrangler：从结构相似进一步走向公共函数

机制阅读与资源核查 · Erlang方法；本地尚未执行。

### 作者机制

带变量绑定信息的AST
表达式泛化与序列索引
再做anti-unification
形成公共函数与替换调用

### 对我们的启发

不只比较整个函数
研究局部机制能否共享
类型／绑定关系可能很关键
结构候选仍需人工取舍

### Rust迁移问题

所有权、生命周期与unsafe
宏／cfg、锁与副作用
泛型或trait引入的复杂度
不能把AST指纹冒称复现

此项用于界定抽象方向；没有本地运行数据，不编造复现结论。



- [Li与Thompson，Incremental Clone Detection and Elimination for Erlang Programs，2011](https://www.cs.kent.ac.uk/pubs/2011/3087/content.pdf)
- 本地证据：`research/notes/2026-11-05-structural-semantic-candidates.md`
- 本地证据：`research/notes/2026-11-05-scc-wrangler-reproduction-readiness.md`

## 13 Librarian：研究输出不只是“哪些代码相似”

原论文v3 · 输入相关文件，输出共享库以及迁移后的原程序。

### 搜索与生成

文件摘要 → 嵌入聚类
按组生成K个重构方案
方案包含库与调用方修改
可进一步考虑已有库

### 验证与选择

保留原先通过的测试
对完整方案计算损失
比较库＋迁移程序总成本
采样后重排，不只看一份生成

借鉴的是“生成—验证—评价”分离，而不是让大模型直接宣布重构更好。

§3/5；MiniCode是基准，Librarian是方法。测试集合保留约束不同于仅比较测试通过率大小。本地未运行Librarian，不能称Rust文档检索为Librarian复现。

- [Kovačič等，Refactoring Codebases through Library Design，2025（v3）](https://arxiv.org/html/2506.11058v3)
- 本地证据：`research/notes/2026-10-27-librarian-reading-01.md`
- 本地证据：`research/notes/2026-11-05-librarian-reproduction-readiness.md`
- 本地证据：`research/notes/2026-11-11-librarian-presentation-audit.md`
- 本地证据：`research/evidence/originals/P21-librarian-v3-full.html`

## 14 Librarian的数据：有竞赛，也有选定工程文件

作者MiniCode · 固定v3表1；文件数、任务数与测试数必须区分。

### CodeContests

300文件 / 10任务
每文件平均87行
每文件平均10个测试
不是300个独立重构任务

### 选定真实工程文件

Transformers：10文件 / 1任务
平均538行、181测试/文件
Diffusers：11文件 / 2任务
平均685行、75测试/文件

### 其他任务域

Logo：300文件 / 1任务
Date：246文件 / 1任务
分别平均10行 / 14行
并涉及留出程序合成评价

数据不是Rust内核；表1写10个CodeContests任务，附录另有6组表述待对齐。

固定v3 §4表1，均为作者汇总；不得将平均测试数相乘当精确总数。Transformers/Diffusers不是全仓。Logo/Date用于库辅助留出合成，与克隆检测不是同一任务。CodeContests选定样本和模型的全部重现条件尚待对齐。

- [Kovačič等，Refactoring Codebases through Library Design，2025（v3）](https://arxiv.org/html/2506.11058v3)
- 本地证据：`research/notes/2026-10-27-librarian-reading-01.md`
- 本地证据：`research/notes/2026-11-05-librarian-reproduction-readiness.md`
- 本地证据：`research/notes/2026-11-11-librarian-presentation-audit.md`
- 本地证据：`research/evidence/originals/P21-librarian-v3-full.html`

## 15 Librarian的作者结果：整体压缩不等于运行加速

原论文v3表2与§7 · 以下均是作者报告，不是我们的实验成绩。

### CodeContests 表2

K=8、S=3，模型o4-mini
MDL Ratio：0.53 ± 0.03
Token Ratio：0.66 ± 0.04
Pass Rate：90.67% ± 1.88

### Transformers 选定10文件

系统MDL：原来的67.2%
作者报告全部集成测试通过
同指标人工重构：66.5%
论文作者人工方案：62%

MDL衡量模型描述长度，不代表性能；Token Ratio与正文降幅存在待核对差异。

CodeContests表2的误差项照原表，不自行定义为标准差或标准误。90.67%不是90.67%的重构完全正确，本轮未核对逐测试分母和跨任务加权。Token Ratio 0.66与正文减少44%不一致。Transformers K=15、S=5、Claude Code；人工方案比较仅限同一MDL指标，不能称维护能力达到人类水平。

- [Kovačič等，Refactoring Codebases through Library Design，2025（v3）](https://arxiv.org/html/2506.11058v3)
- 本地证据：`research/notes/2026-10-27-librarian-reading-01.md`
- 本地证据：`research/notes/2026-11-05-librarian-reproduction-readiness.md`
- 本地证据：`research/notes/2026-11-11-librarian-presentation-audit.md`
- 本地证据：`research/evidence/originals/P21-librarian-v3-full.html`

## 16 Librarian怎样证明评价指标有意义？

原论文§6与附录E · 不仅提出指标，还将指标选择与人类偏好比较。

### 可计算的代理

Tokens：库＋改写文件总长度
MDL：库及条件程序的负对数概率
另比较CC、MI与复用代理
MDL依赖所用概率模型

### 作者人类实验

14位参与者、129次判断
MDL相对MI有显著偏好优势
相对Tokens未得同样显著结论
不能外推全部Rust维护场景

我们的借鉴：指标也需要验证；性能、清晰度与维护价值不能被压缩率替代。

MDL=-log p(L)-Σlog p(P'|L)。129是判断次数，不是129位参与者或独立任务。附录允许近似相同，使用共识阈值筛选；原始分歧、选择偏差和模型配置需要复现时核对。本地仅文献与资源审计，未复现人类实验。

- [Kovačič等，Refactoring Codebases through Library Design，2025（v3）](https://arxiv.org/html/2506.11058v3)
- 本地证据：`research/notes/2026-10-27-librarian-reading-01.md`
- 本地证据：`research/notes/2026-11-05-librarian-reproduction-readiness.md`
- 本地证据：`research/notes/2026-11-11-librarian-presentation-audit.md`
- 本地证据：`research/evidence/originals/P21-librarian-v3-full.html`

## 17 复现进展：明确哪些已有结果，哪些还没有

原工具运行、Rust适配、替代基线和论文数值复现，分开登记。

### 已执行

SCC原工具冒烟与边界检查
SCC的Rust输入适配
原生文档TF-IDF两轮运行
metadata候选成对测试

### 阅读／工件核查

注释LDA：未运行原方法
Wrangler：未运行
Librarian：未调用原管线
BigClone：入口预检，未评测

### 还不能声称

未复现原论文完整指标
尚无独立语义真值
尚无同预算优势结论
不能给出方法准确率排行榜

原工具跑通是真实进展，但“找到代码／有输出”不等于论文结果已复现。

Librarian固定仓库f5167b903d00ace774de419a617138b8db69c4bd，脚本数据路径、模型、集合数和评分端点需对齐；不是实测运行失败。BigClone官方分享入口返回HTML，既不算数据下载成功，也不证明数据不可得。

- 本地证据：`research/notes/2026-11-05-scc-native-smoke.md`
- 本地证据：`research/notes/2026-11-05-scc-boundaries-and-goal-gate.md`
- 本地证据：`research/evidence/runs/2026-11-05-scc-native-02/report.json`
- 本地证据：`research/evidence/runs/2026-11-05-scc-boundaries-01/report.json`
- 本地证据：`research/evidence/runs/2026-11-05-rust-baseline-corpus-01/report.json`
- 本地证据：`research/evidence/runs/2026-11-05-rust-scc-01/report.json`
- 本地证据：`research/evidence/runs/2026-11-09-source-doc-inventory-02/report.json`
- 本地证据：`research/evidence/runs/2026-11-09-doc-tfidf-01/report.json`
- 本地证据：`research/evidence/runs/2026-11-09-doc-tfidf-review-01/report.json`
- 本地证据：`research/notes/2026-11-09-doc-tfidf-review.md`
- [Kovačič等，Refactoring Codebases through Library Design，2025（v3）](https://arxiv.org/html/2506.11058v3)
- 本地证据：`research/notes/2026-10-27-librarian-reading-01.md`
- 本地证据：`research/notes/2026-11-05-librarian-reproduction-readiness.md`
- 本地证据：`research/notes/2026-11-11-librarian-presentation-audit.md`
- 本地证据：`research/evidence/originals/P21-librarian-v3-full.html`
- [BigCloneBench/BigCloneEval固定版本入口预检](https://github.com/clonebench/BigCloneEval/tree/6d393ec8adb1d71493d09881ba520659b6c2c68e)
- 本地证据：`research/notes/2026-11-11-discovery-benchmark-preflight.md`

## 18 先导实验暴露了什么值得研究的问题？

本地开发案例 · 不是新方法效果结论，也不是独立测试集。

### 输入门槛混杂

文档top20中19对不在SCC输出
但两端都小于65 tokens
增量不能直接归因于语义能力
下一轮先统一可评价范围

### 词袋丢失角色关系

权限与类型两个接口
同一组词，替换对象不同
文档cosine可为1
高分仍不能证明可合并

### 已有复用与合理差异

20对解释：配置2、契约7
已有委托6、小重叠未知5
未确认收益不等于全部误报
需要独立标签与不确定类

这些观察给出实验假设；不能把开发样本上的解释当作精度验证。



- 本地证据：`research/evidence/runs/2026-11-09-source-doc-inventory-02/report.json`
- 本地证据：`research/evidence/runs/2026-11-09-doc-tfidf-01/report.json`
- 本地证据：`research/evidence/runs/2026-11-09-doc-tfidf-review-01/report.json`
- 本地证据：`research/notes/2026-11-09-doc-tfidf-review.md`
- 本地证据：`research/evidence/runs/2026-11-05-rust-baseline-corpus-01/report.json`
- 本地证据：`research/evidence/runs/2026-11-05-rust-scc-01/report.json`
- 本地证据：`research/notes/2026-11-11-manuscript-evidence-audit.md`

## 19 一次真实整改试验：测试通过，仍需权衡收益

本地metadata测试夹具抽取 · 对候选做验证，不是强行采纳每个建议。

### 做了什么

两个13字段构造点抽取共享
修改4文件并新增模块
增加25行、删除30行
整体净减5行

### 验证得到什么

原版与候选各通过相同94项测试
同配置、同初始磁盘模板
非unittest构建通过
候选未直接落入用户内核

### 仍然不知道什么

缺少维护成本的独立评价
没有性能提升测量
不证明所有配置行为等价
当前暂缓采纳

经验：更少的重复构造不一定带来更好的整体设计。

这是历史实验，本轮没有重跑内核。94/94指两版本各自同一94项测试，不是188个独立样本。原版使用构建缓存、候选重建，不能比较构建耗时；非unittest只构建、未运行生产内核。

- 本地证据：`research/notes/2026-11-05-metadata-paired-validation.md`
- 本地证据：`research/notes/2026-11-05-metadata-case-disposition.md`

## 20 准备尝试的方向：每一项都需要可否证的实验

研究假设 · 由论文与先导观察共同引出；不预设效果和创新性。

### 代码＋文档

与单token、单文档比较
同单位、同长度范围、同预算
去文档／打乱文档消融
看额外确认数与核查成本

### 角色与结构约束

类型、输入输出与副作用
调用委托、配置及局部机制
测试角色交换与合理独立例
比较是否减少错误合并建议

### 重构质量评价

包含“不改”的方案基线
编译、测试、性能分别测量
独立成对评价代码清晰度
检查抽象成本与实际复用

先验证一个聚焦机制；没有增益或代价过高，也应成为保留结果。



- [Kuttal与Ghosh，Source Code Comments: Overlooked in the Realm of Code Clone Detection，2020](https://arxiv.org/html/2006.14505v1)
- 本地证据：`research/notes/2026-11-09-comment-clone-method-reading.md`
- 本地证据：`research/notes/2026-11-09-comment-clone-artifact-readiness.md`
- [Li与Thompson，Incremental Clone Detection and Elimination for Erlang Programs，2011](https://www.cs.kent.ac.uk/pubs/2011/3087/content.pdf)
- 本地证据：`research/notes/2026-11-05-structural-semantic-candidates.md`
- 本地证据：`research/notes/2026-11-05-scc-wrangler-reproduction-readiness.md`
- [Kovačič等，Refactoring Codebases through Library Design，2025（v3）](https://arxiv.org/html/2506.11058v3)
- 本地证据：`research/notes/2026-10-27-librarian-reading-01.md`
- 本地证据：`research/notes/2026-11-05-librarian-reproduction-readiness.md`
- 本地证据：`research/notes/2026-11-11-librarian-presentation-audit.md`
- 本地证据：`research/evidence/originals/P21-librarian-v3-full.html`
- 本地证据：`research/RESEARCH-PLAN.md`
- 本地证据：`research/notes/2026-11-11-evaluation-layers.md`
- 本地证据：`research/notes/2026-11-11-tool-model-boundaries.md`
- 本地证据：`research/evidence/runs/2026-11-09-source-doc-inventory-02/report.json`
- 本地证据：`research/evidence/runs/2026-11-09-doc-tfidf-01/report.json`
- 本地证据：`research/evidence/runs/2026-11-09-doc-tfidf-review-01/report.json`
- 本地证据：`research/notes/2026-11-09-doc-tfidf-review.md`

## 21 仍沿用六阶段：前期材料服务后续可检验实验

阶段顺序不变；已经开展的小试验用于可行性排查，不替代正式评价。

### 基础调研 → 真实试点

技术谱系与最近邻正文分析
专利技术特征及失败模式
首批约12–20案例设计
含可抽象、独立、重叠与未知

### 基线复现 → 核心实验

先对齐原任务和指标
排除配置／使用问题
一个机制、同预算对照
消融与独立测试

### 场景验证 → 研究产出

全仓扫描、真实重构补丁
跨配置与增量旁路运行
论文与技术交底证据
完整记录失败与负结果

当前案例是开发材料；最终论文贡献与专利候选由实验和查新决定。

首批12–20是既定试点设计规模，不是声明本轮新采样。现有38个不同配对来自两条开发审阅队列，不能当作38个独立案例。正式阶段准入仍需对应计划中的证据要求。

- 本地证据：`research/RESEARCH-PLAN.md`
- 本地证据：`research/notes/2026-11-11-evaluation-layers.md`
- 本地证据：`research/notes/2026-11-11-tool-model-boundaries.md`

## 22 怎样评价，才不只是在xkernel上调出好结果？

后续评价安排 · 尚未完成公开基准或跨项目实验，只描述用途。

### 公开基准＋Rust受控集

公开克隆基准：校验原任务
受控变换：角色／文档／委托
已知分母时报告precision/recall
未知分母不报全仓召回率

### 真实库＋独立工程

std/core历史：材料，不是真值
xkernel既有样本归开发集
ArceOS／Starry／星绽等候选
固定版本，控制共同来源泄漏

下一步优先：对齐一条原任务基线，同时冻结同范围对照与标注协议。

没有保证能取得每个项目的独立真值。项目选择须核查许可、谱系、可构建配置与审阅资源；历史PR合入不等于最优方案。性能实验采用相同配置和负载；维护性需要独立审阅及分歧记录。

- 本地证据：`research/RESEARCH-PLAN.md`
- 本地证据：`research/notes/2026-11-11-evaluation-layers.md`
- 本地证据：`research/notes/2026-11-11-tool-model-boundaries.md`
- [BigCloneBench/BigCloneEval固定版本入口预检](https://github.com/clonebench/BigCloneEval/tree/6d393ec8adb1d71493d09881ba520659b6c2c68e)
- 本地证据：`research/notes/2026-11-11-discovery-benchmark-preflight.md`

## 23 主要参考与材料入口

每页备注提供原始链接、具体章节与本地报告；作者结果与本地结果分别标注。

### 候选与结构方法

SourcererCC · ICSE 2016
arXiv:1512.06448v1
注释/LDA · arXiv:2006.14505v1
Wrangler · Li & Thompson, 2011

### 共享库与本地证据

Librarian · arXiv:2506.11058v3
MiniCode：作者的评价基准
本地reports / 协议 / 日志
SLIDE-NOTES.md逐页索引

目标是找到值得做、能够验证的改进，不是提前拼出一个成功故事。



- [Sajnani等，SourcererCC: Scaling Code Clone Detection to Big Code，ICSE 2016（固定v1）](https://arxiv.org/pdf/1512.06448v1)
- 本地证据：`research/notes/2026-11-05-candidate-token-baseline.md`
- 本地证据：`research/evidence/originals/P01-sourcerercc.pdf`
- [Kuttal与Ghosh，Source Code Comments: Overlooked in the Realm of Code Clone Detection，2020](https://arxiv.org/html/2006.14505v1)
- 本地证据：`research/notes/2026-11-09-comment-clone-method-reading.md`
- 本地证据：`research/notes/2026-11-09-comment-clone-artifact-readiness.md`
- [Li与Thompson，Incremental Clone Detection and Elimination for Erlang Programs，2011](https://www.cs.kent.ac.uk/pubs/2011/3087/content.pdf)
- 本地证据：`research/notes/2026-11-05-structural-semantic-candidates.md`
- 本地证据：`research/notes/2026-11-05-scc-wrangler-reproduction-readiness.md`
- [Kovačič等，Refactoring Codebases through Library Design，2025（v3）](https://arxiv.org/html/2506.11058v3)
- 本地证据：`research/notes/2026-10-27-librarian-reading-01.md`
- 本地证据：`research/notes/2026-11-05-librarian-reproduction-readiness.md`
- 本地证据：`research/notes/2026-11-11-librarian-presentation-audit.md`
- 本地证据：`research/evidence/originals/P21-librarian-v3-full.html`
- 本地证据：`research/notes/2026-11-11-manuscript-evidence-audit.md`

