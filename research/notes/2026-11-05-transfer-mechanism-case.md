# X007：文件传输的多函数共同机制

后续更新：[TM01受控实验](2026-11-05-transfer-tm01-experiment.md)已验证短写路径差异；下文保留执行前的观察与计划。

日期：2026-11-05。新增一个机制级阅读案例，不是多个独立函数对，也不是已确认优化机会。
Starry固定`2e075accf4fb0aefdd1d252ebd9ccf29727d9923`；X-Kernel固定`7e3ac94431a0dbb376d2fc8d85098deeff1bba09`。
这是对先前偏重函数对样本的补充；未测量文本相似度，不能称为“低文本相似正例”。

## 为什么值得选

文件传输不是一个copy循环就能描述：入口参数检查、偏移来源、读取、写入、短写后的计数、位置提交和等待策略共同决定行为。
只对函数做一对一匹配，可能看不到这些职责的分布；只看多个同名syscall，又可能把调用同一公共引擎误判成重复实现。
本例用于检验发现系统能否输出一组有职责关系的对象，并指出已有复用和待核验差异。

## 已读到的组成关系

Starry `kernel/src/syscall/fs/io.rs`：

```text
sys_sendfile / sys_copy_file_range / sys_splice
    → do_send
        → SendFile::has_data / read / write
            → Direct或Offset分支的底层接口
```

X-Kernel `fs/kvfs/src/transfer.rs`（只列选定分支）：

```text
transfer_files（普通文件分支）
    → resolve_pair_positions → pump + file_pair_step → positions.commit
copy_file_range
    → resolve_pair_positions → verify_copy_file_range
    → pump + 原生copy_chunk_from或file_pair_step → 按结果commit
pump_file_to_pipe / pump_pipe_to_file
    → pump + 各自pipe适配
```

两边都有已有公共层，不应建议“把三个syscall复制循环抽出来”却忽略Starry已调用do_send。
X-Kernel的pipe-to-pipe分支直接splice_to，不能将所有路径笼统说成一定经过pump；原生copy分支也不是buffered fallback。
上述关系是人工从固定源码读取的调用关系，含闭包内调用，不是编译器生成或完整运行时调用图。

## 具体共同职责与差异

| 职责 | Starry | X-Kernel | 对候选的影响 |
| --- | --- | --- | --- |
| 分块传输 | do_send维护缓冲、remaining及计数 | pump维护缓冲和结算，step适配提供已确认量 | 有共同职责，未证明接口可互换 |
| 偏移推进 | SendFile::Offset的read/write分别读取并写回用户offset | 普通文件step使用局部位置，由边界发布 | 需比较失败后的可见状态，不能只比最终返回值 |
| 短写 | do_send在bytes_written < bytes_read时先break，再到计数更新之外 | file_pair_step按written推进，Step携带confirmed，pump累加后停止 | 这是值得运行核验的路径差异，不是合并依据 |
| 进展后错误 | do_send显式处理进展后的WouldBlock读取，写入使用?传播 | pump在total>0后遇到step错误返回已完成前缀 | 错误策略未对齐，不能直接提公共循环替换 |
| pipe等待 | do_send在已写入后先检查has_data | pipe适配将total与nonblocking结合 | readiness/阻塞前提需单独核查 |

短写路径是固定源码可见的风险线索：若首次读8、写接受3，Starry当前循环在total_written累加前退出；X-Kernel对应step/pump结构会把confirmed交给结算层。
**尚未执行该输入**，未确认真实后端是否产生该短写、前后位置和系统调用影响；不能直接升级为生产数据损坏或安全漏洞结论。
此研究不以“发现了bug”替代重复/抽象评价，暂不修改任何项目源码。

## 固定核验义务

机器可读记录为`research/protocols/transfer-mechanism-v1.json`，包括两组成员、已读调用边、已有复用和以下检查：

- TM01：读取8、接受3，记录返回量、两端位置、剩余尾部；不能只断言函数返回。
- TM02：首块完整成功、第二块写失败，记录副作用与返回的完成量/错误是否对应。
- TM03：同一打开描述符/不同描述符与显式/管理位置，核查锁顺序、位置共享及检查顺序。

三个检查均not_run。首轮优先TM01，若适配无法保留真实位置语义，则只报告能够验证的层次，不伪造全路径结果。
本例的研究价值是把“可能重复”细化成职责组和验证义务；不是新颖性证明，也不预设需要合并实现。

## 样本和证据边界

X007只计一个机制组，不把成员做笛卡尔积制造许多机会；与此前文件系统案例存在领域关联，后续划分应记录。
四个X-Kernel种子、X005/X006和本例是探索记录，不是七个已确认机会或独立测试样本，12–20个试点目标尚未完成。
后续还需要真正经过测量的低词法相似案例及更多领域，不能以本例替代这些缺口。

Starry源码由固定[官方文件](https://github.com/Starry-OS/StarryOS/blob/2e075accf4fb0aefdd1d252ebd9ccf29727d9923/kernel/src/syscall/fs/io.rs)取得，保存于`research/evidence/runs/2026-11-05-starry-transfer-01/`并校验Git blob。
X-Kernel原文件、SHA256及四个锚点保存于`research/evidence/runs/2026-11-05-xkernel-transfer-01/`，捕获协议为`research/protocols/transfer-context-v1.json`。
本轮未执行内核构建、扫描器、并发测试或性能实验。
