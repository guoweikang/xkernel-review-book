# InMap固定版本执行前检查

2026-11-11。本轮仅匿名读取作者论文所链GitLab仓库，保存API响应和小型源码/配置；没有clone全仓、安装、编译、执行下载代码、接受限制性协议或降低浏览器安全设置。结论：**已从“工件链接”推进到“固定提交及实际入口可审计”；尚不能称最小原方法已可直接运行，更未复现论文结果。**

## 1. 实际固定的身份与目录树

`git ls-remote https://git.cs.kau.se/zipasink/InMap.git HEAD refs/heads/master`实际返回两者均为 **`6921e580c9dc009731010fe671942f19938fe236`**。匿名[项目683 API](https://git.cs.kau.se/api/v4/projects/683)确认公开项目`zipasink/InMap`，默认分支master；[固定commit API](https://git.cs.kau.se/api/v4/projects/683/repository/commits/6921e580c9dc009731010fe671942f19938fe236)记录2022-06-08提交、标题`Test systems updated`。这是本轮取得的仓库快照，不是已确认的2021论文实验版本。

证据统一保存于 `research/evidence/runs/2026-11-11-inmap-preflight-01/`：

- `project.json`、`commit.json`：身份与提交原始API响应。
- `tree-root.json`：根目录9项，含`src/lib/test-systems/eval-results`及`.classpath/.project/MANIFEST.MF/README.md`；没有根级Maven/Gradle/Ant构建文件或LICENSE。
- `tree-src.json`：src递归树60项，分页已结束，含`recommender`实现、`s4rdm3x`模型和Snowball代码；`tree-lib.json`：lib第一层10项，含Lucene8.6.2和ASM6.2.1 jar条目。
- `tree-test-systems.json`：六个系统目录；`tree-jabref.json`：Jabref下architecture、archive、index、src及配置文件。
- `tree-1.json`只是最初全仓递归请求的**前100项**，不是完整树。该次脚本把HTTP头转成普通字典后未正确获取分页头，随后改用大小写不敏感的响应头并按子目录定向核查；不声称已下载全仓递归目录，更不声称所有数据齐备。
- `download-provenance.json`逐文件保存实际请求URL、字节数及实算SHA256。源码内容通过固定SHA的`/repository/files/<编码路径>/raw?ref=<SHA>`取得；根目录与src等定向树响应亦固定同一SHA。

## 2. 构建和执行入口：已见的具体障碍

以下行号对应固定提交；本地归档源码把路径中的`/`替换为`__`。

|已读源码/配置|静态事实与执行影响|
|---|---|
|[`.classpath`](https://git.cs.kau.se/zipasink/InMap/-/blob/6921e580c9dc009731010fe671942f19938fe236/.classpath)，`MANIFEST.MF:1–3`|Eclipse项目以src为源码目录、bin为输出；classpath含作者机器的`C:/Users/zipasink/...`绝对路径，Lucene为8.6.2。Manifest却写Lucene8.4.1，主类`recommender.Evaluator`。不能照抄manifest当已验证打包配方；JRE容器没有锁具体JDK版本。jar条目存在不等于本轮下载/校验或编译成功|
|[`src/recommender/Evaluator.java:25`](https://git.cs.kau.se/zipasink/InMap/-/blob/6921e580c9dc009731010fe671942f19938fe236/src/recommender/Evaluator.java#L25)|硬编码`test-systems/jabref/...`、`jittac/...`等小写路径，而固定树为`Jabref`、`Jittac`等；大小写敏感环境需明确路径适配。这是源码可见不一致，不是本轮实际运行报错|
|`Evaluator.java:292`、`:304`|主入口没有解析CLI参数；实际启用Jittac，Jabref调用位于注释中。直接执行默认入口不是SAC2021 JabRef实验|
|`Evaluator.java:313`、`:347`、`:375`|从Program读取多维参数范围，嵌套循环调用AutoMap；不是天然一次最小运行。需冻结单配置并记录入口调整，不能在未知预算下直接运行默认扫描|
|[`test-systems/Jabref/config-jabref.json:7`](https://git.cs.kau.se/zipasink/InMap/-/blob/6921e580c9dc009731010fe671942f19938fe236/test-systems/Jabref/config-jabref.json#L7)，`:298`|包含JabRef3.7源码路径、六个模块名、架构描述和映射条目；当前配置PS=20、MNBF=30、MDBF=2，不是此前SAC稿表2的PS=50、MNBF=33–35、MDBF=1。文件虽叫json，实际是自定义语法，不能默认交给标准JSON解析器；`Evaluator.java:41`起逐行解析它|
|[`src/recommender/AutoMap.java:117`](https://git.cs.kau.se/zipasink/InMap/-/blob/6921e580c9dc009731010fe671942f19938fe236/src/recommender/AutoMap.java#L117)，`:318`、`:326`|构造IRAnalysis与DependencyAnalysis，并有文本/依赖分数计算路径；不能仅凭类名或旧README确认当前运行模式等同SAC稿纯IR配置。本轮没有读全这两项分析实现，也未验证oracle完整性及所有分数/反馈条件|

本轮取得的8份小文件：`README.md`、`.classpath`、`.project`、`MANIFEST.MF`、`src__recommender__Evaluator.java`、`src__recommender__Program.java`、`src__recommender__AutoMap.java`、`test-systems__Jabref__config-jabref.json`。已证明有源码和部分实际数据配置，**未取得全部目标源码/jar、完整oracle及结果集合**；只见目录不能确认数据版本或内容完整。

## 3. 许可证与安全边界

根目录完整清单未见LICENSE，README未给许可证说明；已读入口文件未提供可据以判断全项目授权的声明。未遍历全部lib和数据许可证，故结论为**本轮未确认项目及数据适用许可**，不是断言全仓没有许可或禁止运行。公开可读、第三方jar存在及Snowball代码不自动提供全项目授权。

README仍建议用允许CORS的浏览器查看作者结果；本轮未执行该建议。最小计算实验应优先核对原始输出文件，无需关闭浏览器同源保护；若展示结果，另设计隔离本地服务。没有接受任何协议、使用凭据或启动服务。

## 4. 能否运行最小原方法：有条件可准备，当前尚未就绪

下一步限定为单个JabRef原任务冒烟，而非Rust适配或全参数扫描：

1. 先明确项目/数据许可，并取得固定提交所需源码与依赖；核对JabRef3.7具体文件清单、模块映射/描述及其与论文输入的一致性。当前master晚于论文且提交修改测试系统，不能自动当作原实验快照。
2. 在独立副本记录最小环境适配：依赖改相对路径、统一jar版本、修正大小写路径、显式选择JabRef，固定一个参数组合。这些属于执行适配，不能混入方法改进；JDK版本和全部依赖兼容性需经后续编译验证。
3. 运行前核对当前IR/依赖权重与反馈判据、原数据分母，再保存逐轮建议、接受/拒绝和未映射集合；禁止把读取现有结果HTML当成重新执行。跑通一次仅为固定版本冒烟；配置/数据未与论文对齐时，不称原数字复现。

本轮停止于静态preflight。**没有给出保证可运行的shell命令，没有编译/运行结果，也没有新论文指标。** 与主线程的函数调用证据和职责投影实验分开登记；原稿与先前工件笔记未改动。
