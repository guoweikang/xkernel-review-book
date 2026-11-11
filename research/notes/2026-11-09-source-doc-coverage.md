# 固定源码文档覆盖与对象绑定

日期：2026-11-09。目的：为代码／文档候选发现比较准备输入，而非训练或评价检测器。复用现有syn解析器，增加字面量doc文本及inner/outer属性类型输出；新增 `scripts/inventory_source_docs.py`。不调用模型，不依赖移动中的内核工作树。

## 输入与实际结果

使用既有四包源码归档，提交 `7e3ac94431a0dbb376d2fc8d85098deeff1bba09`。校验sources.zip、units.json哈希，再核对每个函数的源文件哈希、名称、语法种类、完整对象范围和正文导出范围。

| 包 | 有函数体的归档单元 | 直接非空字面量文档 |
| --- | ---: | ---: |
| fs/kvfs | 2032 | 721 |
| task/kspin | 80 | 26 |
| util/klazy | 59 | 25 |
| util/macros | 9 | 8 |
| 合计 | 2180 | 780 |

88个文件全部解析，2180个函数全部唯一绑定，直接文档覆盖约35.8%。沿用既有test_path_hint分层：测试路径提示组638个中12个有文档；其他1542个中768个有文档。路径提示不是实际cfg构建分类，其他组不能直接称为生产函数。

解析记录保留源码范围、原始属性、字面量文档、祖先索引、签名和函数体范围。文件级文档保留为文件作用域，不猜测它一定属于crate；嵌套模块文档也不自动复制到子函数。全体受支持对象属性中，有1项非字面量doc属性和3项cfg_attr；前者不一定是未展开文本，也可能是doc选项，后者也不一定含文档。

## 可靠性检查与一次失败

内置控制覆盖Unicode字节位置、连续文档及显式doc字符串、普通注释排除、文件／模块inner文档、嵌套函数不继承文档、include_str不求值、cfg_attr不执行、trait声明与宏生成代码不展开、非法源码拒绝。

首次运行01因把original_range误当作签名起点而停止，未生成成功清单。原归档中original_range包含属性，range才对应签名到函数体末尾；已修正为同时验证两组位置。01保留事后失败说明，02完成成功提取，旧数据未修改。

既有解析器回归检查也通过：15个控制样例、5个固定源码文件、41个函数。只证明已检查范围的结构提取行为，不是整个Rust语法或语义正确性证明。02保存实际运行时源码快照；随后主程序只有rustfmt要求的排版调整，快照不覆盖。

## 证据与复跑

- 成功输出：`research/evidence/runs/2026-11-09-source-doc-inventory-02/`，包括files.json、bindings.json、controls.json、脚本、解析器和锁文件、哈希报告。
- 失败说明：`research/evidence/runs/2026-11-09-source-doc-inventory-01/failure.json`。
- 回归结果：`research/evidence/inventory/2026-11-09-syn-doc-regression.json`。

在book根目录执行，输出目录必须不存在：

```sh
env PATH=/root/.rustup/toolchains/1.95.0-x86_64-unknown-linux-gnu/bin:$PATH \
  CARGO_NET_OFFLINE=true cargo build --offline --locked \
  --manifest-path research/tools/rust-syntax-probe/Cargo.toml \
  --bin rust-syntax-probe --target-dir .build/rust-doc-probe
python3 scripts/inventory_source_docs.py \
  --binary .build/rust-doc-probe/debug/rust-syntax-probe \
  --output research/evidence/runs/source-doc-inventory-new
```

## 实验意义与边界

已经具备代码对象到原生文档的直接连接，不必等待完整语义数据库。未覆盖字段、常量、类型别名等全部对象，也未展开宏、配置或include_str，不是rustdoc构建结果；文档存在不证明准确、充分或与重复判定相关。

这次观察支持先分开做“有直接文档的受控比较”和“含缺失文档的完整归档范围比较”，不能先丢掉1400个无直接文档函数后只报好看的效果。祖先文档、trait文档补全和代码生成摘要可作为后续独立干预，不能暗中加入基线。

下一步核查并固定一个公开的简单文档检索实现及评价协议，生成文档单独／代码基线的候选对并保留未知标签。尚未运行相似度检索、标注新候选、证明召回增益或生成重构补丁。四包范围不是整个xkernel，也不是跨项目独立测试集。
