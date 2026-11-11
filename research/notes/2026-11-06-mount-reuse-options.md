# 单点 unmount 与 mount_edge_detach：最小复用选项

2026-11-06；只读 `/root/codes/x-kernel` 固定提交 `7e3ac94431a0dbb376d2fc8d85098deeff1bba09`。范围仅单点 `Path::unmount`、现有 `mount_edge_detach` 及其调用前提；未改内核、未运行测试或编译器探针。主线程另做 Rust 临时 guard/payload 析构探针，本笔记不预报其结果，不作一般死锁排查。

## 前提与不能忽略的持有值

`fs/kvfs/src/mount.rs:1752–1783` 的 unmount 自行校验 mount root、父位置、父 child edge 身份及无子挂载，并在父 inode namespace-exclusive guard 内修改。生产入口 `MntNamespace::detach`（`:420–427`）另持 registry 锁，Path 成功返回后才删除注册项。直接 Path 测试 `fs/kvfs/ut-tests/mount.rs:491–512,1059–1079` 使用 `Mount::new_root` 等夹具，不经过该 registry 入口；这不证明生产调用无锁，也不能称所有现有调用均满足 helper 的 registry 前提。

现有 helper 的注释要求 registry 与受影响 inode 锁（`fs/kvfs/src/mount.rs:591–604`）。其 pivot_root 调用确实先取得 registry 锁（`:482`）及去重排序后的 inode guards（`:527–541`），在 `:561` 调 helper 后继续重挂载（`:567–584`）。helper 的 `match mount.covers.lock().take()` / `Some(covered)` 与 unmount 的 `let covered = ...; match covered` / `Some(ref mount)`（`:1770–1781`）不只是语法差异：需分别核对 scrutinee guard 是否跨分支，以及拥有的 Arc 在分支末尾还是 unmount 局部作用域结束才释放。后者可能改变相对 `mount.detach()` 的析构顺序。父 child 表保存 Weak（`:818–822`），不能将恢复 edge 等同增加持久强引用；registry/测试局部可能另有强引用，但这不足以普遍消除 Drop 时序差异。这里列的是静态行为差异关注点，不是已证明的死锁、释放后使用或运行故障。

## 三种方案

| 方案 | 实际变化与代价 | 本轮判断 |
| --- | --- | --- |
| A：unmount 直接调用现有 helper | 最少文本改动，保留此前所有校验；但引入 helper 的 match guard 嵌套及拥有型 payload 释放时序，还需解释直接 Path 测试与 helper 文档前提的差别。 | 不作为“机械等价去重”提交。字段写入顺序类似不足以过关。 |
| B：先将 helper 规范化为 let + 借用匹配，再复用 | 可显式缩短 covers guard，并让 payload 活到 helper 末尾、跨过 detach；但同时改变已有 pivot_root 的锁/Drop 时序，且 payload 从 unmount 调用方移到 helper 后，精确释放边界仍需核对。 | 不是仅整理 unmount；需作为明确的时序调整单独说明理由与验证范围，本轮不推荐扩大到它。 |
| C：仅提取“恢复覆盖层或删除父 edge” | 小 helper 接收父 mount、dentry、借用的 `Option<&Arc<Mount>>` 一类输入；不取 covers、不清 location、不承担 registry 删除。调用方保留拥有的 payload 和原 guard/作用域：unmount 继续 let + ref，原 helper 继续其 match 分支，再调用低层 helper。 | 可以构造较保守的候选，避免强行统一锁/持有策略；代价是多一层接口，仅省一个短分支，并且仍须检查旧返回值的丢弃位置不变。 |

## 建议与停止边界

建议当前保留重复，不直接选 A，也不借去重顺便实施 B；这不是宣称不可复用。如主线程必须保留一个最小后续候选，优先 C 的借用型 edge 操作，明确调用方负责持锁、持有 covers payload、清 location；必须保留 `install_child_mount` 返回旧 Arc 的丢弃边界（实现见 `:818–823`），不能改成跨层返回而无意延长其生命期。待主线程探针澄清语言级 guard/Drop 顺序后，只需对这两个调用点逐项比较锁与强引用的生存区间；探针本身不证明内核并发正确。若 C 的短分支节省不足以抵消接口与契约成本，就停止在“有重叠、无充分维护收益证据”，不扩展为全局锁序研究、不合并子树卸载、不把现有测试断言或独立 Agent 阅读当真值标签。
