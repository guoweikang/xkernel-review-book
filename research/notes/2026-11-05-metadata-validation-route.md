# metadata候选：真实测试入口与结果验收

日期：2026-11-05。固定源码：`7e3ac94431a0dbb376d2fc8d85098deeff1bba09`。本轮仅核查入口并建立日志门禁，未编译或运行内核。

## 可以复用什么

固定版本的Makefile通过`make unittest`调用`run UNITTEST=y`；xkmake将`UNITTEST_CRATE`传入编译环境，entry读取后交给既有测试收集器。
虽然参数名叫crate，`util/unittest/src/runner.rs`的`module_matches_crate`实际接受完整模块前缀，并要求后续为`::`边界。因此可限定：

```text
kvfs::mount::tests,kvfs::node::dentry::tests_dentry
```

两个模块通过既有`path_mod_test!`接线，测试描述符由`module_path!()`生成。固定源码清单包含mount的57个、node_dentry的37个直接`def_test`函数，没有函数级cfg或嵌套定义。
**94是静态预期数量，不是已执行数量。** 注册、链接、配置是否真正包含它们仍须运行确认。
现有`fs/kvfs/tests/host/path.rs`只覆盖路径函数，不是这些mock的host验证入口；无需另造host替身或测试框架。

七份入口源码及哈希保存在`research/evidence/runs/2026-11-05-metadata-validation-context-01/`。静态测试清单来源为固定的`source-units-v2-verified/inventory.json`，检查器锁定其SHA-256。

## 为什么不能直接使用现成工作树

观察时`/root/codes/x-kernel`的HEAD是`46beed4e75b5e4a65e77cdf50b3230b9b391ca6b`，不是研究快照；现有`.config`为aarch64 release配置。已有xkmake二进制的构建来源不明。
环境中有x86_64和aarch64 QEMU可执行文件，但这不证明所需工具链、磁盘镜像、固件和依赖齐全。没有执行已有二进制，也没有修改该工作树或配置。

下一步在独立固定源码副本中检查前置条件：同版本xconfig解析平台种子，记录最终配置、生成Cargo配置、锁文件、工具链与QEMU版本；原版和候选使用独立输出目录及相同输入。
候选只允许包含已归档patch。先验证原版，再验证候选；缺失依赖或原版失败必须单列，不能归因于候选。
计划与命令见`research/protocols/metadata-validation-plan-v1.json`，命令尚未执行。不得自动下载镜像、修改用户镜像，或为净减5行的候选扩建验证平台。

## 把“测试通过”固化为可检查条件

`scripts/check_metadata_test_log.py`要求：命令退出码为0、恰好一个成功标记、没有失败标记，且94个预期完整测试名各出现一次、全部为ok。缺失、额外、重复、ignored或FAILED结果均不能通过。
这样避免只看到成功横幅，却实际漏跑目标测试。内核原runner允许ignored，研究验收采用更严格的条件。

```sh
python3 scripts/check_metadata_test_log.py --self-check
python3 scripts/check_metadata_test_log.py --log original.log --exit-code 0
```

第二条命令的退出码必须来自真实运行进程，不能人为填0。自检已接受合成的94项正常日志，并拒绝10类负对照，包括缺测、重复、跳过、失败、额外测试、空成功、超时及矛盾标记；记录保存在入口证据目录的`log-gate-self-check.log`。
这验证的是日志检查器，不是kvfs。日志门禁还不能证明运行来源正确：源码、补丁、配置和命令身份仍须单独核对。

即使两版测试通过，也只支持该配置下的已覆盖行为；不能自动得到全配置等价、生产构建无影响或抽象值得采纳的结论。生产构建隔离和维护收益需另外检查。
