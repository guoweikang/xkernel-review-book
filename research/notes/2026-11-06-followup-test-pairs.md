# 冻结候选：两对测试的夹具复用边界

2026-11-06，仅以 `git show` 读取 `/root/codes/x-kernel` 提交 `7e3ac94431a0dbb376d2fc8d85098deeff1bba09` 的两个测试文件及局部 helper。编号沿用主线程输入；本轮未运行测试、未改内核、未新增测试。主线程告知此前 metadata 模块 suite 已运行，本笔记未核对其日志或与本次固定源码的对应关系，不将其转述为本轮执行、独立人工真值或 Linux 行为验证。

## [1765,1766]：祖先陷阱与跨目录成功移动不是同一 oracle

`fs/kvfs/ut-tests/node_dentry.rs:762–789` 构造 `root/ancestor/old/source`，将 source 重命名到祖先目录位置：普通 rename 期望 `DirectoryNotEmpty`，EXCHANGE 期望 `InvalidInput`，并分别确认 source 与 ancestor 的缓存指针未被替换。`:792–812` 则构造兄弟目录 `old`/`new`，成功把 source 移到 `new/target`，断言旧缓存消失、新缓存仍指向原 source、绝对路径更新。前者的祖先拓扑和两次失败调用、后者的兄弟拓扑和成功后身份/路径变化，均应直接保留在测试中；前者名称含 linux 不等于已做 Linux 对照。

两者已复用 `make_renamable_dir_entry`（同文件 `:408–414`）、`make_file_entry`（`:376–389`）和 mock superblock 常量（`:24–25`）。共同剩余步骤是显式插入缓存及 `SuperBlock::new` 绑定 root（`:772–777,798–803`），并非缺少基础夹具。可考虑的更小 helper 仅是“为给定 root 创建并返回 mock superblock”，让调用方仍持有 `_super_block`；不能把该句移入一个立即丢弃返回值的封装，也不应在 helper 内自动推导测试期望或隐藏树形关系。是否值得为这几行再抽象尚无维护数据支持；优先保留现状，不建议用参数/模式切换合并两个测试。

## [1598,1599]：单层与嵌套 mount 的路径边界

`fs/kvfs/ut-tests/mount.rs:516–541` 构造一层 `/mnt`：root dentry 名为空、路径及 render_from 为 `/mnt`、标记为 mount root、`.` 保持同一 Path、`..` 得到 `/`。`:544–570` 增加第二层 `/mnt/mnt`：检查该路径及 render_from、空名和 mount-root 标记，并要求 `..` 得到 `/mnt`；它没有前者的 `.` 身份断言。共用名字/路径断言不表示目的重复，嵌套层级正是不同输入边界。两者调用的测试 helper `lookup_no_follow`（`:27–34`）对 DOT/DOTDOT 分别直接返回 clone/调用 `Path::parent`，因此这不是经完整 syscall/path parser 的 `.`/`..` 端到端验证。

已有 `mock_filesystem`/`mock_superblock`（同文件 `:323–344`）和 `mount_filesystem`（`:37–39`）承担对象构造与挂载参数默认值。较小的新增假设是“在指定父 Path 的指定名字下挂载调用方提供的 fs，返回 child Mount”，只折叠 lookup+mount 两句（`:520–521,550–553`）；保留 fs/各层 mount 的持有关系、显式层级构造及所有期望字面值，不把 `absolute_path` 的结果反过来生成 render_from 或 `..` 的期望。对仅两例而言封装收益很小且会隐藏挂载位置，尚不足以确认维护收益。结论：两对均有可描述的夹具重叠和已有复用，但无合并 oracle 的依据；候选命中、既往 suite 执行均不能替代 helper 等价性或收益证据。
