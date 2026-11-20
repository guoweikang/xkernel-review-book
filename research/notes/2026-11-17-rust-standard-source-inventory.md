# Rust标准库来源：固定身份，不提前授予测试资格

## 来源选择与实际环境

[文档评价设计](2026-11-17-document-evaluation-design.md)要求从不同来源构建机制材料。本轮先核对本机工具链，不安装或改变版本。默认stable实际是1.97.1，不能将其与过去实验用1.95.0混同；显式`rustc +1.95.0 -Vv`得到提交`59807616e1fa2540724bfbac14d7976d7e4a3860`。

本机1.95.0已存在rust-src。此前只在stable标准位置未找到的记录仍是当时有限范围的观察，不应解释为所有工具链均无源码。当前从显式1.95.0 sysroot读取。

## 固定范围与结果

`rust-standard-source-inventory-v1.json`事前限定core/src、alloc/src常规.rs和两份Cargo.toml，不依据相似分数、文档齐全程度或预期效果选文件。遍历338个Rust文件加2份Cargo元数据，共7943303字节：core263文件，alloc77文件（均含各自Cargo）。

每个文件均出现在安装rust-src清单；保存路径、长度、SHA256、按Git对象格式重算的blob SHA1。归档zip固定顺序/时间戳，写入后逐文件重新读出核验。与旧xkernel四package语料源文件的完全摘要匹配为0；这不排除局部复用、改名或同源算法。

两个Cargo均声明MIT OR Apache-2.0；这是包级许可声明，不是对每个文件/依赖的法律认证。源码原件保存在Git忽略的`research/evidence/originals/2026-11-17-rust-standard-inventory-01/core-alloc.zip`，大小1745337字节、SHA256为`5591913e16d3137a839db2dd5354dbd65288552dad56386e1ea74fe6725de635`。公开材料默认只有索引、摘要、脚本和验证记录。

## 官方身份交叉验证

仅记录编译器版本不能保证本地源码没被改动。因此另开`2026-11-17-rust-standard-upstream-01`，保存协议、两次官方GitHub API响应及HTTP头：先读固定提交根树定位library，再读该子树递归清单，均要求未截断。逐项比较340份本地归档的重算Git blob与官方树：**340一致，0不匹配**。[官方固定源码](https://github.com/rust-lang/rust/tree/59807616e1fa2540724bfbac14d7976d7e4a3860/library)

这提供源码版本身份依据，不证明工具链二进制来源、构建可复现、源码行为正确、文档准确或研究样本独立。初始inventory的`upstream_identity_verified=false`保留为先前阶段事实，后续verification报告给出已完成核验，不回写旧工件。

## 可复现入口与停止边界

```sh
python3 scripts/inventory_rust_standard_sources.py --run <新库存批次>
python3 scripts/verify_rust_standard_upstream.py --inventory <库存批次> --run <新核验批次>
```

库存运行`2026-11-17-rust-standard-inventory-01`保存安装清单、版本、冻结协议和完整库存；验证器先查库存/zip摘要，再核对上游，不执行第三方源码。没有Rust测试、相似度排序、新机制标签或方法效果结果。

所有文件仍标`prior_exposure=unknown`和`independent_test_eligible=false`。标准库可能早已进入研究者或模型知识，不能称从未见过；可争取的是本研究开发/测试过程的家族隔离，不是无法核实的预训练清洁性。

下一批先依据该完整库存筛查源码机制与来源引用，记录全部纳入/排除理由；复用已存在Rust提取前端，避免按几个熟悉函数重新手写玩具集。先选范围/定义标签观察域，再生成文档干预；未满足机制证据和分组门槛前不跑效果比较。
