# InMap完整迭代的缺方法反馈对照

## 问题与实验身份

2026-11-11。当前恢复入口没有取得作者的`static-cdg.txt`，但原实现捕获缺文件异常后继续执行。实际运行这一分支，可以建立后续恢复方法关键词时的对照，不能代替原论文完整复现。

采用固定候选提交`cae17d87f8c17d8108d21abd41e0520b6ca65d7c`、原49个Java源文件、作者固定JabRef源码和原oracle。源码不修改，不创建伪调用图。包装器调用原配置解析器及`AutoMap.call()`；参数PS50、MN33、MD1、Search Only、None、Recommendation Average，初始映射比例0。包装器断言调用图不存在且方法反馈表为空；已接受类名称反馈仍然保留，因此这不是“无全部反馈”对照。

输入来源及哈希见[原流水线执行](2026-11-11-inmap-original-input-run.md)；恢复入口范围见[调用图核查](2026-11-11-inmap-graph-recovery.md)。原实现入口：[AutoMap](https://git.cs.kau.se/zipasink/InMap/-/blob/cae17d87f8c17d8108d21abd41e0520b6ca65d7c/src/recommender/AutoMap.java)。论文身份与数据边界见[输出契约](2026-11-11-inmap-runtime-output-contract.md)。

## 实测结果

两次从干净构建目录执行均正常退出；核心五份输出逐字节一致。两次缺图警告保留于stdout，不隐藏失败输入。

|指标|本对照结果|
|---|---:|
|过滤后的类|842|
|非空推荐结果页|28|
|推荐事件|874|
|标签接受映射|823|
|标签拒绝映射|51|
|推荐事件的标签一致率|823/874 = 0.941648|
|总体映射比例|823/842 = 0.977435|
|最终未映射类|19|
|其中无oracle标签|2|
|有标签但未映射|17|

终端打印进入第29次循环，不等于29个有推荐结果的页面。独立检查逐页事件求和并与最终接受／拒绝集合对照，确认本次没有重复事件计数差异；不推断其他配置也必然满足。

19个未映射实体中，6个曾被推荐并拒绝，13个未出现在接受或拒绝集合。13个全部有标签。这把失败定位从笼统“没有映射好”细分为候选未被推荐、推荐未获标签接受、标签本身缺失。不能仅据终态集合判定未推荐的具体原因是截断、同分处理还是阈值；需要终止轮中间状态。

被排除的MacAdapter没有进入最终接受／拒绝集合。此前发现“评分包含被排除实体”不能直接升级为“最终输出了被排除实体”。

## 可复核产物

- 包装器：`research/tools/InMapLoopProbe.java`。
- 运行器：`scripts/run_inmap_input_probe.py`，新增显式`--missing-method-loop`，与检索上限覆写互斥。
- 独立检查：`scripts/check_inmap_loop_probe.py`。
- 原始记录：`research/evidence/runs/2026-11-11-inmap-loop-01/`及`2026-11-11-inmap-loop-02/`。
- 每轮保存配置、依赖校验、包装器、运行器、隔离脚本、命令、stdout/stderr、过滤集合、oracle、逐页统计、接受／拒绝映射和作者生成的HTML/JSON。复跑验证在第二轮`validation.json`。

复跑命令：

```bash
python3 scripts/run_inmap_input_probe.py --run-id NEW-UNUSED-ID --missing-method-loop
python3 scripts/check_inmap_loop_probe.py research/evidence/runs/2026-11-11-inmap-loop-01 --repeat research/evidence/runs/2026-11-11-inmap-loop-02
```

## 对研究目标的意义与下一实验

这不是重复功能检测的准确率，更不是架构合理性的真值。标签一致说明回到了作者给定模块归属，不能证明该归属本身正确。单个JabRef配置也不支持Rust跨项目泛化。

方法反馈缺失、候选版本身份、参数选择和实际论文环境尚未全部对齐，不能把与论文结果的差值归因于缺方法反馈，更不能用本对照较高的标签一致率宣布优于论文。

下一实验先导出终止轮评分、候选筛选及剩余类状态，定位17个有标签未映射对象；只在包装器读取状态，不改变原推荐实现。随后评估从固定源码重建方法关键词的可行性，明确区分源码定义的方法、调用端出现的方法和作者调用图关键词，保留集合差异。只有输入语义对齐后才能进行同配置反馈对照。对xkernel的迁移仍是研究假设：文档／方法／调用关系可能补充职责候选发现，不能自动把映射不一致裁决为职责错位。
