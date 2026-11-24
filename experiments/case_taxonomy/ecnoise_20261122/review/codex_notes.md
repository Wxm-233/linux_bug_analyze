# 第二审查人笔记

审查版本为 df2908090cda。候选包给出的 riscv64 与 arm_lpae 两份配置均关闭 CONFIG_TRANSPARENT_HUGEPAGE。两者在该配置上的零值都可以由源码解释。判定取决于开启透明大页后，同一个观察是否仍为零。

公共层在 mm/debug_vm_pgtable.c:904、909 检查编译和运行条件，在第 924 行从 PFN 和保护属性构造 PMD，在第 927～930 行对采用通用失效实现的架构直接检查这两个组合。第 914～922 行解释了大页拆分期间继续识别映射的理由。mm/huge_memory.c:2761 调用失效接口，mm/pgtable-generic.c:216 转入通用失效函数，第 205 行写入失效项，返回值则是旧项。

RISC-V 的叶掩码是读、写、执行位的并集（arch/riscv/include/asm/pgtable-bits.h:76）。即使 PAGE_NONE 也保留读位（arch/riscv/include/asm/pgtable.h:169）。第 775～783 行的两个变换都保留叶掩码内的位，开启透明大页后的 present 和 leaf 因此可以识别该项。

ARM LPAE 具备架构能力，mm/Kconfig:835～837 允许在具备该能力且关闭 PREEMPT_RT 时选择透明大页。arch/arm/include/asm/pgtable-3level-hwdef.h:18、21、22 分别给出类型掩码 3、节类型 1、表标志 2。arch/arm/include/asm/pgtable-3level.h:82 定义有效位为第 0 位。第 208 行清第 1 位，第 219 行再清第 0 位。PFN 高位不会改变这两个测试结果。第 195 行另有独立的 trans_huge 测试，非零项可通过该测试，公共层第 929、930 行仍分别要求 present 与 leaf 成立。

两条 ARM 线索是同一次位变换对两个公共接口的影响。结论来自静态核对，未编译或运行内核，未观测运行时告警。