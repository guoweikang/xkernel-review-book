# 执行准备核查：实际 facts、工具与资源缺口

日期：2026-11-05。只读获取与制品完整性检查，不是候选检测、基线性能测试或优化实验。
本轮没有触发 CI、安装依赖、运行内核构建、调用模型 API 或提交源码给外部模型。
跨项目身份核查另见 [Rust OS 仓库记录](2026-11-05-rust-os-identities.md)。

## 1. 实际 facts 已能取得

按 X-Kernel `docs/ai/skills/pr-ci-review/SKILL.md` 及 API reference 指引访问匿名只读 Jenkins API。
查询时最新构建为 3887（运行中），3886 为失败，选择当时最近成功的 **3885** 获取制品。
这是一次准备检查样本，不是统计抽样，不代表失败构建没有可用 facts。

入口：[构建 3885](https://jenkins.openkylin.top/job/x-kernel-ci-test/3885/)。
制品前缀为该构建的 `artifact/artifacts/facts/<platform>/`。
取得两平台 `status.json`、`manifest.json`，以及 aarch64 的一个 klazy 压缩事实文件。
原始字节保存在 `research/evidence/originals/T11-ci-3885/`，五份文件的 URL、大小及哈希登记到 manifest。
该目录保持 local-only，不随 book 发布；CI 可能清理历史构建，本地副本不依赖后续在线保留。

| 属性 | aarch64 | x86_64 |
| --- | --- | --- |
| status | ready | ready |
| manifest missing | 空列表 | 空列表 |
| schema | xkernel-facts/0.3 | xkernel-facts/0.3 |
| crate 记录条目 | 343：workspace 148、dep 195 | 349：workspace 145、dep 204 |
| target | aarch64-unknown-none-softfloat | x86_64-unknown-none |
| 提交 | 两者均为 `7e3ac94431a0dbb376d2fc8d85098deeff1bba09` | 同左 |

这些条目不是 A1 的 213 个 manifest 的同一分母：版本不同、配置范围不同、含外部依赖。
不能相加成跨平台唯一 crate 数，也不能用它们直接计算全仓覆盖率。
实际制品提交不同于 A1 的 `7314469a4dc1c478ca17403745cbd65f86805c89`；后续实验须选定统一版本，
不能把新 facts 与旧源码清单拼在一起。`7e3ac944` Git 对象已在本地存在，未为此切换工作树。

## 2. 已做与未做的校验

已完成：

1. 两份 manifest 原始字节 SHA-256 与各自 status 中的 manifest_sha256 相符；commit 也一致。
2. 重算 exporter 摘要：按 `xtask/xkmake/src/facts.rs` 所定义的
   `tools/lints/{Cargo.toml,Cargo.lock,rust-toolchain.toml,src/**}` 内容哈希与排序规则计算。
   A1 固定快照、制品提交、manifest base `61e2e280f8b9494b58ab2cdc69e5e0eede60113d`，以及
   本轮观察到的 origin/main `98520f0d06b9055beb3a8b9dfd981ad7b687fb52` 四份树结果一致。
   共同摘要为 `08302a409c31a4706949d84bcc2fa4f013bdd2b59826a3ced3e3901a261e2b53`。
3. klazy 样本压缩 SHA-256 与清单一致：
   `4f70705cdfa2478a3bf6a79308657928433e543ea7aa1bca286646ca3b0c97a6`。
   压缩大小 11,132 字节，解压 136,204 字节，逐行 JSON 解析得到 424 条，与 manifest 一致。
4. 样本首记录为 crate 头（klazy、指定 target、schema），末记录为 counts。
   使用已有 `libzstd.so.1` 经 Python ctypes 解压，设置输出大小上限并检查解压错误，无新依赖安装。

以上确认文件一致性及 exporter 输入源码一致，**不是构建供应链证明或事实语义正确性证明**。
未下载/校验全部 crate 文件，未核对每条边与源码、未审计编译环境；未验证完整跨配置覆盖。
stats 的导出计数也不能直接当实际运行调用次数。

特别注意配置：manifest 中有 `config_sha256`、features、rustflags，不存在名为 config 的完整对象。
`unittest: false` 同时出现 `rustflags: ["--cfg", "unittest"]`；源码将该 cfg 作为 Dylint 扫描参数。
因此不能凭布尔字段认为所有测试相关项都被排除，也不能凭 cfg 判断运行了单测。
本轮尚未取得与 config_sha256 对应的完整 .config，精确重建所有配置取值仍是缺口。

匿名复查示例（不触发构建）：

```sh
curl -g -fsSL --max-time 25 \
  'https://jenkins.openkylin.top/job/x-kernel-ci-test/api/json?tree=builds[number,result,building],lastBuild[number]'
curl -fsSL --max-time 25 \
  'https://jenkins.openkylin.top/job/x-kernel-ci-test/3885/artifact/artifacts/facts/kplat-aarch64/status.json'
```

首次查询未关闭 curl URL glob 导致 bad range，修正为 `-g` 后成功；该本地命令问题不是权限或 CI 故障。
未使用证书绕过、凭据或任何状态变更端点。

## 3. 本机工具实际情况

| 项目 | 已核实 | 对执行的影响 |
| --- | --- | --- |
| Rust 默认工具链 | rustc/cargo 1.97.1 | 不等于项目固定工具链，不能默认直接用于构建 |
| 项目工具链 | 1.95.0 已安装；rust-src 等组件已安装 | 与 A1 rust-toolchain.toml 可对应，未验证整个构建链 |
| rust-analyzer | 默认 shim 运行失败；`rustup run 1.95.0 rust-analyzer --version` 成功，版本 1.95.0 | 不是完全缺工具；尚未测试其索引/导出工作区能力 |
| Dylint 所需 nightly | nightly-2026-03-08 已在本机 toolchain list | 本轮未运行 driver 或 lint，不声称提取环境可直接工作 |
| Python | 3.13.5 | 足够执行现有盘点与 JSON 工具 |
| tree-sitter | 命令未找到；Python tree_sitter/tree_sitter_rust 未发现 | 若选此解析路线需要单独固定版本和安装验证 |
| syn | 本地 Cargo 缓存有多个版本 | 缓存不是现成提取器，也不证明宏/语义解析足够 |
| zstd | CLI 与 Python zstandard 未发现，系统 libzstd 可用 | 已可读取小样本；正式批量读取实现尚未选定 |
| 本地模型 | Python torch/sentence_transformers 未发现；nvidia-smi 命令未找到 | 不宣称机器一定无 GPU；本轮未建立可用本地 embedding 环境 |
| 外部模型 | 未测试服务、未查看或使用 API 凭据 | 需明确模型、费用及数据外发范围；不能自动沿用当前会话为批量研究后端 |

检查使用 command -v、版本输出、rustup component list、Python find_spec 和限定目录的缓存清单。
未读取密钥、启动服务、安装组件或探测带认证的模型端点。

## 4. 执行准备结论与下一步

| 条件 | 状态 | 下一动作 |
| --- | --- | --- |
| facts 获取入口 | 已打通，双平台元数据和单 crate 样本通过完整性检查 | 固定研究提交，再按需要获取该版本其他文件 |
| 配置与源码对齐 | 提交可定位，完整 .config 未取得 | 获取配置快照或明确可恢复范围，避免混用 A1 快照 |
| Rust 解析路线 | 有工具链和可运行 rust-analyzer，但未验证提取接口 | 比较最小源码解析与编译索引的适用范围，先定对象清单 |
| 模型路线 | 未就绪 | 词法基线准备不受此阻塞；语义路线等待模型与预算/外发条件明确 |
| 多仓对象 | 官方身份已有初查，Starry 新旧承载需要区分 | 使用固定 SHA 核对新布局；共享组件不能当独立测试样本 |
| 标注与试点 | 尚未启动 | A 阶段评审后制定 B 的案例与标注；本轮制品检查不算重复发现实验 |

此前“尚未取得实际 facts”的缺口已部分关闭，不能再概括为完全没有产物；
但也不能因一个样本可解析就宣布完整数据底座和检测工具已经可用。
