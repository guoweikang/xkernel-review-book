# 方法名作为语义输入：清洗控制与真实源码提取

## 所属问题

在职责映射研究中，方法名可能补充模块描述和已接受类名。但观察到映射变化之前，必须知道词属于哪个对象，是否因解析／清洗而被丢弃或串到其他类。这里分别验证原输入实现与构造替代输入，二者不混为“恢复原调用图”。

本轮依据[输入契约核查](2026-11-11-inmap-method-keyword-contract.md)，固定作者提交`cae17d87f8c17d8108d21abd41e0520b6ca65d7c`。没有更换oracle、运行新关键词的完整映射效果实验或修改内核。

## 一、原方法关键词函数的五组控制

工具：`research/tools/InMapKeywordProbe.java`，反射调用原`extractClassMethodsKeywords`及`sanitizeClassMethodsKeywords`，原49个Java源文件不改。构造输入保存在独立文件，未写进`bin/static-cdg.txt`，不伪装成作者图。

|输入条件|实际结果|可解释范围|
|---|---|---|
|只有M行：First.alpha调用Second.beta|两个类分别得到alpha、beta|该格式的两端方法可提取|
|相同M行之前加入C:First Second|两端都得到alpha、beta|C行将同一个空集合赋给两类，后续方法加入发生集合共享|
|相同M行之后加入C行|两端方法集合都变空|后到的类记录覆盖前面的词表|
|内部类归并，固定遍历顺序先出现无关类|Outer得到无关类的unrelatedMethod|原清洗取首条映射值，不是当前内部类的值|
|完全相同条目改为内部类先出现|Outer得到innerMethod|输入条目一致，改变遍历顺序即可改变归并输出|

最后两组以LinkedHashMap显式控制遍历顺序，仅是方法级输入控制，不能外推作者原HashMap在未知真实图上的实际误差比例。前三组使用原字段映射实现。结果与[固定源码](https://git.cs.kau.se/zipasink/InMap/-/blob/cae17d87f8c17d8108d21abd41e0520b6ca65d7c/src/recommender/da/DependencyAnalysis.java)中集合共享、覆盖及取首条值的逻辑相符。

两次干净运行`2026-11-12-inmap-keywords-01`、`-02`的构造输入和阶段输出逐字节一致；独立检查`check_inmap_keywords.py`通过。检查器保留的是观测行为，不把这些结果当理想清洗规范。

## 二、真实Java源码定义方法提取

新工具`research/tools/JavaDeclaredMethods.java`使用固定JDK8的JavacTask解析AST，只parse、不做类型解析、不编译或执行JabRef。遍历具名顶层及具名成员类型的直接方法，记录所有者、方法名与源路径。方法体不递归，因此局部类、匿名类和lambda内部实现不进入此表；构造器及含特殊字符的方法名排除。它不是调用图，也不包含继承但未声明的方法或编译器合成方法。

内置构造输入覆盖重载、成员类、嵌套接口、多个顶层类型、构造器、局部／匿名类型及字符串中的伪方法文本。检查预期保留的五条声明；不以正则扫描替代Java解析。

|观测|结果|
|---|---:|
|源码文件／成功解析单元|843／843|
|解析错误|0|
|具名类型（含具名成员类型）|1096|
|顶层类型|843|
|方法声明，尚未按重载去重|5094|
|与固定842类评价范围精确匹配的顶层类型|842|
|其中直接定义方法名集合非空|797|
|其中成功解析但集合为空|45|
|范围内顶层类去重后的类—方法名配对|4453|

唯一范围外顶层类型是已排除的MacAdapter；没有评价类缺少匹配的顶层声明。45个空集合不能说成解析失败，也不说明类没有功能；继承、构造和成员类型等能力不在这个“顶层直接方法”词表内。

原始清单保留具名成员类型，但四组效果协议选择更保守的顶层直接方法词表；不会把成员方法偷偷归并给外层。内部类归并属于另一项输入因素。

`2026-11-12-inmap-declarations-01`首次提取，`-02`增加构造契约测试，`-03`增加包括零方法类型在内的类型清单；不覆盖早期产物。第二、三轮方法行逐字节相同，第三轮与固定评价集合的精确连接已校验。该比较不是三个完全相同版本的重复试验；变化是新增验证与输出，不宣称提取覆盖全部Java语义。

## 三、这决定了下一项实验怎样设计

采用[四组协议](2026-11-12-inmap-keyword-experiment-protocol.md)：原／修正选择器 × 空／定义方法词表。定义词表在IR接收边界直接注入，绕开原图解析及内部类清洗；因此测的是明确替代输入，不是原方法完整复现。必须同时报告映射覆盖和标签一致率，避免把额外拒绝藏在覆盖增加后面。

目前完成原函数控制与提取原型，尚未完成四组效果比较。协议要求的冻结运行清单、具体预算、逐轮查询观察及声明位置／排除统计仍需补齐；不能把已经取得4453对方法名写成“语义有效性已验证”。不再继续漫无目的修复原工具其他功能，后续工作围绕因素隔离和可验证的新输入。

## 复核入口与原始证据

原始目录均位于`research/evidence/runs/`。每次runner保存配置、依赖、原源码校验身份、包装器、命令、日志及产物哈希；声明检查另核对固定评价集合的哈希。

```sh
python3 scripts/run_inmap_input_probe.py --run-id NEW-KEYWORD-ID --keyword-control
python3 scripts/check_inmap_keywords.py research/evidence/runs/2026-11-12-inmap-keywords-01 --repeat research/evidence/runs/2026-11-12-inmap-keywords-02
python3 scripts/run_inmap_input_probe.py --run-id NEW-DECLARATION-ID --extract-declared-methods
python3 scripts/check_java_declared_methods.py research/evidence/runs/2026-11-12-inmap-declarations-03 --population-run research/evidence/runs/2026-11-11-inmap-loop-01 --previous research/evidence/runs/2026-11-12-inmap-declarations-02
```
