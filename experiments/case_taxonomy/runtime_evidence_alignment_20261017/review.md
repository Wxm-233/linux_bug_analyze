# 同 runtime 配置预处理取证的独立有限复核

结论：**本轮有界采集通过，语义解释保持局部且有条件。** 核对的是一次5个翻译单元的当前编译器预处理、11个预登记函数区域，以及结果后另登记的1个补充区域；不是12个预登记项目、12个不同函数或新案例。未重跑编译器/提取器，没有读旧启动结果、展开其他 helper 或调用模型。

## 命令、保护和区域身份

逐项比较保存的原始/新 argv，并只读回查 WSL 五份现存 `.o.cmd`：全部原 argv 相符，新命令仅移除唯一 `-Wp,-MMD,...` 依赖输出，将精确 `-c -o object source` 尾部改为 `-E -o 新缓存路径 source`，编译器替换为已记录的解析后绝对路径。其他宏、include、优化及架构参数逐项保留。五条各有且仅有一个 `-E`，无 `-c`、make、链接或 objtool；由 `shell=False` 执行。执行记录为5次、各返回0；受控环境确实传入 subprocess，不只是写在账本中。

前后保护表38项完全相等，本次独立只读重算也均匹配：原四 profile 的10个选定对象、旧两 profile 配置及所列生成头、两镜像/两 initramfs、五份原 `.o.cmd`、七份选定观测源码/头和两编译器。此结论只覆盖列出的文件，不表述为全源码树或全部头文件均经过历史身份认证。

五份实际 `.i` SHA均与执行结果相符；11个已保存 text 均逐字等于 `.i` 的登记偏移切片，其区域 hash 与精确名称路径匹配。两份 `cpu_smt_mask` 正确来自公共 `include/linux/topology.h:203–206`，没有误定位到 core.c。其他函数定位于各自登记 `.c`，11项均为 definition。编译器行号给出展开后的归属位置；`all_token_paths_match_name_location=true` 不是全部宏定义原始来源的证明。

补充 `smp_callin` 的协议 hash、现有 x86 `.i` hash及实际切片另核对一致；身份为 `supplementary_after_initial_result`，0次新预处理。原协议、11区域结果和原先N2选择不因此改写。

## 这些区域内能支持的最小关系

下列行号均为**观测源码**坐标，不能与非观测原版行号混用。

| 项目 | 可见原文关系 | 可登记的窄事实 |
|---|---|---|
| s390准备对象 | `update_cpu_masks:256–258` 对 possible 集合的循环目标 `cpu` 取 `&cpu_topology[cpu]`，把其 `thread_mask` 交给 `cpu_thread_map` | 目标索引及结构字段的源码联系；possible循环不能替换为后一个online循环272行 |
| s390资格/效果形状 | `cpu_thread_map:101–113` 清空临时mask，`!cpu_online(cpu)`即转copy；通过后先set自身，非HW直接转copy，HW另有present/online处理 | 资格域为online；拒绝路径clear→copy、接受非HW路径clear→set→copy。只登记调用结构，不在此求实际guard、底层效果或覆盖全部目标 |
| s390局部阶段 | `smp_start_secondary:907,913–914` 先notify，再set_online，再update | 此入口正常顺序中更新位于通知之后；不把CPU必须online当公共消费契约 |
| x86准备对象 | `set_cpu_sibling_map:585–603` 先把目标加入setup集合；非多核分支对目标的per-CPU `cpu_sibling_map` set自身，另一分支遍历setup集合并双向set相应map | setup资格与per-CPU sibling对象的可见使用/写入位置；不求match helper、真实迭代、硬件拓扑或写后稳定性 |
| x86局部阶段（补充） | `start_secondary:241,261` 在set_online前调用smp_callin；补充 `smp_callin:193,210` 先set_cpu_sibling_map，再notify | 已生成同profile材料中可见准备调用→通知的局部顺序；补充前原11区域不能独自给出这条连接 |
| 架构到公共getter | s390 getter返回 `&cpu_topology[cpu].thread_mask`；x86 getter展开为目标CPU的per-CPU `cpu_sibling_map` | 公共同用途接口选择不同提供对象。是源码表达式/目标角色绑定，不是最终链接或实际地址证明 |
| 共同消费 | 两份core `sched_core_cpu_starting:5777–5784` 取getter并调用lock；`sched_core_lock:251,264–268` 先取指针、关中断，再按mask内容遍历并锁对应rq | getter取指针与真正内容遍历分开。公共用途相同，不要求两架构展开文本或原始mask逐字相同 |

观测代码还在core锁函数255–262读取mask/self/weight，并在遍历中累计count。它们是探针读/记账，不能混称原消费者读，也不能由源码中的打印常量或 `r4_note` 参数生成“已准备/未准备”的真值。这里没有使用旧运行观察来补齐语义特征。

## 尚缺什么，不应升级什么

1. `notify_cpu_starting` 到 CPUHP 再到公共起始回调的完整绑定不在这11+1个区域内；本轮没有重新证明那条外部链。其既有证据若需接入，必须明确引用和审核身份，不能假称本次自动提取已闭合。
2. 没有证明同一最终内存对象、目标实际循环覆盖、cpumask原语效果、helper副作用、写后不变或并发。源位置先后不等于完整CFG、准备完成或全局首次消费期限。
3. 原始内容遍历在core265行，而观测采样位于257–259、关中断264行之前；不能将采样升级为精确遍历值或整段稳定性证明。后续weight分支、leader查找与rq状态也不能被一个self条件充分替代。
4. 保留了 runtime 实际config/image与原命令的绑定，消除了“直接拿另一套非观测配置替代”的已知错配；但当前 GCC/当前头文件视图不是历史构建的完整可重放认证。镜像未变亦不证明新 `.i` 已被该旧镜像重新编译采用。

适合接出的最小事实字段为：profile/版本/config/image/source/命令/`.i`身份、目标角色、提供字段、资格集合、局部调用顺序、getter所选对象及公共内容读位置。资格含义、合法上下文及整条履约结论仍需明确研究侧审核；helper调用存在不得自动变成“准备已完成”。

本轮无新对象编译、内核运行、模型请求、确认缺陷或独立样本，R3未恢复。限定通过不关闭N1/N2的完整自动提取、实际消费与独立增益缺口。
