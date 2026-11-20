# HanLP SRL 调用与解释边界（静态核查）

读取日期：2026-11-13。核查官方仓库固定提交 `959a6966f6e7e26d2e89c4112ca9bafbe32eb743` 的 Python 源码，并选择性解析已取得的模型配置。本笔记记录静态接口证据，不确认标签词表或权重运行兼容性；独立的模块导入实测见[运行预检](2026-11-13-hanlp-runtime-preflight.md)。

## 调用与依赖闭包

- **两种参数均成立**：已加载多任务组件可写 `component(text, tasks='srl')` 或 `component(text, tasks=['srl'])`；这是静态接口示意，不是已执行记录。[Component.__call__，25–36行](https://github.com/hankcs/HanLP/blob/959a6966f6e7e26d2e89c4112ca9bafbe32eb743/hanlp/common/component.py#L25)转发至 `predict`；[多任务 predict，459–499行](https://github.com/hankcs/HanLP/blob/959a6966f6e7e26d2e89c4112ca9bafbe32eb743/hanlp/components/mtl/multi_task_learning.py#L459)接受字符串或字符串列表任务选择器，返回 `Document`。原始句子/句子列表是否可直接输入，取决于首任务；不可把单任务 SRL 的预分词输入约定直接套到所有多任务配置。
- [resolve_tasks，570–615行](https://github.com/hankcs/HanLP/blob/959a6966f6e7e26d2e89c4112ca9bafbe32eb743/hanlp/components/mtl/multi_task_learning.py#L570)：先精确匹配任务名，否则处理 `*` 前缀或普通前缀匹配，再加入依赖并按拓扑层排序。因此 `tasks='srl'` **不等于只运行一个 decoder**，也不保证返回仅有 SRL 字段。`skip_tasks` 在闭包之后做减法，不重新证明依赖完整；不要为省算力盲目跳过分词。`resolved_tasks` 可覆盖解析结果，初次探针不宜手工指定。
- 实际图由各任务配置的 `dependencies` 构造，而非写死“SRL 必须先 POS/DEP”：见 [on_config_ready，650–666行](https://github.com/hankcs/HanLP/blob/959a6966f6e7e26d2e89c4112ca9bafbe32eb743/hanlp/components/mtl/multi_task_learning.py#L650)。首任务为 tokenizer 时另有 token 层隐藏表示转换（同文件519–547行）。本轮取得的实际配置已确认SRL键为`srl`、类型为ranking、直接依赖`tok`；尚未通过完整模型加载验证。

## 原始输出契约

- ranking 多任务适配器明确使用 `exclusive_offset=True, with_predicate=True, label_first=True`，默认用空格连接 argument tokens：[rank_srl.py，116–121行](https://github.com/hankcs/HanLP/blob/959a6966f6e7e26d2e89c4112ca9bafbe32eb743/hanlp/components/mtl/tasks/srl/rank_srl.py#L116)。[底层格式化，291–311行](https://github.com/hankcs/HanLP/blob/959a6966f6e7e26d2e89c4112ca9bafbe32eb743/hanlp/components/srl/span_rank/span_rank.py#L291)按谓词组织 frame，并插入 `PRED`。默认形状为每句 `list[frame]`，每个 frame 是 `(text, label, start, end)` 元组列表；`[start,end)` 是**token 索引**，不是字符、Unicode 列或字节范围。非默认 `with_argument` 可改变文本字段形态，须保留配置。
- BIO 多任务类委托另一实现：[bio_srl.py，125–126行](https://github.com/hankcs/HanLP/blob/959a6966f6e7e26d2e89c4112ca9bafbe32eb743/hanlp/components/mtl/tasks/srl/bio_srl.py#L125)；[span_bio.py，374–384行](https://github.com/hankcs/HanLP/blob/959a6966f6e7e26d2e89c4112ca9bafbe32eb743/hanlp/components/srl/span_bio/span_bio.py#L374)同样生成文本/标签/token区间并插入谓词，但仅对非空 arguments 生成 frame。因此无 frame 不能证明句子没有语义角色。多任务返回还按输入形态去除句子外层、并在缺分词字段时补 `tok`：[548–568行](https://github.com/hankcs/HanLP/blob/959a6966f6e7e26d2e89c4112ca9bafbe32eb743/hanlp/components/mtl/multi_task_learning.py#L548)。

## 对合同字段能支持什么

**本研究解释限制，而非 HanLP 保证**：上述接口输出谓词相关的预测标签与 span；未提供通用 `actor/object/condition/norm/report/actual` 字段。不能仅凭 `ARG0/ARG1` 名称固定映射执行者/对象，也不能把某个附加语或情态词识别升级为 only-if 的蕴涵方向、规范履行、报告为真或实际执行的证明。跨 frame 的角色绑定、否定/模态作用域及文档报告与运行事实的分离，需要另行冻结规则和验证；此轮源码核查不证明这些能力存在或不存在于模型表示中。

建议最小下一步仅记录实际配置/任务闭包、输入分词、完整原始 SRL 帧与空输出；合同字段保持未知，不为已见用例补手工解释规则。模型预测和后续研究者映射分栏保存，均不作独立真值。固定源码阅读已完成，具体权重输出与合同适用性未验证。

补充配置证据：本轮实际选择性解析 `research/evidence/originals/2026-11-13-hanlp-resource-probe-01/metadata-00.json`，确认 `hanlp_version=2.1.0-beta.37`、`srl.classpath=hanlp.components.mtl.tasks.srl.rank_srl.SpanRankingSemanticRoleLabeling`、`srl.dependencies='tok'`、`srl.use_gold_predicates=false`、`encoder.transformer='mMiniLMv2L6-no-space'`。这补足上文对具体 SRL 类型与直接依赖的未知：该配置选择 ranking 并声明依赖 tok，不使用金标准谓词；不等于已运行解析完整闭包。配置声明版本与本轮固定源码版本须分别记录，不能将静态源码审计当作旧模型在新安装环境的兼容性证明。HTTP range 字节数和安装状态沿用主线程报告，本旁路没有重新测量。
