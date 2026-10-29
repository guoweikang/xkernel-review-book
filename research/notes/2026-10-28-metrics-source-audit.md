# 评价指标章节：独立小型来源审计

日期：2026-10-28。审阅对象：[chapters/basics/evaluation.md](../../chapters/basics/evaluation.md)，本次读取时共 29 行。结论：示例算术及 Precision/Recall/FPR 的方向成立，但需要明确评价总体、匹配规则与标签假设；**公式正确不能证明数据标签可信**。

## 实际核查范围

- 完整阅读目标章节；检查仓库及适用祖先目录、chapters/research 下的 AGENTS.md，本次未发现适用文件。
- 实际阅读 Stanford《Introduction to Information Retrieval》（Manning、Raghavan、Schütze，Cambridge UP，2008；在线 HTML 版 2009）第 8 章相关小节的官方站点正文，以及 Google/GitHub 官方文档的相关定义与限制。
- Stanford 部分 URL 直接打开超时；下面标注的教材阅读通过检索工具返回的**官方页面正文**完成，不声称下载或逐页通读教材 PDF。Google/GitHub 页面直接打开成功。没有用二手讲解替代定义依据。
- 未检查数据集、标签记录、真实 PR 或代码案例；未运行实验、统计检验、构建或测试，未分配子任务。只新增本文件，不修改被审章节或其他文件。

## 具体来源、阅读深度与边界

### Stanford IIR §8.3：Evaluation of unranked retrieval sets

URL：<https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-unranked-retrieval-sets-1.html>

已读页面正文，重点核对开头定义、列联表与 Precision/Recall 公式。教材的对象是某查询下返回的文档集合；Precision 的分母是返回项，Recall 的分母是相关项。它不直接规定代码审查如何拆分意见、匹配问题或处理重复。下面对此的建议是审计推论，不是教材原文规则。

### Stanford IIR §8.1：Information retrieval system evaluation

URL：<https://nlp.stanford.edu/IR-book/html/htmledition/information-retrieval-system-evaluation-1.html>

已读正文中的测试集合组成、信息需求与相关性，以及开发/测试集合区分。教材以文档集合、信息需求及相应的相关性判断建立评价背景；这支持先定义任务和判断对象，不能只拿到一批输出就宣称具有完整评价总体。信息检索中的“相关”也不等于程序的语义正确性。

### Stanford IIR §8.5：Assessing relevance

URL：<https://nlp.stanford.edu/IR-book/html/htmledition/assessing-relevance-1.html>

已读正文的评审收集、pooling、评审者差异及一致性讨论。大集合可能只标注部分文档；人工判断会有差异。这支持提醒读者交代标注覆盖与分歧，不能把“人工确认”当无误保证。没有复算教材 kappa 示例，也不将其中经验阈值搬成代码审查的合格线。

### Stanford IIR §8.6.2：User utility

URL：<https://nlp.stanford.edu/IR-book/html/htmledition/user-utility-1.html>

已读正文关于用户效用、回访/购买等间接观测，以及用户研究的讨论。其直接支持的是行为指标、用户效用和相关性有不同含义；它并未研究 AI 评审意见采纳。将此用于 adoption≠correctness 是概念迁移，需与下面的产品文档及独立判断结合。

### Google ML Crash Course：Accuracy, recall, precision, and related metrics

URL：<https://developers.google.com/machine-learning/crash-course/classification/accuracy-precision-recall>

已读 Accuracy、Recall、False positive rate、Precision、NaN 及 Choice of metric and tradeoffs 小节；未运行页面交互练习。定义是：

| 指标 | 分母 | 公式 |
| --- | --- | --- |
| Precision | 全部预测为正的实例 | TP / (TP + FP) |
| Recall / TPR | 全部实际为正的实例 | TP / (TP + FN) |
| FPR | 全部实际为负的实例 | FP / (FP + TN) |
| Accuracy | 全部实例 | (TP + TN) / (TP + FP + FN + TN) |

文档也讨论零分母及错误成本。适用前提是实例单位与正负标签已经确定；文档不会替代码审查产生 TN 或证明标签正确。

### GitHub Docs：Data available in Copilot usage metrics

URL：<https://docs.github.com/en/copilot/reference/copilot-usage-metrics/copilot-usage-metrics#copilot-usage-dashboard-metrics>

补充定位：同页 `Per-user report fields` 中 `code_acceptance_activity_count`。

已读上述表格和字段定义，而非通读全部 API 字段。官方将代码补全接受率定义为用户接受建议的比例；接受活动还可按 apply、insert、Copy 等动作计数。这些是行为遥测，定义没有要求一次独立的正确性判定。**代码补全接受率不是评审评论采纳率**，不能照搬其分母或拿其数值作为后者证据。

### GitHub Docs：Application card: GitHub Copilot Agents，§7 Limitations

URL：<https://docs.github.com/en/copilot/responsible-use/agents#7-limitations>

已核对官方正文节选中的 missed code quality problems、false positives 及行动前复核要求。它支持“输出有漏报/误报风险且需复核”，不提供采纳后错误率，也不能证明用户实际进行了可靠复核。此处只引用产品声明，不推断所有评审工具的误报规模。

## 逐项论断审计与建议修正

### 1. 第 3–10 行：6/8、6/10、2/8

**判断：条件成立时正确，无需改动数值。** 与 IIR §8.3 和 Google 定义一致。但应补明：固定评价范围内的 10 个问题是为讲解而假定完整、正确的参照集；每条意见只声称一个问题，6 条成立意见分别命中 6 个不同参照问题，无重复、复合或待定意见。

建议开头改为以下意思（本次不改原文）：

> 为说明计算，假定已固定代码版本、配置和问题范围，并拥有完整且正确的 10 个问题的参照集。8 条意见均为单一问题意见，按预先约定的匹配规则，6 条分别命中不同问题，2 条不成立。

这里“完整且正确”必须明确是教学假设，不是人工标注天然具备的性质。实际评测的标签可靠性仍需单独交代，见 IIR §8.5。

### 2. 第 10–13 行：错误意见占比与 FPR

**判断：原文区分正确，应保留。** 2/8 是输出意见中的错误占比。在全部输出已作二元判断、单位一致且分母非零时，它等于 1−Precision；不是 FPR。FPR 必须用同一评价总体中的实际负例数 FP+TN 作分母。[Google：False positive rate / Precision](https://developers.google.com/machine-learning/crash-course/classification/accuracy-precision-recall)

建议补一句：

> 若没有预先定义并标注可判正负的候选单位，就不报告 FPR；代码行数、文件数、PR 数不能任意拿来充当意见级 TN 的分母。

这是从公式适用前提得出的审计建议。可以设计 PR 级“是否存在目标问题”的分类任务，但那会产生另一套 PR 级 TP/FP/FN/TN；它不能与问题级命中数混用。不要反向写成“代码审查永远不能计算 FPR”。

### 3. 第 22–23 行：评价单位与未知召回分母

**判断：方向正确，建议把两个计数层次直接说出。** 根据 IIR §8.1/§8.3 的集合与判断对象要求，本文将其迁移到评审时建议分别命名：

- **意见级成立比例**：判定成立的意见数 / 已评价意见总数。
- **问题级覆盖率或召回率**：至少被一条意见命中的不同参照问题数 / 参照问题总数。

二者可以并列报告，但一般不能默认共用同一个 TP。重复意见若逐条判真，可以增加第一项的计数，却不能重复增加第二项的命中问题数；重复本身也不必然是“事实错误”。复合意见需先拆分或预先定义部分正确规则。原教学例的一对一假设使两个分子恰好都是 6，这不应被推广为默认协议。

建议将“不能只凭日常评论直接计算召回率”细化为：

> 只有日常评论或不完备的已知问题集时，不能直接报告针对全部真实问题的召回率。若计算的是已标注参照集内的命中比例，应明确这一范围，并说明未标注问题与未知项如何处理。

不能未经论证就把这个比例叫总体召回率的下界：漏标可能与系统是否容易发现相关。IIR §8.5 的 pooling 说明评审覆盖需要处理，**不保证代码审查的候选池完整**。

### 4. 第 24 行：adoption≠correctness

**判断：应保留，但消除术语歧义并明确这是不同测量构念。** 建议写为：

> 意见采纳率描述被采取行动的比例，不等同于意见正确性，也不能替代 Precision 或 Recall。需说明“采纳”是点击应用、按意见修改、合入还是后续保留，并给出相同单位的分母及观察窗口。

理由分三层：IIR §8.6.2 区分用户效用与间接行为观测；GitHub usage metrics 给出实际行为计数定义；GitHub §7 提醒输出仍可能出错。**由此作出的审计推论**是：接受事件本身不带独立正确性判定，也不提供未发现问题的数量，因此不能直接换算 Precision/Recall。

这里的“≠”表示不能定义为同一指标，**不是证明两者毫无相关性**。本次没有核查正确意见未被采纳或错误意见被采纳的发生频率。建议将原文“准确性”改成“意见正确性”，避免与分类 Accuracy 混淆；adoption（工具使用）与 acceptance（建议接受）也应区分。

### 5. 第 17–18 行：成本与信任

**判断：不同错误有不同代价这一原则有来源支持；具体心理/行为效果本次未充分核实。** Google 的指标选择小节支持根据错误成本选择指标；IIR §8.6.2 支持将时间等用户效用另行评价。但“误报降低信任、导致真问题被忽略”是需要专门人因研究的经验论断，不应声称本次教材核查已经证实。

建议将其标为“可能的使用风险”，或后续补专门一手证据；本轮不扩展调研，也不补造影响大小。

### 6. 第 28–29 行：真值、分歧与独立评测

**判断：保留谨慎表述。** IIR §8.5 支持人工判断存在差异；§8.1 明确开发调参与测试报告应区分。但本次未审计受控构造/历史修复各自的具体偏差，更没有检查实际标签或模型训练数据污染。

建议增加一句：

> 指标只反映在当前参照标签和计数协议下的表现；公式与算术检查通过，不等于标签完整、判定无误或结果可以推广。

另可简短说明分母为零应报告未定义/不适用及处理规则，不能悄悄填成 0% 或 100%；待定标签不应默认为负例。这是协议建议，不表示本书已有相应数据。

## 实际查询与访问记录

实际使用的检索字符串如下。第一批 `site.` 是原样记录的非标准写法，之后使用 `site:` 定向检索；不能把第一批视作严格域名限制。

```text
site.nlp.stanford.edu/IR-book evaluation unranked retrieval precision recall accuracy true negative
site.nlp.stanford.edu/IR-book evaluation unit information need relevance user utility
site.docs.github.com copilot acceptance rate suggestions accepted metrics code quality
site.developers.google.com machine learning false positive rate FP TN
site:nlp.stanford.edu/IR-book "Evaluation of unranked retrieval sets"
site:nlp.stanford.edu/IR-book "Assessing relevance"
site:docs.github.com "acceptance rate" "quality"
site:docs.github.com "code review" "false positives"
site:nlp.stanford.edu/IR-book/html/htmledition/information-retrieval-system-evaluation-1.html
site:nlp.stanford.edu/IR-book/html/htmledition/user-utility-1.html
```

最终采用的具体章节 URL 均列于来源节。直接打开失败后，以检索工具返回的同一官方页面正文继续阅读；没有把失败访问算作阅读成功。尝试打开的 [A note on terminology](https://nlp.stanford.edu/IR-book/html/htmledition/a-note-on-terminology-1.html) 实际讨论聚类，已排除，未作为评价单位依据。

另尝试访问 [Choosing a document unit](https://nlp.stanford.edu/IR-book/html/htmledition/choosing-a-document-unit-1.html)，返回超时，未纳入已读来源。评价单位的审计推论以已读的 §8.1/§8.3 为依据。

本次是定义、适用前提和教学措辞的来源审计；不是数据集审计、完整文献综述或性能验证。未核实任何系统的真实 Precision、Recall、FPR、采纳率或正确率。
