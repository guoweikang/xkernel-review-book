# 显式调用声明的源码绑定：能定位，不等于已证明委托

## 研究问题与复用边界

[上一批文档SRL](2026-11-16-candidate-document-srl.md)遗漏Once两接口的调用目标。本批检查：如果文档提供显式调用名称，现有源码工具能否把它连到可审阅的位置？这是一项受约束接口试验，不是自然语言理解准确率或重复功能发现评测。

核查发现现有`probe_reviewed_calls.py`使用**syn 2.0.119**探针，不是tree-sitter。直接复用`rust-call-probe`；二进制SHA与`2026-11-06-reviewed-call-syntax-01/report.json`相符，当前探针源码也与该次归档一致。没有新编译器适配、名称解析器或调用图工程。

既有`governed-doc-claims-v2.json`提供了声明类别、来源和未知状态的组织原则，但本批没有声称调用其校验器即可证明语义。本批协议只新增一个窄字段`target_spelling`：**研究员从既有文本手工抄录**，没有自动提取成绩，也没有提供者认可。显式字段是输入契约，不是机器研究结论。

## 冻结设计与执行

- 协议：`research/protocols/call-reference-binding-v1.json`。
- 执行器：`scripts/bind_call_references.py`。
- 输出：`research/evidence/runs/2026-11-16-call-reference-binding-01`。
- 固定输入沿用`candidate-srl-inputs-01`的两份Once函数、complete/altered四条文本，逐一核验原摘要。
- 四条声明跑两遍；11个事前冻结的语法控制；源码摘要篡改、缺少目标字段两类输入拒绝。

匹配仅比较syn输出的调用拼写。保留调用类别、UTF-8字节范围和嵌套深度。方法调用只保留方法名，不含接收者；限定路径不自动去前缀。没有运行cfg、宏展开、类型或控制流分析。

```sh
python3 scripts/bind_call_references.py --output research/evidence/runs/新的批次名
```

输出目录必须不存在。两遍binding完全相同，11项语法控制均符合冻结预期，2项非法输入被拒绝。另用独立读取代码复核所有归档摘要、源片段身份、匹配字节及四项语义状态；未做独立解析实现或独立真值评价。

## 四条真实文本的结果

| 固定函数与文本臂 | 手工登记的目标名 | 自动绑定结果 |
| --- | --- | --- |
| try_call_once / complete | try_call_once_slow | method_expression，片段字节[291,309) |
| try_call_once / altered | call_once | no_visible_spelling |
| call_once / complete | try_call_once | method_expression，片段字节[71,84) |
| call_once / altered | try_call_once_slow | no_visible_spelling |

字节范围相对归档函数片段，不是完整文件行号。命中只表示该拼写出现在被检查的语法类别；未命中只表示当前可见语法中未找到，不能推导间接调用不存在。四条记录的target_resolution、execution、delegation_correctness、safe_exemption始终为unknown；解析边0、自动免审决定0。

这与SRL结果是不同层次的观察，不能写成“准确率从0提升至100%”：一个从自然语言预测结构，另一个消费人工显式字段并查找源码拼写，输入、任务及人工成本不等。

## 对照揭示的边界

| 控制 | 实际输出 | 必须保留的限制 |
| --- | --- | --- |
| 直接self.target调用 | visible_spelling | 不证明目标身份 |
| 注释和字符串中的target() | no_visible_spelling | 排除这两类文本伪命中 |
| 仅在闭包中调用 | nested_spelling_only | 嵌套深度不证明运行延迟或不执行 |
| 宏内参数含调用 | no_visible_spelling，仍有opaque_macro | 无宏展开，不能反驳调用存在 |
| other.target调用 | visible_spelling | 与self.target无法凭现有字段区分 |
| if false分支 | visible_spelling | 不能证明实际执行 |
| 函数指针别名callback() | no_visible_spelling | 间接目标未解析 |
| cfg(any())限定调用 | visible_spelling | 不能证明配置启用 |
| module::target限定调用，查询target | no_visible_spelling | 精确拼写不等于语义名称解析 |
| 中文字符串后调用 | visible_spelling，字节范围正确 | 验证UTF-8位置，不是语义能力 |
| 非法函数片段 | parse_rejected | 解析失败不能当声明被反驳 |

本批没有新增async、内部函数或doc注释专项控制；历史探针已有部分嵌套测试，不把它们算作本批11项。控制是工具边界回归，不是11个真实重构案例。

## 决策与下一证据缺口

可固定下来的能力是**人工显式声明→已标明局限的源码位置**。它可以帮助审阅者追查“已有复用”的证据，但没有形成自动确认器。此次审议特别强调接收者丢失，主研究员采纳，不将matched升级为resolved，不由no-match推导不存在委托。

停止围绕这两例扩充验证器，不进入优化补丁或免审功能。下一批回到文档规范实验：先审计现有governed-claims材料能否用于同内容自然语言/显式记录对照，分开记录人工填写成本、可自动验证字段、未知和错误声明；不能让手工字段携带最终重复标签，也不能把源码生成文档当成独立规范。正式发现收益仍需固定候选预算、任务标签及来源隔离后的验证。

## 检索、审议与留存

### 接续审计：旧材料不能直接充当表示形式对照

本轮接着读取`build_governed_claims_v2.py`和`2026-11-12-governed-claims-v2-01/claims.json`，确认15条记录的组成：8条源码观察、3条规范职责、2条未知、1条文档报告、1条计划能力。构建器为自然语言text附加kind、来源、版本、行号和excerpt；**没有生成同义的主体/动作/条件/否定/模态显式关系记录**。JSON存储不是语义结构化的充分证据。

旧revised/corrupted文本改变了声明内容，不能作为“信息相同、仅表示不同”的两个实验臂。本批4条target_spelling也只是原句子集，遗漏条件、结果和调用者身份，不能补足这个缺口。当前可以复用的是固定源码、文本、来源类型和干预历史，不是已经存在的同信息表示对照集。

机械校验目前可检查来源摘要与excerpt范围，不能由此计为8条源码观察的语义全部已验证。规范职责、报告和计划更不能因为引用了同版文档就升级为实现真值。所查记录没有对应结构化/绑定/审阅工时字段，本次不倒推或编造历史人工成本。

因此先冻结本轮语法接口，不立即补写大批字段。下一设计门槛是逐条明确哪些信息必须等价保留、哪些显式字段可由工具校验，并前瞻记录编写与审阅操作。材料缺少这种配对只说明暂时不能做纯表示归因，不是否定补写合格文档的方法；后续可有控制地构造配对。该审计无新模型或检测效果数字。

查询`research_lookup.py call-syntax governed-claims target_resolution --limit 3`得到56项，仅展示3项。实际检查旧调用探针源码/执行器、gov-claims-v2及其校验器、确认声明打包器、上一批输入和本次输出；没有重新查新论文。Goodall只读审议确认应复用syn并维持语法/执行/语义分层，建议四声明完成后停止扩展，已采纳。Agent意见不是独立人工金标准。

未修改生产源码、历史运行或模型，未提交推送；本批不构成论文创新或专利成熟证据。
