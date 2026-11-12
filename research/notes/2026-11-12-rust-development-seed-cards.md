# Rust开发种子：来源、配置与困难情境

## 这批材料用于什么

六组已看过的xkernel案例被整理为同一格式的种子卡，服务于[分层评价契约](2026-11-12-layered-candidate-evaluation.md)的开发回归和后续标注准备。它们不是六个独立测试案例，不是随机样本，也没有新增功能重复真值。

全部绑定提交`7e3ac94431a0dbb376d2fc8d85098deeff1bba09`，均标为development。共13个源码成员，保留函数片段、原文件、字节区间、行号、摘要和配置范围。相同源码谱系作为共同origin group，不能把这批分散到开发与测试后声称独立泛化。

## 种子地图

|种子|要研究的问题|现有证据|当前不能声称|
|---|---|---|---|
|DEV-BLOCK-RANGE|不同读写流程能否共享局部范围规划|范围运算与不同I/O路径的静态观察|读写可整体替换、共享必然有收益|
|DEV-SUPERBLOCK-DELEGATION|相似构造器是否其实已有公共实现|源码直接委托与Infallible适配|已经建立解析调用图、没有任何清理空间|
|DEV-STREAM-COMMAND|流式分块是否破坏完整命令语义|完整请求收集、一次处理器调用等源码证据|这个精确配对已有运行替换验证|
|DEV-CFG-SPINLOCK|相同文档是否掩盖互斥配置|stats/not(stats)属性与smp字段条件|已经验证所有配置构建、跨配置不能共享|
|DEV-DOC-PARAMETER-ROLE|文档相似能否区分修改/保留角色|权限与类型字段操作、原始文档|词袋相同意味着可互换、两者毫无共性|
|DEV-ALIGNMENT-DOMAIN|同一算术机制的输入域和错误契约|已执行的有限域测试、非法参数反例|全域等价、内核集成安全或性能收益|

## 每张卡的具体边界

### 1. 局部共享，而非整体替换

`DEV-BLOCK-RANGE`对应旧SCC配对735/736：`fs/kvfs/src/node/device.rs:487`的`read_block_device`与`:537`的`write_block_device`。两者有范围裁剪、非对齐分段的共性；写入还涉及读改写和错误/完成量语义。

可探索的是纯范围规划边界。后续控制应检查空请求、越界、只读、边界读改写与快路径调用次数。本轮只打包已有证据，没有执行这些新控制，也不重开通用短写缺陷研究。依据：[块设备审阅](2026-11-06-block-io-review.md)。

### 2. 已有委托，不是两份引擎

`DEV-SUPERBLOCK-DELEGATION`对应1348/1349：`fs/kvfs/src/super_block.rs:705`的`new_with_flags_and_private`和`:743`的`try_new_with_flags_and_private`。不可失败包装通过Infallible适配闭包并调用可失败版本，初始化/注册机制已有公共实现。

该种子约束“长签名和参数传递相似⇒独立重复算法”的过度推断。源码直接调用可观察，但本轮未做类型解析或运行追踪；也不据此禁止包装层整理。依据：[SCC首批审阅](2026-11-05-scc-first-review.md)。

### 3. 分块流与完整命令

`DEV-STREAM-COMMAND`对应125/1249：`fs/kvfs/src/file.rs:446`的`scalar_write_iter`与`fs/kvfs/src/simple_file.rs:87`的`write_iter`。后者限制完整请求大小，先收集再调用处理器；回调次数、请求内容和失败时迭代器回退是需要保留的契约。

困难情境是将一次完整命令错误地拆成多次分块回调。此前其他SimpleFile/CommandFile夹具不是这个精确配对的执行证据，因此本卡明确标为待构造测试，而不是“反例已跑过”。

### 4. 配置条件是输入的一部分

`DEV-CFG-SPINLOCK`来自文档队列第1对：`task/kspin/src/lock.rs:80`与`:92`两个`new`。函数属性分别是`not(feature="stats")`和`feature="stats"`，stats版本已有`new_with_stats`委托；另有`smp`条件字段。

卡中保留函数、祖先、文件属性及完整源文件，不仅截取正文。当前未求值cfg，也未构建stats×smp矩阵。源码互斥与实际编译成员身份分开；不把互斥当成“绝无共享价值”的负标签。

### 5. 文档词相同，参数角色不同

`DEV-DOC-PARAMETER-ROLE`来自文档队列第6对：`fs/kvfs/src/types.rs:146`的`with_permission`保留类型、替换权限；`:151`的`with_node_type`保留权限、替换类型。原文档和函数体均归档。

该对用于检验表示是否保留“改变什么/保留什么”的关系，而非否定局部位域机制共享。两个文档种子的成员均低于旧SCC的65-token门槛，所以不能把它们不在SCC结果中解释成语义漏检。依据：[文档候选审阅](2026-11-09-doc-tfidf-review.md)。

### 6. 同机制，前置条件并不相同

`DEV-ALIGNMENT-DOMAIN`包括三个`align_up`：`arch/kcpu_slot/src/dynamic.rs:267`、`boot/kernel-elf-loader/src/lib.rs:228`、`xtask/xkmake/src/image_metadata.rs:426`。CPU为debug断言，boot为显式非法输入错误，host没有相同守卫，整数类型也须区分。

沿用上一批复跑证据：输入(17,3)时boot拒绝，而无守卫core算术返回Some(18)。debug/release有限采样测试与5目标metadata编译不证明全域等价，更不说明运行时性能。卡引用完整报告，但不把该报告赋予其他种子。依据：[对齐契约](2026-11-05-alignment-core-contract.md)。

## 机器记录与验证

选择清单：`research/protocols/rust-development-seeds-v1.json`。打包器` scripts/package_rust_development_seeds.py`从原始源码归档、固定候选队列和alignment运行记录绑定成员，不读取当前HEAD替换历史输入。

批次目录为`research/evidence/runs/2026-11-12-rust-seeds-01/`。每个种子子目录有`card.json`及`*-source.rs`、`*-unit.rs`；顶层保留选择协议、构建脚本、输入摘要、工件摘要及校验报告。字节区间采用原文件字节偏移，结束位置不包含在内；行号保留源提取口径。

验证实际通过：6张卡、13个成员的源码/片段摘要和区间绑定；9项拒绝控制覆盖测试集升级、真值升级、收益升级、伪独立审查、缺失配置、重复成员、错误区间、伪编译成员与源码篡改。它们只证明记录一致性，不证明关系判断正确。

静态复核意见另存`source-review.txt`，复核者没有执行新测试或独立标注。六张卡的relation_label仍为unknown，收益仍为unverified；静态观察、已执行有限反例与待执行控制分别标记。

```sh
python3 scripts/package_rust_development_seeds.py --run-id 新批次ID
python3 scripts/check_rust_development_seeds.py 新批次ID
```

## 后续执行顺序

先从参数角色种子建立字段保持断言，验证文档表示丢失角色的可观测后果；随后补配置成员证据。它们能约束后续文档视角实验，成本和范围也比直接生成重构补丁更清楚。

对完整命令种子，只有建立精确配对的事件轨迹后才计为执行反例。局部范围共享与构造器委托保留为静态开发种子，避免为凑平衡数据而强行赋标签。职责归属是另一个有向任务，本批没有独立架构规范，故没有把设备树历史迁移硬塞进功能配对标签。
