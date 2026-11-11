# A1：X-Kernel 优化分析材料盘点

日期：2026-11-04。状态：完成固定源码快照的材料存在性盘点；CI 实际产物、语义正确性和配置级覆盖待核实。
本轮不是重复案例采集、文档合规审计、运行测试或优化实验，不修改内核工作树。

## 1. 快照、范围与复现

执行 `git fetch origin main` 后固定版本 `7314469a4dc1c478ca17403745cbd65f86805c89`。
与此前 facts 评估的 `dc8f8e812` 不同；以下路径、数量只属于本次快照。
读取方式为 Git 对象及 `git archive`，没有 checkout，也没有依赖当前工作树的修改。

在 book 仓库运行：

```sh
python3 scripts/inventory_materials.py \
  --repo /root/codes/x-kernel \
  --revision 7314469a4dc1c478ca17403745cbd65f86805c89 \
  --output research/evidence/inventory/2026-11-04-xkernel-materials.json
```

逐 package 台账位于上述 JSON，包含 manifest、目录、设计/安全文档路径、README、Rust 文件数、
rustdoc 信号文件、测试信号文件及 bench 路径候选；包含方法、限制、版本和解析错误列表。
统计范围为所有已跟踪且含 `[package]` 的 Cargo.toml，不是解析后的 workspace 成员，
更不是某个 Kconfig 配置实际参与构建的 crate。包含 vendor、工具、应用和嵌套测试 package。
文件按最近的 package 目录归属，避免将嵌套独立测试包重复算给父包；不解析跨目录 `#[path]`、
`include!` 或生成代码。Git 未跟踪文件、外部依赖、子模块内容和在线 CI 产物不在本次统计范围。

## 2. 数量基线：只能解释为存在性

| 项目 | 数量 | 解释 |
| --- | ---: | --- |
| 已跟踪普通文件 | 3627 | Git archive 中普通文件 |
| Cargo.toml | 216 | 213 个 package manifest，3 个无 package 的 manifest，解析失败 0 |
| 有标准位置 design.md 的 package | 145 / 213 | 仅 `<package>/docs/design.md`；不是 145 个设计已经正确 |
| 有标准位置 security.md 的 package | 145 / 213 | 仅 `<package>/docs/security.md`；不是安全验证通过 |
| 有 rustdoc 文本信号的 package | 204 / 213 | 至少一个 Rust 文件含文档注释或 doc 属性信号，不是 API 覆盖率 |
| 有测试文本/路径信号的 package | 152 / 213 | tests/ut-tests 路径或测试属性信号，不是测试执行或通过率 |
| 有 bench 路径信号的 package | 6 / 213 | 仅发现入口线索，不证明有性能结果 |

rustdoc 和测试识别使用词法规则，可能命中文档示例或注释，也可能遗漏非标准宏；
不以此判定任何 package 不合规。未在标准位置发现设计文档，也不代表仓库其他位置没有相应说明。
这 213 个 package 的合计不是适用规范的分母；进入 A2 前必须区分生产、辅助测试、第三方等对象。

部分目录分布如下，完整清单以 JSON 为准：

| 物理目录 | package | design | security | rustdoc 信号 | 测试信号 |
| --- | ---: | ---: | ---: | ---: | ---: |
| arch | 10 | 8 | 8 | 10 | 8 |
| core | 8 | 7 | 7 | 8 | 8 |
| drivers | 25 | 22 | 22 | 25 | 16 |
| fs | 16 | 15 | 15 | 16 | 14 |
| mm | 12 | 11 | 11 | 12 | 11 |
| process | 16 | 15 | 15 | 16 | 14 |
| task | 13 | 9 | 9 | 12 | 13 |
| util | 30 | 19 | 19 | 29 | 17 |
| vendor | 10 | 0 | 0 | 10 | 5 |

## 3. 材料入口、用途与核验边界

所有源码路径相对于上述固定版本的 X-Kernel 仓库。

| 类别 | 实际入口 | 可以利用的信息 | 尚缺的证据 |
| --- | --- | --- | --- |
| 版本/构建 | `rust-toolchain.toml`、`Kconfig`、`platforms/*/*defconfig`、`api/kfeat/Cargo.toml` | 固定工具链、合法配置入口、feature 汇聚关系 | 分析用配置快照与实际构建单元；仓库有 defconfig 不代表该配置已测试 |
| 设计 | 各 package 的 `docs/design.md` | 职责、架构、执行上下文、不变量、权衡与生命周期声明 | 声明与当前实现逐项一致性的审计 |
| 安全 | 各 package 的 `docs/security.md` | 安全与信任边界材料入口 | 内容完整性、适用性与验证结果，本轮未逐篇审阅 |
| rustdoc | Rust 源文件；`xtask/xkmake/src/doc.rs` | API 注释与现有文档构建流程 | item 级覆盖、JSON 实际导出、示例执行结果、文档对象与 facts 的映射 |
| 类型/调用/数据关系 | `tools/lints/src/facts_export/`、`xtask/xkmake/src/facts.rs` | 已实现的编译器事实导出和打包 | 指定提交的实际 manifest/status/crate 文件及内容核验 |
| CI 归档 | `docs/jenkins-pipeline.md:186`、`Jenkinsfile:1009` | facts 归档位置与配置选择 | 可下载的实际构建号、产物保留状态、可信 exporter 身份 |
| 测试 | crate 内 `ut-tests/`、`tests/`、测试属性；`docs/ai/skills/test-harness/SKILL.md` | 测试源码与外部 harness 使用约定 | 指定版本/配置的运行记录、断言与契约对应关系 |
| 覆盖率 | `xtask/xkmake/src/coverage.rs`、CI 文档 | 覆盖率生成能力入口 | 实际报告及其覆盖的配置/目标，不把源码存在当覆盖率数据 |
| 性能 | `docs/ai/skills/performance-analysis/` 及其 `references/report-template.md` | 工作负载、环境与报告方法 | 对具体候选可复用的原始 baseline、波动与测量结果 |
| 实现 | 固定 commit 的 Rust 源文件、宏与配置生成逻辑 | 审查文档声明和结构相似性的底层材料 | 选定配置的宏展开、生成结果以及完整动态行为 |

已有 doc 命令调用 `cargo doc --no-deps --workspace`，target 与 `kfeat/*` features 来自项目配置，
显式设置 `cfg(doc)`，默认检查断链，check_missing 模式增加 missing-docs。
所读默认流程是 HTML 文档，不是已经建成的语义数据库，也没有默认包含私有项或输出 JSON。
`make doc` 不等于 doctest。文档视图与正常构建图的差异需在后续映射时保留。

CI facts 只打包两个 Dylint 分支的首次普通配置扫描；后续 unittest/lock-stat 扫描不打包。
不能把制品解释成所有平台/feature/测试配置的并集。产物即使存在也须核对 ready/partial/failed、
missing、commit、配置和 exporter；本轮没有访问 Jenkins 下载制品，也未执行提取器。

## 4. 已有规范：先复用，不另起一套

`docs/ai/skills/module-docs/SKILL.md` 已规定：

- design.md 承担职责范围、组件关系、执行上下文、状态机、算法、并发、取舍和资源释放。
- security.md 承担信任边界、unsafe、不变量、失效、安全及审计材料。
- rustdoc 承担 API 行为、参数/返回、错误、panic、unsafe Safety 与适用示例。

已有审核表位于 `docs/ai/review/module-docs/design-doc-checks.tsv`、
`security-doc-checks.tsv`、`rustdoc-checks.tsv`。例如 RD-009 明确缺运行记录不能把 doctest 判通过，
RD-010 要求文档检查确实启用且覆盖对象，RD-014 要求 crate 用途与首选入口。
因此下一步应做“优化判断所需元素与已有规则的差异对照”，而不是立即要求全仓添加新标题。

## 5. 内容抽查：已有有用语义，但未验证真实性

本轮定向读取 `util/klazy/docs/design.md`、`util/klazy/src/lib.rs` 与
`mm/memspace/docs/design.md`，用于确认材料类型能承载什么，不构成随机质量抽样。

- klazy 文档描述 no_std 一次性初始化、Once/Lazy 分层、原子/自旋、初始化时间和重入限制；
  crate rustdoc 描述用途并关联设计与安全材料。可用于检索和契约候选提取。
- memspace 文档区分地址空间 owner 与 file/anonymous content owner，并描述 callback 的
  分配、执行上下文和锁约束。这种职责边界与条件差异正是判断是否可共享实现所需的信息。

以上均为作者声明的例子，未在本轮证明实现符合声明；也没有据此提出重复或优化案例。

## 6. 缺口与交接

| 缺口 | 本轮状态 | 下一步处理 |
| --- | --- | --- |
| 分析对象的规范适用范围 | 已发现 vendor、嵌套 host tests 等不能混为同一分母 | A2 先定义对象类别及适用条件 |
| 文档元素与判断任务对应 | 有现成规范，无优化证据矩阵 | A2/A3 对照现有规则，标出已有、缺失、条件适用 |
| 来源/版本/配置/核验状态统一关联 | Git 快照已固定，文档声明尚未逐条建模 | 在最低要求中规定证据属性，不先建设数据库 |
| 实际 facts、文档、测试及性能产物 | 未获取，不是已证实不存在 | 登记需取得的构建号、制品与配置；不能把本轮盘点当运行验证 |
| API 级文档覆盖与正确性 | 词法存在性不能回答 | 后续按适用对象做结构化提取与内容核验，单列成本 |
| 其他 Rust OS 的材料分布 | 本轮未盘点 | X-Kernel 清单为首批，不代表跨仓能力；后续核实对象版本与同源性 |

A1 首批交付为源码材料清单及获取缺口；不是所有研究材料已经齐备。
建议接下来进入 A2 草案：将现有 module-docs 规则与优化判断需要的元素逐项映射。
正式案例采集、基线复现和优化实验仍未启动。
