# G 同父版 ARM64 候选的有限正常资格复核

日期：2026-10-20。仅审本阶段已固定的 G 父版 `95706e717c4f55ca62025c151451ccc28863d085` 的 `initial_sources.json`、`supplement_sources.json` 八份文件及 `symbol_search.json`。未读 G/H 模型输出、子版说明或修复，未新增源码、配置、编译和运行。以下是研究侧源码资格意见，不是模型预测，也不构成独立正常真值。

## 能接通的有限接口关系

- 公共 `include/linux/cpumask.h:90–106` 将 online mask 解释为可供调度的 CPU；`1099–1121` 的 `num_online_cpus()`读取在线计数，但注释明确它只是瞬时快照，若要避免并发热插拔影响需要相应锁。公共 `kernel/cpu.c:3129–3165` 保存计数，并在 `set_cpu_online(cpu,true/false)` 中以在线 mask 位的状态变化为条件增减；`3171–3183` 的 `boot_cpu_init()`也设置启动 CPU 在线。这个局部实现可以提出“在线位与计数应在受支持调用条件下同步变化”的用途候选，不能据此证明所有运行时状态始终一致。
- ARM64 `arch/arm64/kernel/smp.c:203–265` 的次 CPU 入口在能力检查、CPU 信息/拓扑存储和启动通知之后，调用 `set_cpu_online(cpu,true)`，再完成 `cpu_running`；`120–148` 的启动 CPU 侧等待完成并检查 `cpu_online(cpu)`，只在检查通过时返回成功。`439–445` 还以 `num_online_cpus()`打印已激活处理器数；`717–735` 准备路径对 `max_cpus==0` 直接返回，不能以功能关闭作为正常例。`arch/arm64/include/asm/smp.h:69–84` 声明次 CPU 入口及相关启动数据。
- G 的 SPARC64 父版也使用上述公共 API：`arch/sparc/kernel/smp_64.c:133–143` 的次 CPU 路径在等待 commenced mask 后置 online；`1283–1301` 的启动 CPU 侧等待目标 online。该文件 `1146–1161` 的 `smp_capture()`读取 `num_online_cpus()`作为等待界限。两架构共享 online/count 接口，但 ARM64 的启动完成和统计打印 **尚不能证明** 与 G 目标修复涉及完全相同的公共消费用途、时点与对象；不能只凭同名 API 判 ARM64 为同用途正常对照。

## 条件性正常候选与缺口

在入口计数与 online mask 已一致、相关 ARM64 启动分支真实到达、`__cpu_up` 的目标与次 CPU 的 `smp_processor_id()`对应、期间没有未解释的并发/其他写入，并且消费者仅要求锁保护条件下的计数快照时，上述局部源码为“成功上线后目标在线且计数随 mask 的实际变化更新”提供条件性线索。这里的正常是**待核资格假说**，不是已经证明的配置、运行或完整契约结论。

本包没有 ARM64 实际 `.config`、有效预处理分支、完整 `boot_secondary`/CPUHP/底层操作链、启动及热插拔运行记录，也没有证明 `cpu_running` 完成事件与指定目标一一对应或从设置 online 到目标消费间稳定。公共头还明确警告无锁读取仅为瞬时快照。当前无法证明合法激活配置中的真实在线 CPU 数、物理 CPU 状态、所有失败/恢复路径，或 G 与 ARM64 在同一消费者处承担相同的具体保证。源码没有警告、启动消息正常、功能关闭或单纯返回成功，均不能填补这些缺口。

## 接触与归属

ARM64 实现文件 `arch/arm64/kernel/smp.c` 曾作为 N2.6 F 父版 `d2e9f53ac5dd76dadc0b5f04f6c27640604ce2af` 的完整补充源码进入 `new_input_contract_trial_20261017/supplement_sources.json`，并作为 `documents_F.json` 的 D05 原文输入参与方法开发；本次 G 父版版本不同不消除源文件/路径暴露。此次有限旧记录未显示 `arch/arm64/include/asm/smp.h` 有相同接触，但单独未见该头不足以使整个对照独立。此候选可保留为同父版资格/已接触源码上的条件分析，**正式独立同用途正常分母仍为 0**；不因结果不足补换另一个对照。后验机制与家族判断须等父版预测或跳过记录保存后，由隔离角色读取必要修复材料，再按预先协议裁定。
