# InMap原版输入流水线与初轮IR评分已实际运行

2026-11-11。本轮从静态工件核查推进到固定原实现的实际执行：编译2020候选快照的49个Java源文件，通过独立harness调用其原配置解析器、预处理、索引和空反馈集合下的初轮IR评分。**没有运行AutoMap完整推荐／反馈迭代，不称论文指标复现。**

## 固定输入与原样执行范围

版本为`cae17d87f8c17d8108d21abd41e0520b6ca65d7c`。通过作者GitLab固定SHA及path参数获取两个有界源码归档：InMap src包含49个文件，JabRef Java根包含1689个文件（含Java与已存预处理等文件）。全部数据文件的Git blob身份与前次19页固定目录树一致；不能只凭归档文件名声称版本固定。下载URL、归档SHA256及逐文件摘要存入`2026-11-11-inmap-fetch-01/downloads.json`，压缩包和原始解包仅在.tools缓存，不自动发布。

原49个Java文件没有修改；复制到全新隔离工作目录后编译。运行使用Temurin8u504、Lucene8.6.2、ASM6.2.1，依赖摘要保留。编译/执行位于无网络namespace及chroot中，只有实验工作目录可写；未执行JabRef代码或Gradle。原预处理器删除已有.jvtp再生成，原始缓存保留不变。

自编harness通过反射调用原私有loadConfigSettings，绕开默认Jittac入口和小写配置路径，不修改解析器；输入为已冻结PS50/MNBF33/MDBF1的单配置。初轮评分直接调用原IRAnalysis.getSimilarityAffinityScores，accepted映射为空，因而没有接受类名／方法名反馈；这是原评分阶段的有界调用，不是整个AutoMap调用。

## 原始运行结果

|产物|实际结果|
|原配置oracle|843条|
|原索引文档|843个，逐路径与源码名称集合一致|
|原filteredClasses|842个，与预期排除MacAdapter后的集合完全一致|
|filteredClasses中无oracle标签|BasicAction、PopupListener两项，与先前路径分析一致|
|初轮IR配对|5052条有限分数，涉及843个不同实体|
|完整迭代所需bin/static-cdg.txt|当前工作输入中不存在|

两个未覆盖实体的首轮最高分均为gui ui=1254，其他模块分数较小。此结果说明它们不是“完全没有可检索信号”；但不能据此宣称GUI是经过独立验证的正确职责，也不能说它们一定会出现在最终推荐页中。原oracle中没有这两个名称，精确匹配接受机制无法接受它们，仍须区分标签覆盖和算法漏检。

## 实际捕获的评分集合边界

第一版独立校验器要求所有评分实体属于filteredClasses，实际失败于MacAdapter。原始结果保留，另记validation-failure.json；没有修改原方法或删除该评分。重新描述事实：842个过滤后实体全部出现在评分集合，但被过滤的MacAdapter也有六个模块分数。

5052恰等于842×6，却不是完整矩阵：JabRefException仅有2项，JabRefExecutorService与PostgresSQLNotificationListener各5项，其余840个实体各6项。不能用总数推断集合完整。

原PreProcessing的文件路径排除与后续IR类名排除不同；实际索引含MacAdapter，IRAnalysis.filterEntries只去除已映射实体，不做排除集合过滤。另一方面，AutoMap后续最高分选择遍历unMappedClasses，来源于过滤后集合，所以**不能从评分含MacAdapter直接宣称最终会推荐被排除实体**。目前要检查的是它是否占据有限检索位置、影响其他配对；不是宣布最终误报或论文结论错误。

## 重跑与检查

- input-01：原配置／预处理／索引执行成功，未调用评分。
- input-02：增加初轮原IR评分；之后的独立集合断言失败，原因和反例已保存。
- input-03：全新隔离目录重新编译并运行；filtered-classes.txt、indexed-paths.txt、initial-ir-scores.tsv与02逐字节一致。
- input-04：显式将检索上限从842改为843的单因素控制，属于实验变体而非作者默认流程；其余源码、输入、空反馈和boost参数不变。

上述目录均位于`research/evidence/runs/2026-11-11-inmap-input-*/`，包含实际命令、退出码、stdout/stderr、harness、runner、配置、依赖摘要和产物SHA。stderr仅有JVM环境警告，检查未发现异常堆栈。复跑一致不是独立准确率验证。

```sh
python3 scripts/run_inmap_input_probe.py --run-id inmap-input-new-run
python3 scripts/check_inmap_input_probe.py research/evidence/runs/2026-11-11-inmap-input-02 --repeat research/evidence/runs/2026-11-11-inmap-input-03
python3 scripts/run_inmap_input_probe.py --run-id inmap-limit-control-new --retrieval-limit 843
python3 scripts/check_inmap_input_probe.py research/evidence/runs/2026-11-11-inmap-input-02 --limit-control research/evidence/runs/2026-11-11-inmap-input-04
```

## 完整迭代的缺口与下一项

DependencyAnalysis构造器需要programUrl下的bin/static-cdg.txt，并从中提取方法关键词，之后用于已接受实体的反馈检索。即便选择Search Only，也不能把缺图后捕获异常并继续的降级输出当作完整原方法。已确认2020 AutoMap与此前读取的2022 AutoMap逐字节一致，输出／终止契约见[审读记录](2026-11-11-inmap-runtime-output-contract.md)。

## 检索上限控制的实际结果

input-04得到5058=843×6个配对；与02共同的5052个配对分数完全相同，新出现的六项正是此前三个不完整行缺少的模块：JabRefException的cli/gui ui/logic/model、JabRefExecutorService的pref、PostgresSQLNotificationListener的global。实体集合和oracle未变化。

这验证六项缺失与本次查询的检索截断有关，不是这些实体与模块完全无匹配，也不是切换similarity的结果。它不证明六项会改变最终推荐或最终准确率。被排除对象留在索引但仍占检索位置，构成需在后续同预算评价里显式管理的边界；不能静默扩预算后声称方法改善。基准保留842上限，843变体单列。

图入口方面，已下载的generic模型只有模块、允许依赖与映射，不含所需方法调用记录，见[格式核查](2026-11-11-inmap-runtime-output-contract.md)。不能把允许关系当作实际调用图。下一项核查其他作者工件或有依据地重建图；若重建须固定抽取器、绑定数据版本并明确属于输入重建，不能拿其他版本图或空图代替。当前不报告最终precision/recall，也不进入Rust适配或生产重构。
