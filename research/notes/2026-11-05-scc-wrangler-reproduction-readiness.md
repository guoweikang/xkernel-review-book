# SourcererCC 与 Wrangler：原任务复现准备核查

日期：2026-11-05。依据作者官方仓库、固定提交文件和已归档论文；没有执行检测器、安装运行时或下载大型数据集。
当前 HEAD 只作为可定位的检查版本，**没有证明它就是论文发表时使用的版本**。

## 1. SourcererCC / P01

官方仓库：[Mondego/SourcererCC](https://github.com/Mondego/SourcererCC)。
本轮 `git ls-remote` 与 GitHub tree API 指向 `88314f51fdf3cd89103eb2c19fb56464308846c8`。

固定源码依据：

- [README](https://github.com/Mondego/SourcererCC/blob/88314f51fdf3cd89103eb2c19fb56464308846c8/README.md)：当前教程走Java文件级输入；所链接的VM还关联DéjàVu工作，不应直接标为P01的完整复现包。
- [build.xml](https://github.com/Mondego/SourcererCC/blob/88314f51fdf3cd89103eb2c19fb56464308846c8/clone-detector/build.xml)：Ant构建，javac source/target为1.7。它不等于已经确定必须使用JDK7，更不证明当前JDK兼容。
- [运行脚本](https://github.com/Mondego/SourcererCC/blob/88314f51fdf3cd89103eb2c19fb56464308846c8/clone-detector/runnodes.sh)：进程启动参数含每节点6GiB初始/最大堆，阈值原始参数默认8。
  [检测器README](https://github.com/Mondego/SourcererCC/blob/88314f51fdf3cd89103eb2c19fb56464308846c8/clone-detector/README.md)的阶段示例又有不同堆配置；不能直接照抄启动大量节点。
- [分词配置](https://github.com/Mondego/SourcererCC/blob/88314f51fdf3cd89103eb2c19fb56464308846c8/tokenizers/file-level/config.ini)：设置分隔符、注释和扩展名；当前扩展名列表不是Rust。加.rs扩展名不能证明Rust分词和块边界正确。
- [requirements.txt](https://github.com/Mondego/SourcererCC/blob/88314f51fdf3cd89103eb2c19fb56464308846c8/requirements.txt)含依赖和WebApp说明的混合文本，不是应无审查直接pip安装的纯锁文件。
- [LICENSE](https://github.com/Mondego/SourcererCC/blob/88314f51fdf3cd89103eb2c19fb56464308846c8/LICENSE)为GPL文本；本轮只确认入口，未审计依赖许可，不提出合并进内核的授权结论。

### 复现任务分层

1. **原工具冒烟**：在隔离目录固定代码/运行时，使用可人工核验的Java小输入，验证分词、索引、检索、ID→源码范围回映射。
   正负例、最低规模和阈值边界须在执行前确定；只产生输出不算通过，不能把空结果误当成功。
2. **原论文评价复现**：回到P01使用的代码块粒度、token定义、阈值、数据版本和匹配规则，
   复查召回分层、精度抽样和资源指标。已有论文定向阅读见 [P01记录](2026-11-05-candidate-token-baseline.md)。
   当前文件级教程成功不能代替这一步。
3. **Rust适配**：固定源码单位、token规则及未展开宏/cfg视图，尽量复用原检索引擎；
   保留前端替换差异。自行实现多重集重叠应命名为SourcererCC-inspired，除非完整机制及等价测试确已完成。

### 数据及评价器

本轮最初误试 `Mondego/BigCloneEval`，得到404/无法匿名读取；这不是官方评价器失效。
沿作者入口找到 [jeffsvajlenko/BigCloneEval](https://github.com/jeffsvajlenko/BigCloneEval)，HEAD为
`6d393ec8adb1d71493d09881ba520659b6c2c68e`。
[固定ReadMe](https://github.com/jeffsvajlenko/BigCloneEval/blob/6d393ec8adb1d71493d09881ba520659b6c2c68e/ReadMe.md)
给出BigCloneBench、IJaDataset下载入口和注册/导入/评价过程。只下载了ReadMe，未取数据库、VM或验证下载内容。
[BigCloneBench官方说明](https://github.com/clonebench/BigCloneBench)区分其版本；本轮HEAD为
`37f6c7141dac914d7eb13c09a967c6ce1a821f91`，未下载其数据。

当前发布数据与P01所用版本是否一致仍待核对。若只能使用新版数据，应写“原方法在新版基准上的再评价”，
而不是宣称精确复现论文数字。数据子集和按类型召回不能混成Rust功能重叠或可重构性的准确率。

## 2. Wrangler / P11

官方入口由[作者项目文档](https://refactoringtools.github.io/wrangler/doc/overview-summary.html)链接到
[RefactoringTools/wrangler](https://github.com/RefactoringTools/wrangler)。本轮HEAD为
`edb509684808cdec892dce53c1718afba48cb2fc`。

- [INSTALL](https://github.com/RefactoringTools/wrangler/blob/edb509684808cdec892dce53c1718afba48cb2fc/INSTALL)描述Erlang及编辑器集成，构建入口为configure/make。
  [rebar.config](https://github.com/RefactoringTools/wrangler/blob/edb509684808cdec892dce53c1718afba48cb2fc/rebar.config)还包含configure、C和elisp构建hook。不能只看到rebar文件就认定是纯Erlang依赖。
- [refac_inc_sim_code.erl](https://github.com/RefactoringTools/wrangler/blob/edb509684808cdec892dce53c1718afba48cb2fc/src/refac_inc_sim_code.erl)导出
  `inc_sim_code_detection_command/8`，参数涉及最短表达式序列、最少token、频次、变量数、相似度、搜索路径及tab宽度。
  这是已核对的程序入口，不是已验证可无编辑器运行的环境配方。
- [refac_sim_code.erl](https://github.com/RefactoringTools/wrangler/blob/edb509684808cdec892dce53c1718afba48cb2fc/src/refac_sim_code.erl)也已保存；全量/增量入口的正确对照及缓存重置仍需运行前核实。
- [LICENCE](https://github.com/RefactoringTools/wrangler/blob/edb509684808cdec892dce53c1718afba48cb2fc/LICENCE)明确作者文件与第三方文件可能采用不同许可；不能把根许可概括为全仓同一授权。

### 复现任务分层

1. **原工具冒烟**：原生Erlang表达式序列样例，核对克隆类、公共函数/实例替换，保留绑定差异与不可泛化负例。
2. **原论文评价复现**：P11 §6的全量/增量时间、克隆类数量及版本更新条件。
   需要找到论文对应源版本和工业测试套件，当前尚未取得；没有这些不能复制表1的结论。
   源版本缺失应标为数据/历史版本缺口，而不是算法失败或召回为零。
3. **Rust结构参照**：AST指纹只是较弱参照；若没有表达式序列、绑定信息和受限反统一，不能称为Wrangler复现。
   未运行结构参照前，也不能宣称我们超过结构方法。

原任务定义及评价边界沿用 [P11指定正文核对](2026-11-05-structural-semantic-candidates.md)和
[公共抽象文献记录](2026-10-27-abstraction-prior-work.md)。本轮没有新增“100%精度”等结论。

## 3. 本机前置条件及成本边界

`command -v` 未找到java/javac/ant/mvn、erl/erlc/rebar3/python2/emacs；
存在make/gcc/g++/docker命令和Python3.13.5。命令缺失不等于整台机器没有相应镜像或安装，
docker命令存在也不证明daemon、镜像或资源可用；本轮没有查询容器、安装或启动服务。

优先安排SourcererCC的隔离冒烟环境，再固定数据进行原任务评价；Wrangler并行解决历史版本/输入与OTP兼容条件。
资源时间和峰值内存尚未实测，不给“几小时就能全部复现”的承诺。
先限定单节点和小输入，明确JVM参数，记录环境适配补丁；环境修复不能混入算法改进。

## 4. 留痕

上述固定版本文件保存于 `research/evidence/originals/reproduction-2026-11-05/`，local-only，
URL、字节数与哈希登记在证据manifest。论文继续使用既有P01/P11存档。
实际操作为官方页面查询、git ls-remote、tree API、下载并阅读少量文本/源码；未clone完整工具、未执行第三方脚本。
