# PAM 原生多记录工件准入（2026-11-18）

## 判定

**数据准入通过；本机可执行准入阻断；精确同源源码配对与重构 oracle 未建立。** 固定官方 commit `f8829c3b699356bfdfc3648e11ffecadd3300ca6`，取得完整小型 Netty ARFF，不是自行制造阳性或截取有利结果。本批没有运行 PAM、测试、构建或安装；不替代主线程的 Aroma 分支。

独立证据目录：`research/evidence/runs/2026-11-18-pam-multirecord-admission-01/`。先冻结 `protocol.json`；`verified-sources.json` 列出原路径、URL、原始字节数、SHA256和Git blob身份；`inspection.txt` 留存只读统计；`runtime.txt` 留存环境探测。新增原件总量 **1,068,062 bytes**，未超过5MB。

## 1. 确有原生多记录输入

官方提供训练与全部调用序列，格式为 `fqCaller,fqCalls`。本批取得两个原文件并与固定 tree 的 Git blob逐一核验。两者不能当成独立数据集：58条训练记录全部出现在123条全集中。[官方训练文件](https://github.com/mast-group/api-mining/blob/f8829c3b699356bfdfc3648e11ffecadd3300ca6/datasets/calls/train/netty.arff)、[官方全集文件](https://github.com/mast-group/api-mining/blob/f8829c3b699356bfdfc3648e11ffecadd3300ca6/datasets/calls/all/netty.arff)。

|文件|字节|记录／不同caller|不同调用序列|调用总次数／不同调用名|单调用记录|
|---|---:|---:|---:|---:|---:|
|train/netty.arff|12,618|58／58|53|223／83|10|
|all/netty.arff|30,692|123／123|104|535／156|28|

两文件均无完全重复行，最长序列分别14／24次调用；相同调用序列可属于不同caller，不能解释为重复实现。两文件所有数据行满足当前原入口的两列逗号切分要求。此为读取与计数，不是运行 Weka/PAM 验证。

- train SHA256：`3e802dd6eaafdb2d13b7f49aff77495757b694185cd36e5a508c427ecb333aef`
- all SHA256：`6e9c3974e479ef8f9058417e16fd8cb005bee6e06e864736556440744b803c76`

官方另有166字节、4条数字transaction的 `api-miner/src/test/resources/TOY.txt`，本批保留原件但不选它充当真实API源码任务。它不是 `PAM.main` 直接要求的ARFF格式。官方 `SequenceMiningTest.testDoInference` 内有两组人工transaction及期望覆盖集合的断言，属于推断单元测试，不是Netty模式或共享职责的真实标签；未执行。[原测试](https://github.com/mast-group/api-mining/blob/f8829c3b699356bfdfc3648e11ffecadd3300ca6/api-miner/src/test/java/apimining/pam/main/SequenceMiningTest.java)。

## 2. 来源身份强于“能定位同源实现”的证据

**已建立**：官方版本和ARFF原件身份；caller字符串、调用序列；官方源文件split清单。训练／测试清单含Netty Java文件34／33个。例如第一条caller `com.torrent4j.net.peerwire.AbstractPeerWireMessage.write` 与训练清单 `netty/AbstractPeerWireMessage.java` 有名称对应线索。

**未建立**：每行到精确仓库commit、文件字节、方法参数／源码区间的可靠映射。ARFF没有源码path/hash/span；清单是 `netty/Foo.java` 等归档相对文件名，不是每行的仓库版本映射。仅类名相符不能算配对成功，也不能据此断言不同文件有独立共同实现。官方完整tree中没有可单独下载的Netty Java文件；`datasets/source/client_files.tar.xz` 为 **15,285,592 bytes**，大于本批全部预算，未获取。较小的example源码包属于另一总体，未拿它替换client源码来制造配对。[官方split清单](https://github.com/mast-group/api-mining/blob/f8829c3b699356bfdfc3648e11ffecadd3300ca6/datasets/source/test_train_split/train_files.txt)。

还有直接可见的历史一致性缺口：固定版本 `APICallVisitor.java:116–129` 构造caller时加入参数括号／参数类型；但本批58／123行caller全部不含括号。故不能宣称“这个commit的提取器已经逐行复建这些数据”。历史提取版本／配置未知，本批不追历史或改数据修补。此前归档 `APICallExtractor` 也表明结果输出是caller和calls，不包含文件版本/跨度；其本地输入目录硬编码。[原提取visitor](https://github.com/mast-group/api-mining/blob/f8829c3b699356bfdfc3648e11ffecadd3300ca6/api-miner/src/main/java/apimining/java/APICallVisitor.java)。

**oracle边界**：多个caller／多条序列 ≠ 同源独立实现配对，更不等于应共享。原论文的序列出现／覆盖指标不是重构正确性或收益标签；训练与全集不可直接当held-out两臂。此处未建立新的金标准。

## 3. 实际可执行入口与限制

已归档并打开 `PAM.java`、`PAMCore.java`、根POM及两个模块POM。

- `apimining.pam.main.PAM.main`（56行）解析 `-f/-o/-i/-s/-r/-l/-v`，调用 `mineAPICallSequences`。它生成临时transaction文件、挖掘、再输出带概率的API子序列。
- `generateTransactionDatabase`（117行）寻找 `@data` 后用 `line.split(",")[1]` 读取调用列，分配调用ID；**caller列不进入挖掘模型**。它不是完整通用ARFF解析器；本批两文件的行结构满足该狭窄读取形式，但未执行入口。
- `decodeInterestingSequences`（152行）只输出概率和调用名子序列；没有支持该模式的caller/path列表。即使将来挖掘成功，模式→原记录→源码的证据链仍需另外核对，不是当前输出自带。
- `PAMCore.sortSequences`（374行）按概率、interestingness、字符串次序排序；未把输出榜单解释为重构排序。
- 原默认迭代10,000、结构步数100,000；`maxRunTime=72*60`分钟与旁边“12hrs”注释不一致，应按代码表达式理解，不照抄注释。runtime检查在循环步骤后，不能代替进程硬timeout；默认文件路径也是作者历史绝对路径，未来必须显式传输入输出。[原PAM入口](https://github.com/mast-group/api-mining/blob/f8829c3b699356bfdfc3648e11ffecadd3300ca6/api-miner/src/main/java/apimining/pam/main/PAM.java)、[原核心实现](https://github.com/mast-group/api-mining/blob/f8829c3b699356bfdfc3648e11ffecadd3300ca6/api-miner/src/main/java/apimining/pam/main/PAMCore.java)。

本批未进一步追完全部EM/Inference依赖，不能把“已打开main”写成取得可构建闭包，也不借未执行的代码阅读宣称singleton实际输出行为已完整核实。

## 4. 本机与构建阻断

只读探测结果：`java/javac/mvn` 均不在当前PATH；JAVA_HOME/M2_HOME为空；常见JVM目录及 `/root/.m2/repository` 不存在；有限深度 `.build` 检索未找到PAM JAR。这不是所有其他机器／路径的穷尽结论。

官方固定tree没有JAR条目。POM要求Java8源码／目标、Maven多模块工程及shade插件，mainClass为 `apimining.pam.main.PAM`；不是一个可以拿既有Python venv直接运行的脚本。依赖包括Guava18、commons-io2.4、commons-math3、JCommander1.35、SPMF0.98c、Weka3.6.6、codemining SNAPSHOT模块；另有指向 `mast-group/maven-repo/raw/master` 的依赖仓库，依赖身份不因主仓固定commit就全部冻结。未解析／获取这些依赖，未断言今天可构建或不可构建。[原api-miner POM](https://github.com/mast-group/api-mining/blob/f8829c3b699356bfdfc3648e11ffecadd3300ca6/api-miner/pom.xml)、[原standalone POM](https://github.com/mast-group/api-mining/blob/f8829c3b699356bfdfc3648e11ffecadd3300ca6/api-mining/pom.xml)。

最小后续候选（仅供主线程决定）：若另行解决可信Java/JAR依赖闭包，冻结完整官方58行训练文件，可做非自检索的原生多记录挖掘烟测；不需Java源码重提取，但没有精确预期模式oracle。命令模板是 `java -jar <verified-original-jar> -f <train/netty.arff> -o <new-output> -i <frozen-limit> -s <frozen-limit> -r <frozen-minutes> -v`，另设外层硬timeout。**本批不选限值、不执行，不能称当前已有小型可运行任务。**

即使烟测成功，若下一目标是实际共享局部实现而非正常API使用模式，仍需client源码配对与支持模式的来源核查。无需先造Rust前端或改造新框架。

## 5. 失败保留与停止

浏览器打开固定GitHub页被拒；官方raw/API下载成功，共13个原件（tree＋12文件）。第一次下载记录的Git blob核验器错误使用字面反斜杠零而非NUL，导致全部false；**这是本批记录器错误，不是源码不匹配**。保留 `acquisition-original.jsonl`，正确NUL算法和独立 `git hash-object` 均已验证12文件与固定tree一致；SHA256始终正确。更正留在 `acquisition-corrections.txt`，没有重下／替换原件或隐去失败。

到此停止：有官方小型多记录数据，有明确源码入口；没有本机Java执行闭包、没有逐行源码复建和重构oracle。算法／测试／构建／安装次数均为0，不以原论文摘要、文件存在或审阅意见冒充效果。未改catalog/PROGRESS，主线程据两分支结果决定下一批。
