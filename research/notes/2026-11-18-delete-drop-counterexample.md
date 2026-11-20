# 相同错误码，不同析构时点：删除事务抽取的反例

## 问题与结论

固定发现队列case-004已识别`unlink_with/rmdir_with`共享的事务骨架。本批不是再次发现它，而是确认最简单的提案：公共helper持有父／受害对象的guard，操作闭包保留类型检查、权限回调和后端调用。

**该朴素提案未通过行为保持门槛。** 若闭包按值捕获尚未执行的`FnOnce`权限回调，类型拒绝路径会改变其捕获对象相对两个guard的析构时点。保留相同错误码与相同显式调用顺序不够。这里只拒绝这一所有权形态，不证明所有抽取方案都不可能，也不证明现有内核有死锁。

## 来源与理论依据

[准入分析](2026-11-18-delete-transaction-admission.md)冻结既有两方法、同版依赖、源码摘要及义务：原函数参数持有权限回调，建立两guard后先检查类型，只有类型匹配才消费调用回调。未消费参数在局部guard退出之后销毁。

[Rust Reference：析构与作用域](https://doc.rust-lang.org/reference/destructors.html#scopes-of-function-parameters)规定函数参数的清理晚于函数体局部绑定，离开多个作用域时由内向外清理。闭包按值持有的对象也有析构行为；不能把`FnOnce`当成无副作用谓词。此次在线原文、摘要及读取日期保存在`research/evidence/runs/2026-11-18-drop-scope-reference-01/`，不是内核固定版本的规范快照。

研究者据实际提案提出析构风险，Goodall明确接受／拒绝门槛，Huygens实现并运行独立宿主见证；主线程复核原源码与观测。这是有针对性的开发验证，不是盲测、模型能力基准或独立人工标签。

## 冻结实验

目录`research/evidence/runs/2026-11-18-delete-transaction-confirmation-01/`保存`protocol.json`、`witness.rs`、`run.py`、事前freeze、全部编译／执行日志及结果。目录沿用确认任务名，但本批**只有宿主见证，没有内核确认运行**。

- 两种形态：原函数直接持有回调参数；naive包装闭包移动回调并由helper消费。
- 三种条件：类型拒绝、权限回调返回错误、成功。
- 两种构建：Rust1.95.0，edition2024，opt-level0／3。
- 观测：错误结果、回调是否执行、捕获析构、guard结束及后端／清理事件。
- guard是带Drop记录的RAII替身，不是ksync锁；没有显式`drop(may)`制造差异。

两次构建、两次执行，各6组观测，总计12组；零接入修复。不是12个独立样本，也不是12次内核测试。源代码、协议和runner在执行期间不变。

## 结果

|条件|返回值比较|事件比较|
|---|---|---|
|类型拒绝|均WrongType|原版先结束victim／parent guard，再析构未调用回调；naive相反|
|权限拒绝|均PermissionDenied|本见证相同；回调已被消费，捕获析构原本就在guard结束前|
|成功|均Ok|本见证相同；回调后执行backend、mark、forget，再结束guard|

类型拒绝两边都没有执行权限回调或后端。差异来自拥有权跨函数／闭包边界，不是业务分支选择不同。debug与opt观测一致。

`scripts/check_delete_drop_witness.py`独立从stdout重建12组记录，核对机器结果和二进制摘要，直接检查相对事件次序。结果在`independent-output-check.json`；没有再次运行探针，也不把两种优化模式当全部编译器／配置的证明。

Rawls独立审读原函数、见证与日志，结论LIMITED ADMIT，未发现该有限范围的源码／记录缺陷；审议在`research/evidence/runs/2026-11-18-delete-drop-review-01/audit.txt`。编译产物在审计后迁到忽略目录`.build/delete-drop-witness-01/`，迁移前后hash相同；`binary-relocation.json`记录位置，`post-relocation-check.json`复核通过。原执行manifest不倒写，源码与命令足以在新的隔离目录重建；不把二进制混入Book内容。

## 对确认流程的作用

发现阶段的相似证据仍成立：确实存在共享顺序。确认阶段新增拒绝理由：这个提案的可观察生命周期不保持。测试成功含义是**预先声明的反例被观察到**，不是重构候选通过。

以后遇到“持guard的helper调用移动回调”可复用以下检查义务：

1. 找出回调尚未消费的提前返回路径。
2. 明确原参数、闭包捕获与guard分别在哪个作用域结束。
3. 区分未调用、已调用后报错、成功三类路径，不要求全部析构都在锁外。
4. 能局部验证时先检查事件次序，再决定是否值得执行更昂贵的内核测试。

这来自已有Rust语义和本次实例，不是新理论／新算法或成熟专利点。当前未实现自动发现此风险的lint、解析器或LLM评测机制；可复用的是见证及校验程序，不能夸大为通用自动证明。

该实例已用于提出风险、设计观测和检查结果，后续只能登记为暴露过的开发／回归反例。不得再把它作为独立测试集，计算新机制的泛化成绩；需要另选未参与设计的样本与相同预算才能比较方法效果。

## 停止与未覆盖部分

否决naive提案，暂停原计划三格QEMU比较，不为了保住提案而不断增加Option、自定义Drop或公共trait。未测试真实ksync、并发、panic、FS后端、具体调用者是否具有相关析构副作用；不报告性能或净维护收益。另一种保持生命周期的抽象若未来提出，必须另做接口成本和契约准入，不能沿用本次相等条件宣称通过。

Goodall终审记录于`research/evidence/runs/2026-11-18-multirecord-route-steering-01/decision.txt`，主线程采纳关闭此机制，不继续构造生命周期变体。下一步返回原固定发现队列，先排除已审对象再有限续审；不将新的helper设计作为本例必须得到的正结果。

原文献复现仍保留为独立路线：[Aroma](2026-11-18-aroma-multirecord-admission.md)缺现成多记录AST，[PAM](2026-11-18-pam-multirecord-admission.md)有原生调用数据但需准备执行与源码映射。此反例没有否定结构方法或重复发现目标；它为“发现→确认”链条提供了一个可复核的拒绝案例。
