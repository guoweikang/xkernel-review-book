# AI 代码审查：原理、方法与评价

独立的 mdBook 源码仓库。入口是 `chapters/README.md`，研究原始笔记保留于 `research/`。
包含基础学习、论文调研、基线适配及局部工程实验，不是已验证的通用 AI review 产品。

仓库：<https://github.com/guoweikang/xkernel-review-book>。
内容按基础前置知识、流程地图、六个审查环节组织；论文与工程实践归入对应环节。

研究材料归档规则见 `research/archive/README.md`；外部仓库版本与恢复入口见
`research/archive/sources.json`。实验原始输入输出按批次存放在 `research/evidence/runs/`，
公开文件摘要清单位于 `research/archive/snapshots/`。缓存与部分本地原件不随Git上传，
当前不宣称提供完整离线复现环境。

## 当前研究进度（2026-11-20整理）

当前目标收敛为设计问题发现，不要求优化证明。先在设计PR参考集评测，再到xkernel部署；[ReviewBench测试流程与接入核查](research/notes/2026-11-20-reviewbench-workflow.md)是最新入口，以下阶段报告保留历史实验事实。

优先阅读[阶段研究报告](research/notes/2026-11-18-stage-progress.md)，再从
[主题地图](chapters/research-topics/scope.md)查看发现、确认、职责文档与评价证据；
[进度记录](research/PROGRESS.md)保留各批次的决策及接续入口。

- 发现：已有词元、文档与调用视角的基线及固定范围比较，尚未证明独立数据上的稳定收益。
- 确认：保留成功与拒绝案例。最新直接委托实验中，原版／候选各303项测试通过；
  缓存Cow helper因清理顺序变化的可接受性未闭合而暂不推荐。
- 边界：测试通过不代表完整等价、性能提升或生产采用；跨crate及跨项目收益仍待验证。
- 下一步：设计PR与接受证据准入、冻结测试集及隔离输入；旧跨crate批次暂停。

最近方法实验日期为2026-11-18；11月20日新增ReviewBench机械审计和框架测试，不是检测效果实验。

## 构建与访问

需要 Python 3.11+ 和 mdBook 0.5.4。当前环境已在 `.tools/mdbook` 安装校验过的二进制；
其他环境可按 [mdBook 安装文档](https://rust-lang.github.io/mdBook/guide/installation.html)
安装，或使用 `cargo install mdbook --version 0.5.4 --locked`。

```sh
python3 scripts/build.py
python3 scripts/check.py
python3 -m http.server 8765 --bind 127.0.0.1 --directory dist
```

本机访问 `http://127.0.0.1:8765/`。远程服务器可先建立 SSH 端口转发；
不要把本机回环地址误认为公网地址。公网或私有托管的部署地址以实际部署结果为准。

## 源码研究工具

固定范围、版本、验收门禁和证据输出的说明见
[源码单位固定流程](research/tools/source-unit-workflow.md)。统一入口：

```sh
python3 scripts/run_source_workflow.py --repo /path/to/x-kernel \
  --output research/evidence/runs/my-source-units-run
```

此工具只验证源码提取，不判断功能重复；输出目录不可重复使用。

## 文件布局

```text
chapters/                 持续维护的教学章节、练习、论文导航
chapters/SUMMARY.md        主阅读目录
research/                 原研究目录的完整保留副本，今后在此维护
research/evidence/        来源、时间、校验和
research/evidence/originals/ 本地原文快照，不进入 Git 或网站
theme/                    阅读样式
scripts/                  可重复构建、链接及归档检查
book.toml                 mdBook 配置
MIGRATION.md              迁移来源与维护规则
migration-manifest.json   首次迁移文件的字节数与 SHA-256
.build/                   生成的输入目录，不手工修改
dist/                     静态网页，不提交 Git
```

修改 `chapters/` 和 `research/` 后重新构建，不直接修改 `.build/` 或 `dist/`。
构建脚本自动收录所有研究 Markdown（不含下载原文），并将原始证据链接转换为一手来源。
参考文献的阅读深度以台账为准；“待学习”不是“已掌握”。

## 发布边界

Git 仓库包含书稿、研究笔记、来源台账和证据清单，不包含第三方原文快照、本地工具及托管账户配置。
原笔记包含项目语境、研究候选及本地路径；未来新增内容仍需检查后发布。
第三方论文和教材不因可下载而自动获得再分发许可；网站只链接一手来源。
未为材料整体添加开源许可证，授权范围需另行决定。第三方资料保留原有权利。
校验和用于追踪一致性，不是法律时间戳或新颖性证明。
