# Rust系统代码重构机会研究：论文与汇报 v0.1

日期：2026-11-11。定位：探索性实证研究初稿，不是已验证的新算法论文。作者、单位与目标投稿场所尚未确定。

## 阅读文件

- [材料充分性评估](ASSESSMENT.md)：问题、方案、实验结果各自的证据边界。
- [论文 PDF](paper.pdf)：8页，含中英文摘要、相关工作、方法、实验、结果、有效性威胁、参考文献与证据附录。
- [可编辑论文](paper.docx)与[正文源文件](paper.md)。
- [10页可编辑演示文稿](slides.pptx)与[演示文稿 PDF](slides.pdf)。
- [独立材料审计记录](../../notes/2026-11-11-manuscript-evidence-audit.md)：另一助手核查报告，不等于独立人工标注。

## 结果与限制

固定xkernel提交和四包范围：88个文件、2180个源码单位；SourcererCC适配输出156对；原生文档TF-IDF固定top20。两批静态审阅合计38个不同配对，不是38个独立随机样本。文档新增19对均在旧token长度门槛之外，不能据此认定语义召回提升。一个测试夹具重构案例原版与候选各通过相同94项测试，维护净收益仍未证实。

本次整理历史实验，不宣称重新运行内核测试。公开基准、独立语义标签、公平对照、消融和跨项目验证仍待完成。论文采用通用学术结构，尚未套用特定期刊或会议模板。

## 重建

在本书仓库根目录执行；需要Python、LibreOffice及Noto Sans/Serif CJK SC字体。

```sh
python3 -m venv .build/publication-env
.build/publication-env/bin/pip install -r research/publications/2026-11-11-pilot-draft/requirements.txt
.build/publication-env/bin/python scripts/build_pilot_publication.py
libreoffice -env:UserInstallation=file:///tmp/xkernel-paper-lo --headless --convert-to pdf --outdir research/publications/2026-11-11-pilot-draft research/publications/2026-11-11-pilot-draft/paper.docx research/publications/2026-11-11-pilot-draft/slides.pptx
```

`paper.md`为论文文本源；幻灯片布局及内容位于`scripts/build_pilot_publication.py`。生成器检查核心数值与配对集合，并记录输入SHA-256。它只重建出版物，不重跑检测和内核测试。原实验协议及运行入口见论文证据附录和对应运行目录。

`evidence-manifest.json`固定本次使用的输入摘要；`deliverables-manifest.json`记录交付物摘要；`validation.json`记录交付时结构校验。Office/PDF文件可能含生成时间等元数据，跨次构建不承诺字节完全一致。重新生成后应同步重新校验并更新交付物摘要，不改写原始实验结果。
