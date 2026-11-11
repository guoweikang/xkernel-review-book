# InMap评分与反馈oracle静态审计

日期：2026-11-11。固定作者仓库提交 `6921e580c9dc009731010fe671942f19938fe236`。本轮下载并定向读取`IRAnalysis.java`、`IndexFiles.java`、`PreProcessing.java`，交叉读取上一轮同提交的`Evaluator.java`、`AutoMap.java`和JabRef配置；补核Apache官方Lucene8.6.2源码。**没有执行、编译、修改作者代码或重新评价数据。** 结论为静态证据，不是原作者运行时观测。

## 1. 论文“TF-IDF”与当前实现并非可直接视为同一公式

此前取得的SAC2021[作者稿§3 STEP5](https://www.diva-portal.org/smash/get/diva2:1552606/FULLTEXT01.pdf)写`tf × log(N/df)`并称使用Lucene返回的权重。本轮代码证据如下（路径均相对固定作者仓库）：

- [`src/recommender/ir/IRAnalysis.java:271`](https://git.cs.kau.se/zipasink/InMap/-/blob/6921e580c9dc009731010fe671942f19938fe236/src/recommender/ir/IRAnalysis.java#L271)：直接构造`IndexSearcher(reader)`，用`StandardAnalyzer`和`QueryParser`查询`contents`；所读完整文件没有`setSimilarity`或`ClassicSimilarity`设置。
- [`src/recommender/ir/IndexFiles.java:93`](https://git.cs.kau.se/zipasink/InMap/-/blob/6921e580c9dc009731010fe671942f19938fe236/src/recommender/ir/IndexFiles.java#L93)：`IndexWriterConfig(analyzer)`也未覆盖similarity。`:199`存储path，`:206`以TextField索引contents。
- 官方[Lucene8.6.2 IndexSearcher源码:117、166](https://github.com/apache/lucene-solr/blob/releases/lucene-solr/8.6.2/lucene/core/src/java/org/apache/lucene/search/IndexSearcher.java#L117)分别定义默认`new BM25Similarity()`并赋给实例；[LiveIndexWriterConfig:125](https://github.com/apache/lucene-solr/blob/releases/lucene-solr/8.6.2/lucene/core/src/java/org/apache/lucene/index/LiveIndexWriterConfig.java#L125)也取该默认值。8.6.2来自本仓库前次归档的`.classpath`及lib目录条目；Manifest仍写8.4.1，是另一个既知版本差异。

**有条件静态结论**：若按固定树声明的未修改Lucene8.6.2加载执行，所读路径使用默认BM25 similarity，而不是代码显式实现论文的裸TF-IDF乘积或TF-IDF cosine。不能反推作者2021实验一定运行BM25：当前提交是2022快照，实际实验classpath、jar身份和旧提交尚未核实。未运行查询解释器，不能把每种查询子句的实际贡献都简化为单一BM25项；本轮也不擅改成ClassicSimilarity后宣称原样复现。

另外，最终IR分数还有显式启发式，不只是Lucene返回值：`IRAnalysis.java:317–369`构造带模块名/描述boost的查询，`:372–484`加入已接受类名与方法名；`:494–513`取Lucene hits及score，`:516–530`检查从路径生成的文档/类名是否包含模块名词，命中则乘MNBF，否则除MNBF。这里有**现有包/类命名信号**，不能称完全独立于布局的纯职责文本评分；`*~`拼接的实际QueryParser解释尚未动态核验。

[`PreProcessing.java:124`](https://git.cs.kau.se/zipasink/InMap/-/blob/6921e580c9dc009731010fe671942f19938fe236/src/recommender/ir/PreProcessing.java#L124)起按行和正则拆分代码/注释，`:137`去import、`:140`去匹配的private行，`:189`起做停用词/关键词处理，`:201`加入类名，`:206`实际合并comments与codeOnly。不能把它描述成仅自然语言文档检索、完整Java语义解析或已经适配Rust的前端。

## 2. 与标签边界的接口

详细反馈定义与目标职责边界由主线程独立笔记 `research/notes/2026-11-11-inmap-label-boundary.md` 承接，本页不重复展开。评分侧已核对：`IRAnalysis.java:257–260`接收accepted映射，`:372`后将已接受类/方法加入查询；因此后续分数取决于反馈历史，不是固定文本之间的一次性相似度。当前评分及其oracle接受都不能单独证明目标职责正确，也不能据命名特征推断全部oracle均由目录派生。

## 3. 交给后续验证的评分差异检查（本轮未执行）

建议先锁定实际classpath与jar摘要，记录运行时`IndexSearcher.getSimilarity()`及writer similarity，再对一条冻结查询保存QueryParser解析结果和`explain()`证据。比较时分开记录Lucene原始hit score、包/类路径包含模块名后乘除MNBF的分数、后续归一化/组合分数；不要把整条评分链直接称为BM25或裸TF-IDF。反馈迭代需同时固定accepted集合，否则查询本身已变。

若另试ClassicSimilarity或论文所列TF-IDF公式，须作为明确的对照变体，而非静默修复原实现。这里尚未证明评分差异改变排名或论文数字，更未证明哪种评分更适合职责判断；需要后续实际验证，不能从静态默认值差异直接宣布论文实验错误。

## 4. 实际归档与未验证项

目录：`research/evidence/runs/2026-11-11-inmap-scoring-audit-01/`；`download-provenance.json`保存每个文件的完整原始URL、字节数和实算SHA256。

|固定源码|字节数|SHA256|
|---|---:|---|
|`IRAnalysis.java`|24946|`27abe716ee3027239a2e6c90402fb436b150bc60a62aa876fd5e468e4e36dea2`|
|`IndexFiles.java`|8204|`bdefc932320577c751d1565122030bd968d4536a0d6d134e871b918779825b2b`|
|`PreProcessing.java`|9833|`a53c6317559e0a6f4ea9dea2353eb21d4799c90d7b5540a715c0c79db8b6e215`|

另归档官方发行标签的`lucene-8.6.2-IndexSearcher.java`及`lucene-8.6.2-LiveIndexWriterConfig.java`，摘要同在provenance中；仅作源码阅读。此前的AutoMap/Evaluator/配置仍引用`research/evidence/runs/2026-11-11-inmap-preflight-01/`，未改动。

官方检索为直接打开[8.6.2 IndexSearcher文档](https://lucene.apache.org/core/8_6_2/core/org/apache/lucene/search/IndexSearcher.html)及[IndexWriterConfig文档](https://lucene.apache.org/core/8_6_2/core/org/apache/lucene/index/IndexWriterConfig.html)，页内找`BM25`未命中后读取上述官方发行源码，不依赖搜索摘要推断默认值。未核验实际jar内容、运行时classpath、完整推荐/归一化/终止路径、标签覆盖及论文实验提交；没有评分结果、性能结论或复现成功声明。
