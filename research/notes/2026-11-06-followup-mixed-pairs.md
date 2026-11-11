# 生产实现与测试支撑：相同字段和接口不等于重复功能

固定提交`7e3ac94431a0dbb376d2fc8d85098deeff1bba09`；本轮仅静态阅读，未修改内核或运行测试，未对Linux作外部核验。

## 1045/1894：nullfs metadata与权限fixture

`fs/kvfs/src/nullfs.rs:68`的NullFsRoot::metadata为固定生产目录生成属性，`:95`起的getattr直接返回它；`fs/kvfs/ut-tests/permission.rs:44`的meta(uid,gid,mode)则用于组合DAC权限测试输入。

| 字段／用途 | nullfs | 权限测试 |
| --- | --- | --- |
| 节点类型 | Directory | RegularFile |
| mode | 固定0555 | 由用例指定 |
| uid/gid | 固定0/0 | 由用例指定 |
| nlink | 2 | 1 |
| block_size／blocks | 4096／0 | 512／1 |
| 共同部分 | device=0、inode=1、size=0、默认rdev、epoch时间 | 同左 |

权限测试从`:67`开始通过不同uid/gid、mode及凭据检查owner/group/other等权限路径。共享Metadata字段名和若干默认值只说明数据形状及初始化惯例重叠，不是两个文件系统实现相同。
现有测试meta已是本地复用点；用生产nullfs默认值再覆盖关键字段既增加生产／测试耦合，又隐藏输入意图。当前没有收益证据支持跨层共享，也不为了复用而扩大已收束的metadata helper。
保留为“字段初始化相似、职责与参数域不同”的对照；不宣称任何更低层数据构造API都没有价值。

## 1135/1800：poll注册策略与测试错误注入

`fs/kvfs/src/pipe.rs:603`按IN注册rd_wait、按OUT注册wr_wait，每步错误通过`?`传播；`fs/kvfs/ut-tests/node_device.rs:141`的CharacterBackend先按reject_registration注入InvalidState，仅对IN注册单个waiters。
真实注册机制已在`task/kpoll/src/registration.rs:179`的PollContext::register中共享：预留owner容量、调用source.register，再把注册项保存到owner。这里只是事件选择和测试策略，不是两份注册管理机制。
`node_device.rs:252`的现有测试明确检查OUT不触发唤醒、IN触发唤醒、readiness切换及注册错误转发。这些是静态预期，本轮未运行，且不在此前metadata的两个模块测试范围内。

最窄的进一步提取只是“某事件位存在时注册某个PollSet”。它不能吸收错误注入，也不能改变两个源的注册顺序或中途失败处理；当前不见足以抵偿新接口的维护需求。
结论为已有公共机制上的短策略包装，保留测试故障注入和独立事件选择，不提出新增helper或整对象合并。

## 证据与工具要求

全文及哈希保存在`research/evidence/runs/2026-11-06-followup-context-02/`。
这两对要求工具分清“同类型字段构造／共同API协议”与“重复维护独立机制”，并显示已有下层复用。它们不是由研究者独立标注的误报真值，也不能用来计算基线precision。
