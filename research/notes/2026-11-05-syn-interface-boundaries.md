# syn 离线结构解析接口边界核查

本轮仅直接阅读本机缓存 `syn 2.0.119`、`proc-macro2 1.0.107` 的源码及随源码文档；未执行解析器、构建 kernel、安装依赖或做性能实验，未复核用户探针的样例结果。下文 `syn/`、`pm2/` 分别指 `/root/.cargo/registry/src/rsproxy.cn-e3de039b2554c837/syn-2.0.119/`、同目录下的 `proc-macro2-1.0.107/`。版本与作者仓库见各自 `Cargo.toml:16`，仓库字段分别在 `:45`、`:36`：[syn](https://github.com/dtolnay/syn)、[proc-macro2](https://github.com/dtolnay/proc-macro2)。URL 仅为源码声明的上游入口，本轮未在线核对，也未校验缓存包校验和。

## 1. parse_file 成功不是 rustc 验证成功

`syn/src/lib.rs:992–1015` 的 `parse_file` 预处理后调用 `parse_str`；`syn/src/parse.rs:1268–1269` 先将字符串词法化为 `TokenStream`，`:1293–1304` 调用指定解析器并检查未消费 token。`syn/src/file.rs:97–109` 顺序读取属性和 item，错误经 `?` 返回。因此它提供的是 **该版本 syn 的文件结构解析结果或解析错误**，不是 rustc 完整语法诊断、错误恢复清单，也不做名称解析、类型检查、借用检查或目标配置下的可编译性证明。不能把一次 `Err` 等同于文件内全部错误已枚举，也不能把 `Ok(File)` 等同于所有内容都有细化 AST：例如 `syn/src/item.rs:961–966` 对分号结尾的函数签名保留为 `Item::Verbatim`，`:988–1009` 另有保留 token 的分支。只遍历 `Item::Fn` 不足以宣称已覆盖所有函数相关结构；应另外记录 `Verbatim`／未分类区域。

## 2. 位置：字节范围与 Unicode 列不是同一单位

`pm2/src/lib.rs:469–511` 明确 `byte_range`、`start`、`end` 需要 `span-locations`；独立程序中位置可在任意工具链上准确提供，而实际 procedural macro 内的稳定工具链存在编译器位置信息限制。**不能将后者直接套用到本次离线字符串解析。** `pm2/src/location.rs:8–14` 定义行号从 1 开始、列从 0 开始，列按 UTF-8 字符计；实际 `pm2/src/fallback.rs:435–446` 使用 `str::chars()` 计数，所以是 Unicode scalar value 数，不是 UTF-8 字节数、UTF-16 code unit 数、字形簇数或终端显示宽度。多字节字符的列不可直接当字符串字节下标，组合字符与制表符也不可按视觉宽度解释。

`pm2/src/fallback.rs:377–402` 将内部字符位置映射回字节，返回半开区间 `start..end`；`:559–570` 还表明 call-site 等合成位置可返回 `0..0`。因此“启用 feature”并不使任意手工构造节点的 span 自动成为有效原文定位。另有容易忽略的 **输入预处理偏移**：`syn/src/lib.rs:995–1010` 去除初始 BOM，并将 shebang 前缀切掉（有换行时保留从换行开始的剩余字符串），`:1013` 才解析。由实现可推导，位置对应处理后的输入，而不保证对应原始文件的字节偏移；BOM 本身占 3 字节，shebang 也会造成前缀偏移。直接切原文件前须保留这层映射，不能仅凭行号相近认定字节定位正确。此处是源码推导，本轮未运行边界样例。

## 3. 宏、cfg 与外置模块的可见边界

`syn/src/mac.rs:14–22` 将宏调用表示为路径、叹号、定界符及 `TokenStream`，`:180–193` 读取定界 token 内容，而不执行宏。**宏内部 token 树可被接受，不表示 matcher/transcriber、实参匹配或展开后的 Rust 正确。** 在 token 内出现的 `fn` 不是自动获得的源码 `ItemFn`；attribute／derive 宏也不会由 `parse_file` 执行，解析到的签名不保证就是编译后签名，宏生成函数不在该未展开 AST 的完整覆盖承诺内。

`syn/src/attr.rs:177–182` 保存属性的 `Meta`，文件解析循环没有 cfg 求值过程（`syn/src/file.rs:97–109`）。因此 `cfg`／`cfg_attr` 是待解释的源码属性，不是当前 target、features、测试模式下的启用结论；不能把解析出的所有函数都计作本次编译的有效函数，亦不能假定 cfg 禁用内容会被 syn 自动跳过。`syn/src/item.rs:1794–1835` 对 `mod name;` 返回 `content: None`，仅对内联模块递归读取 items；它不据文件系统或 `#[path]` 自动加载外置模块。外置文件、宏展开与配置选择均需独立覆盖说明。

## 4. 对候选定位报告的建议与未验证项

用户本轮另行报告：本地 11 个 fixtures 与 5 个文件验证通过；syn 拒绝 `fn broken( {` 和 `let value=;`，接受定界平衡但含未知 token 的宏，以及使用 `Unknown` 类型、调用 `absent` 的源码；41 个源码函数名称的多重集与 RA 一致。本次独立核查未重跑这些验证，该结果按用户提供记录。可将探针定为**下轮只读源码单位清单的候选实现**；这些样例与名称多重集一致性不证明完整诊断、区间一致性、配置有效性或宏展开语义正确。尤其 `byte_range` 是字节半开区间，而 `start/end` 的列是 Unicode scalar value 计数，两者不能互换。

建议把输出称为“指定文件集合上的未展开源码结构候选”，分开记录源文件／输入摘要、预处理映射、节点种类、名称 span 与节点 span、字节半开范围、属性和宏上下文，以及外置模块／Verbatim 待解析项。与编译器 facts 的区间相交只支持建立待核对关联，不证明一一对应、语义等价或候选功能重复；无生成标志也不能仅凭 syn 结果排除 attribute 宏改变代码。以上是基于接口边界的使用建议，不是已实现能力。本轮未检查探针 Cargo feature 实际启用情况、遍历是否覆盖 impl／trait 方法与闭包、节点 span 是否包含属性，也未验证 Unicode／BOM／shebang 样例、rustc 接受范围或宏展开结果。实际查阅仅限上述缓存源码的定向 `sed`／`rg`，无外部搜索、无实验结论。
