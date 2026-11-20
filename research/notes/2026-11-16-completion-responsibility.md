# 提交、完成与持久化：写回责任契约

## 从选中wrapper追到实际实现

沿固定版本`7e3ac94431a0dbb376d2fc8d85098deeff1bba09`归档kvfs wrapper、pagecache实现及现有测试。Git blob与SHA-256核对通过，wrapper与先前抽样副本逐字节相同。协议`research/protocols/completion-responsibility-v1.json`固定四项命题、必要声明元素和验证边界。

需要纠正“两个接口可能已共用同一扫描器”的泛化：选中`writeback_cached_folios`调用`writeback_until`，后者有自己的循环；`submit_cached_ranges`调用`submit_cache_pages`再调用`scan_writeback`。与后者共用扫描器的是第三个接口`write_cache_pages`，不是选中的同步folio接口。低层标记收集等辅助机制已有共享，不能简单标为两套完全独立实现，也不能据此宣布无优化空间。

## 契约必须区分的事件

|事件|含义|不能自动推出|
|---|---|---|
|handoff_to_callback|批次所有权交给提交回调|回调已接受、设备已开始或完成|
|callback_accepted|回调接受这次提交|数据I/O已结束|
|io_ended|调用者观察其提交I/O结束|pagecache账务已更新或数据已持久化|
|completion_accounted|完成凭证更新folio及索引状态|设备持久化屏障已完成|
|durability_established|另有明确持久化协议证据|不能由本组helper单独得出|

不是所有路径都经过一条成功直线：回调可拒绝；drop可走失败完成账务；扫描可在已交付批次后报错。空输入或零预算的Ok也不代表发生过写入。

### 预算是交付数，不是接受数

`pagecache.rs:404`在`submit(batch)`前扣减folio预算。拒绝批次也计入。这要求提供者明确**预算计数发生在哪个事件、用什么单位、拒绝是否计数**，只写“提交预算”仍有歧义。

同步folio路径在写回回调成功、结束该folio写回状态后扣预算；这与交付批次路径的账务时点不同。该结论来自固定源码阅读，不是新的性能测量。

### drop不是等待完成

`WritebackBatch::into_parts`转移数据和完成凭证；`WritebackCompletion::drop`调用失败完成处理。它可能获取索引锁，但不等待设备I/O；仍在索引中的未完成folio重新标脏。文档要求调用者先drain已提交I/O再丢弃凭证，包括错误路径。

因此不能把Rust自动析构理解为“系统自动等到I/O结束”。这里同时存在语言所有权、I/O生命周期和跨模块清理职责，三者需要显式连接。

## 要求提供者声明的必要元素

协议要求声明实体/版本/配置及声明权威、返回值保证的阶段、预算事件与单位、所有权转移、完成凭证拆分/drop语义、drain责任与出口、延迟错误归属、保护对象与保护持续期、睡眠/锁约束、明确不保证的事项。

这些是允许对crate文档提出的新规范要求；目前由研究员整理，尚未获得提供者确认。文档缺项可以整改，不作为放弃该方法的理由。但声明必须再与实际来源、测试或调用者证据核对，不能靠字段齐全就判定职责合理。

## 已有测试及证据缺口

归档测试来源为`mm/pagecache/ut-tests/writeback_unittest.rs`，本轮只阅读，**执行数为零**。

|命题|已有直接依据|当前缺口|
|---|---|---|
|扫描返回后可以保留未完成批次|710行测试保存batch，返回后断言仍under_writeback，再手动complete|尚未运行；未涉及真实设备完成|
|拒绝批次也消耗交付预算|404行实现先扣后调用|747行测试使用`&mut 2`，没有最终预算断言，需补明确观测|
|后续拒绝不结束先前保留批次|747行测试检查先前folio仍under_writeback，随后drop|尚未运行；测试没有真实先前设备I/O|
|完成凭证不代表持久化|类型文档明确非durability barrier，实现为缓存状态处理|没有设备/崩溃持久化实验，不把规范非保证变成设备测量|

779、802行还提供索引借用、非法前缀及不获取内容锁的状态控制。它们有复用价值，但不能把读到测试当测试通过。只读Agent复核确认上述边界；不是独立人工标签。

## 执行入口初检与下一步

固定`Cargo.toml`包含内核任务、同步、分配和unittest依赖；lib通过`unittest::path_mod_test!`接入测试，而不是普通host `#[test]`。固定Makefile的unittest目标启动内核QEMU流程，并提供UNITTEST_CRATE筛选传参。筛选并不证明依赖或配置已启用；本轮没有运行make或改根配置。

下一批先评估在隔离固定版本下执行原pagecache测试的配置、依赖与QEMU条件；优先复用真实测试，不先制作另一个玩具状态机。若只可抽取部分逻辑或替换依赖，必须分别报告，不能冒称原测试复现。拒绝预算的新增断言单独记录为我们的扩展，不归给作者测试。

这使研究问题从“两个相似wrapper能否合并”收敛为“契约能否保留阶段、预算和责任差异，并产生可验证义务”。局部扫描机制是否值得共享、跨crate职责是否应调整，仍没有结论；尚无新的效果分数或专利成熟交接。

## 工件

- `scripts/archive_completion_sources.py`：按固定Git版本归档并核验源码。
- `research/protocols/completion-responsibility-v1.json`：四项命题与必要字段。
- `research/evidence/runs/2026-11-16-completion-sources-01`：wrapper.rs、pagecache.rs、existing-tests.rs、来源摘要及只读执行入口材料。

源码行号均指上述完整副本。复现归档使用新的run-id；无生产变更、无提交推送。
