# 文档关系提取：依存解析能提供什么，不能保证什么

## 研究位置

文档相似度可能忽略动作对象、条件方向及职责归属。上一轮模拟表明，错误关系进入逻辑求解后仍会得到形式上有效的错误结论。本轮检查公开解析器能否提供可追溯的上游结构，不把句法树当作契约真值，也不扩展到生产优化。

## 公开方法及能力边界

|方法|公开输出|本研究的用途与缺口|本轮状态|
|---|---|---|---|
|spaCy DependencyParser|词元依存关系、中心词、句界|定位从句、否定和主被动线索；不直接输出逻辑蕴含或职责事实|固定版本实际运行|
|Stanza|分词、词性、形态、依存等流水线；依存采用UD体系|另一种结构表示候选；不能把不同体系标签直接互换|论文概述与文档核读，未运行|
|Deep Semantic Role Labeling|面向谓词的论元跨度与角色|比句法主宾语更接近动作参与者；仍不等于条件方向、规范或事实性|初步来源审查，未复现|

依据：[spaCy官方接口](https://spacy.io/api/dependencyparser)、[语言学特征说明](https://spacy.io/usage/linguistic-features)、[Stanza论文](https://aclanthology.org/2020.acl-demos.14/)、[Stanza依存接口](https://stanfordnlp.github.io/stanza/depparse.html)、[Deep Semantic Role Labeling论文](https://aclanthology.org/P17-1044/)。这里不是最新方法排名，也未复现这些论文的基准成绩。Stanza PDF和两份spaCy网页的下载来源、大小与摘要保存在`research/evidence/runs/2026-11-13-parser-sources-01/sources.json`；SRL尚无本地原文归档，不宣称完成全文精读。

## 冻结输入与实际运行

协议：`research/protocols/contract-dependency-probe-v1.json`。全部采用此前16对控制中的前提和假设，精确去重后20句，不按解析结果筛选。spaCy 3.8.11、en_core_web_sm 3.8.0，排除NER但保留其他管线组件；记录实际组件、全部包版本、模型文件摘要和安装来源。

两遍各解析231个词元，原始JSON逐字节一致。独立检查脚本核对摘要、词元位置、依存索引与根可达性、句界覆盖及重复一致性。这些是工件完整性检查，不是句法或契约准确率。

首次导入因缺少click失败，未进入解析；隔离环境补装click 8.1.8后成功，pip check通过。失败、安装修复、执行与检查日志全部保留，没有删除失败以制造一次成功的记录。

## 可复查观察

下列编号是`texts.json`与`parses-1.json`中的零基索引；解释属于研究员对已见开发样例的检查，不是独立人工标注集。

|输入|实际输出|对关系提取的影响|
|0：handler called only if collection succeeds|only和if都连接succeeds，succeeds通过advcl连接called|保留条件线索，但未给出必要条件方向|
|4：两个动作分别被not否定|两个neg分别连接succeed和called|保留局部否定位置，不直接证明逆否关系|
|5、6、8：permission/file-type bits change|部分change标成NOUN；5中的第一个change还成为第二个change的nsubj|不能机械地把解析主语当字段、谓词当动作；工程词语和协调结构值得单独测试|
|10：documentation states that module supports|supports通过ccomp连接states|报告层与内容层在结构上分开；仍须解释报告来源，不能直接断言实现支持|
|15：architecture requires crate to decode|crate是requires的dobj，decode是advcl|仅按显式主语无法直接绑定decode的执行主体|
|19：does not require ... to decode|decode通过amod连接properties，与15的结构不同|否定改写下结构变化，不能假定统一模板稳定|

这证明了原始输出中同时存在有用线索和需要处理的偏差，没有证明所有解析器失败，更没有测出重复功能发现准确率。20句都已用于开发，不能作为新方法的独立测试集。

## 方法决策

1. 保留依存结构为一个可追溯视角，不直接接入自动契约裁决。记录原句、词元跨度、模型身份和不支持状态。
2. 不针对这20句增加特判，也不改写文本后只报告更好结果。文档规范可以主动要求清楚的主体、动作、对象、条件与规范/事实状态，但其收益必须另测。
3. 下一批先冻结字段级参考及措辞控制：词汇、主动/被动、协调、否定、only-if与报告/要求。区分句法准确、角色绑定准确、方向/语气准确与最终判定，错误和拒答分别计数。
4. 公共语义角色工具的工件核验继续进行；先确定可运行实现与训练任务，再决定是否增加第二基线。另设后续未见措辞与真实rustdoc，不在当前20句上选出“最优方法”。

这些步骤服务于文档辅助发现及crate职责确认：把“谁应负责”和“谁实际执行”分开，而不是转向一般自然语言排行榜。尚未实现自动逻辑提取、独立标签评测或生产重构。

## 复现入口

```sh
.build/syntax-env/bin/python scripts/run_contract_dependency_probe.py --run-id 新批次ID
python3 scripts/check_contract_dependency_probe.py research/evidence/runs/新批次ID
```

运行归档：`research/evidence/runs/2026-11-13-contract-dependency-probe-01`。`report.json`覆盖原始实验产物；`supplement.json`另外覆盖修复、执行及独立核对日志。模型本体位于Git忽略的隔离环境，不把第三方权重误称已上传。
