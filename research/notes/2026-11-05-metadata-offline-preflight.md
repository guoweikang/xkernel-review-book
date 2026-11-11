# metadata验证：固定源码离线预检

日期：2026-11-05。研究版本仍为`7e3ac94431a0dbb376d2fc8d85098deeff1bba09`，没有修改内核工作树或运行内核测试。

## 已实际完成

新增`scripts/preflight_metadata_validation.py`，从指定Git提交导出隔离源码，清理继承的Cargo/Rust/Git环境变量，指定本地Rust 1.95.0、独立target和离线模式。Git目录上溯被限制在隔离目录，避免构建入口误操作book仓库。

```sh
python3 scripts/preflight_metadata_validation.py --repo /root/codes/x-kernel \
  --run-id metadata-preflight-new-run --resolve-config
```

每步限时120秒；首次错误停止，不自动补依赖或下载镜像。记录命令、退出码、源码归档哈希、锁文件哈希、版本日志及结果工件哈希。复跑必须使用新run-id。

| 项目 | 实际结果 | 不能据此推断 |
| --- | --- | --- |
| Rust工具链 | rustc 1.95.0，LLVM 22.1.2 | 所有目标编译通过 |
| QEMU版本 | x86_64 QEMU 10.0.11 | 内核能够启动 |
| xtask及kernel依赖解析 | cargo metadata --offline --locked均退出0 | 所有feature组合或build脚本能够构建 |
| 同版本xconfig | 离线构建并执行defconfig，退出0 | 内核已编译或测试已通过 |
| 平台配置 | 从x86_64 QEMU种子生成并保存最终.config | 生成Cargo配置及运行输入已全部就绪 |

最终配置为x86_64 release，启用`KFEAT_DRIVER_VIRTIO_BLK`，不启用静态ramdisk。不能直接执行原计划命令并假设磁盘存在，也不能借用用户工作树镜像。
配置身份为SHA-256 `d7d83167755b94104c8fb7ce32edfd3b7130fc5a45c7c284b2c6ebac9a9749c6`。

## 实验记录及脚本缺陷

- `research/evidence/runs/2026-11-05-metadata-preflight-01/`：依赖预检通过，未尝试配置解析。
- `research/evidence/runs/2026-11-05-metadata-preflight-02/`：所有子命令成功、配置生成，但外层脚本错误地只识别依赖成功状态，返回1。保留原脚本和报告，不把这次退出码解释为xconfig失败。
- `research/evidence/runs/2026-11-05-metadata-preflight-03/`：修正成功状态判断后从新隔离目录完整复跑，外层退出0。配置哈希与02一致。

## 下一项决策

补充[运行输入源码核查](2026-11-05-metadata-runtime-prerequisites.md)：`BLK=n`可跳过外部virtio磁盘检查，但不改变内核配置，也不保证guest初始化成功；默认x86 Linuxboot不走显式OVMF路径。unittest入口没有自动调用rootfs下载目标。静态ramdisk与外部磁盘是不同输入，不能混为一谈。

在启动测试前，明确无块设备模式是否符合测试启动路径，或是否需要专用临时镜像；不得因关闭设备能绕过报错，就认定测试语义不受影响。还需核查同版本xkmake构建、生成Cargo配置、启动固件和构建期输入。
随后才进入原版94项日志验收，原版通过后再跑候选。当前结论仅为离线依赖解析与平台配置生成可行，不是“运行环境全部就绪”或“优化成功”。
