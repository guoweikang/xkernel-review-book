# mount detach 候选 [505,507]：静态复核

2026-11-06；全部代码证据来自 `/root/codes/x-kernel` 固定提交 `7e3ac94431a0dbb376d2fc8d85098deeff1bba09`，以 `git show`/`git grep` 读取。候选编号沿用任务输入，未重新验证候选映射。未改内核、未运行测试、未对照 Linux 执行结果。

## 重叠与必须保留的差异

`fs/kvfs/src/mount.rs:1752–1782` 的 `Path::unmount` 与 `:1792–1833` 的 `detach_mount_subtree` 共享：验证 mount root、取父位置、持父 inode namespace-exclusive 锁确认自己仍是可见顶层 mount，然后取走 covers、恢复被覆盖层或移除父 child edge。单点卸载另在 `:1766–1767` 拒绝非空子挂载集合；子树卸载验证传入列表首项就是目标（`:1796–1801`），随后清空列表内各 mount 的 children、covers 和 location（`:1828–1831`）。不能以同一通用卸载直接替换两者而删除这些差异。`collect_subtree`（`:791–805`）包括后代挂载及其覆盖链，但不把目标自身下面的 covers 链作为待删除根层；目标下面的层应恢复。

## 调用方、注册表与提交边界

`MntNamespace::detach/detach_tree`（`fs/kvfs/src/mount.rs:420–444`）始终持 `self.mounts` 锁：先校验注册身份，调用 Path 层成功后才删除注册项；子树入口还在任何树修改前逐项 `require_mount`。注册校验同时比较 mount ID 和 Arc 指针（`:365–375,394–399`），不是只看名字。Path 层本身不更新注册表；测试专用 `unmount_tree`（`:1785–1789`）也不经过该注册表协议。外部已读调用方包括 `posix/fs/src/mount.rs:350–368`：路径解析、解析顶层覆盖 mount、权限检查后按 MNT_DETACH 选择两个 namespace 入口；`entry/src/main.rs:98–106` 在 init 退出回调中 sync 后尝试 detach_tree，失败只记录警告。

锁的作用域须分开：registry guard 跨越 Path 操作及注册项删除；父 inode guard 只跨越 Path 方法，返回后不再覆盖注册项删除。具体字段还由各自 mutex 保护。两方法的显式 `VfsResult` 失败检查都在 covers 被取走之前；子树方法虽在 `:1824` 才标注 commit phase，实际结构修改从 `:1814` 已开始。因此不能把整段宣传为对所有读者原子，也不能把“后续无 Result 错误”升级为 panic/并发安全证明。

## 已有 helper 与可复用机制假设

已有 `mount_edge_detach`（`fs/kvfs/src/mount.rs:591–604`，pivot_root 调用见 `:561`）执行“恢复 covers 或删除父 edge，再清 location”；`Mount::detach` 本身只取走 location（`:829–830`）。优先假设应是复用这一小段提交机制，而非合并单点/子树策略或新增布尔模式大函数。单点路径与 helper 仅在字段操作顺序上相似，不能直接视为锁行为等价：helper 的 `match mount.covers.lock().take()`（`:597–602`）将临时 MutexGuard 放在 match scrutinee 中，存在 guard 延续至分支执行期间的生命周期问题；单点路径则先 `let covered = self.mnt.covers.lock().take();` 再 match（`:1770–1779`），该语句结束后才进入父 child-edge 操作。因而直接复用可能改变 covers 锁与父 `mnt_mounts` 锁的嵌套关系（后者见 `:818–826`），即使最终字段值相同也不足以证明等价。这是源码级锁生命周期审阅关注点，不是已证明的死锁或运行故障；本轮未作完整锁序证明或新增测试。子树路径若用 helper，还会提前清根 location，随后循环再次清理，须另核对可观察顺序。helper 注释要求 registry 与受影响 inode 锁；生产 namespace 入口有对应外层锁，而已有直接 Path 测试没有 registry 入口，契约应显式说明，不能伪称所有调用方已满足同一锁协议。

## 测试材料与下一步边界

已读 `fs/kvfs/ut-tests/mount.rs:491–513` 验证 overmount 卸载后恢复旧层；`:1059–1079` 验证单点遇子挂载返回 ResourceBusy 且保留 children；`:1083–1104` 验证递归清 children；`:1108–1122` 验证隐藏层不能先卸载。`:603–623` 走 namespace detach 检查 bind 源 dentry 保留，`:915–929,949–963` 走 detach_tree 检查 pivot 后恢复可见根。这些是现有断言，不是本轮通过结果；直接 Path 测试不证明 registry 清理正确。建议在决定复用前针对 namespace 入口补核失败前后注册项、子树含覆盖层时的删除/保留集合，以及锁内操作顺序；本轮未完成这类完整性/并发验证。代码重叠与现成 helper 提供具体复用假设，但没有变更历史、维护成本或缺陷数据，维护收益仍未知，不能将候选命中计为已确认优化机会。
