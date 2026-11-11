# P01 原任务对齐：实验单位、配置与复现缺口

2026-11-05，仅用 `pdftotext -layout` 定向读取归档 `research/evidence/originals/P01-sourcerercc.pdf` 的 §2、§3.1、§3.5、§4（含表 1、3、4、5）及 §5。封面标识为 *SourcererCC: Scaling Code Clone Detection to Big Code*，arXiv:1512.06448v1，2015-12-20，ICSE ’16 preprint；固定原文 URL：[https://arxiv.org/pdf/1512.06448v1](https://arxiv.org/pdf/1512.06448v1)。以下节号均指该归档版本，不以当前工具源码／默认配置补足论文事实。未运行检测或大实验，未联网补查其他版本。

## 1. 确定：单位及最小规模不能混用

§2 将 fragment 定位为文件及起止行，clone pair 是两个片段；§3 将代码块表示为 token 多重集。**表 1 的 SourcererCC 实验粒度明确为 function**，不是 Rust AST 节点，也不是整仓库作为一个分类样本。

| 原文实验 | SourcererCC 配置／样本范围 | 定位 |
| --- | --- | --- |
| 规模曲线、BigCloneBench recall | function 粒度，最小 6 行，最小相似度 70% | 表 1，§4.1、§4.3.2 |
| 全 IJaDataset 大规模执行 | 沿用 Scale 配置，但最小 clone size 提到 10 行 | §4.2 |
| Mutation Framework | 工具配置最小 15 行、70%、function 粒度；生成样本另限 15–200 行、100–2000 tokens、mutation containment 15% | 表 1，§4.3.1 |
| BigCloneBench 参考真克隆筛选 | 原文写“至少 6 行 **或** 50 tokens”，不能改写为两者同时满足 | §4.3.2 |

**原文没有在表 1 为 SourcererCC 指定最小 65 tokens。** 表中 50 tokens 还用于其他工具配置，不能移植成 SourcererCC 的论文参数。6 行／50 tokens 也没有固定换算关系。§4.1 的规模 LOC 用 cloc，仅计含代码的行、不计空白及注释；这不自动说明所有 clone 长度与覆盖计算均使用相同归一化规则。

## 2. 确定：三种“百分比”含义不同

- **检测相似度**：§2 的 token overlap 要求共享 token 数至少达到 `ceil(θ × max(|Bx|, |By|))`；这里的大小是带频次的 token 数。表 1 实验 θ 为 **0.7／70%**。§3 用 0.8 的例子讲过滤性质，不是该表实验阈值；本轮 80% 冒烟不能称为已对齐原论文配置。
- **命中参考克隆的匹配门槛**：§4.3.2 使用 subsume-based 匹配，报告片段按行覆盖参考 clone 的 70% 即计命中；这是检测后评价门槛，不是 token overlap。§4.3.1 的合成评价还要求正确处理 mutation 引入的 clone-type-specific edit。
- **参考类型分桶**：§4.3.2 对 T3/T4 用 VST3 `[90%,100%)`、ST3 `[70%,90%)`、MT3 `[50%,70%)`、WT3/T4 `[0%,50%)`。依据 T1/T2 归一化后的行与 token syntactic similarity，并取两种度量中较小者；不等于 SourcererCC 自身未归一化标识符的 overlap 分数。

## 3. 确定：BigCloneBench 数据范围及指标分母

§4.3.2 使用 **IJaDataset 2.0**（约 25,000 Java 项目、300 万文件、250MLOC）中的 BigCloneBench。论文明确区别当时已发布的 **10 个目标功能**版本与本实验采用的 **48 个目标功能、约 800 万 validated clone pairs 的 in-progress snapshot**。不能把“BigCloneBench”名称相同当成数据版本相同。

Recall 实际输入是含已知 true／false clones 的文件子集：**50,532 文件、约 10MLOC**，不是每个工具都直接扫描 250MLOC。不能承受该子集的对比工具再按分区对运行，以使其暴露于所有参考克隆；这不是训练／测试 split。参考真克隆通过上述尺寸筛选后，表 4 给出按类别的 pair 数：

| 类别 | 参考 clone pairs（类别 recall 分母） |
| --- | ---: |
| T1 | 35,787 |
| T2 | 4,573 |
| VST3 | 4,156 |
| ST3 | 14,997 |
| MT3 | 79,756 |
| WT3/T4 | 7,729,291 |

表 5 按 All／Intra-Project／Inter-Project 分别报告各类 recall：分子是该类参考 pairs 中按匹配协议被找回者，分母是对应参考 pairs；不是返回候选数、文件数、函数数或全部潜在函数对。表 4 未给 intra／inter 的各自完整分母，不能凭表 5 的取整百分比倒推精确命中数。SourcererCC 的 All 行依次为 **100%、98%、93%、61%、5%、0%**，不能概括成对所有功能重复都有高召回。

§4.4 的 precision 来自同一 BigCloneBench 输入上的约 **200 万输出 pairs**中随机抽取 **390 对**：人工判定 **355 TP、35 FP，355/390≈91%**。390 才是此 precision 估计的直接分母；35/390 是该样本的错误发现比例，不是以全部真实负例为分母的 FPR。作者称样本达到 95% confidence、±5%，并由三位专家分担验证；原文未说明三人独立重复标注全部 390 对，不能据此声称有三重一致性验证。§5 还说明其他工具的 precision 采用已发表结果，不是本轮统一人工重标。

## 4. 确定：其他实验不能并入同一成功率

§4.3.1 每语言使用 250 个随机函数、10 个随机注入位置、15 个 mutation operators，得到 **37,500 个合成 clones／语言**，Java、C、C# 共 **112,500**。每个 clone 只用一个 mutation operator，作者承认难以代表多种编辑叠加的复杂 T3。表 3 的 100% recall 只适用于该生成与匹配协议，不是 BigCloneBench 或 Rust 的 100%。

§4.2 报告全量执行约 4.5 天、1.46 亿 clone pairs，以及大于 10 行的 470 万函数中约 240 万出现在至少一对中。后者约 51% 是函数参与率，不是 precision／recall。§4.1 规模实验以随机文件构造从 1KLOC 到 100MLOC 的嵌套输入；其时间与内存证据也不能用小样例命中替代。

## 5. 未知及原任务复现所需补齐（非当前工具推测）

1. **快照身份**：已读原文给出 48 功能的开发中快照，但未给可唯一恢复该数据库的 release／commit／摘要；仅下载某个 BigCloneBench 发布版不能确认一致。50,532 文件清单、过滤后的参考 pair ID 清单及精确分桶／匹配实现版本，本轮均未取得。
2. **执行身份**：论文未在本轮核对章节给出可绑定的 SourcererCC commit、完整配置及预处理工件摘要；不能据公开仓库当前 SHA 宣称原实验源码复现。随机规模子集、mutation 选择及 precision 抽样的种子／完整抽样清单未确认。
3. **标注与评价细节**：没有本轮可用的 390 对逐条判断、标注者分配／分歧处理记录、intra/inter 精确分母，以及参考匹配器运行产物；公式和表中数值可读不代表标签可靠性已独立验证。§4.3.2 自身也指出部分 T1/T2 区域可能满足覆盖规则而被计为 T3 命中，故需与 mutation 评价互补。
4. **对当前准备工作的限定**：小规模检测跑通、正负样例符合预期，只是实现 smoke test；若采用不同最小大小、80% 阈值、不同语料／tokenizer，须称“配置变体验证”，不能称复现表 5 或 91% precision。进一步对齐应先锁参考快照、单位、筛选和两个独立的 70% 门槛，再比较同分母结果；本轮不判断当前工具是否已经满足。

本地查找词：`threshold`、`BigCloneBench`、`precision`、`recall`、`lines`、`tokens`、`sample`，以及表 1／3／4／5 邻近段落。所有确定项来自上述固定版本原文；本笔记未以现代工具参数替换论文口径。
