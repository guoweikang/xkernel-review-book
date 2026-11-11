# R008：对齐算术的复用边界

## 问题与结论

固定X-Kernel版本：`7e3ac94431a0dbb376d2fc8d85098deeff1bba09`。
本次是源码及声明依赖筛查，不是运行实验或完整生态API调查。

三个局部实现具有共同算术骨架，但现有`memaddr::align_up`不是保持错误契约的直接替代品。
当前决定是**拒绝直接替换，保留低优先级优化候选**，不是判定为合理独立的最终真值。
新增fallible公共API、使用标准库能力、保留局部实现仍是不同备选，尚无净收益比较。

## 调用前提与契约

| 实现 | 输入来源及类型 | 失败处理 | 已读证据 |
| --- | --- | --- | --- |
| kcpu_slot局部align_up | usize；alloc从`mem::align_of::<T>()`取得align，传给reserve | checked_add失败为None，reserve转Err，alloc转NoSpace | dynamic.rs:90、104、138、267 |
| kernel-elf-loader局部align_up | u64；已读调用用0x1000 | 非法align与溢出返回不同错误字符串 | lib.rs:48、228 |
| xkmake局部align_up | usize；两个生产调用均用4 | 溢出为None，调用方添加上下文错误 | image_metadata.rs:241、366、426 |
| memaddr公共ceil_align / align_up别名 | usize；函数内assert非零二次幂 | 溢出panic，不返回Option或Result | mm/memaddr/src/lib.rs:35、51、109 |

不能仅因局部函数未显式检查align就认定存在缺陷：需检查调用来源。这里的常量和类型对齐来源，与允许任意外部align的公共API不是同一输入契约。
反过来，合法align也不证明加法永不溢出。memaddr中的panic理由注释不能自动转移为ELF解析或元数据处理的前提证明。
例如usize::MAX按4向上取整：从源码可推导Option实现返回None，而memaddr走panic分支；本轮未执行该输入。
u64也不能无条件转成usize：即使某个目标位宽相同，也不证明所有支持目标及输入域相同。

## 声明依赖边界

三份消费者Cargo.toml均无直接memaddr依赖；kernel-elf-loader没有dependencies段。
memaddr是no_std库，声明依赖unittest；xkmake是host构建工具，已有其他内部库依赖。
这些事实只说明引入共享库需要审查依赖，不证明存在依赖环、构建失败或可测的编译成本。
host与no_std并非天然不兼容；必须解析实际目标、配置和传递依赖后再判断。

## 方案及证据门槛

| 方案 | 当前决定 | 升级研究所需证据 |
| --- | --- | --- |
| 直接调用现有memaddr::align_up | 拒绝无条件替换 | 若只替换受限路径，须证明所有支持输入均不溢出且失败策略允许panic |
| 在既有基础库扩展checked API | 可研究，暂不实现 | 明确库归属、usize/u64处理、错误适配、解析依赖和实际维护收益 |
| 采用core整数公共能力 | 未核查，不作推荐 | 固定项目工具链，核查API稳定性、零/非二次幂/溢出语义，再比较生成代码和可读性 |
| 保留局部实现 | 当前不改代码 | 不是最优性结论；后续若发现同步修复、实现漂移等实际负担，再重新排序 |

目前没有记录到这三段之间的共同缺陷修复或重复维护成本，故不为数行相似算术先创建泛型框架或新crate。
停止继续增加溢出反例：静态证据已经足以阻止直接替换；更多相同性质测试不会解决归属与收益问题。

## 固化到候选审查流程

后续每条复用建议至少提交：共同机制、调用可达输入、错误/副作用契约、类型及配置域、已有公共能力、依赖增量、收益依据。
缺少其中关键项时输出“候选／待核查”及具体缺口，不输出“应合并”。
直接替换被拒绝与所有抽象方案不可行应分别记录；不要把前者作为后者的负例标签。
这是本轮形成的工作协议，不是新颖性或检测效果已经验证的方法。

## 证据与复跑

原三个实现全文见`research/evidence/runs/2026-11-05-alignment-seed-01/`。
公共API和四份manifest见`research/evidence/runs/2026-11-05-alignment-context-01/`。

```sh
python3 scripts/capture_pilot_seeds.py --repo /root/codes/x-kernel \
  --protocol research/protocols/alignment-context-v1.json \
  --output /tmp/alignment-context-fresh
```

输出目录必须尚不存在。脚本核验固定提交、唯一锚点和文件哈希，不验证语义标签。
本轮未修改内核、执行内核测试、解析Cargo依赖或测量性能。
下一步对现有案例统一做证据缺口审计，选择能改变优化决策的补证任务；不继续按发现一个差异就追加一个探针的方式推进。
