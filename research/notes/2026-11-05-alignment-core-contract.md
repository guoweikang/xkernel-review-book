# R008：Rust 1.95 checked 对齐契约

读取日期：2026-11-05。只读本机 `/root/.rustup/toolchains/1.95.0-x86_64-unknown-linux-gnu/lib/rustlib/src/rust/library/core/src/` 下的官方 rust-src；未执行 Rust 代码、编译、测试或性能实验，未修改内核。以下行号相对此目录。核查对象为 API 与数学性质，不代替主线程对抽取函数及其调用前置条件的核对。

## 版本及 API 语义：源码直接证据

`num/uint_macros.rs:3698–3720` 定义 `checked_next_multiple_of(self, rhs) -> Option<Self>`：求不小于 self 的最小 rhs 倍数；rhs 为零或结果溢出时为 None，已是倍数则原值返回。实现先 `checked_rem`，余数为零返回 `Some(self)`，否则 `checked_add(rhs - remainder)`。`checked_rem` 在 `:1449–1455` 明确对零除数返回 None。

`:3710–3711` 的稳定性属性同时声明普通 API 和 const API **自 Rust 1.73.0 稳定**，所以不是 1.95 新增功能。此宏也用于 `u64`、`usize`（`num/mod.rs:1273`、`:1337` 起）。可定位的固定官方源码为 [Rust 1.95.0 uint_macros.rs](https://github.com/rust-lang/rust/blob/1.95.0/library/core/src/num/uint_macros.rs#L3698)；本轮实际读取的是上述本机版本目录，未另验安装包哈希。尝试打开官方 [1.95.0 u64 文档](https://doc.rust-lang.org/1.95.0/core/primitive.u64.html#method.checked_next_multiple_of)及 [usize 文档](https://doc.rust-lang.org/1.95.0/core/primitive.usize.html)时浏览工具均返回不可访问，故在线页面未构成额外验证，不用浮动 stable 文档代替。

## 条件等价证明：非零、可表示的二次幂

设同一无符号整数类型宽度为 w，最大值 M=2^w−1；输入 x∈[0,M]，对齐 a=2^k，0≤k<w。比较表达式 `x.checked_add(a - 1).map(|sum| sum & !(a - 1))` 与 `x.checked_next_multiple_of(a)`，所有操作均使用同一类型。

1. 在无溢出的整数算术中，a−1 恰好为低 k 位全 1，清除这些位等价于向下取到 a 的倍数。因此 `(x+a−1) & !(a−1) = a × floor((x+a−1)/a) = a × ceil(x/a)`，正是不小于 x 的最小 a 倍数。
2. 该类型内最大的 a 倍数为 L=2^w−a=M−(a−1)。checked-add 成功当且仅当 x≤L；所需向上倍数可表示也当且仅当 x≤L。因此两式不仅成功值相等，**None 的边界也相同**，不存在“已对齐且合法、仅中间加法溢出”的遗漏。
3. a=1 时掩码为零，所有 x 均返回自身（包括 M）；a>1 时 x=M 返回 None；x=0 对任何上述 a 返回 Some(0)。这些是推导结果，未运行样例。

## 无效对齐与整数宽度：不能扩大等价域

`checked_next_multiple_of` 支持**任意非零倍数**，不要求二次幂。例如数学上 `5.checked_next_multiple_of(3)` 为 Some(6)，但同宽度的加掩码式得到 `(5+2)&!2 = 5`，并非 3 的倍数。若本地函数拒绝非二次幂，应保留该输入检查；直接替换为 core 调用会放宽契约。`is_power_of_two` 的实现为 `count_ones()==1`（`num/uint_macros.rs:3749–3762`），零不满足。

对 a=0，core 返回 None，而原表达式的 `a-1` 本身就可能下溢；后续的 checked-add 并不能保护先前减法。不能声称本地实现对零一定返回 None，除非已核实它先检查输入。以 wrapping 运算、debug/release 溢出策略或仅 debug assertion 代替前置检查，也不在上述证明内。

`primitive_docs.rs:1468` 定义 u64 为 64 位，`:1492–1496` 定义 usize 为指针宽度整数。证明分别适用于各自 w，但 **u64 与 usize 不能在不检查可表示性的情况下互换**：窄 usize 目标上转换可能丢失 x 或 a 的高位，结果／溢出边界随宽度改变。此处 1.95 工具链目录名中的 x86_64 是宿主标识，不能替代内核目标宽度证据；跨类型对照应先验证输入和输出转换，或明确限定相同宽度及值域。

## 对主线程探针的解释边界

可将 core API 作为同类型、非零二次幂输入域的数学对照；另列零、非二次幂和跨类型转换的本地既定行为，不把 core 更宽的输入域误作等价要求。有限样例通过只能说明那些输入吻合，不能替代此证明或确认全部调用者满足前置条件。若本地还包含错误类型、返回形态或附加检查，须另核接口适配。本轮无内核调用链、目标编译、实际探针结果或生成代码证据，也不提出性能收益结论。
