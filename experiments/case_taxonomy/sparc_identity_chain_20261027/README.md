# SPARC64 CPU身份→possible→IRQ栈/per-CPU/bringup消费链（双位宽分支）

2026-10-27。按待办核固定SPARC历史版本的固件身份→possible构造→实际消费链，明确合法cpumask前提和阶段，并评估真实启动与工具限制。**本轮是已读案例的源码投影开发实验，没有SPARC内核构建、启动或模型调用。**

## 案例与新问题

父版`95706e717c4f55ca62025c151451ccc28863d085`，修复`98937707fea8375e8acea0aaa0b68a956dd52719`（v6.10-rc1，修复报告为Ultra 60上CPU编号0/2时只有CPU0上线）。主线`df2908090cda`（v7.3-rc2）的`record_one_cpu`与setup_arch顺序同修复版。

10/21的N2.18投影只用`NR_CPUS=8`，即`NR_CPUS<=BITS_PER_LONG`分支：`small_cpumask_bits=NR_CPUS`，并明确多字/动态位图分支未覆盖。本轮核实sparc64 Kconfig默认`NR_CPUS=4096`、defconfig未覆盖，落在另一分支：`cpumask_weight`和`for_each_cpu`只看运行时`nr_cpu_ids`以内的位。这正是合法cpumask前提要回答的问题。

## 源码链（修复版blob，行号见source_manifest.tsv与file_blobs.tsv）

1. `start_kernel`：`boot_cpu_init`→`setup_arch`→`setup_nr_cpu_ids`→`setup_per_cpu_areas`→…→`smp_init`。
2. `setup_arch`：`parse_early_param`（`nr_cpus=L`把`nr_cpu_ids`降为L）→`paging_init`→`of_populate_present_mask`→每个固件cpuid调用`record_one_cpu`（cpuid直接作位索引）→（父版`smp_fill_in_cpu_possible_map`改写为连续前缀）→`alloc_irqstack_bootmem`以`for_each_possible_cpu`分配softirq/hardirq栈。注释写明此时“已知possible列表”。
3. `setup_nr_cpu_ids`按possible最高位+1重定界；`setup_per_cpu_areas`以`for_each_possible_cpu`设per-CPU偏移。
4. `smp_init`→`cpuhp_bringup_mask(cpu_present_mask)`：先取`per_cpu_ptr(&cpuhp_state,cpu)`，再`cpu_up`；`cpu_up`拒绝非possible CPU。
5. 消费：`handler_irq`→`set_hardirq_stack`直接取`hardirq_stack[smp_processor_id()]`切栈。栈为NULL时会把栈指针切到`THREAD_SIZE-192-STACK_BIAS`附近的低地址；本轮未执行，实际后果未证。

因此在大NR_CPUS分支，修复版`num_possible_cpus() < nr_cpu_ids`只数L以内的位：L以外的稀疏cpuid不增加计数，会继续被设为possible；IRQ栈分配也在重定界前只遍历L以内的位。

## 平台与工具可行性

- QEMU上游v8.2.2：`hw/sparc64/sun4u.c`第813、841行（sun4u/sun4v）及`niagara.c`第166行均为`mc->max_cpus = 1; /* XXX for now */`；niagara另装载`1up-md.bin`/`1up-hv.bin`单CPU镜像。两文件原文存于`platform_sources/`（SHA256 sun4u `7780e552…b175c6`、niagara `8495688a…b972c9`）；Ubuntu二进制未安装、未核同源。
- 因此QEMU路线不能提供多CPU稀疏cpuid的SPARC64 guest；单CPU启动不能触发本关系。本机未装`qemu-system-sparc`与`gcc-sparc64-linux-gnu`（apt有8.2.2与13.2候选），本轮未安装。真实验证需要多CPU SPARC64硬件或能模拟它的平台。

## 方法

`extract_fragments.sh`从固定blob逐字提取13段函数（manifest含行号与SHA），`projection.c`直接`#include`其中9段编入执行：两版`record_one_cpu`、父版`smp_fill_in_cpu_possible_map`、两版`alloc_irqstack_bootmem`、`nrcpus`、`setup_nr_cpu_ids`、`cpuhp_bringup_mask`。cpumask/bitmap、memblock、per-CPU、cpu_up为显式替身；cpu_up只投影首个possible检查和上线标记，不执行副CPU、IPI或中断。两个位宽分支S64（NR_CPUS=64）与L4096（默认4096），父/修复，三组输入×L∈{none,2}，共4次宿主编译、24条记录。全部首次编译成功、退出0，未修源重跑。

关系R1—R5见[checking_policy.md](checking_policy.md)，经不变公共核心`contract_protocol.py`（SHA `42d37cc4…`）评价，共120次。采样分别在重定界后与bringup后；首次硬中断未观察，所有适用项deadline均为不足。

## 结果

| 版本 | 分支 | 违反（24条×5关系中的） |
| --- | --- | --- |
| 父版 | S64 | 7：{0,2}/{0,2,4}的R1身份及R3保留 |
| 父版 | L4096 | 5：同类，但{0,2}/L=2时possible变为{0}，R1转满足、R3仍违反 |
| 修复 | S64 | 0 |
| 修复 | L4096 | 3：{0,2}/L=2的R4；{0,2,4}/L=2的R2与R4 |

关键记录：

- 修复L4096，{0,2}，nr_cpus=2：possible={0,2}，IRQ栈只分配给0，nr_cpu_ids 2→3，CPU2被bringup上线 → R4违反。S64同输入IRQ栈{0,2}，全部满足。
- 修复L4096，{0,2,4}，nr_cpus=2：possible={0,2,4}（3>L）、nr_cpu_ids→5，IRQ栈只有0，三个CPU上线 → R2、R4违反。S64同输入possible={0,2}，CPU4被cpu_up拒绝。
- 父版L4096，{0,2}未给L：possible={0,1}、nr_cpu_ids=2，bringup只遍历2以内present位，CPU2既不上线也不触发cpu_up拒绝信息；S64同输入会对CPU2打印拒绝。二者都与“只有CPU0上线”一致，可观察信息不同；历史机器的实际配置与日志未知。
- 两分支相同输入有4组判定或possible不同，说明位宽分支是该接口的有效适用条件，不能只用小NR_CPUS投影代表默认配置。
- 只检查数量的谓词在24条中21条通过，其中7条存在R1或R4违反（含修复L4096 {0,2}/L=2）。
- 诊断：L4096下有若干次`set_cpu_present/possible`写入不小于当时`small_cpumask_bits`的位，在DEBUG_PER_CPU_MAPS下会触发`cpu_max_bits_warn`；S64修复版{0,2,4}/L=2中CPU4先被`per_cpu_ptr`访问，再被拒绝，此时其per-CPU偏移未设置。二者都只是替身标记，实际后果未证。

10项构造控制全部符合预期：缺事实、借另一分支上下文、未审模型事实、版本错配、期限非消费事件、合成未开启均不足；合成反例/正常/超限/无L范围分别为违反/满足/违反/不适用。

## 结论边界

- 新增认识：SPARC身份契约须把**cpumask位宽分支与nr_cpus早期定界的阶段**作为显式适用条件；同一修复在小NR_CPUS分支满足，在sparc64默认大NR_CPUS分支投影出IRQ栈准备缺失和数量限制失效。
- 修复版/主线候选只到源码投影层级，**不是确认的Linux缺陷**；未核实`nr_cpus`小于最大稀疏cpuid的真实机器是否常见，也未查询上游是否已有报告或补丁。若要外报或确认，需要真实多CPU SPARC64或维护者复核，需用户另行决定。
- 已读案例、研究者在看修复后写定关系、程序只评价登记关系：不是N1自动推导或独立检测；独立正例/正常仍0/0。
- 首轮analysis把not_applicable计入deadline汇总导致汇总字段为false，判定本身未变；原结果保存在`analysis_attempt1/`，修正汇总后重跑为`analysis/`。

## 文件

`frozen_plan.json`（执行前）、`extract_fragments.sh`、`fragments/`、`source_manifest.tsv`、`file_blobs.tsv`、`projection.c`、`run_projection.py`、`attempt1/`（24条原始stdout与execution.json）、`checking_policy.md`、`analyze.py`、`analysis/`、`analysis_attempt1/`、`check_controls.py`、`controls/`、`delivery_manifest.json`。
