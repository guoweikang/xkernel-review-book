# Rust 结构前端准入：归档适配与小型导出器分开判断

## 结论

本批仅核既有 Rust 工具、归档及六个显式小控制，不运行 Aroma、模型、编译器或全语料排名。**现有归档不能仅靠字段搬运忠实生成完整表达式树及局部变量使用输入；这不否定结构方法，也不意味着必须建设大型平台。**

|层次|准入判断|边界|
|---|---|---|
|A：只转换既有输出|完整目标 **否**；单位层级／调用列表的无损适配 **是**|缺表达式父子、完整叶序列、变量出现角色；不可把缺失字段猜出来|
|B：复用现有 syn，新增小型 visitor/exporter|**静态可行，尚未实现或验收**|可以导出语法父子与词法作用域／变量出现；不需先引入类型解析平台|
|C：真实声明绑定、类型及调用目标解析|**未准入、未估为小改动**|需要另定宏展开、配置、crate/import/name resolution、trait／类型推断等范围；不是 B 的承诺|

完整证据位于 `research/evidence/runs/2026-11-18-rust-structure-admission-01/`：`protocol.json` 在任何探针控制前写入；`execution-start.json` 固定协议、runner、源码、二进制摘要；`01..06.rs/.stdout/.stderr/.json` 保存全部输入与原答；`archive-audit.json` 保存既有输入身份和字段扫描；`summary.json` 保存观察。主线程补充边界澄清单列 `decision-scope-addendum.txt`，未改协议或追加控制。

## 现有源码与归档的精确能力

以下路径相对仓库根目录；行号指本次读取版本，完整 SHA256 见 `archive-audit.json`。

1. `research/tools/rust-syntax-probe/src/main.rs:37` 的 Collector 仅保存 `units` 与 `ancestors`。`:43` 的 enter 输出 `kind/name/range/ancestors/attributes`；`:58` 增加 signature/body range。`:74`、`:82`、`:90`、`:98`、`:105`、`:112`、`:136`、`:142`、`:149`、`:156` 分别记录函数、impl方法、trait方法、impl、trait、mod、宏token、闭包、struct、enum。其递归访问不等于序列化全部 AST：没有为普通 call/if/let/pattern/path/identifier 输出节点或边。`:175` 调用 syn::parse_file，非编译／类型检查。
2. `research/evidence/runs/2026-11-05-source-units-v2-verified/inventory.json:44` 起可见 ancestors，`:193` 起的 closure 祖先为 impl 和方法。精确入口 `files[path].units[index]`；祖先索引仅在该文件的 units 数组内有效。88文件、5035个已记录节点全部祖先索引先于子节点且范围包含检查通过。末祖先可转换为**已保留单位树** parent；同一 parent 按已有次序可导出**已保留单位** children/siblings。它们不是完整 AST parent，也不是 Aroma 叶邻接关系。空祖先只是本记录森林根，不表示项目根。
3. 归档源码固定 `7e3ac94431a0dbb376d2fc8d85098deeff1bba09`，2180有体函数、45无体声明。`research/evidence/runs/2026-11-05-rust-baseline-corpus-01/units.json` 为数组，含 `id/path/range/original_range/ancestor_ids/attributes/ancestor_attributes/file_attributes/cfg/sha256/source_sha256` 等；`sources.zip` 保留原文件。源码可供未来重解析，但读取源码并重建语法本身不是现成字段适配。
4. 历史 inventory 的 `report.json:236` 固定 main.rs 为 `bdb2857e…`；当前 main.rs 为 `5f4f4d07…`，两者不同。历史 inventory 声明 binary 为 `007378dd…`；本批未执行或重建 main binary，未假定当前 main 可逐字复现历史归档。归档字段扫描与当前源码能力检查分别陈述。
5. `research/tools/rust-syntax-probe/src/bin/rust-call-probe.rs:13` 输出 `kind/name/range/deferred_depth/target_resolution/cfg/execution`。`:24` 取路径 segments 的 ident，丢弃 leading ::、泛型和 qself 细节；非 Path callee 的 name 可为空。`:34` 方法仅存 method ident，不存 receiver。`:39` 宏 opaque；`:44`、`:50`、`:56` 将 closure/async/item 内调用 depth 加一；`:66` 只解析 ImplItemFn，`:69` 仅访问 body；`:70` 按起始字节排序，非运行顺序。`:73` 保留 parse reject。
6. `research/evidence/runs/2026-11-18-common-call-syntax-01/calls.json` 根 `records` 812条，每条有 `unit_id/source_text/sites`。全量只读字段扫描为5043 method、3858 call、1484 opaque_macro，共10385 sites。site增加的 `source_text` 是其 range 切片，不是完整 receiver/argument 子树。全函数 source_text 尚在，故信息未从源码世界消失；只是未被结构化。没有 parent_id、children、identifier occurrence、binding_id。`target_resolution=unresolved` 不能更名为 resolved API。
7. `research/tools/rust-syntax-probe/src/bin/rust-token-probe.rs:6` 展平 token stream，`:18` 至`:27` 保留 open/close delimiter，故直接 token序列可重建**分隔符组树**，不是语法表达式树；ident标签没有变量／类型／字段区分。`:36` 只做 TokenStream parse。`scripts/prepare_rust_token_bags.py:25` 转 Counter，`:98` 至`:106` 将计数写 blocks.file；已归档 `2026-11-05-rust-token-bags-01/report.json` 的 records[].tokens 是数量，非token数组，blocks.file 不保序，不能从词袋恢复 sibling 次序。

## 与原 Aroma 输入的有限对照

这里只读已归档原代码以明确字段需求，原机制独立研究由主线程承担，不重做论文解释。`research/evidence/runs/2026-11-18-aroma-reference-replay-01/official-similar.py:265` 起遍历嵌套 list、带位置的 parent栈；`:283` 要求 leaf/token，`:287` 根据 var字段存在及首字符启发式处理变量；`:296` 生成 parent位置特征；`:308` 以原 token 字符串为 var_siblings 键；`:329` 起使用遍历叶序列的历史 sibling。**这里的变量使用联系本身也不是已解析声明绑定。**不能将完整类型绑定作为原算法输入的虚构前提，但 Rust 适配必须声明自己导出的 var角色与同名／遮蔽政策。

syn unit.kind、调用列表、词元分隔符均不能直接充当该有标签完整树。把调用拼写挂在人工根下即使能被 JSON 接口接受，也不能称 Aroma表示或原方法复现。本批未生成这类树。原回放 raw JSON CLI失败、JSONL诊断后实际67特征与预期55不符仍然保留，见原 `verdict.txt:1`；本次六控制通过不会抵销该独立 gate。

## 六项冻结控制观察

每项原二进制执行一次，单次上限10秒；实际六次 exit0，五项 parsed、一项预期 rejected，无超时／解码失败。exit0 不代表源码合法编译；reject由JSON状态表达。没有重试、模型、编译／安装或前端变更。源码、二进制与协议前后摘要相同。

|ID|精确原答|观察与不支持的推论|
|---|---|---|
|01|`01.stdout:1`|两次 consume，range [22,29]、[38,45]；未导出 value出现或声明身份|
|02|`02.stdout:1`|源显式增加块内 let value 遮蔽，仍两次 consume，第二range变为[59,66]。01/02仅 `(kind,name,deferred_depth)` 投影相等，**原答、范围、原源码并不相等**；不声称语义等价|
|03|`03.stdout:1`|outer、inner、touch、touch；outer range [22,27]只覆盖callee名，不包含inner；两次touch不含value/other receiver字段。按这些site范围包含无法恢复调用嵌套|
|04|`04.stdout:1`|hidden仍出现且cfg未求值；wrap为opaque_macro，inside不输出；consume在多字节字之后range [68,75]正确切片。不能据出现宣称配置活动或宏内无调用|
|05|`05.stdout:1`|later/pending/nested depth均1，now为0；三类不同延迟上下文压成同一数值，不提供closure capture、scope身份或执行顺序|
|06|`06.stdout:1`|status rejected，sites为空，error="cannot parse string into token stream"；失败输入和诊断保留，不从分母删除|

这只是显式构造的接口／字段控制，不是工程发现效能、语义差异真值或新检索性能结果。

## 最小未来导出器：静态工作量估计，不在本批实现

**建议 B 可作为另冻协议的小任务，而非仅因旧字段缺失拒绝路线。**现有 Cargo.toml 已有 syn full+visit、proc_macro2 span-locations、serde_json，无需安装编译器或新增解析依赖。保守估计一个独立 Rust bin 约250–450行加约10–16个小fixture及轻量校验器；这是人为工程预算估计，未写代码、未计时、不是保证或性能声明。先取受限语法，不承诺完整 Rust-to-Aroma 转换。

- 导出原生中间schema：每节点 `node_id/syntax_kind/byte_range/parent_id/ordered_children`；同时存精确源码／摘要，节点角色保留 receiver/callee/argument/pattern/initializer。用 visitor 的 enter/leave 建栈；需明确哪些Expr/Stmt/Pat/Block及签名节点支持，避免默认递归绕过父节点导致伪树。节点类型标签不是原 Aroma 的 token-placeholder 组合标签；后者另需显式映射与验收。
- 对函数参数、顺序 let、block、closure参数、简单 match arm 建词法 scope；输出 `occurrence_id/spelling/range/role/scope_id`，区分 binder/use/path/field/method。初版可只支持 PatIdent 与简单单段 ExprPath；所有未知分类保留原片段与 unsupported原因，不猜角色。若加最近词法binder的候选关联，要另列 `lexical_candidate`，不得命名 resolved/type binding。
- 顺序 let 的 initializer先在旧作用域访问，再引入新binder；块结束弹出binder；同名shadow使用不同binder候选ID。closure内可记录外层词法候选，但捕获方式、borrow/move及是否运行仍未知。参数类型、字段名、method名不能混入局部变量出现组。
- 暂不处理宏展开／卫生、cfg有效性、use导入、跨item/crate解析、trait/类型推断。解构／or-pattern、if-let／while-let／let-chain、for与match guard的精细可见范围、raw ident规范化、qself、嵌套item捕获边界等必须逐项支持或标为unsupported，不能因syn能parse就宣称已正确处理。宏节点保持opaque，cfg仅源属性，Verbatim显式拒绝或opaque。
- 未来最小验收应覆盖树父子及顺序、UTF8范围、shadow initializer、块退出、closure参数遮蔽、同拼写字段与局部名、宏opaque、cfg两分支保留、未支持语法与parse reject；先冻结期望schema与policy，再运行，不拿新控制调优成方法胜利。若映射要求扩展超出预算，报告部分覆盖并停止，而非升级大平台。

表达式树＋词法出现可以在无类型平台情况下有价值；原 Aroma变量启发式也不要求已解析类型。但是无论选保留同拼写分组还是采用词法候选ID，均属需说明的 Rust适配决定，不能倒称原算法已有此语义。是否进入这一下一批由主线程准入，本批未实施。

## 检索、验证与停止

已读 AGENTS、research-execution、资源检索规范、PROGRESS顶部、discovery专题和独立 `structure-admission-steering-01/decision.txt`。执行 `research_lookup.py Aroma parent shadowing --limit 8`：926命中、显示8、省略918；`research_lookup.py rust-syntax-probe reviewed-call-syntax 结构 --limit 8`：214命中、显示8、省略206。两次清点5892资产，4563文本、1312格式仅元数据、14大小仅元数据、3无路径。查询同时覆盖问题、方法、工具／run标识；没有把显示前8项当穷尽证据。实际打开的原源码、归档及旧失败报告列于 `archive-audit.json`；未重读全部论文、未下载原件或新查网络，因为判断仅针对已给本地版本接口。

六控制输出范围均可按UTF8解码；归档祖先索引与包含检查5035项通过，仅证明已保留边一致，不证明没有漏节点。最终校验记录见run的 `validation.json`。没有更改共享catalog、PROGRESS或专题，按独占授权仅新建本run和本note；未运行会修改共享产物的book构建。无新排名、无Weak重开。停止于三个层次的准入判断，等待主线程决定下一独立任务。
