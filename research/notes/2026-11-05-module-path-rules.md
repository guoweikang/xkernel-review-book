# 模块文件候选：官方路径规则边界

2026-11-05 定向浏览三份官方页面，未读实现代码、未构建或执行路径样例。本轮评估对象是用户描述的 conservative file-local candidates，不是对其实现的测试。结论：可作为条件化的文件候选映射；**找到文件不等于确认 cfg 生效、模块加载或逻辑 crate 归属**。

## 自定义 crate root 名称

Cargo target 的 `path` 指定相对 `Cargo.toml` 的 crate 源文件；`lib.rs`／`main.rs` 只是惯例而非根模块文件名的必要条件。因此 `src/entry.rs` 也可以是配置指定的 root。来源：[Cargo Book — The path field](https://doc.rust-lang.org/cargo/reference/cargo-targets.html#the-path-field)。Reference 将源文件在模块树中的位置定义为来自文件外部，并说明编译器以一个源文件为入口。仅凭本地文件名无法还原其加载身份。来源：[Crates and source files — crate.input-source / crate.module-def](https://doc.rust-lang.org/reference/crates-and-source-files.html#r-crate.module-def)。

## 三个易混淆的路径规则

- 默认 `mod util;` 的 `util.rs` 与 `util/mod.rs` 是互斥选择；两者都有时不能任取一个。来源：[Modules — search-mod](https://doc.rust-lang.org/reference/items/modules.html#r-items.mod.outlined.search-mod)。
- 非内联模块块内的 `#[path = "foo.rs"] mod c;` 相对声明所在源文件的目录，不额外加该文件 stem。来源：[Modules — path.search](https://doc.rust-lang.org/reference/items/modules.html#r-items.mod.outlined.path.search)。
- 内联模块内的 `path` 不同：官方例 `mod inline { #[path = "other.rs"] mod inner; }` 位于普通 `src/a/b.rs` 时加载 `src/a/b/inline/other.rs`；位于 `src/a/mod.rs` 时加载 `src/a/inline/other.rs`。root modules 也属于这里的 mod-rs 类别，不限文件名。内联祖先自身的 `path` 又会改变目录基准。来源：[Modules — path.search-nested（含祖先 path 示例）](https://doc.rust-lang.org/reference/items/modules.html#r-items.mod.outlined.path.search-nested)。

## 对固定流程的建议（规则应用推导，不是实测）

将文件角色记录为假设：默认 root／mod-rs／普通非 root／未知。不要把所有非 `lib.rs`、`main.rs`、`mod.rs` 文件直接确认为 non-mod-rs；若缺少入口证据，自定义 root 应标记 `root-role-unverified`，不能用错误基准静默给出唯一候选。例如 `entry.rs` 若是 root，其普通内联模块基准与“同名普通子模块文件”不同。对通过重命名 `path` 引用的源文件，也不应仅靠 stem 推断逻辑模块名。

默认双路径都存在时，记录 `candidate-conflict` 并保留两条路径；这是条件化冲突，不是在未求值 cfg 的情况下宣布实际编译必然失败。显式 `path` 的候选不应再叠加默认双路径作为同等加载选择。零候选表示本次扫描未找到，一候选也仍只表示文件级匹配，不表示编译归属确认。

维持用户当前暂缓范围：内联祖先 `path`、`cfg_attr`、函数内模块；如内联块内的叶子 `#[path]` 未实现，应显式暂缓，不能套顶层规则。普通内联嵌套规则的应用也必须携带上述文件角色假设。宏生成声明、配置选择、非标准构建入口及递归加载上下文均未由本轮核实；不声称映射覆盖完整 crate 模块树。

## 实际查阅范围

直接打开上述三个官方 URL；Modules 阅读 `Module source filenames` 与 `The path attribute`，Crates 阅读入口及模块身份条款，Cargo Targets 阅读 target 配置及 `path` 字段。无搜索引擎查询、无新增仓库案例、无代码修改；当前在线文档未固定到项目具体 Rust 工具链版本。
