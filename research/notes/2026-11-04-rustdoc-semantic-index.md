# rustdoc JSON 能否用于语义数据库：小型官方核查

日期：2026-11-04。结论：**可以作为 API 结构与文档语义索引的输入，但不是运行行为数据库或重复功能判定器。**本次仅实际阅读下列三个官方网页，没有生成 JSON、运行编译或改动代码。

## 官方 schema：已确认到哪一层

| 对象 | 已核实内容 | 边界 |
| --- | --- | --- |
| `Crate` | 官方把它定义为 `--output-format json` 输出的根对象；同时提供 `FORMAT_VERSION` | 本次未展开 Crate 字段页，未逐字段核验完整结构，不提供猜测性的完整 schema |
| `Function` | 官方定义为函数声明，包含方法及其他关联函数；另有 `FunctionSignature`、`FunctionHeader`、`Generics` 类型 | 未展开 Function 字段页，未核实具体字段组合；不能把“函数声明”解释成已有函数体、调用图或数据流 |
| `Item` | 通用字段包括 `id`、`crate_id`、可选 `name`/`span`/`docs`、`visibility`、`links`、`attrs`、`deprecation`、`stability`、`const_stability`、`inner`；类型专属信息在 `inner: ItemEnum` | `docs` 是 Markdown 文档文本；`links` 解析文档内链接，**不是调用边**；`span` 可缺失，不能保证每条记录都能直接回链源码 |

来源：[官方 rustdoc_json_types 概览：根对象、类型与 FORMAT_VERSION](https://doc.rust-lang.org/nightly/nightly-rustc/rustdoc_json_types/index.html)、[官方 Item：声明与 Fields](https://doc.rust-lang.org/nightly/nightly-rustc/rustdoc_json_types/struct.Item.html)。Item 页还说明，默认文档项为公开项，可要求输出私有项；不能把默认导出当作内核全量符号库。

这次返回的概览页标注 `1.101.0-nightly (32dba69d6 2026-10-09)`，Item 页标注 `1.101.0-nightly (708c94ef0 2026-11-03)`，**不是同一编译器快照的完整 schema 审计**。接入时应固定工具链并核对对应格式版本，不能直接拿滚动 nightly 页面作为永久数据库契约。跨构建 ID 稳定性、完整 Crate/Function 字段及 JSON 命令稳定性本次未验证。

## cfg(doc)：文档视图不等于实际构建视图

官方说明：rustdoc 同样受条件编译过滤，只能看到 host 或指定 `--target` 对应的内容。它在生成文档时设置 `cfg(doc)`，因此 `#[cfg(any(windows, doc))]` 可以让非 Windows 文档也出现该项；这个 cfg 不传给 doctest。rustdoc 不会自动模拟所有平台分别编译，而且不运行所有编译器 pass，部分无效代码可能不报错。[The rustdoc book：cfg(doc) 与 Interactions between platform-specific docs](https://doc.rust-lang.org/rustdoc/advanced-features.html#cfgdoc-documenting-platform-specific-or-feature-specific-information)

由此推论：生成文档成功不证明对应生产配置能编译；文档包含某 API 不证明当前内核运行配置包含它；文档没出现某项也不证明源码中不存在它。多配置覆盖需要显式组织，不能靠 `cfg(doc)` 自动获得全平台一致的事实集合。

## 入库时分开三类证据（设计建议，非已实现效果）

1. **文档声明**：作者写的用途、约束、复杂度、安全要求，保留原文和来源；即使由 rustdoc 输出，也不是编译器验证过的行为保证。
2. **编译器/工具结构事实**：本次 rustdoc 文档视图中的声明、类型关系、可见性、源码位置及文档链接解析结果；绑定 commit、工具链、target、features/cfg、导出选项与格式版本。它们不是实际执行事实。
3. **AI 推断**：功能摘要、相似候选、可能重复及抽象建议，单独标注推断及依据，不能回写成已证实事实。可将 rustdoc 文档与签名用于召回，再结合 XKernel facts 的调用/数据关系及源码验证；本次未核实二者对齐算法或任何服务端实现。

因此，推荐定位是“**文档/API 索引 + 构建事实索引 + 带来源的推断层**”，而不是“rustdoc 生成即得到行为真相”。相似文档、相同签名或共同依赖均不足以证明行为等价或可以免审。

## 实际检索与未完成项

直接打开上述三个官方 URL；无搜索引擎查询词，未访问第四页。阅读概览的根对象/类型清单、Item 的声明与字段解释、Advanced features 的 cfg(doc) 两节。为遵守最多三页与快速收束限制，未继续展开 Function/Crate 字段页；完整 schema 适配需另行核验。未运行实验，未评价检索准确率、配置覆盖率或重复功能识别效果。
