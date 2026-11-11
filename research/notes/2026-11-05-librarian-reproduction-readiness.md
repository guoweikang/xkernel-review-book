# P21 Librarian 原任务复现准备核查

日期：2026-11-05。结论：**作者实现、数据入口和运行脚本可定位，但尚不能称为开箱可运行或论文数值已可复现**。本轮只浏览官方论文、作者项目页和公开仓库，通过 `git ls-remote`、GitHub tree API 与固定 SHA raw 文件只读核查；未 clone、下载完整数据、安装、调用模型、训练或执行评测。

## 1. 原任务与版本身份

已读本书 `research/notes/2026-10-27-librarian-reading-01.md`，沿用其任务区分：Librarian 生成共享库并迁移原程序，MiniCode 是基准；不是仅检索重复函数，也不是 Rust 源码单位定位工具。本轮直接回读 [arXiv 2506.11058v3](https://arxiv.org/html/2506.11058v3)，题名 *Refactoring Codebases through Library Design*，2025-10-05，作者 Žiga Kovačič、Justin T Chiu、Celine Lee、Wenting Zhao、Kevin Ellis；阅读范围为 §3–6、附录 C，以及附录 F 的指标定义段，不声称全文重新精读。

[作者项目页](https://code-refactor.github.io/)分别指向 `code-refactor/Librarian` 与 `code-refactor/minicode`。2026-11-05 匿名读取的默认分支均为 `main`：

| 资源 | 固定 HEAD | 核查边界 |
| --- | --- | --- |
| [Librarian](https://github.com/code-refactor/Librarian/tree/f5167b903d00ace774de419a617138b8db69c4bd) | `f5167b903d00ace774de419a617138b8db69c4bd` | README、打包元数据、入口脚本、部分加载／评分源码及完整目录树 |
| [MiniCode](https://github.com/code-refactor/minicode/tree/3cc71a908f16c78e634010523b264671c3546fc2) | `3cc71a908f16c78e634010523b264671c3546fc2` | README、元数据、CodeContests 加载源码开头及完整目录树 |

搜索也命中第一作者的 `zzigak/Librarian`，其 HEAD 为 `63454f53b60186783ea87d51953b9efb1b0ca1eb`，不同于项目页链接的仓库；本轮未审计二者差异，以项目页所指版本为主。上述 HEAD 是当前快照，不是已确认的 v3 实验提交；包版本均写 `0.1.0`，不能代替实验版本标识。

## 2. 许可证、数据与运行条件

- **许可证（元数据／目录树核查）**：Librarian 的 [pyproject.toml:1–15](https://github.com/code-refactor/Librarian/blob/f5167b903d00ace774de419a617138b8db69c4bd/pyproject.toml#L1) 声明 MIT；完整 tree 未见根 LICENSE，仅发现第三方 `third_party/Faithful-COT/LICENSE`。MiniCode 的 [pyproject.toml](https://github.com/code-refactor/minicode/blob/3cc71a908f16c78e634010523b264671c3546fc2/pyproject.toml) 未声明许可证，完整 tree 未见名称含 license 的文件。结论仅是可见声明状况；第三方许可不能替代本项目许可，代码元数据也不能自动覆盖数据、模型和测试来源。数据再分发及全部依赖许可未确认。
- **数据（目录树／部分源码核查）**：Librarian 实际有 [data/LLM_description_clusters/new/0.jsonl 至 9.jsonl](https://github.com/code-refactor/Librarian/tree/f5167b903d00ace774de419a617138b8db69c4bd/data/LLM_description_clusters/new)，以及 old 目录；本轮未下载这些文件核对样本、测试数和摘要。MiniCode 的 [setup_codecontests.py:29–33](https://github.com/code-refactor/minicode/blob/3cc71a908f16c78e634010523b264671c3546fc2/minicode/setup_codecontests.py#L29) 指定数据集 ID `deepmind/code_contests` 和 `data/clusters.json`。其对应 [Hugging Face 数据入口](https://huggingface.co/datasets/deepmind/code_contests)仅按代码 ID 记录，本轮未打开数据卡；数据 revision、许可、下载可用性与两仓库样本一致性未验证。
- **环境（README／源码核查）**：Librarian [README](https://github.com/code-refactor/Librarian/blob/f5167b903d00ace774de419a617138b8db69c4bd/README.md) 要求 `OPENAI_API_KEY` 与 `TOGETHER_API_KEY`，提供 `uv sync`；`.python-version` 为 3.10，pyproject 要求 Python ≥3.9，并有 `uv.lock`。锁文件存在不代表安装已成功或所有模型版本已锁定。MiniCode 要求 Python ≥3.10；其 README 的 agent baseline 还列 `ANTHROPIC_API_KEY`，这不是 Librarian 方法本身必需的第三个模型。

## 3. 可定位入口不等于可直接运行

Librarian 文档入口依次为 `scripts/codecontests/minicluster/preprocess_LLM_desc_clusters.sh`、`train_librarian.sh`。但 [预处理脚本:4–8](https://github.com/code-refactor/Librarian/blob/f5167b903d00ace774de419a617138b8db69c4bd/scripts/codecontests/minicluster/preprocess_LLM_desc_clusters.sh#L4) 读取 `mini_clusters/LLM_description_clusters/new/$i.jsonl`，与仓库实际 `data/LLM_description_clusters/new/` 不一致；[generate_collection.py:30](https://github.com/code-refactor/Librarian/blob/f5167b903d00ace774de419a617138b8db69c4bd/program_refactoring/domains/codecontests_cpp/generate_collection.py#L30) 直接 `open(args.data_file)`，已读路径没有自动补 `data/`。这是静态路径不一致，不是本轮实际运行报错；正式复现前需明确数据放置／路径调整并记录偏离。

[train_librarian.sh:5–48](https://github.com/code-refactor/Librarian/blob/f5167b903d00ace774de419a617138b8db69c4bd/scripts/codecontests/minicluster/train_librarian.sh#L5) 设 `SAMPLE_K=8`、tuple 上限 3、集合 0–9，调用 `program_refactoring/refactor_db.py --model_name o4-mini`，随后调用 `scripts/codecontests/postprocess_metrics.py`。输出目录由日志中的 `LOG_DIR_PATH` 提取，评分文本写到 `train_metrics/`。脚本名及日志中的 train／ReGAL 字样不能作为本轮执行过训练或应复现另一个任务的证据。

评分源码 [postprocess_metrics.py:19–35、66、146](https://github.com/code-refactor/Librarian/blob/f5167b903d00ace774de419a617138b8db69c4bd/scripts/codecontests/postprocess_metrics.py#L19) 使用 Together 的 prompt token logprobs，默认 `Qwen/Qwen2.5-7B-Instruct-Turbo`。仅有聊天生成权限不一定满足该接口；当前 endpoint 是否仍支持、额度、费用、模型快照和返回结构均未调用确认。预处理 [generate_collection.py:8、59–68](https://github.com/code-refactor/Librarian/blob/f5167b903d00ace774de419a617138b8db69c4bd/program_refactoring/domains/codecontests_cpp/generate_collection.py#L59) 读取 OpenAI key 并调用 embedding helper，因此预聚类数据不等于整个准备过程离线；helper 内部后端未继续审计。

MiniCode [README](https://github.com/code-refactor/minicode/blob/3cc71a908f16c78e634010523b264671c3546fc2/README.md) 提供 `uv run python -m minicode.setup_codecontests`、small/large repository setup 和 Claude/Codex baseline 入口。它们是基准及 agent 入口，不能直接替代上述 Librarian sample-and-rerank 脚本；当前仓库覆盖与 v3 每张表是否对应尚未确认。

## 4. 原指标与仍需对齐的配置

**论文直接核查**：[§3](https://arxiv.org/html/2506.11058v3#S3) 以逐程序保留原先通过的测试集合为约束；[§6](https://arxiv.org/html/2506.11058v3#S6) 对库与改写程序整体计 Tokens／MDL，并比较 CC、MI、库调用复用代理与人类偏好；[附录 F](https://arxiv.org/html/2506.11058v3#A6) 的 Best@k 是采样筛选表现估计，不是单次 pass rate。正文 MDL 模型写 Qwen-2.5-3B，[附录 C](https://arxiv.org/html/2506.11058v3#A3) CodeContests 写 Qwen 2.5 7B Instruct、o4-mini、K=8；同附录先写 10 collections，后写 6。当前脚本是 10 个集合，不能据此替作者消除论文口径差异。

**源码直接核查**：[postprocess_metrics.py:247–309](https://github.com/code-refactor/Librarian/blob/f5167b903d00ace774de419a617138b8db69c4bd/scripts/codecontests/postprocess_metrics.py#L247) 的条件汇总按 `ratio_after >= ratio_before` 选择改写，否则回退原程序指标。通过率大小比较不自动证明原先通过的每个测试都保留；未审计执行器的逐测试身份检查，不能断言整套实现仅用此判据。也不能把带回退的 conditional 汇总当成全部生成候选成功率。

## 5. 建议的复现成功条件（本轮未执行）

1. **先锁协议**：选定 CodeContests 原任务，不混同 Rust 检索、MiniCode agent baseline、Logo/Date 下游合成或人类偏好复现；锁定代码 SHA、样本 ID／测试摘要、模型与评分 endpoint、K、tuple、重试预算、依赖和路径调整。优先复用已发布分组；重新聚类属于另一条实验路径。
2. **区分跑通与复现**：单集合产出共享库、迁移程序、逐测试结果与完整评分日志仅算 smoke success；复现论文指标还需对齐完整样本及分母、失败／超时／API 错误、回退比例、采样预算和聚合方式。缺失结果不能当成功或从分母静默移除。
3. **行为与质量分开**：建议核对原先通过测试的身份集合，并单列实际通过数／总测试数、成功候选数／尝试数及任务数；再用相同评分模型比较原程序与“库＋迁移程序”的 MDL／token ratio。改善范围和数值容差应在运行前约定，不以一次更低 MDL 证明维护性、性能或 Rust 内核适用性。

实际检索词：`"Librarian" "MiniCode" github Kovacic`。其后沿作者项目页链接读取官方仓库；未采信第三方聚合页的复现结论。许可证文件内容、数据卡、模型可用性、测试隔离安全、成本、原始运行日志和所有依赖兼容性仍未确认；准备状态应保留为“资源已定位，运行及论文配置对齐待验证”。

## 补充：实际取得的小型工件

按主线程后续要求，仅保存以下固定 SHA 的原始文件；未改 manifest，URL／哈希统一登记由主线程完成。相对路径基于 book 根目录：

| 实际取得路径 | 原始 URL |
| --- | --- |
| `research/evidence/originals/reproduction-2026-11-05/lib-README.md` | https://raw.githubusercontent.com/code-refactor/Librarian/f5167b903d00ace774de419a617138b8db69c4bd/README.md |
| `research/evidence/originals/reproduction-2026-11-05/lib-pyproject.toml` | https://raw.githubusercontent.com/code-refactor/Librarian/f5167b903d00ace774de419a617138b8db69c4bd/pyproject.toml |
| `research/evidence/originals/reproduction-2026-11-05/lib-train_librarian.sh` | https://raw.githubusercontent.com/code-refactor/Librarian/f5167b903d00ace774de419a617138b8db69c4bd/scripts/codecontests/minicluster/train_librarian.sh |

没有下载数据集或模型；没有查询实时 API 定价、估算总 token／调用成本或验证账户额度。已定位模型名和脚本预算不等于费用已核实，也不等于旧模型 endpoint 现在可用。
