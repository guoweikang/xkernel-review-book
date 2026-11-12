# InMap调用图恢复入口：限定检查结果

2026-11-11。仅检查指定2022 archive递归目录及指定2020 xam文件；未执行作者工具、下载大包、转换图或修改主线程脚本。结论：**这两个指定入口仍未提供可直接恢复`static-cdg.txt`方法调用/方法关键词输入的证据。** 不据此声称全仓或作者其他工件中不存在该图。

## 1. 2022 archive：有模型资料，没有列出的调用图或Java二进制包

固定提交`6921e580c9dc009731010fe671942f19938fe236`的[`test-systems/Jabref/archive`](https://git.cs.kau.se/zipasink/InMap/-/tree/6921e580c9dc009731010fe671942f19938fe236/test-systems/Jabref/archive)递归tree实际返回**16项，单页，无下一页**，其中2个目录、14个blob。

- 含`JabRef-3.7-0001`、`JabRef-3.7-0002`；文档/模型条目包括PDF、docx、xls/xlsx、README、generic文本、xam、diagram.png、architecture.html及readme.txt。
- 完整路径清单中未见`static-cdg`、`.jar`、`.class`、可执行程序或压缩包条目。PDF、Office文件和PNG当然可能是二进制编码文件，不能把这项结果概括为“目录没有任何二进制文件”；准确说法是**未发现名称可识别的Java运行二进制或调用图入口**。
- 本轮只取tree，不读取这些模型/Office文件内容；不能排除文档内描述其他工件链接，也不能假定其中包含可消费的方法图。跨版本目录内容不会被直接当2020输入。

## 2. 2020源码根的jabref.xam：模块模型，不是方法调用记录

固定提交`cae17d87f8c17d8108d21abd41e0520b6ca65d7c`的[`test-systems/Jabref/sources/3.7/jabref.xam`](https://git.cs.kau.se/zipasink/InMap/-/blob/cae17d87f8c17d8108d21abd41e0520b6ca65d7c/test-systems/Jabref/sources/3.7/jabref.xam)按2MiB上限取得，实际**7145字节，读至EOF，完整保存**，不是partial。本轮静态解析XML结构（非执行下载代码）：

|元素|数量与字段|可解释范围|
|---|---|---|
|`component`|6个；id/name|model、gui、CLI、pref、globals、logic高层节点|
|`connector`|13个；source/target|全部端点都对应上述component ID；是模块级连接，不是方法端点|
|`map`（父元素原拼写`maping`）|45个；handle/target|源码文件或包路径映射至component；不能把45映射规则当45类或45调用|
|`email`|1个；url|模型附带字段，不是代码/图输入|

全文元素及属性没有方法签名、caller/callee方法记录、调用位置或调用次数；连接端点都在六个高层组件中。**不能从模块connector推导实际类/方法调用，更不能以这些connector填充缺失的静态调用图。** 本轮未用JITTAC验证connector的具体规范语义，也未比较该xam与architectures目录另一个xam是否相同；文件同名不构成内容一致证据。

## 3. 实际归档与下一步边界

独立目录：`research/evidence/runs/2026-11-11-inmap-graph-recovery-01/`。

|文件|大小|SHA256|
|---|---:|---|
|`archive-tree-page-1.json`|2943|`cc871d13772bfad4e6f482f0d8331287283eec0c2a6f161787ca9b3af32091d7`|
|`2020-jabref.xam`|7145|`f19c0e800470b24b162cd00e4d0cb7ea578a70781cf8b173f80f5386f443e734`|

`download-provenance.json`保存两项完整GitLab API URL、固定ref、字节数、实算SHA256，以及tree分页/xam读取上限与完整性。哈希是本地内容标识，不是签名校验。

主线程拟做的“显式缺方法反馈”完整循环只能作为声明缺失输入的对照/降级变体；本轮没有获得能把它升级为原方法完整复现的图工件。若后续以固定源码重建图，需另记提取器、数据版本、转换规则、覆盖集合与方法关键词差异；2022图即使日后找到，也不得不经对齐直接投入2020任务。本次到此停止，文件写入完成。
