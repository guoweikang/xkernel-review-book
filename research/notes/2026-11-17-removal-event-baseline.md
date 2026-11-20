# 删除事件快照：融合候选与真实内核基线

## 候选为何值得确认

共同预算队列索引7为`unlink_with_pathname_tracked/rmdir_tracked`，属于本次固定top20预算下融合独有的两对之一。代码中存在相同RemovedEntry构造及getattr失败回退，是检查文档/代码多视角候选是否带来可用局部机制的下一对象。它不是文档独自发现的结果，也不因融合独有就成为有价值重构。

检索`research_lookup.py RemovedEntry unlink_with rmdir_tracked --limit 6`；实际读取固定语料mount/dentry/types/namei，随后对同一Git版本查阅POSIX消费者及node_dentry、mount测试，复用pagecache原内核测试运行方案。Goodall并行只读核查锁范围、消费路径及既有断言；其审阅没有冒充执行结果。

## 原始证据链

固定`7e3ac94431a0dbb376d2fc8d85098deeff1bba09`，以下为此版本路径和起始行，不是当前生产工作树结论。

|位置|直接观察|对抽取的约束|
|---|---|---|
|fs/kvfs/src/node/dentry.rs:1214|父namespace锁→查实际victim→victim锁→验证闭包→底层unlink|快照不能提前独立lookup或移出锁；不能合并类型政策|
|fs/kvfs/src/node/dentry.rs:1247|相同锁顺序，但调用rmdir及目录类型检查|目录是否可删仍归原后端，不以缓存子项替代|
|fs/kvfs/src/mount.rs:1651、1684|闭包中构造parent/name/victim引用及删除前nlink|helper仅承载此局部机制，不移动权限、sticky、mountpoint检查|
|fs/kvfs/src/types.rs:162|结果持有parent和victim引用|保持对象身份和引用寿命，不只比较数值字段|
|posix/fs/src/namei.rs:93|tracked删除成功后才继续构造通知对象|构造快照不等于删除提交；后续删除错误仍返回Err|

**明确的文档—实现差异：**mount与types部分旧说明称getattr失败只放弃retirement判断；实际两处生产者均返回`Some(getattr成功的nlink或identity缓存nlink)`。消费端还有`unwrap_or(1)`，不能把它混同于生产者getattr失败分支。这是当前材料的不一致，不据此认定实现bug、Linux不兼容或自动修复政策；重构应先保持实际语义，文档政策另行澄清。

## 本轮真实执行

`scripts/run_kvfs_original_tests.py`复用先前隔离且未改的归档源码和默认配置；执行前后逐一核对3634普通源文件，均无变化。使用新的私有128MiB ext4磁盘，不复用已写入磁盘；Rust 1.95.0、离线Cargo、4编译任务、QEMU TCG、2 vCPU、1GiB。命令为原`make unittest UNITTEST_CRATE=kvfs ACCEL=n NET=n BLK=y VSOCK=n SMP=2 MEM=1g DISK_IMG=...`。

协议、执行器、关键源码、编译/启动日志、逐测试结果及摘要保存在`research/evidence/runs/2026-11-17-kvfs-original-01`。协议在测试前固定，单次300秒上限；本次正常退出0、未超时。独立检查脚本`check_kvfs_original_tests.py`核对全部归档摘要及逐项结果，不只读取汇总。

**297个唯一测试通过、0失败、0忽略**，存在ALL_TESTS_PASSED和COVERAGE_PERSISTED标记；配置不变。包含实际victim验证闭包、rmdir后端选择、只读拒绝和sticky拒绝等关注用例。本轮未运行POSIX通知端到端测试，coverage落盘不是业务事件正确性证明。

## 测试真正覆盖了什么

- node_dentry现有测试能检查验证闭包拿到实际victim、拒绝后不执行底层unlink、缓存保留。
- rmdir现有测试区分目录删除回调与unlink，并验证缓存移除。
- mount现有测试覆盖只读与sticky拒绝等路径。
- **缺口仍在：**这些断言没有直接验证tracked结果的parent/name/victim身份、删除前nlink和getattr失败回退。现成mount MockDirOps固定getattr成功且nlink=1，单纯297项通过不能覆盖该分支。

## 下一实验的可执行边界

在新的隔离副本中扩展既有fixture，而不是改生产或建立通用模拟器。原实现与局部helper候选使用同一组新增断言：成功结果身份；后端nlink与缓存刻意不同；getattr失败采用缓存；底层删除失败不交付成功结果。已有拒绝路径继续保留。

先让原版新增观测通过，再跑候选。候选仅替换闭包内快照构造，不改unlink/rmdir控制流、不移动锁与副作用。若既有fixture不能观察某字段，应记录未覆盖并补对应观测，不能用模型意见代替。结束条件为这些分支及原测试的原版/候选结果留存；不扩成inotify全链路或通用竞态研究。

当前**只完成原版基线及覆盖缺口分析**；未实现事件helper、未运行新增断言、未证明其安全或收益。路径支线已收束，本批转向实际融合增量的确认，不声称方法整体有效或达到专利申请成熟度。
