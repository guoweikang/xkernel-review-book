# 计数契约：事件阶段、单位与观测边界

## 为什么“处理数量”不够

[写回预算四组对照](2026-11-16-pagecache-budget-factorial.md)区分了交付数量和接受数量。本批将这种差异整理成最小可检查声明，再考察不同接口族。选择是阅读源码后的探索性选择，不是独立盲测：保留 pagecache 为已知回归，选择 Ethernet RX，因为原测试分别观察丢弃帧、可交付包和回收失败；另用 semaphore 的 release 界定当前公式的边界。只读评审还提出 RCU 回调计数作为候选，本批没有执行该候选。

固定对象仍为 xkernel `7e3ac94431a0dbb376d2fc8d85098deeff1bba09`，协议 `research/protocols/event-accounting-v1.json` 在本批评价和内核执行前冻结。

## 声明与绑定

|字段|必须澄清的问题|本批约束|
|---|---|---|
|实体、版本、源码摘要|哪一版的哪个接口？|契约对照固定源文件摘要；不是自动符号解析|
|计数单位|folio、字节、回调还是RX工作项？|单位必须与人工登记绑定相同|
|计数事件|进入回调、成功返回、完成账务还是输出载荷？|事件名绑定具体源码阶段，不从名称猜测|
|计数表示|剩余额度还是已完成数量？|分别采用 remaining / spent|
|观测边界|调用中还是返回后，错误出口是否包含？|限定调用返回时，含成功/错误返回|
|作用域|是否有其他修改者、返还、补充额度？|只处理独占、无credit的单次调用窗口|
|记录完整性|计数事件是否漏采？|记录者必须声明完整；声明不是完整性的证明|

公式仅是：`charged = 所选事件数量之和`；remaining 为 `limit - charged`，spent 为 `charged`，并检查 charged 不超过 limit。没有新加权评分。错误出口并不自动“不计数”：取决于计数事件是否已经发生。

`scripts/check_event_accounting.py` 固化字段与身份检查、单位匹配、事件去重、非负数量、范围拒答和公式评价。输出为记录一致、记录反例、证据不足或输入拒绝，不输出“可合并”或“优化更好”。事件绑定和声明正确性仍由人工负责。

## 跨接口观察：网络接收不是“收到多少就算多少”

固定源码 `net/knet/src/device/mod.rs:165` 的 `RxPoll` 区分 Empty 与 Consumed；Consumed 可以没有IP包。其 `poll_rx` 文档明确：丢弃或ARP处理仍可能消耗一个RX工作项；另有独立的 loopback UDP fallback，不属于同一预算。

`net/knet/src/stack/router.rs:1029` 的 `drain_rx_budgeted_into` 只在 `Ok(RxPoll::Consumed(...))` 后增加 `work_done`。`net/knet/src/device/ethernet.rs:1143` 则先接收、解析、回收，回收失败通过 `?` 返回错误，尚未返回 Consumed。

|场景|驱动已收到帧|Router成功收到Consumed|输出IP包|work_done|
|---|---|---|---|---|
|正常丢弃或ARP处理|1|1|0|1|
|正常可交付IP帧|1|1|1|1|
|驱动接收后回收报错|1|0|0|0|

因此，**实体数量相同不表示计数事件相同；低层已发生工作不表示高层账务已确认。** 这是源码与原断言给出的阶段差异，不是本批新发现的生产缺陷。不可据此把 `work_done` 解释成CPU开销、物理接收总数或持久化完成数。

## 两种证据分别记录

### 结构化控制：12项、重复两遍

控制输入是依据源码/已有断言人工转述的合成记录，**不是从内核日志自动采集的事件轨迹**。

- 4项记录一致：原写回交付计数、RX丢弃、RX交付、RX回收失败。
- 2项记录反例：写回接受后扣减变体的已知值、RX将 driver_received 错当计数阶段。
- 2项未知：事件不完整、存在credit。
- 4项拒绝：单位不符、事件ID重复、源码身份不符、负数量。

两遍输出相同；独立检查器核对12项预期状态及前6项算术结果。这里测的是有限控制下检查器行为，不是语义抽取准确率。并发、不同观测边界虽有拒答分支，本批未各自新增独立控制；不能称全部分支覆盖。记录中的 `instrumented_execution` 标签也不是真实性认证，当前没有可信采集器或跨版本轨迹身份认证，应继续限于受控研究输入。

### 原工程执行：22/22通过

在隔离、恢复原源码的目录运行原 `knet::device::ethernet::rx_budget_tests` 模块。沿用固定x86配置、Rust 1.95.0、TCG、2 vCPU、1 GiB和私有根磁盘，关闭QEMU网络设备；测试用例使用自己的 TestNic，并非真实网卡流量。

运行曾等待其他进程持有的共享 Cargo package-cache 锁，保留了等待日志，没有干预其他任务；锁释放后继续完成。最终 **22通过、0失败、0忽略**，四个关注用例均有逐项成功结果：

1. `non_ip_frames_consume_rx_budget_and_recycle_before_returning`
2. `dropped_frames_exhaust_budget_and_rotate_to_another_device`
3. `zero_rx_budget_does_not_consume_an_ethernet_frame`
4. `recycling_failure_ends_rx_without_reading_another_frame`

第四项原断言直接检查 `received=1`、`recycled=1`、`work_done=0` 和错误返回。运行后源码与原归档逐文件一致、配置未变。guest通过标记及coverage持久化标记均出现，make退出0。原测试通过佐证其断言，不认证合成事件记录，也不是本次检查器在内核自动采集并完成验证。

## 适用边界与负结果

- **网络原测试已有足够的局部观测**。本批没有增加网络断言，也没有证明新检查器比原测试多发现问题；只能称字段能够表述另一个接口族，并与原证据对应。
- `task/ksync/src/semaphore.rs:88` 的 release 会增加可用permit，甚至允许超出初始值；`test_semaphore_basic_acquire_release` 已有相应计数断言。跨release窗口不能直接套只减不增公式。本批仅归档阅读，未运行semaphore测试；单次无release窗口可能适用，不能宣称整个semaphore族均不支持。
- 事件阶段不同不等于必须保留重复实现；共享计数策略可以保留不同事件绑定、结果表示与失败边界。确认工具应该返回这些前提，不能只给“重复/不重复”。
- 控制、声明、绑定均由研究员构造，尚无提供者批准、盲测、独立效果集或新颖性结论。当前不具备专利候选交接准备度。

## 复核与后续

运行目录：`research/evidence/runs/2026-11-16-event-accounting-01/`，保存7份固定源码、协议、registry、cases、两遍评价结果、原内核日志、环境等待证据、源码检查报告与补充摘要。

复核命令：`python3 scripts/check_event_accounting_study.py`。执行脚本 `scripts/run_event_accounting_study.py` 是本批固定入口，不覆盖旧run，不是通用采集平台。本地符号ELF、coverage原始profile及文本在 `research/evidence/originals/2026-11-16-event-accounting-01/`，摘要见 `local-originals.json`；该目录被Git忽略，未声称已上传。研究记录和book尚未提交推送。

下一项应补的是**可追溯事件采集与源码/配置/窗口绑定**，而不是继续扩大人工合成案例数。先在已验证的两个接口上用最小观测验证采集完整性、错误窗口与缺事件拒答，再比较自动采集检查和已有断言的重合/新增覆盖。若没有新增覆盖，如网络本例，应如实记为证据组织价值，而非检错收益。
