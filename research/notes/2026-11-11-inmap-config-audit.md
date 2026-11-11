# InMap单配置准备与oracle计数核查

2026-11-11。原任务执行前，使用独立严格配置读取器审计已归档2020候选配置；没有执行Java Evaluator或InMap，不能把此计数称为作者实际运行分母。

## 实际计数

候选配置的ProgramMapping包含843条、843个唯一实体，分布为model97、logic382、pref11、gui ui344、cli8、global1。没有重复实体或未知模块名。PackageExclusion有187条，其中同一bibtexml.package-info条目重复一次；未修改原件。

精确名称排除交集为空。进一步按已读IRAnalysis.filterClasses的规则（取第一个星号之前的非空前缀，再用startsWith；没有星号时仍按前缀）检查，oracle与排除规则的交集也为空。这只是对oracle名称的有限定义检查，不验证实际预处理产物与过滤行为。

论文表2使用842类；当前配置有843个oracle实体。必须继续核对实际源文件、预处理输出、索引文档与过滤后类集合，不能把843直接当评价分母，也不能为了对齐论文删掉一条标签。表1的843源文件与此处843标签数量一致并不足以证明集合相同。

## 冻结运行预算

按配置十进制范围和三种模式数组大小计算，原配置有4×11×2=88组参数组合；其余维度各一个值。这是静态组合数，不是已经执行88次，也不验证Java浮点循环的全部边界行为。

为首次有界冒烟固定PS=50、MNBF=33、MDBF=1，均在论文报告范围内。生成`config-single.txt`和完整diff，只收缩这三维的Min/Max范围，保留模式、映射、描述、排除及其他参数。独立读取器确认只剩一组配置，标签集合保持不变。**该配置还不是可直接运行交付**：源码路径、大小写入口、依赖和实际数据仍需核验。

选择这组参数是为了先运行论文范围内一个固定设置，而非调参追求分数；首次输出出来后不能因不好看而换参数冒充同一试验。

## 工具与留存

`scripts/audit_inmap_config.py`拒绝重复设置、未闭合数组和不支持语法，而非默默跳过。已运行一个正例与四个拒绝控制；这是独立读取器的局部检查，不是与原Java解析器的等价性证明。

- `research/evidence/runs/2026-11-11-inmap-config-audit-01/`保留第一次统计。
- `research/evidence/runs/2026-11-11-inmap-config-audit-02/`补充原实现前缀排除规则检查。
- 每轮保留原配置、衍生单配置、diff、读取器源码和报告，原件及衍生件摘要写入报告。不覆盖前次证据。

```sh
python3 scripts/audit_inmap_config.py --output research/evidence/runs/inmap-config-new-run
python3 scripts/check_inmap_config.py research/evidence/runs/2026-11-11-inmap-config-audit-02
```

原件来源与版本对照见[候选版本核查](2026-11-11-inmap-version-comparison.md)，评分组件行为见[Lucene控制](2026-11-11-lucene-scoring-runtime.md)。下一项是将oracle名称与真实Java源文件、预处理文档的集合对齐，再开始固定参数原任务；当前没有新的算法准确率结论。
