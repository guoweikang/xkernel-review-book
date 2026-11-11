# Rust OS 执行准备：三项目身份与版本核查

核查日期：2026-11-05。仅核查 ArceOS、Starry、Asterinas 三个项目；Starry 的新旧承载仓库分列，不扩展为其他项目调查。读取官方仓库、README、Cargo 声明和许可证文件头，并用 `git ls-remote --symref <官方仓库>.git HEAD` 查询远端，不 clone/fetch、不运行项目、不安装工具。网页可能有缓存；下面 SHA 是本轮远端返回的 HEAD，而 README 的滚动页面读取不自动视为同一 SHA 的快照。

## 1. 默认分支与身份

| 项目 / 承载位置 | 默认分支及本轮 HEAD | 官方身份与范围 |
| --- | --- | --- |
| [ArceOS：arceos-org/arceos](https://github.com/arceos-org/arceos) | `main`；`8d2e6f97efc4a67359b99db5e519a55b7067b524` | README 定位为 Rust 实验性模块化 OS / unikernel，不应直接等同 Linux 兼容宏内核 |
| [Starry：Starry-OS/StarryOS](https://github.com/Starry-OS/StarryOS) | `main`；`2e075accf4fb0aefdd1d252ebd9ccf29727d9923` | README 定位为基于 ArceOS 的实验性宏内核；官方组织说明它现在主要用于维护、老版本分析，不能仅凭仓库名认作最新版 |
| [Starry 当前承载：rcore-os/tgoskits](https://github.com/rcore-os/tgoskits) | `dev`；`84fc932abb49bd44ad87c90221078c8b90896985` | 官方 Starry 组织指向其 `os/StarryOS`；固定 SHA 的根 README 确认该目录及整合关系。表中 SHA 是整个承载仓库，不是独立 Starry 发布版本 |
| [Asterinas：asterinas/asterinas](https://github.com/asterinas/asterinas) | `main`；`da0cb2619940fd429ec5fb226be1ee081df6e7ee` | README 定位为以 Rust 从头构建、兼容 Linux 的通用内核，采用 framekernel/OSTD；这属于项目声明，不是本轮安全或性能测试结论 |

来源：[ArceOS README](https://raw.githubusercontent.com/arceos-org/arceos/main/README.md)、[Starry README](https://github.com/Starry-OS/StarryOS#readme)、[Asterinas README：Introducing Asterinas](https://raw.githubusercontent.com/asterinas/asterinas/main/README.md)。用户所称“星绽”本轮暂按 Asterinas 核查；本轮已读英文官方 README 未独立核实中文正式名称，不据搜索无命中否定该名称。

## 2. Starry 版本歧义与 ArceOS 关系

[Starry-OS 官方组织 README](https://github.com/Starry-OS#介绍) 明确：2026年4月后 StarryOS 升级进入 tgoskits，旧组织中的 StarryOS 用于维护/历史分析。它还列出不同历史入口：`Arceos-monolithic/Starry`（训练营初始版）、`Azure-stars/Starry`（单向依赖过渡版）、`Starry-OS/Starry-Old`（2024主仓）、`oscomp/starry-next`（2025竞赛基础版）。这些身份仅沿用官方目录说明，**未继续逐个打开、解析 SHA 或核对许可证**；不能把名称含 Starry 的仓库合并为一个无版本对象。

依赖/派生关系有三层证据：旧 Starry README 明说基于 ArceOS；其 [Cargo.toml](https://raw.githubusercontent.com/Starry-OS/StarryOS/main/Cargo.toml) 将自身描述为建立在 ArceOS unikernel 上的 Linux 兼容内核，并声明 `axhal`、`axruntime`、`axtask` 等 workspace dependencies（所读页面版本为 `0.3.0-preview.2`）；[固定 SHA 的 TGOSKits README](https://github.com/rcore-os/tgoskits/blob/84fc932abb49bd44ad87c90221078c8b90896985/README.md) 说明通过 Git Subtree 整合独立子项目，并同时列出 `os/arceos` 与 `os/StarryOS`。这足以要求将 ArceOS/Starry 标记为有共享来源或组件关系，**不能预设为互相独立的重复功能样本**；但尚未证明全部直接/传递依赖、锁定版本或 Git 祖先关系。README 的“based on”不能自动改述成 GitHub fork 关系。

官方组织链接的 [新 Starry README](https://raw.githubusercontent.com/rcore-os/tgoskits/dev/os/StarryOS/README.md) 仍有旧仓徽章，因此不能靠徽章判定承载仓库。尝试读取固定 SHA 下 `os/StarryOS/Cargo.toml` 返回 **HTTP 404**；本轮停止展开，当前 package 入口/依赖布局仍未知，不能用旧 Cargo 声明替代新布局。

## 3. 许可证入口（文件级盘点，不作兼容性结论）

- **ArceOS：**仓库根目录列 `LICENSE.Apache2`、`LICENSE.GPLv3`、`LICENSE.MulanPSL2`、`LICENSE.MulanPubL2`。直接读到的 [固定 SHA Cargo.toml](https://github.com/arceos-org/arceos/blob/8d2e6f97efc4a67359b99db5e519a55b7067b524/Cargo.toml) workspace license 为 `GPL-3.0-or-later OR Apache-2.0 OR MulanPSL-2.0`；[LICENSE.MulanPubL2](https://github.com/arceos-org/arceos/blob/8d2e6f97efc4a67359b99db5e519a55b7067b524/LICENSE.MulanPubL2) 文件头为木兰公共许可证第2版。**不能因根目录存在第四份文本就给所有文件追加第四种可选授权**；各组件适用范围未审计。
- **旧 StarryOS：**固定 SHA 的 [LICENSE](https://github.com/Starry-OS/StarryOS/blob/2e075accf4fb0aefdd1d252ebd9ccf29727d9923/LICENSE) 文件头为 Apache 2.0；滚动 [NOTICE](https://raw.githubusercontent.com/Starry-OS/StarryOS/main/NOTICE) 和 Cargo 声明亦指向 Apache-2.0。历史其他 Starry 仓库不随之自动获得同一结论。
- **新 Starry 承载仓库：**固定 SHA 根 [LICENSE](https://github.com/rcore-os/tgoskits/blob/84fc932abb49bd44ad87c90221078c8b90896985/LICENSE) 文件头为 Apache 2.0；这不是对全部 subtree 和依赖逐文件审核的结果。
- **Asterinas：**固定 SHA 的 [LICENSE-MPL](https://github.com/asterinas/asterinas/blob/da0cb2619940fd429ec5fb226be1ee081df6e7ee/LICENSE-MPL) 为 MPL 2.0。README 说源码和文档主要使用 MPL-2.0，部分组件例外；所读 [.licenserc.yaml](https://raw.githubusercontent.com/asterinas/asterinas/main/.licenserc.yaml) 给 `kernel/libs/comp-sys/cargo-component` 指定 Apache-2.0 或 MIT 的头部规则。该规则不是完整依赖许可证清单，不能称全仓统一 MPL。

## 4. 执行前仍须固定的事项

应先选择“旧 StarryOS”还是“TGOSKits 中的新 StarryOS”，保存承载 SHA、具体目录、真实构建入口和依赖锁文件；对 ArceOS–Starry 的共享来源单列，避免把同源组件当成独立发现成果。Asterinas 本轮未核查与另两者的代码谱系，不能把“未见关系声明”当成无共享代码证明。许可证盘点不等于批准复制或组合代码；依赖/文件级范围仍待核。本轮未验证任何构建、测试、ABI 覆盖或性能宣称。

## 5. 实际查询与失败记录

直接打开三个项目官方 GitHub 页面、Starry 组织页面及其指向的新承载路径；读取本文链接的 README/Cargo/NOTICE/许可文件。只用 `git ls-remote --symref` 查询上述四个承载仓库（其中两个属于 Starry 新旧版本），没有下载 Git 对象。另仅提交一次查询 `site:asterinas.github.io 星绽 Asterinas`，返回英文官方页面，未继续扩展。新 Starry GitHub 子目录页面通过网页工具打开失败，随后以官方 raw README 与固定 SHA 根 README 核对；固定 SHA 下 package Cargo.toml 的404保留为未知。`curl | head` 读取许可证头部时出现 broken-pipe 报错，仅表示提前停止输出，本笔记不声称已通读许可证全文。
