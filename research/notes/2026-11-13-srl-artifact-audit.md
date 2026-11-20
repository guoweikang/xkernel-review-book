# SRL公开工件：AllenNLP与HanLP有界核查

日期：2026-11-13。仅实际阅读官方文档、仓库小型源码/模型卡并做权重URL的HEAD请求；没有安装、下载权重、加载模型、推理或训练。“有运行入口”不等于本机已可运行。

## 1. AllenNLP：英语SRL BERT

- **入口与身份**：官方模型卡为[`structured-prediction-srl-bert.json`](https://github.com/allenai/allennlp-models/blob/b1f372248c17ad12684d344955fbcd98e957e77e/allennlp_models/modelcards/structured-prediction-srl-bert.json)，本轮`git ls-remote … HEAD`取得`b1f372248c17ad12684d344955fbcd98e957e77e`并实际读取固定模型卡。卡中指定`allennlp==2.1.0`、`allennlp-models==2.1.0`；不是承诺任意新版本兼容。官方[README](https://github.com/allenai/allennlp-models/blob/main/README.md)公告已进入maintenance mode，停止升级依赖，不将模型卡历史SOTA措辞当当前结论。
- **任务和输出**：英语PropBank式谓词论元分析。官方[predictor源码](https://github.com/allenai/allennlp-models/blob/b1f372248c17ad12684d344955fbcd98e957e77e/allennlp_models/structured_prediction/predictors/srl.py)给出`predict(sentence)`以及`words`、逐谓词`verb/description/tags`输出；构造器依赖`en_core_web_sm`分词/POS。固定源码105–115行按`VERB`以及英语`AUX`建立谓词实例。因此缺少frame也可能来自谓词识别，不表示句子没有职责或条件。此处固定源码用于说明接口，未声称与2.1.0发行包逐字节一致。
- **权重URL**：[2020-12-15 SRL BERT archive](https://storage.googleapis.com/allennlp-public-models/structured-prediction-srl-bert.2020.12.15.tar.gz)。路径由模型卡`archive_file`及官方[`ModelUsage._storage_location`](https://github.com/allenai/allennlp/blob/main/allennlp/common/model_card.py)对应。本轮HEAD返回HTTP 200、`application/x-gzip`、`Content-Length: 405972254`；没有取得正文或SHA256，不能证明可完整下载、archive完整或加载成功。
- **环境障碍**：实际读取[2.1.0 setup.py](https://github.com/allenai/allennlp/blob/v2.1.0/setup.py)：Python声明`>=3.6.1`，但依赖`torch>=1.6,<1.8`、`torchvision>=0.8.1,<0.9`、`spacy>=2.1,<3.1`、`transformers>=4.1,<4.4`。这些历史约束不能直接搬入当前spaCy 3.8/现代NLI环境；现代Python轮子可得性、旧模型包和依赖解析尚未验证。不能把Python最低版本声明解读为支持Python 3.13。
- **许可分层**：仓库[LICENSE](https://github.com/allenai/allennlp-models/blob/main/LICENSE)为Apache-2.0；模型卡`model_details.license`为`null`，不能据代码许可填成已确认权重许可。卡中明确OntoNotes 5.0训练/评价数据因许可限制不能随其发布。推理入口、权重授权与原基准训练复现条件分别记录，未作法律可用性结论。

## 2. HanLP：区分中文单任务与英语可用的多任务入口

- **身份**：本轮远端HEAD为`959a6966f6e7e26d2e89c4112ca9bafbe32eb743`；实际读取该提交的`setup.py`、`README.md`及`hanlp/pretrained/mtl.py`。该HEAD README为中文；最初浏览的浮动`master`英文README不用于覆盖固定版本的许可原文。
- **单任务入口与输出**：官方[SRL API](https://hanlp.hankcs.com/docs/api/hanlp/pretrained/srl.html)展示`hanlp.load(hanlp.pretrained.srl.CPB3_SRL_ELECTRA_SMALL)`，输入已分词句子，输出按谓词组织的`(text, role, start, end)`跨度，例子含`PRED/ARG0/ARG1`。这是中文CPB3模型，不应直接作为本轮英语契约候选。[官方权重地址](https://file.hankcs.com/hanlp/srl/cpb3_electra_small_crf_has_transform_20220218_135910.zip)仅核对文档声明，未探测或下载。
- **英语候选**：固定[`mtl.py:28`](https://github.com/hankcs/HanLP/blob/959a6966f6e7e26d2e89c4112ca9bafbe32eb743/hanlp/pretrained/mtl.py#L28)列出`UD_ONTONOTES_TOK_POS_LEM_FEA_NER_SRL_DEP_SDP_CON_MMINILMV2L6`，说明为UD 2.10/OntoNotes5训练的多任务模型，语言列表包含English，包含SRL任务。不能把多语种整体列表扩成“每种语言的SRL都有同等覆盖或效果”；本轮未取得英语SRL独立运行输出、任务依赖闭包或配置文件。
- **权重URL**：[mMiniLMv2L6 archive](https://file.hankcs.com/hanlp/mtl/ud_ontonotes_tok_pos_lem_fea_ner_srl_dep_sdp_con_mMiniLMv2L6_no_space_20220731_161526.zip)。本轮HEAD为302至[官方ftp域同路径](https://ftp.hankcs.com/hanlp/mtl/ud_ontonotes_tok_pos_lem_fea_ner_srl_dep_sdp_con_mMiniLMv2L6_no_space_20220731_161526.zip)，随后200、`application/zip`、`Content-Length: 475327511`。未下载正文、哈希或检查是否还需额外encoder/tokenizer资源。
- **环境与入口**：官方[安装文档](https://hanlp.hankcs.com/docs/install.html)及本地Python API提供`hanlp.load`路线；固定[`setup.py`](https://github.com/hankcs/HanLP/blob/959a6966f6e7e26d2e89c4112ca9bafbe32eb743/setup.py)声明Python`>=3.6`、torch`>=1.6.0`、transformers`>=4.1.1`。范围宽不等于已测试任意最新组合。无需为了本任务选择REST服务或上传契约文本；也不应未经检查安装全部TensorFlow等extras。CPU耗时/内存、具体模型兼容版本及仅运行SRL任务所需组件尚未知。
- **明确许可**：固定[README:322–338](https://github.com/hankcs/HanLP/blob/959a6966f6e7e26d2e89c4112ca9bafbe32eb743/README.md#L322)区分代码Apache-2.0、多语种模型默认CC BY-NC-SA 4.0、中文模型仅供研究教学（有另行说明者除外）。本轮mMiniLM候选属于多语种入口；未发现该权重专属例外，不把代码Apache许可扩张到模型。根[LICENSE](https://github.com/hankcs/HanLP/blob/master/LICENSE)实际可读；最初尝试`LICENSE.txt`为404，不是“项目没有许可证”。

## 3. 可回答什么，以及下一步停止边界

两个实现都提供可公开定位的模型/调用入口，但本轮仅确认可得性线索，不称已复现或SOTA。SRL标签可辅助识别谓词及其论元，不等于依存标签、字段更新契约、only-if方向、否定/报告事实性或义务逻辑。`ARG0/ARG1`不能统一硬编码成所有谓词的“执行者/被修改字段”；模态或否定跨度即使出现，也不自动推出句对蕴含。应保留分词、谓词选择、完整frame和未知项，不为20条已见句子补规则获得通过。

**建议有界下一项：优先对HanLP mMiniLMv2L6做本地英语SRL兼容性预检，而不是立刻并行安装两套。** 理由只是避开AllenNLP已明确的旧依赖冲突，不是质量/速度比较。先固定发行版、核对模型许可适用范围、完整资源依赖与预算；满足门槛后才另行下载归档、校验摘要、隔离加载并对已冻结20句保存原始SRL输出。若必须额外大包、兼容修补超出预算或英语SRL入口不能确认，就记录阻塞停止，不换模型追求有利结果。AllenNLP保留为历史英语SRL备选，需独立旧环境和权重许可说明，不污染现有解析/NLI环境。

初审由协作代理完成；其定向访问记录包括以上官方URL、两个仓库的`git ls-remote … HEAD`和两个权重HEAD，HEAD状态尚无原始日志独立归档。主研究线程随后另行下载并核读固定HanLP提交的README、setup.py和mtl.py，确认候选定义、依赖声明与许可分层；三份来源URL、字节数及SHA256存于`research/evidence/runs/2026-11-13-srl-preflight-01/sources.json`，原文在Git忽略的originals目录。其余来源不能视为已完成本地原文归档；权重摘要仍未取得。没有安装、下载大包或模型执行。
