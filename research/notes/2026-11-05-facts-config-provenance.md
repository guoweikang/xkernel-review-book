# CI3885 facts 配置来源与可恢复边界

日期：2026-11-05。内核固定 SHA：`7e3ac94431a0dbb376d2fc8d85098deeff1bba09`。下述源码路径/行号均由 `git show <SHA>:<path> | nl -ba` 读取，未切换或修改内核工作树。先读 [execution-readiness](2026-11-05-execution-readiness.md)，本轮不重复其 exporter/压缩文件校验，不运行配置生成、编译、检测或 CI，不安装依赖、不访问凭据；仅新增本笔记。

## 1. 是否有匿名完整 .config：必须区分三种证据

**已有材料：**直接读取本地 `research/evidence/originals/T11-ci-3885/` 的双平台 manifest；该目录仅有两份 status、两份 manifest 和一个 klazy 压缩文件，没有完整 `.config`。前一轮笔记报告这些文件曾从匿名 CI 成功取得并校验；该在线成功与校验结果属于沿用记录，不冒充本轮重验。

**源码约定：**`Jenkinsfile:576` 的常规归档包括 summary 和 facts；`:590` 的诊断归档包括 artifacts/logs/test 输出；`:349` 的 leg 输出 stash 同样未直接列出 Dylint 工作目录下的 `.config`；`:1021` 的早期 facts 归档只抓 facts 输出目录。`xtask/xkmake/src/facts.rs:148` 的 manifest 只有配置摘要和选定字段，`:393` 读取配置字节后计算 SHA-256，没有在这里把原文件复制到 facts 包。因而**已核对的固定源码没有提供完整 Dylint .config 的直接归档路径**。这不是对 Jenkins 实例插件、额外上传或所有归档目录内容的穷尽证明。

**本轮在线核对受阻：**尝试匿名 GET 官方 [CI3885 构建](https://jenkins.openkylin.top/job/x-kernel-ci-test/3885/) 对应的 [制品清单 API](https://jenkins.openkylin.top/job/x-kernel-ci-test/3885/api/json?tree=number,result,artifacts%5BfileName,relativePath%5D)。网页工具无法访问；curl 报 `SSL certificate problem: certificate has expired`，未取得清单。未关闭证书校验、未降级 HTTP、未携带凭据。因此不能写成“已在线确认3885没有.config”或“匿名权限拒绝”；准确结论是：**现有本地材料不含、源码未安排直接归档，而本轮无法确认在线完整清单。**

官方 facts 原始入口：[aarch64 manifest](https://jenkins.openkylin.top/job/x-kernel-ci-test/3885/artifact/artifacts/facts/kplat-aarch64/manifest.json)、[x86_64 manifest](https://jenkins.openkylin.top/job/x-kernel-ci-test/3885/artifact/artifacts/facts/kplat-x86_64/manifest.json)。本轮字段核对以先前归档字节为准，不表示这些 URL 现在均可访问。

## 2. 固定源码中的配置生成链

1. `Jenkinsfile:453`、`:461` 分别指定 `platforms/kplat-aarch64/qemu_defconfig` 和 `platforms/kplat-x86_64/qemu_defconfig`。`:1006` 复制到扫描工作区 `.config`，依次执行 `make defconfig`、`make dylint_test`、带 `FACTS_OUT` 的第一次普通配置扫描。
2. `Makefile:82` 使用本仓库 `xtask` 中的 xconfig/xconf；`:246` 将 `.config` 作为种子，配合根 `Kconfig` 和 `--srctree .` 展开。不是只复制 defconfig 就完成配置。
3. `xtask/xconfig/src/cli/defconfig.rs:23` 创建配置引擎、加载种子、刷新选择/可见性/派生默认值、清理不活动项并写产物。`xtask/xconfig/src/config/engine.rs:437` 同时写 `.config`、`auto.conf`、`autoconf.h`。
4. Dylint 建立 BuildContext 时还会走 `prepare_kernel_config`（`xtask/xkmake/src/context.rs:44`）；后者重新加载引擎并写配置产物（`xtask/xconfig/src/build_config.rs:189`）。因此精确匹配不能只假设 defconfig 初次展开的字节就是最终快照。
5. `xtask/xkmake/src/dylint.rs:103` 把实际 config 路径传给打包器；`xtask/xkmake/src/facts.rs:393` 在打包时读文件字节，`:403` 保存 `config_sha256`，同时记录解析后的 target/profile/features 等。

后续 aarch64 `UNITTEST=y` 扫描与追加 `KFEAT_LOCK_STAT=y`、`olddefconfig` 的扫描发生在普通包完成之后（`Jenkinsfile:964`、`:970`、`:1011`），且不再传 FACTS_OUT。**若事后拿到阶段结束的 aarch64 .config，它可能已经是锁统计配置，不一定对应已归档普通 facts。**独立单测构建又使用 `prepare_unittest_config.sh` 和 `UNITTEST=y VSOCK=n NET=n`（`Jenkinsfile:1062`），不能拿那份配置代替 facts 配置。

## 3. 当前可直接恢复的内容

| 内容 | 已有证据与恢复程度 |
| --- | --- |
| 扫描源码版本 | 两份归档 manifest 的 commit 均为本文 SHA；base 为 `61e2e280f8b9494b58ab2cdc69e5e0eede60113d`。这是产物声明，不是完整构建供应链证明 |
| 平台、target、profile | 分别为 kplat-aarch64 / `aarch64-unknown-none-softfloat`、kplat-x86_64 / `x86_64-unknown-none`；两者均 release |
| 扫描开关与工具链 | 两者 `unittest=false`、`deps=true`、`toolchain=nightly-2026-03-08`、`rustflags=["--cfg","unittest"]`。cfg 与 unittest feature 不是同一开关，也不代表运行过单测 |
| Cargo features | 可从两份 manifest 完整读回所记录列表；例如两平台均含 net/tee/vsock，aarch64 还含 snapshot/watchdog/nmi。只是 manifest 的显式 feature 参数，不是完整 Kconfig 或每个依赖的全部构建条件 |
| 输入种子原文 | 可直接从固定 Git 对象取回两个 qemu_defconfig，包含显式开启/关闭、地址、栈大小等原始设定。例如 aarch64 `qemu_defconfig:8` 起机器/引导设置，`:18` 起图形输入开关，`:47` 起 PCI；x86_64 `qemu_defconfig:8` 起架构/机器，`:38` 起 PCI |
| 默认值与派生规则 | 固定 `Kconfig`、其 source 链和 xconfig 实现提供重建依据；例如 `Kconfig:35` 的 release 默认、`:53` 的 warn 默认可静态确认。但“知道默认规则”不等于所有有效值已逐项求出并核对 |

两份 manifest 的配置字节摘要分别为：

```text
aarch64  6dcda3e5b4c7ad3eb97f2c97d5e647df74c1d4322325d2e56b75278de224b2eb
x86_64   d7d83167755b94104c8fb7ce32edfd3b7130fc5a45c7c284b2c6ebac9a9749c6
```

## 4. 哪些只能有条件重建，哪些不能倒推

**有源码支撑的重建路线，但本轮未执行：**以该 SHA 的完整源码、对应平台种子和同版 xconfig，重放 defconfig 展开及构建前配置准备，生成候选完整 `.config`，再与上述摘要比较。`xtask/xconfig/src/config/writer.rs:15` 写固定头部，`:20` 按名称排序，`:38` 起按类型规范输出；所读 writer 不插入时间戳，这使逐字节比对具有实际依据。但本轮未审计所有求值/环境输入，也未运行该路线，**不能宣称已成功精确恢复或只需读种子就足够**。将来摘要不一致时，应保留不一致而不是手工改写 manifest。

**不能从 manifest 唯一反推的部分：**`config_sha256` 不是配置内容；feature 映射有信息丢失。`xtask/xconfig/src/build_config.rs:343` 只提取特定前缀、值为 y 的符号，还跳过 `KFEAT_FS` 和两种 virtio bus 标记；`xtask/xkmake/src/build.rs:388` 再加 `kfeat/` 前缀及可选 unittest feature。由此无法仅凭 features 还原所有关闭项、整型/字符串/地址、隐式默认值或完整配置序列化。种子中的非 feature 设置可取回，但要与其他 Kconfig 规则共同解析，不能直接标为 CI 最终生效值。

**本轮仍无法恢复/证明：**当时 CI 完整环境、未记录参数、实际工作树是否被额外修改、每次中间配置快照、运行时设备树/命令行设置，以及包外配置扫描结果。即使日后 `.config` 摘要匹配，也只确认配置文件字节一致，不覆盖全部 Cargo/rustc 环境、运行状态和 facts 语义正确性。源码给出正常流程，不能证明线上任务没有额外设置；同样，本轮未看到额外设置也不能虚构它们存在。

## 5. 收束结论与复查记录

相较 execution-readiness，新增结论是：配置不是不可恢复的黑箱，**平台种子、固定求值实现、产物摘要和显式扫描参数均已定位，可规划有校验目标的离线重建**；但完整 `.config` 原件仍未取得，精确重建仍未验证。当前应标记“配置来源可追溯、完整快照待取得/重建比对”，不能标记“已恢复完整配置”。

实际只读操作：阅读既有笔记及两份归档 JSON；`git show` / `git grep` 定向查询上述 Makefile、Jenkinsfile、xconfig、xkmake 和平台种子；匿名 GET 只请求构建制品清单。curl 命令为 `curl -g -q -fsSL --max-time 25 'https://jenkins.openkylin.top/job/x-kernel-ci-test/3885/api/json?tree=number,result,artifacts[fileName,relativePath]'`，本轮 TLS 失败后未绕过校验；后接 JSON 解析报错只是无响应正文的后果，不是 CI 清单为空。后续可在独立目录执行配置生成与摘要比对，不必等待在线清单恢复；本轮未运行配置生成或摘要比对，不再在线重试。
