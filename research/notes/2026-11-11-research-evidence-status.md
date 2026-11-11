# 原文、阅读记录与复现状态核验

核查日期：2026-11-11。本轮仅读取本地文件、笔记和历史run报告，并用Python标准库对实际文件字节计算大小与SHA256；没有联网、重新下载或执行旧实验。**原文已归档、已有定向阅读记录、工具已运行、论文实验已复现是四个不同状态。** 本轮没有重新全文精读，也不以文件存在证明曾经逐页阅读。

## 1. 原文件确实存在：本轮实算字节数与SHA256

下列路径相对book根目录；PDF已检查文件头为`%PDF`，HTML为DOCTYPE开头。哈希证明当前本地字节身份，不独自证明来源真实性或下载历史；来源关联沿用归档与阅读记录，本轮未与远端重新比对。

|对象与实际路径|字节数|本轮计算SHA256|
|---|---:|---|
|SCC：`research/evidence/originals/P01-sourcerercc.pdf`|465934|`987fd8e2e32fce2dd834cd968115f4e9b598c64076b05b18fb3776a76a4c2745`|
|Wrangler：`research/evidence/originals/P11-wrangler.pdf`|428230|`89132f6ddb5500b3bd9b2d37a926aee2aae9dfc4a1cfb2ee2a3dd2ff95b2585f`|
|Librarian全文：`research/evidence/originals/P21-librarian-v3-full.html`|1156241|`5d5986de2f3b65668391b103ac77a800caa346a5b582443e469e1a65c5977b85`|
|Librarian摘要页：`research/evidence/originals/P21-librarian-v3-abstract.html`|40219|`bd3fded2db132302e5103d4ac13f0b5891406f40b1fb26848acf39178b9bc002`|
|注释LDA论文：`research/evidence/runs/2026-11-09-comment-clone-reading-01/paper.pdf`|695256|`19ac0b765388bd39720bcb4da3cd9aa2008bbe937a1d76ddb70d9051d7f9c66e`|
|注释论文提取文本（派生物，不是第二篇原文）：`research/evidence/runs/2026-11-09-comment-clone-reading-01/paper.txt`|82607|`664e919a2cdf60868d549d8785ecd8fe308f89cb9954c2270b17e41d5a025ac2`|

来源入口分别为[SCC固定v1](https://arxiv.org/pdf/1512.06448v1)、[Wrangler作者PDF](https://www.cs.kent.ac.uk/pubs/2011/3087/content.pdf)、[Librarian固定v3全文](https://arxiv.org/html/2506.11058v3)、[注释论文固定v1](https://arxiv.org/pdf/2006.14505v1)。注释论文同目录`provenance.json`保存curl下载及pdftotext命令、版本、阅读范围和`not_reproduced`状态；其中两个摘要与本轮实算一致。Librarian不是“只有摘要页”：另有上表的全文HTML。

## 2. 可追溯的阅读范围（历史笔记声明，不冒称本轮重新精读）

|对象|具体笔记与声明范围|阅读边界|
|---|---|---|
|SCC|`research/notes/2026-11-05-p01-original-task-audit.md`：§2、§3.1、§3.5、§4含表1/3/4/5、§5；记录token单位、70%配置、参考分母、精度抽样和快照缺口|有定向原文参数核查，不能称已重算原始标签或审计所有实验数据|
|Wrangler|`research/notes/2026-11-05-structural-semantic-candidates.md`：P11 §4.1，印刷页6–9；记录表达式序列、绑定注释、结构泛化与anti-unification|该轮明确未重核§4.2增量机制与实验结果；不升级成全论文复现。`2026-11-05-scc-wrangler-reproduction-readiness.md`另记录官方源码/入口核查|
|Librarian|`research/notes/2026-10-27-librarian-reading-01.md`逐轮记录§3、§5、§6/6.2、§7/8、附录A及部分E；`2026-11-05-librarian-reproduction-readiness.md`记录§3–6、附录C与F定义；`2026-11-11-librarian-presentation-audit.md`记录§4–7、附录C/E及F开头直接回读|已做多轮定向阅读；不是全部附录、原始参与者数据或统计实现已完整审计。表2与正文数字、模型/集合数口径仍有待对齐项|
|注释LDA|`research/notes/2026-11-09-comment-clone-method-reading.md`：§II-B、§III–V、表I/II及部分参考文献；工件笔记`2026-11-09-comment-clone-artifact-readiness.md`另查作者链接与2018前作关系|文件集合覆盖指标与配对准确率已作区分；作者实现与标签包入口未找到不等于证明未公开。2018前作全文获取失败不能计作已读全文|

## 3. 实际运行证据与不能声称的复现

以下均为本轮直接读取的历史报告；“已运行”指已有保存的运行结果，不代表本轮重跑成功。

- **SCC已跑工具冒烟及Rust前端适配实验，但原论文效果未复现。** `research/evidence/runs/2026-11-05-scc-native-01/report.json`与`2026-11-05-scc-native-02/report.json`均记录exit0、预期/实际/oracle三对一致；`2026-11-05-scc-boundaries-01/report.json`记录80%和64/65 token边界检查通过；`2026-11-05-scc-smoke-regression-03/report.json`记录回归通过。反例同样保留：`2026-11-05-scc-positions-01/report.json`的`position_gate_passed=false`，空行样例的方法范围及正文切片不匹配，不能概括为原Java前端所有定位均正确。
- **Rust SCC运行**：`research/evidence/runs/2026-11-05-rust-scc-01/report.json`记录检测器SHA `88314f51fdf3cd89103eb2c19fb56464308846c8`、exit0、2180单位、812合格、156对，和329266次token-oracle比较结果一致，Java算法未改。其字段明确为`semantic_labels=unverified`、`paper_result_reproduction=not_run`。80%/最小65 tokens的Rust适配不是原论文70%设置的Java基准复现，更不证明156项重构收益。
- **Wrangler未运行（按当前所核查材料）**：准备笔记记录官方固定源码、Erlang入口、历史语料与运行环境缺口；本轮在`research/evidence/runs/`目录名及其一层`report.json`限定盘点中没有找到Wrangler运行报告。不能把源码归档、结构方法阅读或自己的Rust AST工具说成Wrangler执行成功。
- **Librarian未运行原任务（按当前所核查材料）**：已有官方README、运行脚本和模型/API条件核查；准备及汇报审计笔记均明确未调用模型或执行作者评价，本轮限定report盘点未找到Librarian运行报告。不能把作者MDL/通过率数字写成我们复现的数字。
- **注释LDA未运行**：论文归档目录的`provenance.json`明确`experiment_status=not_reproduced`；方法笔记写未运行作者实现。作者专用实现/标签包尚未定位，不存在本轮可核实的LDA训练、主题组或原论文指标复算报告。
- **文档TF-IDF确实另有运行，但绝不是LDA复现。** `research/evidence/runs/2026-11-09-doc-tfidf-01/report.json`和`2026-11-09-doc-tfidf-02/report.json`记录sklearn1.7.2、2180文档、1400空/缺失、780非零、top20，`semantic_evaluation=not_run`。这是我们另定的TF-IDF/cosine检索基线：算法、函数级对象、Rust语料和评价口径均不同于注释论文文件级LDA主题组。`2026-11-09-doc-tfidf-review-01/report.json`另记录20对静态复核、`runtime_tests=not_run`、`independent_labels=not_available`，不构成LDA实验或独立人工真值。

以上简写的run目录均位于`research/evidence/runs/`。缺失结论限定于上述目录/报告与笔记，未搜索整机或声称绝无其他未登记执行；本轮也未逐个重验所有run工件哈希或重放日志。**交付可准确表述：四条研究线都有实际本地原文及指定章节阅读记录；SCC有工具/适配运行，文档TF-IDF有独立基线运行；Wrangler、Librarian、注释LDA没有本次可核实的原任务复现，SCC也不能称已复现原论文评价数字。**
