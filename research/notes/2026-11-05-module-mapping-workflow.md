# 模块文件候选进入固定流程

日期：2026-11-05。输入仍为固定提交 `7e3ac94431a0dbb376d2fc8d85098deeff1bba09` 的四 crate 清单。
本轮实现文件候选映射，不进行重复检测，也不改变阶段 A/B 的边界。

## 1. 固化的实现

- `scripts/map_source_modules.py`：基于模块语法节点、属性、父级上下文及固定 Git 树产生候选。
- `scripts/check_module_mapping.py`：真实解析器节点结合构造文件树，验收18种路径形态和3种门禁错误。
- `research/protocols/source-units-v2.json`：新增映射规则版本和预期状态分布；v1原协议不修改。
- `scripts/run_source_workflow.py`：默认执行v2，新增模块回归、modules.json和验收门禁；v1仍可显式执行。
- `scripts/check_source_workflow.py`：复查时校验模块产物哈希，并重新计算模块门禁。

解析器现在将直接 `#[path]` 字符串交给 syn 解码并记录 `path_overrides`，支持普通及 raw 字符串。
没有用正则猜 Rust 字符串，也不会将重复path属性任选一个。

## 2. 规则与反例

依据为 [官方模块规则核查](2026-11-05-module-path-rules.md) 中的 Rust Reference 和 Cargo Book。
在线规范未固定到项目编译器版本，因此实现定位是保守文件候选，不是对rustc解析过程的完整复现。

| 形态 | 当前策略 |
| --- | --- |
| manifest指定或约定root、mod.rs、普通文件 | 按各自目录基准生成默认的name.rs和name/mod.rs候选 |
| 普通内联模块嵌套 | 将内联祖先名称追加到默认目录基准 |
| 顶层直接path字符串 | 只检查相对声明文件目录的显式路径，不再混入默认双路径 |
| 默认双路径同时存在 | ambiguous，保留两条证据，不任选 |
| 受版本控制的候选文件没有找到 | missing，不声称生成文件或外部输入也不存在 |
| cfg条件 | 保留not_evaluated，即使找到文件也不认定启用 |
| cfg_attr上下文 | deferred，不猜它是否影响path或属性宏 |
| 内联祖先path、内联块内叶子path、函数内mod | deferred，明确当前不支持，不套用错误规则 |
| 多个或非字符串path | deferred |
| 指向仓库外、绝对路径、反斜杠路径、非普通Git文件如symlink | deferred，不读取外部路径或追随符号链接 |
| raw identifier | 移除r#前缀后构造文件名，保留原节点名称 |

18项案例涵盖上述形态以及自定义crate root文件名。3项门禁负向测试分别伪造声明身份、目标路径、cfg已启用结论，均被拒绝。
没有运行rustc对这些案例做差分验证，故测试通过只证明当前编码规则满足这些验收样例。

## 3. 四 crate 的实际输出

57个外置模块声明全部进入映射台账：

- **50个 matched_candidate**：在规则假设下找到唯一普通Git文件。
- **7个 deferred**：4个来自 `task/kspin/src/lib.rs`，3个来自 `util/klazy/src/lib.rs`；
  原因均为文件级cfg_attr上下文，不是丢失文件或解析失败。
- 本样本没有 ambiguous/missing；这两种状态已由构造案例测试，不能因此删除对应处理分支。

这7项是保守策略造成的暂缓，不能解释为已证实path会改变。当前没有区分
`cfg_attr(..., no_std)` 等不影响模块路径的情况，仍然可能过度暂缓；应在增加结构化属性解释及反例后修订协议。

每条记录同时保存源节点ID、声明范围、候选路径和Git文件mode、匹配依据、目标是否在现有盘点内，
以及 `file_role_assumption`、`cfg_state=not_evaluated`、`semantic_membership=not_established`。
普通文件的角色写为 `ordinary_non_root_unverified`，不凭文件名宣称它一定不是自定义crate root。

root发现仅覆盖默认lib/main及manifest显式lib/bin路径，不是完整Cargo target发现，
也没有还原include!/宏加载或递归path重命名上下文。文件角色假设不成立时，候选关系必须重新核验。
因此**50/57不是召回率、准确率、模块覆盖率或编译归属正确率**。

## 4. 自动门禁与保留记录

v2要求每条外置声明恰有一条映射记录、提交一致、状态汇总可重算、目标路径有普通Git文件证据，
且不得把未知cfg/语义归属升级为确定结论。50/7状态数量只用于固定快照回归，不能用它证明映射正确。
首次运行得到该状态分布后将其固定到v2协议；它不是独立评估数据集上的成功率。

完整结果：`research/evidence/runs/2026-11-05-source-units-v2-verified/`，状态passed_with_limits。
其中modules.json是可机器读取的台账，report.json包含门禁、输入/产物哈希和已知限制。
较早的v2运行目录也保留，后一次补充了逐条文件角色假设，没有覆盖旧记录。

复查命令：

```sh
python3 scripts/run_source_workflow.py --repo /root/codes/x-kernel \
  --config research/protocols/source-units-v2.json \
  --output research/evidence/runs/new-module-check
python3 scripts/check_workflow_integration.py --repo /root/codes/x-kernel \
  --run research/evidence/runs/2026-11-05-source-units-v2-verified
```

下一步可在这份稳定输入上准备候选发现试点的标注和评价协议；
模块完整语义解析继续作为明确限制，不应无限扩展输入工具而推迟研究问题本身。
