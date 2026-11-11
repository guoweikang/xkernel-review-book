# 注释克隆论文：工件可取得性与版本关系

核查日期：2026-11-09。范围仅一手入口、作者关联工件及版本关系；不重复主线程的方法/指标审计，未安装、运行实验或联系作者。**结论：论文可取得，但本轮未找到经作者链接确认的实现仓库或复现数据包；应标“工件入口未找到”，不是“已证实不公开/不可用”。**

## 一手入口与两篇论文关系

- [arXiv 2006.14505v1](https://arxiv.org/abs/2006.14505v1)：作者 Sandeep Kaur Kuttal、Akash Ghosh，提交时间2020-06-25；[固定 v1 PDF](https://arxiv.org/pdf/2006.14505v1) 本轮实际下载并提取文本，12页。只定向检索工件关键词、URL、数据来源及2018引用，不称全文方法复核。页面的 Code/Data 服务开关不是作者提交的具体仓库；TeX Source 是论文源文件入口，不能等同实现代码。
- [作者 publications 页面](https://skuttal.github.io/skk/publications.html) 同时列出2020同名论文（IJCSIS 18(11):11–22）和 Ghosh、Kuttal 的2018 VL/HCC *Semantic Clone Detection: Can Source Code Comments Help?*（pp.315–317）。这确认同一作者研究线及两条出版记录；未逐字比较期刊版与 arXiv v1，不能默认二者完全相同。
- v1 的参考文献[2]指向2018工作（题名写作 *Semantic Code Clones: Can Source Code Comments Help?*），§IV 的 “LDA using Method 2” 明确沿用 Ghosh/Kuttal [2] 的 topic 数选择依据。这是实质性继承证据；不能将两篇作为彼此独立的重复验证。v1 摘要另列跨 Java/Python 分析，但本轮不量化相对2018的新增贡献，也未找到明确“正式扩展版”的作者声明。[v1 原文](https://arxiv.org/pdf/2006.14505v1)

## 工件状态：找到、未找到与访问失败分开

| 项目 | 实际证据与状态 |
| --- | --- |
| 作者项目入口 | [作者 research 页](https://skuttal.github.io/skk/research.html) 的 “Semantic Clone Detection using Source Code Comments” 可读，提供研究描述；该节未见代码/数据下载链接。publications 中两条记录也未提供工件链接。 |
| 实现仓库、提交、许可证、可运行入口 | 在上述作者页面、arXiv 页面和 v1 提取文本的 github/http/available/replication/repository 定向检索中，**未找到作者关联的专用实现仓库**；因此 SHA、许可证、requirements、运行命令均未确认。不能用同名 GitHub 用户或第三方文献列表补齐归属。 |
| 输入数据 | v1 §III.A 列 JHotDraw、Java Swing、PyGUI；参考文献[47]给 `http://www.jhotdraw.org/`，[46]给 `https://docs.oracle.com/javase/javax/swing/package-summary.html`，[69]给 `http://www.cosc.canterbury.ac.nz/greg.ewing/pythongui/version/Doc/index.html`。这些是论文所引上游站点/文档，不是带版本、文件清单和哈希的作者实验快照；本轮未访问这些上游入口，状态为“链接已定位、当前可下载性未核实”。 |
| ground truth、预处理语料、模型/随机种子、运行输出 | v1 有人工建立 ground truth 的叙述，但本轮未定位对应下载包或机器可读标签链接；未确认这些产物是否另处公开。不能用当前上游代码重下载代替作者标注快照。 |
| 2018 PDF | 定向访问会议材料镜像 `https://alfa.di.uminho.pt/~jorgemendes/vlhcc2018/papers/vlhcc2018.pdf`：浏览器工具超时，curl TLS 失败。记为“该链接本轮获取失败”，不是论文不存在；搜索索引摘要不计作本轮成功取得全文。未对其脚注/附件完成核查。 |

## 准备度与停止边界

当前足以记录先例及向作者询问复现工件，不足以称为可直接复跑的作者基线。缺口是作者仓库身份/版本/许可、精确输入快照、ground-truth 文件及映射、可重复环境和随机配置；使用通用 GRAPLE/JPDG/LDA 重建流程只能另标“依据论文重实现”，不能称官方工件复现。本轮不继续追查依赖工具仓库，也不作 Rust 支持或功能等价保证。

实际查询：`"Source Code Comments: Overlooked" github`；`"Semantic Clone Detection: Can Source Code Comments Help" artifact github`；`"Akash Ghosh" "clone" github`；`"Kuttal" "comments" "dataset" clone github`。结论只采用上述论文与作者页面；未采纳第三方综述对方法的概括。仅写本笔记，临时 PDF/文本不登记为 book 归档；未修改来源台账。
