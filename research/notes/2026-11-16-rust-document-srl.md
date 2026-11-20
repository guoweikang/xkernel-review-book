# 真实Rust文档：角色保留与调用条件的提取边界

## 问题与冻结设计

在词汇诊断后回归真实工程：同一个提取器能否保留文档中决定共享边界的关键内容？选择已有源码和行为证据的两个开发案例，不再增加通用句式实验。

每例三种文本，共6条：原生注释原句、已有源码辅助补全文本、已有受控改变文本。后两者直接复用`governed-doc-claims-v2.json`，不为本轮模型表现改写。`scripts/freeze_rust_srl_inputs.py`在推理前冻结文本、研究问题、两份源码副本、来源路径及SHA-256。两个案例均已用于开发，不是独立测试。

权限案例绑定`with_permission`；命令案例绑定`CommandFile::write_iter`，其原生文本来自类型注释而非方法完整契约。补全文本由研究员编写，未获提供者确认。无文档条件记为缺证据，不用空句计算正确率。补全同时增加事实和改变表述，不能据此隔离“文档格式”的收益。

## 实际执行

沿用固定HanLP模型、既有分层环境、离线CPU及安全加载边界，6条输入各两遍。每遍149词元、16帧、49角色跨度；两遍原始输出一致。原始完整性检查及4项损坏控制通过。没有训练、调提示词、改提取规则或运行新生产补丁。

评价是冻结范围内的原始跨度定性审计，不是字段准确率或重复检测准确率。以下观察直接来自`2026-11-16-rust-srl-smoke-01/raw-1.json`；角色标签不自动等于逻辑含义。

|输入|原始输出观察|可以与不可以推断什么|
|---|---|---|
|权限原生|Returns帧把`with new permission bits and the same file type`合成一个ARGM-MNR|文字仍在，但没有独立的“修改／保留”语义字段|
|权限补全|Return帧有`with replacement permission bits` ARG2，retaining帧有`original file - type bits` ARG1|角色相关内容有可引用跨度；未自动映射到Rust字段或证明实现相符|
|权限改变|Return的ARG2转为file-type，retaining的ARG1转为permission|输出保留了交换差异；工具仍不能仅凭文本判断哪个函数应该这样做|
|命令原生|consumes的ARG1只有each，write被标为另一个PRED|原句的“完整请求”没有形成可用的消费契约表示|
|命令补全|只输出invokes与collected两帧；主句invoke没有PRED|原文已有条件也未形成完整的调用动作、频次及条件绑定|
|命令改变|只输出run、copied、waiting三个PRED；主句invoke同样缺失|不能以主调用帧比较一次完整调用与逐片段调用|

命令补全中的invokes帧只有`invokes`和`no handler`，没有恢复“collection error or zero progress”的触发主体。其否定表现在ARG1中的no，而非ARGM-NEG；不能把“没有ARGM-NEG”直接解释为肯定调用。本文只报告原始观察，没有为这个例子新增词汇规则。

## 与源码证据核对

冻结源码来自既有固定版本`7e3ac94431a0dbb376d2fc8d85098deeff1bba09`的证据副本。本轮未重新获取最新生产版本。

- `research/evidence/runs/2026-11-16-rust-srl-inputs-01/command-source.txt:87`先判断空输入、4096上限，再循环收集；`self.write`在循环后。收集错误或零进展发生在处理器之前。
- 同文件第82行的直接`write`不具有同样的空输入前置检查。处理器调用之后的失败不保证没有外部副作用；回退也不能证明任意效果被撤销。
- `research/evidence/runs/2026-11-16-rust-srl-inputs-01/role-source.txt:145`实现替换权限位、保留类型位。改变文本相对于这个函数不成立，却接近相邻`with_node_type`的职责，不能标为整个仓库不存在的行为。
- 命令改变文本是反事实策略，不是另一个真实流式实现的完整契约。已有模型轨迹可区分多片段场景，但不算内核集成验证。

只读代理复核与主线程源码阅读共同指出以上边界；不把Agent意见算成独立人工标注。已有行为依据见[角色控制](2026-11-12-document-role-controls.md)、[事件轨迹](2026-11-12-stream-command-traces.md)。本轮没有重新执行这些旧实验。

## 对方法的影响

**文档治理和提取可靠性是两层问题。** 用户要求正确且包含必要元素的文档是合理的实验前提；本轮并不否定它，而是说明该前提不能替代提取器的验证。权限例提供可用的角色跨度，命令例仍丢核心动作，不能宣称补全普遍有效。

现有SRL不宜直接承担“确认可共享”的最终判定。下一项应比较两条明确分开的路径：自然语言自动提取，以及提供者显式声明的结构化契约输入；后者消除部分提取歧义，却不自动保证声明真实，必须继续绑定函数身份、版本和源码/行为证据。结构化契约和受控语言已有先例，不能把它们本身称为新颖点。

具体下一批先冻结契约适配接口及否定控制：缺核心动作、错函数归属、缺条件、改角色时不能升级为“已确认”。先以这些开发案例验证工具协议是否守住边界，再找独立案例测收益。职责归属另外保留规范依据轨道，不把规范owner误当执行行为。

## 工件与复现

- 冻结输入：`research/evidence/runs/2026-11-16-rust-srl-inputs-01`。
- 两遍原始结果与模型清单：`research/evidence/runs/2026-11-16-rust-srl-smoke-01`。
- 完整性检查、运行日志、结构清点与摘要：`research/evidence/runs/2026-11-16-rust-srl-audit-01`。

执行入口是`run_hanlp_srl_smoke.py --protocol research/evidence/runs/2026-11-16-rust-srl-inputs-01/inference-protocol.json`，其余参数沿用固定assets与精确兼容选项；新执行必须使用新run-id。`check_hanlp_srl_smoke.py`核对原始工件，`summarize_hanlp_frames.py`生成描述性清点。冻结器明确使用本批ID，不覆盖重跑。
