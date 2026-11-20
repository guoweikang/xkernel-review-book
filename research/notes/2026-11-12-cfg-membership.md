# 配置成员确认：互斥构造器与真实特性闭包

## 研究问题

文档发现队列第一对是两个同文档的`SpinLock::new`。要确认的命题不是笼统的“重复吗”，而是：两个实现是否在同一次crate编译中存在？是否已有委托？跨配置是否仍有可共享机制？这三个命题需要不同证据。

本轮固定xkernel提交`7e3ac94431a0dbb376d2fc8d85098deeff1bba09`，不修改生产代码。对应开发种子`DEV-CFG-SPINLOCK`；原卡片保留当时证据状态，不追写成已完成全项目配置验证。

## 理论依据和源码谓词

[Rust Reference条件编译](https://doc.rust-lang.org/reference/conditional-compilation.html)定义`cfg`谓词、`not`以及空`all()`为真、空`any()`为假；`--cfg`可指定配置项。本轮只用这些既有语义，不使用该滚动文档中新加入的其他语法。实际编译器固定Rust 1.95.0，完整版本在manifest。

固定源码`task/kspin/src/lock.rs:79`为`not(feature="stats")`，`:91`为`feature="stats"`。若记统计特性为S，则两个成员谓词分别为¬S和S，合取恒假，析取恒真。这个局部互斥结论不依赖完整Kconfig求解；但某个配置赋值能否在真实工程中达到，另需特性闭包证据。

## 冻结实验和执行结果

协议`research/protocols/cfg-membership-v1.json`先于运行冻结：从原文件原样抽取`SpinLock`结构及第一个完整impl，保留构造器、`new_with_stats`和`into_inner`。使用显式本地`BaseGuard`与`klockstat`类型桩，以std提供对应基础类型；不抽取锁操作、注册机制或真实依赖图。这是成员选择夹具，不是完整kspin编译。

枚举stats×smp四种布尔赋值。原版、同时启用两构造器、同时禁用两构造器三变体，各重复两次，共24次编译。变体只替换两个`new`前的条件为`all()`或`any()`；`new_with_stats`仍保留原条件。

|条件|每次重复的四种赋值结果|两次合计|
|---|---|---:|
|原始条件|全部编译且执行通过|8次执行通过|
|同时启用|全部出现E0592重复定义|8次预期编译失败|
|同时禁用|全部出现E0599缺少new|8次预期编译失败|

执行断言检查值42可取回，smp开启时初始原子flag为false，stats开启时统计引用指向桩的NOOP_CLASS。这些断言不测试统计实现、并发安全或性能。两轮结果类别相同；不要求含临时路径的编译日志逐字节相同。

同时启用且stats关闭的变体还可能产生缺少`new_with_stats`错误，不能宣称失败只有单一原因；全部日志保留，E0592本身是重复成员控制的观察证据。摘要、抽取片段、配置覆盖、24次结果和预期失败码由独立检查脚本复核。

## 项目特性来源：静态证据不等于闭包已解析

以下均来自同一固定提交，并由并行代理只读复核，非独立人工标签：

|来源|观察|
|---|---|
|`Kconfig:384`、`task/ktask/Kconfig.diagnostics:56`|引入并定义KFEAT_LOCK_STAT；debug默认开启，不是release禁止开启|
|`xtask/xconfig/src/build_config.rs:343`、`xtask/xkmake/src/build.rs:388`|y值KFEAT符号转小写feature，并加kfeat前缀|
|`api/kfeat/Cargo.toml:188`|lock_stat开启kspin/stats，还涉及pagecache、procfs、ksync|
|`task/kspin/Cargo.toml:18`|stats启用klockstat、linkme及klockstat/stats；默认特性为空|
|`api/kfeat/Cargo.toml:31`、`:92`|smp向kspin等转发；aarch64、x86_64、riscv64平台feature包含smp|
|`process/kprocess/Cargo.toml:53`、`sync/krcu/crates/krcu-core/Cargo.toml:20`、`util/krcu-list/Cargo.toml:20`、`util/kxarray/Cargo.toml:21`|其他依赖声明也直接请求kspin/smp|

因此不能从某个平台feature没有显式smp，或NR_CPUS设为1，就推出最终kspin/smp关闭。是否激活这些依赖、解析到哪个crate实例、目标及构建种类仍需完整上下文。这里没有执行Cargo特性闭包解析，也没有验证四种赋值对应四个有效的完整内核配置。未将发现的额外边定性为规则违规，规则适用性是另一项检查。

## 对确认模型的影响

- **同配置独立实现：**本例两个new互斥；不能以源文件出现两次就判同配置重复实现。
- **已有委托：**stats版本调用`new_with_stats`，已有局部复用，不是两份完全独立初始化引擎。
- **跨配置共享：**互斥不排除抽取公共初始化；是否值得抽取仍未知，不直接过滤掉候选。
- **文档相似：**相同描述没有告诉我们成员谓词，[词序实验](2026-11-12-document-word-order.md)也未解决这个缺口。配置证据补充的是不同维度，不应压成另一个任意相似度权重。

全局“重复”和优化收益标签仍unknown。局部成员互斥命题已有语言语义、原源码和有限编译控制三层证据；不把这三层当作三个独立统计样本。

## 后续研究决策

下一批优先把六组开发种子的确认命题拆开，逐项登记成立、被反例否定或未知及其证据。配置例已说明需要区分“同配置并存”和“跨配置共享”；角色例则需要区分“可互换”和“共享局部机制”。先固化这个可复核契约，再制作独立标签协议，不能给六个案例随意赋一个重复分数。

完整特性闭包是后续真实配置验证的必要输入，但不是证明本例S与¬S互斥的前提。本轮不为该已确定命题扩张到完整内核构建；当研究跨配置共享候选或目标可达性时，再要求具体配置、Cargo解析图与编译结果。

## 归档与复现

```sh
python3 scripts/run_cfg_membership.py --repo /root/codes/x-kernel --run-id 新批次ID
python3 scripts/check_cfg_membership.py --run-id 新批次ID
```

主批次`research/evidence/runs/2026-11-12-cfg-membership-01`包含冻结协议、执行器、源码、夹具、每条命令、日志与摘要。追加静态来源在`research/evidence/runs/2026-11-12-cfg-lineage-01`，独立manifest注明非已解析特性图，不改写主批次。临时可执行文件不归档；可从源码与固定工具链重新生成。该脚本是本例专用实验工具，不是通用Rust cfg解析器或完整检测器。
