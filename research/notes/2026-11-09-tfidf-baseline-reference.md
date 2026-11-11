# Rust 文档候选基线：TF-IDF / cosine 官方依据

2026-11-09，仅阅读官方 API 文档，未安装、运行实验或查看候选结果。已按主线程固定版本重新核对 **1.7 系列官方文档（页面标示1.7.2）**，以下链接均已替换，不再以浮动 stable 为实验依据。主线程告知1.7.2隔离环境安装待完成、`doc-tfidf-discovery-v1.json` 已冻结且尚无输出；这些是交接状态，不是本轮执行核验。后文排序与零向量处理仅为设计建议，不修改冻结协议；1.7.2 `text.py` 原文归档由主线程负责。

## 已核实的定义和默认值

- **TF-IDF**：文档集合大小为 `n`，`df(t)` 是包含词 t 的文档数，不是总出现次数。默认自然词频乘以 `idf(t) = log((1+n)/(1+df(t))) + 1`，再做行 L2 归一化。关闭平滑时为 `log(n/df(t)) + 1`，并非去掉最后的 `+1`；出现在所有文档中的词仍有 IDF=1。`sublinear_tf=True` 才将正词频改为 `1+log(tf)`。默认 `use_idf=True, smooth_idf=True, sublinear_tf=False, norm='l2'`。[TfidfTransformer：定义与 Parameters](https://scikit-learn.org/1.7/modules/generated/sklearn.feature_extraction.text.TfidfTransformer.html)
- **文本入口**：`TfidfVectorizer` 默认 `analyzer='word'`、`lowercase=True`、`token_pattern=r'(?u)\b\w\w+\b'`、`ngram_range=(1,1)`、`stop_words=None`、`min_df=1`（计数）、`max_df=1.0`（比例）、`max_features=None`、`binary=False`、`dtype=float64`；上述 TF-IDF 默认值相同。默认不是 Rust lexer，也没有自带标识符语义拆分。文档提示内置 English stop list 存在已知问题；callable analyzer 接收原始未预处理输入，不能假定默认预处理继续全部生效。[TfidfVectorizer：签名与 Parameters](https://scikit-learn.org/1.7/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html)
- **余弦**：非零向量的分数为 `dot(x,y)/(||x||*||y||)`；L2 归一化后等价于点积。`Y=None` 产生 X 内两两相似度；`dense_output=True` 是默认值，即使输入稀疏也可能输出稠密矩阵。官方示例中零行与非零行的返回分数为0；这属于 API 行为，不把数学上零分母解释成有定义的语义相似性。[cosine_similarity：定义、Parameters、Examples](https://scikit-learn.org/1.7/modules/generated/sklearn.metrics.pairwise.cosine_similarity.html)

## 对 Rust doc 基线的推论，不是官方效果承诺

默认 word/unigram 会丢失词序；单字符类型参数可能被过滤，大小写区别被折叠，`::` 等符号不能作为 Rust 结构保留。文档提取、Markdown/code fence 保留策略、标识符拆分及停用词表必须写入输入协议，不能统称“默认 TF-IDF”。重复样板和同主题词可制造高分；过时/缺失注释、同义改写会削弱或误导信号。高分只表示固定表示下的词汇相似，不是功能重复、正确性、可复用性或维护收益真值；低分亦非功能不同证明。

词表与 IDF 的 fit 集合必须固定：它决定 `n/df`，改变候选文档库也会改变分数。库内候选发现可预先声明在整个冻结库上 fit；若是独立查询/留出评估，应明确训练/索引库与 query 的 transform 边界，不临时将查询加入 fit 后仍称相同协议。不同 corpus 的绝对 cosine 阈值不应直接比较。以上是本实验建议，不宣称官方为本任务提供有效阈值。

## 确定性输出：我们的设计建议，非 scikit-learn 排名保证

1. 固定文档单位 ID、顺序、提取文本和参数；同一索引共享词表/IDF。主线程若自实现公式，应称公式基线，不据本笔记声称与 scikit-learn 数值完全一致。
2. 预先标记零向量（空文档、过滤后无词或 query 无词表内词）；从正相似候选榜排除并单独报告数量/原因，不用任意零分邻居填满 top-k。非零但分数为0的配对也不默认视为候选。没有足够正分时允许少于 k；全库无有效词时记录基线不可计算，不造分数。
3. 排除自配对；无向对用固定 ID 的规范次序去重。按未四舍五入分数降序、再按固定 ID 升序打破精确同分；若采用容差/量化定义“同分”，须事先固定规则。展示舍入不参与排序，不承诺不同数值库/硬件产生完全相同的近同分顺序。
4. 保留并列与截断规则、零向量比例、覆盖分母；不要把 API 返回矩阵顺序当相关性裁决，也不要把候选命中数量叫 precision/recall。标签与后续人工/行为核验独立于本分数。

实际查询方式：直接打开并在以上三个官方页面定位 `token_pattern`、`idf(t)`、`normalized dot`，未使用二手资料；未核查本地依赖版本或主线程实验实现，未改其他文件。
