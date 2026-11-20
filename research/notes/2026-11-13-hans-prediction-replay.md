# 作者预测重放与配对交互方法的复现边界

## 已执行：四份HANS预测评分重放

固定作者仓库提交`7299f6f657089ce06a0f98e7e81f8d0f5b7741ce`，下载README列出的BERT、Decomposable Attention、SPINN、ESIM四份预测。协议`research/protocols/hans-prediction-replay-v1.json`在执行前固定范围、标签映射、重复和独立计分检查。[原始仓库](https://github.com/tommccoy1/hans/tree/7299f6f657089ce06a0f98e7e81f8d0f5b7741ce)

每份包含30000个完整唯一ID。预测原标签为entailment、contradiction及部分neutral；显式把后两者合并为non-entailment，拒绝其他标签，再交原评价器。四份各执行两次，共8次；每次96个分组均与独立计数一致，同条件stdout逐字节相同，归档摘要核对通过。

|仓库预测文件|正确条数|整体accuracy|蕴含组accuracy|不蕴含组accuracy|
|---|---:|---:|---:|---:|
|bert_preds.txt|16439|54.80%|97.47%|12.13%|
|decomp_attn_heur_preds.txt|15082|50.27%|98.38%|2.17%|
|spinn_preds_heur.txt|15154|50.51%|94.84%|6.19%|
|esim_heur_preds.txt|15004|50.01%|98.83%|1.19%|

数值来自本地重算，不是抄写论文表格。总体与各标签分母分别30000和15000；完整子类、模板结果保留于report。这些文件明显偏向蕴含，与上一轮词汇捷径控制形成可检查的对应，但仅凭预测不能断言每个模型内部采用了同一种机制。

这是**公开预测评分重放**：训练0、模型推理0、权重下载0。不把单个公开文件当多随机种子平均，不声称复现所有论文表格，也不是现代模型排名。公开文件上的表现不能替代Rust功能重叠标签。

## ESIM入口审查：交互模型不等于语义角色解析

[ESIM原论文](https://aclanthology.org/P17-1152.pdf)§§3.1–3.3先编码两句，再进行跨句软对齐，将对齐结果与差值/逐元素乘积等组合，经推理组合与池化分类。它是句对条件化交互，不是分别编码后计算余弦；也不显式产出谓词—论元角色。论文的Tree-LSTM变体需与顺序ESIM分开。

原文PDF、作者仓库commit元数据及README已下载，固定commit为`f503a1bdb34a36525ce03b0b0426b246d2a84659`。[固定作者入口](https://github.com/lukecq1231/nli/tree/f503a1bdb34a36525ce03b0b0426b246d2a84659)

README依赖Python 2.7、Theano 0.8.2，存在明显的旧环境复建成本。代理另阅读浮动master的小型下载/训练脚本，观察到SNLI/GloVe输入、旧GPU配置和训练输出路径；这些额外脚本未做固定版本归档，结论仅作为下一次工件核验线索，不称冻结复现配方。已查README及这些入口未给直接checkpoint链接，不能据此断言全仓或其他发布位置没有权重。

尤其要避免混淆：HANS论文§4的ESIM使用AllenNLP实现、MNLI训练；作者ESIM仓库的SNLI入口不是同一实验配置。[HANS原文](https://aclanthology.org/P19-1334.pdf)

## 决策与后续门槛

本批完成评分重放后停止，不为了增加“复现数量”立即重建旧Theano环境。下一项需核实HANS实际实现/训练配置与可用权重，再比较两条路径：历史环境复建，或明确标为替代实现的现代可运行方法。前者服务论文可复现性，后者服务Rust实验可用性，两者证据不能混写。

同时继续筛选显式关系/角色表示：能否保留动作、对象、条件和副作用，以及是否有公开测试和可运行提取器。不能因ESIM在这份文件上差，就排除全部交互模型；也不能因它有对齐机制，就宣称已解决角色交换。

## 工件

```sh
python3 scripts/replay_hans_predictions.py --run-id 新批次ID
```

- 重放：`research/evidence/runs/2026-11-13-hans-prediction-replay-01`，包括原始来源摘要、规范化预测、8次stdout/stderr、全部分组统计及执行器。
- ESIM预审：`research/evidence/runs/2026-11-13-esim-preflight-01/sources.json`；原PDF/README本地存于对应originals目录，Git忽略。
- 预测与数据、评价器绑定同一HANS提交；调用前核对前轮数据及评价器摘要。执行器复用的严格验证函数源码也随run留存。

上述结果已进入book；尚未生成生产重构补丁或独立Rust检测准确率。
