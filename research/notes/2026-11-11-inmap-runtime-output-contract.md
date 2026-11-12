# InMap运行输出契约：静态核查

2026-11-11。仅读`research/evidence/runs/2026-11-11-inmap-preflight-01/src__recommender__AutoMap.java`，其来源是**2022固定提交`6921e580c9dc009731010fe671942f19938fe236`**，不是本轮拟运行的2020候选`cae17d87f8c17d8108d21abd41e0520b6ca65d7c`。AutoMap两版本尚未比对，以下只能作为运行检查清单，不能直接宣称2020实现完全一致。原文件URL/hash见上述目录`download-provenance.json`；行号均指该归档文件。没有下载依赖、运行或改脚本。

## 1. 终止与执行路径

- `call():164–297`重设页号、runMapping等状态，循环执行IR评分、移除曾拒绝的映射、选择每类最高分、产生建议、接受/拒绝和记页结果。`:249–273`的依赖评分、归一化和组合调用处于注释中；输出存在权重字段不证明该轮确实运行组合评分。构造器`:117–123`仍创建DependencyAnalysis并取类数/方法，因此不能反推完全没有依赖分析成本。
- `produceRecommendedMappings():840–872`应用阈值后若建议为空，通常令`runMapping=false`；若权重类型含`Search Only Then`且尚未runComplete，先改两个状态，后续空建议才停止。这不是达到100%覆盖才停，也不是“无建议意味着职责已全部正确”。本文件所读主循环没有显式最大页数、总时间或调用预算；外部超时须与算法自然终止区分。
- `printAffinityScores():1061–1064`另有无有效结果时停机分支。`:292–295`在循环后依次写页JSON、图JSON、HTML，再打印Completed；没有显式结构化终止原因字段。
- 空结果特殊路径`:1088–1100`计算`precision=0`后仍计算F1；若recall也为0则表达式为0/0，再构造BigDecimal，存在静态异常风险。未运行验证，不能把“没有结果文件”直接解释为零召回成功完成。

## 2. 计数和分母不能混同

|字段／集合|源码定义|报告边界|
|---|---|---|
|`numOfClasses`|构造器`:119`取`depAnalysis.numOfClasses()`，IR类数赋值被注释|不是自动等于843源码文件、843oracle名称或论文842类；实际运行应保存此值及对应实体集合来源|
|`unMappedClasses`|`:746–777`从IR的filteredClasses中减去accepted集合的类名并集|它与依赖分析分母可能不同；HTML中`numOfClasses−numOfMappedClasses`不必等于此集合大小|
|`numberOfAcceptedClasses`、`numberOfRecommendations`|`:909–970`每页重置，过阈值的建议按配置oracle判定，逐项累加；`:974`将本页accepted加入累计数|前者是本页接受计数，后者是本页实际处理建议数，不是唯一类总数或所有可能class-module对|
|`acceptedMappings`／`mappedClasses`|`:76–80`均以HashSet去重；`:935–946`接受后加入；`:746`起可重建类名并集|集合唯一数与累计接受事件数须交叉核对，不能不检查就视为恒等|
|`numOfRejectedMappings()`|`:301–310`求各模块rejected类名HashSet大小之和|计不同的拒绝class-module对，不是唯一被拒绝类。一个类可先被几个错误模块拒绝，后来映到正确模块|
|页precision|`:1018–1019`为本页accepted/本页recommendations，输出保留两位小数|不能平均各页precision冒充总体precision；不同页建议数可能不同|
|最终HTML recall/precision|`:1187–1200`分别为mapped类数/依赖分析类数；累计accepted/(累计accepted＋去重拒绝对数)|前者是该程序分母下的映射覆盖，后者混用接受累计数和拒绝集合数，需核对事件去重性质；不是架构违规准确率或目标职责正确率|

`removeRejectedMappings():329–345`从后续分数候选中剔除已拒绝对，`retrieveUnMappedClasses()`排除已接受类，意图避免同对反复推荐；但**同一类换模块再推荐仍可发生**，推荐总次数大于唯一类数并不自动是重复计数bug。实际运行应记录每页class-module建议与反馈，核对同对重现、跨模块重试和accepted累计数；当前页汇总不足以重建这些事件。不得把“901建议”之类的计数直接当901个独立类样本。

## 3. 哪些工件能证明本次实际执行

源码输出位置统一为`eval-results/results/<timestamp>/run-results/<program>/`：

- `*-run-<runCount>-results-data.json`（`:1142–1164`）是**无字段名的8列行数组**，依次为页号、IR权重、依赖权重、threshold、本页“accepted / recommendations”字符串、页precision、累计mapped类数、映射百分比。内存`runResults`含更多字段，但写出的这份JSON没有直接保存累计rejected或每条建议。
- `*-run-<runCount>.html`（`:1187–1246`）含配置、分母、最终recall/precision和拒绝数；读取已有HTML仅是查看已有结果，不证明重新执行。普通页记录`:1056`写的是`thresholdFilter`而非实际可能动态更新的threshold，不能据列名认定记录了每页真实平均阈值。
- `*-run-<runCount>-graph-data.json`（`:1255–1323`）含accepted模块节点、未映射节点和依赖边；不是完整拒绝日志或独立真值。生成时的unMapped集合来自最近一次刷新，不应未经集合一致性检查就当最终精确补集。

**建议本次执行最小证据链**：独立空输出目录＋固定源码/适配补丁/配置/输入摘要＋实际JDK/classpath＋完整命令和起止时间/退出状态/标准输出错误＋本次新建文件清单和摘要。日志应能对应`RUN CONFIG`、页进展和结束阶段，结果程序/参数与计划一致；独立解析输出，检查页数、原始整数计数、分母和最终集合。`Completed`或exit0单独不足：源码多处catch IOException只打印堆栈（如`:1167–1170`、`:1248`附近），文件写入失败不一定传播为非零退出。仓库自带历史结果、时间戳目录名或单个百分比都不构成本次运行证据。

## 4. 给主线程的停止门槛

运行前先确认2020 AutoMap是否与上述文件一致；若不一致，以实际运行版本重新定位关键行和公式。若最小原任务产生新工件且证据链完整，可称“固定版本、单配置原工具执行/冒烟”；只有数据、参数、反馈与分母进一步对齐后才谈论文指标复现。超时、异常、空结果或只有旧HTML均单独记录，不补写成功。本文不证明2020已运行，不给性能或标签可信性结论。

## 5. 同日补查：2020 architectures目录的图入口

主线程报告2020 DependencyAnalysis构造需要`programUrl + "bin/static-cdg.txt"`且从图抽取方法关键词；这是主线程源码核查结论，本页未另读2020 DependencyAnalysis。按追加请求，本轮只取固定`cae17d87f8c17d8108d21abd41e0520b6ca65d7c`的`test-systems/Jabref/architectures`递归tree：**16项、单页、无后续分页**。此前完整Jabref根目录清单未见bin，本次architectures树也未见名为`static-cdg.txt`的文件。

发现可进一步检查、但尚未验证格式的入口：

- `architectures/JabRef-3.7-0002/jabref-generic.txt`
- `architectures/JabRef-3.7-0002/jabref.xam`
- 同目录`README.md`、`jabref-diagram.png`

其他条目主要为高层文档、intended architecture/violations表和source-vs-binary表。**本轮只看文件名/tree，不能据名字认定generic或xam含调用边、方法关键词，或可替代static-cdg格式。** 没有下载这些内容，没有转换、生成空图或执行作者工具；不能以图缺失时的降级输出冒充完整原方法。

原始tree响应保存于`research/evidence/runs/2026-11-11-inmap-data-readiness-01/architecture-tree-page-1.json`，实际固定URL及SHA256已追加同目录`download-provenance.json`。下一步由主线程检查上述小型入口/来源及格式；若需重建图，须绑定源码、抽取器版本和转换规则，明确与作者原输入的差异。未取得兼容图以前保持“执行前置缺口”，不能由本次有界树检查断言全仓绝无图。

## 6. 同日收束：generic文件不是所缺方法调用图

本轮对同一2020固定提交的`architectures/JabRef-3.7-0002/README.md`与`jabref-generic.txt`设置每文件2MiB保存上限；实际分别取得**322字节、1844字节，均读至EOF、完整保存**。归档于`research/evidence/runs/2026-11-11-inmap-architecture-format-01/`，`download-provenance.json`含固定URL、SHA256、完整性及限额记录。没有转换或运行。

README全文说明：xam是JITTAC模型，generic以工具无关形式描述模块、依赖和映射。generic全文确有三段：`Modules`（gui/CLI/logic/globals/model/pref）、`Allowed Dependencies`（模块间允许边）、`Mappings`（模块对应的类名和包名前缀）；例如`logic -> model`是**许可依赖**，不是观察到的类/方法调用边。全文未见方法签名、caller/callee记录或调用次数；类名/包名出现在映射中，不是完整实际类依赖图。末尾还有孤立字符`2`，未擅自清理或解释。

结论：**这两份文件不能直接替代主线程所述的`bin/static-cdg.txt`方法调用图及方法关键词输入。** 把Allowed Dependencies转成实际调用边会把规范混作实现证据；补空图也会改变原方法。它们可作为另一份高层模型/映射资料，但与运行配置的模块命名和展开规则是否一致未在本轮核对。xam内容仍未取得，不能从generic推断其一定包含或不包含完整图。

主线程另告知AutoMap2020/2022已字节一致，并已编译49个2020源文件、运行配置/预处理/索引/初轮IR；本页将这些标为**主线程进展通知**，未独立重跑或审计其日志。前文版本未对齐的提示据此得到主线程补证，但不能据局部IR运行宣称完整反馈循环已跑通。图前置缺口仍须单独解决。本次文件写入完成，到此停止。
