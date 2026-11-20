# 独占创建：复用已有能力而非新增helper

## 研究问题

固定续审case-005保留了一种不同于缓存helper的假设：`create_exclusive_with`能否直接委托已有`lookup_or_create_with(name, true, create_fn)`，从而移除重复的创建完成协议？这是当前kvfs保留库存的最后一项有界确认，不扩排名、不新造共享接口。

同文件能力复用可提供具体维护决策，却不能替代跨crate的可见性、依赖许可、配置及公共契约证据。选择理由不是它更容易通过，而是它检验“已有能力未被复用”，与上一份新增Cow helper有不同采用条件。

## 事前协议与静态准入

协议`research/protocols/exclusive-delegation-v1.json`固定：唯一委托方案、最多六个新增测试、原版与候选两格各300秒、最多一次编译接入修正。不增加helper、模式参数、锁、公开类型或新的错误策略；失败不改oracle追通过。run为`2026-11-18-exclusive-delegation-01`，输入版本仍为`7e3ac94431a0dbb376d2fc8d85098deeff1bba09`。

主线程与Rawls分别核对两方法、`with_locked_child`、结果枚举和两个positive谓词。状态顺序保持：目录／名称校验 → namespace guard／lookup → 真实inode存在则AlreadyExists → 执行FnOnce → 错误原样传播 → flags仍negative则InvalidInput → clone原候选。inode存在和flags positive不是同一谓词，提案没有替换它们。

成功值适配用完整匹配，将Existing或Created的拥有型payload移出；没有unwrap、panic、新错误或额外clone。固定general实现中exclusive=true成功不会产生Existing；匹配两种payload是避免增加不可达分支策略，不是放宽正entry的错误语义。general方法及非exclusive路径保持逐字不变。

callback所有权不能机械套用先前删除事务反例：这里原版和general方法都把create_fn移入同一个`with_locked_child`调用形态。positive拒绝发生在operation闭包已被调用、create_fn尚未调用时，两形态均在namespace guard仍存在时销毁未调用capture；lookup失败则由helper参数生命周期决定清理次序。适配闭包不拥有用户callback。上述是正常返回路径静态分析，未证明panic／unwind或动态锁时点。

静态审阅仅准许进入限定原／候选比较，不是批准生产采用。原报告及提案摘要分别为`static-admission.txt`、`independent-static-review.txt`和`execution-freeze.json`。

## 六项真实Dentry观察

|测试情形|直接断言|
|---|---|
|已有positive child|AlreadyExists，callback 0次，原缓存对象身份不变|
|negative回调报错|NotFound原样传播，callback 1次、收到原对象|
|回调Ok但未实例化|InvalidInput，仍negative，callback 1次|
|创建成功|callback 1次，返回原candidate，缓存同身份|
|非exclusive已有对象|Existing及原身份，callback 0次|
|非exclusive完成创建|Created及原身份，callback 1次|

测试复用固定原模块的MockFilesystem和真实Dentry，不是完整文件系统I/O；状态／次数预期不通过被委托方法计算。没有增加mutant，也没有测试同一对象的竞争调度或任意Drop观察。测试构造、两格源码和命令均在执行前冻结。

## 检索与执行记录

`create_exclusive_with lookup_or_create_with exclusive-delegation`命中104、返回6、省略98；原输出为`lookup.json`。实际读固定源码1147–1206、枚举与谓词、直接注册测试及上一轮审议，不重开其他候选。第一次输入freeze未包含之后生成的提案，执行freeze才同时绑定提案、完整candidate源码、fixture与runner，二者职责分开。

`scripts/run_frozen_kvfs_cell.py`提供单格执行，改进了旧摘要漏收assert诊断的问题，但最终仍核完整原日志。`scripts/check_exclusive_delegation.py`核对原297测试集合、新增测试、两格完整人口、仅窄方法变化及恢复记录。

## 实测结果与有限结论

|执行格|完整结果|新增六项|退出／超时|
|---|---|---|---|
|原版＋冻结fixture|303通过、0失败|6通过|0／否|
|直接委托＋同fixture|303通过、0失败|6通过|0／否|

两格保留同一297项既有测试和同一6项新增测试。没有编译接入修正，没有更换断言或候选；完整源码差分仅替换`create_exclusive_with`，general方法、其非exclusive分支和锁helper逐字不变。实验结束后在finally中恢复隔离副本，3634份归档源码与配置全部相符。生产仓库未改。

本批支持一个具体的**有限复用候选**：在所测状态与配置、静态检查的正常控制流下，可以用已有一般能力替代窄入口的重复完成逻辑。它不新增helper、类型、锁或模式参数，窄方法非空行由16减为10；代价是调用链多经过已有general方法，并读取拥有型结果枚举适配。行数只是描述，不能替代可读性或维护效果评价。

这与缓存Cow提案暂缓形成不同采用取舍：不是所有相似都合并，也不是出现一次生命周期风险就拒绝全部委托。但两对象不是匹配实验，不据此声称“委托优于提取”的普遍规律。

仍未验证：前置校验错误的新增定向断言、未缓存backend路径、callback改状态后再报错、异常flags／inode组合、竞争调度、任意析构／unwind、代码生成和性能。既有297测试可能涉及部分路径，本批没有以测试名推断其完整覆盖。不把303通过称为整个程序等价证明，不据此宣告已可合入或已有专利点。

完成当前kvfs保留库存后停止新增局部变体；后续转向跨crate真实消费者与提供者的能力、依赖和配置证据，另行冻结，不把本结果当跨crate效果。

Rawls的`independent-outcome-audit.txt`核对完整日志、同测试集合、精确窄方法差分、冻结摘要及两文件／配置恢复，给出有限支持；3634文件全量恢复归属于主线程检查，未冒称重复执行。Goodall的`steering.txt`建议下一批固定最多六条本地依赖边，按事前顺序选第一条能闭合公开能力—真实consumer调用—manifest关系的边，再比较代码与追加同版原生契约的证据覆盖。主线程采纳此方向；选择表、历史机制排除及具体输入仍须在下一批看正文前冻结，不在本批宣称已取得跨crate增量。
