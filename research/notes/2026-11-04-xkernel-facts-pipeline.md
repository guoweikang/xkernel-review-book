# XKernel facts：CI、构建与产物生命周期只读调研

日期：2026-11-04。固定版本：`dc8f8e81224b6733fd05b83fb3f54c5397d261c3`，由 `/root/codes/x-kernel` 中 `git rev-parse 'dc8f8e812^{commit}'` 获取。下述内核路径和行号均指这个 SHA，而非工作树当前内容。

## 结论与核查范围

已有可复用的**按构建配置生产、打包和归档 facts 的生产端链路**，不只是文档设想。它适合作为重复功能识别的候选检索、调用邻域定位和证据回链输入；不能据此认定已有重复功能识别服务，更不能以“未找到相似项”证明不存在重复。

本次实际阅读：`docs/jenkins-pipeline.md`、`tools/lints/README.md` 的相关说明；`Jenkinsfile` 的源码快照、Dylint、归档、提交解析、缓存路径；`xtask/xkmake/src/dylint.rs` 的构建扫描流程；`xtask/xkmake/src/facts.rs` 的身份、选取、校验、状态、打包和 wrapper；`scripts/ci/check_dylint_environment.sh`；Makefile/CLI 参数绑定、构建 feature 计算、exporter 写盘与环境依赖代码片段。提取器的数据流/调用边语义由主 agent 负责，本笔记不作独立完整性背书。

**未运行**构建、CI、测试、提取或消费实验；未下载真实 CI 产物，未访问 Jenkins 实例，未核对 xreview 服务端。本次只读固定版本代码，不 checkout、不修改内核、不子委派；仅新增本笔记。以下“实现”均指静态代码证据，不是线上运行效果。

## 1. 从源码到可下载产物

| 环节 | 已核实实现及代码位置 | 边界 |
| --- | --- | --- |
| 源码快照 | `Jenkinsfile:1245` 清理源码目录、checkout 后以 `git rev-parse HEAD` 设置 `GIT_COMMIT`；`Jenkinsfile:238` stash `.ci/source/**`；`Jenkinsfile:1327` 用 tar 恢复源码快照 | 快照用于各 leg，不能把 Job 取 Jenkinsfile 的 ref 自动等同被分析源码 ref |
| 扫描配置 | `Jenkinsfile:951` 设置每平台独立 target、facts 目录；`Jenkinsfile:1005` 检查环境、复制 defconfig、`make defconfig`、`make dylint_test`、再 `make dylint FACTS_OUT=...` | facts 来自第一次普通配置扫描；后续 aarch64 unittest、锁统计扫描并未打包（`Jenkinsfile:964`、`Jenkinsfile:970`） |
| 构建与导出 | `xtask/xkmake/src/dylint.rs:153` 构建独立 lint 库；`:199` 启动 cargo dylint；`:232` 使用独立 dylint target 与扫描 rustflags；`:237` 启用 facts；`:260` 保存 Cargo JSON 消息 | 不是另一个全仓源码遍历器，受实际编译入口、target 和 cfg 限制 |
| 选择与打包 | `xtask/xkmake/src/facts.rs:324` 按本次 Cargo 消息选 unit，压缩有效 facts，生成 manifest/status；输出 `status.json`、`manifest.json`、`crates/<stem>.jsonl.zst` | 不按 target 目录全量 glob；已有文件不自动代表本次构建单元 |
| 归档 | `Jenkinsfile:1014` 在 Dylint 阶段 finally 尽早归档，失败只记日志；`:349` facts 进入 leg 输出 stash；`:574`、`:621` Post 再归档 | `allowEmptyArchive: true`，且早期归档 `fingerprint: false`；有归档代码不保证每次制品都实际可下载 |
| 保留 | `Jenkinsfile:18` 配置 build 和 artifact 数量各保留 60；`docs/jenkins-pipeline.md:195` 给出 `artifact/artifacts/facts/<platform>/` 地址约定 | 不是持久知识库；实际实例配置、清理结果、可用期未核实 |

CI 的两份普通配置 facts 对应 aarch64/x86_64 的 qemu defconfig，不能因 CI 还有其他构建/测试阶段就推断已有那些阶段的 facts 包。`docs/jenkins-pipeline.md:186` 与 `Jenkinsfile:976` 对“仅第一次扫描打包”一致。

## 2. Commit / config 绑定：已有元数据，不是可信证明

### 2.1 实际被分析的提交

- `Jenkinsfile:1336` 对 PR 选择源仓库、源分支；`:1369` fetch 该分支，`:1393` checkout/reset 到该远端分支，然后记录实际 HEAD。**并非这里主动生成或 checkout PR merge commit。**
- `docs/jenkins-pipeline.md:214` 的 Job 配置写 `pull/${giteePullRequestIid}/MERGE`，描述 Pipeline 脚本来源配置；不得据此覆盖 `checkoutProject()` 实际取源分支的行为。两层来源应分开表达。
- `Jenkinsfile:946` 经 `resolveHeadSha()` 传 `--facts-commit`，后者优先 `GIT_COMMIT`（`:1588`），再退到事件 SHA 等。源分支可能已在事件之后更新，消费端应比较包内实际 commit 与所审查 diff，而不能只按 PR 编号取最新包。
- `Jenkinsfile:1282` fetch 目标分支、检查 merge base；`:1001` 再计算 facts base，计算失败被 `|| true` 容忍，可能不传 base。这里只记录 base，没有自动为 base 再生产一份 facts。
- 本地 `FactsRun::begin` 接受外部 commit，缺省才读 HEAD（`xtask/xkmake/src/facts.rs:275`、`:784`）；CLI 是字符串参数（`xtask/xkmake/src/cli.rs:162`）。所读路径未见提交声明与完整工作树内容的一致性校验，也未见 dirty tree 拒绝。因此 commit 字段不是源码真实性证明。

### 2.2 manifest 的配置指纹

`xtask/xkmake/src/facts.rs:148` 定义、`:393` 填充：commit/base、target/platform/arch/profile、配置文件字节 SHA-256、kernel features、扫描 rustflags、unittest、deps、toolchain、rustc、exporter 信息，以及 crate 清单、missing、counts、时间。

- `config_sha256` 是实际配置文件字节的 hash，不是所有构建输入的统一摘要。
- features 来自 `kernel_feature_flags()`（`xtask/xkmake/src/build.rs:388`）：配置 cargo features 加 `kfeat/` 前缀，并按 context 加 `unittest`。
- manifest 的 `rustflags` 来自常量 `SCAN_RUSTFLAGS = ["--cfg", "unittest"]`（`xtask/xkmake/src/facts.rs:84`、`:405`），不是完整 rustc 命令行录制。普通图仍带这个 cfg；`UNITTEST=y` 所选 optional dependencies 是另一层，见 `Jenkinsfile:962`。
- exporter digest 覆盖 `tools/lints` 下 `Cargo.toml`、`Cargo.lock`、`rust-toolchain.toml`、`src/`，按排序后的路径和内容摘要再 hash（`xtask/xkmake/src/facts.rs:80`、`:750`）。它不是整个内核、xkmake packer、Jenkinsfile 或 builder 镜像的摘要。
- manifest 所列字段没有独立的完整工作树摘要、内核 Cargo.lock 摘要或 builder 镜像 digest。`Jenkinsfile:185` 使用镜像 tag，注释还说明预加载镜像 digest 可能不同。不能据此声称构建完全可复现。

**复用建议而非既有服务实现：**索引至少保留仓库来源、实际 commit、target/platform、config hash、features、profile、unittest/deps、schema、toolchain/exporter 身份与 CI build 定位信息；跨配置合并时保留来源标签，不能只以 commit 为唯一键。

## 3. 缓存与完整性

### 3.1 已有缓存机制

- `Jenkinsfile:190` 把 `/xkernel-target` 放在匿名 volume；Cargo、rustup、rootfs 使用有名卷。`docs/jenkins-pipeline.md:105`、`:120` 明确前者限同一架构 leg 内复用，不跨 Jenkins build 共享编译 target；后者为节点缓存。不能把节点依赖缓存说成跨提交 facts 索引缓存。
- lint 库与内核扫描 target 分开；库构建固定空 `CARGO_ENCODED_RUSTFLAGS` 和自身 target（`xtask/xkmake/src/dylint.rs:416`）。
- exporter 把 `XKERNEL_FACTS` 注册为 rustc env dependency（`tools/lints/src/facts_export/mod.rs:90`）；CI 整阶段保持 facts 和 deps 开关为 1（`Jenkinsfile:976`），减少因开关变化重查。实际加速幅度未测。
- `scan_units()` 不要求 `fresh=false`，所以 fresh unit 也会进入打包（`xtask/xkmake/src/facts.rs:515`）；依赖已有旁路 `.facts.jsonl`。缺失则列入 missing，没有在该打包函数中看到自动强制重编译补齐。
- `deps=true` 通过 rustc wrapper 为内核 target 的依赖启用 exporter（`xtask/xkmake/src/facts.rs:635`）；host build script 等不在这条 target 依赖导出范围。不能解释为所有依赖源码均已覆盖。

### 3.2 状态的准确含义

`xtask/xkmake/src/dylint.rs:61` 在 BuildContext 创建前清旧产物；`xtask/xkmake/src/facts.rs:263` begin 再清理并写 running。扫描失败后仍尝试打包已有结果，setup 失败写 failed/build（`xtask/xkmake/src/dylint.rs:79`、`:95`）。

状态计算在 `xtask/xkmake/src/facts.rs:475`：

- 扫描成功且 missing=0 → ready。
- 否则已有有效 crate → partial；扫描失败 reason=build，扫描成功但缺 facts reason=exporter。
- 否则无有效 crate → failed；packer 本身出错写 failed/exporter（`:307`）。

**关键限制：**ready 仅相对于已被消息解析器选中的 unit。`scan_units()` 会跳过不可解析消息、不匹配消息和不选中的 unit（`:518`）；状态函数并未要求 packed>0，故“成功、零 missing、零 packed”也走 ready 分支。这是静态代码边界，不表示已在真实 CI 观察到空包。

因此 missing 不是全仓遗漏清单；失败时尚未发出 compiler-artifact 的 crate 也不一定在 missing 内。ready 不能证明全仓、全配置、所有函数/调用边齐全。

`dylint::run` 调用 finish 后返回原扫描结果，并未把返回的 Partial 状态转换为错误（`xtask/xkmake/src/dylint.rs:102`）；所以**扫描成功不等于 facts 完整**。第一次 facts ready 后，后续 unittest/lock-stat 或其他 CI 阶段仍可失败，反过来 CI 失败也不必然使那份普通配置 facts 无效。

早期 shell EXIT trap 在没有 status 时写简化 failed/build（`Jenkinsfile:993`），该简化对象没有 commit/target。开始前基础设施失败、强制终止或归档失败仍可能无可用状态；构建结束后 running 应视为未完成。不能把 finally/trap 写法解释成任何故障都保证产物到达。

### 3.3 文件校验不等于内容可信

- exporter 原始文件采用临时文件加 rename（`tools/lints/src/facts_export/mod.rs:149`）；status/manifest 同样采用临时文件再 rename（`xtask/xkmake/src/facts.rs:829`）。压缩 crate 文件直接写入（`:365`），整体目录不是单次事务提交。
- `summarize()` 检查 UTF-8、首行 crate/schema/stem、末行 counts（`xtask/xkmake/src/facts.rs:562`）。**没有逐条解析中间记录并验证关系引用、重算 footer counts 或对全部 header 配置字段进行交叉核验。**
- crate `sha256` 是压缩文件字节的 hash（`:385`）；status `manifest_sha256` 是 manifest JSON 字节的 hash（`:426`）。可供消费端检查下载一致性，但不是签名或独立真实性证明。
- `tools/lints/README.md:99` 明确提示 PR 可以修改 exporter/facts，并要求消费方按可信目标分支 exporter digest 管理信任、把 facts 当提示而非 gate。**这是文档要求；本次未见服务端执行证据。**生产者自己提供的 digest 不能单独抵御恶意伪造。
- 环境检查脚本核对工具版本、安装 receipt、toolchain components/targets 与 driver 可执行文件存在（`scripts/ci/check_dylint_environment.sh:41`）；它不等于对所有二进制做加密认证。

## 4. 对重复功能识别的复用边界

| 可以复用的生产端能力 | 不能由此推断的能力 / 建议补齐 |
| --- | --- |
| 按配置的事实包及代码位置、crate 身份，可作为候选索引输入 | 语义重复判断、行为等价、抽象是否合理、性能取舍均不由归档链路提供 |
| 同一配置本次选中 unit 的清单与状态，可标注证据范围 | 找不到候选只能说“在当前已覆盖范围未找到”；未编译代码、未打包配置和失败遗漏不能作负例 |
| commit/base 字段可辅助选择比较版本 | 未见自动 base 包生成、跨版本增量索引、删除同步、稳定函数对齐；`tools/lints/README.md:126` 也只把键稳定性限定在 commit 内 |
| status→manifest→压缩文件摘要可构成消费校验链 | 需要消费端实际校验身份、摘要、schema、覆盖范围和可信生产者；未核实这些已实现 |
| 两平台产物可保留配置维度开展检索 | 合并去重不能抹去 cfg/架构差异，否则同名或相似函数可能是有意的不同平台实现 |

建议消费者遇到 partial/failed/running/缺包时降级为“证据不足”，并显式显示范围；对 ready 仍校验预期 unit/平台覆盖。若把 partial 中的有效文件用于候选召回，应保留“不完整”标签，不能据此自动免审。这些均是后续接入建议，不是当前服务效果。

## 5. 未验证事项与检索记录

未验证：线上 Jenkins Job 实际配置、成功制品样本、归档延迟/失败率/保留时长、缓存命中与性能、相同源码不同配置的实测隔离、服务端下载重试/鉴权/摘要校验/schema 拒绝/可信 digest 管理、索引更新删除与检索 API、重复功能识别的准确率及免审效果。未完成 extractor 语义边界审计；不要从本笔记推出调用图或数据流精确性结论。

实际使用的只读检索方式（`SHA` 为本文完整固定 SHA）：

```sh
git rev-parse 'dc8f8e812^{commit}'
git ls-tree -r --name-only "$SHA"
git show "$SHA":docs/jenkins-pipeline.md
git show "$SHA":tools/lints/README.md
git show "$SHA":xtask/xkmake/src/dylint.rs | nl -ba
git show "$SHA":xtask/xkmake/src/facts.rs | nl -ba
git show "$SHA":Jenkinsfile | nl -ba
git show "$SHA":scripts/ci/check_dylint_environment.sh | nl -ba
git grep -n -E 'FACTS_|facts_|artifacts/facts|merge-base' "$SHA" -- Jenkinsfile scripts Makefile xtask/xkmake/src/cli.rs
git grep -n -E 'facts|GIT_COMMIT|checkout|xkernel-target|archiveArtifacts|stash' "$SHA" -- Jenkinsfile
git grep -n -E 'env_depinfo|DEPS_ENV|FACTS_ENV|rename|extra_filename' "$SHA" -- tools/lints/src/facts_export/mod.rs
git grep -n -E 'fn kernel_feature_flags|fn pin_lint_build_env|runDylintCheck|buildDiscarder' "$SHA" -- Jenkinsfile xtask/xkmake/src
```

另以 `git show` 配合 `nl -ba`、`sed -n` 读取上述命中区间及 `build.rs`、CLI、exporter 生命周期片段。未做外部检索；主源即固定 Git 对象中的代码和仓库文档，未生成全局来源 ID。
