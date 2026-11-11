# ArceOS／Starry 名称、上游关系与评估独立性

读取日期：2026-11-05。仅核查维护者 GitHub 页面、README 和读取时 `main` 的部分 Cargo 元数据；未运行实验、比较源码相似率或审计提交谱系。主线程已指定本次评估版本如下；本笔记后续所称评估对象以这两个固定提交为准，而非浮动 `main`：

- ArceOS：[`8d2e6f97efc4a67359b99db5e519a55b7067b524`](https://github.com/arceos-org/arceos/tree/8d2e6f97efc4a67359b99db5e519a55b7067b524)，主线程源码片段保存位置为 `research/evidence/runs/2026-11-05-arceos-scope-01/sources/`。
- StarryOS：[`2e075accf4fb0aefdd1d252ebd9ccf29727d9923`](https://github.com/Starry-OS/StarryOS/tree/2e075accf4fb0aefdd1d252ebd9ccf29727d9923)，主线程源码片段保存位置为 `research/evidence/runs/2026-11-05-starry-scope-01/sources/`。

以上 SHA 和保存位置由主线程提供。后续已直接读取两份 scope 的 `tree.json` 及下述源码片段，未重新校验全部归档哈希。下表在线材料用于名称和关系识别，不自动证明与固定提交逐字相同；固定版本结论见补核段。

## 官方可确认关系

| 名称／入口 | 本轮直接读到的证据 | 可确认边界 |
| --- | --- | --- |
| [arceos-org/arceos](https://github.com/arceos-org/arceos) | README 定义为 Rust 模块化 OS／unikernel，并提供复用 `axalloc`、`axhal` 等模块的 Cargo 示例 | 是可被其他 OS 复用的组件基础，不应假设使用它的项目与它完全独立 |
| [Starry-OS/StarryOS](https://github.com/Starry-OS/StarryOS) | README 明确称基于 ArceOS 的实验性宏内核；[Cargo.toml](https://raw.githubusercontent.com/Starry-OS/StarryOS/main/Cargo.toml) 描述 Linux-compatible kernel built on ArceOS，并列 `axhal`、`axtask`、`axruntime` 等 workspace dependencies | 有直接声明及依赖证据的上游／组件复用关系；不据此宣称整仓库是 ArceOS 的 Git fork，或所有文件均派生自它 |
| [arceos-org/starry-next](https://github.com/arceos-org/starry-next) | README 标题为 StarryOS，明确称基于 ArceOS 的宏内核，快速开始调用 `scripts/get_deps.sh` 获取基础仓库 | `starry-next` 与 StarryOS 名称有交叠，必须带 owner、URL 和提交区分；本轮未证明其与当前 StarryOS 主仓的具体迁移／合并关系 |
| [Starry-OS/starry-next](https://github.com/Starry-OS/starry-next) | 本轮打开重定向到 [AsakuraMizu/starry-next](https://github.com/AsakuraMizu/starry-next)，页面标为 forked from `oscomp/starry-next`；其 README 同样称基于 ArceOS | 该旧入口不能直接登记成当前 `Starry-OS/StarryOS`；重定向与 fork 标签只是读取时的托管关系证据 |
| [Starry-OS/Starry](https://github.com/Starry-OS/Starry) | 当前打开重定向到 `Starry-OS/StarryOS` | 当前 URL 别名不证明历史 Starry 的某个旧提交、架构、评测或代码已经与当前主仓相同 |

### 固定 scope 补核

- 两份归档 `tree.json` 均为 `truncated: false`，遍历条目未见 `mode: 160000`。因此这两个捕获树均无 gitlink；**README 的 recursive 命令不能当当前 submodule 证据**。这不排除历史版本或构建步骤另取依赖。
- StarryOS 固定 [Cargo.toml:22–37](https://github.com/Starry-OS/StarryOS/blob/2e075accf4fb0aefdd1d252ebd9ccf29727d9923/Cargo.toml#L22) 声明 `ax*` 的 `0.3.0-preview.2` 版本要求，其中 `axfs` 是 `package = "axfs-ng"` 的依赖名。[Cargo.lock:542](https://github.com/Starry-OS/StarryOS/blob/2e075accf4fb0aefdd1d252ebd9ccf29727d9923/Cargo.lock#L542)、`:619`、`:968` 分别将 `axfs-ng`、`axhal`、`axsync` 锁为该版本，包含 registry source 与 checksum；本轮已直接读归档对应条目。**registry 包不等于 ArceOS 当前 main，也未证明等于固定 ArceOS `8d2e6f97…` 的同名源码。** 版本要求与 lock 精确包身份也应分开记录；包内容和仓库提交的对应仍待核对。
- ArceOS 固定 [modules/axsync/src/lib.rs:17–28](https://github.com/arceos-org/arceos/blob/8d2e6f97efc4a67359b99db5e519a55b7067b524/modules/axsync/src/lib.rs#L17) 直接 `pub use kspin as spin`，并在 `not(feature = "multitask")` 分支将 `SpinNoIrq`／`SpinNoIrqGuard` 重导出为 `Mutex`／`MutexGuard`；已直接读归档。这可作**源码层已有复用对照**，不是两个独立重复实现，也不是本次构建实际启用该分支的证明。不能将此固定源码事实外推为 Starry registry `axsync` 的源码事实。

## 对跨项目评估的限制（研究建议，不是实测结论）

**仓库数量不等于独立实验数量。** ArceOS 与基于它构建的 Starry 应至少标注为有关联的项目族；`starry-next` 的不同 owner／别名也不能直接充当额外独立项目。共同上游、共享组件或搬迁代码可能使“跨仓命中”主要反映已知来源复用，而不是对独立实现的功能重复泛化；但本轮未测量实际重叠比例，不能把所有命中都预判为复制。

建议分别报告仓库数、谱系族数和去重后的候选单位数，并区分“共享上游／依赖区域”与“项目自身实现区域”。若做开发／测试划分，应防止同源文件、派生变体及相同依赖版本跨集合，另报告项目族隔离的结果；依赖未包含在扫描源码中时，也应说明扫描边界，而非假设已扫描全部编译代码。

## 未知与停止边界

未确认：各 `starry-next` 与当前 StarryOS 的共同祖先、迁移时间、合并提交、registry 包内容与 ArceOS 提交的对应、实际构建依赖／feature 激活、代码复制比例及实验样本泄漏情况。已读 lock 条目只是声明的锁定身份，未运行解析或构建。历史 Starry 需用当时提交重新界定，不能以今日重定向替代历史取证。本轮仅官方材料和主线程归档补核，无第三方关系推断、无运行或效果结论。
