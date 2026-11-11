# metadata 测试运行前提：QEMU 与镜像

核查日期：2026-11-05。仅以 `git show`/`git grep` 读取 `/root/codes/x-kernel` 固定提交 `7e3ac94431a0dbb376d2fc8d85098deeff1bba09`；下述路径和行号均属于该提交。不执行 Make、内核工具、构建或测试，不核实本机镜像/QEMU/固件是否齐备；离线 Cargo/config 预检由主线程处理。

## 入口与 `--no-block` 的准确边界

- `Makefile:240–244` 的 `unittest` 转调 `run UNITTEST=y`；`:141–158` 转换为 xkmake 的 `--unittest` 等参数，`BLK=n` 才添加 `--no-block`。`:192–197` 区分普通 `run` 与 `justrun --no-build`；`xtask/xkmake/src/main.rs:85–100` 确认普通 run 先构建 bundle，再调用 QEMU。因此不能把 `make unittest BLK=n` 当成只执行已有二进制。
- `xtask/xkmake/src/qemu.rs:475–509` 仅在 `KFEAT_DRIVER_VIRTIO_BLK` 启用且未指定 `no_block` 时检查 `disk_image.is_file()`、添加 virtio-blk 和 raw drive；非 dry-run 缺文件直接报错，不在此下载。`--no-block` 跳过的是这一外部磁盘设备及文件检查，不是关闭所有存储、清除内核配置或保证测试能启动。`Makefile:99–105` 明确区分 `DISK_IMG` 与编译期嵌入的 `RAMDISK_IMG`。

## ramdisk 与下载：声明不能代替接线证据

- `drivers/contracts/block/src/lib.rs:61–63` 对 `ramdisk_image` 作 feature 门控；启用对应静态模块时，`src/ramdisk_image.rs:26–27,52–54` 通过 `env!`/`include_bytes!` 消费镜像长度与路径。`drivers/contracts/block/build.rs:24–54` 读取的是 **`XKERNEL_RAMDISK_IMG`**，缺环境变量直接返回，给定路径缺文件也不会生成或下载。静态镜像要求独立于 QEMU 的 `--no-block`。
- `ramdisk_image.rs:7–11` 注释称 Makefile 从 `RAMDISK_IMG` 设置上述环境变量；但固定树定向检索未在 Makefile/xkmake 找到该变量的设置，也未找到 unittest 自动调用 `ramdisk_img` 的接线。不能据注释宣称此链已实现；实际启用 feature、环境注入及镜像内容仍需主线程预检。
- `Makefile:276–285` 的显式 `rootfs` 目标在架构/variant 命名镜像不存在时，以 `curl -f -L` 下载 `.xz`、`xz -df` 解压，再复制到 `DISK_IMG`；URL/variant 默认见 `:106–108`。`unittest/run` 的已读入口没有依赖该目标，不能说缺盘会自动下载。`:313–320` 的 `disk_img` 是显式本地 FAT32 创建；`:322–355` 的 `ramdisk_img` 是显式本地创建，已有文件即跳过，ext4 且源 rootfs 存在时用 `debugfs` 抽取 busybox/musl，否则无该填充步骤，再用 `dd` 和对应 mkfs。不要把生成空文件系统等同满足 guest 启动/测试内容要求；本轮均未运行。

## QEMU 与固件

- `xtask/xkmake/src/qemu.rs:76–87` 按架构选择 `qemu-system-*`；`:143–172` 中 AArch64/LoongArch64 走直接 kernel，RISC-V 显式使用 `-bios default`。这只是命令构造，未验证宿主 QEMU 的安装、版本、默认固件可用性。
- x86 默认 Linuxboot（`:202–224`）；选择 UEFI 才进入 OVMF 查找并挂载 UEFI 镜像（`:225–250`）。OVMF 按显式参数、环境变量、候选本地路径查找；缺失报错，无此路径内的下载逻辑（`:264–335`）。非 dry-run 会将 VARS 模板复制到 target 下运行目录（`:277–285`）。`--no-block` 不屏蔽这些 UEFI pflash/IDE drive，它只影响前述 virtio-blk 分支。

结论边界：源码支持“可绕过外部 virtio 磁盘检查”，不支持“无镜像/无固件即可运行 metadata 测试”或“unittest 会自动准备所有镜像”。未验证 guest 初始化是否依赖其他存储、所选配置实际启动路径和测试结果；未作全仓网络行为审计，不能据此保证全流程离线。
