# SourcererCC 原生文件级冒烟

后续更新：[阈值与长度边界已补测](2026-11-05-scc-boundaries-and-goal-gate.md)。以下保留原两轮的证据范围。

日期：2026-11-05。对应 P01、B-SCC。阶段 A 中验证基线能否运行，不替代阶段 C 的正式结果复现。

## 实测结果

原版 tokenizer → init → index → search 已运行，算法 Java 文件未修改。
源码固定为 `88314f51fdf3cd89103eb2c19fb56464308846c8`；第二轮将提取的所有文件逐一与该提交 Git tree 的 blob SHA-1 比较，全部一致。
Git blob 校验验证快照一致性，不等于签名认证或安全审计。

| 构造输入 | token 数及共有量 | 预期与实际 |
| --- | --- | --- |
| ExactA / ExactB | 各302，共有302 | 报告一对 |
| ExactA / Near、ExactB / Near | 各302，共有292 | 报告两对 |
| Unrelated 与三个长输入 | 各302，共有0 | 不报告 |
| Tiny / TinyCopy | 各2，共有2，但低于65 | 不报告 |

六文件的15个无序组合中，6个组合满足最小长度条件。三个预定正例全部报告，另外三个合格组合未报告，9个含短文件的组合未报告。
这些是构造用例验收计数，**不是总体准确率、召回率或真实工程效用估计**。
期望清单先于工具执行写入；独立检查器对原tokenizer输出计算多重集合交集，验证 `10 × shared ≥ 8 × max(total)`，再与原工具输出比较。
这个检查器没有独立验证tokenizer的语言解析正确性，也不是人工标注的功能等价oracle。

第一轮五文件通过，但只有一个短文件，无法排除“没有报告只是因为不相似”的解释。
第二轮增加完全相同的短文件作为负对照，保留第一轮记录而不覆盖。
尚未测试恰好80%/略低于80%、64/65 token边界、复杂注释/字符串、类型重命名、语义等价、跨文件组合或实际工程输入。

## 固定执行入口

在book仓库根目录运行：

```sh
python3 scripts/run_scc_smoke.py --run-id scc-native-new-run
```

需要Linux用户/挂载/PID/网络命名空间、GNU timeout、mount、chroot、setpriv、Python3。
每个run-id只能用一次；失败输出保留在独立目录，不覆盖以前证据。
上游源码和运行时放在忽略目录 `.tools/scc-smoke/`，本次没有修改系统安装。
在新环境须先准备以下固定工件，不能把本机缓存当作无需准备的依赖：

- [官方固定源码归档](https://codeload.github.com/Mondego/SourcererCC/tar.gz/88314f51fdf3cd89103eb2c19fb56464308846c8)：保存 `source.tar.gz`，提取同名顶层目录的 `clone-detector/`、`tokenizers/file-level/`、LICENSE、README.md。
- [固定Git tree](https://api.github.com/repos/Mondego/SourcererCC/git/trees/88314f51fdf3cd89103eb2c19fb56464308846c8?recursive=1)：保存 `source-tree.json`，不得截断。
- [Temurin Java8u504-b01 Linux x64](https://github.com/adoptium/temurin8-binaries/releases/download/jdk8u504-b01/OpenJDK8U-jdk_x64_linux_hotspot_8u504b01.tar.gz)：保存 `jdk.tar.gz`，解压到 `jdk8u504-b01/`。下载后对照官方元数据验证SHA256：`9c70e102f527ac674ac2fe9c7d47b9a04e2d19842ba5ab8e9b33f368bbadfaea`。
- [Ant 1.10.18](https://archive.apache.org/dist/ant/binaries/apache-ant-1.10.18-bin.tar.gz)：保存 `ant.tar.gz`，解压到 `apache-ant-1.10.18/`。本次从dlcdn下载，对照Apache发布的SHA512验证；完整工件SHA256见manifest，未做PGP签名验证。

运行时为Java8、Ant1.10.18、Python3.13.5。原配置最小65、最大500000、分片保留，阈值参数8表示80%。
只改tokenizer扩展名为Java、线程数为1，采用自有单节点启动器替代默认多节点6GiB堆启动器。
Java堆上限512MiB（Ant256MiB），串行GC；每进程地址空间3GiB、CPU120秒，整个启动命令timeout240秒。
这些是环境适配，不用于性能基准比较；没有测量峰值内存或复现论文吞吐量。

## 隔离与实际障碍

Docker daemon不可用；bubblewrap挂载失败。改用独立用户、挂载、PID、网络、IPC、UTS命名空间及chroot，进入后丢弃capabilities。
宿主/usr与工具目录只读，专用work目录可写；不挂载宿主/root、凭据目录或宿主/proc。
这是本机小型可信源码实验的隔离措施，不是经过安全认证的恶意代码沙箱；资源限制也不是cgroup总量限制。

环境探测经历三类失败，未把它们算作算法失败：

1. 新命名空间中挂载proc被拒绝，最终不挂载proc；不能改为暴露宿主proc。
2. 缺少proc导致JDK找不到libjli，显式设置LD_LIBRARY_PATH解决。
3. 默认JVM堆估计过大，地址空间限制下初始化失败；显式限定堆、元空间并采用串行GC后运行成功。

JVM仍输出无法检测主线程栈位置的警告，保留在日志；本次执行成功不代表这套无proc环境适合所有基准。
另一次下载旧Ant归档出现TLS EOF，未关闭证书验证，转为下载官方当前发行版。
环境探测失败只有此处摘要；正式两次管线执行的原始日志完整保留。

## 证据与结论边界

- 仓库目录 `research/evidence/runs/2026-11-05-scc-native-02/`：完整报告 `report.json`、原始输出 `query_1clones_index_WITH_FILTER.txt`、执行日志 `execution.log`。
- 同目录的 `expected.json`、`manifest.json`、`source-integrity.json` 保存输入期望、工件/命令和源码一致性；另外包含fixture、token、文件ID映射、配置和脚本快照。这些原始附件保留在Git材料中，不由book构建器发布。
- 第一轮 `research/evidence/runs/2026-11-05-scc-native-01/report.json` 保留，尚未含短文件重复负对照。

当前只确认：固定新版工具能够在小型Java文件输入上完成token克隆检测并符合预先定义的用例期望。
没有确认：论文对应提交、block级数据/指标复现、Rust适配效果、功能冗余、可安全抽象或性能改善。
下一步先补阈值/长度边界，再对齐P01原任务和BigCloneEval数据口径，不能直接拿本次三个命中当研究效果。

上游行为依据：[固定版本README](https://github.com/Mondego/SourcererCC/blob/88314f51fdf3cd89103eb2c19fb56464308846c8/README.md)、[原启动器](https://github.com/Mondego/SourcererCC/blob/88314f51fdf3cd89103eb2c19fb56464308846c8/clone-detector/runnodes.sh)、[tokenizer](https://github.com/Mondego/SourcererCC/blob/88314f51fdf3cd89103eb2c19fb56464308846c8/tokenizers/file-level/tokenizer.py)。具体调用、输出解释以固定源码和保存的实测产物为准。
