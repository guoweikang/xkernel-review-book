# 公开SRL运行前检查：配置、依赖与资源闭包

## 要解决的证据缺口

现有窄规则在16条开发控制中覆盖一半字段。下一基线需要真正调用公开SRL，而不是由研究员看句子补字段。本批先验证HanLP的安装、模型配置及原始输出接口，不运行模型，不新增准确率结论。

## 实测环境与修复

固定HanLP 2.1.7 wheel，SHA256为`69dad933187ee4e723e38232125aaae9024283a22feb7179d770162a31be3359`。实际wheel元数据要求`hanlp-common>=0.0.24`，本轮保存的[PyPI common元数据](https://pypi.org/pypi/hanlp-common/json)仅列到0.0.23。不能把忽略依赖后安装成功当兼容成功。

固定[官方源码setup.py](https://github.com/hankcs/HanLP/blob/959a6966f6e7e26d2e89c4112ca9bafbe32eb743/plugins/hanlp_common/setup.py)确实声明0.0.24。按单独修订协议，从该提交取得14个文件、102546字节，逐文件验证Git blob SHA1与SHA256，构建common wheel，再安装已固定的小依赖。没有降低依赖要求或修改第三方源码。这属于**发行包加官方源码依赖的组合环境**，不是纯PyPI发行复现。

首次并行源码获取出现TLS EOF，后续安装因缺setup.py失败；补取缺失文件并验证摘要后重试成功。保留pip失败日志和结构化失败说明；第一次urllib完整堆栈仅留在会话工具记录，不能声称所有失败原日志均已归档。

新环境`.build/srl-preflight-env`通过显式`.pth`复用既有NLI环境中的torch/transformers等包，没有升级或卸载既有包。它是分层预检环境，不是可独立搬走的虚拟环境。记录全部包版本和模块实际路径。最终`pip check`通过；在禁用socket connect的导入探针中，torch、transformers、hanlp、多任务模块及ranking SRL模块五项全部成功。模型加载0、推理0；这些导入检查不证明权重兼容。

## 模型配置：从URL线索到实际字节

编写有下载上限的HTTP Range ZIP读取工具，服务器必须返回精确206和Content-Range，否则拒绝，不回退为整包下载。对475327511字节的模型ZIP只读取68808字节，取得中央目录和config.json，并由zipfile校验读取成员CRC。保存响应范围、原始分段和配置SHA256。

配置实测：

|字段|值|意义|
|---|---|---|
|hanlp_version|2.1.0-beta.37|训练归档与当前2.1.7安装版本不同，需实际加载验证|
|srl.classpath|SpanRankingSemanticRoleLabeling|不是BIO SRL组件|
|srl.dependencies|tok|调用SRL仍需分词任务|
|srl.use_gold_predicates|false|谓词也由系统预测，不能只评价已知谓词的论元|
|encoder.transformer|mMiniLMv2L6-no-space|存在额外编码器/分词资源引用|
|srl.max_seq_len|256|实际长句处理需后续单独核验|

目录还列出model.pt，解压大小539091372字节；仅目录信息，未取得权重正文或验证其完整性。配置与分段摘要不等于整个ZIP摘要。

对照实际安装源码的资源映射并做HEAD请求，tokenizer ZIP返回200、3730182字节，encoder ZIP返回200、228455859字节。三个资源声明合计707513552字节，但这只是已识别下载候选，不是完整运行资源闭包证明：还需确认推理分支到底访问哪些文件、是否触发其他下载。HEAD不能证明正文可完整获取。

## 原始SRL与研究字段之间的界线

[接口审查](2026-11-13-srl-interface-boundaries.md)确认API可选择`srl`，依赖任务仍由组件解析；ranking输出按谓词组织，区间是token索引而非字符范围。必须保留分词、完整frame、空frame和模型身份。ARG0/ARG1不是跨所有谓词通用的actor/object类型，SRL也不直接交付条件蕴含、规范履行或文档真实性。

因此下一次实跑先生成原始SRL档案，不允许人工补齐六字段后算自动成绩。需要另行冻结角色映射与作用域规则，并报告未覆盖字段。此前开发16句仅作接口检查，不能充当新方法独立测试集。

## 检查与下一次执行边界

ZIP工具的本地小型ZIP正控制通过；忽略Range、错误Content-Range、短响应、超单请求预算四项控制均拒绝。真实分段及配置摘要检查通过。这些检查验证下载器行为，不验证模型语义。

下一批在单独资源预算内获取已识别工件并验证完整摘要，再冻结离线加载与原始SRL烟测。当前源码存在`weights_only=True`加载及TypeError后的旧兼容分支；后续不得以不安全反序列化绕过错误，也不得通过自动下载掩盖资源缺失。模型许可仍按上一批代码/权重分层记录，不把本次技术可行性当商业使用许可。

本批停止在预先定义的资源与导入检查边界，不宣称已跑通SRL模型或复现论文效果。

## 证据入口

- 协议：`research/protocols/hanlp-runtime-preflight-v1.json`及`hanlp-preflight-source-amendment-v1.json`。
- 下载探针：`research/evidence/runs/2026-11-13-hanlp-resource-probe-01`。
- 环境、wheel/源码身份、HEAD响应、导入结果：`research/evidence/runs/2026-11-13-hanlp-environment-01`。
- 第三方源码、wheel及模型配置原始字节放在Git忽略的originals目录；可跟踪的manifest保留URL、摘要与范围，不声称正文已上传。

```sh
python3 scripts/probe_hanlp_resources.py --run-id 新批次ID
python3 scripts/check_hanlp_resource_probe.py research/evidence/runs/新批次ID
.build/srl-preflight-env/bin/python scripts/probe_hanlp_imports.py 新输出路径.json
```
