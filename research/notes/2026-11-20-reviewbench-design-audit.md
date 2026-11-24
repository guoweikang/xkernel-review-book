# ReviewBench：设计议题发现与标签来源审计

日期：2026-11-20。**新目标仅为 issue discovery：先真实 golden PR，后考虑 xkernel；不延续旧内核实验。** 本批不调用模型、不运行评测或上游脚本、不修改上游，不改 catalog/PROGRESS。只读本地 clone 的数据、文档与元数据；没有下载 PR 完整讨论、patch 或修复提交，故不能独立确认设计建议已被接受。

## 1. 固定输入与结论

- 原件根：`/tmp/reviewbench-study-20261120`（下文 `RB/`），LastOstra/ReviewBench，HEAD `101b6d6bb612a5befee3ec46974cd3b4587c7e44`；初查 `git status --short` 无输出。
- 已读 book `AGENTS.md`、research-execution skill、PROGRESS；旧进度方向由本次任务明确取代。执行 `research_lookup.py ReviewBench --limit 3`：0 命中，不用旧笔记代替本次原件。
- 完整解析 `golden-rust/*.json` 全部83条 finding 的标签、来源和 justification，并逐条审读 justification；设计候选进一步读 message/source。解析通用 golden 全量统计，重点打开其中 Rust 任务的设计类别及下列具体 finding。**通用 golden 全4632条未做逐条语义审读。**
- `golden-rust` 不是纯设计问题集：其准入规范明确排除风格、命名、文档和设计偏好，保留 correctness/contract/soundness。最适合本目标的是“有具体行为后果的职责/API边界问题”，不能把全部83条都改叫设计标签。
- 通用 `golden/` 的 Rust 子集确有更直接的重复与模块职责候选，但多由模型提出；`tp` 是数据集判定，不等于 PR 作者采纳。**本批独立确认的 accepted design labels 数量为0；这是核验状态，不是声称真实世界没有已接受建议。**

## 2. 数据人口、ID及两种标签口径

| 数据入口 | 任务数 | finding数 | 原始标签与用途 |
|---|---:|---:|---|
| `RB/corpus/rust-set.json` → `golden-rust/` | 57个head快照，52个不同PR，8个repo | 83 | 全部 `tp`、`human_review`、83个不同评论URL；correctness75 / reliability8；high29 / medium51 / low3 |
| `RB/corpus/manifest.json` → `golden/` | 219 | 4632 | tp2623 / fp2009；混合生产者，不是全部人工评论 |
| 上行 manifest 的 `language == "Rust"` | 11 | 215 | tp115 / fp100；不是上面的57题集 |
| `RB/corpus/test/test.json`、`findings.json` | 25 | 后者按25任务映射 | 通用219题的展示子集；不能与57题合并计数 |
| `RB/findings-rust/` | 57文件 | 133 | producer=`pr-agent`，无tp/fp、category；候选输出，不是golden扩充或accepted证据 |

57题按repo：asterinas22、Theseus18、rust-lang/rust11、redox-os/termion2，liner/sodium/tfs/users各1。按 `(repo, PR, head)` 而非只按PR编号计数，尤其Theseus1031、917、1019及Asterinas2388存在多快照，不能当独立 held-out family。

通用全量类别（tp/fp）：correctness1068/617、reliability362/329、maintainability365/366、api-architecture81/46、testing223/150、documentation306/212、performance63/60、security98/210、accessibility57/7、other0/12。**maintainability并不自动等于职责/重复问题，api-architecture也包含普通兼容性bug。**

通用Rust215条类别（tp/fp）：correctness34/32、reliability19/13、maintainability24/16、api-architecture8/7、testing13/4、documentation8/19、performance2/4、security7/5。其中设计类别名粗筛55条（maintainability40 + api-architecture15），32tp/23fp；这不是55条确认设计缺陷。

### ID约定

文件给出 `pr_key`，但 finding **没有独立 `id` 字段**。以下 `task#F1` 表示 `golden[-rust]/<task>.json` 的第一条，即 JSON pointer `/findings/0`；F2对应`/findings/1`。这是本审计定位约定，不虚构上游ID。人工 finding 同时给出准确 `discussion_r...` 外部评论ID；完整URL保存在该finding的`source.url`。八位head只是task key的一部分，完整base/head以对应manifest/golden `pr`对象为准。

## 3. golden-rust 全83条的研究者二次筛分

**本节是研究者导航标签，不是上游确认的设计分类。** 互斥口径：A=评论明确涉及能力复用、实体归属、类型/API/安全责任边界；B=架构/抽象相关后果，但当前finding主要是行为错误，未充分给出独立设计义务；C=其余普通缺陷/局部修正。先按A清单，再B清单，余下全部为C；不因发现同类bug就推断应抽象共享。

| 组 | finding数 | 涉及任务数 | 含义 |
|---|---:|---:|---|
| A：明确设计相关、但同时有缺陷/契约后果 | 19 | 15 | 复用3，职责归属1，抽象/API15 |
| B：设计相邻、保留为次级导航 | 4 | 4 | 不提升为纯设计正例 |
| C：其余普通缺陷/局部修正 | 60 | 不作互斥任务计数 | 同一任务可以同时含A和C，任务数不可简单相加 |
| 总计 | 83 | 57 | 上游类别仍是75correctness+8reliability |

### A：完整定位清单（19条）

| task / finding | 评论ID | 研究者归类与具体问题；不是采纳确认 |
|---|---|---|
| `asterinas_asterinas_2342-e1163681#F1` | `2299580220` | **职责**：`FileTable::set_stdio`依赖空表上下文；评论建议移至唯一调用者所在父模块的`init_in_first_process`，避免通用type方法暗藏初始化前提。最贴近“放对type/mod”。 |
| `asterinas_asterinas_2705-3ae42372#F1` | `2601641995` | **复用**：使用已有`will_ignore`而非局部只判断`SigAction::Ign`，遗漏默认忽略行为；不是单纯重复行数。 |
| `rust-lang_rust_129838-ab840e05#F1` | `1795056092` | **复用**：`Box::into_raw`替代as_mut_ptr再forget/move，保留指针所有权契约；局部机制复用，非通用DRY案例。 |
| `theseus-os_Theseus_1027-e71c4173#F2` | `1284819268` | **复用**：避免无映射/边界证明的整页引用；评论提出`MappedPages::as_slice()`，justification另称后来用mod_mgmt安全API。提议与最终实现身份仍需核对，不能混称同一方案。 |
| `asterinas_asterinas_1928-a56d1ffe#F1` | `2011521104` | API：safe转换trait不足以直接证明AtomicModeGuard；blanket unsafe impl跳过真实guard取得。 |
| `asterinas_asterinas_1937-a9c63339#F1` | `2033149546` | API/表示：RCU内部过早存储`Ref<'a>`，评论要求裸指针内部表示、在借用接口处延后构造引用。 |
| `asterinas_asterinas_1937-a9c63339#F2` | `2033143404` | unsafe契约：NonNullPtr::into_raw宣称一直可借用，与Weak目标可能销毁不相容。不是一般措辞润色。 |
| `asterinas_asterinas_3339-8cfed512#F1` | `3379140710` | API：convert_gpa_range暴露safe入口却要求调用者满足TDX转换安全条件。 |
| `rust-lang_rust_142098-fb17077d#F1` | `2179205158` | API：普通_fmt函数把buffer容量安全前提转嫁给caller却未标unsafe。 |
| `rust-lang_rust_142098-fb17077d#F2` | `2179210596` | 上一问题的u128版本；独立位置，但同一家族，不是第二种机制。 |
| `rust-lang_rust_159130-c257aefd#F1` | `3676975528` | API：enc_16lsd使用assert_unchecked却以safe入口接受未经证明的前提。 |
| `rust-lang_rust_165681-1f37fda1#F1` | `4523383007` | unsafe trait契约：返回searcher的haystack必须与传入slice一致，保证对象需要明确。 |
| `rust-lang_rust_165681-1f37fda1#F2` | `4523903013` | unsafe trait责任：guarantees/requirements及默认方法分别由谁保证，不能倒置。 |
| `theseus-os_Theseus_813-26b8912a#F1` | `1156515192` | 接口：DeadlockPrevention无状态enter/exit不能传播嵌套抢占guard；类型接口承载状态的职责不足。 |
| `theseus-os_Theseus_813-26b8912a#F2` | `1156508134` | 同接口的IRQ嵌套问题；与F1应按family绑定。 |
| `theseus-os_Theseus_890-d3a057a5#F1` | `1142580100` | type边界：公开CpuId构造器破坏可信CPU身份；justification称构造迁到MpidrValue，待原讨论/修复核验。 |
| `theseus-os_Theseus_917-e0310316#F1` | `1159159657` | unsafe责任：安全macro掩盖unsafe trait实现义务，使字段/类型错配无需unsafe语法即可发生。 |
| `theseus-os_Theseus_958-fcb9b8a6#F3` | `1204886339` | API返回建模：PCI无中断的0xFF不能当InterruptNumber；评论建议Option及pin信息类型。 |
| `theseus-os_Theseus_985-d275d754#F1` | `1244168989` | 生命周期抽象：优先级继承撤销只返回闭包，unwind不执行；建议Drop guard承载恢复责任。 |

精确代码位置由每条JSON的file/start_line/end_line提供。例如2342为`kernel/src/fs/file_table.rs:55–60`；2705 F1为`kernel/src/syscall/rt_sigtimedwait.rs:77–78`；813 F1/F2分别为`kernel/sync_preemption/src/lib.rs:14–23`和`libs/sync_irq/src/lib.rs:14–24`；890 F1为`kernel/cpu/src/aarch64.rs:47–53`。本批未重新打开目标head源码，不能把JSON的“verified”措辞改写成我们的源码核验。

### B及C的边界

B完整清单：`asterinas_asterinas_2592-c390ea92#F1`（cgroup.freeze误用SIGSTOP）；`asterinas_asterinas_3864-a5cd36f4#F1`、`asterinas_asterinas_4003-81eaaca3#F1`（chmod/chown快照检查与更新分离导致TOCTOU，后者justification提及架构难修/FIXME）；`theseus-os_Theseus_1081-2d7aab64#F1`（统一IRQ handler丢失每个中断的identity）。这些可提示抽象能力不足，但目前golden判定对象是具体行为错误。

C定义为全部83条减上述23条，因而可逐文件/ordinal精确重建。例：`rust-lang_rust_122441-cc92a9b8#F1–F4`是read_exact限额/边界/更新错误，F4重复另一实现的错误不自动证明应共享；`theseus-os_Theseus_1031-a3210d5c#F1–F2`是两处页范围off-by-one；`redox-os_liner_3-cb866c44#F1`是遗留冲突标记；`asterinas_asterinas_1502-99f62575#F1`是cfg编译失败。`theseus-os_Theseus_890-d3a057a5#F2`虽提到复用栈和简化循环，golden核心是末尾栈泄漏，未计独立设计标签。

这不是全覆盖且唯一正确的架构分类；边界明确保留混合问题，不拿“correctness”字段机械排除所有设计议题，也不把所有安全问题泛化成架构问题。

## 4. 被筛掉的真正设计线索：不能当正/负真值

`golden-rust/asterinas_asterinas_2432-32c1e385.json` F1 justification明确记载：另一候选评论`2471590727`讨论mount options属于Mount而非FileSystem，被删除为API-design preference；现存F1是遗漏MS_NODIRATIME。被删评论不是现存finding，不能给它一个虚构F2。可从PR2432原线程补证，当前只有数据集编者摘要。

`golden-rust/asterinas_asterinas_2705-3ae42372.json` F2 justification记录排除了fast-path评论`2601622539`、dedup评论`2601648633`，理由为不属实质缺陷。现存F1的will_ignore复用不等于这些被排除评论。**设计未入选是该集筛选偏好，不证明设计建议错误或无研究价值。**

## 5. 通用golden中的更直接设计发现入口

以下来自11个Rust任务中的定向审读，不声称通用golden设计议题全量召回。完整路径均为`RB/golden/<task>.json`。

| 精确task/finding | 上游标签/生产者 | 发现用途与未解决义务 |
|---|---|---|
| `OpenDevicePartnership_embedded-services_793-f63a0246#F3` | tp/low/maintainability；`llm_review:claude-sonnet-4.6` | `PartitionGuard::within_bounds`与Partition重复；`partition-manager/partition-manager/src/lib.rs:138–151`。适合实际局部实现共享调查。 |
| 同task `#F4` | 同上 | `ext/bdd.rs:53–88`的start_block/check_access重复；要核对真实字段/guard/生命周期，而非因文本相同即推荐helper。 |
| 同task `#F5` | 同上 | `ext/bdd.rs:189–201`中Guard RW/RO read重复；已有Partition通过readonly委托，但Guard没有该能力。复用成本/接口差异是具体发现义务。 |
| `mheuss_chronicle_14-04ac4c02#F13` | tp/low/maintainability；`ccr:claude-opus-4.7[ReasoningEffort=medium]` | `chronicle-daemon/crates/storage/src/files.rs:1–42`留下测试专用影子实现，而生产逻辑已迁media；是测试责任和真实代码路径断裂线索。 |
| 同task `#F17` | tp/low/maintainability；`ccr:gpt-5.5[ReasoningEffort=medium]` | `storage/src/lib.rs:16`残留files模块声明；与F13高度相关，不能当独立两机制成功。 |
| `MatthewPeterKelly_fractal-renderer_163-0d3f5f18#F11` | **fp**/low/maintainability；human_review，评论`3068329256` | “main应只委托库”的职责意见，但golden解释称所选head已为10行委托。可做**快照/缓解核对**案例，不可当confirmed accepted设计正例。 |

前三条source只有`type=llm_review, alignment=generated`，没有人工讨论URL；后两条模块候选source为`type=ccr, alignment=generated`。golden justification中的“confirmed/verified”是上游标签解释，不是本次验证。特别是“unrelated structs不能共享trait”这类建议文本不应直接被采纳为Rust约束；必须检查具体泛型/借用与方案边界。

建议发现顺序：先golden-rust2342的**职责位置**原讨论/固定head，再通用Rust793的**同任务三finding视为一个共享family**，再按需要核验Theseus813/890的**接口承载状态/可信type**。这些是可审PR入口，不是新排名算法、重构实现或效果实验；xkernel放在以后，不能拿旧内核发现反向挑选“成功”标签。

## 6. 标签来源与accepted-review缺口

1. `RB/docs/RUST_SET_WORKFLOW.md` §1–§5要求人工inline评论，head等于original_commit_id、base为merge-base、完整patch语义审查、拒绝作者反驳项。实际生成的83条均带human_review和source评论信息；这是良好追溯入口。
2. 但其宣称的唯一事实源`rust-set-work/findings_spec.json`、ledger、原始GitHub缓存、selfcheck/裁决历史**不在本clone**；`.gitignore`忽略整个本地独立rust-set-work。无法重跑该完整来源链。不能从输出JSON倒推出selfcheck所有检查实际完成，也不能把justification里“作者认可/已修复”的摘要当原回复原件。
3. 通用`RB/docs/METHODOLOGY.md` §5.4说初始标签由Sonnet4.6分类器产生、后经人工审计并纠正47条TP；后续分类器版本说明与开发过程应单独记录。README的“human-reviewed golden”是集合层说明，不是每条PR作者接受记录。§5.1明确目标是估计人类是否愿意处理，而非已观测所有人的行为。
4. 通用4632条生产者：sonnet4.6=1474、gemini2.5-pro=705、gpt4o=781、ccr opus4.7=270、ccr gpt5.5=1065、human_review=191、semgrep=146。来源4295条只有type/alignment，146条附tool/rule，191条带人工作者/URL等字段。不能将模型标签与评论原作者立场混成“人工接受”。
5. 两套输出没有逐条accepted/rejected-resolution、接受者、修复commit验证、修改前后设计义务映射。评论存在≠作者同意，作者表示同意≠实现已落地，PR合并≠每项建议被采纳。特别是Rust4003的FIXME接受可能只是承认未解决问题；Theseus1027评论建议API与摘要称实际替换API还不完全同名。
6. 通用集准则允许一些pre-existing/outside-diff发现作为TP；Rust工作流只纳入PR引入缺陷。不能用同一TP数混算两个总体。Rust集全TP也没有天然的设计误报负例；通用fp不能无审查视为真实设计负例。
7. README/METHODOLOGY描述聚合分类一致率，不是设计子任务准确率，更非本次实验。golden原文已经被研究者读过，后续若建立任务，要把答案、justification、修复内容隔离到评价侧；按PR/family分割，防同PR多head、同机制多个finding泄漏。

本批只完成**数据/标签及问题发现导航**。下一最小补证是为一个选定PR取得固定head完整patch/相关源、原review线程含回复、后续提交与作者决议；分别登记“具体bug事实”“职责/复用主张”“是否接受及落实”。未取得前一律称待核实候选，不给accepted design标签，也不启动模型或xkernel实验。

## 7. 可复核摘要与限制

本地原件SHA256：

```text
corpus/rust-set.json e0fa2770c55d59bce6ecddaa4ac5bed578e8364c732c60c1bf6e799bad4fdcf4
corpus/manifest.json e74656b8c1c4bbab5ce85f1fcb742a7aaad550a4d7bd46e1f83a0746807bfa02
docs/RUST_SET_WORKFLOW.md a6f8b8b60e654f0d91a33bd1871de9a7d693db49c41d23f078d215f0df078d4c
docs/METHODOLOGY.md 2b69e9f9a4bfeb7d568fccaf159dbffc3993a5dd0f941ed1b3954bbc1ac608a4
golden-rust/ sorted-file digest a5ac13ca7a31ff2f64ccb1b29e6d2fd56c2f13c53942087da69e72561f2fcaba
golden/ sorted-file digest 2cd5b1b49e628c66d333c96efc0a4707927182d97e34e9c2d4a576f83ddfc457
```

目录digest算法：按文件名排序每个`*.json`，串接`filename + " " + SHA256(file_bytes) + "\n"`，再对UTF-8串取SHA256。计数直接解析JSON，不采用文档可能陈旧的数量。未安装依赖、未运行classifier/judge/selfcheck；不更改任何上游数据。一次尝试读取`schema/golden.schema.json`发现不存在，未据此推断存在accepted-schema；实际schema目录是agent manifest相关文件。部分长终端输出截断后，对83条justification、候选详情、来源统计和§5.4分别重读；未把被截断内容声称全部人工阅读。

公开文档入口：[Rust构建流程](https://github.com/LastOstra/ReviewBench/blob/101b6d6bb612a5befee3ec46974cd3b4587c7e44/docs/RUST_SET_WORKFLOW.md)、[方法论](https://github.com/LastOstra/ReviewBench/blob/101b6d6bb612a5befee3ec46974cd3b4587c7e44/docs/METHODOLOGY.md)。本批证据实际读取的是上述本地固定clone，不声称在线核验这些链接或任何原PR。只新增本笔记，不登记catalog，由主线程安排。
