# Rust词法前端与SCC输入序列化

## 实现与边界

在既有独立Rust解析工具中新增`src/bin/rust-token-probe.rs`，复用锁定的proc-macro2 1.0.107，不修改原单位提取入口，也不修改SCC检测算法。
构建使用Rust 1.95.0、offline与locked。它接收源码片段，输出token tree展开序列；不是rustc类型检查、宏展开或完整Rust语法验证。
平衡但语法无效的`fn invalid() { let = ; }`可以分词成功，已作为边界对照，不能将tokenized状态解释为合法函数。

表示规范固定在`research/protocols/rust-token-representation-v1.json`：

- 标识符、字面量保留TokenTree显示形式与类别，不归一化变量名或常量值；不是承诺逐字符保持原文件拼写。
- 标点保留字符及Joint/Alone信息；括号、方括号、花括号各有开闭token。
- 普通注释由Rust token解析处理，字符串内的注释标记保留；不使用SCC原来的正则删注释方式。
- doc注释可能被转换为doc属性，若位于单位内部则参与当前表示；签名前缀已在上轮导出视图中排除。
- 序列随后变成词频袋，失去操作顺序。保留括号类别也不意味着词袋保留了完整嵌套关系。

这是有明确取舍的初始文本表示，不是最优Rust相似度定义。保留字面量可能降低改名／改值案例召回，保留内部文档可能引入相似性噪声；未据当前案例命中情况调参。

## 序列化与源码对应

`scripts/prepare_rust_token_bags.py`将token编码为`t`加UTF-8十六进制，再按SCC格式生成词频及header。
这样字面量中的逗号、换行、`@#@`和`@@::@@`不会破坏字段边界；每个单位都校验反向解码后词频一致。
header里的MD5只为上游格式兼容，输入、二进制与工件身份另用SHA256，不将MD5用作安全身份依据。
file_id映射到既有unit_id、固定路径及原区间，身份不由函数名称或分词后的行号猜测。
上游语料哈希不符、回归失败或词法拒绝会阻止成功状态；失败和未达长度门槛的记录不会静默消失。

## 已执行检查

`scripts/check_rust_token_bags.py`覆盖：嵌套块注释和行注释、五类字面量、生命周期、raw及Unicode标识符、联合标点、括号类别、数字后缀、doc转换、两类词法拒绝、语法边界、特殊分隔符编码，以及两项损坏序列化拒绝。全部通过。
语料准备脚本会先执行这些回归，不依赖执行者记得手动运行。
原syn提取回归也重新通过：15个构造输入、5个固定源码文件、41个对照函数；本轮没有重新盘点整个内核。

固定语料运行结果：

| 状态 | 单位数 |
| --- | ---: |
| 总输入 | 2,180 |
| 成功分词并通过序列化回映射 | 2,180 |
| 词法拒绝 | 0 |
| 达到65–500,000 token窗口 | 812 |
| 少于65 token | 1,368 |
| 大于500,000 token | 0 |

最大单位1,241 token。所有成功单位都写入blocks.file，让检测器执行其原有长度筛选；812只是长度符合的单位数，不是重复候选数。
长度门槛沿用预先声明的基线设置，没有为增加覆盖而降低。Rust前端计数包含标点及分组，不能与原分词器的65-token解释混同。
1,368个短单位不能被标成“不重复”；它们在这一基线设置下不能参与合格配对，是工具覆盖边界。

## 复跑

```sh
CARGO_TARGET_DIR=.build/source-workflow-target cargo +1.95.0 build \
  --offline --locked --manifest-path research/tools/rust-syntax-probe/Cargo.toml \
  --bin rust-token-probe
python3 scripts/prepare_rust_token_bags.py \
  --binary .build/source-workflow-target/debug/rust-token-probe \
  --corpus research/evidence/runs/2026-11-05-rust-baseline-corpus-01 \
  --output research/evidence/runs/rust-token-bags-new-run
```

输出目录必须未使用。正式证据位于`research/evidence/runs/2026-11-05-rust-token-bags-01/`，保存源码、依赖锁、回归日志、blocks.file及逐单位映射报告。
本轮**尚未运行SCC候选检索**，没有precision、recall或重构建议。SCC是否接受这些记录、原始配对是否正确回映射，仍是下一道门禁。

下一步只接既有固定检测器，保存原始输出，并核验阈值、大小限制、来源身份和祖先包含关系；不在看到结果后修改前端或门槛。
