# ArceOS与Starry：固定版本、采样范围和同源控制

日期：2026-11-05。本轮确定外部取样对象并阅读少量入口，不进行全仓检测、构建或重构。

## 固定对象

| 对象 | 仓库 | 本次固定提交 | Git树中的.rs文件数 |
| --- | --- | --- | ---: |
| ArceOS | arceos-org/arceos | `8d2e6f97efc4a67359b99db5e519a55b7067b524` | 184 |
| Starry | Starry-OS/StarryOS | `2e075accf4fb0aefdd1d252ebd9ccf29727d9923` | 105 |

提交经git ls-remote HEAD与GitHub API交叉确认。数量是固定树的文件盘点，包含测试等，不代表编译范围、有效函数数或已阅读文件数。
两棵树均未列出gitlink；即使README写有recursive克隆步骤，也不能据此认定当前版本有已锁定子模块。
本次选择Starry组织主仓，不把历史Starry、竞赛分支和starry-next混成一个版本。名称沿革另见[关系核查](2026-11-05-cross-project-lineage.md)。

源码及来源：[ArceOS固定树](https://github.com/arceos-org/arceos/tree/8d2e6f97efc4a67359b99db5e519a55b7067b524)、[Starry固定树](https://github.com/Starry-OS/StarryOS/tree/2e075accf4fb0aefdd1d252ebd9ccf29727d9923)。

## 已影响采样的具体发现

### ArceOS：同名接口不等于重复实现

`modules/axsync/src/lib.rs`重导出kspin；multitask关闭时，Mutex是SpinNoIrq的别名；开启时使用本地mutex模块。
`mutex.rs`中的RawMutex持有WaitQueue，竞争路径调用wait_until；不能只因两者都叫锁就认为可以无条件替换。
还有一处配置证据冲突：lib.rs文档称multitask默认启用，但同版本Cargo.toml的default为空。
这不意味着实际应用一定未启用：工作区调用方仍可启用feature。需要构建配置，不能仅凭文档或单个manifest推断实际锁语义。

依据：[lib.rs](https://github.com/arceos-org/arceos/blob/8d2e6f97efc4a67359b99db5e519a55b7067b524/modules/axsync/src/lib.rs)、[Cargo.toml](https://github.com/arceos-org/arceos/blob/8d2e6f97efc4a67359b99db5e519a55b7067b524/modules/axsync/Cargo.toml)、[mutex.rs](https://github.com/arceos-org/arceos/blob/8d2e6f97efc4a67359b99db5e519a55b7067b524/modules/axsync/src/mutex.rs)。

决定：新增阅读单元X005，用于检查工具能否识别已有复用及配置条件，不将重导出计作独立实现或重复机会。

### Starry：依赖发布版不等于ArceOS当前main

根manifest声明多个ax组件发布版，axfs对应package名axfs-ng。Cargo.lock中axsync、axfs-ng均为0.3.0-preview.2，来自registry并带checksum；kspin锁定0.1.1。
本次ArceOS的axsync manifest却要求kspin 0.2。名称与生态关联不足以证明源码相同或不同，不能直接替换依赖源进行比较。
没有下载这些registry源码、执行Cargo解析或展开完整依赖图；锁文件也不证明每个包在某目标配置都参与编译。

依据：[Starry Cargo.toml](https://github.com/Starry-OS/StarryOS/blob/2e075accf4fb0aefdd1d252ebd9ccf29727d9923/Cargo.toml)、[Cargo.lock](https://github.com/Starry-OS/StarryOS/blob/2e075accf4fb0aefdd1d252ebd9ccf29727d9923/Cargo.lock)。

新增阅读单元X006：`kernel/src/pseudofs/file.rs`及proc.rs/dir.rs。入口可见SimpleFileOps、RwFile和闭包适配；写契约是write_all，不能按名字直接等同X-Kernel的CommandFile接口。
本轮只完成入口阅读，尚未完整核对调用、错误与生命周期，不把它标为重复候选。与X-Kernel相似命名的历史来源仍未知，不声称独立发明或复制关系。

## 对试点和评价的约束

现在有三个仓库的取样入口，不等于已完成三个项目验证。四个X-Kernel种子加两个外部阅读单元，也不等于六个已确认机会。
ArceOS/Starry先按相关生态处理；X-Kernel与这些模块的谱系还需审计。数据划分按相关案例/上游家族分组，不仅按仓库名划分。
每个候选应记录“本仓实现/重导出/外部依赖/来源未知”，保留package版本和源码身份，不把同名crate自动合并。
暂不扩大基础设施：下一轮先深读X006并与R004做契约对照，判断这是已有复用、不同职责，还是值得核验的部分重叠。
还需补低文本相似和多函数共同机制案例；当前取样未覆盖全部研究问题。

## 归档和复查

协议：`research/protocols/cross-project-scope-v1.json`。
四个`research/evidence/runs/2026-11-05-{arceos,starry}-{scope,reading-scope}-01/`目录保存Git提交对象、完整树元数据、选定文件、URL、blob及SHA256、捕获脚本。
只下载14份选定文件，不把树清单称为全仓源码下载。未执行外部脚本、安装内核依赖或改变本地研究仓库分支。
`scripts/capture_github_scope.py`要求固定完整SHA，验证所选blob与提交树一致，拒绝覆盖；异常保留incomplete状态。
Git对象校验是内容一致性校验，不是签名验证或来源安全认证。
