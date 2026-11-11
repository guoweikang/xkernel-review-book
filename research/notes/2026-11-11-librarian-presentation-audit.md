# Librarian：三页研究中汇报的证据审计

日期：2026-11-11。固定论文为 *Refactoring Codebases through Library Design*，Žiga Kovačič、Justin T Chiu、Celine Lee、Wenting Zhao、Kevin Ellis，arXiv:2506.11058 **v3（2025-10-05）**。本轮直接读本地 `research/evidence/originals/P21-librarian-v3-full.html` 的§4–7、附录C/E及F开头，回读两份 `research/notes/*librarian*`，并核对归档README和运行脚本；未浏览新版本、运行模型或复算作者统计。不要将既有笔记中的后续发表状态替代本轮固定版本身份。

## 幻灯片1：原任务与数据——生成共享库，不是重复代码检索榜单

作者任务输入为相关文件，输出为**共享库＋迁移后的原程序**；§3以保留原先通过的测试为约束，§5采用摘要/嵌入聚类、采样候选、测试筛选、指标重排。[§3](https://arxiv.org/html/2506.11058v3#S3)、[§5](https://arxiv.org/html/2506.11058v3#S5)。MiniCode是作者组织的基准，Librarian是方法，不应把二者或我们的Rust静态候选发现混为同一任务。

可直接展示[§4表1](https://arxiv.org/html/2506.11058v3#S4)的作者统计：

|数据域|文件数|任务数|平均LoC|每文件平均测试数|
|---|---:|---:|---:|---:|
|CodeContests|300|10|87|10|
|Transformers|10|1|538|181|
|Diffusers|11|2|685|75|
|Logo|300|1|10|1|
|Date|246|1|14|1|

这些是不同层次的计数，不能把文件数当独立任务数或将平均测试数相乘当精确总测试数。CodeContests取问题、解答与测试；[附录C](https://arxiv.org/html/2506.11058v3#A3)说明约9k个有Python解答的问题，剔除选定解答不足10行后剩4596，摘要嵌入、聚为120组、每组选30文件，再选10组。**同附录后段又写6组**，展示表1时应脚注“按表1，附录口径待对齐”。Transformers/Diffusers仅选定Python模型文件，不是整个仓库；Logo/Date沿用既有任务，问题由人编写、解答由gpt-3.5-turbo生成，并用于留出程序合成评价；不是Rust内核数据。

## 幻灯片2：作者定量结果——压缩、测试与偏好分开讲

指标定位：[§6](https://arxiv.org/html/2506.11058v3#S6)对库和迁移程序整体计Tokens；MDL为 `-log p(库) − Σ log p(迁移程序 | 库)`，依赖模型似然，不是模型自由指标，也不是运行时间或维护成本。CC、MI为另两种质量代理；库调用数是复用代理。[附录F](https://arxiv.org/html/2506.11058v3#A6)的Best@k是采样筛选后的压缩表现估计，不是一次生成成功率。

|可引用的作者结果|正文定位与必要限定|
|---|---|
|CodeContests：Pass Rate `90.67% ±1.88`；Pass Rate Improvement `6.33% ±1.41`；MDL Ratio `0.53 ±0.03`；Token Ratio `0.66 ±0.04`|[§7表2](https://arxiv.org/html/2506.11058v3#S7)，10任务，K=8、S=3、o4-mini；比例是相对于原代码，不是我们的测量。表中误差项按原样引述，不自行标成标准差/标准误；本轮未核实逐测试分母、跨任务加权与原始统计实现，不把90.67%写成“90.67%的重构完全正确”|
|库函数数 `10.30 ±1.41`，每函数平均调用 `5.17 ±1.08`，单次使用函数比例 `38.03% ±4.88`|同表2；说明抽象并非都被多次复用，不等于已证实长期维护收益|
|Logo留出合成：REGAL `49.3% ±1.1`，Librarian `69.9% ±0.9`；Date分别 `90.2% ±0.5`、`94.7% ±0.7`|[§7表3](https://arxiv.org/html/2506.11058v3#S7)，表列gpt-3.5-turbo；是借助学得库解决留出合成任务的通过率，不能与表2或Rust检索准确率混算；本轮未核对留出任务精确分母与原始记录|
|Transformers的10文件：MDL降至原来的67.2%，作者报告通过全部集成测试|§7 Real-World Refactoring，K=15、S=5、Claude Code；不是运行性能改善32.8%。同10文件人工方案为66.5%（HuggingFace）与62%（论文作者），仅是相同MDL指标比较，不是维护性达到人类水平的证明|
|14位参与者、129次判断；MDL对MI偏好差异显著|[§6.2](https://arxiv.org/html/2506.11058v3#S6.SS2)、[附录E](https://arxiv.org/html/2506.11058v3#A5)；MDL对Tokens未获同样显著性结论。附录设计为每人10对，允许近似相同，采用75%共识阈值过滤并称保留92.4%；129不可写成参与者数或129个独立样本|

**上屏避坑**：表2 Token Ratio=0.66与邻近正文“减少44%”不一致，推荐只列原表比率并标注待核对；正文MDL模型写Qwen-2.5-3B，附录C写7B Instruct，不擅自合成唯一复现配置。附录E的 `p=0.67`伴随95%区间[0.56,0.78]，不要误抄成显著性检验的p值。§8明确压缩不必然对应复用，未见应用开发任务的实际效用仍待研究。

## 幻灯片3：我们的复现状态——资料已定位，原任务尚未复现

直接核对的归档工件为 `research/evidence/originals/reproduction-2026-11-05/lib-README.md`、`lib-train_librarian.sh`；README提供CodeContests实现、OpenAI/Together API条件、预处理与运行入口；脚本设K=8、tuple上限3、集合0–9、o4-mini，再生成评分文件。**有入口不等于运行成功**。截至本轮所查笔记与 `research/evidence/runs/*/report.json`，未找到Librarian原任务运行报告；准备笔记明确未下载完整数据、安装、调用模型或执行评价，不能展示我们的MDL/通过率复现数字。

官方资源（以下SHA沿用2026-11-05准备核查，不称今日最新HEAD，也未确认是v3实验提交）：
- [作者项目页](https://code-refactor.github.io/)；[Librarian固定仓库](https://github.com/code-refactor/Librarian/tree/f5167b903d00ace774de419a617138b8db69c4bd)，SHA `f5167b903d00ace774de419a617138b8db69c4bd`。
- [MiniCode固定仓库](https://github.com/code-refactor/minicode/tree/3cc71a908f16c78e634010523b264671c3546fc2)，SHA `3cc71a908f16c78e634010523b264671c3546fc2`。原作者数据入口已定位，不等于数据已完整归档或核验。
- [归档README原URL](https://raw.githubusercontent.com/code-refactor/Librarian/f5167b903d00ace774de419a617138b8db69c4bd/README.md)、[归档脚本原URL](https://raw.githubusercontent.com/code-refactor/Librarian/f5167b903d00ace774de419a617138b8db69c4bd/scripts/codecontests/minicluster/train_librarian.sh)。许可及其覆盖范围、API存续/额度/成本、数据revision和与表2样本一致性仍未确认。

下一步只宜列为计划：先锁定一个CodeContests集合与测试身份、数据/代码版本、模型及评分endpoint、采样预算和回退处理，验证产生“库＋迁移程序＋逐测试结果＋评分日志”；跑通单集合仍不是完整论文数值复现。既有 `research/notes/2026-11-05-librarian-reproduction-readiness.md` 记录的预处理路径不一致、条件汇总判据与论文测试集合约束之间的对齐问题仍待处理。本页没有验证这些问题已修复。三页页脚统一写明：**作者实验：v3论文报告；本项目：文献与资源审计完成，Librarian原任务未复现。**
