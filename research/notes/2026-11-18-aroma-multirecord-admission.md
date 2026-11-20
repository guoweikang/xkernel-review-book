# Aroma多记录任务：数据来源与运行准入

## 研究问题

单记录自检索及构造AST控制不能证明结构方法在不同源码之间有价值。本批核查作者是否提供可直接用于多记录、非自检索的小型原生任务；不是重新修复既有55／67特征失配，也不是重建全部论文语料。

## 原件与实际检查

固定[作者仓库](https://github.com/facebookresearch/aroma-paper-artifacts/tree/e8d8beeb99255d8929874c156fd65aac74d21508)及既有commit。协议、下载器、原响应、SHA256、CSV检查和首个结果来源都在`research/evidence/runs/2026-11-18-aroma-multirecord-admission-01/`。累计取得约1.05MB材料，无安装、无算法运行。

|原件|本次实测|能支持什么|
|---|---:|---|
|完整Git树|25条，truncated=false|在该固定工件树中只见一份JSON，即example_query.json|
|github_repositories.csv|5339记录|原语料的仓库、commit与定位信息，不是已提取语法树|
|stack_overflow_code_snippets.csv|64记录|完整／部分查询、作者归因和原分类结果|
|biggroum_code_snippets.csv|17记录|15编号主题，其中第7项含a/b/c三个变体，不是论文说15而文件损坏|
|第一条非空结果链接|固定文件下载成功，7892字节|原结果基础片段的源码可回查，不等于重放聚类与推荐|

CSV按UTF-8 BOM兼容方式读取。保留原顺序，首条为数据库事务；取得固定commit下ReaderUserTable.java并保存59–78行。没有挑换为更容易访问的来源，也没有据此给其余结果链接判定可用。

[作者README](https://github.com/facebookresearch/aroma-paper-artifacts/blob/e8d8beeb99255d8929874c156fd65aac74d21508/README.md)明确区分查询素材、原语料重建清单与推荐基础片段链接；并非所有合成推荐结果直接发布。本次树／CSV计数与来源读取支持该区分。公开标签描述作者在原语料上的结果，不应挪用成我们新语料的正确性标签。

## 准入结论

目前不具备“直接运行原生多记录小工件”的条件：现有Python入口可用，但作者语法树只有单个例子；多个Java查询与可回查的一个结果文件不能直接喂给树算法。本环境PATH中java、javac、mvn均未找到，仅说明当前命令环境，不证明机器所有目录不存在工具链。

未来可以另行安装隔离工具链、恢复官方Java转换器并冻结独立语料，但那是新的语料构建／工具复现批次，不能在此宣布已完成或在结果后手造AST。本批按原预算停止此入口，不因数据未直接提供而断言Aroma无效；也不为了获得一次成功而用self-query替代。

## 失败、可复核性与下一动作

最初下载误用了`facebookresearch/aroma`路径，产生五次404；这是研究者URL错误，不是论文材料下线。回读已归档`sources.json`和commit元数据后更正为`aroma-paper-artifacts`，原脚本及失败manifest不覆盖，重试放`corrected/`。首次随后的树检查因文件不存在而失败，未产生任何有效计数。`correction.txt`明确记录。

检索`research_lookup.py Aroma PAM multi-record --limit 4`命中114项、返回4、省略110；回读旧原件README、原入口、既有可行性审计和最新阶段记录。该检索不保证穷尽。新协议在下载与检查前固定，获取源文件只限预定第一条非空链接。所有计数可通过`inspect.py`逻辑复算，但脚本拒绝覆盖既有结果；它不是算法效果评测。

并行核查PAM是否提供更完整的原生多记录数据；如果同样缺少本批可用执行链，则优先处理固定xkernel队列尚未确认的删除事务候选，而不是继续扩Rust前端或围绕两个self构造测试。是否复现成功、数据是否可用、是否值得优先投入是三个不同问题。
