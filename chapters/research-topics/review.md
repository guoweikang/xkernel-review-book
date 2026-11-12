# AI Review规则学习与流程

## 与核心研究的关系

这条线研究意见如何成为可复用规则或确定性检查，以及如何评价自动化覆盖。它可以承载重复功能与职责候选的审阅，但不是相似度检测本身，也不要求所有工具只能在PR增量流程运行。

## 参考与已有分析

[Bugbot Learned Rules](../research/notes/2026-10-29-bugbot-learned-rules-analysis.md)与[Auto-SCAT](../research/notes/2026-10-29-auto-scat-analysis.md)的材料输入、学习方式和规则作用范围不同；对照见[规则自动化比较](../research/notes/2026-10-29-rule-automation-comparison.md)。

这些是资料分析，不代表已经在xkernel复现平台效果。把历史意见转成lint或脚本，还需要正反例、适用前提和覆盖边界；检查存在不意味着Agent可以对整个审查维度免审。

## 后续接口

重复候选工具应输出对象、证据、范围、失败与未知状态；Review负责基于上下文提出意见。全仓扫描和增量审查共享证据协议，但候选预算、历史上下文与评价分母分别记录。
