# 条件提取对词汇替换的敏感性

## 问题与设计

前一轮[作用域消融](2026-11-13-srl-scope-ablation.md)的两个only-if端点表现不同。本轮是已见失败后的开发诊断，不是独立测试、原论文复现或新方法有效性证明。

固定模板 `The ACTOR releases the RESOURCE only if the CHECKER accepts the TOKEN.`，四个二值因素依次为allocator/recycler、buffer/lease、validator/verifier、request/ticket。运行全部16种组合，不挑选有利子集。必要条件不证明释放已经发生，全部参考为unknown；此集合不能衡量保留有用肯定回答的能力。

`scripts/freeze_srl_lexical.py`在推理前保存全部输入、协议、未修改的六臂评价器及SHA-256。复用既有HanLP权重、分层环境、CPU离线推理、安全加载与精确NER buffer兼容检查；两遍推理。这里只测英文构造句，不推广中文文档或Rust项目准确率。

## 结果

16句均保留only/if词元，每句有两个谓词帧。10句的releases帧保留完整条件从句ARGM-ADV，6句没有该附加语；两遍原始输出及六臂结果一致。

|规则|错误肯定|拒答|正确确定回答|
|---|---:|---:|---:|
|flat|16|0|0|
|仅跨帧包含|16|0|0|
|仅修饰语|6|10|0|
|组合|6|10|0|
|任意多帧即拒答|0|16|0|
|全部拒答|0|16|0|

每因素保持其余三个词不变，有8对比较；从前词换成后词，条件附加语数量净变化依次为−2、0、−2、−6。request的8句均保留条件，ticket的8句只有2句保留。这个差异只描述该模板和模型，不说明ticket普遍造成遗漏，也不能解释模型内部因果机制。buffer/lease在这批对照中不改变附加语有无。

**没有提取条件，不等于原文没有条件。** 组合检查无法发现自身输入遗漏；所有失败都保留，没有给ticket等词新增规则。粗略全部拒答虽不犯本批错误，却不能证明比组合方法有工程价值。此前24句成绩不能当作稳定收益外推。

## 验证及运行问题

原始输出检查、四项损坏控制、既有11项规则合成控制、独立重算24组统计通过；评价器和参考摘要与推理前冻结副本一致。因素汇总额外核验16组合完整、每因素8配对，以及直接从原始帧读出的修饰语与评价器标记一致。

首次在推理尚未结束时过早启动检查器，因report.json未生成而报FileNotFoundError，未运行后续评分；等待推理成功退出后重新检查通过。这是编排失误，不是模型失败。首次异常仅保留在会话，未声称有原始日志文件；成功日志归档于补充清单。

## 证据与复现

- 冻结：`research/evidence/runs/2026-11-16-srl-lexical-inputs-01`。
- 原始推理：`research/evidence/runs/2026-11-16-srl-lexical-smoke-01`。
- 六臂结果：`research/evidence/runs/2026-11-16-srl-lexical-ablation-01`。
- 逐项配对：`research/evidence/runs/2026-11-16-srl-lexical-contrasts-01`。
- 工具：`scripts/freeze_srl_lexical.py`、`scripts/run_hanlp_srl_smoke.py`、`scripts/evaluate_srl_scope.py`、`scripts/summarize_srl_lexical.py`；前后两辅助脚本使用明确的固定批次ID，重跑须选择新目录，不覆盖历史。

## 对主线的决策

本批完成后停止扩展词汇诊断。它支持把“提取完整性”当风险来源，不构成创新性或可专利性证明。回到[源码辅助契约](2026-11-12-governed-claims-v2.md)的完整命令与固件职责：前者检验执行条件/回调边界，后者检验规范owner、历史报告与源码现状是否混淆。

下一批须将“完整收集后调用一次”和“逐片段调用”作为不同命题，并把规范归属与实际支持路径分开。分别记录自动提取、证据连接、可回答/未知，不给工具人工补上条件后再称自动成功。复用已知案例只能评价开发敏感性；新的模型运行和工程收益仍待测。

### 工程入口复核

只读代理复核建议先以完整命令和权限/类型角色做行为对照：两者已有可执行证据，固件职责则另设规范证据轨道，不把owner设计优劣混进行为真值。主线程复读以下源码确认入口；代理意见不是独立人工标签。

- `research/evidence/runs/2026-11-12-governed-doc-packets-01/complete-command/source.txt:87`：空/超长前置分支、收集循环与循环后的单次self.write。与`research/evidence/runs/2026-11-12-rust-seeds-01/DEV-STREAM-COMMAND/1-source.rs:446`及已有轨迹配对；行为轨迹仍是模型，不是内核验证。
- `research/evidence/runs/2026-11-12-role-preservation-01/source.rs:145`：原生rustdoc明确修改与保留的角色，函数体对应相反掩码操作。可检验角色提取是否丢失区别，不据此否定局部共享。
- 固件职责继续沿用`research/protocols/governed-doc-claims-v2.json`的规范/报告/源码观察分层；没有上位规范确认时不计算职责归属准确率。

因此下一项先冻结真实原生文档、研究员补全文档和受控错误版本的输入差异，再跑同一固定提取器。补全文档必须标记为研究员构造，提供者确认数仍为零；加入源码事实的收益不得记成纯表示方式收益。
