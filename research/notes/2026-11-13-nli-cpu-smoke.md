# 替代NLI模型首次实跑：能运行，不等于契约可靠

## 实验身份

沿用[模型预审](2026-11-13-nli-model-preflight.md)固定的DeBERTa NLI版本和权重摘要。七份模型/tokenizer资产已完整下载，737726552字节权重的SHA256与发布者记录一致。不是此前HANS四份公开预测对应的历史模型。

隔离环境实际使用Python 3.13.5、torch 2.15.0+cpu、transformers 4.57.3；完整依赖版本与安装日志归档。没有修改book原有环境。只用本地safetensors，禁联网、禁远程代码。模型卡来源见[固定版本](https://huggingface.co/cross-encoder/nli-deberta-v3-base/tree/6c749ce3425cd33b46d187e45b92bbf96ee12ec7)。

协议`research/protocols/nli-cpu-smoke-v1.json`在看到结果前规定：HANS每子类按ID字典序取前10条，共300条，CPU float32、4线程、batch8、最大长度128；同一已加载模型执行两遍。这不是随机样本、未见数据或独立加载复现。

## 已测结果

|分组|正确/总数|准确率|
|---|---:|---:|
|全部开发子集|237/300|79.00%|
|entailment|149/150|99.33%|
|non-entailment|88/150|58.67%|

两次预测一致率100%，最大logit差0。实际最大输入长度24，截断0。脚本计时约13.38秒，包含脚本内校验、模型加载与推理，不含安装和下载，不能当纯推理吞吐基准。

部分困难子类：`cn_after_if_clause`、`sn_NP/S`、`sn_past_participle`各0/10；`cn_disjunction`1/10，`sn_NP/Z`2/10，`cn_embedded_under_verb`3/10。每类只有10条且按固定顺序选取，不能由此估计完整子类精度。

这次结果不能直接与此前四份30000条作者预测的总分作同范围排名。模型、训练数据和评价集合不同；以后若比较，应先将历史预测投影到相同300个ID，并仍声明训练来源差异。

## 计分与执行检查

模型仅收到前提/假设。三个logit先argmax，再将neutral和contradiction映射为non-entailment；精确并列时取最小类别索引。没有用负类概率求和来改变判定，没有按结果调整阈值。

运行前只读复核指出完整性和超时留痕缺口，执行前补上每batch三列输出、每轮300个ID全覆盖、资产清单全覆盖及下载URL版本一致性检查。30分钟alarm超限抛异常，外层命令记录日志和退出码；本次退出0。运行日志只有torch弃用警告，没有因此更改模型。

独立标准库检查器重新选取ID，并从保存的600条logits重算类别、分组计数、重复差异及摘要，全部通过。它验证计分实现，不验证模型语义正确性或HANS标签适用于Rust。

## 对目标的意义与下一步

现在已有可实际运行的配对判别模型，能作为词法发现后的**待验证辅助信号**，而不是直接负责重复或重构结论。它在涉及条件/从句的控制上仍出现集中失败；工程契约恰好经常依赖“仅在……时”“完成之后”“失败时不……”等条件，不能跳过这些失败直接移植。

下一批先做同ID的历史预测对照和错误类别核查，确认哪些关系仍失效，再冻结少量Rust契约成对控制。不得挑选本模型擅长的案例，不改变已知困难句来制造改进。职责规范符合性、功能重叠和行为等价仍分别评价；本轮没有生产重构或优化收益结论。

## 复现与工件

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .build/nli-inference-env/bin/python \
  scripts/run_nli_cpu_smoke.py --run-id 新批次ID
python3 scripts/check_nli_cpu_smoke.py --run-id 新批次ID
```

主运行`research/evidence/runs/2026-11-13-nli-cpu-smoke-01`保存协议、固定ID、两遍logits/预测、输入长度、版本清单、全部分组及脚本。安装与执行日志作为运行后补充工件单独登记摘要；原report的生成时清单不回写。权重及配置在Git忽略的originals中，下载清单和发布者摘要在`2026-11-13-nli-weights-01`。
