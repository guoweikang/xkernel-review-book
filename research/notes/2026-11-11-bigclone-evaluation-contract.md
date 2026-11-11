# BigCloneEval：reference slice 的最小评估契约

2026-11-11。只读作者仓库固定提交 `6d393ec8adb1d71493d09881ba520659b6c2c68e` 的 README、目录树及下列源码；未下载完整数据库/源码数据集，未安装或执行评估。数据下载元信息及路线选择由主线程负责。本笔记提出切片契约，不声称已有可运行切片。

## 依赖：源码切小不等于数据库可以省略

[固定 ReadMe.md：Installation Steps 2/3、Experimental Process](https://github.com/jeffsvajlenko/BigCloneEval/blob/6d393ec8adb1d71493d09881ba520659b6c2c68e/ReadMe.md) 分别要求 BCB 数据库、IJaDataset 源码，并区分检测、导入结果、评估。源码供检测器产生结果；匹配/计数依赖参考数据库和工具结果数据库。`BigCloneBenchDB.java:37–38` 使用 `bigclonebenchdb/bcb` 的 H2 连接并设置 `IFEXISTS=TRUE`；不是下载几个 Java 文件即可运行官方评分器。[数据库连接源码](https://github.com/jeffsvajlenko/BigCloneEval/blob/6d393ec8adb1d71493d09881ba520659b6c2c68e/src/database/BigCloneBenchDB.java#L37)

`CoverageMatcher.java:60–96` 从 ToolsDB 查导入区间，同时经 Functions.get 取得参考两端文件身份/行号；默认两端各自覆盖参考区间至少70%，两种端点顺序均尝试。这个70%是**匹配覆盖率**，不是检测器 token 相似阈值。`EvaluateTool.java:58,89–101` 默认 `CoverageMatcher 0.7`，向 evaluator 传尺寸、judges/confidence 等筛选参数。[Matcher](https://github.com/jeffsvajlenko/BigCloneEval/blob/6d393ec8adb1d71493d09881ba520659b6c2c68e/src/cloneMatchingAlgorithms/CoverageMatcher.java#L60)；[入口](https://github.com/jeffsvajlenko/BigCloneEval/blob/6d393ec8adb1d71493d09881ba520659b6c2c68e/src/tasks/EvaluateTool.java#L89)。因此若自行导出轻量评分数据，至少需参考配对、两端身份/原行号、所用筛选字段及匹配规则；这种替代须另验证，不能自动称为原版 BCE 执行。

## 最小有效切片（我们的建议）

匹配器边界补充：上述覆盖率描述针对默认分支。固定 `CoverageMatcher.java:65–69,98–107` 的可选 line/ratio tolerance 分支存在待核对的占位符/绑定编号疑点：基础参数为1–10，后续绑定从12开始；line 分支追加4个占位符却绑定至15。本轮不扩查、不运行验证，不保证这些可选模式可用，也不据静态疑点宣称已复现故障。任何原版 evaluator 运行成功的表述均不属于本笔记结论。

预先冻结非空参考集合 R、筛选条件、数据版本和配对ID；令检测语料包含 R 两端的原始文件，保留文件身份与原行号。只截方法文本而不做坐标映射，会破坏官方匹配契约。分母是 R 中满足预定条件的参考配对数，分子是按固定 matcher 命中的参考配对数；分母为0应报告不适用。**不能只挑检测器已命中的正例再选 R。**仅在正例端点文件上运行仍是受限正例切片召回，不是完整项目发现召回或规模评测。

更贴近原框架的小范围路线是选择一个有参考标注的 functionality，确保其计分参考两端都在检测语料中，并只报告该功能的行，而不报告全库汇总。源码 `ToolEvaluator.java:172–199` 提供按功能与全库计数，`:2480` 仍加载数据库全部 functionality；本轮所读入口/构造器没有任意文件白名单参数。故任意若干文件切片不能只靠减少检测输入就同步缩小官方分母；需另行冻结参考集并实现/验证筛选，或明确读取与语料对应的功能报告。数据库可以保留完整，源码可按目标范围缩减；物理裁剪数据库及其schema/关联闭包本轮未验证，不给出“最少几张表即可”的保证。[Evaluator 固定源码](https://github.com/jeffsvajlenko/BigCloneEval/blob/6d393ec8adb1d71493d09881ba520659b6c2c68e/src/evaluate/ToolEvaluator.java#L172)

## 不完整真值与 precision

官方主流程测参考克隆 recall，并不保证穷尽语料中全部真克隆。值得注意：不能简单写“代码没有 precision”——`ToolEvaluator.java:393–410` 确有 precision 方法，以**命中的已知正/负参考项**计比值；这不是拿所有检测器输出逐条独立标注后的 precision。未标注输出不能一律作 false positive，已知负例上的命中率也不能充当全集 FPR。最小切片只支持其参考范围的召回；Rust 可重构性、性能或维护收益仍无真值依据。[precision 方法及注释](https://github.com/jeffsvajlenko/BigCloneEval/blob/6d393ec8adb1d71493d09881ba520659b6c2c68e/src/evaluate/ToolEvaluator.java#L393)

## 许可及未核实事项

固定树有根 [`license`](https://github.com/jeffsvajlenko/BigCloneEval/blob/6d393ec8adb1d71493d09881ba520659b6c2c68e/license)，正文为 GNU GPL Version 2；不能标框架“无可见许可”。另有 [`libs/licenses`](https://github.com/jeffsvajlenko/BigCloneEval/blob/6d393ec8adb1d71493d09881ba520659b6c2c68e/libs/licenses) 列依赖许可链接。补核 [BigCloneBench 作者仓库当前 README 的 License 节](https://github.com/clonebench/BigCloneBench/blob/master/README.md#license)（2026-11-11读取，浮动分支，不是上述 BCE 固定提交）：明确数据库及其派生物采用 **CC BY-NC 4.0**；IJaDataset 保留各文件原有许可证，数据库记录来源和检测到的许可。**框架 GPL 不能替代数据库许可或源码逐文件许可**；本轮未检查数据包内部逐文件声明，不作商业用途可行性或其他法律结论。

主线程交接的下载探测状态：两个官方分享入口均返回 HTTP 200 HTML landing page，仅各读64KiB，不是数据包正文；本 sidecar 未复跑或审计其报告。该状态不能证明完整数据可下载，也不能证明不可用或必须登录。README 的“可能需要登录”须保留条件语气。若主线程转做小型 matcher 集成测试，它只能证明所构造输入上的接线/匹配行为，不能替代真实 reference slice 的数据库、分母与检测评估；本轮不重复实现该测试。

实际读取：固定 raw README、根 license、GitHub recursive tree，定向下载小型 Java 源码到临时目录阅读，包括 `MixinOptions.EvaluationOptions`；无数据库访问、检测、基准执行或结果生成。未验证完整性、真实数据库schema/版本兼容、筛选后实际分母及任何检测效果。
