# 固件节点职责：固定历史案例与依赖基线盲区

日期：2026-11-11。性质：回顾性开发案例，不是盲测、自动发现成绩或重构收益验证。没有改动内核工作树、运行内核或实施优化。

## 1. 为什么选择这个案例

用户举例：上层直接扫描／解释设备树，可能承担公共抽象应有的职责。本轮实际读取当前内核文档与源码，发现已有相关迁移，不应把该假设写成当前未修缺陷。通过历史日志选择CPU节点解释改动，检验哪些证据能区分解释逻辑和委托。

本轮固定当前HEAD为`1c70f4cc2402c7fc02bfcd6328dc79b478c3662c`，不是之前四包SCC语料的提交；不将两者混为同一评价集。读取Git对象而非工作树，未触碰已有未跟踪文档，未拉取或修改内核分支。

| 快照 | 固定提交 | 用途 |
| --- | --- | --- |
| before | `cb5bfa7ec35b6d79f1b4433e7ff0149a884dd247` | CPU能力改动的父版本 |
| after | `20c6ead060376cf628b9ba3fcbb60fd8ad64e44a` | 实际历史改动 |
| current | `1c70f4cc2402c7fc02bfcd6328dc79b478c3662c` | 本轮现状对照 |

## 2. 职责依据不是事后全部补写

before已有`drivers/firmware/of/docs/firmware-node-direction.md:5`，将结构访问、属性解码、节点状态、地址翻译归于rs_fdtree；控制器特定寄存器角色和中断编码归于驱动；内核注册、IRQ/MMIO映射及DMA分配不归DT库。该文档约束说明不是所有固件相关逻辑都应下沉。

但before这份一般职责声明没有单独证明每个CPU操作都应移动。after新增的`rs-fdtree/docs/design.md`硬件CPU身份章节与提交说明只能用于解释历史决策，不能倒灌为before检测输入，也不能把作者合入决定当最优方案真值。

## 3. 源码证据

- before `drivers/firmware/of/src/lib.rs:134`：`is_cpu_node`直接读取`device_type`；同文件`:143`起的`cpu_node_reg`先分类再调用本地`node_reg`。本地helper读取父节点`#address-cells`并解码`reg`。
- after同文件`:134`：分类转为`CpuNode::from_node(node).is_some()`；`:148`：CPU身份转为`CpuNode::from_node(node)?.hardware_id().ok().flatten()`。
- after新增`drivers/firmware/rs-fdtree/src/cpu.rs`，集中CPU节点分类及身份解释。没有逻辑CPU索引、MMIO映射或控制器接纳逻辑。
- after的`is_enabled_cpu_node`仍在OF，且`node_reg`没有完全删除，仍被syscon路径使用。不能把出现`node_reg`或直接读取属性作为该CPU迁移失败的判断；其他消费者要另查。

当前快照也保留上述CPU委托形式。已归档26份存在文件，before缺少新cpu.rs的事实单列，没有用after文件填补。

## 4. 第一个实际检验：crate依赖是否能区分前后？

用Python标准库解析before/after的OF `Cargo.toml`，比较整个普通`dependencies`表：**完全相同**。两侧均声明rs_fdtree依赖，但CPU解释逻辑的落点发生了变化。

这构成一个具体反例：只看该crate的普通依赖声明，无法区分这个历史变化。不是宣称所有依赖分析都无效；函数级调用目标和实现行为可能能区分。没有构建完整调用图，也没有自动确认职责错位。

收集器还报告六种预先写入脚本的字面量位置。它们是在看过补丁后选取的定位特征，会匹配注释／声明，不是Rust语义解析器、泛化检测算法或召回率实验。

## 5. 不能把这条提交当作纯行为保持重构

新增CpuNode检查身份载荷长度，区分缺失与畸形；提交同时增加中立fwnode能力和测试。它不只是移动同一段代码，还包含接口与严格性变化。因此不能把旧版本自动标为错误、新版本标为完全等价且更好，也不能直接作为纯重构评价的标准答案。

该案例适合开发两项确认检查：实际解释和已有委托的区分；通用DT机制与保留上层策略的区分。行为与收益、全配置测试以及独立人工标签本轮均未验证。

## 6. 固化工具和复跑

```sh
python3 scripts/collect_firmware_boundary_case.py --repo /root/codes/x-kernel --current 1c70f4cc2402c7fc02bfcd6328dc79b478c3662c --output research/evidence/runs/firmware-boundary-new-run
python3 scripts/check_firmware_boundary_case.py --repo /root/codes/x-kernel --run research/evidence/runs/firmware-boundary-new-run
```

运行记录位于`research/evidence/runs/2026-11-11-firmware-boundary-01/`，包含三快照源码／文档／清单、historical.patch、收集器快照、逐文件SHA和report.json。输出目录必须不存在；输入提交必须在本地Git对象库中。

本轮校验包括26份源码摘要、原始补丁与收集器摘要、临时目录重跑报告逐字节一致，以及拒绝覆盖已有目录。此处确定性仅限固定输入与当前环境；不证明职责分类正确。

## 7. 下一实验决策

先完成Reflexion Models定义与映射的可执行小型例子，再把该案例作为映射粒度的开发反例：crate级别不可分辨时，函数／能力级映射能否描述实际差异？同时保留上层策略与必要直连反例。

职责映射若由人提供，必须报告人工成本；若由文档或模型推断，则要独立评价映射错误。不得把从after推导的映射塞给before，再宣布自动发现历史问题。当前案例不进入冻结后的独立测试集，不修改生产代码。
