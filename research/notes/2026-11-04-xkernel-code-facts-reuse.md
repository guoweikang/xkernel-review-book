# X-Kernel 编译器代码事实：复用评估

日期：2026-11-04。任务：核实用户指出的既有数据与调用关系提取能力，判断能否作为重复功能识别的底座。

## 版本与读取方式

已执行 `git fetch origin main`。本次远端 main 为
`dc8f8e81224b6733fd05b83fb3f54c5397d261c3`。
`/root/codes/x-kernel` 工作树仍为 `f429a5953fdc1b37702bd0a55ee105eefa952730`，存在无关未跟踪材料，
未 checkout、reset 或修改工作树；以下通过 `git show <revision>:<path>` 与 `git grep` 核对远端快照。

合入记录：`af220050f`（!1203，代码事实导出与 CI 制品），`45e4f98d0`（!1204，依赖、字段类型、uses 与函数值流向）。
因此此前“仅注册一个自定义 lint”的旧快照描述不能原样套到新版本；新 `facts_export` 是不报告违规的导出 pass。

## 已实现的数据层

所有路径相对于该提交的 X-Kernel 仓库。

| 能力 | 实际内容 | 代码依据 |
| --- | --- | --- |
| 导出入口 | Dylint LateLintPass，开关 XKERNEL_FACTS=1；schema xkernel-facts/0.3；单 crate 原子写文件 | `tools/lints/src/facts_export/mod.rs:60`、`:108` |
| 定义与层级 | mod、struct、enum、trait、impl、函数、闭包、字段、可见性、父项、源码与宏位置 | `tools/lints/src/facts_export/items.rs:19`、`:58` |
| 类型组成 | 字段声明类型、提及的 ADT/dyn trait keys；枚举 variant；static/const 类型 | `tools/lints/src/facts_export/items.rs:131` |
| 调用 | MIR 调用、Drop；静态、trait、dyn、fnptr、closure、foreign 等分类 | `tools/lints/src/facts_export/bodies.rs:115`、`:243`、`:400` |
| 函数值来源 | 参数、字段、函数、闭包捕获，输出 ref 和 via_* 关联线索 | `tools/lints/src/facts_export/flow.rs:1`、`bodies.rs:304` |
| 数据使用 | static、const、variant、field、struct 的 read/mut/construct/match/ref 位置 | `tools/lints/src/facts_export/uses.rs:1` |
| 安全线索 | unsafe block、调用是否位于 unsafe、原子调用的 ordering | `tools/lints/src/facts_export/bodies.rs:142`、`:600` |
| 测试 | 内嵌 UI fixture 对上述多种记录有断言 | `tools/lints/src/facts_export/tests.rs:191` |

函数 item 导出 unsafe/generic/owner 等属性，但所读 `fn_fields` 不导出完整参数与返回类型签名。
不能将字段类型能力写成“完整函数类型索引”。也未见职责摘要、需求契约、embedding、代码相似度或重构收益计算字段。

## 关键边界

1. **配置范围。** 只覆盖本次构建选中的代码。CI 默认包对应普通配置，不能当所有 feature/平台的并集。
2. **调用证据强弱。** `trait_generic`、`trait_unresolved`、`dyn`、`fnptr` 与已解析静态目标不同；存在记录不等于已知唯一运行目标。
3. **局部值流。** `flow.rs` 的 MAX_DEPTH 为 8，只追踪单次赋值等受限来源，多次赋值或不可解析来源返回 Unknown；不是完整全程序 points-to/别名分析。
4. **不是控制流图。** call/use 关系不表达完整路径条件、执行次数或数据流等价；调用集合相似不能证明行为相同。
5. **主动降噪。** `use` 排除 core/alloc/std/compiler_builtins，格式化内部调用也被省略；不能把缺失当“没有使用”。
6. **标识稳定性。** def-path key 在 commit 内使用；跨 commit 需要重新关联，行号、impl 编号和路径变化都应纳入考虑。
7. **可信来源。** PR 能修改 exporter；README 要求消费者信任已认可的 exporter 摘要，并把 facts 当 review 线索而非 gate。

制品包含 status.json、manifest.json 与逐 crate 压缩 JSONL。README 区分 ready、partial、failed 和 running；使用前必须检查状态、missing 列表及配置，不能仅凭存在制品判定覆盖完整。

## 对重复功能工具的实际帮助

判断：应优先复用这些 facts，而不是重新实现 Rust 符号与调用提取。

| 研究需求 | 可直接利用 | 仍需补充 |
| --- | --- | --- |
| crate/mod/type 职责索引 | 定义层级、类型组成、使用者和位置 | rustdoc、design.md、实现语义的职责摘要及证据 |
| 候选召回 | 相同数据类型的使用、相近依赖/调用/字段模式 | token/语法相似度与语义检索；多路召回防止仅同结构命中 |
| 候选核验 | 调用方、trait 实现、字段使用、unsafe/原子线索 | 参数契约、错误行为、上下文、配置、性能要求 |
| 重构影响 | 使用者和关联关系 | 动态调用不确定性、其他配置、迁移设计与回归验证 |
| 收益评价 | 可定位到定义及使用点 | 整体代码成本、性能和维护性数据，不能只看删行 |

例如：两个函数都操作相同字段且调用相同底层 API，可以成为候选；但其中一个允许阻塞、另一个要求立即返回时，不应直接合并。
这是候选解释示例，不是本轮发现的真实重复案例。

## 建议的最小接入顺序（未实施）

1. 获取一份已归档的事实制品，核查 status、manifest、commit/config、schema、exporter 与 missing；保留不确定边。
2. 只做只读查询：定义、调用者、被调用者、类型持有者与数据使用点；验证实际数据足够支持检索。
3. 在此之上补职责摘要和代码相似度候选；输出“为何相似、关键差异、缺失证据”，不是直接给合并命令。
4. 经用户确认案例标准后，再做候选人工核验、实际精简补丁和性能/回归测试。

这不等于另起一个数据提取项目，也不要求先自建图数据库。存储选型应在确认现有消费者/API 后再定。

## 本轮验证范围

已核对文档、导出源码与测试断言；未运行 exporter、UI 测试或内核构建。
在两个已知本地 target 路径的有限深度查找未得到可用 facts 包；不声称全环境没有制品。
未查询 Jenkins 实际构建产物，未取得 xreview 索引服务端/API 实现；不能宣称已有完整语义数据库或线上质量保证。
没有新增重复案例标注，没有实现判分或重构工具。
