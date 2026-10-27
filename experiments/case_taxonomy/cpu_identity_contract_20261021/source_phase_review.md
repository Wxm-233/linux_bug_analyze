# N2.18 源码阶段与 API 替身预审

范围：仅审 `source_plan.json`、本阶段 6 份 `sources.json` 原文、已固定的 G 父版 `documents_G.json` 和 `next_task_N218.md`。未运行 harness、编译或补采源码。父／子 `init/main.c`、`kernel/smp.c` 的 blob/文本摘要分别相同；本轮差异应归于 SPARC 枚举与后处理，不可伪装为公共启动代码改动。

## 可由当前源码确认的时序和数值

1. `init/main.c:894,898,901–903` 先 `boot_cpu_init()`、再 `setup_arch()`、再 `setup_nr_cpu_ids()`；SPARC 父版 `arch/sparc/kernel/setup_64.c:622–627` 在 `setup_arch` 内先调 `parse_early_param()`，`:669–680` 后调旧 `smp_fill_in_cpu_possible_map()`、再分配 possible CPU 的 IRQ 栈。`init/main.c:760–772` 有 `done` 门控，故通用 `start_kernel:909` 的再调用不应在替身中重复应用 `nr_cpus`。`kernel/cpu.c:3171–3179` 把引导 CPU 预置为 online/present/possible；测试初态不能默认三个 mask 全空。固定包没有 `of_populate_present_mask()` 的实际调用点，也没有完整 `paging_init`／固件设备树调用链；“它先于旧整理函数”的全局可达顺序只能作为有标注的投影前提，不记作本包完整证明。
2. `kernel/smp.c:934–967` 区分：`nr_cpus=N`（有效且 `0<N<nr_cpu_ids`）在**早期**调 `set_nr_cpu_ids(N)`，源码称 hard limit；`maxcpus=N` 改的是 `setup_max_cpus`，用于激活数量，不能拿来替换 possible 身份范围。`setup_nr_cpu_ids()` 在 possible mask 形成后写入 `find_last_bit(..., NR_CPUS)+1`，即当时最高 possible **编号的上界**，不再是早期的入选数量。若稀疏 ID 为 0/2、早期名额为 2，后期边界为 3 本身不能算违反“至多两个入选”。`init/main.c:1530,1540` 与 `kernel/smp.c:970–989` 说明较晚才执行准备和 `smp_init`；旧包 `kernel/cpu.c:1908–1915` 显示通用 bringup 接收 `setup_max_cpus`，且串行分支以 **present mask** 为输入，不可声称它直接只消费 possible mask，也不能从本包断言 CPU 2 实际成功或失败上线。
3. 父版 `prom_64.c:434–466,481–498` 的 OF 枚举读取真实 `cpuid`，拒绝缺失／负编号并在 SMP 条件下跳过 `cpuid>=NR_CPUS`；回调把受理 ID 设入 present 与 possible。父版 `smp_64.c:1219–1231` 随后按 `num_possible_cpus()` **计数**重建 `[0,count)` 前缀并清掉其余位。子版 `prom_64.c:481–500` 仍把受理 ID 设入 present，但仅在 `num_possible_cpus()<nr_cpu_ids` 时把**该真实 ID**设入 possible；子版 `smp_64.c:1205–1220` 不再有旧整理函数。子版 `setup_64.c` 的调用删除只能引用先前已保存的修复差分，本次 6 份新增原文没有它的全文件；harness 不得制造“修复版同名整理函数”。`ncpus_probed++` 不是 possible 的去重计数，重复 ID 不应按它耗尽名额。
4. 旧包 `include/linux/cpumask.h:5–8,39–51,54–88,699–708,1004–1043,1114–1148` 是替身的精确分支依据。位图物理容量为 `NR_CPUS`，但 `nr_cpu_ids` 可是运行变量或在 `NR_CPUS==1`／`CONFIG_FORCE_NR_CPUS` 下为编译期常数；`num_possible_cpus()` 在 SMP 下为 `cpumask_weight`，它读取 `small_cpumask_bits`：`NR_CPUS<=BITS_PER_LONG` 时为 **NR_CPUS**，否则为 **nr_cpu_ids**。`for_each_cpu` 也按 `small_cpumask_bits` 扫描（`:278–283`）。所以不能无条件把计数／遍历写成 popcount `[0,nr_cpu_ids)`，也不能把 `NR_CPUS`、早期 `nr_cpu_ids`、后期 `nr_cpu_ids`、`maxcpus` 合并。`NR_CPUS==1` 时 `num_possible_cpus()` 恒为 1，本轮稀疏 SMP 实验应明确排除；`CONFIG_FORCE_NR_CPUS` 的 setter 仅检查是否等于固定 `NR_CPUS`，亦应单列不足，不静默使用可变分支。

## 执行前应固定的替身边界和有限输入

建议测试配置族先限 `CONFIG_SMP=1`、`CONFIG_FORCE_NR_CPUS=0`、`NR_CPUS>1`、OF 非 hypervisor、引导 CPU ID=0、引导初态 possible=present=online=`{0}`、`setup_max_cpus=NR_CPUS`（不提供 `maxcpus` 参数）；仅受理非负且 `<NR_CPUS` 的固定枚举序列。每次记录早期 `nr_cpu_ids`、原始 physical mask、`num_possible_cpus` 的**实际计数域**、父版后处理前/后或子版枚举后、`setup_nr_cpu_ids` 后边界及有效位遍历集合；观察点应在任何通用 bringup 前。`set_cpu_possible`／`set_cpu_present` 只改变指定身份位；`num_possible_cpus` 不得使用 `ncpus_probed` 或 present 计数。宿主替身须保留原函数的条件与循环，明确哪些宏／设备树操作由相同投影值代替；它只能检验这段源码在假定输入下的集合效果，不能证明这些输入是合法 SPARC 硬件或实际启动路径。

以下 **6 个输入 × 父/子两版 = 12 个版本/输入组合**，在运行前一次登记、不按结果换例；`small_bits` 列按假定 64 位字推得。`limit` 是传给早期 `nr_cpus` 的有效值；无参数时早期 `nr_cpu_ids=NR_CPUS`。每一组均从上述初态开始，序列含 boot ID 时只是重复置位。

| 输入 | `NR_CPUS` / `small_bits` | 早期 `nr_cpu_ids` | 固定受理顺序 | 用途 |
|---|---:|---:|---|---|
| I1 | 64 / 64 | 64 | 0,1 | 连续、无限制基线 |
| I2 | 64 / 64 | 64 | 0,2 | 报告中的稀疏编号形状；并非报告机器复现 |
| I3 | 64 / 64 | 64 | 2,0 | 同集合、不同枚举顺序；排除按顺序造前缀的替身 |
| I4 | 64 / 64 | `nr_cpus=2` | 0,2,4 | 数量限制下先受理 2，4 仍 present 但不预设 possible |
| I5 | 64 / 64 | `nr_cpus=2` | 0,4,2 | 相同候选集合但另一入选顺序；目标是保留**被选择的原编号**，非保留所有 present |
| I6 | 128 / 128（`small_bits=nr_cpu_ids`） | 128 | 0,2 | 覆盖大于字宽的计数分支，且本组不触及缩小后高编号的存储疑点 |

I4/I5 是**限定宿主投影**：当早期 `nr_cpu_ids=2` 而物理身份位 2/4 仍在 `NR_CPUS=64` 范围内时，源码的 `small_cpumask_bits` 仍为 64；这能说明旧／修订集合转换，但 `cpumask.h:5–8,22–27` 同时称通常仅 `nr_cpu_ids` 位有效。不可因此宣布该输入对应合法构建／设备树，也不能把后期 `nr_cpu_ids` 超过 2 直接判错。`NR_CPUS>BITS_PER_LONG` **且**早期 `nr_cpus` 小于稀疏高 ID 的组合没有纳入这 12 项：此时 `small_cpumask_bits=nr_cpu_ids` 可能漏计高位，动态 mask 容量／合法写入仍缺配置与分配证据，应标不足并停止，不借 I6 外推。重复 ID、无效 ID、`CONFIG_FORCE_NR_CPUS`、UP、hypervisor 分支也未被这 12 组覆盖。

条件检查只能比较“入选的**身份**集合和容量”，例如在已固定枚举顺序、初态与计数域下，子版没有凭空出现未提供的身份，并只保证达到名额前的已选择 ID 留在 possible；无限制且所有受理 ID 有效时可比较完整身份集合。不能用 `present==possible`、`nr_cpu_ids` 前后恒等、仅数量相等、或“无 WARN／函数返回 0”作契约真值。I4/I5 的 `present` 可以严格大于 possible；旧版前缀里出现未提供的 1 才是可检验的源级身份混淆。程序输出应把这些研究者后验条件、模型原始谓词、实际父/子源码行为分列；缺乏配置／调用链真值继续记不足。

以上 I1–I6 是执行前的审阅备选建议，并非本轮实际登记或执行组；实际计划仅以随后冻结的 `experiment_pre.json` 为准，其中 `NR_CPUS=8` 的 12 组未覆盖多字位图分支。
