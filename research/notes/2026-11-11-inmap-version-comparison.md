# InMap候选版本对比：实现相同，配置接口已经变化

2026-11-11。实际下载并比较2020-12-24候选快照`cae17d87f8c17d8108d21abd41e0520b6ca65d7c`与2022-06-08固定头`6921e580c9dc009731010fe671942f19938fe236`的四个选定文件。不是全仓差异分析，也没有编译运行InMap。

## 字节比较结果

|文件|结果|
|`.classpath`|完全相同|
|`src/recommender/ir/IRAnalysis.java`|完全相同|
|`src/recommender/Evaluator.java`|完全相同|
|`test-systems/Jabref/config-jabref.json`|不同，完整unified diff已保存|

这缩小了“可能只是2022评分实现变化”的解释空间：已读评分源码及声明的classpath在候选论文前快照中已经存在。但还不能证明论文作者实际执行的jar、配置、数据和命令就来自这个快照。

## 影响最小运行的具体差异

旧配置使用`ProgramMapping`和`PackageExclusion`，新配置改成`EntityMapping`和`ExclusionList`。相同的Evaluator源码在73–138行的arrayKey switch只处理前两个旧名称，没有新名称分支。因此本次取得的新JabRef配置与这个解析入口不匹配；这是静态读取结果，未把它写成实际启动报错。

新配置还移除了旧配置的WeightingType、NormalizationType、ThresholdType数组，而Evaluator的run路径319–353行读取并遍历它们。旧映射为逐类条目，新映射包含包级条目与类级例外；不能只改字段名称就认为恢复了相同oracle语义。

旧配置参数范围为PS=20–50（步10）、MNBF=30–40（步1）、MDBF=1–2（步1），包括论文报告的PS50、MNBF33–35、MDBF1。新配置固定20、30、2。包含论文参数不证明实际结果相同；原样扫描旧配置也不符合本轮有界冒烟预算。

旧源码目录为`test-systems/Jabref/sources/3.7/src/main/java/`，新配置为`test-systems/Jabref/src/3.7/src/main/java/`。两版Evaluator都仍引用小写jabref配置路径；在大小写敏感系统需要明确环境适配。此前文件级Apache头也随IRAnalysis字节一致得到历史确认，但没有扩大为全仓授权声明。

## 后续执行选择

优先使用2020候选快照核对实际数据、oracle与入口，选定单个论文范围内参数组合，保留旧配置原件及适配差异。不在2022配置上连续猜补字段，不把版本接口问题归因于算法召回或精度。先取得能复核的最小原任务运行，再考虑Rust前端及去路径信号对照。当前没有原任务运行结果，不称找到论文精确版本。

证据：`research/evidence/runs/2026-11-11-inmap-version-comparison-01/`内8份原件、逐URL/字节数/SHA256的provenance、选定文件diff、比较报告与collector源码。重跑工具：

```sh
python3 scripts/compare_inmap_versions.py --output research/evidence/runs/inmap-version-new-run
```

原始入口：[候选快照](https://git.cs.kau.se/zipasink/InMap/-/tree/cae17d87f8c17d8108d21abd41e0520b6ca65d7c)、[固定头](https://git.cs.kau.se/zipasink/InMap/-/tree/6921e580c9dc009731010fe671942f19938fe236)。完整可达历史及许可范围见[历史核查](2026-11-11-inmap-history-preflight.md)，评分运行控制见[组件实验](2026-11-11-lucene-scoring-runtime.md)。
