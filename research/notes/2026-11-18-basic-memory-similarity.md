# Basic Memory：语义检索与疑似重复提示的边界

## 核查对象

本机`basic-memory --version`返回1.0.0，安装目录`/root/.local/venvs/basic-memory/lib/python3.13/site-packages/basic_memory`。本次只读程序源码与相关配置字段，没有读取笔记正文／数据库、运行重建索引或修改配置。用户所说“投影重复率”尚未绑定到具体界面；本次找到的是语义检索、相似笔记提示和内容hash去重，不能假定存在一个架构／代码重复率工具。

## 实现链

1. `repository/semantic_chunking.py`按结构组织文本块，常量上限900字符；超长文本的字符窗口回退保留120字符重叠。标题、正文及观察／关系来源参与语义索引，不是Rust AST分析。
2. embedding provider将文本转换为向量。`fastembed_provider.py`调用`unit_normalized`归一化；查询也映射到同一向量空间。
3. `sqlite_vec_index.py:441`将归一化向量的L2距离d转换为`max(0,min(1,1-d*d/2))`，对应余弦相似度裁剪，而非重复字符占比。分数0.8不能解释成80%内容重复。
4. 混合检索结合关键词与向量得分；相似笔记提示则走VECTOR查询，不等同混合检索结果。
5. `mcp/similar_notes.py`用标题＋去frontmatter正文的前900字符作为探针，最多提示3篇邻近笔记；过滤自身、已链接等候选。`mcp/tools/write.py:292`只在created分支调用提示，不自动合并或拒绝保存。

源码明确不展示提示分数：近重复与仅相关笔记可能处于同一分数区间，显示数字会制造不应有的精确感。判断是否合并留给调用方。另有内容hash跳过未改变chunk的重新embedding，这是增量索引优化，不是语义重复判定。

## 本地配置与阈值

只读JSON配置显示：database_backend=sqlite、embedding provider=fastembed、model=jinaai/jina-embeddings-v2-base-zh、dimensions=768、semantic_min_similarity=0.35、reranker_enabled=false。这是文件配置，不保证某个服务进程没有环境或路由覆盖；未执行查询验证实际索引状态。

`similar_notes_min_similarity`中的0.70阈值只适用于源码指定的默认embedding身份，非所有模型通用。当前文件配置不是该默认身份，不能把0.70套用为本机判重阈值；通常回退到服务端检索阈值。SQLite使用sqlite-vec，配置中的Postgres vector index选项不能据此解释为本机使用pgvector。

## 对职责研究的用途

可以复用为候选证据检索：功能描述找相关crate职责、相关规范条款、已有设计与历史记录。不需要为此重写embedding／向量索引基础设施。

但相关性不等于适当归属。“负责DT解释”和“不负责DT解释”可能相近；合理驱动绑定与底层通用解析也可能相关。版本、否定、责任对象、例外及实际代码行为仍要单独处理。该工具可承担检索层，不能直接给出职责越界、应拆crate或逻辑重复的真值。本批未运行本地效果测试，没有新评分或创新结论。

## 官方参考

- [Semantic Search](https://docs.basicmemory.com/concepts/semantic-search)：结构化分块、向量／混合检索及hash增量处理。
- [MCP Tools Reference](https://docs.basicmemory.com/reference/mcp-tools-reference)：1.0工具接口。
- [similar_notes.py](https://github.com/basicmachines-co/basic-memory/blob/main/src/basic_memory/mcp/similar_notes.py)：上游提示机制；main会变化，具体本机行为以本次1.0.0安装源码为准。

独立源码复核由Huygens执行，报告保存在`2026-11-18-basic-memory-audit-01`；本地源码版本与官方在线文档分开，不假定在线main与安装包完全一致。
