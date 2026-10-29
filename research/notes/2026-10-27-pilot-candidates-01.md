# 首批真实案例候选：Once 与 RTC

状态更正（2026-10-27）：用户要求严格先完成基础调研。本笔记封存为提前产生的
探索材料，不计为阶段 B 已启动或正式试点数据；当前不继续扩充或验证。

日期：2026-10-27。阶段 A/B 第一批取证；只读源码，不是重复问题判决或重构建议。
固定仓库版本：`43b5f35d4a7bc6a0fa766d4fd3654844bb66e028`。
两个候选组均未完成维护者标注、配置构建、行为验证或性能测量，标签为 `unlabelled`。
当前工作树无已跟踪代码修改；以下位置以该 commit 为准，不依赖未来行号不变。

## 采样方式与局限

本轮在 `util/`、`drivers/` 手工搜索初始化、队列、资源释放等符号，再阅读相关实现、
调用方、Cargo 依赖、设计文档及测试。保留两个便于核查的候选，而不是挑选已知正例。

主要命令：

```sh
rg -n 'struct .*Ring|struct .*Queue|fn align_up|fn align_down|impl.*Drop for' util drivers
rg -n 'Once|try_call_once|get_or_try_init|mod sync' util/xcover/src util/xcover/tests
rg -n 'fn (get|try_call_once|try_call_once_slow)|PanicGuard|Status::Failed' util/klazy/src/once.rs
rg -n 'unsigned_seconds|mapped|goldfish|pl031' drivers/platform/rtc/ut-tests/lib.rs
git log -4 --format='%h %s' -- util/xcover/src/sync.rs drivers/platform/rtc/src/lib.rs
```

这是便利采样，偏向具名且容易定位的实现；不能据此估计仓库重复比例、召回率或自然基率。
测试中多个 Drop 探针未纳入本批，因尚未判断测试局部隔离需求；不是已证明不值得抽象。
下一批必须补充低文本相似、多实体组合及跨配置案例，避免只研究小函数对。

## C001：xcover::Once 与 klazy::Once

### 已观察事实

- `util/xcover/src/sync.rs:28` 定义 crate 私有 `Once<T>`；`get` 在 READY 时返回共享引用，
  `get_or_try_init` 提供可失败初始化；失败返回 Err 时重置状态，初始化竞争时自旋。
- `util/klazy/src/once.rs:48` 定义公共 `Once<T>`，`try_call_once` 在第 242 行；
  存储、发布和失败重试存在对应机制，但公共 API 更广，不是完全相同实现。
- `util/xcover/src/runtime.rs:24` 的 `RUNTIME_IMAGE` 使用前者，`image_or_init`、
  `has_image`、`record_value` 等调用体现真实需求；这些调用位于 `alloc` 配置下。
- xcover 使用 `portable_atomic::AtomicU8`；klazy 使用 `core::sync::atomic::AtomicU8`。
  前者 Cargo 直接依赖 portable-atomic 并要求 CAS；后者声明 paste、unittest 依赖。
  这些是依赖声明差异，不是已测得的体积或运行开销。
- klazy 的慢路径建立 `PanicGuard`，其析构写入 Failed 状态；xcover 文件中有 POISONED
  常量及匹配分支，但本次读到的实现没有写入 POISONED 的路径或相应 guard。
  文档中的 poisoning 声明不能直接当作已实现事实。该差异在实际 panic 策略下的影响
  尚未测试；本批不扩展为 bug 修复，也不声称两者行为等价。

### 为什么纳入

能测试“职责与主要状态转换相似，但依赖和边界行为未对齐”的情况。
单靠类型名字、模块摘要或成功路径，很容易过早给出直接替换建议。

### 尚待判定

1. xcover 是否有独立发布、可移植目标、覆盖率自举/插桩等必须维持的限制？
   文件注释写明替代 spin/klazy 的意图，但没有据此推断完整设计理由。
2. 需求要求怎样的 panic、重入与并发初始化语义？实际支持哪些配置和原子能力？
3. 若保留独立实现，原因是必需约束还是当前依赖布局？公共底层或局部适配是否更合理？
4. 复用成本应包含公共 API、依赖、构建和测试变化，不能只数删除行数。

### 待比较方案与验证义务

比较保持现状、适配 klazy API、提取更小公共机制三条路线，不预选赢家。
覆盖成功发布、Err 后重试、并发竞争、非阻塞 get、析构次数以及适用 panic 策略。
`util/klazy/tests/host/once_host.rs` 已有 panic、重试、并发和 Drop 相关测试；
尚未核实 xcover 的等效测试覆盖，也未运行任何测试。
在提出替换前，须取得维护者需求判断和依赖/目标可行性证据。

## C002：Goldfish 与 PL031 RTC 采样包装

### 已观察事实

- `drivers/platform/rtc/src/goldfish.rs:7` 与 `drivers/platform/rtc/src/pl031.rs:8` 均有 `read_mapped`：
  检查空地址、调用具体设备读取时间戳、转换为 `SystemTime`。
- 具体设备构造方式不同：PL031 包装中包含有前提说明的 unsafe 构造和 u32→u64 转换；
  Goldfish 包装使用另一库的构造及读取接口。本轮未核对外部依赖内部的寄存器语义。
- 时间范围校验已经公共化：`drivers/platform/rtc/src/lib.rs:51` 的
  `system_time_from_unsigned_seconds` 被两者使用，另有 CMOS 调用及配置条件。
- 同文件通过 `RtcKind`、`RtcTransport`、`RtcConfig` 统一配置与分发；
  `read` 中的 backend 选择受 feature/target 条件控制。
- `drivers/platform/rtc/docs/design.md` 明确采样与时间管理职责分离，以及早期启动使用方式。
  `ut-tests/lib.rs:10` 覆盖 unsigned 秒数越界拒绝；这不证明 MMIO 访问正确性。
- `platforms/kplat-riscv64/Cargo.toml:13` 和 `platforms/kplat-aarch64/Cargo.toml:19`
  分别转发 Goldfish/PL031 feature；本轮未完整追踪 Kconfig 到 kfeat 到平台的所有组合。

### 为什么纳入

用于检验“已经有适度公共抽象，剩余相似代码是否还值得合并”。
不能看到同名函数就建议抽取整个 backend，也不能忽略既有公共 helper 再生成一套。
这是保留差异的候选案例，尚不是已标注负例。

### 尚待判定与验证义务

比较保持两个小包装、局部公共 helper、泛型/trait 化采样接口；
判断后两者是否真的减少共同维护负担，还是只把设备差异搬进更复杂接口。
约束包括有效映射、unsafe 前提、数据宽度、时间戳有效范围、配置可达性与依赖边界。
若试验抽象，需分别验证目标配置、范围检查、设备读取顺序及调用方行为；
真实 MMIO 语义需外部库源码、QEMU/硬件或合适模型支持，不能靠整数单测推断。

## 可复核的源对象

以下 Git blob 来自 `git ls-files -s`，与本轮固定 commit 的对象一致；
后续用 `git show <commit>:<path>` 还原原文。哈希不是标注或正确性证明。

| 文件 | blob |
| --- | --- |
| `util/xcover/src/sync.rs` | `c3a7acb8ff1c470a88955d4f0c8958961bb14a72` |
| `util/xcover/src/runtime.rs` | `4be59b3d98eb0bcb82177c5c92f39b934301e9fe` |
| `util/klazy/src/once.rs` | `7818fd75f271897d2ef51fab045a9887288ccfd9` |
| `drivers/platform/rtc/src/lib.rs` | `f6a81485182562d34b08fd2703ce264532c22ce5` |
| `drivers/platform/rtc/src/goldfish.rs` | `2a5b718118f37c0fefd6ff8111bc670b855f12c0` |
| `drivers/platform/rtc/src/pl031.rs` | `7ab417832fb3ca05cd1440312bd4a98508eab0e2` |

## 下一步取证模板

后续每个候选组沿用：ID/版本/来源 → 实现集合及职责 → 已有公共抽象 → 共同与差异事实
→ 文档声明和冲突 → 配置/依赖/执行上下文 → 未决需求 → 备选方案 → 验证义务
→ 独立标注/仲裁结果及理由。未验证的性能和维护收益统一写 unknown。

本批尚无 gold label、有效优化数或方法效果数据。首先补足两组的边界证据，
同时按研究计划补齐更复杂样例；不能把这两组静态阅读包装成全仓重复检查结果。
