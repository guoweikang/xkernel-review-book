# RMTool与后续自动映射：一次有界工件核查

日期：2026-11-11。实际浏览作者官方页面、官方链接的项目站及作者机构论文存档；仅下载小型文档/论文，没有安装、运行下载代码、执行实验或改manifest。后续研究只选**InMap**，不扩成综述；不重复主线程的函数调用语法与职责投影实验。

## 1. 原工具入口及版本边界

- [作者RMTool 1.5页](https://www.cs.ubc.ca/~murphy/software/rmtool/index.html)仍可读；[作者jRMTool页](https://www.cs.ubc.ca/~murphy/jRMTool/doc/)区分Java重写的2.0 beta与2003年的Eclipse插件，后者曾验证于Eclipse2.1.1。它们不是已经确认等同1995论文实验的源码快照。
- 独立版输入除高层模型、源码关系、映射外，还需结构描述文件。工具本身不负责抽取任意源码；作者文档列出外部抽取与格式转换路径。旧Java、正则表达式包、Grappa/Graphviz等依赖尚未验证现代兼容性。[官方概览](https://www.cs.ubc.ca/~murphy/jRMTool/doc/)
- [CLI文档](https://www.cs.ubc.ca/~murphy/jRMTool/doc/command-line-interface.htm)给出三个阶段：`jRMTool.map.Ml2map`编译映射，`jRMTool.compute.Compute`生成投影关系及未映射实体/映射信息，`jRMTool.model.MakeRM`比较高层关系，输出文本（可选dot）。这是**已取得的运行接口说明，不是已跑通的命令**。
- [官方示例页](https://www.cs.ubc.ca/~murphy/jRMTool/doc/examples.htm)列出发行包中的`401_pl0`、`netbsd`与`jRMTool`数据，并指定`.des/.lss/.map/.hlm`路径。文档已取得，数据文件本轮未取得；不将示例清单当成已归档数据或原论文全量输入。

### 取得性与许可分开

作者页直接链接的[SourceForge项目](https://sourceforge.net/projects/jrmtool/)列Common Public License 1.0；[source-v1.0.0目录](https://sourceforge.net/projects/jrmtool/files/jrmtool/source-v1.0.0/)可定位源码发布入口。对`https://downloads.sourceforge.net/project/jrmtool/jrmtool/source-v1.0.0/jrmtool_v1.0.0.tar.gz`的一次下载尝试发生TLS EOF，**本轮未取得源码包**，不能推断官方包不存在；包内许可证、依赖和数据内容未核查。

独立版的[下载页面](https://www.cs.ubc.ca/~murphy/jRMTool/doc/download-questions.htm)另有须接受的限制性协议及表单，涉及评价用途及修改/再分发限制。本轮未提交表单、未代用户接受协议，也没有尝试绕过该流程。不能把插件页面的CPL元数据套用到独立版或所有第三方组件；不作法律可用性结论。

## 2. 一条后续研究：InMap的交互式映射建议

实际取得并定向阅读作者机构存档的 *InMap: Automated Interactive Code-to-Architecture Mapping*，Zipani Tom Sinkala、Sebastian Herold，**SAC2021，pp.1439–1442，DOI 10.1145/3412841.3442124**；PDF含机构封面共5页。重点读§3流程、§4数据/反馈设置与工件链接，不声称完整统计复算。[作者接受稿](https://www.diva-portal.org/smash/get/diva2:1552606/FULLTEXT01.pdf)

输入为Java源码与模块名称/自然语言架构描述；用Lucene/TF-IDF给出类到模块建议，人工接受/拒绝后更新查询，直到不能继续决策。§4的JabRef3.7实验使用已有oracle程序化模拟反馈，**不是现场独立人工用户实验**。它自动推荐映射，不自动证明架构规范正确或依赖违规。检索还命中同作者ICSA2021带“Recommendations”的不同题名/DOI；本页不将其六系统摘要结果拼接到已下载的SAC单系统实验。[SAC作者稿§3–4](https://www.diva-portal.org/smash/get/diva2:1552606/FULLTEXT01.pdf)

**工件身份得到作者原文直接支持**：SAC稿§3链接 `https://git.cs.kau.se/zipasink/InMap`。浏览器工具打不开，但curl实际取得[GitLab项目页](https://git.cs.kau.se/zipasink/InMap)及[master README](https://git.cs.kau.se/zipasink/InMap/-/raw/master/README.md)，故不能写成“仓库不可访问”。页面标识`Tom / InMap`、项目683、页面请求指向master；**没有锁定提交SHA**。README称包内有自动评价器及结果，提示查看`algo-eval-results.html`；但没有给出完整构建/运行配方，且正文仍用AutoBot旧名。本轮只取得页面和README，未取得完整源码、数据、oracle、结果文件或许可证；不能据README宣称包已验证完整可跑。其建议关闭浏览器同源限制，本轮没有照做；后续宜先考虑隔离环境/本地服务，不能直接降低日常浏览器安全设置。

## 3. 本轮实际归档（URL—文件—实算摘要）

统一目录：`research/evidence/runs/2026-11-11-reflexion-artifacts-01/`。网页是访问时快照，非固定提交；以本地SHA256标识。下载仅curl GET，PDF以pdftotext定向读取，未执行任何工件代码。

|文件|原始URL|字节数|SHA256|
|---|---|---:|---|
|`jrmtool-overview.html`|https://www.cs.ubc.ca/~murphy/jRMTool/doc/|7861|`673c346e09cb8ab3e65b87e49e9be4b0d787bbad2c8e2c454e4cf94c22159349`|
|`jrmtool-cli.html`|https://www.cs.ubc.ca/~murphy/jRMTool/doc/command-line-interface.htm|6599|`b7cf54102bd96187768cc007dc235548f3317d00310e1226af5f82007b67ab15`|
|`jrmtool-examples.html`|https://www.cs.ubc.ca/~murphy/jRMTool/doc/examples.htm|4801|`766f89f1a81c73fed782068968f13bb027d225690cd5ecd8bd3612ed454726b8`|
|`inmap-sac2021.pdf`|https://www.diva-portal.org/smash/get/diva2:1552606/FULLTEXT01.pdf|539413|`ceeb5ffb465d4382ba830e67f8d158cd9f49db9fe56dec1a7d9738ba38601275`|
|`inmap-repo-page.html`|https://git.cs.kau.se/zipasink/InMap|42697|`f60dbf497e692df4aa5e7de5b90c3c988cd72bccd281111aeff209c1aa9353ee`|
|`inmap-README.md`|https://git.cs.kau.se/zipasink/InMap/-/raw/master/README.md|1198|`3cb1534be3e12742ff72c2cbf091972586a4f148920dbda369f2d5fac0ad5b07`|

## 4. 下一步可复现实验与停止条件

1. **RMTool最小原工具冒烟（尚有工件前置缺口）**：先取得许可适用的包及依赖并固定摘要，选择官方`401_pl0`四个输入文件，按CLI三阶段运行；核对文档列出的对应边类别和源码边追溯、未映射输出。通过只说明该版本与该示例跑通，不是1995性能/系统实验复现。若包仍不可取得，可以做论文定义的独立实现，但必须这样命名，不能称执行原RMTool。
2. **InMap最小作者任务复跑（目前仅就绪入口）**：先固定仓库提交、许可证、JabRef版本/类清单、模块描述与oracle，再核对构建入口和参数；若齐全，可用原oracle回放建议接受/拒绝，保存每轮建议、错误和未映射项。评价对象是映射建议及其反馈过程，不是职责合理性、违规判断或Rust适用性。没有原数据/配置时只能另标适配或重实现。
3. 本轮停止于入口与小文档核查，不继续克隆/安装/下载大数据，不承诺运行时间或复现成功。主线程现有投影实验与这些原工具复现是不同证据层，不能互相替代。

实际查询词：`Gail Murphy RMTool reflexion model tool download source`；`automatic mapping reflexion models architecture mapping source code authors artifact`；`"InMap" "mapping" github`；`"InMap" "Sinkala" "github.com"`；`site:cs.ubc.ca/~murphy rmtool download`；`"InMap" "Sinkala" artifact zenodo`。结果只采用作者官方入口、其直接关联项目与作者接受稿；不依据同名第三方项目或搜索摘要补齐代码取得/执行结论。
