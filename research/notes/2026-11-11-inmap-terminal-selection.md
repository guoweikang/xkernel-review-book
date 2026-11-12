# InMap终止轮：唯一最高分也可能被候选选择删除

## 所属问题与实验目的

研究问题：职责映射候选没有输出，究竟是输入缺失、评分不足、候选选择还是标签拒绝？本实验继续[缺方法反馈对照](2026-11-11-inmap-missing-feedback-control.md)，不是新映射算法或完整论文复现。只给包装器增加终态读取及运行结束后的隔离输入控制，不修改原49个Java源文件。

## 运行与证据

固定候选版本`cae17d87f8c17d8108d21abd41e0520b6ca65d7c`；数据、oracle和参数与前一对照一致。两轮分别保存至`research/evidence/runs/2026-11-11-inmap-terminal-01/`和`2026-11-11-inmap-terminal-02/`。

包装器在原`call()`完成后导出评分、最高分候选、推荐集合和终止状态。分数已经经过拒绝映射移除，不是原始检索分数。两轮与先前loop-01的五份核心输出逐字节一致，读取终态未改变已经保存的推荐结果。第二轮另在保存全部真实结果之后，清空已接受状态并注入四组人工分数，反射调用原私有选择方法；这些控制不属于真实推荐序列。

## 实测终态

原循环进入第29轮时停止，最高分候选和推荐集合都为空，阈值为0。19个未映射对象分为：

|终态类别|数量|说明|
|---|---:|---|
|没有剩余分数|1|JabRefException；仅凭终态不能区分检索截断和此前拒绝等完整历史贡献|
|最高分并列而未被选择|8|存在评分，但多个模块并列最高|
|唯一最高分而未被选择|10|不是“没有信号”，也不是在此终止轮被平均阈值筛掉|

例如WaitForSaveOperation的gui ui分数为1451.4722900390625，其他模块最高约0.0909，仍未进入最高分候选。此处分数包含原命名乘除权重，不是校准后的置信概率。

## 原选择器的四个输入控制

分数按原模块顺序model、logic、pref、gui ui、cli、global注入到一个真实过滤集合内的类；其余类无评分。

|输入分数|数学上的唯一最高值|原方法选中配对数|
|---|---|---:|
|1,2,9,0,0,0|有|1|
|1,1,9,0,0,0|有|0|
|1,9,9,0,0,0|无|0|
|1,9,2,2,0,0|有|1|

第二个控制表明，较低分的早期并列会影响后面唯一最高分的选择。这是原方法直接执行的结果，不是Python重实现模拟。

固定源码[AutoMap.java](https://git.cs.kau.se/zipasink/InMap/-/blob/cae17d87f8c17d8108d21abd41e0520b6ca65d7c/src/recommender/AutoMap.java)的`pickHighestClassScore`将早期并列的`oldMap`加入`similarScoreMappings`，随后用`oldMap.putAll(newMap)`继续改变同一个对象；最后按该对象当前内容删除候选。早期并列记录没有在出现更高分时被撤销，因此可能删除后来的唯一最高分。该实现还涉及可变Map用作键；本次不扩展为通用Java缺陷研究。

## 对方法研究的影响

不能把这10项遗漏直接归为“缺方法关键词”，更不能通过添加文档信号掩盖候选选择器的损失。原baseline、修正选择器的实验变体和新增信息机制必须分别标记，否则无法判断收益来自哪里。

该结果只定位固定候选实现及当前对照，不证明论文实验版本具有同样问题，不证明职责正确，也不证明整个研究方法无效。19个对象的逐项终态保留在analysis.json；没有逐轮全轨迹，不能宣称解释了每个对象全部历史路径。

## 固定复核入口

```sh
python3 scripts/run_inmap_input_probe.py --run-id NEW-UNUSED-ID --missing-method-loop
python3 scripts/analyze_inmap_terminal.py research/evidence/runs/2026-11-11-inmap-terminal-02
python3 scripts/check_inmap_loop_probe.py research/evidence/runs/2026-11-11-inmap-loop-01 --repeat research/evidence/runs/2026-11-11-inmap-terminal-02
```

分析器核验原run哈希、有限分数、配对唯一性、原选择器输入拷贝一致、终止标志及五类诊断控制；若存在四组Java控制，也核对其实际结果。检查验证输出与分类契约，不把分类正确性升级为设计真值。

## 后续同配置选择器对照

已将上述比较实施为独立变体：仅在隔离构建副本替换`pickHighestClassScore`，选择最终唯一最高分；真正最高分并列仍不输出。原工具缓存和原始run不修改。替换文本保存在`research/tools/InMapUniqueMaximum.txt`；runner记录移除的方法文本、修改前后SHA256及`original_sources_modified=true`，不再声称该变体原源码未改。

`2026-11-11-inmap-selector-01`与`-02`保存两次运行；检查器对齐配置、依赖、oracle、过滤集合和候选版本。两轮核心输出一致。与原版比较：

|指标|原选择器|唯一最高分变体|
|---|---:|---:|
|接受映射|823|832|
|拒绝映射|51|52|
|推荐事件|874|884|
|未映射类|19|10|
|标签一致率|0.941648|0.941176|

新增9个gui ui接受映射，新增JabRefExecutorService→global拒绝；原接受／拒绝配对无减少。输出更多并未提高标签一致率，不能仅报覆盖上升而隐藏额外拒绝。查询反馈轨迹随新接受映射变化，因此这是选择器改变对整个循环的效果，而不是固定查询下的单次打分实验。

```sh
python3 scripts/run_inmap_input_probe.py --run-id NEW-UNUSED-VARIANT-ID --missing-method-loop --unique-maximum-control
python3 scripts/compare_inmap_selectors.py research/evidence/runs/2026-11-11-inmap-terminal-02 research/evidence/runs/2026-11-11-inmap-selector-01
python3 scripts/check_inmap_loop_probe.py research/evidence/runs/2026-11-11-inmap-selector-01 --repeat research/evidence/runs/2026-11-11-inmap-selector-02
```

这组实验排除了“新增方法语义信号导致这9个新增接受”的解释：没有新增方法词表，变化来自选择器。它是复现有效性诊断，不作为新语义方法或专利贡献。下一步输入扩展受[方法关键词契约](2026-11-11-inmap-method-keyword-contract.md)约束，Java定义方法只能作为替代输入，不得称恢复作者原图。优化内核实现仍不在本轮范围。
