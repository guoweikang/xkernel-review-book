# AI 代码审查：原理、方法与评价

独立的 mdBook 源码仓库。入口是 `chapters/README.md`，研究原始笔记保留于 `research/`。
当前为基础调研及共同学习，不是已验证的 AI review 产品。

仓库：<https://github.com/guoweikang/xkernel-review-book>。
内容按基础前置知识、流程地图、六个审查环节组织；论文与工程实践归入对应环节。

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

## 目录

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
