# 缓存共享方案：集中事务不等于值得采用

## 判断

**暂不准入这份Cow helper提案。** 源码显示它集中了一处共同事务，保留了已检查的正常路径状态选择和解锁后保留对象；但owned输入命中已有赢家时，未采用的候选Dentry与名字String的清理先后发生变化。其可接受性未建立，新增接口也尚无净维护收益证据。

这不是现实缺陷或性能退化的报告，不否定两方法具有局部重叠，也不证明所有共享方案不可能。只关闭本次具体提案，不继续加Option状态／返回guard等补丁追求通过。已有303项测试并没有运行本提案，更不能作为它的等价证明。

## 对象、方法与证据

对象为固定续审case-002，xkernel版本`7e3ac94431a0dbb376d2fc8d85098deeff1bba09`，`dentry.rs:831–845`和`:933–949`。准入协议为`research/protocols/cache-sharing-admission-v1.json`；run为`2026-11-18-cache-sharing-admission-01`。先冻结四份输入，再提交唯一`proposal.rs`；提案摘要由census及独立审阅分别固定为`e25a1638d9ef48d9856526f112bfc1503b7cf34ddcb5de2764493e44475e77e5`。它不在最初输入freeze中，不能冒称事前已冻结生成结果。

本批是源码静态准入，不是原论文复现或新检测算法实验。参考本地codebase-design技能的接口负担与知识集中视角，但技能不是效果证据，不用行数比值定义模块质量。状态验证背景见[真实缓存fixture](2026-11-18-cache-transaction-fixture.md)。Rawls在`independent-review.txt`完成一份独立静态审阅；Agent共识不是金标准。

检索`cache-transaction Cow insert_cache`命中175、返回6、省略169，原输出保存为`lookup.json`。实际回读fixture笔记、完整结果与原源码，删除事务的既有结论仅作已关闭机制边界；未重跑它。补读本机1.95.0的`alloc/src/borrow.rs:331–336`及官方Rust Reference，原件和摘要归档于`language-sources.json`。官方网页是当前版本，不冒称与工具链版本相同。

## 唯一提案

增加私有`cache_live_or_insert(Cow<str>, &Dentry) -> Option<Dentry>`，由它拥有children guard并处理raw weak查找／插入。两个wrapper仍分别决定缓存资格和superblock保留方式，不新增公共类型、trait、回调或生产接口。

`Cow::into_owned`在本机固定源码中对Borrowed调用to_owned、对Owned移动原值，因此该形态没有在源码层额外要求owned名字复制，borrowed名字仍仅在miss时物化。没有测指令、内联、总分配或性能，不能称零成本。

|路径／义务|源码核对|
|---|---|
|live正常／PAR赢家|仍直接upgrade并返回原赢家，无过滤|
|absent／expired|仍在同一children guard内插入weak候选|
|owned准入拒绝|gate不变，helper不执行，参数仍在wrapper清理|
|borrowed保留|仍在guard结束后clone并交给superblock|
|owned插入成功|名字移入map，候选仍由wrapper移动给superblock或在返回时清理|
|owned命中已有赢家|名字移入helper后提前结束生命周期；相对候选参数的清理顺序变化|

## 为什么已有状态测试不足

Rust的函数体局部值先于函数参数清理，离开多个作用域时从内向外；据此和参数顺序可推导本提案的正常返回路径。语言依据见[Rust Reference：析构作用域与函数参数](https://doc.rust-lang.org/reference/destructors.html#scopes-of-function-parameters)。

- 原owned hit：children解锁 → wrapper的entry参数清理 → name参数清理。
- 新owned hit：helper的children解锁 → Cow拥有的name清理 → 返回wrapper后entry参数清理。

两者都在children解锁后清理；不能误写成新方案把析构放进锁内。Dentry是Arc包装，最后一个拥有者的释放可能进一步清理inode、parent及children等成员，但本批没有跟踪真实最后拥有者、allocator或实际调度，不能推出有害后果。

已有live-hit fixture把`candidate.clone()`交给owned wrapper，并保留caller的强引用；断言关注赢家和weak slot，不观察这一清理相对顺序。即便未来本提案通过同一fixture，也无法由此消除该证据缺口。这是测试覆盖与采用义务的差别，不是测试失败。

## 维护成本分账，不给主观总分

`census.py`可重算固定源码切片，结果在`census.json`：

|字面指标|原版|提案|
|---|---:|---:|
|方法数|2|3|
|children lock／live upgrade／weak insert实现位置|各2|各1|
|保留对象调用位置|2|2|
|非空行，提案不计impl外壳|32|39|

收益是共同的raw-map事务只实现一次；成本是helper跳转、Cow输入语义及wrapper/helper之间的所有权约定。行数受排版影响，不能据增加7行判定较差；相反也不能据共同事务少一处判定较好。当前没有独立维护任务、性能预算或真实变更收益支持放宽清理次序义务，因此主线程采纳DEFER。

## 停止边界与研究产物

本批0编译、0内核运行、0生产改动。保留提案、反对依据、语言出处及数值清点；不修改先前fixture的成绩或已冻结门槛。尚未建立算法创新、专利成熟度或可采用的内核优化。后续方向由阶段研究瓶颈决定，不在这份小helper上继续扩建通用验证平台。
