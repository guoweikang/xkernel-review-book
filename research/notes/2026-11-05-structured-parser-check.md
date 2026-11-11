# 结构化解析接口验证：syn 的可用范围与拒绝策略

日期：2026-11-05。阶段 A 的解析适配检查，不是重复检测基线或真实案例评价。
承接 [定位探针](2026-11-05-rust-unit-location-probe.md)。

## 1. 验证目标与实现

前一轮 rust-analyzer CLI 输出格式不稳定，且残缺源码也可能成功退出、没有 ERROR 节点。
本轮验证是否能使用结构化接口取得函数/方法/模块/闭包边界，并明确拒绝不能解析的输入。

在 book 内建立独立工具 `research/tools/rust-syntax-probe/`，不改内核，不纳入内核 workspace。
固定 `syn=2.0.119`、`proc-macro2=1.0.107`、`serde_json=1.0.154`，保留 Cargo.lock。
使用本机缓存、Rust 1.95.0 和 `--offline --locked` 构建；未安装依赖或运行内核 build.rs。
独立工具依赖的正常 Cargo 构建步骤会执行，不将这次构建描述成完全没有构建脚本。

探针从 stdin 读取源码，调用 `syn::parse_file`，通过 Visit 接口记录：

- 普通函数、impl 方法、trait 声明/默认方法，以及函数体可选范围；
- 模块是否内联、impl/trait/函数的父级索引、闭包与宏 token 区域；
- item、签名、函数体的 UTF-8 字节范围，保留原始源码，不靠重新打印 token 还原文本；
- `parsed_by_syn` 或 `rejected_by_syn` 状态及诊断；拒绝时不给出可用函数清单。

这里的签名是源码语法签名，不是解析后类型。Signature 范围包括 const/unsafe 等修饰符，
但不包含 pub 可见性和外层 impl/trait 约束；后者要从 item/祖先节点另取。
属性和文档可从 item 范围追溯，当前并未结构化输出全部契约字段。

## 2. 实际验证结果

执行脚本 `scripts/check_syn_probe.py`，结果为
`research/evidence/inventory/2026-11-05-syn-adapter-check.json`。

| 核查项 | 实际结果 | 不能据此声称 |
| --- | --- | --- |
| 上轮 7 个构造输入 | 正常形态按预期提取；残缺函数和错误 let 表达式被拒绝并返回诊断 | 已覆盖全部 Rust 错误或能完整收集所有诊断 |
| 新增 4 个边界输入 | 拒绝宏 token 的不配对括号；接受括号配对但内部不是合法 Rust 函数的宏 token；接受未解析名称；保留 const/unsafe 签名修饰符 | 接受宏 token 等于展开正确，或接受函数等于可编译 |
| Unicode 与同一行函数 | 原始 UTF-8 字节切片取得完整第二个函数 | 字符列可以直接作为字节下标 |
| trait 声明与默认方法 | 无函数体的声明独立标记 | 声明也是可比较的实现代码 |
| klazy 五个固定源文件 | 全部被 syn 接受，共 41 个源码函数/方法；名称多重集与上一轮 RA 结果逐文件一致 | 独立语义真值已确认，或全仓提取准确率达到 100% |
| 字节范围 | 输出的 item/签名/body 范围在文件内且可按 UTF-8 解码 | 每个范围都经过人工逐一确认 |

另外补充 BOM、shebang 和 Verbatim 三个边界输入，合计 14 个构造输入，
它们是解析器验收样例，不是重复功能数据集。
五个文件仍固定为 `7e3ac94431a0dbb376d2fc8d85098deeff1bba09`，与上一轮逐文件哈希一致。
41 个源码函数不等于 44 个 fn facts：前一轮已经确认 3 个派生生成函数没有直接源码定义；
其余 5 个属性宏函数虽然在源码中可见，展开后签名/函数体并不等同原始输入。
本轮没有重做编译事实的语义身份匹配，不将“两个解析器名称一致”当成事实关联已完成。

## 3. 诊断边界和调用约定

工具的进程退出码表示输入输出协议是否成功；源码拒绝也会正常输出 JSON。
调用者必须读 `status`，不能再次只靠退出码接受源码。
失败文件输出空 units，记录错误；后续可以另设不可信词法视图，但不得混入已接受的 AST 单位。

独立源码核查发现 parse_file 会移除 BOM/shebang，可能改变原始字节偏移。
当前适配器对这类前缀保守返回 `unsupported_prefix`、不产出单位；这不是判定源码非法，
而是在尚未实现偏移映射时防止错切源码。两类前缀均有验收输入。
另为顶层 `Item::Verbatim` 保留未细化 token 区域，`fn declaration();` 样例证实不会被静默丢弃。
这尚未穷尽所有节点位置的 Verbatim 变体，不能声称全部未知语法已登记。

`syn::parse_file` 并非 rustc 的完整语言/edition/名称/类型/借用检查器。
宏内部只要求相应 token 结构可解析，不执行宏；cfg 也不求值。
因此采用“被当前版本 syn 接受”的状态名，不用“代码正确”“编译通过”或“完整语法验证”。
接口依据和更细限制见 [syn 接口边界](2026-11-05-syn-interface-boundaries.md)。

## 4. 本轮决策

**选用固定版 syn 探针作为下一轮只读源码单位清单的候选实现，暂不继续解析器选型扩散。**
理由是它已解决当前遇到的 CLI 输出格式依赖和两个具体错误漏报，并提供结构节点和字节范围。
这不是性能优劣比较，也没有证明它优于其他解析器。

下一轮输入清单必须记录：文件哈希、解析状态、拒绝原因、对象种类、精确范围、祖先上下文，
以及 cfg/宏/测试来源；编译事实关联仍另表保留唯一候选、多义、生成和未匹配状态。
先固定这些字段和失败行为，再扩至多个 crate 检查适配，不以增加样本为由提前报告重复检测效果。

当前未解决：外置模块加载与路径覆盖、cfg 生效判断、宏展开、跨 crate 身份、完整契约、运行时性能。
这些缺口分层登记，不能要求全部解决后才发现候选，也不能当作已经实现。

## 5. 复查

在 book 仓库根目录：

```sh
CARGO_TARGET_DIR="$PWD/.build/syn-probe-target" cargo +1.95.0 build \
  --offline --locked --manifest-path research/tools/rust-syntax-probe/Cargo.toml
cargo +1.95.0 fmt --manifest-path research/tools/rust-syntax-probe/Cargo.toml -- --check
python3 scripts/check_syn_probe.py \
  --binary .build/syn-probe-target/debug/rust-syntax-probe \
  --repo /root/codes/x-kernel \
  --prior research/evidence/inventory/2026-11-05-rust-unit-probe.json \
  --output research/evidence/inventory/2026-11-05-syn-adapter-check.json
```

首次格式检查发现一处链式调用排版，修正后通过；重新构建和全部适配检查通过。
Cargo.lock 固定传递依赖；没有相应缓存的环境需要另行准备依赖，不能承诺直接离线复现。
输出保存本次二进制哈希及依赖版本，二进制哈希不保证不同机器或构建路径间相同。
