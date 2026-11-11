# 已有复用证据检索：输入获取与语法降级

## 问题与范围

对已有18对开发候选，检索函数是否已经委托给公共实现的证据。此轮只准备可复跑输入，不判断可否安全重构，不执行检索对照，也不重新导出整仓编译器事实。

沿用 `reuse-evidence-pilot-v1.json` 的原文／邻近上下文／调用候选定义片段三组设计。18对均已被研究者阅读，不能作为独立测试集。

## 精确制品获取失败

`scripts/fetch_kvfs_facts.py` 从归档的CI 3885 x86_64 manifest选择kvfs条目，限定HTTPS、启用证书校验，并设置大小、超时与预期SHA256门禁。此次唯一请求返回HTTP 404，curl退出22，未取得facts正文，未执行源码关联。

记录位于 `research/evidence/runs/2026-11-06-kvfs-facts-fetch-01/`，包含命令、预期身份、stderr与脚本快照。报告中的 `started_at_utc` 实际在请求结束后采集，应理解为记录时间，不能用于计算请求时长。404只说明该地址在此次请求中不可获取，不证明CI从未生成制品，也不证明调用不存在。

## 降级输入：未解析的调用语法

复用现有固定版本syn解析项目，新增 `rust-call-probe` 二进制及 `scripts/probe_reviewed_calls.py`。读取固定提交 `7e3ac94431a0dbb376d2fc8d85098deeff1bba09` 的已归档源码，而非当前移动中的内核工作树。输入归档与每个函数片段均经过哈希检查。

| 观察项 | 结果 |
| --- | ---: |
| 已审阅候选对 | 18 |
| 去重函数片段 | 33 |
| 成功解析片段 | 33 |
| 方法调用表达式 | 169 |
| 其他调用表达式 | 151 |
| 不展开的宏调用 | 41 |
| 闭包、async或嵌套item内的站点 | 11 |
| 已解析的调用边 | 0 |

结果位于 `research/evidence/runs/2026-11-06-reviewed-call-syntax-01/`，保存调用位置、原文、控制输入与结果、源码和依赖锁文件快照、制品哈希。控制项覆盖Unicode字节位置、泛型路径、函数指针变量、宏不展开、延后／嵌套语法区域及非法输入拒绝。

所有站点明确标记 `target_resolution=unresolved`、`cfg=not_evaluated`、`execution=not_established`。方法名不等于方法身份；调用表达式可能是构造器或函数指针；词法嵌套深度不证明实际运行时机。该工具不解析接收者类型、不展开宏、不处理隐式drop或证明路径可达性。因此不能把320个调用表达式称为320条已确认调用边。

## 复跑

在book仓库根目录执行，输出目录必须不存在：

```sh
python3 scripts/fetch_kvfs_facts.py --repo /root/codes/x-kernel \
  --output research/evidence/runs/kvfs-facts-fetch-new
env PATH=/root/.rustup/toolchains/1.95.0-x86_64-unknown-linux-gnu/bin:$PATH \
  CARGO_NET_OFFLINE=true cargo build --offline --locked \
  --manifest-path research/tools/rust-syntax-probe/Cargo.toml \
  --bin rust-call-probe --target-dir .build/rust-call-probe
python3 scripts/probe_reviewed_calls.py \
  --output research/evidence/runs/reviewed-call-syntax-new
```

离线构建需要本地已有锁定依赖。制品下载失败是独立记录，不应阻止使用已归档源码的语法降级。

## 下一项与停止条件

先冻结邻近窗口分配、候选排序、歧义处理、递归深度和开发参考证据位置，再生成三组证据包。每对保持相同函数正文、相同16KiB源码字节上限及最多8个片段，记录实际使用量；不是等token实验。

检索到同名定义仍只能称候选，必须单独核对身份。比较的是有限预算内能否补到已有公共实现的证据，不是重复功能检测准确率。若歧义主导或相对邻近上下文无收益，应保留负结果并重新判断路线，而非顺势建设全程序解析器。当前三组比较尚未运行，不能报告检索增益、token节省或优化收益。
