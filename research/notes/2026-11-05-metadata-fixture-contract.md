# Metadata fixture：有限契约复核

2026-11-05，仅通过 `git show` 读取内核固定提交 `7e3ac94431a0dbb376d2fc8d85098deeff1bba09` 的 `fs/kvfs/ut-tests/mount.rs` 与 `fs/kvfs/ut-tests/node_dentry.rs`。以下行号均指此提交。未扩展到模块接线／生产实现，未运行测试、修改内核或评估补丁；测试断言仅作为预期证据。本笔记不授予绝对优化标签，也不作为独立人工真值。

## 1. 哪些值确实相同

`mount.rs:172–193` 与 `node_dentry.rs:246–267` 的 `MockDirOps::getattr` 直接构造相同目录元数据：`device=0`、`inode=self.inode`、`nlink=1`、Directory 加默认权限、`uid=gid=0`、`size=0`、`block_size=512`、`blocks=1`、默认 rdev、三个时间均 UNIX_EPOCH。二者均不使用 idmap/path/request-mask/query-flags，且直接返回 `Ok`。

这能支持“两个 mock 显式采用相同固定字段组合”，不能证明每个常量都有必须一致的历史设计理由。inode 不是公共常量，应继续取各实例的身份。mount 的 synthetic-device 测试（`:1126–1142`）有更明确意图：两个文件系统的 inode 同为 1，但经路径 getattr 得到的 device 分别匹配各 mount 的 synthetic ID，且彼此不同；不能在共享 builder 中提前填入预期 synthetic ID，绕过这一被测转换。

## 2. Mock 状态和初始化不是同一份期望对象

- mount `MockDirOps` 保有 `mount_flags` 与 inode（`:156–164`）；node_dentry 的同名类型还保有 rename/remove 能力、unlink/rmdir 计数、lookup_result（`:197–238`）。相同 Metadata literal 不支持合并两个 mock 类型、共享可变实例或吞掉计数／能力差异。
- node_dentry 的 `MockFileOps::getattr`（`:76–97`）虽然有相同默认字段，但 node_type 取实例字段、size 在锁内读取 data 长度；`setattr` 则记录 owner 与 update_count（`:100–108`），而 getattr 的 uid/gid 仍固定为零。不能把 owner 记录自动变成 getattr 的动态返回值，亦不能在此次提取时缓存 size 或移除必要状态读取。
- **已有 fixture helper 不是可直接替代的 Metadata builder**：mount `inode_init(inode)`（`:287–301`）构造 `VfsInodeInit`，使用 512 block_size；node_dentry `inode_init(inode,node_type,size)`（`:432–445`）构造同一初始化类型，但 block_size 为 **4096**，而其 getattr literal 为 **512**。这是真实源码差异，本轮未证明差异是有意还是历史遗留；不得为“统一默认值”静默改成相同值。
- mount `mock_regular_file_filesystem`（`:346–367`）甚至用 `MockDirOps` 搭配 RegularFile 的初始化 metadata、owner `(1000,100)`，再修改权限。这进一步说明 ops 返回内容与 inode 缓存初始／变更状态不能直接当作一个对象。本文不判定该组合为缺陷，也不从它推断生产路径行为。

## 3. 测试预期需保持什么独立性

`node_dentry.rs:448–465` 检查文件类型与 size=7；`:468–491` 从当前 metadata 创建更新输入，显式设置 nlink=2、size=11，再断言这些值，并将 inode 改为 3 期待 InvalidInput，negative dentry 期待 NotFound。这类测试可以共享准备代码，但应保留字面值／外部契约定义的断言，不能把 expected 改成再次调用返回 actual 的同一个 helper，从而让字段遗漏或错误默认值同时污染两侧。

同理，mount 的 owner/group 测试（`:1280–1318`）及时间测试（`:1545–1580`）检查更新后的具体值和权限错误；不能用默认 Metadata builder 代替这些更新预期。mock 内部数据、inode 初始化／缓存、传入的更新对象和断言 oracle 是不同角色；并非禁止一切共享，而是避免同一新逻辑既生成被测输入又自行证明其输出。

## 4. 已有复用与建议边界

两文件各有本地 `inode_init`；mount 还已有 `mock_superblock`／`mock_filesystem`（`:323–344`），node_dentry 已有 `make_file_entry` 和多种目录构造 helper（`:376–429`）。本轮在这两个文件中未见用于上述两个 getattr literal 的共同 Metadata helper；不声称全仓不存在。

若主线程继续最小提取，较窄候选是**无状态、每次返回新 Metadata 值的测试默认字段构造**，保持 inode 及必要的 node_type／size 参数显式，两个 mock 的行为与锁继续留在原处。应保存两个目录 getter 的逐字段结果，同时不连带统一 `VfsInodeInit` 的 512／4096、不改变 regular-file 特例、不改 oracle 为自比较。这样可能减少 fixture 字段维护点，但本轮没有共同变更历史、构建验证或缺陷减少证据；是否值得引入跨测试 helper，仍由模块接线成本与实际可读性决定。
