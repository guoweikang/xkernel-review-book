# 需求语义结构化：有界先例与实验方向

日期：2026-11-13。仅核查两项相关一手工作，不是穷尽查新或创新性结论。本笔记记录文献阅读，未复现两项方法；HanLP烟测是另一条实验记录。

## 1. Rimay：角色、动作与条件结构已有明确先例

Veizaga、Alferez、Torre、Sabetzadeh、Briand，**On systematically building a controlled natural language for functional requirements**，*Empirical Software Engineering* 26:79，2021，DOI [10.1007/s10664-021-09956-6](https://doi.org/10.1007/s10664-021-09956-6)。本轮直接核读[出版商全文](https://link.springer.com/article/10.1007/s10664-021-09956-6)中 §3.3.5 的规则构造/角色命名、§4.3–4.3.1 的响应与编辑器、§5.1.1–5.1.4 的评价流程，并核对摘要分母；未逐条审完附录语法，部分嵌图未转录。

- 已有内容：基于 VerbNet 等词汇资源组织动作信息，将 AGENT 调整为领域使用者熟悉的 ACTOR；语法包括情态动词、条件和系统响应，配套 Xtext 编辑器。不是仅计算词相似度。
- 核心边界：它帮助作者**用受控语言表达/改写需求**，不是本轮核实到的任意 rustdoc 自动抽取器。摘要的 405/460（约88%）是四份金融需求文档的可表达性，不是自动抽取准确率；§5.1.2 明确由两位作者改写并由领域分析师检查意图，§5.1.3 还包含迭代改进语法。不能将该数值当冻结模型的独立测试性能。

## 2. FRET：结构化需求→逻辑→实现映射已有工具链

Giannakopoulou、Pressburger、Mavridou、Rhein、Schumann、Shi，**Formal Requirements Elicitation with FRET**，REFSQ 2020 联合活动论文集。直接阅读 [NASA 作者论文 PDF](https://ntrs.nasa.gov/api/citations/20200001989/downloads/20200001989.pdf) §2（PDF第2–4页，输入/可视化/分析）与 §3（第4–5页，架构）；未复现关联案例或检查全部实现。

- 2020论文的 FRETish 有 scope、condition、component、shall、timing、response 六字段；生成时序逻辑并可在输入轨迹上评价。§2 Requirements Analysis、§3 Analysis Portal 明确要求关联需求变量与模型/代码变量，再导出验证代码。因此“需求已解析”“逻辑公式正确”和“实现满足需求”不是同一证据。
- 官方[写作说明](https://github.com/NASA-SW-VnV/fret/blob/master/fret-electron/docs/_media/user-interface/writingReqs.md)本轮亦已读取：当前页面增加概率模式，最多七字段；不要把当前页面与2020版本混写。`shall` 表达应当符合要求，不是已经执行的观察。官方[仓库入口](https://github.com/NASA-SW-VnV/fret)由论文提供；本轮没有安装、固定源码版本或验证运行可用性。

## 3. 对本项目可说与不可说的边界

**不能仅凭目前方案宣称新颖**：角色/动作/条件/情态字段化、受控自然语言、结构化需求转逻辑、用轨迹检查公式，以及把需求映射到实现变量。这两项工作足以要求我们收窄相关表述；但不构成全领域查新完成。也不能以“换成 Rust/rustdoc”“接入现成 SRL”“16个已见用例通过”替代方法贡献证据。

**仍可提出的研究问题，不是已证明差异**：面对非受控、版本化 rustdoc，如何保留来源与语气，避免将报告/规范提升为运行事实，并在字段不确定时拒答；这种约束能否在未见文本上减少错误确认且不过度损失覆盖率？本轮所读章节不足以断言两项先例没有处理任何报告/事实问题；亦未核查任意自然语言抽取领域的完整先例。SRL预测不能自动替代需求意图核验、程序变量绑定或实现验证。

## 4. 一个可证伪的后续实验（提案，未执行）

冻结同一抽取器和字段映射后，只比较**是否强制声明类型/证据来源门控**：①仅靠已抽字段确认；②缺少实现观察或证据绑定时禁止从规范/报告推出实际动作。两臂使用相同文本、字段与候选，不能给第二臂人工真值字段而称自动收益。用未参与规则编写的措辞及项目/模板分组留出；测试标签由不看系统输出的复核者审定，保留歧义与分歧。现有16例只作开发控制。

预先冻结指标：规范/报告→实际行为的错误升级数及分母、字段提取正确性、回答覆盖率、已回答项错误率，并单列条件方向与角色绑定。金标准字段输入仅作诊断上界，不能混入自动结果。增加真正有实现证据、同义改写、角色交换和 only-if 方向控制；若少错仅来自全部拒答，或在预设可比覆盖率下未减少错误，则收益假设不成立。完成有界批次即报告全部结果，不依据结果继续特判。即便成功，也先支持限定域的证据门控效果，而非新通用语义模型、功能重复真值或重构收益。

## 实际检索与取得范围

协作初审查询词两条：`Rimay controlled natural language requirements actor modal condition paper Arora`；`FRET formal requirements elicitation tool NASA conditional shall semantics paper`。随后读取上述两项一手全文/官方说明及文内定位。PMC镜像首次可读、后续定位遇到验证码，改读出版商全文，未绕过限制。主研究线程另行打开出版商全文和NASA PDF核对任务边界，并下载两篇PDF；URL、大小和SHA256存于`research/evidence/runs/2026-11-13-requirement-semantics-01/sources.json`，原文存于Git忽略的originals目录。没有下载源码或执行两项工具；本笔记没有作者实验之外的新测量。
