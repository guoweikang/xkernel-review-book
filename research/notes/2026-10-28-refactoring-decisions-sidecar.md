# 重构决策旁支：拒绝抽象、保留重复与后续回退

日期：2026-10-28。阶段：A 基础调研。精选三篇，非系统性综述，不作创新性判断。

## 范围与证据口径

本次服务于现有 [研究计划](../RESEARCH-PLAN.md) 的 RQ3/H3：建议是否值得采用，以及历史接受、拒绝、撤回能否提供评价依据；同时补充 RQ2 中“保留独立实现”这一合法方案。

仅阅读一手论文和作者工件说明；没有追入论文引用的真实 PR、邮件线程或生产仓库，没有采集新案例、下载样本数据、运行工具或实验。未研究 CodeTaste、CodeReviewer、RefactorBench，未再派代理。本文件是唯一新增文件；按本次任务要求不更新 PROGRESS/SOURCES，不分配全局来源 ID。

这里的“偏好对”特指：**同一问题与上下文中，可辨识的候选方案 A/B，加上维护者选择及理由**。两个不同 PR 的接受/拒绝状态不是天然偏好对；重构前后版本也不自动满足这一标准。“负例”还须区分技术错误、方案不合适、收益不足、流程放弃与临时试验。

## 三篇材料及阅读深度

### When Do You Repeat Yourself? Voices from the Trenches of Linux Kernel Maintainers on Code Duplication

Luan Arcanjo、David Tadokoro、Marcelo Spessoto、Rafael Passos、Paulo Meirelles；TechDebt 2026，47–52 页。正式发表的短论文。

- 一手正文：[ACM DOI 页面](https://doi.org/10.1145/3794915.3795783)。阅读深度：通过检索返回的出版方正文段落核对第 3 节方法、第 4 节讨论与表 1、第 5 节威胁和第 7 节工件；不是逐页 PDF 精读。DOI/全文直接打开受阻，部分性能讨论截断。
- 作者工件：[Zenodo 17503684](https://doi.org/10.5281/zenodo.17503684)。论文声明含匿名评审线程；本轮入口访问失败，**未核对文件内容或数据模式**。

**论文事实。** 作者及学生向 AMDGPU/IIO 提交去重修改，研究 13 次补丁互动，8 次接受。讨论归纳驱动分叉、可读性、集成负担、性能四类因素。维护者可能容忍重复，也可能在修改方案后接受去重；参数化不是必然获拒。性能是评审中的取舍理由，本轮没有核得可复用的性能测量集。研究局限包括两个子系统、新贡献者、候选预筛及 Type-1/2 克隆范围。[正文，第 3–5 节](https://doi.org/10.1145/3794915.3795783)

**与设想差异（本笔记判断）。** 这是最直接的“去重建议为何不被采用”材料，但研究者主动提交建议会改变观察过程，不能当自然历史 PR 的无干预样本。它适合帮助列出拒绝理由，不直接验证我们的 Rust 契约表示、自动生成或全仓召回。作者讨论的项目特定因素也不是已证实的跨项目规则。

### Code Review Practices for Refactoring Changes: An Empirical Study on OpenStack

Eman Abdullah AlOmar、Moataz Chouchen、Mohamed Wiem Mkaouer、Ali Ouni；MSR 2022。阅读的是作者预印本及其 HTML 转换。

- [作者论文 HTML](https://arxiv.org/html/2203.14404)；[作者 PDF](https://smilevo.github.io/self-affirmed-refactoring/Preprint/MSR22-preprint.pdf)。阅读深度：核对第 3 节筛选/分析方法、第 4.2 节及表 4；不是全篇逐页复核。
- [作者工件说明](https://smilevo.github.io/self-affirmed-refactoring/refactoring-review/)：核对其列出的 SQLite、RQ1/RQ2 CSV、分析脚本及访谈材料；未下载压缩包或逐行检查标签。

**论文事实。** 研究比较 5,505 个重构评审与等量对照，定性分析 384 个较长评审，形成六大类、28 个子类。理由覆盖可读性、行为保持、领域约束、收益、测试及集成等。样本含 Merged/Abandoned；放弃可能源于无人继续评审。筛选明确剔除了撤销重构的评审，不能据此估计后续回退。关键词与长评审选择限制代表性。[正文，第 3 节、第 4.2 节、表 4](https://arxiv.org/html/2203.14404)

**与设想差异（本笔记判断）。** 它提供通用重构评审理由框架，未把“拒绝这个抽象”与“保留这些重复”专门建成判定任务。适合提醒我们记录收益说明、迁移负担和流程背景；不能把分类出现频次解释成维护者对任意两个方案的排序，更不能把 Abandoned 全部当正确性负例。

### Quick remedy commits and their impact on mining software repositories

Fengcai Wen、Csaba Nagy、Michele Lanza、Gabriele Bavota；Empirical Software Engineering 27, Article 14，2022（2021 年接受）。

- [作者所属机构书目页](https://search.usi.ch/en/publications/36369)；[DOI](https://doi.org/10.1007/s10664-021-10051-z)；[论文 PDF 的国家图书馆副本](https://d-nb.info/1249003601/34)。阅读深度：核对摘要、引言，以及 PDF 印刷页 19–21 的重构回退结果和有效性威胁；不是全篇精读。作者站 PDF 未能正常取得，图书馆副本经流式文本提取阅读，没有保存副本。
- [作者复现仓库](https://github.com/USI-INF-Software/EMSE-ICPC2020-quick-remedy-commit)：只读 README/文件目录，确认列出项目清单、500 条已标注提交及回退影响结果；未打开样本行、未克隆仓库。

**论文事实。** 研究包含快速补救分类及回退对挖掘数据的影响。后者在 100 个 Java 系统中发现 1,447 个被回退的重构提交。文中 0.27 是每个完全回退提交平均对应的噪声重构数据点，**不是全部重构有 27% 被回退**。检测限于相邻提交；正文包含临时试验被撤回的解释，不能一律解读为设计遭否定。[论文，印刷页 19–21](https://d-nb.info/1249003601/34)

**与设想差异（本笔记判断）。** 这是历史标签可靠性材料，不是抽象取舍基准。作者针对部分挖掘任务讨论清除回退噪声；我们的潜在任务可能反而需要保留撤回链及理由，但必须重新定义标签。论文没有证明被回退重构均错误，也没有覆盖任意长时间后的反向设计决策。

## 数据适配性对照

下表是依据上述阅读范围作出的材料适配判断，“未核得”不等于不存在。

| 材料 | 历史 PR 偏好对 | 负例 | 性能取舍 | 后续 revert |
| --- | --- | --- | --- | --- |
| Linux 去重研究 | 有真实补丁版本/评审反馈，但来自研究介入；未核得标准化 A/B 偏好对工件 | 有 Dropped 及不同理由；需区分错误实现与合理保留重复 | 有明确讨论；未核得性能测量数据集 | 本轮所读内容未建立合入后的长期回退链 |
| OpenStack 评审研究 | 有历史 Gerrit 评审；未核得同题候选偏好对 | 有异议/放弃，不能直接作为技术负例 | 未核得专门性能权衡标注或测量集 | 筛选排除重构撤销评审；不是回退研究 |
| Quick remedy | 有提交—回退关联，不是 PR 候选偏好对 | 可作为待解释的撤回信号；包括试验性变更 | 未核得针对抽象性能权衡的标签 | 有相邻提交回退分析；不等于长期追踪 |

来源对应上一节各篇正文与工件入口。本轮没有确认任何一份可直接投入“历史 PR 偏好学习”的完整数据包；这是访问与核对范围的报告，不是文献空白结论。

## 对后续设计的有限启示

以下仅是基础调研后的协议建议，未执行标注或实验，也未变更研究计划：

1. 分开记录“当前方案不可接受”“保留重复更合适”“暂时不值得集成”“流程中止”“试验撤回”。同一事件可同时含多个理由，不强迫单一标签。
2. 若以后构造偏好对，应保留同题候选、当时可见上下文、理由及版本顺序；不能把不同任务的 accepted/rejected 任意拼对，也不能让回退后的信息泄漏进当时输入。
3. 把性能担忧与测得退化分开；把局部可读性与跨驱动共同维护成本分开。评审意见可作为证据，但不替代契约与性能验证。
4. 回退应先辨析范围和动机，再决定是否用于负例。恢复旧代码、撤销试验、撤回部分错误实现，并不都表示维护者拒绝公共抽象。

## 实际检索记录与未展开线索

检索日期为 2026-10-28；入口为联网搜索及论文/作者站内页面。下列为实际执行的主要查询词，保留失效或低相关查询，以便主代理避免重复：

```text
refactoring code review rejected refactorings empirical study duplication
refactoring rollback revert empirical study reasons abstraction
"refactoring" "rejected" "duplication" study developers
"refactoring" "reverted" empirical study
"To clone or not to clone" developers empirical
"When Do You Repeat Yourself" pdf
refactoring "rollback" "empirical study"
"When Do You Repeat Yourself" Linux
"refactoring" "reverted" study refactoring reversal
"Why are Commits Being Reverted" pdf
"3794915.3795783" "performance"
"3794915.3795783" "Authors"
"17503684"
"3794915.3795783" "T3" "T2"
"Quick remedy commits" "replication"
site:pmc.ncbi.nlm.nih.gov/articles/PMC8553712/ "6." "refactoring"
site:pmc.ncbi.nlm.nih.gov/articles/PMC8553712/ "0.27" "false"
"Code Review Practices for Refactoring Changes" "replication" github
```

- `To clone or not to clone`、裸数字 `17503684` 及部分站内查询产生大量无关结果，未作为证据。
- [Why are Commits being Reverted?（作者页）](https://rebels.cs.uwaterloo.ca/confpaper/2016/10/04/why-are-commits-being-reverted.html)：仅筛选摘要，涉及一般提交回退；三篇限额内优先保留直接分析重构标签污染的 Quick remedy，不再展开。
- [One Thousand and One Stories（作者 PDF）](https://mkaouer.net/publication/golubev-2021-one/golubev-2021-one.pdf)：仅见检索摘要/节选，涉及 IDE 重构 undo 的自报原因；与合入后 revert 不同，未纳入三篇卡片。
- [An Empirical Study on Refactoring-Inducing Pull Requests（作者 PDF）](https://users.encs.concordia.ca/~nikolaos/publications/ESEM_2021.pdf)：仅见检索节选，偏向评审诱发重构，未展开。
- ACM 直连受阻时只使用出版方返回的正文段落，没有使用其 AI 摘要作为事实来源；Zenodo 未访问成功。OpenStack 工件仅核对说明，Quick remedy 工件仅核对目录/README。上述限制不能写成“数据不可用”或“已完成复现”。

本旁支仅将“取舍理由”“评审过程”“回退标签”三类证据分开交付；不据此声称我们的方法新颖、有效，或既有工作未覆盖该问题。

## 主线整合记录

2026-10-28 主代理将以上三篇分别登记为 P26、P27、P28。补存 P27 作者 PDF 和
P28 图书馆 PDF，P26 DOI 直连返回 403；获取结果及校验和已写入证据清单。
上述新增下载不改变旁支原有阅读深度，也未下载案例数据集。
