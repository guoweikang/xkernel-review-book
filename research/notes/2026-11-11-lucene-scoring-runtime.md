# InMap评分前置实验：查询解释比默认模型名称更重要

2026-11-11。本轮实际执行Apache Lucene8.6.2微型实验，**不是运行InMap，也不是复现SAC2021论文数字**。目的在于检验[静态审计](2026-11-11-inmap-scoring-audit.md)暴露的评分疑问，避免把“默认BM25”直接当作整条评分链的解释。

## 输入与执行边界

自编`research/tools/LuceneScoringProbe.java`使用六个内存文档：两个内容完全相同但路径不同的文档、词频较高的文档、前缀词cpus、拼写差异cpx、无关network文档。比较cpu、cpu*、cpu~、cpu*~以及按已读源码模式构造的`( cpu*~ )^30.0 ( node*~ )^2.0`。后者只是冻结的微型查询，不是从JabRef完整流水线捕获的真实查询。

每组分别以默认similarity和显式ClassicSimilarity建索引及检索。保存writer/searcher类型、解析后的查询类型、rewrite、逐命中原始分数和explain。另按已读IRAnalysis的路径命名乘除逻辑，在本地harness里模拟MNBF=30的调整，未调用InMap原函数。Classic是对照变体，不等于论文公式的完整复现。

依赖从Maven Central固定8.6.2取得：core、analyzers-common、queryparser、queries、sandbox。仓库SHA1与下载内容一致，并计算本地SHA256；这不是独立签名验证。Java为已存Temurin8u504。编译及运行位于独立user/mount/PID/network/IPC/UTS namespace和chroot，无网络、无仓库写访问，仅隔离工作目录可写；120秒CPU、512MB Java堆限制。原始stderr保留了JVM线程栈探测警告，退出码为0。

## 实际观察

|对照|实际结果|解释边界|
|默认similarity|writer/searcher均BM25(k1=1.2,b=0.75)|不代表所有查询子句都使用词频评分|
|cpu与cpu~|分别为TermQuery和FuzzyQuery|普通term在两种similarity下分数不同|
|cpu*~与cpu*|都为PrefixQuery，命中及分数相同|该组合在此版本和输入上没有得到“前缀加模糊”效果|
|cpx对照|被cpu~命中，未被cpu*~命中|不能把两种查询解释当等价|
|cpu*~重复词频|所有命中原始分数均1.0|该查询未利用词频差异排序|
|双子句模板|同时命中cpu和node得32，只有node得2|此例是boost后的常数子句相加；两similarity结果相同|
|相同内容、不同路径|原始分数相同；模拟调整后比为900|30乘与30除的比为30²，不能解释成语义相似度差900倍|

这些是构造输入上的组件现象，不是独立样本准确率。普通cpu查询中，重复词文档原始得分高于cpu.Node，但模拟路径调整后cpu.Node更高；这证明该启发式**能够**改变此构造样例的排序，不证明在实际JabRef或xkernel上有害。命名信号可能有助于映射现有架构，是否妨碍发现错位需要单独实验。

重要负结果：先前看到默认BM25后怀疑评分模型会造成差异，但在本次前缀模板中切换similarity没有改变命中分数。仅核对模型类名不足以解释行为；不能在没有真实查询证据时宣称论文数值因BM25不同而失效。

## 失败与复跑

- `2026-11-11-lucene-scoring-01`：Maven的.sha512入口404，在编译前失败；保留failure.json。随后使用同源SHA1一致性检查与本地SHA256留存，不把缺少.sha512当作jar不可用。
- `2026-11-11-lucene-scoring-02`：隔离脚本未设执行位，直接执行返回126；stdout/stderr、runner和依赖记录保留。下一次显式用bash启动脚本，不改变既有脚本权限。
- `2026-11-11-lucene-scoring-03`：编译与运行成功，原始输出、源码、runner、namespace脚本和依赖摘要留存于同名evidence/runs目录。
- `2026-11-11-lucene-scoring-04`：重新下载、校验、编译和运行成功；与03的stdout、依赖清单及Java源码SHA256完全一致。两次不是独立样本，只验证固定环境下可重复。

检查器的解析与分数断言来自首次运行后的观察，是回归检查，不是预注册统计假设。首次运行前固定的内容相同和路径乘除控制保存在runner中。没有把失败目录覆盖成成功结果。

```sh
python3 scripts/run_lucene_scoring_probe.py --run-id lucene-new-run
python3 scripts/check_lucene_scoring_probe.py research/evidence/runs/lucene-new-run
python3 scripts/check_lucene_scoring_probe.py research/evidence/runs/2026-11-11-lucene-scoring-03 --repeat research/evidence/runs/2026-11-11-lucene-scoring-04
```

## 接回研究问题

文档／代码相关性基线必须公开实际查询、重写方式、路径信号及反馈历史，而非只标注“TF-IDF”或“BM25”。下一步原InMap运行应保留未调整分数与路径调整分数，区分复现作者默认配置和去路径信号的探索变体；后者才用于测试模型是在识别能力还是复现已有布局。尚未执行该端到端对照，不宣布新方法优势。

依据：[固定IRAnalysis源码](https://git.cs.kau.se/zipasink/InMap/-/blob/6921e580c9dc009731010fe671942f19938fe236/src/recommender/ir/IRAnalysis.java)、[Lucene8.6.2发行源码](https://github.com/apache/lucene-solr/tree/releases/lucene-solr/8.6.2)、[SAC作者稿](https://www.diva-portal.org/smash/get/diva2:1552606/FULLTEXT01.pdf)。原论文与原项目结果仍分别登记。
