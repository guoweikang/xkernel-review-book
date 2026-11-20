# CodeSearchNet：文档基准来源与复用边界

## 实际阅读范围

2026-11-17直接浏览作者论文[1909.09436v3](https://arxiv.org/html/1909.09436v3)的§2、§3/3.1、§4.3及表1–4，并打开[PDF](https://arxiv.org/pdf/1909.09436v3)交叉定位；版本为2020-06-08修订。另读[官方README](https://github.com/github/CodeSearchNet#data)的Data、Evaluation、Schema & Format、Human Relevance Judgements及Licenses。不是模型/数据运行：未下载语料、未训练、未复算指标、未检查逐仓划分实现；README未固定提交。实际检索方式是直接打开上述官方URL，再定位`Filtering`、`Limitations`、`Dataset Statistics`、`Evaluation`和`Schema & Format`，没有扩展第三方搜索。

## 原任务与划分

论文任务是自然语言查询检索完整函数，不是函数对共享机制判定。§2列Go、Java、JavaScript、PHP、Python、Ruby，没有Rust；训练配对来自函数文档，比例80/10/10。§4.3表3的MRR任务用文档查找对应代码，另配999个干扰片段；§3.1的Challenge采用真实查询与人工相关性判断、NDCG，不能混作同一个标签任务。作者指出未标注结果可能仍相关。详见[论文§2–4.3](https://arxiv.org/html/1909.09436v3)。

README明确同一repository只进入一个split；它不是“任意语义家族或跨仓谱系均隔离”的承诺。Schema提供repo/path/func_name/url等定位字段；不能把其中`sha`未经核对当源码字节摘要。官方提供语言数据下载入口和人工判断CSV入口，本轮只确认链接存在，未验证大文件可取得性。项目代码/文档MIT与数据中各项目许可证需区分。[README Data、Schema、Evaluation、Licenses](https://github.com/github/CodeSearchNet#data)

## 文档与泄漏注意事项

**作者明确说明：**§2文档裁为首段，并过滤短函数、测试/构造等类别及近重复；文档可能陈旧，同作者代码/文档词汇高度重合，文档查询不是实际查询。§3还观察到方向颠倒结果。因此不能把天然docstring当“完整合规契约”，或将该语料直接作为保留重复实现的基准。[论文§2 Filtering/Limitations、§3 Directionality](https://arxiv.org/html/1909.09436v3)

**本项目的输入风险推断，不是作者公布的泄漏率：**官方README示例中`code`和`original_string`仍包含目标docstring，而`code_tokens`示例已去掉它；直接把前两字段送入“代码独立臂”可能暴露答案。需要按实际字段审计，不能假定所有code文本均已清注释。函数名词汇重合是潜在捷径，但不自动等同违规泄漏。[README Schema示例](https://github.com/github/CodeSearchNet#schema--format)

## 准入建议：复用原则，不移植真值

- **可复用：**repository分组、来源可追溯、去重意识，以及“文档代理任务”和“独立查询相关性评价”分轨。若以后运行作者任务，应保留作者split并核查实际文件，而非自行随机拆函数。
- **不直接复用：**检索相关性标签不能充当Rust共享机制、安全抽取或维护收益真值；也没有现成的合规/退化文档配对标签。本轮不建议为当前Rust基准下载整套语料。
- **我们的前瞻要求：**原件、派生实现、同一家族及全部文档干预版本在分割前归为同组；“同repo不跨split”只是必要控制之一，不保证跨仓克隆隔离。开发阶段可拟合词表/选阈值，测试文档与结果不得回流调参；若有传导式拟合需另列。先定义可观察的完整性范围，再称doc-complete；天然首段与研究员补写均非提供者确认。
- **仍未知：**本轮未核验作者实际各split的重复残留、完整谱系、当代预训练模型是否见过该公开语料或数据逐文件许可。机械split检查只能证明登记分组未交叉，不能证明语义独立、文档正确或独立人工标签成立。
