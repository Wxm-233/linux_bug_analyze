# 待复核的问题（Linux v6.1，RISC-V）

## P00

**被标记的位置**：`arch/riscv/kernel/machine_kexec.c`中的`machine_shutdown`

**为什么**：本函数自己的关中断区间内

**程序给出的理由**：sleep A:irq: line 139 smp_shutdown_nonboot_cpus -> smp_shutdown_nonboot_cpus

**调用链**：
（直接调用）

## P01

**被标记的位置**：`arch/riscv/kernel/traps.c`中的`die`

**为什么**：本函数持有自旋锁的区间内

**程序给出的理由**：sleep A:spin: line 42 bust_spinlocks -> might_sleep

**调用链**：
- `bust_spinlocks`（lib/bust_spinlocks.c第25行调用`console_unblank`）
- `console_unblank`（kernel/printk/printk.c第2911行调用`console_lock`）
- `console_lock`（kernel/printk/printk.c第2565行调用`might_sleep`）

## P02

**被标记的位置**：`arch/riscv/include/asm/vdso/processor.h`中的`cpu_relax`

**为什么**：公共代码中标了noinstr或__cpuidle的函数，在可插桩区间之外调用了本函数，而参照架构的同名函数标了noinstr/__cpuidle/__always_inline

**程序给出的理由**：noinstr N1: line 12 cpu_relax -> called from noinstr/__cpuidle

**调用链**：
（直接调用）

## P03

**被标记的位置**：`arch/riscv/kernel/process.c`中的`arch_cpu_idle`

**为什么**：公共代码中标了noinstr或__cpuidle的函数，在可插桩区间之外调用了本函数，而参照架构的同名函数标了noinstr/__cpuidle/__always_inline

**程序给出的理由**：noinstr N1: line 40 arch_cpu_idle -> called from noinstr/__cpuidle

**调用链**：
（直接调用）
