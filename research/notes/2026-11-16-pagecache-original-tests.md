# 写回确认：原内核测试执行与环境对照

## 问题与方法

确认阶段不能一直依赖抽取夹具。对[提交与完成责任](2026-11-16-completion-responsibility.md)的四项命题，本批先检查固定工程原测试能否执行，再判断哪些命题还缺观测，不修改生产实现或先造模拟器。

对象固定为 xkernel `7e3ac94431a0dbb376d2fc8d85098deeff1bba09`。从 Git archive 提取到独立临时目录，采用原 `platforms/kplat-x86_64/qemu_defconfig`；只在该目录展开配置。Rust 1.95.0、QEMU 10.0.11、TCG、2 vCPU、1 GiB；Cargo 离线、4 个编译任务。`UNITTEST_CRATE=pagecache` 是运行筛选，不是只编译该 crate。

协议依次冻结为 `research/protocols/pagecache-original-tests-v1.json` 与 `pagecache-disk-control-v1.json`。第二协议在第一批失败后制定，属于环境诊断对照，不是事前两臂效果实验。没有依赖下载、源码补丁或共享根配置变更。

## 两次执行

|条件|实际执行|结果|解释|
|---|---|---|---|
|原默认配置，QEMU 不接 block/net/vsock|配置展开、内核编译、QEMU 启动|`fs/boot/src/lib.rs:578` 报 `No block device found!`，make 返回 2|默认 FS 初始化要求根块设备，测试尚未开始；不是 pagecache 测试失败|
|同一源码与配置，仅接新建的私有 ext4 磁盘|原 unittest 入口及 coverage 导出|**68 passed、0 failed、0 ignored**，make 返回 0|四个写回关注用例均有逐项 `RESULT ... ok`，不是只看进程退出|

第二次使用 128 MiB 空 ext4 文件，关闭 metadata_csum/64bit 格式特性；不是下载的发行版镜像。net/vsock 设备仍关闭，不表示所有内核功能或设备均关闭。初次配置耗时 17.143 秒，首轮构建加启动 265.680 秒；不是性能基准。成功条件只执行一轮，尚无重复运行稳定性结论。

程序核对 68 个唯一逐项结果、汇总总数和状态标记。原测试输出 `ALL_TESTS_PASSED` 及 `COVERAGE_PERSISTED`，随后导出 coverage。**没有把覆盖率数值当契约正确率，也没有评价覆盖充分性。** 对提取源码中 3,634 个归档普通文件逐一比较 SHA-256，未发现变化；展开后的配置前后相同，原根及 xtask 锁文件未变。

## 能支持什么

|命题|本批支持|仍不能推出|
|---|---|---|
|交付返回不等于完成|`submitted_snapshot_outlives_scan_and_preserves_redirty_and_failed_tail` 在真实内核测试环境通过，含返回后未完成状态、快照及重脏断言|任意调用者都遵守 drain 责任；任意配置成立|
|后续拒绝不结束先前持有批次|`rejected_submission_redirties_its_batch_without_ending_prior_io` 通过|这里没有真实设备请求；不能称设备 I/O 故障注入|
|完成凭证及锁边界|`completion_borrows_index_until_last_writeback_finishes`、`writeback_completion_finishes_without_acquiring_the_content_lock` 通过|所有并发交错及锁序均安全|
|拒绝批次是否扣预算|原测试执行成功，但仍使用匿名 `&mut 2`，没有最终预算断言|不能以通过替代缺失的观测；该语义当前仍主要来自源码|
|完成是否持久化|原类型文档明确不保证；本批无持久化命题测试|coverage 写盘成功不是业务数据 crash durability 证明|

这一步把“已阅读原断言”推进到“原工程中确实执行并通过”，不是重复检测算法准确率、重构收益或论文方法复现。测试只支撑具体断言；已有代码中的测试本身也不是独立人工语义标签。文档提供者可以被要求明确预算事件、交付与完成、失败路径 drain 归属，再与实际断言绑定。

## 可复核材料

- 失败批次：`research/evidence/runs/2026-11-16-pagecache-original-01/`，含冻结协议、runner、配置、环境、完整命令日志、锁文件摘要和检查结果。
- 成功对照：`research/evidence/runs/2026-11-16-pagecache-disk-01/`，含建盘日志、完整 run/qemu 日志、父报告身份、全源码比较计数、检查结果和补充摘要。
- 原始实现和测试：`research/evidence/runs/2026-11-16-completion-sources-01/`。运行入口判据来自固定源码 `entry/src/main.rs:57`、`:293`；xkmake 另在 `xtask/xkmake/src/coverage.rs:44` 验证 guest 标记，不仅判断 QEMU 退出。
- 本地大材料：`research/evidence/originals/2026-11-16-pagecache-kernel-01/` 保存源码 tar、符号 ELF、原始 coverage profile、coverage.info/txt。成功批次 `local-originals.json` 给大小与 SHA-256。此目录受 Git 忽略，**未上传 GitHub**；可复核命令、日志、摘要在 run 目录，未声称仓库已完整远端备份。
- 检查器：`python3 scripts/check_pagecache_original_tests.py research/evidence/runs/2026-11-16-pagecache-disk-01`。初次 runner 接收新 run-id；disk-control 是本批固定 ID，已有目录即拒绝覆盖，不是任意项目通用执行器。

## 下一项判别实验

在另一隔离副本保留原测试基线，把拒绝测试的匿名预算改为可观测变量并新增预算断言；再对“交付前扣减 / 接受后扣减”的受控实现变体比较。事前固定应区分的声明、断言和预期反例，不把变体混入原测试通过记录。若不能区分，先检查断言映射，而不是提高语义评分。之后才评估这些证据对候选共享边界判断的增量价值。

目前仍未达到专利候选交接准备度：原测试执行是证据基础工作，并非新的机制或优于已有方法的效果证明。
