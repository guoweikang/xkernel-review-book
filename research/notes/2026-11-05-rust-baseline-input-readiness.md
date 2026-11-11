# Rust文本基线：输入就绪与前端边界

## 本轮形成的工具产物

复用既有syn单位清单，不再手写函数提取器。新增`scripts/export_rust_baseline_corpus.py`，从固定Git对象导出原文输入及源码映射。
固定版本`7e3ac94431a0dbb376d2fc8d85098deeff1bba09`；范围为kvfs、kspin、klazy、macros四个物理package。
输入清单哈希和上游验收状态均核对，每份源码再次比对原清单哈希，导出范围必须落在原单位内并以原body花括号为边界。

实测导出88份原文件、2,180个带body函数／方法单位。每个单位保留稳定ID、原文件及片段SHA256、字节区间、行号、属性和祖先关系。
`units.zip`保存从签名起点到body结束的原文，`sources.zip`保存完整源码，`units.json`负责映射；不是可独立编译的2,180个crate。
签名前属性与文档不参与这个文本视图，但在映射和原文件中保留；函数体内部注释、字符串和宏内容没有改写。

存在22个嵌套在函数内的函数单位，外层片段也包含其文字，后续不能将这种包含关系当作两个独立重复实现。
638个单位带test_path_hint，这只是既有路径提示，不是全部测试代码的语义识别；没有过滤测试、cfg或小函数。
没有求值cfg、展开宏或核验编译归属，2,180不代表某个实际配置的运行函数总数。

## 自动检查

```sh
python3 scripts/export_rust_baseline_corpus.py --repo /root/codes/x-kernel \
  --output research/evidence/runs/rust-baseline-input-new-run
python3 scripts/check_rust_baseline_export.py \
  --run research/evidence/runs/rust-baseline-input-new-run
```

新目录要求防止覆盖证据。输出记录失败，而不是默默跳过出错文件。
本轮检查通过：UTF-8构造样例、三项错误区间拒绝、全部2,180片段逐字节回映射、ID唯一性和工件哈希。
回映射证明导出遵循已有区间，不独立证明syn区间或语义单位必然正确；原提取回归及已知限制继续适用。

## 现有案例到底覆盖哪些

| 案例 | 当前输入范围 | 不能声称什么 |
| --- | --- | --- |
| R002、R003、R004 | 两侧所需源码文件在四package中 | 文件在不等于候选必命中或已有真值标签 |
| R001 | 只有klazy侧 | xcover缺席不能算漏检 |
| X006、X007 | 只有X-Kernel侧 | 不能测跨项目发现能力 |
| X005 | ArceOS不在输入 | 不能计算该例覆盖 |
| R008 | 三个对齐消费者均不在输入 | 不为追求命中临时把它们塞入本轮范围 |
| H001 | 历史父版本及消费者不在输入 | 不冒称历史机会发现成功 |

这是现有固定清单的接入检查，不是新的代表性抽样，更不是全仓扫描。

## 为什么不直接将扩展名改为rs

固定SCC源码`tokenizers/file-level/config.ini`目前选择C/C++/C#扩展名；其`tokenizer.py:141–156`先用正则删除块注释、行注释，再将分隔符替换为空格。
直接允许rs只改变文件接收范围，不能使这些正则获得Rust词法语境。
例如字符串内的`//`并非注释，Rust嵌套块注释也不能简单等同最短`/*...*/`匹配；本轮依据源码指出适配风险，未运行原分词器的Rust反例，不报告实测错误率。
Rust生命周期、原始字符串、字符和运算符也需要明确表示规则，不能依赖“看起来能输出token”。

因此此次未运行候选检索，更没有把导出成功写成检测成功。Java方法前端不适用于此处，也不重新排查它。

## 下一步的有限实现范围

保留SCC检测器，复用现有Rust解析依赖构建词法前端。先通过字符串、嵌套注释、生命周期、原始标识符、标点和序列化分隔符构造回归，再接入固定输入。
token表示和序列化规范必须先记录；新前端会改变计数语义，必须称为Rust适配基线，不能宣称原论文指标复现。
协议`research/protocols/rust-text-baseline-input-v1.json`预先沿用现有冒烟基线的65-token下限及80%阈值；不是已校准的最佳参数。
过小单位、失败单位和未命中需保留，祖先包含关系单列；相似配对不直接生成“应该重构”的意见。
当前没有真值标签或检索输出，不能计算precision、全仓recall或优化成功率。

证据目录：`research/evidence/runs/2026-11-05-rust-baseline-corpus-01/`。上游提取入口与门禁见`research/tools/source-unit-workflow.md`。
