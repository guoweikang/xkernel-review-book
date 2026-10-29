# AI 代码审查：原理、方法与评价

AI Review 从一组代码和要求出发，形成可核查的意见，再通过修复、反馈与评价改进后续检查。
这个过程既涉及程序理解，也涉及输入选择、工具分工和知识维护。

## 基础前置知识

[基础术语与概念](basics/terms.md)介绍 PR、diff、契约、上下文、lint、finding 与评价指标。
[审查职责与工具分工](basics/roles.md)区分代码、意见和审查系统三个评价对象。

## 流程全景

[知识地图](map.md)将审查分成六个相互连接的环节：

1. [输入与任务边界](flow/inputs.md)：固定版本、需求、规则及不同审查方向需要的材料。
2. [审查对象拆解与方向分配](flow/routing.md)：处理 diff 或存量对象，关联文件，分配审查任务。
3. [上下文检索与语义分析](flow/analysis.md)：搜索调用关系和契约，形成有证据的候选判断。
4. [核验、筛选与意见输出](flow/findings.md)：检查触发条件、工具结果和报告范围。
5. [反馈处理与质量评价](flow/evaluation.md)：区分处理状态、技术正确性与整体审查表现。
6. [知识沉淀与规则演进](flow/learning.md)：将经过核验的经验转成文档、测试或工具规则。

## 工程与研究

[公共抽象](topics/abstraction.md)位于语义分析环节；[Themis 与评价研究](flow/evaluation.md)位于反馈和质量评价环节；
[Bugbot、Auto-SCAT](topics/review-rule-automation.md)位于知识沉淀环节。
各环节对照第三方方法和 X-Kernel 的工程约定，分别说明已有依据与效果边界。

[阅读路线](learning-path.md) · [参考资料](references.md) · [研究档案](archive.md)

---

编写中。X-Kernel 实践的版本和核查范围见[工程依据](research/notes/2026-10-29-review-framework-evidence.md)。
