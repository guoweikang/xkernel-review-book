# 发现阶段基准选择与实际接入预检

日期：2026-11-11。目标是选择一个与发现任务相符的公开评价入口，而不是再扩充候选审阅数量。本轮实际执行来源固定和网络响应采集，未运行克隆检测或基准评价。

## 选择及理由

选择BigCloneBench V2／BigCloneEval作为首个公开克隆发现评价参照；CodeSearchNet仍用于自然语言代码检索，MiniCode留给后续方案生成与质量评价。三者不放在同一排行榜，不因下载便利而用错误任务替代当前问题。Rust受控案例另立开发实验，不代替公开基准。

选择协议：`research/protocols/discovery-benchmark-selection-v1.json`。源码定位、克隆关系和重构收益三个任务分别验证；BigCloneBench结果不证明Rust重构有效。

## 本轮真实操作

1. 固定BigCloneEval提交 `6d393ec8adb1d71493d09881ba520659b6c2c68e`，取得commit/tree、README和Makefile，并校验Git blob。另固定捕获CoverageMatcher和CloneMatcher源码。
2. 从固定README提取数据库、配套精简IJaDataset的两个官方OneDrive分享链接。新脚本 `scripts/probe_bigclone_downloads.py` 对每项读取最多65536字节，使用默认TLS验证、不带凭据。
3. 两项均返回HTTP 200，但Content-Type为HTML，响应声明长度约419KB，读取到的是网页前缀，未取得gzip数据包。报告保留URL、最终地址、状态、类型、长度、范围头及响应字节哈希。HTTP 200不是下载成功；该观察也不证明数据不存在或必须登录。
4. 固定BigCloneBench官方仓库HEAD `37f6c7141dac914d7eb13c09a967c6ce1a821f91` 并保存README；它区分V2与旧ERA数据，说明数据库许可和来源代码各自的许可状态。

证据目录：

- `research/evidence/runs/2026-11-11-bigclone-scope-01/`
- `research/evidence/runs/2026-11-11-bigclone-matcher-01/`
- `research/evidence/runs/2026-11-11-bigclonebench-scope-01/`
- `research/evidence/runs/2026-11-11-bigclone-download-probe-01/`

下载探测只检查分享入口。响应可能包含临时网页信息，保留在研究归档，不作为book静态站点公开内容。不借第三方未经核验的小样本冒充完整V2，不静默改用旧ERA数据。

## 执行前必须处理的评价条件

[评价契约核查](2026-11-11-bigclone-evaluation-contract.md)分开说明数据库、源码和matcher职责。小片段实验也必须先明确参考分母，只能评价实际扫描范围内的参考对；不能扫描十个文件后仍使用整个数据集的分母，也不能只挑检测器已命中的参考对。

既有SCC方法前端的空行定位问题已在历史实验复现，因此不能直接把其行号导入评价器。本轮没有重新修整Java前端。应先用固定的边界样例校验范围回映射，再导入真实基准输出。

此外，捕获的CoverageMatcher源码在可选line/ratio参数绑定处存在编号疑点，见契约笔记；仅为静态风险，未执行验证，不宣称所有模式失效。默认覆盖模式与可选越界限制也不能混为一谈。下一项需限定为实际选用模式的小型集成检查，不扩为通用Java缺陷研究。

官方README将数据库及其衍生物标为CC BY-NC 4.0，并说明来源文件保留各自许可。这里只记录声明，不作商业使用或专利的法律判断。后续数据采集、论文工件和工具发布分开处理，不自动把原始数据打包发布。

## 对主线的影响

当前状态为“基准已选择、源代码已固定、数据正文尚未取得”，不是方法失败或论文复现完成。停止重复查找新基准名称；下一步只解决公开数据取得路径和评价接入条件。同时制定Rust受控机制集，区分保行为变换、部分共享、已有委托和契约差异，并将来源种子及变体分组隔离。

若标准数据短期无法取得，Rust实验可以继续，但必须标为自建开发集，不将其结果充当公开基准成绩。已有xkernel文档top20只用作失败分析，不能拿来调整方案后再宣称独立效果。

一手来源：[固定BigCloneEval说明](https://github.com/jeffsvajlenko/BigCloneEval/blob/6d393ec8adb1d71493d09881ba520659b6c2c68e/ReadMe.md)、[固定BigCloneBench说明](https://github.com/clonebench/BigCloneBench/blob/37f6c7141dac914d7eb13c09a967c6ce1a821f91/README.md)。
