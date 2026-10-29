# AI Review 流程全景

审查可以针对 PR 变更，也可以针对固定版本的整个仓库。两者都需要明确要求、收集证据和核验结论；
PR 额外强调变更归因与 diff 定位，全仓扫描则需要自行确定候选范围。

## 流程地图

<div class="knowledge-flow">
<a href="flow/inputs.html"><b>1 · 输入与任务边界</b><small>版本、需求、规则、代码范围与配置</small></a>
<span aria-hidden="true">↓</span>
<a href="flow/routing.html"><b>2 · 拆解与方向分配</b><small>行为变化、相关文件、审查任务</small></a>
<span aria-hidden="true">↓</span>
<a href="flow/analysis.html"><b>3 · 检索与语义分析</b><small>调用方、契约、候选问题与证据</small></a>
<span aria-hidden="true">↓</span>
<a href="flow/findings.html"><b>4 · 核验与输出</b><small>触发条件、验证结果、可核查意见</small></a>
<span aria-hidden="true">↓</span>
<a href="flow/evaluation.html"><b>5 · 反馈与评价</b><small>修复、复核、误报、遗漏与成本</small></a>
<span aria-hidden="true">↓</span>
<a href="flow/learning.html"><b>6 · 知识沉淀</b><small>文档、测试、AI 规则与工具检查</small></a>
</div>

**回路：**知识沉淀更新输入规则与方向分配；核验缺少证据时返回检索；作者回复或新提交触发重新核验；发现契约不清时返回需求确认。
图示是本书的分析框架，不是要求所有平台采用同一种串行执行器。

评价目标、单位与预算应在任务开始时确定，第五环节集中处理反馈和结果，不是等审查结束才选择衡量标准。

## 审查方向是另一条轴

| 方向 | 输入重点 | 分析重点 | 验证与评价重点 |
| --- | --- | --- | --- |
| 功能与正确性 | 需求、状态、调用方 | 控制流、边界、错误与清理 | 触发条件、行为和回归 |
| 安全与并发 | 信任边界、生命周期、执行上下文 | 不变量、访问关系、同步 | 可达性、约束及残余风险 |
| Linux/POSIX 兼容性 | 兼容范围、规范、参考实现 | 返回值、errno、ABI、副作用 | 用户可观察语义差异 |
| 性能与资源 | 负载、规模、平台 | 频率、复杂度、竞争和占用 | 测量方法、预算和收益 |
| 文档 | 文档、实现、配置、示例 | 契约与实现一致性 | 对应行为和使用方式 |
| 复用与可维护性 | 已有实现、职责、依赖 | 功能重叠、抽象与迁移成本 | 行为保持、整体复杂度与性能 |

方向之间可以共享上下文，但判断标准不同。同一修改也可能跨多个方向。
X-Kernel 文档把 Bug、POSIX 等称为“阶段”；这里将其放在方向轴上，避免与书中的流程环节混淆。

## 各环节中的知识与研究

| 环节 | 理论与概念 | 已有阅读材料 | X-Kernel 对照 |
| --- | --- | --- | --- |
| 输入与边界 | 契约、需求、版本一致性 | Google 上下文指南、Bugbot 规则作用域 | 源分支规则、PR 元信息、POSIX 与显式文档审查 |
| 拆解与分配 | 相关性筛选、依赖和范围 | Google 分工实践、Bugbot 路径规则 | 变更分类、CG paths/triggers |
| 检索与分析 | 不变量、程序语义、抽象取舍 | Librarian、REM/REM2 | 调用链、资源生命周期、复用搜索 |
| 核验与输出 | 证据、反例、严重程度 | Google 评论指南、重构验证方法 | diff 定位、结构化意见、低置信政策 |
| 反馈与评价 | 参照标签、Precision/Recall、偏好 | Themis、CodeTaste、Librarian 人类评价 | 轮次与 head 跟踪；没有已验证的整体效果数据 |
| 知识沉淀 | 概括、规则作用域、工具覆盖 | Bugbot Learned Rules、Auto-SCAT | CG 注册、lint 分工、例外与候选 |

这张表提供知识归属，不表示所有文献已经完成同等深度的阅读。
[研究与论文索引](papers/index.md)保留具体材料入口，[工程依据](research/notes/2026-10-29-review-framework-evidence.md)区分规范、实现与未验证效果。
