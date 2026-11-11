# SCC 六对候选：归档上下文反向审阅

2026-11-05；固定内核提交 `7e3ac94431a0dbb376d2fc8d85098deeff1bba09`。仅审阅指定 file_id 对，以 `research/evidence/runs/2026-11-05-rust-scc-01/candidates.json` 映射到 `research/evidence/runs/2026-11-05-rust-baseline-corpus-01/{sources,units}.zip`。直接读取各 unit 及 sources.zip 中对应完整源文件的相关 impl、fixture、后端与相邻调用上下文，不读取当前内核工作树。六对所有成员的 source/unit SHA256 均与 candidates.json 字段相符；这仅核对归档内部映射，不是重新认证整个提交来源。下文代码路径行号均指该固定归档。

未运行测试、构建或更改内核。测试断言是意图证据，不是已通过结果；cfg 未求值。本笔记为 Agent 静态审阅建议，**不是独立人工真值标签**；token 相似、pair 数和 hash 一致均不直接代表重构机会。这里只给逐对依据，不另建主线程队列协议。

## [1237,1578]：生产 rename 拒绝实现与 mount mock

- **定位／共同机制**：`fs/kvfs/src/simple_dir.rs:603` 与 `fs/kvfs/ut-tests/mount.rs:274` 都实现同一形状的 rename 回调，忽略入参并返回固定错误；主要重叠是 trait 签名，而非复制了一套 rename 算法。
- **已有分层／必要差异**：前者属于 `SimpleDirInodeOperations<O>`（`:487`），同 impl 的 mkdir/rmdir 等已委托 `self.dir.ops`（`:541`）；rename 本身不委托。后者属于 `MockDirOps`（mount `:206`），lookup 只构造 `mnt` 等测试所需行为。生产返回 `OperationNotPermitted`，mock 返回 `OperationNotSupported`，不能替换成同一错误而称行为保持。
- **收益证据／下一步**：只见各一条拒绝语句，无重复复杂逻辑或共同缺陷维护记录。建议保留显式回调，降为低优先级接口样板；若未来考虑 trait 默认实现，先核实全体实现的错误契约及 trait 默认行为，本轮未审计，不以此 pair 单独发起抽象。

## [1237,1660]：生产 rename 与 namei 测试目录

- **定位／共同机制**：同一生产 `simple_dir.rs:603` 对照 `fs/kvfs/ut-tests/namei.rs:217`；也是相同接口上的拒绝回调。该对与上一对共用 1237，不能算两项独立生产维护负担。
- **已有分层／必要差异**：namei 的 `TestDir` 在 `:127` 实现目录操作，create/mkdir/mknod 记录创建参数并实例化测试 inode（`:141`、`:158`、`:187`），rename 则固定拒绝。它与生产对象的职责和错误值不同：`OperationNotSupported` 对 `OperationNotPermitted`；没有可以从这两个 body 中提取的共同操作流程，除固定返回包装。
- **收益证据／下一步**：没有变更历史证明这些签名样板造成维护问题。建议作为“生产／测试角色不同且错误契约不同”的审查对照，保持现状；即使测试 mock 之间将来共享设施，也不应据本对将生产策略搬进测试。

## [702,1809]：字符设备注册入口与局部 registry 测试 helper

- **定位／共同机制**：`fs/kvfs/src/node/device.rs:151` 的 `cdev_add` 与 `fs/kvfs/ut-tests/node_device.rs:296` 的 `add_test_range` 都构造 `Arc<ChrdevEntry>` 后添加到 registry。
- **已有委托**：边界验证已在 `ChrdevEntry::new`（生产 `:39`）统一完成；重叠／重复范围处理已在 `ChrdevRegistry::add`（`:75`）统一完成。测试 helper 并未重写两种校验算法，`:307` 起用局部 registry 检查无效、溢出和重叠范围。
- **必要差异**：生产入口取得全局 `CHRDEV_MAP` 锁，先保存 `add` 结果，再显式 `drop(entry)`，注释强调被拒绝后端在解锁后析构（`:153–155`）。测试 helper 接收调用方的 `&mut ChrdevRegistry`、克隆借入的 ops，没有全局锁。附近测试在后端析构中断言 `CHRDEV_MAP.try_lock()` 可成功（测试 `:435`），是该生命周期约束的额外源码证据，不是执行结果。
- **收益证据／下一步**：核心机制已复用；合并两个薄入口没有已证实收益，反而必须保留隔离 registry 与析构时机。建议标记“已有复用／边界适配”，不进一步抽象；若有建议，先明确它减少的是哪项尚未共享的维护责任。

## [1281,1672]：公共字节读取 helper 与可变测试文件读取

- **定位／共同机制**：`fs/kvfs/src/simple_file.rs:419` 的 `read_generated_bytes` 与 `fs/kvfs/ut-tests/namei.rs:332` 的 `TestFile::read` 都按 offset 判断 EOF、限制复制长度、返回已读字节数。
- **已有委托／差异**：生产 generated read（`:353`）和 snapshot read（`:388`）已经调用同一个 helper；测试 `TestFile` 的数据由 mutex 保护（namei `:254`、`:333`），锁覆盖复制。生产 helper 接收借入 slice、不负责锁。另有真实代码差异：生产先以 u64 比较 EOF 再转 usize；测试先 `offset as usize` 再比较。在 usize 小于 64 位且 offset 超出其范围时，不能声称二者全域等价；本轮未证明这种目标／输入在本测试中可达，不报系统漏洞。
- **收益证据／下一步**：测试读路径尚未委托生产 helper，但没有历史维护负担或收益量化。建议先确认支持位宽与测试 mock 的偏移契约；不为这一小段单独扩大私有 helper 可见性。复用测试支持代码可作为低优先级选择，但须权衡测试对生产实现的耦合；不能再次将已共享的 generated/snapshot 读取算成新机会。

## [1830,1831]：两个不同故障阶段的块设备测试

- **定位／共同机制**：`fs/kvfs/ut-tests/node_device.rs:780` 与 `:797` 都用 512-byte `BlockIoFixture`，注入故障后检查 Io 错误、调用计数及数据保持范围。
- **已有委托**：fixture 的构造／注册与清理已共享（`:645–678`）；`MemoryBlockDevice` 共享 I/O 计数和注入机制（`:462–533`）。前者的 `fail_after_write_bytes` 分支先写入前缀再返回错误（`:500–507`）；后者 `fail_io` 在读复制前报错（`:482–490`）。
- **必要差异**：`:780` 检查对齐写发生一次、无读、只修改指定 512-byte 前缀且不重试；`:797` 先检查读失败不修改调用者 buffer，再检查非对齐写的前置读取失败后没有后端写入、storage 不变。它们不是同一失败场景的冗余断言。
- **收益证据／下一步**：已有 fixture 消除了主要准备样板；未见进一步合并能降低维护成本。建议保留两个具名测试与各自 oracle，不因相似度合并成笼统“失败时返回 Io”测试。若扩展测试矩阵，再评估仅共享准备步骤，不隐藏部分写入与读改写前置失败的区别。

## [1703,1710]：magic link 与 trailing-slash 路径语义测试

- **定位／共同机制**：`fs/kvfs/ut-tests/namei.rs:1092` 与 `:1316` 都以 flags 调用 `Filename::open_with_flags_at` 并检查类型／错误；大段相同参数是同一 API 的调用样板。
- **已有委托**：已共享 `test_tree()`（`:483`）。其中 `/link`、`/dirlink` 是分别指向普通文件／目录的符号链接（`:491–500`）；`/magic` 有 `TestMagicLink` 的 retained Path 与 follow counter（`:367–405`、`:518–530`）。
- **必要差异**：前者检查 magic link 在 O_NOFOLLOW 下报 FilesystemLoop、O_CREAT|O_EXCL 下报 AlreadyExists，而 O_PATH|O_NOFOLLOW 保留 symlink 且 follow_count 为零。后者检查尾斜杠强制目录需求：`/target/` 报 NotADirectory、`/dirlink/` 即使带 O_NOFOLLOW 仍得到目录、`/link/` 报 NotADirectory。对象类型、路径形式和预期条件不能互换。
- **收益证据／下一步**：未取得样板导致错误或高维护成本的证据；共享 fixture 已存在。建议保留两类语义场景，至多在测试数量增长时讨论显式接受 path／flags 的小测试 helper，保留具体断言和 follow counter 检查；不把同 API 的两次用例计为生产功能重复。

## 收束

六对中未取得“现在就应合并”的充分证据；这是限定上下文下的行动建议，不是绝对负例标签。优先保留错误值、锁／析构边界、位宽条件及测试 oracle 差异；已有委托应从新增机会叙述中扣除。未审计历史变更、全部 trait 实现或测试接入／运行状态，故维护收益、覆盖充分性及跨配置等价性均仍未知。
