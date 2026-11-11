# R008：真实host入口核查与阶段收束

固定版本：`7e3ac94431a0dbb376d2fc8d85098deeff1bba09`。本轮只核查源码和配置，未编译完整xkmake、运行镜像处理或执行微基准。

## 构建入口的限定

Makefile的XKMAKE命令指定host target，清空RUSTFLAGS和CARGO_ENCODED_RUSTFLAGS，通过`cargo run --manifest-path xtask/Cargo.toml -p xkmake --`启动工具，没有请求release或显式profile。
`.cargo/config.toml`的xkmake别名也没有请求release。配置允许引入生成配置和个人配置；本轮没有解析它们、环境中的profile覆盖或某次真实执行日志。
因此可以确认的是“已读入口未请求release”，不是所有用户的最终构建参数已确定。

`xtask/Cargo.toml`是独立的xtask workspace，只对`profile.dev.package.sha2`显式设置opt-level=3，不能据此把xkmake自身也认作O3。
此前生成代码实验固定O3、panic=abort、关闭debug assertions，属于受控对照，不能冒充上述入口的真实产物。
这不推翻动态参数代码生成观察，但限制了向工程影响的外推。

## 调用路径与次数

`xtask/xkmake/src/build.rs:463`在待发布镜像处理过程中调用`image_metadata::finalize`。
`image_metadata.rs:135`开始的finalize读取ELF，调用两次note_layout，再调用两次finalize_note_header，随后散列加载段并写回文件。

| 调用 | 每次成功finalize中的次数 | 对齐操作 |
| --- | ---: | --- |
| note_layout | 2 | owner_end按4对齐（:241） |
| finalize_note_header | 2 | descriptor_size按4对齐（:366） |

这条静态成功路径中，对齐辅助函数执行四次，错误路径可能提前返回；不是每次make、每个进程或整个构建必然只执行四次。
对齐不在该函数的段散列循环里。文件读写、解析和散列同处路径，但未测量，不能断言它们必然主导耗时，也不能断言四次对齐开销一定可忽略。
这是host镜像收尾，不是已证明的内核运行热路径；动态包装不能代替此处的常量调用。

## 为什么不继续微基准

目前没有取得这三处反复同步修复、实现漂移或显著维护成本的证据。未取得不等于不存在，本轮没有穷尽历史审计。
标准方法可能更易读，但仍是待评价偏好；将短私有函数改短，不自动形成值得继续投入的研究收益。
额外指令也不能自动否决host工具中的小规模算术。

因此不继续构建完整xkmake或追加O0微基准来追逐一个未提出成本预算的结论。
收束依据是净收益问题尚不具体、追加微实验决策价值低，不是“core更慢已证明”。
真实调用上下文的最终机器码、耗时及可读性比较仍记为未验证，不是通过或失败。

## 阶段状态及重启条件

- 共同算术机制：存在，有源码证据。
- memaddr无条件直接替换：错误契约不符，不推荐。
- core同类型适配：非零二次幂域有推导及局部测试支持，保留boot校验及错误映射。
- 生成代码：受控包装存在差异及动态除法风险，不等于生产性能退化。
- 工程净收益：未知，暂不批量整改，不生成强制lint规则。
- 研究用途：保留为“可替换性与值得替换必须分开”的开发对照；不标绝对负例，不算自动发现成功。

仅在出现具体重复维护事件、维护者明确的可读性目标及成本预算，或实际调用路径可接受性证据时重启。
不再增加对齐值、架构或包装函数。停止实验不意味着工具应隐藏该重叠；建议应标为待权衡，而不是应合并。

## 证据与下一项

本轮四份固定文件由`research/protocols/alignment-host-context-v1.json`捕获至`research/evidence/runs/2026-11-05-alignment-host-context-01/`。
完整image_metadata源码见`research/evidence/runs/2026-11-05-alignment-seed-01/`；前序实验见[生成代码筛查](2026-11-05-alignment-codegen-screen.md)。

下一项回到候选发现能力：对既有固定Rust单位和案例，检查单路文本基线的输入可用性、单位位置、参数及原始输出接入。
先明确现有案例哪些在输入范围内，保留未命中、已有委托和未知项；不调参到命中R008，不从九个便利案例计算全仓召回率。
这是基线接入准备，不是论文结果复现或独立测试。复用既有提取和SCC脚本；缺口超出有限范围则记录，不重开Java前端排障。
