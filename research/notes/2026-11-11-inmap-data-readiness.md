# InMap 2020候选：JabRef数据路径、版本与许可

2026-11-11。固定作者GitLab项目683提交 **`cae17d87f8c17d8108d21abd41e0520b6ca65d7c`**。仅请求目录树与小型README、LICENSE、构建版本文件；没有下载大包、全部源码、索引或二进制，没有运行脚本/构建，不接受协议。未读取旧配置oracle或核算单配置预算，留给主线程。

## 1. 实际路径：旧树是sources/3.7，不是顶层src/archive

以下来自固定SHA的GitLab tree API，而非依据当前master或论文反推：

|路径|实际返回与可支持结论|
|---|---|
|`test-systems/Jabref/`|包含`.VSCodeCounter`、`architectures`、`index`、`sources`及`config-jabref.json`；完整单页目录中没有`src`或`archive`|
|`test-systems/Jabref/sources/`|包含`3.7`目录及`readme.txt`|
|`test-systems/Jabref/sources/3.7/`|确有源码项目结构：`src`、`buildres`、`gradle`、`lib`、`licenses`等，以及`LICENSE.md`、`README.md`、`build.gradle`、`gradlew`等文件条目；不是只有下载说明|
|`test-systems/Jabref/sources/3.7/src/main/java/`|确有`net`与`osx`目录；进一步读取`net/sf/jabref`，看见cli、gui、logic、model、preferences等子目录和`Globals.java`等blob条目，支持实际源码树存在|
|`test-systems/Jabref/src/`与`test-systems/Jabref/archive/`|分别定向请求返回HTTP404；结合父目录清单，只能判定这两个**固定路径**不存在，不是数据集整体不可取得，也不证明全树没有任何归档/二进制|
|`test-systems/Jabref/architectures/`|含`JabRef-3.7-0001`、`JabRef-3.7-0002`子目录、架构docx/html及结果xlsx条目；仅取得清单，没有下载或审计这些内容，不能据名称认定为已验证oracle|

主入口：[固定旧Jabref树](https://git.cs.kau.se/zipasink/InMap/-/tree/cae17d87f8c17d8108d21abd41e0520b6ca65d7c/test-systems/Jabref)。此前2022头的`src/archive/architecture`布局不能套到本提交；本轮证实的源码入口为 **`test-systems/Jabref/sources/3.7/src/main/java/`**（注意Jabref大小写）。所有目录均为定向非递归树，本轮没有统计全量Java文件数或验证所有文件可下载。

## 2. 数据版本：目录标签3.7与文件声明存在差异

- 实际下载的[`sources/3.7/build.gradle:38–39`](https://git.cs.kau.se/zipasink/InMap/-/blob/cae17d87f8c17d8108d21abd41e0520b6ca65d7c/test-systems/Jabref/sources/3.7/build.gradle#L38)声明 **`version = "3.8-dev"`**、`project.ext.threeDotVersion = "3.7.0.1"`。
- [`sources/3.7/README.md:1、10`](https://git.cs.kau.se/zipasink/InMap/-/blob/cae17d87f8c17d8108d21abd41e0520b6ca65d7c/test-systems/Jabref/sources/3.7/README.md#L1)标题为JabRef Development Version，并明确描述开发版本。
- [`sources/readme.txt`](https://git.cs.kau.se/zipasink/InMap/-/blob/cae17d87f8c17d8108d21abd41e0520b6ca65d7c/test-systems/Jabref/sources/readme.txt)列出给两个包添加`@SuppressWarnings`的操作提示。它只证明存在此说明，不证明这些修改已经实施；本轮未比对具体源码。

**因此不能把目录名直接写成“原封不动的JabRef正式3.7发行版”。** 可以固定并使用作者工件中的这一源码快照，但其与上游release/tag、论文准确输入及预处理/修订状态的一致性尚未验证。版本声明差异不独自证明论文实验错误，亦不等于已找到完整上游commit身份。本轮不联网追查上游历史，以免扩展范围。

## 3. 许可入口：JabRef数据本体有明确MIT文本

实际取得[`sources/3.7/LICENSE.md`](https://git.cs.kau.se/zipasink/InMap/-/blob/cae17d87f8c17d8108d21abd41e0520b6ca65d7c/test-systems/Jabref/sources/3.7/LICENSE.md)：MIT License，版权2003–2016 JabRef Authors，包含保留版权/许可通知条件和免责声明。README:105–108另说明自3.6起采用MIT并指向该文件。这是**所归档JabRef源码项目的明确许可证据**，不应继续概括该数据本体“许可未找到”。

`licenses/`目录清单还列AppleJavaExtensions、JGoodies、ANTLR、PDFBox等第三方许可文件；本轮只取得清单，没有逐个读取。JabRef LICENSE不自动覆盖InMap自身实现、外围`architectures`文档、实验oracle/结果或所有第三方内容；不作整体再分发或商业使用法律结论。

## 4. 留痕、就绪程度与停止边界

独立证据目录为`research/evidence/runs/2026-11-11-inmap-data-readiness-01/`。`download-provenance.json`逐项记录固定ref的实际URL、成功文件字节数/实算SHA256、分页信息；两次404记录为请求失败，没有以错误页冒充数据。

小文件包括`test-systems__Jabref__sources__readme.txt`、`jabref-3.7-README.md`、`jabref-3.7-LICENSE.md`、`jabref-3.7-build.gradle`；目录API响应以路径编码命名，另有`tree-licenses.json`、`tree-src__main__java__net__sf__jabref.json`。所有内容均从作者固定提交读取，没有执行其中gradle任务或下载gradlew/jar。

可交付判断：**作者旧数据源码入口存在且有JabRef许可文本，已能明确下一步取数路径；完整原任务执行仍未就绪。** 后续需保留此固定数据身份，在不混用2022布局的前提下由主线程对齐配置、类集合和oracle；若要宣称论文版本一致，还需解释上述3.7/3.8-dev差异。目录存在、MIT文件取得与原论文数值可复现是不同结论。本轮没有运行、数据完整性或标签正确性结果，未改其他笔记或manifest。

## 5. 同日补充：完整Java子树与oracle路径集合差集

按主线程追加请求，仅补取同一固定SHA下`test-systems/Jabref/sources/3.7/src/main/java/`的递归tree API，**19页、1813个目录/文件条目，最后一页13项且无下一页**。范围内以`.java`结尾的blob为843个；没有下载这些源码文件。原始19页保存为同目录`java-tree-page-1.json`至`java-tree-page-19.json`，URL/hash及分页证据已追加`download-provenance.json`。

读取主线程已保存的`research/evidence/runs/2026-11-11-inmap-config-audit-02/config-original.txt`，仅取ProgramMapping的类名集合（文件实算SHA256：`bac8ac53dc28ae6bc41029c1747e9932aded21b3e179d0b14da549815c720b44`），得到843唯一名称。对每个Java路径去除上述根前缀与`.java`后缀，再把`/`替换为`.`，得到843唯一**路径推导名称**。交集为840；双方各有3项差集，不能因总数相等声称完全对齐。

**仅在oracle、不在路径推导集合中：**

- `net.sf.jabref.logic.importer.EntryBasedFetcher`
- `net.sf.jabref.logic.importer.IdFetcher`
- `net.sf.jabref.logic.importer.WebFetcher`

**仅在Java路径集合、不在oracle中（相对上述Java根）：**

- `net/sf/jabref/gui/plaintextimport/BasicAction.java`
- `net/sf/jabref/gui/plaintextimport/PopupListener.java`
- `osx/macadapter/MacAdapter.java`

完整路径清单为`java-source-paths.json`，集合结果及输入摘要为`source-oracle-path-diff.json`。这是离线路径集合计算，不是InMap或Java执行；未应用作者预处理/排除规则，未读取package声明、内部类或非`.java`模板，因此“oracle-only”只表示没有匹配的Java文件路径，**不是已证明类不存在**。本轮没有解释三个差异的来源，也未把它们擅自删掉以拟合论文842类；843文件、843oracle名称、840交集与论文类数是不同口径，仍须主线程对齐。证据和笔记写入已完成。
