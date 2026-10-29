# X-Kernel 重复功能识别、公共抽象与优化建议研究

本目录是本研究的统一入口。最后整理：2026-10-28。

> 维护位置更新：本目录已迁移至独立 `ai-review-book` 仓库。旧笔记中的工作树与分支
> 信息属于历史记录；当前从仓库根目录 `chapters/` 阅读课程，从本目录维护研究证据。
> 初次迁移来源与校验清单见仓库根目录 `MIGRATION.md` 和 `migration-manifest.json`。

## 研究目标与边界

用户提出：为 X-Kernel 的 crate、mod、结构体建立职责语义元数据索引，结合代码重复
检测，检查已合入的存量仓库，也支持 PR diff 增量分析。研究既包括直接复用已有能力，
也包括从多份实现中提取公共模块、以 Rust 类型/泛型等保留定制部分，并给出合理优化建议。
AI review 是应用入口之一，不是系统的范围边界；公共抽象不要求仓库里已有可复用模块。
研究还需形成可追溯的论文和专利素材。当前先讨论方案，不进入系统开发。
后续真实评测覆盖 X-Kernel、ArceOS、Starry、星绽等候选 Rust OS；受控构造与真实工程
实验分开设计。当前只执行基础调研，暂停案例扩充和验证，保留原六阶段顺序。

语义索引、克隆检测、契约可行性、评价系统是同一研究主线。xerj 等工具只作为
实现候选和对照对象；其评估不替代主线，也不代表已经选型。

## 恢复工作时的阅读顺序

学习入口：[AI Review 知识图谱 v0.1](KNOWLEDGE-MAP.md)，汇总共同讨论、关键关系与待补知识。

1. 阅读 [PROGRESS.md](PROGRESS.md)：当前阶段、用户要求、未决问题、下一步。
   科研目标、阶段产物、研究假设及实验门槛以 [RESEARCH-PLAN.md](RESEARCH-PLAN.md) 为当前规划提案。
2. 阅读 [范围修正与研究问题](notes/2026-10-27-scope-and-abstraction.md)，再读
   [初步研究与设计](notes/2026-10-27-initial-research.md)：任务定义、metadata、
   检索/判定分工、标签、评价和可能贡献。这里的设计仍是提案，不是已批准规格。
3. 根据子任务查 [SOURCES.md](SOURCES.md) 和专题笔记，不从零重做已有搜索。
4. 基础调研已形成 [最近邻技术矩阵](notes/2026-10-27-nearest-method-matrix.md)。
   [早期案例笔记](notes/2026-10-27-pilot-candidates-01.md) 仅为历史探索记录，不是正式试点或已确认问题。
5. 当前补充成果：[基础调研第二批](notes/2026-10-27-foundations-02.md) 与
   [公共抽象专利技术对照](prior-art/2026-10-27-abstraction-claims.md)。
6. 最新：[Librarian 共同阅读及候选登记](notes/2026-10-27-librarian-reading-01.md)、
   [历史偏好定向查新](notes/2026-10-28-historical-preference-prior-work.md)。
   后者已找到合入提交偏好与历史重构评价的直接先例，下一篇建议读 Themis。
7. 用户同意扩大学习视野至 AI review 全流程，教学地图见研究计划的
   “学习范围补充（2026-10-28，用户授权）”；不改变六阶段或自动扩大实现范围。
8. 已开始 [Themis 共同精读](notes/2026-10-28-themis-reading-01.md)，先读 §3 的标签来源。

## 材料布局

```text
reuse-review/
├── README.md                       统一入口、研究边界与维护方式
├── PROGRESS.md                     当前状态、待决问题、工作日志
├── RESEARCH-PLAN.md                科研路线、假设、实验与阶段门槛
├── SOURCES.md                      论文、专利、工具的来源及检索台账
├── notes/
│   ├── 2026-10-27-initial-research.md
│   ├── 2026-10-27-scope-and-abstraction.md
│   ├── 2026-10-27-abstraction-prior-work.md
│   ├── 2026-10-27-nearest-method-matrix.md
│   ├── 2026-10-27-pilot-candidates-01.md
│   └── 2026-10-27-foundations-02.md
├── prior-art/
│   ├── 2026-10-27-patents.md        首批五组专利的权项及出版记录比较
│   └── 2026-10-27-abstraction-claims.md
├── tools/xerj/
│   ├── 2026-10-27-assessment.md
│   └── 2026-10-27-incremental.md
└── evidence/
    ├── README.md                   原始资料与证据强度说明
    ├── manifest.json               下载结果、来源、时间、SHA-256
    └── originals/                  论文/专利/固定版本源码的本地副本
```

## 每次子任务如何归档

- 开始前在 PROGRESS 中明确它服务哪个未决问题；没有改变研究目标的小任务继续归入本目录。
- 新来源登记稳定编号、URL、版本/公开日期、阅读深度和局限。检索线索与已经核对的证据分开。
- 调研写入日期化专题笔记，引用来源台账和证据；不要把临时结论散放到通用 reports。
- 完成后更新 PROGRESS 的工作日志、结论状态及下一步。用户未确认的建议仍标为提案。
- 后续实验在本目录增加 experiments/<日期-主题>/，保存输入快照、配置、命令、原始结果和解释。
  当前尚无实验，不预造结果。评估指标、标注协议和选型结论成熟后再单独成文。
- 事实、推断、用户决定、研究假设分别标明；新结论更正旧笔记时留下日期和理由。
- 不把研究笔记自动混入 CG 规则 PR。当前材料尚未提交/推送；只有明确发布操作后才更新此状态。

## 既有材料迁移

2026-10-27 将此前 `docs/ai/reports/` 下四份研究文档迁入本目录，并更新内部引用。
论文与设计讨论、专利权项分析、xerj 总体评估和增量核对均保留；原目录中无关的
`process-docs-audit.md` 未移动。研究来源代码基线及 xerj commit 仍见各原始笔记。
