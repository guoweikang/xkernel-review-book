# 842与840：先区分标签覆盖限制和检索遗漏

2026-11-11。此处是固定工件的路径集合审计，不是InMap运行，更不是论文复现结果。

## 实际计算

[完整Java目录核查](2026-11-11-inmap-data-readiness.md)取得843个Java文件路径；旧配置含843个唯一oracle实体，两集合交集只有840，双方各有3项差集。

本轮按已读IRAnalysis.filterClasses的非空前缀规则对路径推导名称做过滤，843个中只有`osx.macadapter.MacAdapter`被排除，剩余842个。它们与oracle的交集仍为840。未获标签覆盖的两个路径名称为：

- `net.sf.jabref.gui.plaintextimport.BasicAction`
- `net.sf.jabref.gui.plaintextimport.PopupListener`

oracle中另有EntryBasedFetcher、IdFetcher、WebFetcher三个名称没有同名Java文件路径。未读取文件定义来验证这些名称是否可由其他文件、模板或内部类产生，因此不称这些类不存在。

## 可以推出什么

如果实际索引与过滤输出恰好是这842个路径名称、原任务使用此未修改oracle、且没有其他名称变换，那么按已读AutoMap的类名精确匹配接受逻辑，最多840个实体能获得接受，标签覆盖上界为840/842≈0.997625。

论文报告842类中除2个之外得到正确映射，并以两位小数显示recall=1.00。数值一致是一条值得验证的线索，**尚不能断言论文那两个未映射对象就是上述两个，也不能宣布作者算法不存在检索遗漏**。本文候选快照还没有被确认是论文实际输入；必须拿到逐轮推荐、索引名称和未映射清单才能归因。

相反，也不能先把最后两个未映射对象解释成文本相似度不足，再针对它们调参。如果对象根本没有oracle标签，即使推荐到合理模块也会被固定oracle拒绝；那是评测输入限制，与算法召回不足不同。

## 对本研究评价设计的影响

之后的原方法验证必须同时保存四个集合：源对象、有效索引对象、oracle覆盖对象、最终接受对象。分别报告预处理损失、标签覆盖缺口与有标签对象上的漏检。保持原作者指标用于复现，另行给出覆盖诊断；不要静默删除未标注对象使分数更好，也不要修改oracle让结果拟合论文。

这是一项评价有效性诊断，不是当前提出的新算法或已确认创新点。

## 可复跑证据

`scripts/audit_inmap_population.py`生成`research/evidence/runs/2026-11-11-inmap-population-01/report.json`，保存输入SHA256、过滤规则命中、两个差集、条件上界和明确前提。源码及输入来自[版本核查](2026-11-11-inmap-version-comparison.md)与[配置审计](2026-11-11-inmap-config-audit.md)。

```sh
python3 scripts/audit_inmap_population.py --output research/evidence/runs/inmap-population-new-run
```

下一步原任务运行应先导出实际索引类名单并验证这些前提，再计算指标；不把本轮静态集合结果记为实际recall。
