# Rust 候选单位定位：源码语法树与编译事实的小样本核查

日期：2026-11-05。阶段 A 的输入适配验证，不是重复检测效果实验。
源码固定为 `7e3ac94431a0dbb376d2fc8d85098deeff1bba09`，样本沿用 CI3885 的 klazy。

## 1. 验证方法

调用本机 `rustup run 1.95.0 rust-analyzer parse`，只解析 stdin，不加载 Cargo 工作区、
不执行 build.rs、不展开宏、不联网安装组件。工具版本为 `rust-analyzer 1.95.0 (5980761 2026-04-14)`。
`--help` 明确说明子命令及其参数没有稳定性保证，因此本轮使用的是**临时诊断输出适配器**，
不是承诺长期可维护的正式 AST 接口。

脚本：`scripts/probe_rust_units.py`。
结果：`research/evidence/inventory/2026-11-05-rust-unit-probe.json`。
结果记录工具二进制哈希、源文件哈希、语法树输出哈希、节点字节范围、父级范围、关联状态及限制。
制品与版本的前置一致性由 [样本核查](2026-11-05-facts-source-alignment.md)建立，
本脚本不单独认证任意输入制品的 commit。

## 2. 七个构造输入检验的边界

| 输入形态 | 实际观察 | 对候选提取的意义 |
| --- | --- | --- |
| 中文注释、字符串中假 fn/括号、同一行两个函数 | 两个 FN，按字节切片得到完整第二个函数；字符串未变成函数 | 用 UTF-8 字节位置，不能用字符下标或按行分割替代 |
| trait 声明、默认方法、泛型 impl | 三个 FN，其中声明没有 body | 区分接口声明与实现；函数外的 impl/trait 约束要另取 |
| 函数内函数和闭包 | 两个 FN；闭包另有 CLOSURE_EXPR，保留父级链 | 不能将闭包默认作为独立普通函数；嵌套单位会重叠 |
| cfg 禁用函数、外置 mod、内联 mod | 禁用函数仍可见；外置 mod 只有声明 | 源码语法视图不是生效配置视图，不自动加载外置模块 |
| macro_rules 中的 fn 模板及调用 | 零个普通 FN | 不展开宏就拿不到生成函数；模板 token 不能冒充已生成定义 |
| 残缺 `fn broken( {` | 返回 0，生成 FN/BLOCK_EXPR，没有 ERROR 节点 | **成功退出且没有 ERROR 不足以证明语法正确** |
| 错误表达式 `let value = ;` | 返回 0，有一个 ERROR 节点 | 检查 ERROR 只能发现部分错误，不构成完整诊断接口 |

七例具有明确的人工期望和脚本断言，但只是接口行为检查，不能据此报告真实项目提取准确率。
没有编译这些构造输入，其中两个故意非法。也没有把它们当成重复功能正负样本。

## 3. 固定源码的实际关联结果

解析 klazy facts 所引用的五个源文件，对其 44 条 fn item 使用简单定位规则：
同文件、同名称，语法节点名称行落在 facts 的行范围内；唯一命中只记为定位候选。

| 状态 | 数量 | 解释 |
| --- | --- | --- |
| 唯一定位候选 | 36 | 不是经过独立标注确认的语义身份或完整覆盖 |
| 宏生成项，不直接关联 | 3 | Status 的派生 clone/fmt/eq；保留编译视图身份，不伪造源码函数 |
| 名称行规则未命中 | 5 | 均为 `#[def_test]` 标记的函数，原因如下 |

所有五个输入文件的 dump 都没有 ERROR 节点，但鉴于非法输入的反例，不将其表述为完整语法验证通过。

### 真实失败：属性宏不必带 gen 标志

`util/klazy/ut-tests/once_unittest.rs:9` 是 `#[def_test]`，函数名在第 10 行。
对应 facts 的 `line=end_line=9`，`macro` 和 `defined_by` 都为 `#[def_test]`，却没有 `gen: true`。
其他四个测试函数呈现同类现象。

这不是解析器没有发现函数，而是**宏调用处范围与原定义名称范围不同**。
改用同名 FN 整节点（含属性）的范围交集，可为这五项各找回一个源码候选；
本轮保存该结果，但不把原失败覆写成“已准确匹配”。属性宏可能改变签名和函数体，
源码候选只能表示原始输入位置，不能自动等同编译后的实现。

进一步核查 `util/macros/src/lib.rs:238`、`:247`：`def_test` 实际重建为
`fn 名称() -> unittest::TestResult`；原函数没有显式返回类型时追加 `TestResult::Ok`，
并另外生成测试描述符。这不是仅理论上的宏风险，而是本样本确实存在的签名/函数体变换。
因此应将这五项记为属性宏变换、源码范围交集候选、不假定签名等价。

exporter 的 `gen` 判断是 `name_span.from_expansion()`，不是“这个定义是否经过任何宏处理”。
来源：固定树 `tools/lints/src/facts_export/items.rs:72` 附近。
因此宏影响判定需要结合 `macro/defined_by/gen`，不能只过滤 `gen=true`。

### 函数文本不是全部接口上下文

`Lazy::force` 的 `F: FnOnce() -> T` 在外层 impl 上；只拿函数签名会丢失它。
本探针保留父级 IMPL/TRAIT 的字节范围，但没有做名称解析和类型绑定。
`fn_signature_tail_range` 只从 fn 关键字到函数体之前，不含前置 pub/unsafe/const/async，
也不是完整的语义接口记录；正式提取应分别存修饰符、参数、返回值、where、外层约束和属性。
doc 注释/属性可能包含在节点内，后续代码相似度与文档相似度应分字段，不能无意混在一起。

## 4. 技术选择和失败应对

1. 保留“源码定义视图”和“配置内编译视图”，通过有状态的关联记录连接，不强行做一张同一对象表。
2. 普通定义可以继续验证字节级切片；正式解析器需提供稳定节点接口及完整语法诊断。
   本轮证明本机工具可辅助探查，不决定长期选 rust-analyzer CLI、syn 或其他实现。
3. 属性宏：先记录原始源码与编译对象的候选关联；宏语义未核验时标为 transformed/unknown，
   不将原始函数体当作展开后函数体。
4. 宏模板、derive 和其他生成项单列覆盖与成本；无生成源码不能计为“没有重复”。
5. 外置模块解析、cfg 求值、名称绑定和完整函数签名仍需补齐；不能由成功切出文本推定这些能力已具备。
6. 进入检测实验前冻结代码单位与输入口径，保留遗漏/多义清单；严禁只保留容易定位的对象而隐藏分母。

当前可以推进源码候选单位的适配，但**还不能宣布可靠的全仓函数提取器已完成**。
下一步优先核查带诊断的结构化解析接口，并把这些失败例作为适配验收输入；不先堆叠语义模型。

## 5. 复查命令和一手依据

```sh
python3 scripts/probe_rust_units.py --repo /root/codes/x-kernel \
  --revision 7e3ac94431a0dbb376d2fc8d85098deeff1bba09 \
  --sample research/evidence/originals/T11-ci-3885/klazy-aarch64.jsonl.zst \
  --output research/evidence/inventory/2026-11-05-rust-unit-probe.json
rustup run 1.95.0 rust-analyzer --help
git -C /root/codes/x-kernel show 7e3ac944:util/klazy/ut-tests/once_unittest.rs
git -C /root/codes/x-kernel show 7e3ac944:tools/lints/src/facts_export/items.rs
```

其余固定树依据：`util/klazy/src/lazy.rs:118`（外层泛型约束）、
`util/klazy/src/lazy_static.rs:79`（宏模板）、`util/klazy/src/once.rs:630` 附近（测试模块加载）、
`util/macros/src/lib.rs:173`（def_test 入口）。原始 facts 的来源和哈希沿用 T11 存档，未重新下载。
