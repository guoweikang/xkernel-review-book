# 四个 crate 的源码单位清单与未覆盖边界

日期：2026-11-05。阶段 A 的输入适配验证，不是重复检测、性能基线或优化收益实验。
固定源码：`7e3ac94431a0dbb376d2fc8d85098deeff1bba09`。

## 1. 选取范围与实际结果

在运行前选定四个物理 package 目录：延续已有样本的 `util/klazy`，增加
同步相关 `task/kspin`、文件系统接口 `fs/kvfs` 和过程宏实现 `util/macros`。
目的是覆盖几种源码形态，不是随机抽样或宣称四者代表全仓。
本轮对这些目录下 Git 跟踪的全部 `.rs` 文件进行读取；按最近的 Cargo.toml 划分物理归属，
嵌套 package 会另记排除清单。本次没有嵌套 package 文件被排除。

| 物理 package | Rust 文件 | 函数/方法/trait 声明 | 含 tests 或 ut-tests 路径的文件 |
| --- | ---: | ---: | ---: |
| fs/kvfs | 72 | 2075 | 30 |
| task/kspin | 8 | 82 | 1 |
| util/klazy | 7 | 59 | 3 |
| util/macros | 1 | 9 | 0 |
| 合计 | 88 | 2225 | 34 |

88 个文件均被固定版 syn 接受，解析/适配失败清单为空。
2225 项分为 **2180 项有函数体、45 项无函数体声明**，没有把后者当作实现代码。
另记录 struct 224、enum 24、trait 23、impl 384、mod 61、closure 454、macro_tokens 1640。
全部 5035 个节点的本次快照 ID 无重复；这些节点嵌套且范围可能重叠，不能直接累计为去重代码量。

klazy 变成 7 文件、59 个函数而非前轮 5 文件、41 个函数，是因为本轮读取物理目录内全部源码，
前轮只读取选定配置 facts 引用的五个文件。两组分母不同，不是算法效果提升。
测试路径只是标记线索，路径外也可能含测试，不能把剩余文件自动标为纯生产代码。

## 2. 新增的元数据

结构化探针升级到 `syn-unit-probe/2`，保留上一轮结果文件，新增 v2 验证记录。

- 文件：固定提交、源码哈希、物理 package、解析状态/诊断、文件级属性、测试路径线索。
- 节点：种类/名称、字节范围与行范围、父级索引、直接属性的路径/范围/原始片段。
- 函数：源码签名和可选 body 范围；声明与实现区分。
- 模块：内联/外置声明区分；不把物理目录猜成逻辑模块路径。
- 身份：由 commit、路径、源码哈希、节点种类/范围/局部索引构造快照 ID，**不是跨版本稳定 ID**。
- 配置：显式 `cfg_state=not_evaluated`；父级属性通过 ancestor 索引追溯，不伪造生效结果。

直接属性、祖先属性和文件属性分开保存。嵌套 cfg/derive/inline 的构造样例验证了这些信息没有丢失。
属性原文是源码事实，不等于属性宏行为已解释；当前也没有输出解析后的类型或完整设计契约。

## 3. 尚未解决的边界没有被“零失败”掩盖

| 边界 | 本轮观察或策略 | 后续处理 |
| --- | --- | --- |
| 外置模块归属 | 57 处外置 mod 声明；只记录，没有解析到文件 | 处理普通布局、内联上下文、path 属性、cfg 歧义，并保留未解析原因 |
| 宏 | 1640 个 macro_tokens 节点，包含调用等不同用途 | 不把这个数字称作生成函数数；宏展开及属性宏关联仍独立处理 |
| cfg | 41 个节点直接 cfg/cfg_attr 属性；另有文件属性和继承上下文 | 不将其计为全部配置项，也不据此推断当前编译覆盖 |
| 未支持节点 | 当前不全面提取 union/type alias/const/static/foreign fn 等 | 节点清单不是全量符号索引；扩大用途前增加这些类别及验收样例 |
| Verbatim | 顶层有显式保留，其他位置的变体尚未穷尽 | 不声明未知语法均已登记 |
| 解析拒绝/超时/崩溃 | 文件保留在分母，输出状态/原因，不产生可用单位；每文件进程30秒超时 | 不以忽略失败文件来提高覆盖率 |
| 编译事实关联 | 本轮没有全量 facts join | 编译身份、属性宏变换、跨配置对应仍不能从源码 ID 推断 |

“88 文件全部接受”仅指本次范围和接口版本，没有独立人工真值，因此不是 100% 提取准确率。
物理 package 归属也不是 Cargo target 成员身份；可能包含配置外文件或当前不使用的源码。

## 4. 复查产物与验证

实现：`scripts/inventory_rust_units.py`、`research/tools/rust-syntax-probe/`。
结果：`research/evidence/inventory/2026-11-05-four-crate-units.json`。
适配回归：`research/evidence/inventory/2026-11-05-syn-adapter-v2-check.json`。

新增属性样例后，15 个构造输入及原五文件检查通过。
另以 `/bin/false` 替代解析器，对 util/macros 做负向检查：唯一文件记录 adapter_failure，
失败清单保留路径、节点为空，验证了异常不会被计作成功或从文件分母中消失。
没有构建内核、运行重复检测、调用模型或生成重构补丁。

```sh
CARGO_TARGET_DIR="$PWD/.build/syn-probe-target" cargo +1.95.0 build \
  --offline --locked --manifest-path research/tools/rust-syntax-probe/Cargo.toml
python3 scripts/inventory_rust_units.py --repo /root/codes/x-kernel \
  --revision 7e3ac94431a0dbb376d2fc8d85098deeff1bba09 \
  --binary .build/syn-probe-target/debug/rust-syntax-probe \
  --package util/klazy --package task/kspin --package fs/kvfs --package util/macros \
  --output research/evidence/inventory/2026-11-05-four-crate-units.json
```

## 5. 下一步

优先核对这批外置模块的源码映射，保持“找到路径”“确认逻辑归属”“确认当前配置启用”三种状态分离。
暂不扩大到全仓或增加模型；先使已有单位的归属和比较口径可解释。
这仍是 A 阶段输入准备，之后再按原计划开展 B 的真实候选试点，不改变研究阶段。
