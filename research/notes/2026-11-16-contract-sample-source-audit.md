# 新抽样 pair-2/4：契约与委托静态复核

2026-11-16。依据 `research/evidence/runs/2026-11-16-contract-sample-01/frozen.json`，源码固定 `7e3ac94431a0dbb376d2fc8d85098deeff1bba09`。本轮直接阅读四份 unit 与对应完整 source；两对各自的两份 source 经逐字节比较相同。仅静态 Agent 复核，无新实验、无提供者确认；事前固定抽样不等于盲测或独立人工标签。未追查本范围之外的回调实现/调用方。

## pair-2：[250,251] FsContext 两种事务构造

- **原文定位**：`research/evidence/runs/2026-11-16-contract-sample-01/pair-2-1-unit.rs:1`（new）、`research/evidence/runs/2026-11-16-contract-sample-01/pair-2-2-unit.rs:1`（new_reconfigure）。上下文 `research/evidence/runs/2026-11-16-contract-sample-01/pair-2-1-source.rs:49` 对应 `fs/kvfs/src/fs_context.rs:49`，构造体在59–111行；共享 `initialize` 在287–293行。
- **确定事实**：两者已经调用同一 `Self::initialize`，该函数调用 `fs_type.init_context(&mut context)?` 并拒绝缺少 operations 的结果。进入初始化回调前，new 设置 Mount、空 mask、无目标 superblock；new_reconfigure 从既有 superblock 取 fs_type，设置 Reconfigure、传入 mask、有目标。不能把这些初始字段全部说成返回后的不变量：回调接收可变 context，当前文件还有 flags/mask/private 等 setter。
- **上下文边界**：第49–58、81–89行的可睡眠、reclaim 锁约束和发布/加锁前初始化是文档声明，本函数未做运行时上下文检查。第125–133行 get_tree 检查 purpose，第196–197行 super_block 检查目标是否存在；它们是可观察区别，不是“所有初始化均成功”的保证。`new_reconfigure` 构造提案，不等于已完成重配置；第278–280行另有提交操作委托。
- **可评价命题**：确认器能否同时识别“共享初始化已经存在”和“事务目的/目标/掩码来源不同”，拒绝仅凭相同字段装配确认整体互换。若以后验证局部抽取，最小观察为初始化回调次数及其入口字段、错误传播与 operations 缺失检查；需先冻结共同输入映射，不把两组不同参数直接比较为等价或不等价。
- **需提供者声明**：validated request 的验证责任；mount/reconfigure 的允许输入映射；初始化器可修改哪些字段、失败副作用/清理责任；睡眠/reclaim 与锁顺序前提；构造和发布/应用的边界。已有注释可作待确认声明，不能代替真实调用路径证据。字段装配仍可能有局部共享空间，但维护负担和净收益未知。

## pair-4：[88,89] 同步写回与提交所有权

- **原文定位**：`research/evidence/runs/2026-11-16-contract-sample-01/pair-4-1-unit.rs:1`（writeback_cached_folios）、`research/evidence/runs/2026-11-16-contract-sample-01/pair-4-2-unit.rs:1`（submit_cached_ranges）。`research/evidence/runs/2026-11-16-contract-sample-01/pair-4-1-source.rs:147` 对应 `fs/kvfs/src/address_space/writeback.rs:147`；提交文档/实现为161–185行。
- **确定事实**：两者把 visible_len、半开范围和预算/跳过计数的可变引用交给 `i_pages`，但分别调用 `writeback_until` 与 `submit_cache_pages`，**本快照不足以确认二者底层是否共用同一循环**。回调分别接收 `(PageIndex, &[u8], usize)` 与按值 `WritebackBatch<'a>`，后者另有 max_bytes。共同参数准备并不消除回调协议差别；visible_len 返回错误时，`?` 会在进入缓存方法前返回。
- **声明而非完成证据**：第12–16行区分 completed 与 handed-off 计数；第163–170行明确提交预算不是完成预算，文件系统须限制未完成批次、同步 writepages 返回前 drain、保持 inode/mapping 保护并负责先前 I/O；此 helper 不负责记录延迟错误，也不保证非阻塞安全。第142–144行只证明 writepages_control 在调用 ops.writepages 时持有 invalidate 读锁，不能据此证明所有提交调用或异步完成都受该锁保护。第187–209行另有完成前缀接口，其契约不能移植为本对接口的已验证行为。
- **可评价命题**：确认器能否从声明中保留“提交≠完成”和“helper≠完成责任所有者”，拒绝由 `Ok(())` 推出数据已写完、延迟错误已处理或可直接互换。将来最小判别场景是提交接受但完成延后，以及先前提交后出现扫描/提交错误；本轮没有执行，也未验证被调缓存算法。
- **需提供者声明**：回调成功究竟承诺接受还是完成；batch 生命周期、drain/销毁与失败路径责任；预算单位和 max_bytes 边界；保护对象与锁持续时间；sleepable/sync_mode/data_only 的处理责任；延迟错误归属。两 wrapper 本身未读取 sync_mode/data_only，不能升级成整个调用链忽略它们。局部参数准备抽取仍可讨论，但须另证接口成本和维护收益；现有委托不等于不存在任何优化。

## 本轮可交付的判断范围

两对均可评价“提取是否保留责任与条件、是否把委托关系识别正确”，尚不能给全行为等价、优化价值或实际上下文安全标签。pair-4 更适合作为责任声明不被升级为完成事实的下一步控制；pair-2 更适合作为已有共享与入口差异并存的控制。提供者确认、实际配置及下层/调用者证据缺口保留 unknown，不因抽样新或文本相似而升级。
