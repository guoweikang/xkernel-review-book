# 流程框架的 X-Kernel 工程依据与边界

核查日期：2026-10-29。本地仓库 `/root/codes/x-kernel`，HEAD 为
`5157a33207cf55281e89203320892c7482786e0d`；相关 review/CG 路径未见工作区修改。
本次没有 fetch、运行 review、修改内核规则或检查 xreview 服务端代码。

## 六环节与项目文件

下列路径相对于该 X-Kernel 仓库；本书未复制工程文件。行号是本次读取的定位，不作为线上服务行为证明。

| 环节 | 文件与位置 | 实际核对的内容 | 证据等级 |
| --- | --- | --- | --- |
| 输入 | `docs/ai/review/README.md:9` | 源分支读取阶段规则、不可读时停止 | 仓库规范 |
| 输入 | `docs/ai/review/description.md:21` | PR 元信息、diff 与描述对照，缺 body 的变体 | 仓库规范，不保证每个 agent 都得到需求 |
| 输入 | `docs/ai/review/posix.md:1` | 适用接口、man page/规范/Linux 源码优先级与查证流程 | 仓库规范；未运行 fetch_man_page |
| 输入 | `docs/ai/review/module-docs/README.md:1` | 显式 docreview、固定 HEAD TSV、规则变化导致缓存失效的约定 | 工程文档；未审计执行器或缓存 |
| 分配 | `docs/ai/review/common.md:32`、`guidelines.md:28`、`logic.md:10` | 变更分类与规范主题选择 | 仓库规范 |
| 分配 | `docs/code-guidelines/README.md:7`、`docs/ai/review/guidelines.md:22` | paths/checks/triggers、AI 与 lint 后端分工 | 元数据与规则存在；服务端筛选未核实 |
| 分析 | `docs/ai/review/bug.md:25`、`logic.md:26`、`performance.md:1` | 路径、状态、资源与性能依据 | 仓库规范 |
| 核验输出 | `docs/ai/review/common.md:24`、`:67`、`:127` | 标注 diff、查证、结构化 finding、低置信项 | 存在下述文本冲突 |
| 反馈 | `docs/ai/skills/pr-ci-review/SKILL.md:192` | review 轮次、意见 ID、head 状态及反馈读取 | skill 文档；未访问历史数据 |
| 沉淀 | `docs/code-guidelines/README.md:1`、`lints.md:55`、`pending.md:1` | CG 注册、full/partial、例外与迁移候选 | 文档与注册文件 |
| 工具实现 | `tools/lints/src/lib.rs:1`、`tools/lints/src/unregistered_static_spinlock.rs:1`、`xtask/xkmake/src/dylint.rs:1` | 已注册 lint、检查范围、构建配置与 driver 调用 | 源码已静态核对，未实跑 |

以上没有一项可单独证明漏报、误报或 token 的改善幅度。
相应的论文效果与平台自报指标也不替代 X-Kernel 的实际测量。

## 本轮发现的规则张力

### 低置信问题是否报告

`common.md:71` 要求依赖未证明假设的问题不报告；`:85` 要求可疑点不得静默丢弃，
未核实内容标低置信输出；`:127` 之后的格式约定又明确低置信项不阻塞。
这些要求没有在所读文本中形成无歧义的统一条件。书中保留为未解决的工程问题，不替项目决定优先级。

### 完整文件与按符号裁剪

`common.md:45` 要求相关完整文件，`:73` 后的效率约束将完整上下文解释为目标函数及直接调用链，
并禁止整文件倾倒；`guidelines.md:66` 又要求 Rust 文件完整读取。
“避免无关大文件”和“不得漏读依赖语义”都合理，但具体调度策略不能由上述文本直接推定。

### 输入范围不等于每阶段实际接收

Description 有 PR 元信息读取要求，不自动证明 Bug/Logic 的每次输入都包含同样需求材料。
书中提出的共享任务输入表是教学设计；不能冒充已落地的统一服务端数据结构。

### 文档一致性与完整文档审计

Guidelines 有代码/文档同步要求；module-docs 的完整审计是显式入口。
因此“文档变化值得对照代码”不等于“普通 PR 自动运行全部 DD/SD/RD 检查”。

## 书稿结构决策

用户要求先基础术语，再流程大地图，再在每个环节中展开原理、第三方研究、项目实践、原因与收获。
六环节是书稿分析框架，不是修改研究六阶段，也不是改造 xreview 执行器。
性能、兼容性等是方向轴；新六环节是流程轴。已有论文按相关问题归位，而非另建孤立论文课程。

章节里的设计收益是对规范作用的分析，明确区别于实测效果。尚无数据的结果不补写成经验。
本轮未新增论文研究、未采集案例，仍属基础调研与知识组织。
