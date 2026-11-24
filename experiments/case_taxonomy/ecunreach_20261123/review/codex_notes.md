# 第二审查人笔记

审查对象为 df2908090cda。本轮按候选编号计数，七条“可能”共享一个待核实的问题。

PowerPC 的 PAGE_NONE 保留 PRESENT。arch/powerpc/mm/book3s64/pgtable.c:229 合入保护位，第 252 行构造大页。六种修改在 arch/powerpc/include/asm/book3s/64/pgtable.h:900 至 905 分别处理访问、写或脏状态。R6 给出了没有修改时的对照。

RISC-V 的风险判断取决于原有映射。普通指令、读和写缺页受 arch/riscv/mm/fault.c:249 的 VMA 权限检查约束，因此不能假定无权限 VMA 会因普通缺页直接插入 PUD。另一条路径是对既有大页修改保护，mm/mprotect.c:609 至 612 区分拆分与整项更新。riscv64_thp 的配置同时打开 TRANSPARENT_HUGEPAGE 和 HAVE_ARCH_TRANSPARENT_HUGEPAGE_PUD。上述证据支持保留一条线索，尚未核实实际平台、映射提供方及后续观察结果。mm/debug_vm_pgtable.c:944 的大页断言采用第 1158 行初始化的 VM_ACCESS_FLAGS，不能将其直接套到所有保护常量。

规则 5 的“保持”只概括两端均确定的样本。设置访问位、清脏、写保护各有明确的目标状态；必须区分初始已满足目标与操作不能改变状态。R16、R17 中不确定的初值不能算作已观测到零。

此次仅作源码和配置审查，未运行内核。
