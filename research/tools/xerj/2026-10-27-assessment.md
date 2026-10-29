# XERJ 对 X-Kernel 复用审查的适用性

日期：2026-10-27。研究快照：`xerj-org/xerj@2b67a883ab43cd2146199968f537912c0bee3b9d`。
只克隆并阅读官方源码和文档，没有安装、启动服务、索引 X-Kernel 或实测性能。
结论是架构适配判断，不是上线或性能验收。

## 结论

XERJ 值得作为可替换的候选检索与元数据存储后端评估。它提供词法、向量、混合搜索，
Rust 语法定义索引，以及 HTTP/MCP 接口；职责建模、完整 Rust 语义、克隆检测、
复用可行性与评分校准仍需要独立层。不要把默认 autoindex 的产物当成完整语义数据库。

## 已核对的能力与限制

| 项目 | 证据 | 对需求的意义 |
| --- | --- | --- |
| Rust 定义提取 | [code.rs](https://github.com/xerj-org/xerj/blob/2b67a883ab43cd2146199968f537912c0bee3b9d/engine/crates/xerj-autoindex/src/extract/code.rs#L1749) 的 tree-sitter 查询抓取 function、struct、enum、trait、mod、macro、type、const、static。 | 可用作语法候选目录；该查询未独立捕获 impl 块，也没有类型解析或 Cargo 模块树解析。不能从同名方法直接确定其接收者。 |
| 符号内容与引用位置 | 同文件 [Symbol](https://github.com/xerj-org/xerj/blob/2b67a883ab43cd2146199968f537912c0bee3b9d/engine/crates/xerj-autoindex/src/extract/code.rs#L416) 和 [emit_symbol_records](https://github.com/xerj-org/xerj/blob/2b67a883ab43cd2146199968f537912c0bee3b9d/engine/crates/xerj-autoindex/src/extract/code.rs#L1440) 保存 name、kind、行号、声明和实现片段。 | 声明截取上限 400 字符，实现片段上限 16 KiB；容器截在第一个嵌套定义之前。完整审查需回源码补齐，不能据返回片段断言完整职责。 |
| embedding 后端 | [embedder.rs](https://github.com/xerj-org/xerj/blob/2b67a883ab43cd2146199968f537912c0bee3b9d/engine/crates/xerj-ai/src/embedder.rs#L1) 区分 lexical、proxy、neural、实验性 ONNX。 | 默认是词法 feature hashing，不是神经语义理解。需要显式选择模型，查询和索引保持一致。 |
| 内置 neural | [neural.rs](https://github.com/xerj-org/xerj/blob/2b67a883ab43cd2146199968f537912c0bee3b9d/engine/crates/xerj-ai/src/neural.rs#L1) 默认 sentence-transformers all-MiniLM-L6-v2，通过 candle 推理。 | 它是句子编码器；是否适合 Rust 实现/中英文契约检索需要评估，不能继承一般文本指标。可考察 proxy 对接独立代码模型服务。 |
| 搜索与 agent 接入 | [README](https://github.com/xerj-org/xerj/blob/2b67a883ab43cd2146199968f537912c0bee3b9d/README.md) 描述 BM25、kNN、hybrid、定义检索和 MCP；[memory_api.rs](https://github.com/xerj-org/xerj/blob/2b67a883ab43cd2146199968f537912c0bee3b9d/engine/crates/xerj-api/src/memory_api.rs#L50) 明确混合检索的 RRF/linear。 | 后端可以减少重复建设；x-review 服务调用 HTTP，agent 交互可用 MCP。检索命中和搜索分数仅是候选证据。 |
| 自定义 Rust 事实 | [Rust AST security substrate](https://github.com/xerj-org/xerj/blob/2b67a883ab43cd2146199968f537912c0bee3b9d/docs/examples/rust-ast-audit/README.md) 展示外部 tree-sitter 抽取、NDJSON、显式 schema 导入。 | 是可借鉴的集成方式，属于审计示例，不是 autoindex 默认具备的完整分析器。 |
| 自定义元数据字段 | [ingest.py](https://github.com/xerj-org/xerj/blob/2b67a883ab43cd2146199968f537912c0bee3b9d/docs/examples/rust-ast-audit/ingest.py#L26) 显式定义 crate、module_path、owner、trait_impl、unsafe、锁等字段。 | 可用相同方式写入我们定义的 entity_id、职责、契约、配置、证据、revision；身份字段应显式为 keyword。 |
| 图关系 | [detectors](https://github.com/xerj-org/xerj/blob/2b67a883ab43cd2146199968f537912c0bee3b9d/engine/crates/xerj-autoindex/src/detect/mod.rs#L1) 为文档链接、路径、同目录等关系；[cratecite](https://github.com/xerj-org/xerj/blob/2b67a883ab43cd2146199968f537912c0bee3b9d/engine/crates/xerj-autoindex/src/detect/cratecite.rs#L1) 按含 Cargo.toml 的目录名识别文本引用。 | 不能视为 Cargo crate 依赖图或 Rust 调用图；审计示例也明确排除无法类型推断的方法调用边。 |
| 重排及判断 | [RERANK](https://github.com/xerj-org/xerj/blob/2b67a883ab43cd2146199968f537912c0bee3b9d/docs/RERANK.md#L1) 是外部相关性重排；[DECISIONS](https://github.com/xerj-org/xerj/blob/2b67a883ab43cd2146199968f537912c0bee3b9d/docs/DECISIONS.md#L1) 有标注历史近邻投票。 | “相关答案”分数和历史投票不等于可复用概率。重排文档明确提示未校准，且启用外部服务会发送候选文本。 |

上述代码提取路径没有提供重复率或 Type-1–4 克隆判定；本次未发现可直接替代独立克隆
检测器的能力。此结论限定于检查过的 autoindex/search 路径，不声称穷举所有实验目录。

## 建议接入边界

```text
固定代码快照 + Kconfig/构建配置
  → 外部实体/契约抽取与证据维护
  → 自定义 metadata、源码及设计文档写入 XERJ
PR diff → 完整变更实体 → XERJ 多路检索 + 独立克隆候选
  → 合并候选 → 契约/配置/依赖审查 → 可复用途径 → AI review
```

XERJ 返回候选、位置、内容与检索分数；审查层拥有领域标签、适配成本、反证和置信度。
`xerj def` 是便捷检索接口，其 [过滤构造](https://github.com/xerj-org/xerj/blob/2b67a883ab43cd2146199968f537912c0bee3b9d/engine/crates/xerj-autoindex/src/def.rs#L276)
会依据字段 mapping 是否适用决定是否添加 kind/language 条件。领域约束应使用我们
掌控的显式 mapping 和查询，并校验返回元数据，不能把便捷接口选项当作严格配置隔离。
字段建议包含 repo/revision/config、符号身份、父子关系、职责描述、结构签名、
上下文/生命周期契约、证据位置和 unknown 状态。代码与职责摘要可分通道检索后融合。
较大的原始源码和短职责摘要不应盲目混为一个向量，具体切块方案需要比较。

Rust 类型/trait/宏展开与跨文件关系若需要精确解析，可结合 rust-analyzer/SCIP；
tree-sitter 作为语法覆盖补充。Kconfig 与 feature 覆盖、原生代码与宏生成代码的对应关系
仍由我们的索引层记录。代码被改动的前后实体应独立比较，排除移动与删除后的旧实现。

自动增量同步不能直接等同于固定 PR 快照。建议 review 使用按 repo/revision/config
隔离并验证完成状态的只读索引；更新后重新校验源码证据。索引生命周期、删除和一致性
的进一步源码核对见 [增量与隔离笔记](2026-10-27-incremental.md)。

## 进入原型前的验收问题

1. 能否稳定返回跨文件的同名方法、宏定义/展开、cfg 分支、模块重导出的正确实体？
2. 对一批已标注复用正例和困难负例，BM25、neural/proxy、hybrid 各自的 Recall@K 如何？
3. 自定义身份/config/revision 过滤是否真正执行，候选能否严格回溯到固定 HEAD？
4. 修改、删除、重命名、两个 PR 并行和中途失败之后，是否存在旧候选或混合代际？
5. 增量时间、索引空间、候选 token 量、P95 查询耗时及可行动建议精度是否满足预算？

这些是后续实验，不是本轮已通过的测试。本轮不依据 README 中其他项目的性能数字
估算 X-Kernel 收益，也不将产品功能组合当作论文或专利的新颖性证据。
研究贡献仍应集中在复用契约、配置/架构可行性与评价系统，底层检索后端保持可替换。
