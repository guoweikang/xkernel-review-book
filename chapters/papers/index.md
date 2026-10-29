# 按流程查找研究与论文

| 流程环节 | 材料 | 用来理解什么 |
| --- | --- | --- |
| 输入与方向分配 | [Google 检查指南](https://google.github.io/eng-practices/review/reviewer/looking-for.html)、[Bugbot 文档](https://cursor.com/docs/bugbot) | 上下文、分工和规则作用域；均非论文效果证据 |
| 分析与方案生成 | Librarian、REM、REM2 | 公共抽象、Rust 重构约束与验证 |
| 核验与质量评价 | Librarian、Themis、CodeTaste、CodeFavor | 评价对象、偏好标签与指标有效性 |
| 知识沉淀 | Auto-SCAT、Bugbot Learned Rules | 历史意见到工具配置或 AI 规则 |

一项研究可能跨多个环节；以下提供原文入口，阅读范围和限制保留在对应笔记中。

以下论文分别涉及公共抽象、代码质量评价与 Rust 重构。阅读时可比较研究问题、方法、评价依据和适用边界。

| 材料 | 阅读问题 |
| --- | --- |
| [Auto-SCAT 作者版 PDF](https://mdipenta.github.io/files/Auto_SCAT_EMSE.pdf) | 怎样用历史评审评论选择已有静态检查项？ |
| [Librarian PDF v3](https://arxiv.org/pdf/2506.11058v3) | 怎样生成公共抽象并评价重构质量？ |
| [Themis PDF v1](https://arxiv.org/pdf/2605.00754v1) | 已合入提交如何变成条件性质量标签？ |
| [CodeTaste v1](https://arxiv.org/html/2603.04177v1) | 历史重构选择与开放式设计评价有什么关系？ |
| [CodeFavor v2](https://arxiv.org/abs/2410.03837v2) | 如何利用代码演化构建多维偏好？ |
| [REM](https://verse-lab.org/papers/rem-oopsla23.pdf) | 生命周期与所有权怎样约束 Rust 代码抽取？ |
| [REM2](https://arxiv.org/html/2601.19207v1) | Rust 重构如何进行受限等价验证？ |

## 重构评价与质量标签

Librarian 连接“生成重构方案”和“选择方案”；Themis 连接“质量偏好数据”和“评价评分模型”。
二者都不应被直接等同于完整 PR 合入决策系统。

详细阅读记录：[Librarian](../research/notes/2026-10-27-librarian-reading-01.md)、
[Themis](../research/notes/2026-10-28-themis-reading-01.md)。其他材料的版本与核查范围见[来源台账](../research/SOURCES.md)。

## 工业实践：规则学习

[Bugbot Learned Rules](https://cursor.com/blog/bugbot-learning) 是产品机制介绍，不是学术论文。
与 Auto-SCAT 的区别及工具覆盖问题见[从评审意见到自动化规则](../topics/review-rule-automation.md)。
