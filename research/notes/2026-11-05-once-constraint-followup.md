# Once 独立实现约束：有限补核

原始文件归档：既有`research/evidence/runs/2026-11-05-rust-pilot-seeds-01/`与`research/evidence/runs/2026-11-05-rust-pilot-context-01/`，新增README及klazy库入口见`research/evidence/runs/2026-11-05-once-constraint-followup-01/`。本次由辅助Agent阅读、主研究者复核关键理由；不是独立人工标注。
首次捕获将重导出锚点误写为`pub use paste::paste;`，脚本拒绝；核对源码后改为`pub use paste as __paste;`再捕获，没有放宽唯一性检查。

2026-11-05。先读 `research/notes/2026-11-05-rust-pilot-context.md`，随后仅以 `git show 7e3ac94431a0dbb376d2fc8d85098deeff1bba09:path` 读取下列九个内核文件的相关段落：xcover 的 `Cargo.toml`、`README.md`、`src/{lib,runtime,sync}.rs`，klazy 的 `Cargo.toml`、`docs/design.md`、`src/{lib,once}.rs`。总计十个内容文件；未 fetch、修改内核、运行测试／构建或做 panic 探针。以下路径行号均属于该固定 SHA，不代表工作树或最新版本。

## 直接依据：有独立意图，但必要性未证实

- **明确意图**：`util/xcover/src/sync.rs:5–11` 明说本地 Once 用于 no_std statics，替代该 crate 对 `spin::Mutex` 或 `klazy` 的需要；`:23–27` 强调 CAS、初始化后的原子读取及不依赖 spin crate。这支持“有意保持本地实现”，**未说明为什么 klazy 不可用**，更不是构建环、插桩重入或代码体积开销的证明。
- **原子后端事实**：`util/xcover/Cargo.toml:14–19` 默认启用 alloc，portable-atomic 关闭默认 features 并请求 require-cas；`util/xcover/src/sync.rs:13–15` 使用它的 `AtomicU8`。对照 `util/klazy/src/once.rs:9–14` 使用 core `AtomicU8`。这只是后端与配置差异，不足以断言 xcover 已支持无原生 CAS 的任意目标；未读取 portable-atomic 实现或实际目标解析结果。
- **klazy 的目标声明更具体**：`util/klazy/docs/design.md:154–158` 明列 x86_64、aarch64、riscv64、loongarch64，声明其 AtomicU8 lock-free，因而不需 polyfill。`:43–58` 声明适用于早期启动、不睡眠、不依赖当前任务，同时要求避免长初始化及同实例递归。这些是设计文档声明；本轮没有目标 triple／target-feature／编译产物或机器验证，不把架构名直接当所有配置均受支持。
- **no_std／自举不能单独成为排除理由**：`util/xcover/src/lib.rs:11` 与 `util/klazy/src/lib.rs:19` 都有 no_std 配置。`util/klazy/src/once.rs:629–631` 更明确说明 boot loaders 无 allocator，且在解析测试宏前以 `cfg(unittest)` 门控。这反驳“klazy 必然要运行时 std／allocator 才能用”的笼统推断，但不能替代完整依赖闭包检查。
- **依赖最小化是目标，不是测得收益**：`util/klazy/Cargo.toml:13–15` 将 paste、unittest 列为普通依赖；`util/klazy/src/lib.rs:21–24` 重导出 paste。`util/klazy/docs/design.md:146–158` 说明 API 控制、发布独立与依赖最小化的动机；`:177–180` 将 paste 描述为编译期宏。不能仅按依赖条目数推断运行时二进制更大，也不能从测试调用门控推断 unittest 不进入构建依赖图。

## 具体调用需求与适用边界

`util/xcover/src/runtime.rs:17–42` 将 `Once<ProfileImage>` 及初始化入口置于 alloc feature 下，以 `get_or_try_init` 初始化、以 `get` 查询；`:61–64` 的记录入口在未初始化时不操作 image。它们支持“发布一次、可失败重试、非阻塞观察”的调用需求。`util/xcover/src/sync.rs:55–66` 与 `util/klazy/src/once.rs:481–496` 均有 Acquire 读取的非阻塞 `get`；因此“初始化后无需互斥锁”不是已证明只能由本地实现提供的差异。并不据此认定全部状态契约可替换。

`util/xcover/README.md:3–15` 声明面向 no_std／embedded、LLVM coverage／PGO；`:19–35` 要求 recent nightly，并提醒插桩 flags 默认也影响 build-dependencies／proc macros，可显式指定 target 区分。它提供了**核对插桩边界的理由**，但没有说引入 klazy 会造成插桩循环或自举失败，也未给出必须依赖 portable-atomic 的完整受支持目标清单。README 的 `x86_64-unknown-linux-gnu` 命令是示例，不是完整支持矩阵。

## 哪些补充证据会改变取舍

不重复主线程证据缺口矩阵，仅列决策杠杆：

1. **具体目标要求**：若维护者给出必须支持、而 core AtomicU8／CAS 不满足的 target 配置，并证实所选 portable-atomic 配置可满足，则反对“直接替换为现状 klazy”；仍可讨论共享可选原子后端的小机制。若真实目标全部满足 klazy 前提，这项后端差异不足以单独保留两份状态机。
2. **依赖／发布／插桩边界**：需要固定目标与 features 下的依赖路径，或明确维护决策说明 xcover 必须独立分发、不得引入内核测试依赖，以及实际插桩配置对应的调用链。证实不可接受的依赖环／插桩重入才构成实质反对依据；目前仅见独立意图，未见决定性禁止规则。拆出更小公共组件是否可行亦尚未证明。
3. **调用契约及收益门槛**：需要维护者确认上述 get／Err 重试／初始化上下文的必要语义，以及现有 panic 策略要求；本轮不以探针替代需求确认。若接口适配与目标约束可保持，才进入直接复用或共享机制比较；若主张独立实现更轻／更快，需可接受的成本预算和同配置证据，而非把“单次原子读取”注释当性能测量。

**结论：在限定九个内核文件内，未取得足以证明“必须独立”或“可以安全直接替换”的决定性证据。** 保留候选、先确认目标与依赖边界，不升级成整改要求、漏洞结论或独立人工标签；本轮也未审计其他历史 ADR／维护者讨论，不能声称仓库其他地方不存在理由。
