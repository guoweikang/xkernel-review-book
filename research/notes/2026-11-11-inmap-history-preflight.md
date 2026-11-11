# InMap历史版本与授权声明：有界核查

2026-11-11。仅匿名读取作者GitLab项目683的元数据、固定提交可达历史、各历史根目录和README；没有下载大仓、编译、执行、接受协议或调整浏览器安全策略。未涉及主线程的Lucene独立评分实验。

## 1. 2021论文时期是否有可固定版本

请求[固定提交的commits API](https://git.cs.kau.se/api/v4/projects/683/repository/commits?ref_name=6921e580c9dc009731010fe671942f19938fe236&per_page=50&page=1)，实际返回**15条可达提交**（含固定头，之前14条），响应`X-Next-Page`为空。此结论限该提交的可达历史，不覆盖其他分支、删除历史或作者未公开版本。

|可固定提交|API记录的提交日期与标题|可用解释|
|---|---|---|
|`6921e580c9dc009731010fe671942f19938fe236`|2022-06-08，`Test systems updated`|现有核查版本，晚于2021论文|
|`cae17d87f8c17d8108d21abd41e0520b6ca65d7c`|2020-12-24，`Update README.md`|可达历史中最新的2021年之前快照，亦为固定头父提交；适合下一步核查论文同期工件，但不是已确认论文实验版本|
|`aa13d9a50c01ae216397026a8980dc2bff531118`|2020-12-24，`Updated with results for 3 more test systems`|表明扩充实验材料的历史节点；标题不能证明其对应某张论文结果表|
|`76ef842ba7d9bc383b8870fd146c78ebc34f412a`|2020-10-12，`cleaned version`|更早代码/材料快照，尚未比对算法差异|
|`c7ee37ab3668257c94d6789aff326bbdcbf4e96b`|2020-03-03，`Initial commit`|根目录只有README；不要把它当完整实现起点|

**没有日期落在2021年的提交**；2020年底快照存在，不能说“无论文时期版本可用”，也不能由时间邻近直接说“找到论文用的精确版本”。[tags API](https://git.cs.kau.se/api/v4/projects/683/repository/tags?per_page=100)返回空数组，本轮未找到用于绑定论文的release tag。SAC与ICSA2021论文的精确代码/数据绑定仍待作者说明或版本内更直接证据。

## 2. LICENSE及明确授权说明的实际结果

- [项目API附license参数](https://git.cs.kau.se/api/v4/projects/683?license=true)实际返回`visibility="public"`、`description=""`、`license_url=null`、`license=null`。这是GitLab当前元数据未识别许可，不是法律上“必然无许可”的结论；该元数据不是历史时点快照。
- 对上述**15个提交分别读取完整根目录**（每次per_page=100，均无后续分页），均未发现根级LICENSE、LICENCE、COPYING或NOTICE文件。没有递归扫描全部数据与第三方库，不声称整个历史全树没有许可证或源码头部声明。
- 根目录树中的README blob ID共有**5种**，本轮逐种取得代表版本全文：`c7ee37ab…`、`cb643638…`、`fa438366…`、`50e8533a…`、`cae17d87…`。这些README均未给出明确的软件许可证、修改/再分发授权条款或指向许可证的链接。
- 历史README称测试系统为open-source Java systems，并称提供配置及自动评价器；这不是InMap实现的明确授权，更不能代替各测试系统及依赖的许可证。最新历史README称replication package，仍不足以自动确定授权范围。README的CORS提示未执行。

### 补核：文件级明确许可不能被根目录缺失掩盖

主线程提示后，本轮实际回读已归档固定`6921e580…`源码文件头（位于`research/evidence/runs/2026-11-11-inmap-scoring-audit-01/`，URL/hash沿用该目录provenance）：

- `IRAnalysis.java:1–13`：明确写2019年Zipani Tom Sinkala版权及Apache License 2.0授权声明。这是作者文件级明确许可，不是“全部实现许可未知”。
- `IndexFiles.java:1–16`：明确为ASF贡献许可格式的Apache License 2.0文件头，并引用随附NOTICE；本轮未核验该NOTICE的配套内容，不能将其误记为与IRAnalysis相同的作者版权头。
- `PreProcessing.java:1`直接开始package，所读文件头未见许可声明；没有据此断言该文件法律上没有任何适用许可，也没有自动把相邻文件的声明传播给它。

因此准确结论为：**公开作者工件及论文前快照可取得；2022固定版本至少两份已核对源码有明确Apache-2.0文件级声明；项目整体、其他文件、数据及各历史版本的许可覆盖尚未完整确认。** 当前文件头也不能直接证明2020候选快照同样含该声明，历史文件内容仍需定向比对。根级LICENSE缺失或GitLab的`license=null`均不能推翻已见文件头。未向作者发送请求，不作整体授权法律结论。

## 3. 实际归档与精确追溯

独立目录：`research/evidence/runs/2026-11-11-inmap-history-preflight-01/`。保存23个成功响应文件及一份`download-provenance.json`；后者逐项列实际URL、字节数、实算SHA256，API分页信息在适用条目中保留。

- `project-license.json`、`commits-page1.json`、`tags.json`：项目许可元数据、可达提交记录和空tag列表。
- `root-<完整提交SHA>.json`共15份：API形如`https://git.cs.kau.se/api/v4/projects/683/repository/tree?ref=<SHA>&per_page=100`，仅根目录。
- `README-<完整提交SHA>.md`共5份：API形如`https://git.cs.kau.se/api/v4/projects/683/repository/files/README.md/raw?ref=<SHA>`，覆盖已见全部README blob变体。
- 下一步优先参考的[论文前快照树](https://git.cs.kau.se/zipasink/InMap/-/tree/cae17d87f8c17d8108d21abd41e0520b6ca65d7c)与[README](https://git.cs.kau.se/zipasink/InMap/-/blob/cae17d87f8c17d8108d21abd41e0520b6ca65d7c/README.md)均已通过上述固定版本API取得对应信息。本轮未下载该版本全部源码、jar或数据。

## 4. 下一步及停止边界

可把`cae17d87f8c17d8108d21abd41e0520b6ca65d7c`列为**论文前候选复现版本**，后续仅对比该版本与已核查2022头的构建入口、评分设置、目标数据/配置；在作者或版本内证据明确前，保持“候选”而非“论文精确版本”。如需使用/修改或再分发工件，补查实际涉及文件的许可，必要时向作者确认项目授权及论文提交身份；这不是虚构运行实验必须逐步批准，而是当前证据缺口。

本轮停止在历史与许可入口核查：没有实际运行结果，不评价哪个版本能编译，也不据README或提交标题修订论文评分结论。未修改此前笔记、manifest、计划或其他实验产物。
