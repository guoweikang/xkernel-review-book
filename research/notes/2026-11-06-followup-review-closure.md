# 六对发现候选审阅完成：机会比较与下一项决策

固定队列未重选、阈值未调整；本轮完成后四对静态审阅，没有生成内核补丁、增加实验或重新运行测试。
完整发现清单更新为`research/protocols/discovery-ledger-v3.json`：156对中18对已审阅、138对未知，15个人工维护主题。所有这些数量均不是独立案例数或准确率分母。

## 后四对的结论

| 配对 | 已核查事实 | 行动 |
| --- | --- | --- |
| 1045/1894 | nullfs固定目录属性与权限测试可变输入共享结构体形状，但类型、权限、owner、链接数及块统计不同；测试已有meta helper | 保留生产／测试边界，不扩展metadata实验 |
| 1135/1800 | 共同注册机制已在PollContext::register；管道选IN/OUT两源，测试backend另有InvalidState注入且仅注册IN | 保留短策略包装，不报两套注册管理 |
| 1765/1766 | 祖先目标rename拒绝与跨目录成功移动采用不同拓扑和断言，已有基础fixture | 不合并oracle；更小superblock绑定helper收益未证实 |
| 1598/1599 | 单层和嵌套mount对dotdot目标的要求不同，已有构造／挂载helper | 保留显式层级，不为折叠两句引入通用测试模式 |

证据见[生产／测试混合配对](2026-11-06-followup-mixed-pairs.md)及[两对测试审阅](2026-11-06-followup-test-pairs.md)。新增七份固定源码保存于`research/evidence/runs/2026-11-06-followup-context-02/`。
一个额外边界：mount测试的lookup_no_follow直接处理`.`和`..`，因此既往模块测试通过不能表述为完整syscall/path parser端到端验证。测试的真实调用路径也应进入证据记录，而不只读测试名。

## 六对放在一起比较

这里的顺序是研究资源取舍，不是经过校准的优化评分，也不说明未审阅138对价值更低。

1. **卸载现成helper复用：下一项有限核查。** 已有具体公共实现和两个残留相似提交段，不必先发明新抽象。阻碍是锁guard持续范围、调用方锁前提和子树清理顺序。先只核对单点unmount能否复用；不把递归路径或死锁分析自动并入任务。
2. **块读写范围规划：保留备选。** 共同几何真实存在，但新接口的净简化尚不明确；后端调用次数、缓冲分配时机和完成语义必须保留。没有具体维护收益前，不进入补丁／性能矩阵。
3. **其余四对：保留边界对照。** 当前剩余相似主要是数据形状、共同协议或不同测试的准备步骤；没有足够证据支持追加重构实验。保留未知收益，不赋绝对负标签。

## 下一项工作的预算与停止条件

对单点卸载，仅回答三个会改变方案决策的问题：现有helper与内联路径的锁生命周期是否一致；实际调用者是否满足同一前提；最小复用能否减少维护点而不新添模式／回调接口。
若必须改变锁协议或大范围重组调用链，停止把它当低风险复用候选；若存在可局部保持顺序的方案，再决定是否值得生成小补丁并复用既有验证流程。任何死锁、性能收益或行为等价结论都需要另外的证据，当前没有这些结论。
不因本批缺少明显收益就修改筛选规则追求正例，也不把“持续产生对照”当作方法已有效；该检查结束后应比较这18对揭示的发现瓶颈，判断继续人工阅读的边际价值。

## 可复跑台账

旧结果v1与旧清单v1/v2保持不变，完整六对结果保存为`discovery-followup-results-v2.json`；脚本通过显式参数选择版本，避免悄悄改写历史输入。

```sh
python3 scripts/build_discovery_ledger.py --followup \
  --followup-results research/protocols/discovery-followup-results-v2.json --self-check
python3 scripts/build_discovery_ledger.py --followup \
  --followup-results research/protocols/discovery-followup-results-v2.json \
  --output /tmp/discovery-ledger-new.json
```

脚本连接与五类错误输入自检通过。语义判断仍来自源码审阅，并非已经实现自动重复功能判定或独立人类标注。
