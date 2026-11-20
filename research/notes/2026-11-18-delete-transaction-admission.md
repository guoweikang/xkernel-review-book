# 删除事务：固定既有slot4的确认准入

## 判断

对象仅为已审 `call-subset-review-01/case-004` 的 `unlink_with/rmdir_with`，不是新发现或重新选样。两方法仍重复持锁事务骨架；已有下层共享没有消除这段重复。但**不能直接采纳移动may回调的naive操作闭包**：类型检查失败会改变Drop-bearing捕获的销毁与解锁相对顺序。最初为静态阻断；后续有界宿主见证已观察该差异，见文末，kernel测试仍为0。

最窄边界仍可描述为一个私有 `FnOnce(&VfsInode, &Dentry) -> VfsResult<()>` 删除事务helper；若用wrapper-owned Option保留未调用回调的拥有权，可能保留Drop次序，却增加状态／take／不可达断言与间接层。因此本批只准许有条件的**确认准备**，未证明净收益；若维护成本门槛要求代码更短或更直接，当前证据不足，可如实拒绝提取，不强求合并。

## 身份与证据索引

新run `research/evidence/runs/2026-11-18-delete-transaction-admission-01/` 的 `source-selection.json` 在详细义务分析前冻结两ID、源码范围、完整cfg hints及SHA256。固定提交 `7e3ac94431a0dbb376d2fc8d85098deeff1bba09`。

- unlink ID `43f18f21cc18955475ef4404ef1761de33e5c453a5c1a6fa43f83da380c546af`，原 `fs/kvfs/src/node/dentry.rs:1214–1236`，snippet SHA256 `0a952a3c053a8c670045baf98be1f7acc765b7dc69c7451a62b03764283bb7e9`。
- rmdir ID `fbe1d876173ef6a46419d8bd9e6e989e4e6a27596f41e170db96e4dcf6ab4cb1`，同文件`:1247–1269`，snippet SHA256 `3655389bd0cb89991cfd65f291e67da03e8fbd7d856dd609c2d7e3c363d8c39d`。
- 两份完整源都为SHA256 `5320914efdbd2c5a70ccd8d8ad04c8654c85514ef55490d8da30019d351fc6d7`；归档在 `research/evidence/runs/2026-11-18-call-subset-review-01/reviewer/case-004/{left,right}-source.rs`。snippet按各自range逐字重建通过，original_range含pub(crate)前缀差异，不能混用两个起点。
- 两方法direct/ancestor attributes为空、非nested、test_path_hint=false、cfg=not_evaluated；不据此称已验证生产配置。附近`:1209`／`:1242` 的cfg(unittest)仅门控便捷unlink/rmdir wrapper，不是目标with方法的cfg。

`evidence.json` 保存十份同版原件完整hash及带精确原行号的片段，ID为D(dentry)、I(inode)、M(mount)、S(super_block)、T(node_dentry测试)、L(lib)、C(kvfs Cargo)、R(ksync rwlock)、G(design)、W(root Cargo)。D/I/M/S/T/L与原sources.zip相应成员逐字相同；C/R/G/W从同一固定Git对象只读取得。以下引用均指原路径原行号，不能解释成当前HEAD。

## 必须保持的顺序和失败边界

1. **前置顺序**：父as_dir先于verify_child_name，再取得parent inode Arc。非目录父返回NotADirectory，即使name也非法；name空、dot、dotdot、slash或NUL为InvalidInput，过长为NameTooLong。证据D1218/D1251、D415、D764。
2. **锁与对象身份**：parent exclusive namespace guard先建立；在其内部positive lookup，再取victim inode Arc；Arc::ptr_eq自别名拒绝先于victim锁，返回InvalidInput；随后victim exclusive guard。两Arc和两guard须由同一helper栈帧持有直到操作和成功清理结束，不返回“准备好的victim”而提前释放guard。D1220–1227、D1253–1260；I2180–2185显示实际为ksync RwLock，非kspin锁。
3. **正lookup与副作用**：lookup错误直接传播；负dentry转换NotFound（D1138）。lookup_locked可能建立／替换／撤销缓存候选、调用后端lookup并释放lookup_mutex（D1073–1134）。所以失败路径只能说不执行本删除函数的显式成功清理，不能说无任何缓存副作用或事务回滚。
4. **两操作必要差异**：unlink在两锁下拒绝目录IsADirectory；rmdir拒绝非目录NotADirectory。类型检查必须先于may、may恰好一次且先于对应backend；不得交换成rmdir→unlink或用公共children计数判空。D1228–1232、D1261–1265。rmdir emptiness由FS负责，D1238–1241；默认InodeDirOperations::rmdir虽委托unlink（I222），override仍可不同，不能消除该分派。
5. **成功提交边界**：policy Err跳过backend和显式清理；backend Err跳过mark/forget，原错误保留。backend Ok之后mark_unlinked，再forget_cache_entry，仍在双namespace guard内。D1231–1235、D1264–1268。不是完整ACID事务，也无新panic保证。
6. **隐藏的location锁边界**：VfsInode::{unlink,rmdir}各自先lock_location，构造LockedDentry后调用目录操作（I2285–2295）。该内层guard随调用结束而释放，随后mark_unlinked才获取location write（D705）。不能把LockedDentry提到helper长期保存，否则改变锁生存期甚至阻塞自己；helper只拥有原两namespace guard。
7. **cleanup具体含义**：mark仅置location.is_unlinked=true，不直接抹掉inode。forget按name删除父children映射，再superblock uncache；若移除对象是正目录，递归forget其缓存子项（D875–897、D1382）。S1186的uncache移除dcache强引用但不撤销外部引用；不得把这一逻辑重新发明成简单map.remove，亦不得额外清理失败路径。
8. **上层回调不是纯谓词**：Mount回调还做权限、sticky、mountpoint检查，并捕获RemovedEntry及删除前nlink；unlink另有trailing-slash差异（M1630–1667、M1675–1700）。不得移到锁外、重复调用或重做一次可能不同的lookup。现代码getattr失败有缓存fallback，不能按邻近陈旧注释误读成失败必然拒绝删除；本批不修改该政策。
9. **析构可观察性**：通常返回时victim guard先于parent guard释放；未调用FnOnce参数在原函数局部guard退出后销毁。naive helper操作闭包若按值捕获may，在类型失败时它已经被调用，未执行的may捕获会随操作闭包退出而先销毁，此时helper双guard仍活跃。Drop可以观察锁状态／执行代码，故不能无条件等价。需单独宿主原/naive见证、再核候选借用持有的版本；不能用普通无Drop闭包测试掩盖。

## 已共享什么，新增边界是什么

verify_child_name、lookup_positive_locked、mark_unlinked、forget_cache_entry已经共享。`with_locked_child`（D1147）共享父锁与可负lookup，主要用于create；它不持victim锁、不拒绝负候选、不执行成功删除清理，不能宣称这对已完全委托。

最窄helper复制且集中两份相同的validation→parent lock→positive lookup→alias check→victim lock→operation callback→mark→forget序列。现有两个wrapper各自保留type check→may→选定backend这一整段，不加bool模式、公共trait或泛化namespace框架。不直接复用with_locked_child，因为其callback不提供已固定parent inode、lookup语义也不同；为共用而改其接口会扩大本次范围。

这是同模块**尚未集中实现的事务顺序**，而非独立新能力或相互无关的两个后端。是否值得额外一层闭包必须以实际差分、Drop维护负担及可读性门槛判断；当前不承诺LOC减少。

## 未来同测试确认矩阵：未执行

宿主只适合验证研究副本的控制流／仪器化guard与闭包capture Drop顺序，不能代替实际ksync、调度、FS后端或内核配置。原/naive Drop见证应固定type mismatch及事件顺序；若扩为Option候选须另标其设计成本，并保留naive负结果。

内核同fixture原/候选/固定权限忽略mutant应覆盖：父非目录且name非法优先级、bad/long name、lookup Err和negative、parent/victim别名、两种type mismatch、policy拒绝、backend拒绝、unlink成功、rmdir成功及缓存子项清理。每项分别观测精确错误、callback对象身份、计数／先后、mark和父cache；对递归清理增加实际victim子cache及superblock可见性断言，不仅建立子项。

已有入口T683验证rmdir backend选择及父cache移除；T704验证policy拒绝与对象身份、backend0、cache保留；T851验证自别名。T317有可复用backend计数／失败控制。它们并未证明两namespace锁在每个时点都被实际观察到；当前API只有blocking namespace accessor，不能同线程重入它冒充非阻塞测试，R49–55明确重入panic条件。主线程可使用既有kernel harness测实际调用链，同时将持锁全时域与并发交错保留为缺口。

配置边界：L11为no_std，L109使用ksync；C11–38依赖内核任务等，不是现成独立host库。G114–135说明ut-tests通过cfg(unittest)挂到私有父模块，dentry末行1657为path_mod_test；host只有独立path测试，不是dentry删除测试。root edition为2024且承认cfg(unittest)，不等于任一目标已编译。源码准入阶段没有构建；后续仅运行文末独立宿主见证的两次rustc，没有cargo、make或QEMU。

## 过程与后续状态

检索 `research_lookup.py unlink_with rmdir_with delete-transaction --limit 6` 当前115命中、返回6、省略109；读旧review-b及固定原件，而非把旧AI评论当gold。后备优先级由Goodall `multirecord-route-steering-01/decision.txt`处理，本笔记不研究Aroma/PAM或重开前端。

主线程随后授权独立 `delete-transaction-confirmation-01` 的准备：复用既有隔离kvfs/QEMU流程，先解决Drop条件、冻结原件/候选/单mutant/同fixture；等待主线程读readiness后才执行。既有source.tar/.config、QEMU和构建缓存路径已发现，但可运行性尚未实测。这里的准入产物只包含来源、义务、风险与计划；不把后续准备或静态推导登记为功能等价。

## 后续Drop门槛：已执行反例，kernel准备暂停

主线程明确将优先级收窄为小型原/naive见证，停止kernel三格准备。`research/evidence/runs/2026-11-18-delete-transaction-confirmation-01/protocol.json`在见证实现和执行前冻结三场景：type mismatch、callbackErr、success；原/naive各一，debug与opt各执行一次。`witness.rs`保留精确所有权形状：原FnOnce为函数参数，naive将其move进被helper调用的操作闭包。两guard由仪器化RAII对象代替，捕获值自行实现Drop；没有显式drop(may)人为制造次序。

两种优化级别均得到：类型失败同为WrongType且无may/backend调用；原版事件为 `parent_lock → victim_lock → type_check → victim_unlock → parent_unlock → may_drop`，naive为 `parent_lock → victim_lock → type_check → may_drop → victim_unlock → parent_unlock`。callbackErr均PermissionDenied，may_call及may_drop后解锁，未执行backend或cleanup；success均Ok，may_call／may_drop／backend／mark／forget之后解锁。两控制不抹除类型失败反例，也不证明其他输入等价。

`results.json`的passed表示匹配事前事件预期，**不是候选通过**。该观察否决naive形状对Drop-bearing FnOnce的无条件等价主张；不是实际ksync并发测试、生产缺陷或所有真实调用方都有可观察Drop的断言。2次编译、2次执行、12条场景/形状/优化观测，0修复，0内核运行。完整stdout/stderr、版本、输入hash及二进制hash均保存；debug/opt原始输出一致。

本轮停止。Option只保留为先前提出但未实现／未测试／未准入的复杂性取舍；没有新候选、kernel fixture或QEMU脚本。最终准备结论是先拒绝naive直接提取，而不是继续建设基础设施迫使候选成功。
