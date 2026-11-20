# 真实候选的文档干预：参数、委托与共同步骤

## 所回答的问题

上一批主题检索受大量并列限制，不能把相似度当重复性。本批不调主题数、不扩大候选池，检查另一个必要环节：公开语义角色标注工具能否保留真实函数文档中区分参数、调用目标及共同步骤的信息？

这不是新的发现效果评测，也不判断能否安全重构。复用固定HanLP模型与既有离线推理程序；模型出处、下载身份、安全加载兼容边界见[SRL实跑记录](2026-11-13-hanlp-srl-smoke.md)。未训练或添加案例特判。研究审议建议复用成熟提取器，而非再做一轮字段拼接词袋相似度；主研究员采纳。

## 固定对象与干预

选择[上一批LDA候选](2026-11-16-doc-lda.md)并集的零起始索引0、8、25、9：read/write、Once两接口、symlink/mkdir、查询/创建。八个函数均来自既有冻结语料，不是独立测试集，选择已受源码审阅影响。

每个函数三份文本：native原生绑定文本、complete源码辅助补写、altered在补写中只替换一个目标字符串，共24份。自然语言输入只含id/text，不把参考判断、其他函数标签或“是否重复”答案交给模型。单个字符串替换不保证模型仅改变一个论元，它只是输入干预约束。

**complete是实验臂名称，不是完整契约认证。** 补写聚焦目标关系，没有穷尽错误、panic、线程、类型、配置等条件；未获提供者确认。read/write原生trait注释描述接口意图，补写描述默认实现的切片可变性和InvalidInput返回，二者语义范围不同。不能将效果变化归因于纯格式改善，也不能宣称满足了全部文档治理要求。

源码冻结发现read/write均是默认报错桩，因此不虚构成功的数据传输：本批把原拟议的“读写方向”测试收窄为shared/mutable切片参数和错误返回。symlink/mkdir共享的require_directory_operations带`?`，可能提前返回；补写只概述后续成功路径，没有明确写出这个前置条件。后续完整契约需要补齐，本批不能声称抽出了条件正确的共享机制。

| 对象 | complete → altered的唯一文本修改 |
| --- | --- |
| write | shared → mutable |
| read | mutable → shared |
| try_call_once | try_call_once_slow → call_once |
| call_once | calls try_call_once → calls try_call_once_slow |
| symlink | a target string → a mode value |
| mkdir | a mode value → a target string |
| lookup_inode | retrieves → creates |
| constructor | creates → retrieves |

## 执行与完整性

冻结器`scripts/freeze_candidate_srl_inputs.py`保存24文本、8份原函数片段、unit身份与SHA、干预记录、协议及自身副本。输入目录为`research/evidence/runs/2026-11-16-candidate-srl-inputs-01`；原始推理与检查在`research/evidence/runs/2026-11-16-candidate-srl-01`。

沿用HanLP 2.1.7及既有资源，CPU4线程、seed0、batch4，两遍，网络禁用，强制安全权重加载；仅允许已验证的未执行NER缓冲区兼容处理。实际两遍原始输出一致；每遍24条、934词元、84帧、249跨度，1条零帧（native mkdir）。4项损坏控制全部拒绝；跨度、ID、文本、谓词数及归档摘要检查通过。这些数字是完整性统计，不是84个正确语义关系或249个独立样本。

```sh
python3 scripts/freeze_candidate_srl_inputs.py
timeout 600 .build/srl-preflight-env/bin/python scripts/run_hanlp_srl_smoke.py --run-id 新批次ID --assets-run 2026-11-13-hanlp-assets-03 --allow-unused-ner-buffers --protocol research/evidence/runs/2026-11-16-candidate-srl-inputs-01/inference-protocol.json
python3 scripts/check_hanlp_srl_smoke.py research/evidence/runs/新批次ID
python3 scripts/summarize_hanlp_frames.py research/evidence/runs/新批次ID
```

冻结器拒绝覆盖已有输入目录；复跑模型可直接引用冻结协议并使用新的run-id。checker与汇总器输出分别保存checks.json、frames.json；它们不做语义真值评价。

## 24份输出逐项审读

下面每行覆盖同一函数的三个臂，均直接核对raw-1.json；第二遍逐字节相同。ARG编号只引用模型输出，不被直接转换成软件领域字段。

| 函数 | native | complete | altered |
| --- | --- | --- | --- |
| write | Writes谓词与file data论元 | accepts的ARG1为shared byte slice；returns保留错误 | accepts的ARG1改为mutable byte slice；错误返回保持 |
| read | 错将file标为PRED，Reads成ARG0 | accepts的ARG1为mutable byte slice；returns保留错误 | ARG1改为shared byte slice；错误返回保持 |
| try_call_once | 有失败、等待、初始化等帧；未构成直接调用目标表示 | calls帧只有it与Otherwise，没有被调用函数 | calls仍无函数目标，多出with the supplied closure作为ARG1；未可靠表达目标交换 |
| call_once | 有执行、等待、panic等帧 | 只有returns/wraps；关键calls谓词未输出 | 同样没有calls；不能据此区分两种目标 |
| symlink | Create与symbolic link | locks/obtains/calls/retaining四帧；calls ARG2为target string | 同四类帧，ARG2变mode value；原共同步骤仍在 |
| mkdir | 无帧 | obtains/locks/calls/retaining四帧；ARG2为mode value | 四类帧仍在，但target string对应论元消失，并非可靠保留错配值 |
| lookup_inode | finds hashed identities等帧，未恢复完整主句 | retrieves ARG1为existing inode；调用在ARGM-MNR文本中 | 主谓词变creates；保留existing inode与调用文本，但不自动指出矛盾 |
| constructor | Constructs inode及stores等帧 | creates、selects、calls；目标在calls ARG2 | creates变retrieves，但inode with attribute operations拆为两个论元；其他帧仍在 |

调用目标字符串仍可能出现在分词输出中，不能把“SRL帧漏掉”写成“原文没有”。符号被拆分，如try_call_once拆成多个词元；从文本回连Rust符号尚未实现。源码中的调用语法也不等于已解析的编译器调用图。

## 研究决策

1. 不把SRL直接用作可共享/独立实现/已有委托分类器。Once例恰好遗漏决定已有委托的目标，可能使文档确认失效。
2. 补写文档是可实施干预，某些参数和步骤在输出中确实更清楚；但本批同时改变内容、长度、措辞及描述层次，不能估计格式规范的独立收益。
3. 共同的locks/obtains框架是可引用候选线索，不是安全抽取证明；必须保留`?`失败路径、guard作用域和操作参数，后续再做类型与行为验证。
4. 下一批不继续为HanLP改写句子：先复查既有`governed-doc-claims-v2.json`与源码绑定工具，复用文档声明到源码证据的接口，不另造一套。区分工具可机械验证的符号/位置与仍需审查的契约；比较同内容的自然语言与显式关系记录时，不把手工填写字段的成绩误计成自动提取能力。

回收Goodall只读反馈后进一步限定：lookup补写还省略了Option失败可能性；altered中的“creates an existing inode”有措辞冲突。因此单字符串控制并非已证明自然、等难度的错误文档分布。主研究员采纳，不回改已执行文本；本结果只支持当前输入下的敏感性及漏提观察。审议确认关键委托目标缺失、参数漏标及论元切分变化，但模型间意见一致不作为独立标注或准确率证据。

已有信息支持推进“受约束文档＋源码交叉核查”的研究，而不支持声称已解决发现、已有新颖专利点或已验证重构收益。完整合格文档是可追加的实验输入条件，本批局部补写不足不否定该方法。

## 检索与来源边界

实际查询`research_lookup.py document-style contract-field SRL --limit 4`：224项匹配，只显示4项，不声称穷尽。进一步读取发现专题、字段控制笔记、真实Rust文档SRL笔记、现有冻结器/推理器/检查器、上一批候选笔记及本批原始帧；部分长输出被截断，未作为完整阅读依据。本轮未重新检索新论文，也没有把既有SRL工件运行说成原论文效果复现。
