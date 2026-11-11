# facts 可用性：18 对复核候选的证据边界

2026-11-06，限定检查 book 的 `research/evidence/{originals,inventory,runs}` 文件名索引、下列归档原件/报告及固定内核源码。未联网、构建或重新导出 facts；仅在内存解压既有 klazy 样本核对头和计数，未写新数据集。**结论：在本轮检查范围内，有 kvfs 的 CI manifest 条目，但未找到已归档且经校验的 kvfs call/use 正文及18对候选的逐项对齐审计；实际正文样本与审计对象仍是 klazy。不能说 CI 没有 kvfs，也不能说18对已有自动调用证据覆盖。**

## 直接核对的原件与实际范围

- `research/evidence/originals/T11-ci-3885/kplat-aarch64-manifest.json` 与 `kplat-x86_64-manifest.json`：均声明 commit `7e3ac94431a0dbb376d2fc8d85098deeff1bba09`，schema `xkernel-facts/0.3`。kvfs 条目分别指向 `crates/kvfs-57a59f415a7d6525.jsonl.zst`（SHA256 `183f687eb7eabf7f64ed875ccbc1cab01ce8ddaaab9b91bd1ae21a0e3837dc46`）及 `crates/kvfs-913aa38194a04ed3.jsonl.zst`（`7f03f02be405737749cff559b5524a399b05bbbb0b055c7c55483966d49eb23a`）；均记 44015 records。这是**包目录清单中的记录数**，不是已核验调用边数量。该归档目录实际仅有两份 manifest、两份 status 和一份 klazy 压缩正文。
- 同目录 `kplat-aarch64-status.json`、`kplat-x86_64-status.json` 均声明 ready 并记录 manifest 摘要；ready 不证明本地已取得全部 crate 正文或逐条语义校验。
- `research/evidence/originals/T11-ci-3885/klazy-aarch64.jsonl.zst`：本轮读取正文并计算压缩 SHA256，得到 `4f70705cdfa2478a3bf6a79308657928433e543ea7aa1bca286646ca3b0c97a6`，与归档审计及 manifest 条目一致。头为 klazy/aarch64、`cfg=["unittest"]`，424条记录：94 item、213 call、88 use、11 ref、16 site、头尾各1；记录顶层 file 字段未见 `fs/kvfs/`。这不排除引用其他 crate，但不能用它冒充 kvfs 函数体 facts。
- `research/evidence/inventory/2026-11-05-klazy-facts-audit.json` 保存44个 fn、5份 klazy 源码路径、无重复 item key/越界行号等结果；footer 计202普通调用边与11 drop边。直接阅读 `scripts/audit_facts_sample.py` 确认其检查压缩哈希、字节/记录数、头身份和固定 Git 源码行号范围，**并不逐条验证 call/use 语义正确性**。本轮未重新执行该审计脚本。行号合法、哈希一致都不是调用图精度结论。

## 配置与其他归档不能替代的部分

两份原始 manifest 的 `unittest=false` 与 `rustflags=["--cfg","unittest"]` 并存，`deps=true`、toolchain `nightly-2026-03-08`，分别面向 aarch64 与 x86_64；不能解释成无测试代码或已运行测试。配置摘要分别为 `6dcda3e5b4c7ad3eb97f2c97d5e647df74c1d4322325d2e56b75278de224b2eb`、`d7d83167755b94104c8fb7ce32edfd3b7130fc5a45c7c284b2c6ebac9a9749c6`。上述 CI 原件目录没有完整 `.config`；本轮不裁定其他 preflight 是否恢复了相同摘要，也不将后续本地配置当 CI facts 配置。两平台记录数相同不能证明配置覆盖相同，更不覆盖全配置。

另直接阅读 `research/evidence/runs/2026-11-05-source-units-v2-verified/report.json` 与 `research/evidence/runs/2026-11-05-rust-scc-01/report.json`：前者记录源码结构工作流，后者记录2180源码单位、812合格单位和156个唯一 token 候选对及其算法 oracle 比较。它们不是 kvfs MIR call/use 验证报告；SCC 的 oracle 比较也不是“已有委托/应当复用”的真值。未逐一重审18对，也未检查隐藏构建目录或全文件系统，故本结论是归档证据可用性边界，不是全机不存在数据的断言。

## exporter 能力与自动已有委托证据

固定 SHA 源码 `tools/lints/src/facts_export/bodies.rs:113–135` 实现 MIR 选择，`:243–260` 实现符合条件的析构调用记录；`tools/lints/src/facts_export/uses.rs:5–6,27–39` 定义 MIR 中 static/const/variant/field/struct 使用类别及访问类别，并排除 core/alloc/std/compiler_builtins 的 uses。这支持“已有导出能力和非全量边界”，不支持“本地18对已成功关联”。沿用既有能力笔记时必须保留这一差别。

若取得并校验对应 kvfs 正文，再完成候选源码单位到 facts 身份/宏来源/配置的关联，call 可为“该编译配置下存在指向既有 helper 的静态边”提供检索线索，use 可提示共享字段/类型操作；当前只能提出此用途，不能给18对填自动证据已满足。无边不能证明没有委托；有边也不能证明运行可达、完整控制流、锁/Drop 时序相同或可安全替换。尤其 mount helper 的持锁及 Arc 生命周期仍须源码核查，调用集合不能替代。已有 sidecar 的手工源码引用可作为独立证据类型登记，但不是 facts 自动召回结果、独立人工标签或维护收益证明。
