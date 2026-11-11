# R008：用core能力替代局部算术的最小实验

## 决策结果

项目固定提交`7e3ac94431a0dbb376d2fc8d85098deeff1bba09`的`rust-toolchain.toml`指定Rust 1.95.0。
本机同版本rust-src确认`checked_next_multiple_of`是core整数方法，普通与const API从1.73.0稳定。
不需要std、增加公共crate、改feature或进行usize/u64转换，就有一条可实验的复用路线。

**当前升级为“已有最小适配且局部验证通过”的候选，不是已验证净收益的优化正例。**
补丁只保存在研究证据中，未应用到内核。它替换三个私有函数的算术表达式，保留原函数边界、debug assertion、boot输入校验及错误字符串。
保留这些很短的包装并不等于仍在独立实现算法：它们承担局部输入约束和错误适配，实际取整委托core。

## 适用域

[契约核查及数学推导](2026-11-05-alignment-core-contract.md)说明：同一无符号类型、非零二次幂align下，原checked-add加掩码与core方法的成功值和溢出边界相同。
这个推导由研究者给出，未经过形式验证或独立人工评审。

此前调用核查表明，cpu路径用类型对齐，host两处生产调用用4，boot已读调用用0x1000。
core还支持非二次幂，因此**不能删除boot的非法输入检查**；cpu/host对违反前提输入的行为不在等价承诺内。
不使用`u64 as usize`规避类型问题，两种类型各自调用对应方法。

## 可复跑实验

入口：`scripts/run_alignment_core_probe.py`；固定测试模板：`research/tools/alignment-core-tests.rs.in`。

```sh
python3 scripts/run_alignment_core_probe.py --repo /root/codes/x-kernel \
  --run-id alignment-core-new-run
```

要求本机1.95.0工具链、所列目标core组件及现有隔离辅助环境；run-id必须未使用。
脚本从固定git版本抽取三函数，原始片段另存；生成候选时只替换一次匹配的算术表达式。
测试封装将函数可见性提升为pub(crate)以便调用，算法未做其他改写。使用独立namespace运行host测试。
保存编译器身份、项目工具链声明、core源文件、原函数、候选、完整原文件、研究补丁、命令和日志；报告记录工件SHA256。

| 检查 | 实际结果 | 边界 |
| --- | --- | --- |
| host debug | 四项通过 | x86_64 host；不是完整crate测试 |
| host release（-O） | 四项通过 | 不把测试耗时当性能基准 |
| 非零二次幂域对照 | usize与u64全部可表示二次幂；值取0–4095、MAX附近、最大可对齐值附近 | 有限取样，不是遍历64位值域 |
| boot非法输入与溢出错误 | 指定零及非二次幂输入保留invalid alignment；MAX按4溢出保留原错误 | 不是完整ELF解析验证 |
| 无校验core差异对照 | 17按3返回18，而boot拒绝 | 支持保留校验，不是删除校验后的变异测试 |
| 五个目标no_std检查 | x86_64-none、x86_64-uefi、riscv64gc-none、aarch64-none-softfloat、loongarch64-none-softfloat均成功 | 只生成metadata，不是链接、运行或完整机器码验证 |

编译日志中的dead_code告警来自仅用于编译核查的包装模块，已保留，不当作完整项目无警告声明。
实验目录：`research/evidence/runs/2026-11-05-alignment-core-01/`，`candidate.patch`是待评价方案而非已合入改动。

## 收益与风险

可以直接看到的结构变化：三处手写掩码取整改为标准方法；不增加库依赖、公共接口或整数转换；boot仍保留领域错误。
潜在维护收益是减少本地实现算术机制，而不是必须把三个包装函数再合成一个泛型库。
可读性与长期维护收益尚未获得独立评价，不能用删行量替代。

**主要未决风险是代码生成。** core源码使用余数运算，原算法使用加法和掩码；这不证明最终会产生除法，也不证明优化器一定消除它。
host常量4、boot常量0x1000与cpu类型对齐实例应分别看待。通用动态align函数也应单独比较，不能用常量场景代替。
五个目标的metadata编译只证明API类型可用，不能消除该风险。

下一步对原实现与候选在同一编译器、优化参数下比较常量与动态输入的生成代码，再决定是否值得做实际crate补丁及性能测量。
若动态路径出现额外成本，允许只改兼容的常量路径，或保留原实现；不为了得到“优化成功”而放宽性能要求。
本轮没有证明检测器自动发现能力、全仓召回率、实际运行性能或创新性。
