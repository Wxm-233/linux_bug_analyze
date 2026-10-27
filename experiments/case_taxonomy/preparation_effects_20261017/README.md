# N1.4c.4：有限准备效果与候选卡

2026-10-17，接续同配置提供者/消费者绑定。只研究同一已读s390案例的两个版本和两类有限出口，不新增内核、C原型、编译或外部模型请求；R3继续暂缓。

本轮把调用清单推进为**带明确假设的函数出口效果**：若资格被拒绝，clear→copy使目标逻辑位域为空；若资格通过且为非HW模式，clear→set(target)→copy使目标逻辑位域只含target。旧/修复的同类路径效果相同，差别在于online/setup资格何时成立以及更新是否赶上公共使用，不是原语本身在两个版本间改变。

这不是实际启动目标已准备的证明。实际分支、updater是否覆盖目标、首次消费时的内容及中间稳定性仍未确定。

## 原语依据与信任边界

`collect_primitives.py`从两版已登记的原非观测topology.i提取四个完整原语定义，复核预处理、配置和autoconf共每版三项输入，并保存同版cpumask.h有限注释。版本、profile、原文、定义指纹与GCC行映射在`primitive_evidence.json`；函数都来自同一历史cpumask.h，两版对应定义相同。

| 原语 | 历史API依据与配置表达式 | 本轮采用的逻辑摘要 |
|---|---|---|
| clear，cpumask.h:388 | API注释clear all cpus；实际调用bitmap_zero(bits, ((unsigned int)4)) | 有效逻辑位清零 |
| set，cpumask.h:309 | API注释set a cpu，索引要求cpu < nr_cpu_ids；实际调用set_bit(cpumask_check(cpu), bits) | 合法目标位设为真，其他有效位保持 |
| test，cpumask.h:342 | API注释说明成员测试；实际调用test_bit(cpumask_check(cpu), bits) | 对合法索引给成员真假，不改变集合 |
| copy，cpumask.h:574 | API注释dst = src；实际调用bitmap_copy(dst_bits, src_bits, ((unsigned int)4)) | 将源有效逻辑位复制给目标 |

`4`是这个配置下clear/copy的位图操作长度，不能据此断言运行时nr_cpu_ids=4。合法目标仍需满足cpu < nr_cpu_ids并处于该逻辑位域中，实际nr_cpu_ids及目标合法性没有在本轮测量。只解释有效逻辑位，不解释padding、所有物理字节、原子性或并发效果。

bitmap_zero/copy、set_bit/test_bit和cpumask_check是本轮停止继续展开的依赖边界。摘要由本助手及独立角色结合历史API注释、配置表达式审核，属于显式研究侧语义假设；不是底层实现的形式证明、人类专家真值或新模型自动推导。名称相同、hash相同和review标记本身也不证明摘要正确。

首次采集器只支持裸十进制位宽，遇到真实`((unsigned int)4)`而停止；`first_attempt_failure.json`保留原因。随后只增加这个明确的unsigned-int常量形式，重新采集成功，没有按NR_CPUS猜测位宽或修改原源码。

## 程序做了什么

新增`linux_bug_analyze/finite_set_effects.py`，解释显式IR中的clear/add/test/copy逻辑集合操作。核心不含架构名、函数名或特定CPU答案。摘要必须与context、定义hash和外部语义审核记录匹配；未知操作、初值不明、输出未写或不支持的路径保持不足。

已读案例的`run_effects.py`负责单列的源绑定：借既有前向路径提取器，将mapper原形参0映为输出、原形参1映为目标，同一静态局部声明地址映为临时对象。参数发生改写、身份不明或出现未审核调用则拒绝。这个角色选择是研究侧已读绑定，不是自动恢复任意C指针、别名、类型或完整调用图。

每个条件结果明确假定：

1. 存储有效，目标索引合法。
2. 逻辑位域相容，使用受支持的不重叠对象。
3. IR对应所选源码路径，该片段实际按该路径到达出口。
4. 静态临时对象在片段中不受其他调用、重入或并发干扰。
5. 摘要中的调用正常返回。

程序中这些拆为七个独立前提；缺任何一个就不输出后置条件。即使显式假定全部成立，仍标记premises_proved=false、runtime_effects_proved=false和whole_contract=insufficient。它们是“若这些条件成立，则出口如何”，不能成为实际前提已满足的证据。

## 结果与检查

| 源码路径替代 | 每个版本在显式前提下 | 不添加这些前提 |
|---|---|---|
| 资格拒绝且到达copy | 出口有效位为空 | insufficient |
| 资格接受且非HW、到达copy | 出口有效位恰为{target} | insufficient |
| HW路径进入for边界 | insufficient，不拿前缀冒充出口 | insufficient |

两版共四个条件出口、两个HW不足；无前提时六项均不足。这里是一个已读案例的路径替代，不是六个案例、四个新检出或独立准确率。online/setup guard原样保存，实际真假保持unknown；test摘要不被用来凭空选择实际分支。提供方资格也没有进入消费者适用scope。

新增11项方法测试覆盖清除旧成员、正确/错误目标、未知初值、逐一缺前提、HW边界、未写输出、未知调用、错版本/hash/审核、copy别名和test不写集合。连同既有19项前向路径与28项判定核心回归，共58项通过。源码角色与方法角色独立只读复核原语/结果及IR实现，未发现本轮阻断问题。

`primitive_summaries.json`是单独审核后保留的输入，重放只读，定义/profile/版本不符就停止重新审核，不会按同名函数自动生成新批准。`results.json`保存源码路径、IR及条件/无前提两种结果；`candidate_card.json`汇总三段链，引用已有冻结卡而不修改它。函数出口结果没有自动借给公共消费期限。

## 本轮收束与下一步

c.4有限摘要及候选卡子项完成，完整N1.4c/N1/N2、R5/R6仍未完成。保留四类未闭合义务：启动目标实际进入updater迭代、最终链接/实际对象、使用期限与写后稳定性、未覆盖HW/并发路径。独立同机制正/正常仍0/0，新确认缺陷0，完整Opus分析状态不因这次离线核对变为通过。

下一步先把现有受限提取、编译绑定、条件效果及拒判边界整理成固定的迁移协议，合并这些未闭合义务，再审独立同机制问题和同用途正常样本的资格。先评估受支持组件的迁移，不把它称为完整内核检测率；初筛接触、规则开发已读、同修复家族分别记录。没有合格样本就保留零分母，不把已读回放改叫独立验证。本例不继续递归展开bitops/include树或增加HW组合。

## 重放

在内层项目根目录：

```powershell
python -B -X utf8 -m unittest tests.test_finite_set_effects tests.test_forward_guards tests.test_contract_protocol
python -B -X utf8 experiments/case_taxonomy/preparation_effects_20261017/run_effects.py
```

只有重新采集四原语时需在WSL运行`collect_primitives.py`；所有脚本均不调用模型或构建/启动内核。
