# 测试目录元数据：从相似配对到最小研究补丁

## 已有能力不能直接套用

固定X-Kernel提交`7e3ac94431a0dbb376d2fc8d85098deeff1bba09`，候选为SCC file_id 1571/1732。
在kvfs范围搜索metadata构造、测试支撑名称，并阅读实际实现后，未找到可直接替代两个目标getter的公共测试构造函数。这是限定范围结论，不证明全仓没有同类能力。

- `ut-tests/node_inode.rs:76`的fill_metadata从对象锁内状态复制再覆盖字段，不是无状态目录默认值。
- `src/nullfs.rs:68`的metadata用于具体文件系统：nlink=2、权限0555、blocks=0等，与目标getter的nlink=1、默认权限、blocks=1不同。
- `src/node/inode.rs:891`一类fill_metadata读取实际owner、times、mode等状态，不能为复用而用它替换测试固定值。
- `src/types.rs:204`的Metadata是字段结构；当前读到的定义没有可直接表达本测试默认组合的公共构造器。

不能将“同样返回Metadata”当成可替换证据，也不应向生产类型增加只服务这两个测试的默认策略。

## 共享边界与必须保留的差异

[两文件契约复核](2026-11-05-metadata-fixture-contract.md)确认两个目录getter的13个字段构造相同，仅inode来自各自对象；两个mock的状态与操作能力不同。
尤其需要保留：node_dentry的inode初始化helper使用block_size=4096，而目标getattr返回512。此次提取不判断这种差异是否合理，更不擅自统一。
mount测试还通过后续流程生成synthetic device identity；共享构造器继续返回原来的device=0，不预先填入期望答案。
测试预期继续由原测试断言表达，不能调用同一个新helper同时生成actual和expected以制造自证。

## 候选补丁

研究补丁保存在`research/evidence/runs/2026-11-05-metadata-fixture-patch-02/candidate.patch`，**没有应用到内核工作树**。

| 文件 | 修改 |
| --- | --- |
| fs/kvfs/ut-tests/support.rs | 新增纯构造directory_metadata(inode)，每次返回新Metadata值 |
| fs/kvfs/ut-tests/mount.rs | 仅目标getter的Metadata表达式改为调用helper |
| fs/kvfs/ut-tests/node_dentry.rs | 同上，不改变其他getter／mock状态 |
| fs/kvfs/src/lib.rs | 用现有path_mod_test宏声明私有test_support模块 |

`util/unittest/src/lib.rs:39`的path_mod_test展开带cfg(unittest)。目标两个测试模块也通过该宏引入，拟议helper沿用既有门控，不新增Cargo feature、Kconfig选项或crate依赖。
helper函数为pub(crate)，容器模块私有；源码设计上不是新增对外生产API。实际配置编译及发布产物是否符合预期仍未验证，不把宏阅读当完整构建证据。

## 已做的机械检查

入口：`scripts/prepare_metadata_fixture_patch.py`。它固定来源SHA和候选映射，确认两个原表达式逐字相同，检查13个字段、唯一inode替换和局部改写可逆性。
补丁在`.build/metadata-fixture/`隔离目录的固定源码副本上执行git apply --check及apply，随后逐文件对比生成方案，均通过。
新helper的Rust 1.95 rustfmt检查通过。第一轮保留显式inode字段名，第二轮改成Rust字段简写并增加替换可逆检查，旧证据保留。

这些检查证明改动范围与文本替换符合计划，**不证明Rust类型检查、模块接线或内核测试已经通过**。没有通过手工替身测试冒充实际kvfs验证。
测试文件其余内容（包括断言、初始化helper、其他mock方法）由固定区间外字节保持确认未改；两个目标mock仍独立。

```sh
python3 scripts/prepare_metadata_fixture_patch.py --repo /root/codes/x-kernel \
  --run-id metadata-fixture-new-run
```

必须使用新run-id；输出保存候选补丁、完整拟议文件、脚本、命令和哈希。不会修改被研究仓库。

## 收益账本，而不是成功标签

可以确认选定的两处13字段构造变为一个实现、两个调用。补丁统计为25行增加、30行删除，净减少5行，涉及四个文件并新增一个测试模块。
这种收益很有限：共同字段维护点减少，但跨文件跳转、helper命名和两个测试对共同默认值的耦合增加。
未取得长期维护成本、缺陷率或独立可读性评价；也没有性能收益主张。不能因自动检索后生成了补丁，就记为“自动优化成功”。
后续[入口核查](2026-11-05-metadata-validation-route.md)已确认模块前缀过滤与静态94项预期集合，日志门禁自检通过；真实内核验证尚未运行。下一步限定为独立固定源码环境预检，并保留相关独立断言。
若验证成本远高于该小改动，或维护审阅认为新模块不值得，就保留可行但未采纳的候选，不扩建测试平台或强推合入。
管道包装等其他线索保持原优先级，不同时启动新的性能排查。

新增模块／类型／宏证据见`research/evidence/runs/2026-11-05-metadata-support-context-01/`；两个测试及所属模块全文已在固定Rust基线sources.zip中。
