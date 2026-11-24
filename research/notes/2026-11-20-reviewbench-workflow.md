# ReviewBench 接入与设计问题评测流程

日期：2026-11-20。目标为发现设计问题，不再要求生成重构补丁或证明优化收益。历史内核优化实验保留；此前排队的六条xkernel依赖边试验暂停。先在独立PR参考集上验证发现能力，xkernel作为之后的真实部署对象。

## 来源与复用结论

- 项目主页：<https://review-bench.ai/>。主页排名不是本研究成绩。
- 用户提供的仓库：<https://github.com/LastOstra/ReviewBench>。
- 固定提交：`101b6d6bb612a5befee3ec46974cd3b4587c7e44`；本地工作副本 `/tmp/reviewbench-study-20261120`。
- 已核对 `AGENT_CONTRACT.md`、`docs/JUDGING_INPUT.md`、`docs/METHODOLOGY.md`、`docs/RUST_SET_WORKFLOW.md`、`scripts/local_run.py`、`scripts/eval/{eval,input-validation,matcher,scorer}.ts`，不是仅按README推断能力。

**复用格式、运行接口和评分实现，不直接把现有Rust集称为设计问题基准。** 保留审查输出、语义匹配、未匹配意见分类、确定性计分的分层；数据适用性和维护者接受证据另外审定。原工具运行、我们的机械审计、后续发现算法效果是三种不同成果。

## 取得的数据

|数据|任务快照|finding|标签|适用性|
|---|---:|---:|---|---|
|`corpus/rust-set.json` + `golden-rust/`|57|83|75 correctness、8 reliability；全部TP|Rust正确性／契约补充轨，不是设计主轨|
|`corpus/manifest.json` + `golden/`|219|4632|2623 TP、2009 FP；127 api-architecture、731 maintainability（含TP/FP）|有设计候选池，不能按类别直接确定设计正例|

计数由 `scripts/audit_reviewbench_dataset.py` 全量计算，保存JSON指针、文件摘要和来源字段。Rust数据流程明确排除设计偏好、风格和文档意见；接口契约错误可以与设计相关，但不自动等于职责外散或重复实现。具体初筛见[用例审计](2026-11-20-reviewbench-design-audit.md)。

公开Rust文件带评论URL、作者、时间和original_commit；构建事实源 `rust-set-work/findings_spec.json`、台账、缓存与selfcheck脚本不在此克隆中，不能声称已复现私有构建审计。评论真实且未被反驳，不等于已取得接受回应和修复映射。上游混合模型、工具和人工来源，人工标注TP与PR维护者接受是不同证据。

## 测试流程

### 1. 数据准入和冻结

独立建立设计集，不覆盖Rust正确性集。完整 `repo/pr_number/base/head` 标识任务；同PR多head不得跨开发／保留集，按仓库和变更族分组隔离。公开已审读案例记录暴露，不称模型无污染盲测。

沿用manifest和golden格式，另存评测侧证据：

|元素|要求|
|---|---|
|类型|重复实现、能力未复用、职责外散、类型／模块／crate边界；纯风格另列|
|问题存在|评审时head、base的merge-base依据、完整patch、相关文件及当时契约|
|原评审|永久链接、原文、作者、时间、original_commit、上下文|
|接受证据|明确接受回应或对应修改及定位，记录异议；不能以PR合并代替|
|裁决|问题成立／合理差异／证据不足，审定人、理由和复核状态|
|隔离|agent输入白名单、修复与标签隔离、历史暴露、拆分组|

尚未核实接受的案例可用于开发，但不进“已接受设计意见”的正式分母。已知正例覆盖不等于全部设计问题召回。模型审读不能冒充独立人工真值。

### 2. 工具预检

```sh
git clone https://github.com/LastOstra/ReviewBench.git ReviewBench
cd ReviewBench
git checkout 101b6d6bb612a5befee3ec46974cd3b4587c7e44
npm ci --ignore-scripts
python3 -m venv /tmp/reviewbench-venv
PATH=/tmp/reviewbench-venv/bin:$PATH npm test
npm run check:golden
npm run check:test-set
```

`check:golden`仅检查默认golden目录的完全重复意见，不是Rust完整审计；`check:test-set`检查上游test子集同步。本仓库另提供机械预检：

```sh
python3 scripts/check_reviewbench_dataset.py
python3 scripts/audit_reviewbench_dataset.py \
  --manifest /path/to/ReviewBench/corpus/rust-set.json \
  --golden /path/to/ReviewBench/golden-rust \
  --output /tmp/rust-inventory.json
```

机械预检不访问GitHub、不拉源码、不证明标签正确、不检查接受证据。完整schema、源码行内容和merge-base语义仍需后续审计。

### 3. 审查运行

输出沿用 `pr` 身份、`agent`、`findings` 和可选 `usage`。每条意见含producer、仓库相对file、head坐标start_line/end_line、问题及后果message；一条逻辑问题一条输出。跨文件证据可放sidecar，保持兼容格式。

可让已有审查器直接产出此格式；`local_run.py`是 **pr-agent专用适配器**，只接受 `--diff-file ... --json-output ... review` 契约。源码仅显式传diff，不能假定模型拿到了manifest的title/body或全仓上下文。

以下是准入后的兼容性试跑模板，**不是本轮已经执行的设计实验**：

```sh
cd /path/to/ReviewBench
run=$(mktemp -d /tmp/reviewbench-design.XXXXXX)
python3 scripts/local_run.py \
  --manifest corpus/design-dev.json \
  --pr-agent /absolute/path/to/pr-agent --producer design-baseline \
  --work "$run/work" --seed-dir "$run/repos" \
  --out "$run/findings" --limit 1
```

`design-dev.json`与`golden-design/`须在案例准入后生成，当前未创建。先单题冒烟，再去除limit运行冻结的完整人口。每轮独立目录，不能混入已有 `findings-rust/` 的结果。

正式运行前必须处理以下边界：

- `local_run.py`实际从上游SSH克隆，`--mirror-org`未用于URL；所谓回退还是同一仓库，与说明的镜像流程不同。
- runner强制checkout并执行 `git clean -qfdx`；只使用专用一次性工作区，禁止指向开发树。
- 宿主runner继承环境、完整Git对象可能包含后续修复，不是防泄漏沙箱。正式agent只能见base/head可达历史和当时元信息，不能访问golden、后续修复和PR评审。PR body可能事后更新，也要核对或固定不提供。
- `try-agent.sh`仅支持test/full选择，不直接接受自定义manifest；本地Docker脚本不等于托管平台网络、历史和超时保障。
- `to_findings`静默丢弃部分非法意见，必须核对转换前后数及拒绝原因；`--skip-existing`只按文件存在跳过，不能用来复用不同配置旧结果。
- 每个预定任务须有有效输出（完成审查但没意见为`findings: []`）或明确失败记录；失败不能当作未发现问题或静默排出分母。

这些是正式实验准入要求，本轮**未实现安全runner或真实推理运行**。

### 4. 独立判卷

审查后由独立评测进程读取golden，API凭据仅通过环境注入。运行模板：

```sh
npm run judge -- \
  --candidate "$run/findings" \
  --manifest corpus/design-dev.json --golden golden-design \
  --provider "$JUDGE_PROVIDER" --model "$JUDGE_MODEL" \
  --repo-dir "$run/repos" --output "$run/scoring/results.json" --strict
```

offline指本地，不表示无模型API或费用；审查与judge都要固定模型、prompt、预算和重复次数。禁用 `--ingest`，防止当前结果写回冻结golden；不能用`--no-strict`跳过失败后出正式成绩。此版本judge不支持`--help`，失败输出已保留。

独立核对预定任务、完成输出、被评分任务三个集合；strict只检查已有输入，不保证完整manifest覆盖。同PR多文件意见会合并，不能把不同轮次放在同目录。

若所有预定PR确已完成且全部输出空findings，本版本strict还会拒绝“总意见数为0”。先独立核完人口及输出，再额外传`--allow-empty`计分，仍保留strict；不能用它掩盖没有有效PR、缺失golden或零交集，也不能把合法零发现误判成执行失败。

### 5. 计分和复核

- **grounded recall**＝覆盖golden TP／全部golden TP，用作已标注问题覆盖，不是全量真实召回。
- **grounded precision**＝匹配golden TP的候选／匹配任意golden的候选，排除未匹配输出。Rust集全TP，因此非空匹配时必为1，不能表示误报少。
- **augmented precision**纳入模型裁决的未匹配意见；**augmented recall**分母随各Agent新增TP变化。不能当独立人工准确率或唯一比较指标。
- 另报全部告警的有效／无效／未知、裁决覆盖、去重问题数、核查成本、token／时间／费用和运行失败。未裁决意见不默认TP或FP。
- matcher只在同文件内匹配。跨文件职责问题可能根因相同而锚点不同，需评测侧稳定issue ID和多锚点说明、人工复核漏匹配；不能未经验证改评分器提高分数。

设计问题成立及接受证据需审定，但不要求历史修复是唯一合理方案、不要求证明优化性能。受控正负题验证评价器，不能代替真实PR。

## 本轮执行证据

路径：`research/evidence/runs/2026-11-20-reviewbench-intake-01/`。

- 固定版本并全量机械清点，原仓库工作树未改。
- `reviewbench-source.tar.gz`归档该提交全部Git跟踪文件（含LICENSE、源码、依赖锁、公开数据与测试），不含node_modules、私有rust-set-work、PR源仓库或API凭据。`manifest.json`记录摘要、环境和命令；它不是完整离线可执行环境。
- `npm ci --ignore-scripts`成功；首轮类型检查通过、49/53测试通过，4项因找不到`python`失败。独立venv补齐命令后，原源码53/53通过、0跳过；不是修改测试迁就结果。
- 原`check:golden`及`check:test-set`通过；本仓库审计Rust57/83及上游219/4632，身份与基本字段0错误；检查器通过有效fixture及五项负控制。
- 没跑真实pr-agent或付费judge，没有设计发现成绩。原测试含构造空意见的judge入口，不是AI评审有效性测量。

资料检索：`golden ReviewBench` OR查询命中7／返回6／省略1；`设计 标签 --topic evaluation`为17／6／11；`themis historical-preference`为23／6／17。先前误用单引号内整句得到0字面命中，不作为不存在材料的依据。实际读了PROGRESS、RESEARCH-PLAN、scope/evaluation、检索规范、Themis及历史偏好笔记和上述ReviewBench源码；未重读全部旧实验或重做Themis论文核查。原检索结果在`.build/retrieval/reviewbench-*.json`，关键清点随run保存。

## 方向审议与下一批

Goodall独立只读审阅建议复用框架、不把Rust集当设计主集，先核至多六个设计PR的接受链。主线程采纳：错误标签上的漂亮分数不能回答目标问题。Rawls另做用例初筛，两位Agent都不是独立人工标注者。

二次审计发现全零意见须配合`--allow-empty`，已补到运行流程。机械清点中`source_commit_matches_head`仅记录、不作为错误条件，因此0错误也不证明评论锚点全部通过外部核验。

下一批先冻结至多六个不同PR的名单与顺序，优先api-architecture及实质结构／复用类maintainability，核对原评审、问题时点源码、接受回应或对应修复；不足如实记录，不强凑正例。已查看标签的案例作开发，保留集由未参与方法调整者提供／封存。之后冻结输入隔离与人口检查，再执行基线和一项机制对照。xkernel不加入这轮分母，旧优化证明分支不续跑。

固定来源：[Rust流程](https://github.com/LastOstra/ReviewBench/blob/101b6d6bb612a5befee3ec46974cd3b4587c7e44/docs/RUST_SET_WORKFLOW.md)、[scorer](https://github.com/LastOstra/ReviewBench/blob/101b6d6bb612a5befee3ec46974cd3b4587c7e44/scripts/eval/scorer.ts)、[runner](https://github.com/LastOstra/ReviewBench/blob/101b6d6bb612a5befee3ec46974cd3b4587c7e44/scripts/local_run.py)、[方法论](https://github.com/LastOstra/ReviewBench/blob/101b6d6bb612a5befee3ec46974cd3b4587c7e44/docs/METHODOLOGY.md)。
