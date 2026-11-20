# RemovedEntry专用追加测试

挂接：将同目录`removal-event-tests.rs`的全部内容原样追加到**新的隔离副本**`fs/kvfs/ut-tests/mount.rs`末尾，保持同一模块；不再包一层module，不替换现有MockDirOps或测试。不修改`/tmp/xkernel-pagecache-n1y2__y3`基线。目标源码固定为`7e3ac94431a0dbb376d2fc8d85098deeff1bba09`。

依赖同模块已有的`MockDirOps::new/getattr/lookup`、`mock_superblock`和imports。专用操作对象委托原MockDirOps提供metadata模板与未命中lookup；直接缓存真实Dentry，使用真实Mount/Path/VfsInode及unlink/rmdir路径。所有状态由每个case独立创建的Arc持有，无静态全局计数。

新增六个`#[def_test]`入口：两个backend成功快照、两个getattr失败缓存回退、两个删除失败。每个删除失败入口覆盖getattr成功及失败，所以共八个场景。预先设置backend nlink=7、缓存nlink=3；成功删除回调将二者改为2。检查返回快照为7或3而不是2、parent/victim对象身份和name、缓存移除、正确删除回调计数。失败回调不改变状态，要求Err且缓存对象仍在；不把内部已构造快照当成功提交。

getter计数及删除入口记录要求victim getattr已发生且仅一次。固定源码`fs/kvfs/src/node/inode.rs:2041`直接委托getattr，不把返回metadata写回缓存，因此可区分7与3；读取identity不触发后端。此观察是单线程回调顺序，不证明namespace锁持有、并发安全或引用释放顺序。fixture本身持有victim引用，不能用它验证RemovedEntry独自pin住对象的生命周期。

静态核对依据：`fs/kvfs/src/mount.rs:1625/1676`、`fs/kvfs/src/node/dentry.rs:1214/1247`、`fs/kvfs/ut-tests/mount.rs:156/172/321`。首轮接入编译失败暴露普通helper的断言返回类型问题：unittest宏直接返回TestResult。当前版本已令helper显式返回TestResult，所有入口用is_ok断言传播，双场景入口不忽略首个结果。原失败fixture和日志保留在removal-factorial-01；修正版在02重新冻结。执行结论见[配对控制实验](../notes/2026-11-17-removal-event-controls.md)，本说明不代替运行日志。

四cell建议为original-observed、candidate-observed、mutant-old、mutant-observed；旧original 297项为另存基线，不能冒充本次新增义务已覆盖。若mutant仅将getattr失败回退改成None、保留成功分支，预期两个`removal_event_*_cached_fallback`击中Some(3)与None差异。删除失败场景只要求Err，不应期待它们也击中该变体。mutant-old是否通过由实跑决定，不预填结果。该变体检验实现兼容性，不裁决缓存回退政策优于None。
