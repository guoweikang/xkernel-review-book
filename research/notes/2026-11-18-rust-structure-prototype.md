# Rust 结构原型：受限导出器，不是 Aroma 或类型绑定

## 本批结果

新增 `research/tools/rust-syntax-probe/src/bin/rust-structure-probe.rs`，281行；仅复用现有 syn／proc_macro2／serde_json。离线 locked 构建一次成功，零修复。12项冻结控制全部通过检查：11 parsed、1预期语法拒绝；固定429集合按ID排序前8项全部提取，8 parsed，但**完整 exported-body-subset 覆盖0/8**。不换样本、不扩大语法、不排名。

这是小型新 exporter 的接口准入证据，表明无需先造类型平台就能导出部分表达式父子与词法候选；不是完整 Rust AST、Aroma schema、真实声明绑定、方法效能或生产收益结论。已知缺口是全部八个真实函数仍有 opaque；不能用解析成功掩盖它。

## 协议与入口

专属run：`research/evidence/runs/2026-11-18-rust-structure-prototype-01/`。

- `protocol.json` 在实现／构建／探针执行前冻结，SHA256 `d67a9640e96551dc6ffc00bca4e88e45b6db417f3d090daf23653f96e4f54469`。固定源码／429列表摘要、八ID、12输入、预期检查、最多两次窄修复预算；实际零修复。
- `schema-clarification.json` 是执行前的字段／保守性说明，不替换输入或预期。`nodes` 提供 `node_id/syntax_kind/parent_id/ordered_children/range/role/scope_id/source_text/coverage/subtree_closed`；`scopes`、`binders`、`occurrences` 分别存作用域、已声明简单binder和出现。
- `run.py` 为独立runner，`check_controls.py` 为本批检查器；运行命令为 `.build/doc-retrieval-env/bin/python -B research/evidence/runs/2026-11-18-rust-structure-prototype-01/run.py --attempt 0`。目录创建拒覆盖；不再重跑现有目录。
- `attempt-0/` 含实际执行源码、runner/tests、Cargo.toml/lock和协议快照，build/version完整stdout/stderr、exit与耗时，以及12份控制源和输出；`corpus/` 含八份源码／输出／命令及 `results.json`。没有构建或探针错误被删除，控制12拒绝完整保留。
- 二进制 `.build/rust-structure-probe/debug/rust-structure-probe`，SHA256 `0556490fa749b4867232f18f99b5839b842a9bc673ada8fcce3e327553b1cb90`。工具链显式用已安装1.95.0，`CARGO_NET_OFFLINE=true`，独立 `CARGO_TARGET_DIR=.build/rust-structure-probe`，命令同时 `--offline --locked`。未改现有任何probe、Cargo或lock。

## 表示与保守策略

源码行号均指本批快照，完整hash在最终manifest。

- `rust-structure-probe.rs:30` 节点保存UTF8字节半开范围及逐字切片；`:246` 按源码范围排序children并自底向上计算闭合。节点ID是访问次序，不是源码排序或执行次序。
- `:54` 的name处理只为单段路径寻找当前活跃frame中的最近已登记简单binder；`r#`只在查询名规范化时移除，原拼写保留。`method_name/field_name/function_name`不当局部使用；没有类型、import、trait或API目标解析。
- `:83` 块入口建新frame；存在任何nested item时从块开头保守标未知，避免假定item仅在声明后生效，不实现item resolution。普通顺序let先访问initializer再登记binder；退出块pop恢复外层。当前scope或任一活跃祖先未知时，局部使用全部 `binder_candidate=null,candidate_status=unknown_scope`，不退回旧同名binder。
- 不支持的表达式、complex pattern、let-else、closure、match、for、if/if-let、宏和item保留完整opaque范围与原因；不进入内部声称覆盖。复杂路径／类型语法也opaque，但不假设它们引入局部binder。未知表达式／声明保守污染当前frame。scope的 `unknown_binding_effects` 是历史标记；先前已给出的候选不因之后顺序污染被倒写。未模拟宏展开／卫生或宏产生的前向item作用域，因而候选仍只针对输入中显式可见的受限词法构造，不是实际Rust解析。
- `coverage.complete_supported` 的domain明确为 `exported_body_subset_not_full_rust_ast`，仅说明导出body里无opaque；不说明签名、类型、cfg、运行行为或绑定完整。`exported_tree_closed` 包含签名opaque；`lexical_scopes_without_unknown_effects` 另列历史scope不确定性。parse状态与这些字段分开。
- 签名／类型、属性、限定符未提供完整语义节点；节点保留原片段，类型opaque，`signature_semantics=not_evaluated`，`cfg=not_evaluated`。函数／参数未支持属性会标对应scope未知；并未做配置裁剪或编译验证。

## 预先固定的控制与真实输入

控制01验证let initializer见旧binder、后续使用见新binder；02验证块退出恢复；03验证self receiver、method及field角色分离；04验证中文字节范围与raw identifier；05简单运算符；06限定路径opaque但普通实参独立；07closure opaque并保守未知；08复杂let整体opaque；09match／for／if-let不扩实现；10宏／cfg属性／nested item；11未知内块pop后恢复；12 malformed。实际原答在 `attempt-0/control-01.stdout` 至 `control-12.stdout`，检查结果 `control-checks.json`。

八个ID明确冻结为：00536a…、00d2ba…、028957…、028c8c…、02b109…、03c3cb…、044ab1…、04e10a…；完整ID在protocol中，全部保留。来源是原429人口和812调用归档的原source_text，未读排名或标签选择。`corpus-context.json` 后补保存八条完整原unit metadata、属性／祖先／文件cfg hints，核对原sources.zip整文件hash及原range逐字重建全部通过。

注意部分unit的`original_range`包括外层文档／属性前缀，实际输入仍是既有`range`切出的函数签名＋body；原区间和所有metadata均保留。侧车中的外层／祖先cfg未送入探针、未参与候选计算，不能把片段内候选解释成多配置可见性事实。该侧车为事后来源核查，不是改动冻结输入或选择规则。

八份输出共222节点、79出现；其中59非局部使用、15 unknown_scope、5 lexical_candidate。44 opaque节点中23是类型，13为if/if-let，2 match，1 for，1限定／泛型路径，4其他未支持表达式。没有从不支持分母剔除任何函数；0/8 body闭合只说明这个受限原型在该预定八例的缺口，不代表全429或结构方法无效。

## 验证、耗时与结案

本批检查器验证parent/children互指、单根无环、来源范围、子范围包含、source排序、UTF8切片、scope索引及候选祖先／同名、预期遮蔽和未知模式；八个原文件hash及切片另核。主线程独立checker及故意破坏负例由主线程执行，不在本批改动或冒领其结论。

构建墙时2.701524秒；12个控制进程耗时合计0.013662秒；八个提取进程合计0.016116秒。后两者不含检查器和来源侧车核验，不与旧提取时间相加，也不作吞吐或总体性能比较。

已读AGENTS、research-execution、PROGRESS与上批准入及协议；本批承接上批结构字段检索，新增 `research_lookup.py rust-structure-admission rust-structure-probe --limit 3` 得66命中、显示3、省略63。仅定位，不当穷尽证据。主线程提供的Rust Reference作用域提醒用于执行前保守item策略；本线程未再次浏览或将在线规范称内核固定版本。

按本次明确要求，仅改上批note归因措辞“用户后续边界澄清”为“主线程补充边界澄清”。上批run的旧note hash保持历史事实，不重写旧validation或任何源归档；本批manifest记录当前note hash与这次授权校正。

停止：导出器＋新run＋本note交付，无shared catalog／PROGRESS改动，无LLM／排名／生产改动；不因8例均部分覆盖而擅自扩充语法或追加案例。下一准入与方向由主线程及独立审议处理。
