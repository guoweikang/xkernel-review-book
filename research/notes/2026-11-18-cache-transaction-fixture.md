# 缓存插入事务：补齐真实内核验证入口

## 问题与选择依据

[固定队列续审](2026-11-18-call-subset-continuation.md)保留两项局部共享假设，但没有满足该批“现成验证入口”的门槛。本批不倒写上一批结果，而是单独回答：能否为第一项假设建立有辨别力的真实Dentry测试？缺材料可以补齐，不等于方法失效。

对象按原槽位顺序固定为case-002：`insert_cache`和`cache_lookup_candidate`，源码版本`7e3ac94431a0dbb376d2fc8d85098deeff1bba09`。没有因case-005看起来容易而换对象，没有扩排名。Goodall审议记录为续审run的`steering.txt`；主线程采纳真实内核入口、原版与单负控制的有界方案。另一份128行组合宿主设计保留为未采纳草案，后续`verification-design-kernel.txt`明确收窄，不把设计稿当执行证据。

## 输入与事前冻结

`scripts/preflight_cache_transaction.py`只读核对既有隔离源码，归档到`2026-11-18-cache-transaction-preflight-01`：原source.tar摘要相符，3634个归档文件全部相符，配置相符；QEMU、make、rustup及mkfs存在。另查到1.95.0工具链已安装。输入可用不是测试已经通过。

检索词`insert_cache cache_lookup_candidate kvfs-original`命中97、返回6、省略91，完整查询输出归档。实际回读上一轮删除事务准入、既有`run_kvfs_original_tests.py`、pagecache原版和kvfs原版的协议／报告，以及当前固定源码与测试。未以检索命中代替逐份阅读；外部仓库及未登记资料不在此检索的完整性保证内。

新协议为`research/protocols/cache-transaction-fixture-v1.json`，新run为`2026-11-18-cache-transaction-fixture-01`。六个新增测试、原版／单mutant两个执行格，每格300秒；最多一次编译接入修正，不改断言追通过。fixture、runner、协议、两格源码摘要及配置在`freeze.json`中事前固定。测试附加到既有隔离副本的私有子模块，不改生产仓库，不新增生产接口或重构helper。

## 观测与对照

六个测试覆盖：普通live赢家、PAR_LOOKUP赢家、absent／expired槽位、不可缓存父节点、四种子节点缓存flags、superblock存在／不存在时的保留与驱逐。比较真实Arc／Weak对象身份和原始children map，不用会过滤PAR或删除过期项的lookup接口作oracle。

负控制只在隔离副本的`cache_lookup_candidate`中故意过滤已升级的PAR_LOOKUP赢家。要求新增测试的`par_winner_identity`断言明确失败；超时、编译错误或无关panic不算检测成功。先清除PAR状态并移除表项，再断言，避免构造错误污染后续清理。

该组状态测试不能证明并发线性化、unlock-before-retention时序、额外分配／clone、任意析构或净维护收益。保留String移动／借用、弱项替换清理及guard范围为静态义务。本批没有实现待采用重构，最多能说明新增测试对指定错误有辨别力。

## 实测结果与核验

|执行格|完整测试结果|新增六项|进程状态|
|---|---|---|---|
|原版＋fixture|303通过、0失败|6通过|exit 0，无超时|
|单mutant＋同fixture|302通过、1失败|5通过、PAR赢家项失败|exit 2，无超时|

mutant原日志明确记录`node_dentry.rs:1334: par_winner_identity`断言失败，唯一失败测试为`test_cache_fixture_live_par_winner`；不是编译失败或任意panic。此项目的`unittest::assert!`返回失败状态，不是标准库panic。两个执行格有相同的303个测试名；其余297个已有测试在这一负控制下仍通过，因此不能用“原测试套件整体较大”替代具体覆盖证据。

新增六项内部包含22个顺序状态组合，不是22个独立真实案例；整个内核测试套件可并发运行，但没有为同一缓存构造竞争调度，不能声称已测线性化。没有编译接入修正，没有改变oracle，没有候选helper实现。该结果支持新增测试对这一人工错误的辨别力，不支持所有缓存错误的检出率。

`scripts/check_cache_transaction_fixture.py`核对两格日志摘要、完整测试人口、所有六项、唯一失败、断言对应的实际源码行、单行mutant及冻结输入。原runner的摘要筛选漏收`assert! failed`行，故核验读取完整原日志，保留旧runner不倒改。独立输入审计指出了这一报告边界。

主线程在等待mutant结束的`finally`中通过补丁恢复两个隔离源码文件；复核全部3634个归档文件及配置相符，记录在`verified-results.json`。磁盘／target输出留在隔离构建区，不作为源代码归档；原日志、fixture、输入快照、冻结清单及原／错误两格结果保留在research run中。生产仓库未修改。

本批到此停止，不增mutant或追加排序。下一步只允许针对具体共享边界做静态所有权／锁范围准入，再决定是否有足够价值实现候选；当前已补的入口仍不能覆盖名字分配、clone次数、锁释放时点与任意析构。若helper需要更多状态和间接层，却无可证维护收益，可以拒绝提取，而不是为了正结果继续扩实验。

Rawls在`independent-outcome-audit.txt`独立复核完整两格日志、同303项人口、唯一指定断言、冻结摘要及两个源码文件／配置恢复，结论为LIMITED ADMIT；3634文件全量恢复明确归属于主线程检查，未冒称另跑一遍。Agent复核仍非独立人工金标准。资料目录和book校验通过：259篇研究文档、307页HTML、87项归档摘要检查。
