# 普通 if 的单次受限扩展准入

## 结论与停止

新增独立 `research/tools/rust-syntax-probe/src/bin/rust-structure-if-probe.rs`，312行，相对冻结原版仅新增31行、删除0行；原 `rust-structure-probe.rs` 逐字不变。只扩无模式绑定的普通if，未扩closure／match／for／类型或平台。

一次离线构建成功，零修复。原12控制全部通过且JSON与旧结果一致；新增4控制全部通过。同8输入均解析，但**完整 exported-body-subset 仍0/8**。节点222→561、出现79→189；lexical_candidate 5→18、unknown_scope 15→50。这些是表示覆盖计数，不是语义质量、真实绑定或检索收益。

**本批到此停止**，不按新增opaque继续补语法、不换样本、不运行排名。主线程独立checker／固定census自行执行，本报告不冒领或预判重复候选组结果。

## 冻结、文件及实现

证据目录 `research/evidence/runs/2026-11-18-rust-structure-if-01/`。`protocol.json` 先于新bin实现与运行冻结，SHA256 `b669b2784308fad18deffc802d4e5ea70098de5345f60db5d656c934a4f723fb`；固定旧协议／测试／源码／输入hash、原八ID、原12控制和新增13–16完整源及预期。最多一次窄修复预算未使用。

- 新bin源码 SHA256 `a070c96b62be3a854c70c554faeead68ee347f259dcfe2f17cf3de1015919541`，实际差分保存 `source-delta.diff`。
- `rust-structure-if-probe.rs:8` 至`:22` 用 `syn::visit::Visit::visit_expr` 递归检测condition中的 `ExprLet`，`:12` 的专用回调标记命中；**没有文本匹配**。保守地排除遍历到的任何ExprLet，包括let-chain；宏token本身不伪解析。
- `:132` 只为无ExprLet的ExprIf选择 `ordinary_if`；有ExprLet仍走`:154`原 `unsupported_if_including_if_let` whole opaque＋taint。属性检查继续沿原规则，未求cfg。
- `:179` 先导出condition；`:182` 若条件导出的任何节点opaque，就将**当前外层live scope**标未知。因此条件块内opaque即使已经pop也不能在then／else重新变成已知。限定路径等opaque condition同样保守处理，不推断控制流／条件真假。
- `:187` then用原block入口建立scope，role=`then_branch`；`:189` else以role=`else_branch`递归导出block或普通else-if。condition role明确；branch binder按原block pop，不泄漏外层。外层已taint时两分支均保留unknown。

原 `rust-structure-subset/1` schema不变。`coverage.complete_supported`仍只指导出的body子集无opaque，不包括签名类型语义、cfg、真实声明绑定或执行路径；`parsed`与coverage分列。作用域、候选和历史taint含义均沿原协议，不称Aroma schema或类型解析。

## 控制与实测

`attempt-0/control-01..16.rs/.stdout/.stderr/.command.json` 保留全部控制、原输出与日志；`control-checks.json`记录检查。15 parsed、1预期malformed rejected，16检查通过。原12使用未改旧checker及原期望，并逐对象比较旧JSON相等；没有改旧测试以适配结果。

|新增控制|事前检查|结果|
|---|---|---|
|13|condition／then／else角色；then let initializer见旧binder，后续见新binder，else及if后恢复旧binder|通过|
|14|else-if递归；两个分支block隔离，branch binder不泄漏|通过|
|15|直接if-let与 `&& let` 条件均整体opaque，0 ordinary_if、2旧原因opaque，不产生内部假出现|通过|
|16|包含宏的条件block退出后仍未知；then、else、if后三次value使用均unknown|null候选，检查通过|

真实输入严格复用上批429排序前8的同ID、同字节，未读标签或排名做选择。路径沿原约定 `corpus/<unit_id>.rs/.stdout/.stderr/.command.json`；`corpus/results.json`分项保留状态，`summary.json`有逐单位前后节点数。新解析出的普通if共15个，其中包括原opaque父级内部此次才暴露的嵌套if，不能简单当成旧13个opaque的一对一替换。

八单位合计561节点、189出现；其中117非局部使用、18词法候选、50未知作用域、4无可见词法binder。62个opaque：23类型、25限定／泛型路径、4closure、4其他未支持表达式、3if-let、2match、1for。opaque数量44→62是展开后暴露更多内部内容，不是扩大或缩小语义正确率的度量。所有八例仍不完整，均留在分母。

`reference/corpus-context.json`逐字保留上批八unit完整metadata与原文件／切片核验。片段外属性／祖先cfg不进入本探针候选推理，仍未求值。source全文、site切片、parent／children和scope均可供主线程独立审计。

## 执行边界与验证

使用既有Python venv和安装的Rust1.95.0，`cargo build --offline --locked --bin rust-structure-if-probe`，manifest为原 `research/tools/rust-syntax-probe/Cargo.toml`；独立 `CARGO_TARGET_DIR=.build/rust-structure-if-probe`。没有新增依赖、联网、修改Cargo/lock或旧探针。

新二进制 SHA256 `dc4037b15057eeefde15adc521579d6f9d5677e388a5b1f4594f9754a01c02e2`。`attempt-0`保存执行源码／runner／checks／协议／Cargo快照、版本环境、全部构建日志及hash。构建墙时9.969256秒；16控制进程合计0.022849秒；八单位提取进程合计0.028151秒，均单轮测量、后两者不含检查成本，不作总体性能比较。

本批检查沿用原树／range／scope／candidate一致性，再加分支角色、同scope隔离、条件未知传递、旧12不回归和输入字节不变；最终原始输入hash、旧源码hash、新源码与执行快照、协议hash再次核查。`final-manifest.json`保存本批产物及新增源／note摘要。编译和检查无异常，预期malformed拒绝不隐藏。

已读最新PROGRESS、discovery专题、原协议、Goodall普通if单次扩展决策和research-execution。检索 `research_lookup.py 'ordinary if' rust-structure-prototype --limit 3` 得118命中、显示3、省略115；承接先前Rust字段／scope审计，不当穷尽来源检索。未新增外部文献或语义真值声明。

未改shared catalog／PROGRESS／census或旧run；无模型、排名、生产改动。本批只有这一项扩展，是否有足够局部变量使用结构由主线程固定census及审议判断，不预设正结果。

交付前主线程另行通知：独立checker的24输出通过、八源码一致；同规则census为7/8、35子树，重复候选组1，仅在 `!self.dentry.ptr_eq(&self.mnt.mnt.mnt_root)` 中有两次self。**这是主线程通报的独立结果，不是本runner的测量**，未合并进本批summary或重跑census；原日志及最终解释以主线程独立审计归档为准。该结果不构成编译器绑定、方法效能或重构收益结论，本批仍停止。
