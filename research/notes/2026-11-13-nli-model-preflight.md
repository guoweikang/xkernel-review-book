# 历史权重身份与替代模型：两条实验路径

## 历史复现缺的不是模型名字，而是对应关系

固定HANS提交`7299f6f657089ce06a0f98e7e81f8d0f5b7741ce`的递归目录树完整返回，未发现常见权重文件后缀；根README及已查论文没有将四份2019预测文件绑定到具体checkpoint摘要或训练run。这里只说已查材料中未找到，不推断权重从未发布。[固定仓库](https://github.com/tommccoy1/hans/tree/7299f6f657089ce06a0f98e7e81f8d0f5b7741ce)

后续`berts_of_a_feather`明确提供100个MNLI微调BERT，预测文件的各列对应`bert_00.zip`等权重，并要求Google BERT提交`88a817c`。Zenodo记录可访问，单个文件约1.2GB。但它属于2020年的多次训练研究，未把某个编号声明为根目录2019预测的模型，不能偷换复现对象。[固定说明](https://github.com/tommccoy1/hans/blob/7299f6f657089ce06a0f98e7e81f8d0f5b7741ce/berts_of_a_feather/README.md)、[权重记录](https://zenodo.org/records/4110593)

因此保留原预测重放结果，历史checkpoint恢复作为独立支线；不无限修复Theano或TensorFlow旧环境来阻塞Rust方法验证。代理只读来源核查得到相同边界，不构成模型实验。

## 可运行候选的版本与接口

选择`cross-encoder/nli-deberta-v3-base`作为**替代判别模型候选**，不是最优模型结论或历史复现。发布者模型卡声明SNLI/MultiNLI训练、Apache-2.0许可，提供句对分类入口。[发布者模型卡](https://huggingface.co/cross-encoder/nli-deberta-v3-base)

本地固定：

- 模型revision：`6c749ce3425cd33b46d187e45b92bbf96ee12ec7`。
- 配置架构：`DebertaV2ForSequenceClassification`；DeBERTa v3权重使用此实现类，不因类名自行改成另一模型。
- 类别：0 contradiction、1 entailment、2 neutral，配置与模型卡一致。
- 发布者safetensors大小：737726552字节；SHA256：`d8148c6d49e0a7925134294c56326c71fe0ab1dc390e37355e00c7efbb488afa`。

API、README、配置、tokenizer配置和HANS树/说明共六份来源存档于`research/evidence/runs/2026-11-13-nli-model-preflight-01/sources.json`。权重元数据可访问不等于权重下载成功，更不等于模型可运行。

这里仍是训练过的神经模型，不能称为“无模型工具”。固定推理流水线可重复，与生成式Agent自由判断不同，但分类结果仍需独立评价，不能作为正确性证明。

## 工件取得与环境

`scripts/fetch_pinned_nli_weights.py`只下载固定版本的safetensors及六个配置/tokenizer文件，拒绝覆盖旧批次，权重完成后核对发布者大小及摘要；不读取pickle权重、不执行仓库远程代码。下载结果以`research/evidence/runs/2026-11-13-nli-weights-01/report.json`是否成功生成及其中状态为准；没有成功报告时不能称已验证。

系统Python为3.13.5，当前没有torch、transformers、sentencepiece或onnxruntime；未取得可用GPU清单，不能按GPU速度估计。磁盘和主存有余量，但后续仍限制CPU线程和时长。依赖只装独立环境，记录实际版本及失败，不升级book既有环境。

## 已冻结但尚未执行的推理实验

`research/protocols/nli-cpu-smoke-v1.json`固定每个HANS子类按pairID字典序取10条，共300条。它是已见数据上的确定性开发子集，不是随机抽样或独立测试。

CPU float32、4线程、batch8、长度128，记录截断；仅输入前提和假设，不输入标签/子类/模板。三分类logit取argmax后再合并neutral/contradiction，不能悄悄改成概率求和阈值。执行两次，保留logits、预测一致性、最大差异、总分和各子类分数；30分钟上限，部分完成不报告全量成绩。

该实验尚未运行。先通过身份、加载与标签检查，再判断是否扩大到全量HANS及Rust契约；不会把HANS好成绩直接当作重复发现、职责归属或安全重构成绩。
