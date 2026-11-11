# 文档top20源码核查：新增候选不等于语义召回提升

日期：2026-11-09。范围：冻结的 `2026-11-09-doc-tfidf-01/review-queue.json` 全20对，未换样本或调整排序。固定源码提交 `7e3ac94431a0dbb376d2fc8d85098deeff1bba09`。单个AI研究助手静态审阅，未经独立人工复核，不作真值、精确率、召回率或收益标签。

## 1. 最重要的混杂因素：候选门槛不同

20对中仅rank3两端满足既有SCC的65-token下限，也恰是与旧156对清单重叠的一对。其余19对的两个端点均少于65 token。旧基线从未对这些短函数进行同范围检测，不能把这些输出称为它的语义漏检，更不能用19个新增候选宣称文档路线更优。

这并不证明文档没有价值：文档可以把短包装和跨层接口联系起来，但价值须通过共同范围、预算和标签下的比较建立。当前也不能以“短”直接排除优化机会。

## 2. 全队列审阅结果

以下分组是本轮方便汇总的主解释，不是互斥的理论分类。带有边界差异的代码也可能包含可共享片段。

| 主解释 | 数量／rank | 源码证据与决策 |
| --- | --- | --- |
| 配置互斥版本 | 2：1、5 | SpinLock／SpinRwLock的new受stats和not(stats)控制；启用stats的版本已有new_with_stats委托。不能当作同配置并存实现，也不据此断言跨配置绝无共享空间 |
| 角色或契约差异 | 7：2、6、9、10、11、13、19 | 已持锁视图与自行加锁、替换权限与替换类型、不同Guard资源效果、构建态普通flags与共享态原子flags、共享与独占借用 |
| 已有委托 | 6：3、7、16、17、18、20 | 默认构造参数包装、dentry兼容入口、文件到AddressSpace写回、dentry到inode downcast。rank3还存在少量可讨论的包装重复，但核心已共享 |
| 小片段重叠，收益未知 | 5：4、8、12、14、15 | 两个接口相同默认NotATty；WriteBeginRequest／WriteEndRequest共享范围字段及访问器，但请求阶段和copied状态不同 |

没有确认新的净收益重构机会，不等于给20对全部判为误报。检测“功能相关”“实现重叠”“值得重构”是不同任务，此轮尚没有适用于precision计算的独立标签。

## 3. 三个能指导下一项实验的具体失败模式

### 词袋丢失参数角色

rank6的两段文档分别描述“替换权限、保持类型”与“替换类型、保持权限”。当前词袋表示的cosine为1，但代码分别应用权限掩码和类型位移。相同词集合不表达谁改变、谁保持。这个例子支持以后比较词序／契约字段表示，但不能用它调参后再拿它证明独立效果。

### 相同目的掩盖已有复用

rank18的VfsFile::writeback_mapping_range调用mapping().writepages_range；mapping返回`Arc<AddressSpace>`引用，而匹配的另一端正是AddressSpace::writepages_range。rank20也沿Dentry::vfs_inode返回`Arc<VfsInode>`后调用downcast。源码与类型签名支持已有委托，不是仅凭同名猜测调用边。此处未验证全程序调用图、并发行为或调用可达性。

### 短包装的真实含义在类型与上下文

rank10的两个new正文相同，但Self分别代表IrqSave和NoPreemptIrqSave，后者还管理抢占；对应BaseGuard::acquire/release定义了不同效果和顺序。rank2的LockedDentry已持有location读guard，普通Dentry则自行读锁。不能仅凭文档和函数体就建议互相替换。

上述上下文来自原归档的 `task/kspin/src/guard/types.rs`、`task/kspin/src/lock.rs`、`task/kspin/src/rwlock.rs`、`fs/kvfs/src/node/dentry.rs`、`fs/kvfs/src/file.rs`、`fs/kvfs/src/address_space/operations.rs`、`util/klazy/src/once.rs`。来源是已有sources.zip，而非当前工作树；逐对函数范围、源文与哈希保存到本轮reviews.json。

## 4. 固化产物与核验边界

- 逐对判断：`research/protocols/doc-tfidf-review-v1.json`。
- 连接检查脚本：`scripts/check_doc_tfidf_review.py`。
- 运行输出：`research/evidence/runs/2026-11-09-doc-tfidf-review-01/`。

脚本验证原队列哈希、源码归档及函数片段哈希，按对象ID连接既有token记录，检查每个rank恰好一次。缺项、重复项和非法结论类型三个负对照通过。它验证数据连接和记录结构，不验证自然语言判断是否正确；token数量沿用原实验，并非本轮重分词。

原候选队列不覆盖，历史SCC清单不改写。2026-11-11写稿时按完整对象ID复核并更正：rank3与SCC全体156对重叠，但不在原已审阅18对中；两批已审阅配对交集为0，合计38个不同配对。它们仍不是38个独立随机样本，可能共享函数或主题。此前将全体候选重叠误当已审阅集合重叠的文字判断撤回。未编写内核补丁、运行性能测试或行为实验。

## 5. 下一步的决策

先建立同范围对照：保持当前原始运行不变，在另外冻结的协议中让token路线和文档路线面对相同的函数集合，显式处理短函数门槛、零文档及相同审阅预算，再谈候选增益。不能事后降低旧SCC门槛并覆盖原结果。

此外，把本轮暴露的已有委托、词序角色和配置／类型上下文作为开发失败清单，选择一个机制做后续扩展；不同时开发多个复杂模型。这20对只供机制设计和回归，不作为新方法独立测试集。对WriteBegin/End公共范围抽象暂不写补丁，除非出现明确维护负担或可测收益假设，避免再陷入微小getter重构。
