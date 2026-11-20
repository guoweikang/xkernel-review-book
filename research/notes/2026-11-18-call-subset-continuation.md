# 固定发现预算的续审：历史暴露与剩余候选

## 研究问题与固定边界

在429函数的原词元／调用集合top20中，排除已审对象和已关闭机制后，是否仍有值得确认的局部共享实现？这是开发队列续审，不重新训练或排序，不是方法准确率／召回率评测。

协议`research/protocols/call-subset-continuation-v1.json`在读新片段前冻结：两路各最多3个独有槽位、交替选择、原排序、仅top20、不足不补。Weak收集、删除事务及格式化的原端点列为已关闭机制；不为更好结果更换样本。未审pair不代表未见函数、文件或语义机制。

## 排除审计拦截了四对历史暴露

初选`2026-11-18-call-subset-continuation-01`仅继承44对排除及上一批6对，得到6槽。独立Agent检查另三份具名登记：LDA38、共同预算40、RRF43；合并原有登记后共有103对历史暴露。RRF只是准备过材料，不改称已完成评审，但本批保守排除。

初选中一对构造函数和parent/file_name已有审读；另两对在RRF材料中准备过。四对都在源码包装／阅读前被拦截。保留旧selection、freeze、runner，增加`amendment.json`，最终名单重新冻结在`2026-11-18-call-subset-continuation-02`；不是看过不利结果后换样本。

历史工件的创建时`reviewed=0`不等于之后仍未审。审计对照了后续笔记／登记状态，记录详见`2026-11-18-call-subset-continuation-audit-01/exclusion-input.json`和`decision.txt`。它只覆盖五份具名注册表，并非穷尽所有会话或隐含阅读历史。

## 最终固定名单

|槽位|来源／原排名|对象|
|---|---|---|
|1|调用9|symlink／file的address-space构造|
|2|词元16|insert_cache／cache_lookup_candidate|
|3|调用10|initialize／initialize_with_private|
|4|词元17|mknod_with_mode／create_with_mode|
|5|调用15|create_exclusive_with／lookup_or_create_with|
|6|词元19|Mount::mknod／create|

均为同文件pair且同属kvfs；同项目、同文件集中性没有被过滤掉或包装成独立样本。列表的语义判断尚需源码，名称相似既可能是独立重复，也可能只是已有委托。

`scripts/prepare_call_subset_continuation.py`分select和package两步，冻结协议、排除来源摘要、原排名、语料身份及选择结果。包中只提供源码、位置与配置线索，不含方法／分数／排名；底层源码固定`7e3ac94431a0dbb376d2fc8d85098deeff1bba09`，不与当前HEAD混合。

`scripts/check_call_subset_continuation.py`核对最终6槽与独立审计的重算结果、12个成员的完整源／片段摘要、UTF8字节切片及原行号。检查全部通过；这证明包与冻结输入对应，不证明代码行为或审阅结论正确。

## 审读范围与证据层次

两个fresh、非fork Agent分别读槽位1–3与4–6；最多15分钟／pair，可读取同版完整所在文件和直接相关helper／测试，记录实际阅读范围。任务范围、ID及输出位置见最终run的`dispatch.json`；其中是指令摘要，不冒充逐字提示词归档。

要求分辨已有共享、必要差异、可确认候选和证据不足。候选必须附带一项会改变采用决定的行为义务及现成验证入口，不能只建议“可以再抽helper”。不运行测试／编译、不改生产、不生成候选补丁。隐藏排名不是科学盲评，Agent意见不是独立人工金标准。

审读已完成，原始报告分别保留为最终run的`review-a.txt`与`review-b.txt`。报告中的confirmation_candidate仅表示待确认假设，不等于通过本批准入门槛。

|槽位|源码审读结果|本批准入|
|---|---|---|
|1|已有共同address-space构造；类型约束和操作表差异必要|不进入确认|
|2|children map的live-winner／weak-insert事务局部重叠|缺完整验证入口，保留假设|
|3|已委托initialize_inner|不进入确认|
|4|操作分派形状相似，但create与mknod契约不同|不进入确认|
|5|exclusive创建可尝试委托已有lookup_or_create_with|缺已核实验证入口，保留假设|
|6|已委托create_exclusive_with，差异在操作与权限策略|不进入确认|

槽位2的义务是保留原子竞争者选择、过期弱项替换、PAR_LOOKUP赢家和解锁后保留强引用的次序。已有snapshot过滤测试只覆盖相邻行为，不足以确认整个义务。槽位5的义务是exclusive创建协议等价，包括回调次数／锁范围、错误顺序和返回对象身份；审读者没有读取外部测试，不能将“未找到”写成“仓库没有测试”。

因此结果为3对已有共享、1对必要差异、2对待验证假设、0对满足本批既定确认准入。按协议关闭这轮top20扩审，不扩排名或调权。零准入不说明相似方法无效，也不证明两项假设不能优化；尤其“缺现成验证材料”是可补齐条件，不应成为永久否决。下一步应另行冻结测试构造／验证准入，不能补完后倒写本轮成功数。

主线程回读槽位2完整文件的831–845及933–949行，确认两处独立事务与解锁位置；未执行内核、并发或重构收益测试。两名Agent各约数分钟的开发审读不是独立人工标注，不据6对报告precision／recall或方法优劣。

## 检索记录

`research_lookup.py call-subset continuation reviewed --limit 4`命中232、返回4、省略228。实际回读原协议、排除登记、上一轮源码审读状态、Drop确认后的停止门槛及发现专题。原lookup保存于初选run，审计新增检索与出处单独归档。检索命中不保证全历史不遗漏；本批四对更正正是资料登记需要交叉核查的实例。
