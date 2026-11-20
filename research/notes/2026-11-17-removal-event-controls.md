# 删除事件快照：原版、局部抽取与回退错误控制

## 实验要回答的问题

[原版基线](2026-11-17-removal-event-baseline.md)的297项通过，不意味着覆盖了RemovedEntry的关键字段。本批将实际候选确认分为两个问题：局部helper是否保持被观察的行为；新增断言是否能识别旧测试遗漏的一种回退政策变化。

检索`research_lookup.py RemovedEntry fallback --limit 4`，阅读原版基线、执行方案、mount/dentry/inode及已有测试。协作者Goodall编写专用追加fixture并审阅候选，主研究员编写运行器、核对源码、执行和独立结果检查。两者协作不是盲评、独立人工真值或文档语义自动生成。

## 固定设计

协议`research/protocols/removal-event-factorial-v1.json`，执行器`run_removal_event_factorial.py`。虽然历史命名用了factorial，实际是四个有目的的配对控制，**不是完整析因设计**：

|条件|实现|测试|
|---|---|---|
|original-observed|冻结原版|旧297项加6个新入口|
|candidate-observed|仅两处RemovedEntry构造改为同一个helper|相同新增断言|
|mutant-old|getattr失败改为None，成功仍Some后端值|旧297项|
|mutant-observed|同一错误控制|相同新增断言|

旧original测试是上一批单独留存的基线，不冒称本批完整析因中的一格。错误变体测兼容性，不裁决“缓存回退一定比None正确”。不根据结果换坏变体或挑断言。

固定源码仍为`7e3ac94431a0dbb376d2fc8d85098deeff1bba09`。从已验证基线复制到新的隔离目录，离线Rust 1.95.0、原kvfs内核测试框架、QEMU TCG、2核1GiB。每格使用新建私有ext4磁盘、单次300秒上限。源码候选、测试、运行器及摘要在首格执行前冻结，运行后核对归档已有文件和配置；不声称目录没有构建生成文件。

## 新增观测及限制

fixture复用原mount MockDirOps的metadata模板与lookup，执行真实Mount/Path/VfsInode/Dentry和删除调用链；专用受控后端不是实际磁盘文件系统。六入口包含八场景：unlink/rmdir × getattr成功/失败 × 删除成功/失败，后两种getter状态在删除失败入口内分别检查。

后端nlink预设7、缓存3，成功删除回调将两者改为2。断言快照保留删除前的7或3，parent/name/victim身份正确，getter在删除回调前恰好一次，删除类型选择正确；删除失败必须返回Err并保留缓存/原计数。每场景状态独立，无静态共享计数。

测试本身另持有victim引用，因此不能证明快照独自延长生命周期。单线程调用计数不是持锁或并发交错证明。源码审阅显示两调用仍位于原锁内验证闭包、策略检查之后和删除之前，表达式次序未显式移动；这与运行观测是不同证据。

## 接入失败也保留

`2026-11-17-removal-factorial-01`在原版首格编译失败：普通helper返回`()`, unittest断言宏却要求失败时返回TestResult（E0308），零测试执行。保留原fixture、编译日志、输入与失败报告；没有进入后续格，不当作原版行为反例。

02只修正helper返回TestResult及各入口检查传播，原断言、场景和候选不变，重新冻结完整四格。每次复用隔离副本时记录前序允许文件的起始摘要，其余3632个归档源文件不得变动；不覆写01。

## 结果与取舍

执行结果须经`check_removal_event_factorial.py --run <批次>`独立核对后登记。核对包括原297个测试ID完整集合、6个新入口、唯一性、汇总完成标记、失败具体入口和日志摘要。遍历完四格或任意非零退出不等于成功杀死变体。

02四格全部完成，独立核对通过：

|条件|实际通过/总数|失败及解释|
|---|---:|---|
|original-observed|303/303|无；新增观测在原行为上成立|
|candidate-observed|303/303|无；局部抽取保持这些观测|
|mutant-old|297/297|无；旧测试漏掉这处不相容变化|
|mutant-observed|301/303|仅unlink/rmdir两个cached_fallback入口失败|

失败日志明确显示`removed.victim_nlink=None`与预期`Some(3)`不同，不是编译、启动、超时或无关错误。其余成功快照与删除失败场景仍通过。四格配置不变、无非预期归档源码变化；每格仅执行一次。具体运行耗时包含增量编译和coverage导出，不作为性能对比。

证据目录`research/evidence/runs/2026-11-17-removal-factorial-02`包括冻结输入、原版/候选/变体源码、两套测试、差异、每格命令/完整日志/逐测试结果及checked-results。01的编译失败独立保留。复跑应在新的隔离源码副本中使用新的批次名：`python3 scripts/run_removal_event_factorial.py --source /tmp/xkernel-removal-event-新副本 --run 新批次名`，随后执行checker；不覆盖旧输出。

这支持两个局部结论：此具体抽取在新增观测与现有测试下兼容；关于失败回退的显式断言弥补了一个可复现盲区。它不证明自动提取这些义务的能力、任意回退变体可检出、全并发安全或该回退政策本身正确。

候选新增私有helper的victim与victim_path是关联冗余参数；当前调用保证一致，但签名不阻止未来传错。旧外围注释仍未与缓存回退逻辑同步，因此本批不能声称改善文档一致性或维护净收益。行为保持的开发原型不是可直接合并的最终接口设计。

结构计量用`measure_removal_structure.py`对归档源码另存副本后以同一rustfmt 1.95.0工具链、edition2024格式化，不修改已冻结/编译源码。完整模块1919→1915行、非空1732→1727；新增1个私有helper、2调用点及3个显式参数（不计self）。因此仅净减4行，局部集中政策维护是可能收益，而非已测维护改善。归档原始生成候选有缩进问题；格式化副本及diff供审阅，未冒称它们是实际编译字节。

下一步将结果回填原共同预算40对队列，保留被融合挤出的代码候选和所有未尝试结果为未知，不据两个事后选择案例计算方法成功率。不继续扩展通用快照验证器或通知端到端框架。

该回填已执行，见[发现队列与行动证据](2026-11-17-discovery-action-map.md)。快照局部控制支线到此收束：不再以继续修小helper作为方法进展。
