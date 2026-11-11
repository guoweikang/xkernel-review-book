# 函数级确认：语法证据能回答什么，不能回答什么

2026-11-11。沿用[历史案例](2026-11-11-firmware-boundary-case.md)固定的before/after/current快照。研究问题：在crate依赖不变的情况下，函数级调用语法能否揭示解释与委托的变化？不是评价职责分类准确率。

## 输入与方法

协议`research/protocols/firmware-confirmation-v1.json`在运行前固定，但选定函数和信号时已经读过补丁，因此是回顾性开发协议。三文件选择OF的六个函数、CpuNode两个方法、DT后端hardware_cpu_id一个方法。原版本后面三者不存在，缺项单列，不用新增代码补齐。

复用锁定syn解析工具和rust-call-probe：先解析完整源码得到函数签名／body字节区间，再解析函数内调用表达式、方法表达式和不透明宏。结果保留源码／片段SHA、原文件行号和字节区间、闭包等嵌套深度。所有目标均标为unresolved，没有宏展开、cfg求值、类型解析或动态执行证据。

只用名字匹配产生四类检索信号：底层属性读取、CPU视图拼写、本地reg helper拼写及遍历拼写。它们不是能力识别器，不输出违规、正确委托或重复实现判断。

## 实际结果及解释

共提取24个函数版本：before 6、after 9、current 9。它们来自同一个案例，不是24个独立样本。

| 函数／方法 | before信号 | after信号 | 可以支持的解释 |
| --- | --- | --- | --- |
| OF is_cpu_node | 直接property_str | CpuNode::from_node | 语法明确变化；结合人工读取re-export和实现，可追踪分类委托 |
| OF cpu_node_reg | 本地node_reg，没有直接属性读取 | CpuNode::from_node和hardware_id | 只搜直接读取会遗漏旧调用方承担的间接解释；需要跨函数上下文 |
| OF is_enabled_cpu_node | property_str | 相同property_str | 仍有状态策略；存在直接读取不等于必须下沉，也未验证当前策略所有语义 |
| OF node_reg | parent_property_u32与property_u32_cells | 相同调用 | helper仍被其他路径使用，不因CPU迁移消失；不能标为迁移失败 |
| OF enabled_cpu_nodes | all_nodes/filter | 相同调用 | 遍历自身不能证明重复解释或职责错位 |
| OF syscon_poweroff | 属性读取与本地node_reg | 相同调用 | 另一条尚待确认路径，不当作已确认合理或违规 |
| CpuNode from_node/hardware_id | 文件缺失 | 属性读取 | 属性读取出现在DT后端，与公共解释职责相容；不是收益验证 |
| DT后端hardware_cpu_id | 方法缺失 | CpuNode::from_node/hardware_id | 新增委托路径；不能把原先无接口等同功能缺陷 |

前后六个共同OF函数中，只有is_cpu_node和cpu_node_reg函数片段变化；其余四个片段完全一致。该差异由源片段哈希机械比较，不来自相似度阈值。

## 七个构造控制

直接读取、视图调用、注释／字符串中的伪调用、不透明宏、同名但不同限定路径、闭包内读取、无效语法。七项均符合固定预期。

其中`unrelated::CpuNode::from_node(...).hardware_id()`仍因hardware_id名称产生视图拼写信号，说明必须保留未解析状态，不能把信号提升为真实目标。宏中的调用未被展开，不匹配不等于不存在；闭包内读取的嵌套标记也不等于未执行。构造片段只做语法检查，没有类型检查，不是行为测试。

## 职责文档的实际困难

before的`of/docs/design.md:5`描述后端迁移，`:20`之后的Purpose/Responsibilities又列现有OF语义访问与兼容功能。它们可能分别描述目标与过渡现状，而非简单互相矛盾。确认不能把整份文档嵌入后取一个“最相似模块”就宣告违规。

下一步职责证据需区分：规范目标、现状描述、迁移债务、明确例外、配置适用范围；若没有解释清楚，输出待确认。after新增CPU专属说明只能解释历史改动，不能作为before的先验规则。

## 证据与复跑

首次运行：`research/evidence/runs/2026-11-11-firmware-confirmation-01/`。随后加入自动前后比较与解析工具源码归档，以新目录`2026-11-11-firmware-confirmation-02`运行，不覆盖首轮结果。

```sh
CARGO_TARGET_DIR=.build/source-workflow-target cargo +1.95.0 build --offline --locked --manifest-path research/tools/rust-syntax-probe/Cargo.toml --bin rust-syntax-probe
CARGO_TARGET_DIR=.build/rust-call-probe cargo +1.95.0 build --offline --locked --manifest-path research/tools/rust-syntax-probe/Cargo.toml --bin rust-call-probe
python3 scripts/probe_firmware_confirmation.py --output research/evidence/runs/firmware-confirmation-new-run
```

需要固定历史快照目录及已缓存Rust依赖；不自动下载缺失依赖。目录中有protocol、源码片段、逐调用位置、控制输入与结果、缺项、前后比较和SHA报告。没有执行内核、生成优化补丁、计算语义准确率或完成独立确认。
