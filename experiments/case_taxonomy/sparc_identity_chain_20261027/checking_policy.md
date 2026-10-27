# SPARC64 CPU身份—消费链检查政策（研究者登记）

2026-10-27。本文件登记本轮关系、依据和支持域，供既有`contract_protocol.py`账本引用。关系由研究者在已读案例及修复后写定，不是模型或程序自动推导。

## 依据

- `Documentation/admin-guide/kernel-parameters.txt`（修复版blob，4113—4120行）：`nr_cpus=n`限制内核支持n个处理器，并说明需据此预分配per-CPU启动内存。
- `arch/sparc/kernel/setup_64.c` setup_arch注释：OF/MDESC建立且nr_cpus解析后即“知道possible列表”，因此在这里分配IRQ栈；`alloc_irqstack_bootmem`以`for_each_possible_cpu`分配softirq/hardirq栈。
- `arch/sparc/kernel/kstack.h` `set_hardirq_stack`：直接取`hardirq_stack[smp_processor_id()]`并据此切换栈；`irq_64.c` handler_irq在每次硬中断调用它。
- `include/linux/cpumask.h`：`NR_CPUS<=BITS_PER_LONG`时`small_cpumask_bits=NR_CPUS`；更大时为运行时`nr_cpu_ids`。`cpumask_weight`和`for_each_cpu`都使用`small_cpumask_bits`。sparc64 Kconfig默认`NR_CPUS=4096`，sparc64_defconfig未覆盖。
- `kernel/smp.c`：`nrcpus`早期把`nr_cpu_ids`降为n；`setup_nr_cpu_ids`在setup_arch之后按possible最高位+1重定界。`kernel/cpu.c` `cpu_up`拒绝非possible CPU；`cpuhp_bringup_mask`遍历present。

## 关系

| 编号 | 关系 | 采样阶段 | 适用范围 |
| --- | --- | --- | --- |
| R1 | possible不含未提供的cpuid（本路径cpuid直接作位索引） | setup_nr_cpu_ids后 | 全部 |
| R2 | 给定nr_cpus=L时possible数量≤L | setup_nr_cpu_ids后 | 仅给定L |
| R3 | 不需截断（未给L或提供数≤L）时possible等于提供集合 | setup_nr_cpu_ids后 | 仅不需截断 |
| R4 | 每个被拉上线的CPU均已分配hardirq/softirq栈 | bringup后 | 全部 |
| R5 | 每个被拉上线的CPU均已有per-CPU偏移 | bringup后 | 全部 |

R2/R3只说明数量与身份保留，不规定截断时选哪几个cpuid。R4/R5是消费准备关系：采样在bringup之后，实际首次硬中断未被观察，因此deadline与whole_path保持不足。

## 支持域与不支持

- 证据层级为宿主源码投影：原函数体逐字包含，cpumask/bitmap、memblock、per-CPU与cpu_up只有显式替身；cpu_up只投影首个possible检查和上线标记，不执行副CPU、IPI、idle线程或中断。
- 输入{0,1}/{0,2}/{0,2,4}与L=2/none是构造条件；{0,2}形状来自历史报告，没有核实真实机器。投影不认证配置合法。
- 修复版违反只是候选，需要真实多CPU SPARC64平台或维护者确认；QEMU 8.2.2 sparc64机型仅支持1 CPU。
