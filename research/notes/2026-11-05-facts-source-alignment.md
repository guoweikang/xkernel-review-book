# facts 与源码关联：已验证范围和候选发现所缺字段

日期：2026-11-05。阶段 A 的输入核查，不是重复候选实验。
固定源码为 `7e3ac94431a0dbb376d2fc8d85098deeff1bba09`，与 Jenkins 3885 制品 manifest 一致。
保留旧 A1 盘点，不覆盖其历史记录；新增同版本盘点用于后续关联。

## 1. 同版本盘点和单 crate 回查

复用 `scripts/inventory_materials.py`，新结果为
`research/evidence/inventory/2026-11-05-xkernel-ci3885-materials.json`。
该树有 216 份 Cargo manifest，其中 213 份包含 package、3 份虚拟 manifest，解析错误为零；
145 个 package 有专用设计文档、145 个有安全文档、204 个有 rustdoc 文本信号。
这些数量恰与旧盘点相同，不代表文件内容相同，也不是配置内编译覆盖率。

新增只读核查脚本 `scripts/audit_facts_sample.py`，输入归档 manifest、压缩样本与本地 Git 对象。
校验压缩哈希、压缩/解压字节数、记录数、crate 身份及 schema/target；
随后按 manifest.commit 读取源码，记录源码哈希并检查 item 行号是否在文件内。
不读取当前工作树的修改，不运行内核构建。

klazy 的实际结果保存为 `research/evidence/inventory/2026-11-05-klazy-facts-audit.json`：

| 检查 | 结果 | 结论边界 |
| --- | --- | --- |
| JSON 记录 | 424：item 94、call 213、use 88、site 16、ref 11、头尾各 1 | call 包含 202 条普通调用边与 11 条 drop 边，不是执行次数 |
| item 类型 | 44 fn、24 impl、6 mod、5 struct、5 static、5 closure、2 macro、其余 3 | 不代表源码中的所有配置、所有生成结果 |
| 源文件 | 5 个路径均存在于固定 Git 树，94 个 item 行号范围均合法 | 范围合法不证明匹配正确或完整函数提取 |
| 生成项 | 14 个 item 标有 gen | 不能把宏调用位置直接当成独立函数源码 |
| 样本内 item key | 未发现重复 | 不证明全仓、不同依赖版本或不同配置之间唯一 |
| 测试来源 | 包含 `util/klazy/ut-tests/once_unittest.rs` | 不能把此制品视作纯生产代码集合 |

测试来源还可从固定树 `util/klazy/src/once.rs` 的 `#[cfg(unittest)]`
和 `unittest::path_mod_test!` 对应确认。crate 头也包含 `cfg: ["unittest"]`。
仅确认测试代码进入分析，不表示测试已经执行或通过。

源码哈希是本地固定 Git 树的字节哈希，不是 CI 工作区逐文件哈希证明。
未对 213 条调用边逐条做正确性审计；本轮不是调用图精度评估。

## 2. 现有数据能回答哪些问题

| 候选发现需要 | 现有依据 | 缺口及处理 |
| --- | --- | --- |
| 对象属于哪个 crate/mod/impl | crate 头、item.key/parent/path/kind | 使用带快照和配置的身份；不只按名称合并 |
| 对象源码在哪 | file/line/col/end_line，固定 Git 树 | 没有精确结束列/字节范围；整函数分词前需要解析器定位 |
| 对象职责和使用边界 | 固定树 rustdoc、design/security 文档 | facts 不含职责正文；文本是待核对的设计声明，不是自动成立的契约 |
| 类型和接口相似性 | struct fields/variants、类型引用、impl self_ty/trait、fn generic/unsafe | fn 记录没有完整参数/返回签名和 where 约束；需要源码解析或额外语义提取 |
| 使用者与已有能力 | call/ref/use 及部分间接调用来源 | 受配置、过滤和流分析范围限制；无边不是无人使用 |
| 行为、性能及可替换性 | 代码、文档中的线索 | facts 不提供运行频率、耗时、功能等价或抽象后零开销证明 |
| 全仓覆盖 | 源码盘点加配置内事实视图 | 配置外代码、host 工具、宏生成、外部依赖分别登记，不能统一报已覆盖 |

接口字段缺口来自 exporter 源码核查，而不是仅凭 klazy 样本未出现字段推断：
`tools/lints/src/facts_export/items.rs:232` 的 `fn_fields` 只从签名读取 safety，
并导出泛型标志、符号和关联类型/trait 名称，没有输出完整签名。

一个具体定位陷阱：klazy 的 `lazy` 模块 item 位于 `src/lib.rs` 的 `mod lazy;` 声明行，
其实现却在 `src/lazy.rs`。因此 mod 的行范围不能当模块完整内容，必须通过子项或模块解析定位。
同理宏生成项的 place 是用户调用处，不保证是生成定义的文本范围。

## 3. 证据关联规则（研究侧设计，尚未实现索引服务）

1. **分开三种身份。** 源码身份使用仓库、commit、路径和 blob 哈希；
   编译视图使用 target、config_sha256、features/rustflags、工具链和 exporter 摘要；
   item 身份再附所属 crate 制品哈希、crate_id/stem 和局部 key。
2. **不将 key 当永久 ID。** `mod.rs:373` 用 crate 名称加 def path 构造 key；
   `{impl#N}` 会受源码变化影响，且 key 未携带依赖版本。
   跨版本匹配需要单独记录依据和不确定性，不能复用同名字符串直接覆盖旧对象。
3. **跨 crate 边不强行连线。** 调用目标 key 若在候选依赖制品中多义，保留 unresolved/ambiguous；
   必须有依赖身份等证据才能消歧，不能仅凭 callee 名称猜目标。
4. **文档绑定到版本和对象。** 记录文档位置、原文片段/哈希、关联对象及关联方法；
   区分“编译提取事实”“文档声明”“模型推断”。设计文档存在不等于描述正确。
5. **全源码与配置视图并存。** 测试/生成/外部来源先标识，再明确实验是否纳入；
   未编译对象不是不存在，未采集项不是合理独立或没有重复。
6. **先定位后比较。** 行范围只能支持人工跳转和局部上下文；
   没有可靠函数边界时，不能把范围切片默认为 D1/D2 的公平函数输入。

这些规则防止证据混用，不证明功能重叠；真实候选仍要保留相似依据、差异、合理独立理由和未知项。

## 4. 本轮关闭和保留的缺口

- 已关闭：源码盘点版本与制品版本不一致；现有归档样本能否关联到固定源码。
- 已收窄：字段可用性已有 exporter 和实际样本两种依据；精确函数边界和完整签名是明确缺项。
- 保留：完整配置复现、全量制品验证、跨 crate 身份消歧、解析器验证、模型选择、真实案例标注。
- 不要求先补齐所有语义字段才能做低成本候选发现；生产代码/测试代码口径和函数输入边界须先明确。

配置来源的进一步核查见 [配置溯源](2026-11-05-facts-config-provenance.md)。
下一项技术核查是固定少量手工可检查的 Rust 定义形态，验证候选单位能否可靠定位；
这是提取器适配验证，不把它当重复检测效果实验或提前挑选算法成功案例。

## 5. 复查入口

```sh
python3 scripts/inventory_materials.py --repo /root/codes/x-kernel \
  --revision 7e3ac94431a0dbb376d2fc8d85098deeff1bba09 \
  --output research/evidence/inventory/2026-11-05-xkernel-ci3885-materials.json
python3 scripts/audit_facts_sample.py --repo /root/codes/x-kernel \
  --manifest research/evidence/originals/T11-ci-3885/kplat-aarch64-manifest.json \
  --sample research/evidence/originals/T11-ci-3885/klazy-aarch64.jsonl.zst \
  --output research/evidence/inventory/2026-11-05-klazy-facts-audit.json
git -C /root/codes/x-kernel show 7e3ac944:tools/lints/README.md
```

原始制品来源：[Jenkins 3885 facts](https://jenkins.openkylin.top/job/x-kernel-ci-test/3885/artifact/artifacts/facts/)。
字段语义的固定版本来源：`tools/lints/README.md:115`、
`tools/lints/src/facts_export/items.rs:60`、`items.rs:232`、
`tools/lints/src/facts_export/mod.rs:293`、`mod.rs:373`、`tools/lints/src/facts_export/paths.rs:45`。
均按上列完整 SHA 读取，而非滚动主分支。非法压缩帧、manifest 错误记录数的负向检查均被拒绝。
