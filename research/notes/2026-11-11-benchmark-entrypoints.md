# 分阶段基准入口：任务与工件边界

2026-11-11。仅核对作者/官方仓库 README 与 MiniCode 作者论文；**工件入口可读不等于下载完整、环境可运行或已完成评测**。本轮未安装、训练、运行检测/测试，也不制定主线程的分阶段评估政策。除特别标注外，仓库链接为浮动分支，执行前仍须固定版本和数据摘要。

| 基准与一手入口 | 原任务、语言/领域 | 本轮确认的工件状态 | 与 Rust 优化真值的距离（本轮判断） |
| --- | --- | --- | --- |
| [BigCloneBench](https://github.com/clonebench/BigCloneBench)、[BigCloneEval ReadMe](https://github.com/jeffsvajlenko/BigCloneEval/blob/master/ReadMe.md) | IJaDataset Java 项目的已知克隆基准；BigCloneEval 是评估框架而非检测器，导入检测器的源码区间配对后测 recall，可按克隆类别、功能、跨/内项目及相似区间汇总。 | 两份 README 成功读取。BCB 推荐随 BCE 分发的 V2，标旧 ERA 过时；BCE Installation Steps 2/3 提供数据库和 reduced IJaDataset 的 OneDrive 链接，另有VM入口。BCB 提示大文件可能要求登录；本轮未访问数据下载目标、核验哈希或安装。 | 可用于对应 Java 协议下的克隆召回，不能把未命中标注集的结果全当假阳性，更不能据此算 Rust 重构 precision。已知克隆关系不表示应合并、替换安全或性能收益。 |
| [CodeSearchNet 官方 README](https://github.com/github/CodeSearchNet/blob/master/README.md) | 自然语言 query→函数/方法代码检索；训练资源是注释/code 对，语言为 Python、JavaScript、Ruby、Go、Java、PHP，未列 Rust。Evaluation 使用 NDCG；99个查询的人工检索相关性标注与训练对不同。 | README 可读，指向 `resources/queries.csv`、`resources/annotationStore.csv`、`src/relevanceeval.py`，数据经 S3/setup 获取。challenge 已结束，不再接受提交；官方仍提供数据/人工评价入口。未下载完整语料、逐行审计标签或验证旧环境。 | 衡量检索相关性，不是两个实现的功能等价、文档一致性或优化可行性。不能将天然 comment/code 配对当人工重复标签，也不能将未标注项直接视为不相关。 |
| [MiniCode 作者仓库固定 README](https://github.com/code-refactor/minicode/blob/3cc71a908f16c78e634010523b264671c3546fc2/README.md)、[作者论文 v3 §4](https://arxiv.org/html/2506.11058v3#S4) | 输入相关源文件，输出共享库及改写调用方的开放式库设计/重构任务；论文包含 CodeContests 竞赛程序、Python Transformers/Diffusers 机器学习库，以及沿用的 Logo/Date 小程序任务，不是 Rust 内核基准。 | 本轮重读固定提交 `3cc71a908f16c78e634010523b264671c3546fc2` 的 README：提供 `minicode.setup_codecontests`、`setup_repos`、`setup_large_repos` 及 agent/汇总入口，要求模型 API keys。这是本地生成 splits/运行的入口，不证明所有论文任务与当前脚本完全对应；数据依赖下载、权限、费用、全套测试尚未核验。 | 可评价所给测试约束下的重构与库设计代理指标，不是生产候选发现标签。测试保留不证明全行为等价，MDL/压缩不证明运行速度、锁约束或维护收益。 |

**版本/来源提醒：**MiniCode 固定提交从 book 既有 `research/notes/2026-11-05-librarian-reproduction-readiness.md` 定位，本轮实际在线读取该 README；不是本轮确认的最新 HEAD。MiniCode 与 Librarian 方法实现不可混称；论文§§3/6的测试约束与 MDL 指标也不可统一称为“优化正确率”。BigCloneBench 的完整/精简数据、ERA/V2 与检测单位匹配参数应分别登记，不因共享名称而混用。

**本轮读取记录：**直接打开以上官方入口及其 raw README；BigCloneEval 的 `README.md` 返回404，目录显示实际文件为 `ReadMe.md`，更正后成功读取，因此不是仓库不可用。CodeSearchNet 定向读取 Data/Evaluation/Annotations；MiniCode 读取 setup/baseline 段与作者论文任务定义。未扩展搜第三方排行榜、未声称本轮任何基准已复现，未修改其他文件。
