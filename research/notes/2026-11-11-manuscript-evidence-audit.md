# 论文材料充分性与主张边界审计

核查日期：2026-11-11。仅阅读本地历史报告、台账及笔记，并对已有候选ID作只读集合联结；未重新运行检测、内核测试或外部研究。内核语料固定于 `7e3ac94431a0dbb376d2fc8d85098deeff1bba09`。下列路径均相对本书仓库；报告记录的成功不等于本轮复现实验。

## 主张—证据—允许推论—缺口

|拟写主张|已核对证据|允许推论|不能推出／缺口|
|---|---|---|---|
|2180个源码单位，812个SCC合格单位，156对输出|`research/evidence/runs/2026-11-05-rust-scc-01/report.json`：阈值参数8、最少65 tokens、最多500000；329266次oracle比较，输出与oracle均156对，无缺失或额外对；SCC版本为 `88314f51fdf3cd89103eb2c19fb56464308846c8`|固定源码单位与token协议下，80%阈值检测输出与token算法oracle一致|不是全内核所有配置的函数全集；不是156个重构机会，也不是语义precision/recall。`semantic_labels=unverified`、`paper_result_reproduction=not_run`；80%不能写成原论文70%任务复现|
|SCC已审18对、未审138对|`research/protocols/discovery-ledger-v3.json`：18对归入15个维护主题，`net_benefit_confirmed=0`；`research/notes/2026-11-06-followup-review-closure.md`|形成有源码依据的静态处置与待证问题清单|15主题不是独立实验样本；未审138对不能自动判负；保留线索、已有复用、契约差异都不是独立人工真值|
|doc-TFIDF输出全局top20|`research/evidence/runs/2026-11-09-doc-tfidf-01/report.json`、`2026-11-09-doc-tfidf-02/report.json`：2180文档，1400缺失或空，780非零；词表2084，正分数对204459；sklearn1.7.2。协议说明见 `research/notes/2026-11-09-doc-tfidf-first-run.md`|固定输入、冻结协议下的轻量文档检索基线；全2180条参与IDF拟合，分数先取12位小数再筛选、排序与按ID破同分|文档相似不是真实功能等价；两次本机运行不证明跨环境普遍确定性。约1秒仅fit/评分/排序，不含安装、收集与人工审阅，不能作为端到端成本或性能优越证据|
|两轮共38个不同静态审阅pair|本轮直接联结 `research/protocols/discovery-ledger-v3.json` 各family的 `pairs`，用 `research/evidence/runs/2026-11-05-rust-scc-01/candidates.json` 将file_ids映射到member.id，再与 `research/evidence/runs/2026-11-09-doc-tfidf-01/review-queue.json` 的unit_ids规范化无序配对比较：旧18∩doc20=0，并集38。doc rank3对应file_ids `[936,937]`，在完整SCC156内但不在已审18内|可以明确写“38个不同pair身份的静态审阅记录”|不是38个独立样本、38项优化机会或38个人工标签。旧doc复核笔记把完整输出重叠误当已审集合重叠；本审计以实际ID联结纠正，不能沿用37对说法|
|doc复核提供不同候选及失败分析|`research/evidence/runs/2026-11-09-doc-tfidf-review-01/report.json`：20对，配置替代2、契约差异7、已有委托6、小重叠但收益未知5；19对双方均低于65 tokens，1对双方满足大小门槛；`independent_labels=not_available`、`runtime_tests=not_run`|这些解释支持案例级候选筛选边界；doc路径可触达此SCC协议大小门槛外的单位|不能把19对称为SCC语义漏检或doc更优；两路输入资格不同。没有确认收益不等于全部是假阳性；3项负控只验证标注结构检查，不能验证判断内容。开发过程中已读案例不应再充当未触碰的最终测试集|
|metadata候选通过94项测试|`research/evidence/runs/2026-11-05-metadata-pair-01/report.json`：original与candidate均expected/observed94、exit0、无缺失/额外/non-ok；`candidate.log:889`记录94 passed。两组初始磁盘摘要相同，候选在隔离源码副本；运行限定 `kvfs::mount::tests,kvfs::node::dentry::tests_dentry`|历史证据支持固定配置、两个测试模块下原版与候选均通过同一94项测试|不是188个独立测试，更不是全内核等价、并发安全或维护净收益证明；两组缓存策略不同，不是计时实验。本轮没有执行测试|
|metadata测试夹具去重可编译且未混入生产测试模块|`research/evidence/runs/2026-11-05-metadata-fixture-patch-02/report.json` 记录构造点2→1、13字段保留及隔离副本补丁检查；后续 `research/evidence/runs/2026-11-05-metadata-production-01/report.json` 记录 `UNITTEST=n` build exit0、depfiles排除ut-tests、runtime未运行、net_benefit未验证|支持一个受限候选从静态提出到测试及非unittest构建的证据链；生产构建结果应引用后续报告|不能将早期patch报告的not_run误写成全程未测试；也不能将后续构建通过写成生产运行验证。构造点减少不直接证明总代码减少、性能提升或长期维护改善|

## 充分性判断与建议写法

**材料足以支撑完整的经验性先导研究／可行性与失败分析论文初稿及对应汇报，不足以支撑已验证的新检测算法或普遍优化效果论文。** 可把贡献定位为：固定Rust源码上的有界候选发现流程、分阶段证据门槛、38个不同pair的静态分析，以及一个受限测试夹具候选的历史构建／测试验证。不能以使用成熟token检索、TF-IDF或LLM分析本身宣称方法新颖；不在本轮作全面新颖性结论。

优先缺口是：独立人工标注与分歧处理；同输入资格、同审阅预算的比较；漏检及未知负例的合理分母；未参与开发的冻结留出语料／配置；标准基准的实际执行；与所宣称收益相匹配的维护或性能测量。多Agent复核不是独立人工标签，算法oracle一致不是语义标签可信。当前结果可以如实成文，不必补造这些实验；摘要、结果表与PPT均应保留“先导、固定范围、静态解释、收益未确认”的限定。
