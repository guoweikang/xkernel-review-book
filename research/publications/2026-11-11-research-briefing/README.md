# 研究中汇报：问题、相关工作与复现进展

2026-11-11，新版23页。不以固定页数裁剪内容，不作为结题或已验证新方法的报告。保留上一版论文与10页试点汇报，二者不被本版覆盖。

- [可编辑PPT](research-briefing.pptx)
- [PDF预览](research-briefing.pdf)
- [逐页内容、讲解备注与证据](SLIDE-NOTES.md)

## 内容安排

| 页码 | 内容 |
| --- | --- |
| 1–4 | 研究动机、项目预期价值、问题拆分及相关研究地图 |
| 5–8 | SourcererCC机制、作者数据与分层结果、原工具验证及Rust适配 |
| 9–11 | 注释辅助发现的原数据与指标、评价口径分析、我们的文档基线 |
| 12 | Wrangler结构抽象机制与Rust迁移问题；未运行，不展示虚构结果 |
| 13–16 | Librarian方法、MiniCode数据、作者定量结果与人类评价 |
| 17–19 | 复现状态总表、本地先导观察与一次真实重构验证 |
| 20–22 | 待验证方向、原六阶段研究路线及评价安排 |
| 23 | 主要参考及材料入口 |

作者结果、我们的运行结果、文献分析和研究计划分开标记。未复现LDA、Wrangler或Librarian原任务，不把TF-IDF替代基线称为LDA复现，也不把SCC输入适配称为论文基准数值复现。具体引用见每页页脚、演讲者备注及逐页索引；论文中的口径冲突同时保留。

## 重建与证据

在book仓库根目录，复用上一版发布环境（依赖记录在`research/publications/2026-11-11-pilot-draft/requirements.txt`）：

```sh
.build/publication-env/bin/python scripts/build_research_briefing.py
libreoffice -env:UserInstallation=file:///tmp/xkernel-briefing-lo --headless --convert-to pdf --outdir research/publications/2026-11-11-research-briefing research/publications/2026-11-11-research-briefing/research-briefing.pptx
python3 scripts/build.py
python3 scripts/check.py
```

`slides.json`保存页面内容及引用映射；生成器复用上一版的基础视觉函数，生成可编辑文本与形状。`evidence-manifest.json`记录被引用文件与生成源码SHA-256；`delivery-checks.json`记录交付时检查和产物摘要。重新生成后应重新检查并更新交付摘要；不承诺含Office元数据的文件跨次构建字节相同。本轮仅整理既有研究与原论文结果，没有新增检测或内核实验。
