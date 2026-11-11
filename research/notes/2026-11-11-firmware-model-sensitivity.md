# 同一段代码为什么会被不同架构模型判成不同关系

2026-11-11。本轮已运行结构投影，但投影关系刻意定义为`contains_call_spelling`，不是编译器解析的调用依赖、职责实现或行为关系。输入为[函数语法实验](2026-11-11-firmware-confirmation-evidence.md)的固定报告；模型为研究员设定的探索假设，未获维护者规范确认。

## 实验设定

把所选OF函数映到OF桶，所选rs_fdtree函数映到DT桶；每个语法调用位置根据冻结词表映到属性读取、CPU视图拼写、reg helper拼写或遍历拼写。未命中的API、构造器和不透明宏保留在未投影清单，不将其偷偷改成“没有操作”。

严格假设允许OF使用视图、helper和遍历，DT使用读取及视图，但未列OF直接读取；过渡假设只多列OF→读取。两者只检查关系集合，不判断是否该允许。其选择在看过案例后完成，不能算预注册效果实验。

## 实际输出

| 快照 | 语法位置总数 | 未投影位置 | 严格假设的偏离 | 过渡假设的偏离 |
| --- | ---: | ---: | --- | --- |
| before | 27 | 15 | OF→底层读取 | 无 |
| after | 57 | 39 | OF→底层读取 | 无 |
| current | 57 | 39 | OF→底层读取 | 无 |

before严格假设的同一高层偏离由is_cpu_node、is_enabled_cpu_node、node_reg、syscon_poweroff共同贡献。after/current少了is_cpu_node，但其他贡献仍在。因此只比较高层边是否存在，无法看到这次局部迁移；必须展开贡献的源码证据。after新增三个方法导致分母变化，不能把计数差解释为覆盖率或质量改善。

before输出还有DT→读取、DT→视图、OF→视图三条absence。这与当前抽取范围中尚无三个新增方法有关，不能解释成整个库缺少底层读取能力，更不是三个功能缺陷。after没有这些absence也不证明设计已完善。

在同一源码上只增添一条高层边，所有divergence消失。这展示模型假设会支配结构分类结果，**不是过渡模型更准确的实验结论**。放宽模型容易让一切通过，收紧模型容易制造误报；必须独立确定规范／迁移例外并评估映射，不能用“符合边更多”奖励一个方法。

## 下一项方法取舍

1. 普通crate依赖和粗粒度关系只作筛选，保留逐函数／逐位置贡献，不直接作为职责确认。
2. 从文档读取职责时要区分规范、现状、迁移债务与例外。缺少该区别时保留unknown，不自动套用禁用边规则。
3. 映射推荐与架构判定分开评价。后续InMap路线如能运行，评价的是映射建议，不把其命中率借用作职责正确率。
4. 当前开发案例与模型都看过历史结果，不进入独立测试集；没有输出生产优化建议。

## 工具与证据

```sh
python3 scripts/project_firmware_syntax.py --input research/evidence/runs/2026-11-11-firmware-confirmation-02 --output research/evidence/runs/firmware-projection-new-run
python3 scripts/check_firmware_confirmation.py --syntax-run research/evidence/runs/2026-11-11-firmware-confirmation-02 --projection-run research/evidence/runs/2026-11-11-firmware-projection-01
```

`research/evidence/runs/2026-11-11-firmware-projection-01/report.json`保存两模型×三快照的完整输入、映射、三类边、未投影项和源码贡献位置；算法与runner源码及SHA随附。检查器重算投影、重跑语法提取和投影，校验片段／位置／摘要，并篡改临时calls.json验证拒绝不可信输入。实验未运行原RMTool或编译内核。
