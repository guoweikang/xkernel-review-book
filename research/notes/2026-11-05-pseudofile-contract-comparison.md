# 跨项目伪文件：共同机制与不可抹去的写入契约

后续更新：PC01/PC03已完成[受控方法片段实验](2026-11-05-pseudofile-method-experiment.md)，下文保留实验前的源码预测与边界。

日期：2026-11-05。X-Kernel固定`7e3ac94431a0dbb376d2fc8d85098deeff1bba09`，Starry固定`2e075accf4fb0aefdd1d252ebd9ccf29727d9923`。
本轮为X006/R004的源码契约对照，不是跨项目效果实验；不新增两个“独立样本”。

## 相似到底发生在哪里

两边有SimpleFileOps、闭包适配、Cow/Vec内容以及按offset向调用者缓冲区复制数据的机制。
Starry的`SimpleFile::read_at`在取得内容后做范围检查、截取、限长复制；X-Kernel的`read_generated_bytes`实现对应的局部复制步骤，并已被Generated和Snapshot两种操作复用。
这支持“存在共同局部机制”，不支持“整个伪文件语义相同”，也不证明引入一个跨项目公共依赖值得维护。
这些相似代码是否源自共同历史尚未审计；不把它们宣称为独立重复发明。

## 关键差异矩阵

| 维度 | Starry固定实现 | X-Kernel固定实现 | 审查约束 |
| --- | --- | --- | --- |
| 写入对象 | SimpleFile::write_at读取旧内容，按offset修补后write_all；特定全覆盖输入可直接write_all(buf) | CommandFile::write将本次data交给回调，忽略offset | 不能用同一写算法无条件替换 |
| 写入前读取 | write_at先调用read_all，失败则不执行write_all | CommandFile::write不读取旧内容 | 必须比较错误顺序、副作用及成本来源 |
| 回调上下文 | Write携带字节切片 | Write携带VfsFile和字节切片 | 不能丢失调用者依赖的描述符上下文 |
| read返回Ok(None) | RwFile::read_all调用unwrap | CommandFile::read_all返回InvalidData | 错误与panic策略是契约的一部分 |
| 读取内容时机 | 此SimpleFile::read_at每次调用read_all | Generated每次生成；Snapshot在open保存内容 | 只比较局部copy不能证明生命周期等价 |
| append/resize | SimpleFile实现append和set_len，对旧内容修改后write_all | 本轮CommandFile未承担同样的整内容操作 | 没看到对等接口不等于仓库缺少该能力 |

以上只针对所读直接方法。外层syscall到这些方法的路由、实际feature和权限检查没有完整追踪。
尤其不能把CommandFile::write_iter中的4096字节上限，未经路由核验就宣称为所有直接scalar写入的统一限制：scalar方法本身没有该检查。

源码依据：[Starry file.rs](https://github.com/Starry-OS/StarryOS/blob/2e075accf4fb0aefdd1d252ebd9ccf29727d9923/kernel/src/pseudofs/file.rs)；X-Kernel原文见`research/evidence/runs/2026-11-05-rust-pilot-seeds-01/sources/fs/kvfs/src/simple_file.rs`。

## 调用方证据，不只看接口名字

Starry proc.rs中的oom_score_adj和comm以RwFile处理Read/Write；X-Kernel task_nodes/root.rs同名节点使用CommandFile。
前者Write回调接收的是由外层write_at准备的内容，后者回调接收单次命令，不能因为两段comm回调高度相似就认为组合后的文件行为等价。
X-Kernel的oom_score_adj还调用专用解析器并检查范围；本轮没有追踪两边所有下层setter，不能据此判断另一边缺乏完整校验或存在可利用漏洞。
本轮读到的Starry两个Read分支返回Some；`Ok(None)`的unwrap差异不等于这些生产调用已经会触发panic。

来源：[Starry proc.rs](https://github.com/Starry-OS/StarryOS/blob/2e075accf4fb0aefdd1d252ebd9ccf29727d9923/kernel/src/pseudofs/proc.rs)；X-Kernel调用方固定快照保存于`research/evidence/runs/2026-11-05-pseudofile-caller-01/`。
X-Kernel设计及测试源码此前已归档：写命令不拼接此前内容、缺少读取内容返回错误等断言可见，但本轮未运行它们。

## 可证伪的检查计划

不只记录“语义不同”，将区别固化为`research/protocols/pseudofile-contract-checks-v1.json`：

- PC01：旧内容abcdef，在offset=2写XY，观察回调收到abXYef还是XY。
- PC02：读取回调返回Ok(None)，观察错误返回与panic事件。
- PC03：旧内容生成失败但写回调可接受输入，观察写操作是否被读取失败阻止。
- PC04：固定字节内容，对照边界offset、空缓冲及未写区域，核验共同复制机制；生成调用次数单列。

这些是依据源码作出的**静态预测，未执行**。PC01不是实际proc文件的运行结果，PC02也不是生产可达性判断。
未来执行需先明确直接方法层的适配和测试环境，不以手工改写的模型测试通过冒充原实现通过。
失败时区分提取/适配错误、上下文前提不足和真实行为差异，保留原始结果。

## 目前支持的决定

| 问题 | 当前结论 |
| --- | --- |
| 是否存在具体重叠？ | 局部字节复制、闭包包装有源码依据 |
| 是否直接替换？ | 当前不支持，写入契约存在实质差异 |
| 是否可能抽象？ | 可以研究策略分离，但可行性和收益未验证 |
| 是否值得整改？ | 未确认；不建议为一个短复制片段先引入跨仓公共库 |
| 是否性能更好？ | 未测量；减少读取/分配若改变语义，不能算等价优化 |

研究贡献候选是“发现重叠后保留契约差异并安排能区分方案的核验”，不是宣称这一思想首次出现。
当前只能作为一个部分重叠、需保留差异的案例组，不作为独立人工真值或已确认优化正例。
另一Agent的[反向复核](2026-11-05-pseudofile-counter-review.md)用于检查推断边界，不替代维护者标注。
下一步按上述PC01/PC03做最小原实现行为验证；不继续扩大伪文件阅读范围，避免不断积累静态描述而没有可检验结果。
