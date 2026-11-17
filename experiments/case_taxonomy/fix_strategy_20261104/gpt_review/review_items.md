# 修复方式标注复核材料

下面30条都是Linux内核中的跨架构缺陷修复提交（缺陷只在RISC-V或部分架构上出现）。请对每条独立判断以下字段，不要参考任何已有标注。每条给出“对应物”，即其他架构或公共代码中处理同一条件的代码位置。

## 二、标注字段（第一标注人：模型Claude，逐条读改动后标）

| 字段 | 取值 | 说明 |
| --- | --- | --- |
| `action` | 修复动作，见第三节，可多选，第一个为主动作 | 改动实际做了什么 |
| `follow` | F1 照对应物补齐；F2 部分照搬；F3 另行实现；F4 无可照的对应物 | 修复后，RISC-V处理这个条件的方式与对应物的关系 |
| `layer` | A 架构代码；C 公共代码；AC 两者都改 | 按改动的文件判断，构建文件按其所在目录 |
| `cites` | Y / N | 提交说明是否明确提到其他架构或公共代码中的同类做法（如“like arm64”“as x86 does”） |
| `note` | 一句话 | 修复要点 |

`follow`的判断：
- **F1**：对应物处理同一条件的方式，修复后RISC-V在该条件上与它一致，允许名字、寄存器等架构差异。
- **F2**：修复只覆盖了对应物所处理条件的一部分，并且能在修复后的代码中指出遗漏的部分。
- **F3**：有对应物，但修复按RISC-V自身情况采用了不同做法。
- **F4**：没有可照的做法，包括对应物当时也错（S2），或其他架构没有这个功能（S3）。

## 定稿的修复动作（替换原第三节）

| 代码 | 动作 | 定义 |
| --- | --- | --- |
| A1 补检查或防护 | 参数、空指针或范围检查，`array_index_nospec`，能力或特性检查 | 拒绝或钳住不该处理的输入 |
| A2 调整顺序或时机 | 调用先后、初始化或拆除顺序、生成指令的先后 | 改动只改变先后，不增删处理 |
| A3 改执行上下文 | 开或关中断、把可能睡眠的操作移出锁区或避开早期启动、避免在该场合取锁 | 让操作符合当前场合的限制 |
| A4 补缺失的处理 | 补调用、补条件分支、实现钩子或覆盖公共默认实现、补遗漏的情形 | 原来漏掉了某种情况或某一步 |
| A5 改接口参数、属性或标注 | 加flag或属性位，改节区、`noinstr`、`__always_inline`等标注，改用正确的宏 | 调用和流程不变，只改调用时给的参数或代码的属性 |
| A6 改配置或构建条件 | Kconfig的select/depends、Makefile、按编译器能力的条件编译 | — |
| A7 改数值、类型、宽度、对齐或边界 | 常量、类型宽度、符号扩展、对齐、比较的边界、可用地址范围 | — |
| A8 补资源释放或状态恢复 | 出错路径释放、卸载时恢复原状态 | — |
| A9 删除错误的处理 | 删掉基于错误假设的代码 | — |
| A10 换信息来源 | 从可靠来源取值（传入参数、保存的值），不再从不可靠来源推断 | — |
| A11 补同步与内存顺序 | 内存屏障、原子操作的有序性、加锁保护并发访问 | 处理多个执行者之间的并发 |
| A0 其他 | 以上都不合适，写明 | — |

## `follow`的补充规则（补充第二节）

- **F1**：修复后，RISC-V处理这个条件的方式与对应物一致。对应物是公共约定（K1）时，遵守了这条约定也算F1。
- **F4**：修复时没有可照的正确做法。包括对应物当时也错、与RISC-V在同一组补丁中一起修（如A301），以及其他架构没有这个功能。
- **其他架构先修、RISC-V后照着修**：即使样本集标的是S2，只要修复时对应物已经正确，仍按F1或F2判（如A379）。

测试集108条按本修订标注。遇到放不下的情况标A0并写明，不再改分类。

请按如下格式逐条回答：`编号 | action（主动作在前） | follow | layer | cites | 一句话理由`

## 1. A003
对应物：kernel/events/uprobes.c:is_trap_insn（__weak默认）；arch/powerpc/kernel/uprobes.c:is_trap_insn

```
##### A003 b701f9e726f0 riscv: provide riscv-specific is_trap_insn()
--- 说明 ---
riscv: provide riscv-specific is_trap_insn()
uprobes expects is_trap_insn() to return true for any trap instructions,
not just the one used for installing uprobe. The current default
implementation only returns true for 16-bit c.ebreak if C extension is
enabled. This can confuse uprobes if a 32-bit ebreak generates a trap
exception from userspace: uprobes asks is_trap_insn() who says there is no
trap, so uprobes assume a probe was there before but has been removed, and
return to the trap instruction. This causes an infinite loop of entering
and exiting trap handler.
Instead of using the default implementation, implement this function
speficially for riscv with checks for both ebreak and c.ebreak.
Fixes: 74784081aac8 ("riscv: Add uprobes supported")
Signed-off-by: Nam Cao <namcaov@gmail.com>
Tested-by: Björn Töpel <bjorn@rivosinc.com>
--- 改动 ---
diff --git a/arch/riscv/kernel/probes/uprobes.c b/arch/riscv/kernel/probes/uprobes.c
index 194f166b2cc4..4b3dc8beaf77 100644
--- a/arch/riscv/kernel/probes/uprobes.c
+++ b/arch/riscv/kernel/probes/uprobes.c
@@ -3,6 +3,7 @@
 #include <linux/highmem.h>
 #include <linux/ptrace.h>
 #include <linux/uprobes.h>
+#include <asm/insn.h>
 
 #include "decode-insn.h"
 
@@ -17,6 +18,11 @@ bool is_swbp_insn(uprobe_opcode_t *insn)
 #endif
 }
 
+bool is_trap_insn(uprobe_opcode_t *insn)
+{
+	return riscv_insn_is_ebreak(*insn) || riscv_insn_is_c_ebreak(*insn);
+}
+
 unsigned long uprobe_get_swbp_addr(struct pt_regs *regs)
 {
 	return instruction_pointer(regs);
```

## 2. A029
对应物：arch/arm64/include/asm/tlb.h:__pmd_free_tlb（经tlb_remove_ptdesc延迟释放并刷新）

```
##### A029 8246601a7d39 riscv: tlb: fix __p*d_free_tlb()
--- 说明 ---
riscv: tlb: fix __p*d_free_tlb()
If non-leaf PTEs I.E pmd, pud or p4d is modified, a sfence.vma is
a must for safe, imagine if an implementation caches the non-leaf
translation in TLB, although I didn't meet this HW so far, but it's
possible in theory.
Signed-off-by: Jisheng Zhang <jszhang@kernel.org>
Fixes: c5e9b2c2ae82 ("riscv: Improve tlb_flush()")
Link: https://lore.kernel.org/r/20231219175046.2496-2-jszhang@kernel.org
Signed-off-by: Palmer Dabbelt <palmer@rivosinc.com>
--- 改动 ---
diff --git a/arch/riscv/include/asm/pgalloc.h b/arch/riscv/include/asm/pgalloc.h
index d169a4f41a2e..c80bb9990d32 100644
--- a/arch/riscv/include/asm/pgalloc.h
+++ b/arch/riscv/include/asm/pgalloc.h
@@ -95,7 +95,13 @@ static inline void pud_free(struct mm_struct *mm, pud_t *pud)
 		__pud_free(mm, pud);
 }
 
-#define __pud_free_tlb(tlb, pud, addr)  pud_free((tlb)->mm, pud)
+#define __pud_free_tlb(tlb, pud, addr)					\
+do {									\
+	if (pgtable_l4_enabled) {					\
+		pagetable_pud_dtor(virt_to_ptdesc(pud));		\
+		tlb_remove_page_ptdesc((tlb), virt_to_ptdesc(pud));	\
+	}								\
+} while (0)
 
 #define p4d_alloc_one p4d_alloc_one
 static inline p4d_t *p4d_alloc_one(struct mm_struct *mm, unsigned long addr)
@@ -124,7 +130,11 @@ static inline void p4d_free(struct mm_struct *mm, p4d_t *p4d)
 		__p4d_free(mm, p4d);
 }
 
-#define __p4d_free_tlb(tlb, p4d, addr)  p4d_free((tlb)->mm, p4d)
+#define __p4d_free_tlb(tlb, p4d, addr)					\
+do {									\
+	if (pgtable_l5_enabled)						\
+		tlb_remove_page_ptdesc((tlb), virt_to_ptdesc(p4d));	\
+} while (0)
 #endif /* __PAGETABLE_PMD_FOLDED */
 
 static inline void sync_kernel_mappings(pgd_t *pgd)
@@ -149,7 +159,11 @@ static inline pgd_t *pgd_alloc(struct mm_struct *mm)
 
 #ifndef __PAGETABLE_PMD_FOLDED
 
-#define __pmd_free_tlb(tlb, pmd, addr)  pmd_free((tlb)->mm, pmd)
+#define __pmd_free_tlb(tlb, pmd, addr)				\
+do {								\
+	pagetable_pmd_dtor(virt_to_ptdesc(pmd));		\
+	tlb_remove_page_ptdesc((tlb), virt_to_ptdesc(pmd));	\
+} while (0)
 
 #endif /* __PAGETABLE_PMD_FOLDED */
```

## 3. A032
对应物：arch/x86/mm/fault.c:do_user_addr_fault（同一提交同改）

```
##### A032 46e714c729c8 arch/mm/fault: fix major fault accounting when retrying under per-VMA lock
--- 说明 ---
arch/mm/fault: fix major fault accounting when retrying under per-VMA lock
A test [1] in Android test suite started failing after [2] was merged.  It
turns out that after handling a major fault under per-VMA lock, the
process major fault counter does not register that fault as major.  Before
[2] read faults would be done under mmap_lock, in which case
FAULT_FLAG_TRIED flag is set before retrying.  That in turn causes
mm_account_fault() to account the fault as major once retry completes. 
With per-VMA locks we often retry because a fault can't be handled without
locking the whole mm using mmap_lock.  Therefore such retries do not set
FAULT_FLAG_TRIED flag.  This logic does not work after [2] because we can
now handle read major faults under per-VMA lock and upon retry the fact
there was a major fault gets lost.  Fix this by setting FAULT_FLAG_TRIED
after retrying under per-VMA lock if VM_FAULT_MAJOR was returned.  Ideally
we would use an additional VM_FAULT bit to indicate the reason for the
--- 改动 ---
diff --git a/arch/arm64/mm/fault.c b/arch/arm64/mm/fault.c
index 460d799e1296..55f6455a8284 100644
--- a/arch/arm64/mm/fault.c
+++ b/arch/arm64/mm/fault.c
@@ -607,6 +607,8 @@ static int __kprobes do_page_fault(unsigned long far, unsigned long esr,
 		goto done;
 	}
 	count_vm_vma_lock_event(VMA_LOCK_RETRY);
+	if (fault & VM_FAULT_MAJOR)
+		mm_flags |= FAULT_FLAG_TRIED;
 
 	/* Quick path to respond to signals */
 	if (fault_signal_pending(fault, regs)) {
diff --git a/arch/powerpc/mm/fault.c b/arch/powerpc/mm/fault.c
index 9e49ede2bc1c..53335ae21a40 100644
--- a/arch/powerpc/mm/fault.c
+++ b/arch/powerpc/mm/fault.c
@@ -497,6 +497,8 @@ static int ___do_page_fault(struct pt_regs *regs, unsigned long address,
 		goto done;
 	}
 	count_vm_vma_lock_event(VMA_LOCK_RETRY);
+	if (fault & VM_FAULT_MAJOR)
+		flags |= FAULT_FLAG_TRIED;
 
 	if (fault_signal_pending(fault, regs))
 		return user_mode(regs) ? 0 : SIGBUS;
diff --git a/arch/riscv/mm/fault.c b/arch/riscv/mm/fault.c
index 90d4ba36d1d0..081339ddf47e 100644
--- a/arch/riscv/mm/fault.c
+++ b/arch/riscv/mm/fault.c
@@ -304,6 +304,8 @@ void handle_page_fault(struct pt_regs *regs)
 		goto done;
 	}
 	count_vm_vma_lock_event(VMA_LOCK_RETRY);
+	if (fault & VM_FAULT_MAJOR)
+		flags |= FAULT_FLAG_TRIED;
 
 	if (fault_signal_pending(fault, regs)) {
 		if (!user_mode(regs))
diff --git a/arch/s390/mm/fault.c b/arch/s390/mm/fault.c
index 249aefcf7c4e..ab4098886e56 100644
--- a/arch/s390/mm/fault.c
+++ b/arch/s390/mm/fault.c
@@ -337,6 +337,9 @@ static void do_exception(struct pt_regs *regs, int access)
 		return;
 	}
 	count_vm_vma_lock_event(VMA_LOCK_RETRY);
+	if (fault & VM_FAULT_MAJOR)
+		flags |= FAULT_FLAG_TRIED;
+
 	/* Quick path to respond to signals */
 	if (fault_signal_pending(fault, regs)) {
 		if (!user_mode(regs))
diff --git a/arch/x86/mm/fault.c b/arch/x86/mm/fault.c
index ab778eac1952..679b09cfe241 100644
--- a/arch/x86/mm/fault.c
+++ b/arch/x86/mm/fault.c
@@ -1370,6 +1370,8 @@ void do_user_addr_fault(struct pt_regs *regs,
 		goto done;
 	}
 	count_vm_vma_lock_event(VMA_LOCK_RETRY);
+	if (fault & VM_FAULT_MAJOR)
+		flags |= FAULT_FLAG_TRIED;
 
 	/* Quick path to respond to signals */
 	if (fault_signal_pending(fault, regs)) {
```

## 4. A043
对应物：arch/x86/mm/tlb.c:arch_tlbbatch_flush（cpumask_clear）

```
##### A043 3951f6add519 riscv: Fix arch_tlbbatch_flush() by clearing the batch cpumask
--- 说明 ---
riscv: Fix arch_tlbbatch_flush() by clearing the batch cpumask
We must clear the cpumask once we have flushed the batch, otherwise cpus
get accumulated and we end sending IPIs to more cpus than needed.
Fixes: 54d7431af73e ("riscv: Add support for BATCHED_UNMAP_TLB_FLUSH")
Signed-off-by: Alexandre Ghiti <alexghiti@rivosinc.com>
Reviewed-by: Charlie Jenkins <charlie@rivosinc.com>
Reviewed-by: Jisheng Zhang <jszhang@kernel.org>
Link: https://lore.kernel.org/r/20240130115508.105386-1-alexghiti@rivosinc.com
Signed-off-by: Palmer Dabbelt <palmer@rivosinc.com>
--- 改动 ---
diff --git a/arch/riscv/mm/tlbflush.c b/arch/riscv/mm/tlbflush.c
index dffb0e5bd942..893566e004b7 100644
--- a/arch/riscv/mm/tlbflush.c
+++ b/arch/riscv/mm/tlbflush.c
@@ -234,4 +234,5 @@ void arch_tlbbatch_flush(struct arch_tlbflush_unmap_batch *batch)
 {
 	__flush_tlb_range(&batch->cpumask, FLUSH_TLB_NO_ASID, 0,
 			  FLUSH_TLB_MAX_SIZE, PAGE_SIZE);
+	cpumask_clear(&batch->cpumask);
 }
```

## 5. A058
对应物：arch/arm64/include/asm/pgtable.h:vmemmap（减去memstart_addr对应的页号）

```
##### A058 a11dd49dcb93 riscv: Sparse-Memory/vmemmap out-of-bounds fix
--- 说明 ---
riscv: Sparse-Memory/vmemmap out-of-bounds fix
Offset vmemmap so that the first page of vmemmap will be mapped
to the first page of physical memory in order to ensure that
vmemmap’s bounds will be respected during
pfn_to_page()/page_to_pfn() operations.
The conversion macros will produce correct SV39/48/57 addresses
for every possible/valid DRAM_BASE inside the physical memory limits.
v2:Address Alex's comments
Suggested-by: Alexandre Ghiti <alexghiti@rivosinc.com>
Signed-off-by: Dimitris Vlachos <dvlachos@ics.forth.gr>
Reported-by: Dimitris Vlachos <dvlachos@ics.forth.gr>
Closes: https://lore.kernel.org/linux-riscv/20240202135030.42265-1-csd4492@csd.uoc.gr
Fixes: d95f1a542c3d ("RISC-V: Implement sparsemem")
Reviewed-by: Alexandre Ghiti <alexghiti@rivosinc.com>
--- 改动 ---
diff --git a/arch/riscv/include/asm/pgtable.h b/arch/riscv/include/asm/pgtable.h
index 89f5f1bd6e46..6066822e7396 100644
--- a/arch/riscv/include/asm/pgtable.h
+++ b/arch/riscv/include/asm/pgtable.h
@@ -84,7 +84,7 @@
  * Define vmemmap for pfn_to_page & page_to_pfn calls. Needed if kernel
  * is configured with CONFIG_SPARSEMEM_VMEMMAP enabled.
  */
-#define vmemmap		((struct page *)VMEMMAP_START)
+#define vmemmap		((struct page *)VMEMMAP_START - (phys_ram_base >> PAGE_SHIFT))
 
 #define PCI_IO_SIZE      SZ_16M
 #define PCI_IO_END       VMEMMAP_START
```

## 6. A069
对应物：arch/arm64/kernel/patching.c:__aarch64_insn_write（raw_spin_lock_irqsave(&patch_lock)）

```
##### A069 a370c2419e46 riscv: Disable preemption when using patch_map()
--- 说明 ---
riscv: Disable preemption when using patch_map()
patch_map() uses fixmap mappings to circumvent the non-writability of
the kernel text mapping.
The __set_fixmap() function only flushes the current cpu tlb, it does
not emit an IPI so we must make sure that while we use a fixmap mapping,
the current task is not migrated on another cpu which could miss the
newly introduced fixmap mapping.
So in order to avoid any task migration, disable the preemption.
Reported-by: Andrea Parri <andrea@rivosinc.com>
Closes: https://lore.kernel.org/all/ZcS+GAaM25LXsBOl@andrea/
Reported-by: Andy Chiu <andy.chiu@sifive.com>
Closes: https://lore.kernel.org/linux-riscv/CABgGipUMz3Sffu-CkmeUB1dKVwVQ73+7=sgC45-m0AE9RCjOZg@mail.gmail.com/
Fixes: cad539baa48f ("riscv: implement a memset like function for text")
Fixes: 0ff7c3b33127 ("riscv: Use text_mutex instead of patch_lock")
--- 改动 ---
diff --git a/arch/riscv/kernel/patch.c b/arch/riscv/kernel/patch.c
index 37e87fdcf6a0..30e12b310cab 100644
--- a/arch/riscv/kernel/patch.c
+++ b/arch/riscv/kernel/patch.c
@@ -80,6 +80,8 @@ static int __patch_insn_set(void *addr, u8 c, size_t len)
 	 */
 	lockdep_assert_held(&text_mutex);
 
+	preempt_disable();
+
 	if (across_pages)
 		patch_map(addr + PAGE_SIZE, FIX_TEXT_POKE1);
 
@@ -92,6 +94,8 @@ static int __patch_insn_set(void *addr, u8 c, size_t len)
 	if (across_pages)
 		patch_unmap(FIX_TEXT_POKE1);
 
+	preempt_enable();
+
 	return 0;
 }
 NOKPROBE_SYMBOL(__patch_insn_set);
@@ -122,6 +126,8 @@ static int __patch_insn_write(void *addr, const void *insn, size_t len)
 	if (!riscv_patch_in_stop_machine)
 		lockdep_assert_held(&text_mutex);
 
+	preempt_disable();
+
 	if (across_pages)
 		patch_map(addr + PAGE_SIZE, FIX_TEXT_POKE1);
 
@@ -134,6 +140,8 @@ static int __patch_insn_write(void *addr, const void *insn, size_t len)
 	if (across_pages)
 		patch_unmap(FIX_TEXT_POKE1);
 
+	preempt_enable();
+
 	return ret;
 }
 NOKPROBE_SYMBOL(__patch_insn_write);
```

## 7. A081
对应物：arch/arm64/include/asm/cmpxchg.h:__XCHG_CASE(mb_,8/16，dmb ish)

```
##### A081 1d84afaf0252 riscv: Fix fully ordered LR/SC xchg[8|16]() implementations
--- 说明 ---
riscv: Fix fully ordered LR/SC xchg[8|16]() implementations
The fully ordered versions of xchg[8|16]() using LR/SC lack the
necessary memory barriers to guarantee the order.
Fix this by matching what is already implemented in the fully ordered
versions of cmpxchg() using LR/SC.
Suggested-by: Andrea Parri <parri.andrea@gmail.com>
Reported-by: Andrea Parri <parri.andrea@gmail.com>
Closes: https://lore.kernel.org/linux-riscv/ZlYbupL5XgzgA0MX@andrea/T/#u
Fixes: a8ed2b7a2c13 ("riscv/cmpxchg: Implement xchg for variables of size 1 and 2")
Signed-off-by: Alexandre Ghiti <alexghiti@rivosinc.com>
Reviewed-by: Andrea Parri <parri.andrea@gmail.com>
Link: https://lore.kernel.org/r/20240530145546.394248-1-alexghiti@rivosinc.com
Signed-off-by: Palmer Dabbelt <palmer@rivosinc.com>
--- 改动 ---
diff --git a/arch/riscv/include/asm/cmpxchg.h b/arch/riscv/include/asm/cmpxchg.h
index ddb002ed89de..808b4c78462e 100644
--- a/arch/riscv/include/asm/cmpxchg.h
+++ b/arch/riscv/include/asm/cmpxchg.h
@@ -10,7 +10,7 @@
 
 #include <asm/fence.h>
 
-#define __arch_xchg_masked(prepend, append, r, p, n)			\
+#define __arch_xchg_masked(sc_sfx, prepend, append, r, p, n)		\
 ({									\
 	u32 *__ptr32b = (u32 *)((ulong)(p) & ~0x3);			\
 	ulong __s = ((ulong)(p) & (0x4 - sizeof(*p))) * BITS_PER_BYTE;	\
@@ -25,7 +25,7 @@
 	       "0:	lr.w %0, %2\n"					\
 	       "	and  %1, %0, %z4\n"				\
 	       "	or   %1, %1, %z3\n"				\
-	       "	sc.w %1, %1, %2\n"				\
+	       "	sc.w" sc_sfx " %1, %1, %2\n"			\
 	       "	bnez %1, 0b\n"					\
 	       append							\
 	       : "=&r" (__retx), "=&r" (__rc), "+A" (*(__ptr32b))	\
@@ -46,7 +46,8 @@
 		: "memory");						\
 })
 
-#define _arch_xchg(ptr, new, sfx, prepend, append)			\
+#define _arch_xchg(ptr, new, sc_sfx, swap_sfx, prepend,			\
+		   sc_append, swap_append)				\
 ({									\
 	__typeof__(ptr) __ptr = (ptr);					\
 	__typeof__(*(__ptr)) __new = (new);				\
@@ -55,15 +56,15 @@
 	switch (sizeof(*__ptr)) {					\
 	case 1:								\
 	case 2:								\
-		__arch_xchg_masked(prepend, append,			\
+		__arch_xchg_masked(sc_sfx, prepend, sc_append,		\
 				   __ret, __ptr, __new);		\
 		break;							\
 	case 4:								\
-		__arch_xchg(".w" sfx, prepend, append,			\
+		__arch_xchg(".w" swap_sfx, prepend, swap_append,	\
 			      __ret, __ptr, __new);			\
 		break;							\
 	case 8:								\
-		__arch_xchg(".d" sfx, prepend, append,			\
+		__arch_xchg(".d" swap_sfx, prepend, swap_append,	\
 			      __ret, __ptr, __new);			\
 		break;							\
 	default:							\
@@ -73,16 +74,17 @@
 })
 
 #define arch_xchg_relaxed(ptr, x)					\
-	_arch_xchg(ptr, x, "", "", "")
+	_arch_xchg(ptr, x, "", "", "", "", "")
 
 #define arch_xchg_acquire(ptr, x)					\
-	_arch_xchg(ptr, x, "", "", RISCV_ACQUIRE_BARRIER)
+	_arch_xchg(ptr, x, "", "", "",					\
+		   RISCV_ACQUIRE_BARRIER, RISCV_ACQUIRE_BARRIER)
 
 #define arch_xchg_release(ptr, x)					\
-	_arch_xchg(ptr, x, "", RISCV_RELEASE_BARRIER, "")
+	_arch_xchg(ptr, x, "", "", RISCV_RELEASE_BARRIER, "", "")
 
 #define arch_xchg(ptr, x)						\
-	_arch_xchg(ptr, x, ".aqrl", "", "")
+	_arch_xchg(ptr, x, ".rl", ".aqrl", "", RISCV_FULL_BARRIER, "")
 
 #define xchg32(ptr, x)							\
 ({									\
```

## 8. A094
对应物：arch/arm64/kernel/patching.c:aarch64_insn_patch_text_nosync

```
##### A094 ee9a68394b4b riscv: Re-introduce global icache flush in patch_text_XXX()
--- 说明 ---
riscv: Re-introduce global icache flush in patch_text_XXX()
commit edf2d546bfd6 ("riscv: patch: Flush the icache right after
patching to avoid illegal insns") mistakenly removed the global icache
flush in patch_text_nosync() and patch_text_set_nosync() functions, so
reintroduce them.
Fixes: edf2d546bfd6 ("riscv: patch: Flush the icache right after patching to avoid illegal insns")
Reported-by: Samuel Holland <samuel.holland@sifive.com>
Closes: https://lore.kernel.org/linux-riscv/a28ddc26-d77a-470a-a33f-88144f717e86@sifive.com/
Signed-off-by: Alexandre Ghiti <alexghiti@rivosinc.com>
Reviewed-by: Samuel Holland <samuel.holland@sifive.com>
Reviewed-by: Charlie Jenkins <charlie@rivosinc.com>
Link: https://lore.kernel.org/r/20240801191404.55181-1-alexghiti@rivosinc.com
Signed-off-by: Palmer Dabbelt <palmer@rivosinc.com>
--- 改动 ---
diff --git a/arch/riscv/kernel/patch.c b/arch/riscv/kernel/patch.c
index 69e5796fc51f..34ef522f07a8 100644
--- a/arch/riscv/kernel/patch.c
+++ b/arch/riscv/kernel/patch.c
@@ -205,6 +205,8 @@ int patch_text_set_nosync(void *addr, u8 c, size_t len)
 	int ret;
 
 	ret = patch_insn_set(addr, c, len);
+	if (!ret)
+		flush_icache_range((uintptr_t)addr, (uintptr_t)addr + len);
 
 	return ret;
 }
@@ -239,6 +241,8 @@ int patch_text_nosync(void *addr, const void *insns, size_t len)
 	int ret;
 
 	ret = patch_insn_write(addr, insns, len);
+	if (!ret)
+		flush_icache_range((uintptr_t)addr, (uintptr_t)addr + len);
 
 	return ret;
 }
```

## 9. A113
对应物：arch/arm64/kernel/vdso/Makefile（-fno-builtin）

```
##### A113 bf40167d54d5 riscv: vdso: Prevent the compiler from inserting calls to memset()
--- 说明 ---
riscv: vdso: Prevent the compiler from inserting calls to memset()
The compiler is smart enough to insert a call to memset() in
riscv_vdso_get_cpus(), which generates a dynamic relocation.
So prevent this by using -fno-builtin option.
Fixes: e2c0cdfba7f6 ("RISC-V: User-facing API")
Cc: stable@vger.kernel.org
Signed-off-by: Alexandre Ghiti <alexghiti@rivosinc.com>
Reviewed-by: Guo Ren <guoren@kernel.org>
Link: https://lore.kernel.org/r/20241016083625.136311-2-alexghiti@rivosinc.com
Signed-off-by: Palmer Dabbelt <palmer@rivosinc.com>
--- 改动 ---
diff --git a/arch/riscv/kernel/vdso/Makefile b/arch/riscv/kernel/vdso/Makefile
index 960feb1526ca..3f1c4b2d0b06 100644
--- a/arch/riscv/kernel/vdso/Makefile
+++ b/arch/riscv/kernel/vdso/Makefile
@@ -18,6 +18,7 @@ obj-vdso = $(patsubst %, %.o, $(vdso-syms)) note.o
 
 ccflags-y := -fno-stack-protector
 ccflags-y += -DDISABLE_BRANCH_PROFILING
+ccflags-y += -fno-builtin
 
 ifneq ($(c-gettimeofday-y),)
   CFLAGS_vgettimeofday.o += -fPIC -include $(c-gettimeofday-y)
```

## 10. A115
对应物：drivers/of/kexec.c:of_kexec_alloc_and_setup_fdt（__pa(initial_boot_params)）

```
##### A115 b2473a359763 of/fdt: add dt_phys arg to early_init_dt_scan and early_init_dt_verify
--- 说明 ---
of/fdt: add dt_phys arg to early_init_dt_scan and early_init_dt_verify
 __pa() is only intended to be used for linear map addresses and using
it for initial_boot_params which is in fixmap for arm64 will give an
incorrect value. Hence save the physical address when it is known at
boot time when calling early_init_dt_scan for arm64 and use it at kexec
time instead of converting the virtual address using __pa().
Note that arm64 doesn't need the FDT region reserved in the DT as the
kernel explicitly reserves the passed in FDT. Therefore, only a debug
warning is fixed with this change.
Reported-by: Breno Leitao <leitao@debian.org>
Suggested-by: Mark Rutland <mark.rutland@arm.com>
Signed-off-by: Usama Arif <usamaarif642@gmail.com>
Fixes: ac10be5cdbfa ("arm64: Use common of_kexec_alloc_and_setup_fdt()")
Link: https://lore.kernel.org/r/20241023171426.452688-1-usamaarif642@gmail.com
--- 改动 ---
diff --git a/arch/arc/kernel/devtree.c b/arch/arc/kernel/devtree.c
index 4c9e61457b2f..cc6ac7d128aa 100644
--- a/arch/arc/kernel/devtree.c
+++ b/arch/arc/kernel/devtree.c
@@ -62,7 +62,7 @@ const struct machine_desc * __init setup_machine_fdt(void *dt)
 	const struct machine_desc *mdesc;
 	unsigned long dt_root;
 
-	if (!early_init_dt_scan(dt))
+	if (!early_init_dt_scan(dt, __pa(dt)))
 		return NULL;
 
 	mdesc = of_flat_dt_match_machine(NULL, arch_get_next_mach);
diff --git a/arch/arm/kernel/devtree.c b/arch/arm/kernel/devtree.c
index fdb74e64206a..3b78966e750a 100644
--- a/arch/arm/kernel/devtree.c
+++ b/arch/arm/kernel/devtree.c
@@ -200,7 +200,7 @@ const struct machine_desc * __init setup_machine_fdt(void *dt_virt)
 
 	mdesc_best = &__mach_desc_GENERIC_DT;
 
-	if (!dt_virt || !early_init_dt_verify(dt_virt))
+	if (!dt_virt || !early_init_dt_verify(dt_virt, __pa(dt_virt)))
 		return NULL;
 
 	mdesc = of_flat_dt_match_machine(mdesc_best, arch_get_next_mach);
diff --git a/arch/arm64/kernel/setup.c b/arch/arm64/kernel/setup.c
index b22d28ec8028..87f61fd6783c 100644
--- a/arch/arm64/kernel/setup.c
+++ b/arch/arm64/kernel/setup.c
@@ -175,7 +175,11 @@ static void __init setup_machine_fdt(phys_addr_t dt_phys)
 	if (dt_virt)
 		memblock_reserve(dt_phys, size);
 
-	if (!dt_virt || !early_init_dt_scan(dt_virt)) {
+	/*
+	 * dt_virt is a fixmap address, hence __pa(dt_virt) can't be used.
+	 * Pass dt_phys directly.
+	 */
+	if (!early_init_dt_scan(dt_virt, dt_phys)) {
 		pr_crit("\n"
 			"Error: invalid device tree blob at physical address %pa (virtual address 0x%px)\n"
 			"The dtb must be 8-byte aligned and must not exceed 2 MB in size\n"
diff --git a/arch/csky/kernel/setup.c b/arch/csky/kernel/setup.c
index 51012e90780d..fe715b707fd0 100644
--- a/arch/csky/kernel/setup.c
+++ b/arch/csky/kernel/setup.c
@@ -112,9 +112,9 @@ asmlinkage __visible void __init csky_start(unsigned int unused,
 	pre_trap_init();
 
 	if (dtb_start == NULL)
-		early_init_dt_scan(__dtb_start);
+		early_init_dt_scan(__dtb_start, __pa(dtb_start));
 	else
-		early_init_dt_scan(dtb_start);
+		early_init_dt_scan(dtb_start, __pa(dtb_start));
 
 	start_kernel();
 
diff --git a/arch/loongarch/kernel/setup.c b/arch/loongarch/kernel/setup.c
index 00e307203ddb..10d878204018 100644
--- a/arch/loongarch/kernel/setup.c
+++ b/arch/loongarch/kernel/setup.c
@@ -290,7 +290,7 @@ static void __init fdt_setup(void)
 	if (!fdt_pointer || fdt_check_header(fdt_pointer))
 		return;
 
-	early_init_dt_scan(fdt_pointer);
+	early_init_dt_scan(fdt_pointer, __pa(fdt_pointer));
 	early_init_fdt_reserve_self();
 
 	max_low_pfn = PFN_PHYS(memblock_end_of_DRAM());
diff --git a/arch/microblaze/kernel/prom.c b/arch/microblaze/kernel/prom.c
index e424c796e297..76ac4cfdfb42 100644
--- a/arch/microblaze/kernel/prom.c
+++ b/arch/microblaze/kernel/prom.c
@@ -18,7 +18,7 @@ void __init early_init_devtree(void *params)
 {
 	pr_debug(" -> early_init_devtree(%p)\n", params);
 
-	early_init_dt_scan(params);
+	early_init_dt_scan(params, __pa(params));
 	if (!strlen(boot_command_line))
 		strscpy(boot_command_line, cmd_line, COMMAND_LINE_SIZE);
 
diff --git a/arch/mips/kernel/prom.c b/arch/mips/kernel/prom.c
index 6062e6fa589a..4fd6da0a06c3 100644
--- a/arch/mips/kernel/prom.c
+++ b/arch/mips/kernel/prom.c
@@ -41,7 +41,7 @@ char *mips_get_machine_name(void)
 
 void __init __dt_setup_arch(void *bph)
 {
-	if (!early_init_dt_scan(bph))
+	if (!early_init_dt_scan(bph, __pa(bph)))
 		return;
 
 	mips_set_machine_name(of_flat_dt_get_machine_name());
diff --git a/arch/mips/kernel/relocate.c b/arch/mips/kernel/relocate.c
index 7eeeaf1ff95d..cda7983e7c18 100644
--- a/arch/mips/kernel/relocate.c
+++ b/arch/mips/kernel/relocate.c
@@ -337,7 +337,7 @@ void *__init relocate_kernel(void)
 #if defined(CONFIG_USE_OF)
 	/* Deal with the device tree */
 	fdt = plat_get_fdt();
-	early_init_dt_scan(fdt);
+	early_init_dt_scan(fdt, __pa(fdt));
 	if (boot_command_line[0]) {
 		/* Boot command line was passed in device tree */
 		strscpy(arcs_cmdline, boot_command_line, COMMAND_LINE_SIZE);
diff --git a/arch/nios2/kernel/prom.c b/arch/nios2/kernel/prom.c
index 9a8393e6b4a8..db049249766f 100644
--- a/arch/nios2/kernel/prom.c
+++ b/arch/nios2/kernel/prom.c
@@ -27,7 +27,7 @@ void __init early_init_devtree(void *params)
 	if (be32_to_cpup((__be32 *)CONFIG_NIOS2_DTB_PHYS_ADDR) ==
 		 OF_DT_HEADER) {
 		params = (void *)CONFIG_NIOS2_DTB_PHYS_ADDR;
-		early_init_dt_scan(params);
+		early_init_dt_scan(params, __pa(params));
 		return;
 	}
 #endif
@@ -37,5 +37,5 @@ void __init early_init_devtree(void *params)
 		params = (void *)__dtb_start;
 #endif
 
-	early_init_dt_scan(params);
+	early_init_dt_scan(params, __pa(params));
 }
diff --git a/arch/openrisc/kernel/prom.c b/arch/openrisc/kernel/prom.c
index 19e6008bf114..e424e9bd12a7 100644
--- a/arch/openrisc/kernel/prom.c
+++ b/arch/openrisc/kernel/prom.c
@@ -22,6 +22,6 @@
 
 void __init early_init_devtree(void *params)
 {
-	early_init_dt_scan(params);
+	early_init_dt_scan(params, __pa(params));
 	memblock_allow_resize();
 }
diff --git a/arch/powerpc/kernel/dt_cpu_ftrs.c b/arch/powerpc/kernel/dt_cpu_ftrs.c
index af4263594eb2..1bee15c013e7 100644
--- a/arch/powerpc/kernel/dt_cpu_ftrs.c
+++ b/arch/powerpc/kernel/dt_cpu_ftrs.c
@@ -867,7 +867,7 @@ bool __init dt_cpu_ftrs_init(void *fdt)
 	using_dt_cpu_ftrs = false;
 
 	/* Setup and verify the FDT, if it fails we just bail */
-	if (!early_init_dt_verify(fdt))
+	if (!early_init_dt_verify(fdt, __pa(fdt)))
 		return false;
 
 	if (!of_scan_flat_dt(fdt_find_cpu_features, NULL))
diff --git a/arch/powerpc/kernel/prom.c b/arch/powerpc/kernel/prom.c
index 0be07ed407c7..88cbe432cad5 100644
--- a/arch/powerpc/kernel/prom.c
+++ b/arch/powerpc/kernel/prom.c
（改动共332行，只列前160行）
```

## 11. A143
对应物：arch/arm64/mm/hugetlbpage.c:huge_ptep_get_and_clear（按sz计算个数）

```
##### A143 83d78ac677b9 riscv: Fix hugetlb retrieval of number of ptes in case of !present pte
--- 说明 ---
riscv: Fix hugetlb retrieval of number of ptes in case of !present pte
Ryan sent a fix [1] for arm64 that applies to riscv too: in some hugetlb
functions, we must not use the pte value to get the size of a mapping
because the pte may not be present.
So use the already present size parameter for huge_pte_clear() and the
newly introduced size parameter for huge_ptep_get_and_clear(). And make
sure to gather A/D bits only on present ptes.
Fixes: 82a1a1f3bfb6 ("riscv: mm: support Svnapot in hugetlb page")
Link: https://lore.kernel.org/all/20250217140419.1702389-1-ryan.roberts@arm.com/ [1]
Link: https://lore.kernel.org/r/20250317072551.572169-1-alexghiti@rivosinc.com
Signed-off-by: Alexandre Ghiti <alexghiti@rivosinc.com>
--- 改动 ---
diff --git a/arch/riscv/mm/hugetlbpage.c b/arch/riscv/mm/hugetlbpage.c
index b4a78a4b35cf..375dd96bb4a0 100644
--- a/arch/riscv/mm/hugetlbpage.c
+++ b/arch/riscv/mm/hugetlbpage.c
@@ -148,22 +148,25 @@ unsigned long hugetlb_mask_last_page(struct hstate *h)
 static pte_t get_clear_contig(struct mm_struct *mm,
 			      unsigned long addr,
 			      pte_t *ptep,
-			      unsigned long pte_num)
+			      unsigned long ncontig)
 {
-	pte_t orig_pte = ptep_get(ptep);
-	unsigned long i;
-
-	for (i = 0; i < pte_num; i++, addr += PAGE_SIZE, ptep++) {
-		pte_t pte = ptep_get_and_clear(mm, addr, ptep);
-
-		if (pte_dirty(pte))
-			orig_pte = pte_mkdirty(orig_pte);
-
-		if (pte_young(pte))
-			orig_pte = pte_mkyoung(orig_pte);
+	pte_t pte, tmp_pte;
+	bool present;
+
+	pte = ptep_get_and_clear(mm, addr, ptep);
+	present = pte_present(pte);
+	while (--ncontig) {
+		ptep++;
+		addr += PAGE_SIZE;
+		tmp_pte = ptep_get_and_clear(mm, addr, ptep);
+		if (present) {
+			if (pte_dirty(tmp_pte))
+				pte = pte_mkdirty(pte);
+			if (pte_young(tmp_pte))
+				pte = pte_mkyoung(pte);
+		}
 	}
-
-	return orig_pte;
+	return pte;
 }
 
 static pte_t get_clear_contig_flush(struct mm_struct *mm,
@@ -212,6 +215,26 @@ static void clear_flush(struct mm_struct *mm,
 	flush_tlb_range(&vma, saddr, addr);
 }
 
+static int num_contig_ptes_from_size(unsigned long sz, size_t *pgsize)
+{
+	unsigned long hugepage_shift;
+
+	if (sz >= PGDIR_SIZE)
+		hugepage_shift = PGDIR_SHIFT;
+	else if (sz >= P4D_SIZE)
+		hugepage_shift = P4D_SHIFT;
+	else if (sz >= PUD_SIZE)
+		hugepage_shift = PUD_SHIFT;
+	else if (sz >= PMD_SIZE)
+		hugepage_shift = PMD_SHIFT;
+	else
+		hugepage_shift = PAGE_SHIFT;
+
+	*pgsize = 1 << hugepage_shift;
+
+	return sz >> hugepage_shift;
+}
+
 /*
  * When dealing with NAPOT mappings, the privileged specification indicates that
  * "if an update needs to be made, the OS generally should first mark all of the
@@ -226,22 +249,10 @@ void set_huge_pte_at(struct mm_struct *mm,
 		     pte_t pte,
 		     unsigned long sz)
 {
-	unsigned long hugepage_shift, pgsize;
+	size_t pgsize;
 	int i, pte_num;
 
-	if (sz >= PGDIR_SIZE)
-		hugepage_shift = PGDIR_SHIFT;
-	else if (sz >= P4D_SIZE)
-		hugepage_shift = P4D_SHIFT;
-	else if (sz >= PUD_SIZE)
-		hugepage_shift = PUD_SHIFT;
-	else if (sz >= PMD_SIZE)
-		hugepage_shift = PMD_SHIFT;
-	else
-		hugepage_shift = PAGE_SHIFT;
-
-	pte_num = sz >> hugepage_shift;
-	pgsize = 1 << hugepage_shift;
+	pte_num = num_contig_ptes_from_size(sz, &pgsize);
 
 	if (!pte_present(pte)) {
 		for (i = 0; i < pte_num; i++, ptep++, addr += pgsize)
@@ -295,13 +306,14 @@ pte_t huge_ptep_get_and_clear(struct mm_struct *mm,
 			      unsigned long addr,
 			      pte_t *ptep, unsigned long sz)
 {
+	size_t pgsize;
 	pte_t orig_pte = ptep_get(ptep);
 	int pte_num;
 
 	if (!pte_napot(orig_pte))
 		return ptep_get_and_clear(mm, addr, ptep);
 
-	pte_num = napot_pte_num(napot_cont_order(orig_pte));
+	pte_num = num_contig_ptes_from_size(sz, &pgsize);
 
 	return get_clear_contig(mm, addr, ptep, pte_num);
 }
@@ -351,6 +363,7 @@ void huge_pte_clear(struct mm_struct *mm,
 		    pte_t *ptep,
 		    unsigned long sz)
 {
+	size_t pgsize;
 	pte_t pte = ptep_get(ptep);
 	int i, pte_num;
 
@@ -359,8 +372,9 @@ void huge_pte_clear(struct mm_struct *mm,
 		return;
 	}
 
-	pte_num = napot_pte_num(napot_cont_order(pte));
-	for (i = 0; i < pte_num; i++, addr += PAGE_SIZE, ptep++)
+	pte_num = num_contig_ptes_from_size(sz, &pgsize);
+
+	for (i = 0; i < pte_num; i++, addr += pgsize, ptep++)
 		pte_clear(mm, addr, ptep);
 }
```

## 12. A175
对应物：arch/x86/kernel/traps.c:do_error_trap（cond_local_irq_enable）

```
##### A175 969f028bf2c4 riscv: Enable interrupt during exception handling
--- 说明 ---
riscv: Enable interrupt during exception handling
force_sig_fault() takes a spinlock, which is a sleeping lock with
CONFIG_PREEMPT_RT=y. However, exception handling calls force_sig_fault()
with interrupt disabled, causing a sleeping in atomic context warning.
This can be reproduced using userspace programs such as:
    int main() { asm ("ebreak"); }
or
    int main() { asm ("unimp"); }
There is no reason that interrupt must be disabled while handling
exceptions from userspace.
Enable interrupt while handling user exceptions. This also has the added
benefit of avoiding unnecessary delays in interrupt handling.
Fixes: f0bddf50586d ("riscv: entry: Convert to generic entry")
Suggested-by: Sebastian Andrzej Siewior <bigeasy@linutronix.de>
--- 改动 ---
diff --git a/arch/riscv/kernel/traps.c b/arch/riscv/kernel/traps.c
index 9c83848797a7..80230de167de 100644
--- a/arch/riscv/kernel/traps.c
+++ b/arch/riscv/kernel/traps.c
@@ -6,6 +6,7 @@
 #include <linux/cpu.h>
 #include <linux/kernel.h>
 #include <linux/init.h>
+#include <linux/irqflags.h>
 #include <linux/randomize_kstack.h>
 #include <linux/sched.h>
 #include <linux/sched/debug.h>
@@ -151,7 +152,9 @@ asmlinkage __visible __trap_section void name(struct pt_regs *regs)		\
 {										\
 	if (user_mode(regs)) {							\
 		irqentry_enter_from_user_mode(regs);				\
+		local_irq_enable();						\
 		do_trap_error(regs, signo, code, regs->epc, "Oops - " str);	\
+		local_irq_disable();						\
 		irqentry_exit_to_user_mode(regs);				\
 	} else {								\
 		irqentry_state_t state = irqentry_nmi_enter(regs);		\
@@ -173,17 +176,14 @@ asmlinkage __visible __trap_section void do_trap_insn_illegal(struct pt_regs *re
 
 	if (user_mode(regs)) {
 		irqentry_enter_from_user_mode(regs);
-
 		local_irq_enable();
 
 		handled = riscv_v_first_use_handler(regs);
-
-		local_irq_disable();
-
 		if (!handled)
 			do_trap_error(regs, SIGILL, ILL_ILLOPC, regs->epc,
 				      "Oops - illegal instruction");
 
+		local_irq_disable();
 		irqentry_exit_to_user_mode(regs);
 	} else {
 		irqentry_state_t state = irqentry_nmi_enter(regs);
@@ -308,9 +308,11 @@ asmlinkage __visible __trap_section void do_trap_break(struct pt_regs *regs)
 {
 	if (user_mode(regs)) {
 		irqentry_enter_from_user_mode(regs);
+		local_irq_enable();
 
 		handle_break(regs);
 
+		local_irq_disable();
 		irqentry_exit_to_user_mode(regs);
 	} else {
 		irqentry_state_t state = irqentry_nmi_enter(regs);
```

## 13. A213
对应物：arch/arm64/boot/Makefile（$(obj)/Image: vmlinux）

```
##### A213 66562b66dcbc riscv: boot: Always make Image from vmlinux, not vmlinux.unstripped
--- 说明 ---
riscv: boot: Always make Image from vmlinux, not vmlinux.unstripped
Since commit 4b47a3aefb29 ("kbuild: Restore pattern to avoid stripping
.rela.dyn from vmlinux") vmlinux has .rel*.dyn preserved. Therefore, use
vmlinux to produce Image, not vmlinux.unstripped.
Doing so fixes booting a RELOCATABLE=y Image with kexec. The problem is
caused by this chain of events:
- Since commit 3e86e4d74c04 ("kbuild: keep .modinfo section in
  vmlinux.unstripped"), vmlinux.unstripped gets a .modinfo section.
- The .modinfo section has SHF_ALLOC, so it ends up in Image, at the end
  of it.
- The Image header's image_size field does not expect to include
  .modinfo and does not account for it, since it should not be in Image.
- If .modinfo is large enough, the file size of Image ends up larger
  than image_size, which eventually leads to it failing
--- 改动 ---
diff --git a/arch/riscv/boot/Makefile b/arch/riscv/boot/Makefile
index bfc3d0b75b9b..5301adf5f3f5 100644
--- a/arch/riscv/boot/Makefile
+++ b/arch/riscv/boot/Makefile
@@ -31,11 +31,7 @@ $(obj)/xipImage: vmlinux FORCE
 
 endif
 
-ifdef CONFIG_RELOCATABLE
-$(obj)/Image: vmlinux.unstripped FORCE
-else
 $(obj)/Image: vmlinux FORCE
-endif
 	$(call if_changed,objcopy)
 
 $(obj)/Image.gz: $(obj)/Image FORCE
```

## 14. A238
对应物：arch/arm64/kernel/entry-ftrace.S:ftrace_stub（间接调用的汇编函数用SYM_TYPED_FUNC_START）

```
##### A238 f2abc305aa93 riscv: Define __riscv_copy_{,vec_}{words,bytes}_unaligned() using SYM_TYPED_FUNC_START
--- 说明 ---
riscv: Define __riscv_copy_{,vec_}{words,bytes}_unaligned() using SYM_TYPED_FUNC_START
After commit 67bdd7b01387 ("riscv: Split out measure_cycles() for
reuse") and commit c03ad15f7cf6 ("riscv: Reuse measure_cycles() in
check_vector_unaligned_access()"), there are CFI failure when booting
kernels with CONFIG_CFI=y:
  CFI failure at measure_cycles+0x38/0xe0 (target: __riscv_copy_words_unaligned+0x0/0x50; expected type: ...)
  CFI failure at measure_cycles+0x38/0xe0 (target: __riscv_copy_vec_words_unaligned+0x0/0x24; expected type: ...)
The __riscv_copy_*_unaligned() functions are now called indirectly but
they are not defined with SYM_TYPED_FUNC_START, which is required for
assembly functions called indirectly from C to pass CFI checking. Switch
to SYM_TYPED_FUNC_START to clear up the CFI failures.
Fixes: 67bdd7b01387 ("riscv: Split out measure_cycles() for reuse")
Fixes: c03ad15f7cf6 ("riscv: Reuse measure_cycles() in check_vector_unaligned_access()")
Signed-off-by: Nathan Chancellor <nathan@kernel.org>
--- 改动 ---
diff --git a/arch/riscv/kernel/copy-unaligned.S b/arch/riscv/kernel/copy-unaligned.S
index 2b3d9398c113..90f3549621f7 100644
--- a/arch/riscv/kernel/copy-unaligned.S
+++ b/arch/riscv/kernel/copy-unaligned.S
@@ -1,6 +1,7 @@
 /* SPDX-License-Identifier: GPL-2.0 */
 /* Copyright (C) 2023 Rivos Inc. */
 
+#include <linux/cfi_types.h>
 #include <linux/linkage.h>
 #include <asm/asm.h>
 
@@ -9,7 +10,7 @@
 /* void __riscv_copy_words_unaligned(void *, const void *, size_t) */
 /* Performs a memcpy without aligning buffers, using word loads and stores. */
 /* Note: The size is truncated to a multiple of 8 * SZREG */
-SYM_FUNC_START(__riscv_copy_words_unaligned)
+SYM_TYPED_FUNC_START(__riscv_copy_words_unaligned)
 	andi  a4, a2, ~((8*SZREG)-1)
 	beqz  a4, 2f
 	add   a3, a1, a4
@@ -41,7 +42,7 @@ SYM_FUNC_END(__riscv_copy_words_unaligned)
 /* void __riscv_copy_bytes_unaligned(void *, const void *, size_t) */
 /* Performs a memcpy without aligning buffers, using only byte accesses. */
 /* Note: The size is truncated to a multiple of 8 */
-SYM_FUNC_START(__riscv_copy_bytes_unaligned)
+SYM_TYPED_FUNC_START(__riscv_copy_bytes_unaligned)
 	andi a4, a2, ~(8-1)
 	beqz a4, 2f
 	add  a3, a1, a4
diff --git a/arch/riscv/kernel/vec-copy-unaligned.S b/arch/riscv/kernel/vec-copy-unaligned.S
index 7ce4de6f6e69..361039f7b944 100644
--- a/arch/riscv/kernel/vec-copy-unaligned.S
+++ b/arch/riscv/kernel/vec-copy-unaligned.S
@@ -2,6 +2,7 @@
 /* Copyright (C) 2024 Rivos Inc. */
 
 #include <linux/args.h>
+#include <linux/cfi_types.h>
 #include <linux/linkage.h>
 #include <asm/asm.h>
 
@@ -16,7 +17,7 @@
 /* void __riscv_copy_vec_words_unaligned(void *, const void *, size_t) */
 /* Performs a memcpy without aligning buffers, using word loads and stores. */
 /* Note: The size is truncated to a multiple of WORD_EEW */
-SYM_FUNC_START(__riscv_copy_vec_words_unaligned)
+SYM_TYPED_FUNC_START(__riscv_copy_vec_words_unaligned)
 	andi  a4, a2, ~(WORD_EEW-1)
 	beqz  a4, 2f
 	add   a3, a1, a4
@@ -38,7 +39,7 @@ SYM_FUNC_END(__riscv_copy_vec_words_unaligned)
 /* void __riscv_copy_vec_bytes_unaligned(void *, const void *, size_t) */
 /* Performs a memcpy without aligning buffers, using only byte accesses. */
 /* Note: The size is truncated to a multiple of 8 */
-SYM_FUNC_START(__riscv_copy_vec_bytes_unaligned)
+SYM_TYPED_FUNC_START(__riscv_copy_vec_bytes_unaligned)
 	andi a4, a2, ~(8-1)
 	beqz a4, 2f
 	add  a3, a1, a4
```

## 15. A255
对应物：arch/arm64/kernel/vdso/Makefile（CFLAGS_REMOVE含CC_FLAGS_LTO）

```
##### A255 ad6dcfa02376 riscv: vdso: Do not use LTO for the vDSO
--- 说明 ---
riscv: vdso: Do not use LTO for the vDSO
With LTO enabled the compiler assumes that the vDSO functions are not
used and optimizes them away completely. Currently this happens to
__vdso_clock_getres(), __vdso_clock_gettime(), __vdso_getrandom(),
__vdso_gettimeofday() and __vdso_riscv_hwprobe().
Disable LTO for the vDSO, as these functions are hand-optimized anyways.
Reported-by: kernel test robot <lkp@intel.com>
Closes: https://lore.kernel.org/oe-kbuild-all/202606301855.WvkSC4kD-lkp@intel.com/
Fixes: 021d23428bdb ("RISC-V: build: Allow LTO to be selected")
Cc: stable@vger.kernel.org
Signed-off-by: Thomas Weißschuh <thomas.weissschuh@linutronix.de>
Link: https://patch.msgid.link/20260701-riscv-vdso-lto-v1-1-89db0cd82077@linutronix.de
Signed-off-by: Paul Walmsley <pjw@kernel.org>
--- 改动 ---
diff --git a/arch/riscv/kernel/vdso/Makefile b/arch/riscv/kernel/vdso/Makefile
index a842dc034571..43ee881f6c6f 100644
--- a/arch/riscv/kernel/vdso/Makefile
+++ b/arch/riscv/kernel/vdso/Makefile
@@ -69,9 +69,9 @@ CPPFLAGS_$(vdso_lds) += -DHAS_VGETTIMEOFDAY
 endif
 
 # Disable -pg to prevent insert call site
-CFLAGS_REMOVE_vgettimeofday.o = $(CC_FLAGS_FTRACE) $(CC_FLAGS_SCS)
-CFLAGS_REMOVE_getrandom.o = $(CC_FLAGS_FTRACE) $(CC_FLAGS_SCS)
-CFLAGS_REMOVE_hwprobe.o = $(CC_FLAGS_FTRACE) $(CC_FLAGS_SCS)
+CFLAGS_REMOVE_vgettimeofday.o = $(CC_FLAGS_FTRACE) $(CC_FLAGS_SCS) $(CC_FLAGS_LTO)
+CFLAGS_REMOVE_getrandom.o = $(CC_FLAGS_FTRACE) $(CC_FLAGS_SCS) $(CC_FLAGS_LTO)
+CFLAGS_REMOVE_hwprobe.o = $(CC_FLAGS_FTRACE) $(CC_FLAGS_SCS) $(CC_FLAGS_LTO)
 
 # Force dependency
 $(obj)/$(vdso_o): $(obj)/$(vdso_so)
```

## 16. A277
对应物：arch/loongarch/net/bpf_jit.c:build_insn（BPF_CALL处按调用约定sign_extend）

```
##### A277 f2aaa6215910 riscv, bpf: Fix missing sign-ext for signed 1-byte and 2-byte kfunc args
--- 说明 ---
riscv, bpf: Fix missing sign-ext for signed 1-byte and 2-byte kfunc args
On RV64, the ABI requires sign-extension for signed 1-byte and 2-byte kfunc
args. However, the RV64 JIT currently does not perform sign-extension for
such kfunc args.
Before commit 7ce090afbf72 ("bpf: Infer zext_dst based on static register
liveness analysis"), state pruning could potentially omit zero-extension
of 32-bit subregisters, which inadvertently masked the above issue by making
the args appear as if they had been properly sign-extended. After that
commit, the problem is exposed, causing the kfunc_call/kfunc_call_test4
selftest to fail.
Fix this by extending the existing sign-extension logic to handle signed
1-byte and 2-byte kfunc args as well.
Fixes: 443574b03387 ("riscv, bpf: Fix kfunc parameters incompatibility between bpf and riscv abi")
Signed-off-by: Pu Lehui <pulehui@huawei.com>
--- 改动 ---
diff --git a/arch/riscv/net/bpf_jit_comp64.c b/arch/riscv/net/bpf_jit_comp64.c
index 2504df1fa111..74efe4b138d2 100644
--- a/arch/riscv/net/bpf_jit_comp64.c
+++ b/arch/riscv/net/bpf_jit_comp64.c
@@ -1823,9 +1823,10 @@ int bpf_jit_emit_insn(const struct bpf_insn *insn, struct rv_jit_context *ctx,
 
 			for (idx = 0; idx < fm->nr_args; idx++) {
 				u8 reg = bpf_to_rv_reg(BPF_REG_1 + idx, ctx);
+				bool sign = fm->arg_flags[idx] & BTF_FMODEL_SIGNED_ARG;
 
-				if (fm->arg_size[idx] == sizeof(int))
-					emit_sextw(reg, reg, ctx);
+				if (sign_extend(reg, reg, fm->arg_size[idx], sign, ctx))
+					return -EINVAL;
 			}
 		}
```

## 17. A288
对应物：arch/x86/kernel/module.c:module_alloc（VM_FLUSH_RESET_PERMS）

```
##### A288 749b94b08005 riscv: Fix module_alloc() that did not reset the linear mapping permissions
--- 说明 ---
riscv: Fix module_alloc() that did not reset the linear mapping permissions
After unloading a module, we must reset the linear mapping permissions,
see the example below:
Before unloading a module:
0xffffaf809d65d000-0xffffaf809d6dc000    0x000000011d65d000       508K PTE .   ..     ..   D A G . . W R V
0xffffaf809d6dc000-0xffffaf809d6dd000    0x000000011d6dc000         4K PTE .   ..     ..   D A G . . . R V
0xffffaf809d6dd000-0xffffaf809d6e1000    0x000000011d6dd000        16K PTE .   ..     ..   D A G . . W R V
0xffffaf809d6e1000-0xffffaf809d6e7000    0x000000011d6e1000        24K PTE .   ..     ..   D A G . X . R V
After unloading a module:
0xffffaf809d65d000-0xffffaf809d6e1000    0x000000011d65d000       528K PTE .   ..     ..   D A G . . W R V
0xffffaf809d6e1000-0xffffaf809d6e7000    0x000000011d6e1000        24K PTE .   ..     ..   D A G . X W R V
The last mapping is not reset and we end up with WX mappings in the linear
mapping.
So add VM_FLUSH_RESET_PERMS to our module_alloc() definition.
--- 改动 ---
diff --git a/arch/riscv/kernel/module.c b/arch/riscv/kernel/module.c
index aac019ed63b1..862834bb1d64 100644
--- a/arch/riscv/kernel/module.c
+++ b/arch/riscv/kernel/module.c
@@ -894,7 +894,8 @@ void *module_alloc(unsigned long size)
 {
 	return __vmalloc_node_range(size, 1, MODULES_VADDR,
 				    MODULES_END, GFP_KERNEL,
-				    PAGE_KERNEL, 0, NUMA_NO_NODE,
+				    PAGE_KERNEL, VM_FLUSH_RESET_PERMS,
+				    NUMA_NO_NODE,
 				    __builtin_return_address(0));
 }
 #endif
```

## 18. A313
对应物：arch/x86/mm/fault.c:mm_fault_error（处理VM_FAULT_SIGSEGV）

```
##### A313 0c710050c47d riscv/mm: Add handling for VM_FAULT_SIGSEGV in mm_fault_error()
--- 说明 ---
riscv/mm: Add handling for VM_FAULT_SIGSEGV in mm_fault_error()
Handle VM_FAULT_SIGSEGV in the page fault path so that we correctly
kill the process and we don't BUG() the kernel.
Fixes: 07037db5d479 ("RISC-V: Paging and MMU")
Signed-off-by: Zhe Qiao <qiaozhe@iscas.ac.cn>
Reviewed-by: Alexandre Ghiti <alexghiti@rivosinc.com>
Link: https://lore.kernel.org/r/20240731084547.85380-1-qiaozhe@iscas.ac.cn
Signed-off-by: Palmer Dabbelt <palmer@rivosinc.com>
--- 改动 ---
diff --git a/arch/riscv/mm/fault.c b/arch/riscv/mm/fault.c
index 5224f3733802..a9f2b4af8f3f 100644
--- a/arch/riscv/mm/fault.c
+++ b/arch/riscv/mm/fault.c
@@ -61,26 +61,27 @@ static inline void no_context(struct pt_regs *regs, unsigned long addr)
 
 static inline void mm_fault_error(struct pt_regs *regs, unsigned long addr, vm_fault_t fault)
 {
+	if (!user_mode(regs)) {
+		no_context(regs, addr);
+		return;
+	}
+
 	if (fault & VM_FAULT_OOM) {
 		/*
 		 * We ran out of memory, call the OOM killer, and return the userspace
 		 * (which will retry the fault, or kill us if we got oom-killed).
 		 */
-		if (!user_mode(regs)) {
-			no_context(regs, addr);
-			return;
-		}
 		pagefault_out_of_memory();
 		return;
 	} else if (fault & (VM_FAULT_SIGBUS | VM_FAULT_HWPOISON | VM_FAULT_HWPOISON_LARGE)) {
 		/* Kernel mode? Handle exceptions or die */
-		if (!user_mode(regs)) {
-			no_context(regs, addr);
-			return;
-		}
 		do_trap(regs, SIGBUS, BUS_ADRERR, addr);
 		return;
+	} else if (fault & VM_FAULT_SIGSEGV) {
+		do_trap(regs, SIGSEGV, SEGV_MAPERR, addr);
+		return;
 	}
+
 	BUG();
 }
```

## 19. A344
对应物：arch/arm64/kernel/entry-common.c（el0异常处理先开中断）

```
##### A344 453805f0a28f riscv: misaligned: enable IRQs while handling misaligned accesses
--- 说明 ---
riscv: misaligned: enable IRQs while handling misaligned accesses
We can safely reenable IRQs if coming from userspace. This allows to
access user memory that could potentially trigger a page fault.
Fixes: b686ecdeacf6 ("riscv: misaligned: Restrict user access to kernel memory")
Signed-off-by: Clément Léger <cleger@rivosinc.com>
Reviewed-by: Alexandre Ghiti <alexghiti@rivosinc.com>
Link: https://lore.kernel.org/r/20250422162324.956065-3-cleger@rivosinc.com
Signed-off-by: Alexandre Ghiti <alexghiti@rivosinc.com>
--- 改动 ---
diff --git a/arch/riscv/kernel/traps.c b/arch/riscv/kernel/traps.c
index b1d991c78a23..9c83848797a7 100644
--- a/arch/riscv/kernel/traps.c
+++ b/arch/riscv/kernel/traps.c
@@ -220,19 +220,23 @@ static void do_trap_misaligned(struct pt_regs *regs, enum misaligned_access_type
 {
 	irqentry_state_t state;
 
-	if (user_mode(regs))
+	if (user_mode(regs)) {
 		irqentry_enter_from_user_mode(regs);
-	else
+		local_irq_enable();
+	} else {
 		state = irqentry_nmi_enter(regs);
+	}
 
 	if (misaligned_handler[type].handler(regs))
 		do_trap_error(regs, SIGBUS, BUS_ADRALN, regs->epc,
 			      misaligned_handler[type].type_str);
 
-	if (user_mode(regs))
+	if (user_mode(regs)) {
+		local_irq_disable();
 		irqentry_exit_to_user_mode(regs);
-	else
+	} else {
 		irqentry_nmi_exit(regs, state);
+	}
 }
 
 asmlinkage __visible __trap_section void do_trap_load_misaligned(struct pt_regs *regs)
```

## 20. A387
对应物：arch/arm64/kvm/guest.c:kvm_arch_vcpu_ioctl_set_guest_debug

```
##### A387 5eb6d68fe24d RISC-V: KVM: Fix ebreak self test failure
--- 说明 ---
RISC-V: KVM: Fix ebreak self test failure
The ebreak self test enables/disables guest debugging as a part of the
test. However the KVM_SET_GUEST_DEBUG ioctl doesn't actually do it.
Fixing it by calling kvm_riscv_vcpu_config_guest_debug.
Fixes: 6ed523e2b612 ("RISC-V: KVM: Factor-out VCPU config into separate sources")
Signed-off-by: Mayuresh Chitale <mayuresh.chitale@oss.qualcomm.com>
Reviewed-by: Anup Patel <anup@brainfault.org>
Link: https://lore.kernel.org/r/20260525095930.3924905-1-mayuresh.chitale@oss.qualcomm.com
Signed-off-by: Anup Patel <anup@brainfault.org>
--- 改动 ---
diff --git a/arch/riscv/kvm/vcpu.c b/arch/riscv/kvm/vcpu.c
index a73690eda84b..cf6e231e76e2 100644
--- a/arch/riscv/kvm/vcpu.c
+++ b/arch/riscv/kvm/vcpu.c
@@ -538,6 +538,7 @@ int kvm_arch_vcpu_ioctl_set_guest_debug(struct kvm_vcpu *vcpu,
 	else
 		vcpu->guest_debug = 0;
 
+	kvm_riscv_vcpu_config_guest_debug(vcpu);
 	return 0;
 }
```

## 21. A393
对应物：security/integrity/ima/ima_kexec.c（可能产生空缓冲区）

```
##### A393 81bbcff0c053 riscv: Prevent NULL pointer dereference in machine_kexec_prepare()
--- 说明 ---
riscv: Prevent NULL pointer dereference in machine_kexec_prepare()
A NULL pointer dereference issue is noticed in riscv's
machine_kexec_prepare(), where image->segment[i].buf might be NULL and
copied unchecked.
The NULL buf comes from ima_add_kexec_buffer(), where kbuf is added by
kexec_add_buffer(), but kbuf.buffer is NULL, then it is copied without
a check in machine_kexec_prepare():
  kexec_file_load
    -> kimage_file_alloc_init()
       -> kimage_file_prepare_segments()
          -> ima_add_kexec_buffer()
             -> kexec_add_buffer()
    -> machine_kexec_prepare()
       -> memcpy()
--- 改动 ---
diff --git a/arch/riscv/kernel/machine_kexec.c b/arch/riscv/kernel/machine_kexec.c
index 2306ce3e5f22..738df176ff6f 100644
--- a/arch/riscv/kernel/machine_kexec.c
+++ b/arch/riscv/kernel/machine_kexec.c
@@ -41,6 +41,9 @@ machine_kexec_prepare(struct kimage *image)
 		if (image->segment[i].memsz <= sizeof(fdt))
 			continue;
 
+		if (!image->segment[i].buf)
+			continue;
+
 		if (image->file_mode)
 			memcpy(&fdt, image->segment[i].buf, sizeof(fdt));
 		else if (copy_from_user(&fdt, image->segment[i].buf, sizeof(fdt)))
```

## 22. B432
对应物：init/Kconfig:RUST（与CFI_CLANG互斥）

```
##### B432 8933cf4651e0 rust: make mutually exclusive with CFI_CLANG
--- 说明 ---
rust: make mutually exclusive with CFI_CLANG
On RISC-V and arm64, and presumably x86, if CFI_CLANG is enabled,
loading a rust module will trigger a kernel panic. Support for
sanitisers, including kcfi (CFI_CLANG), is in the works, but for now
they're nightly-only options in rustc. Make RUST depend on !CFI_CLANG
to prevent configuring a kernel without symmetrical support for kfi.
[ Matthew Maurer writes [1]:
    This patch is fine by me - the last patch needed for KCFI to be
    functional in Rust just landed upstream last night, so we should
    revisit this (in the form of enabling it) once we move to
    `rustc-1.79.0` or later.
  Ramon de C Valle also gave feedback [2] on the status of KCFI for
  Rust and created a tracking issue [3] in upstream Rust.   - Miguel ]
Fixes: 2f7ab1267dc9 ("Kbuild: add Rust support")
--- 改动 ---
diff --git a/init/Kconfig b/init/Kconfig
index b9a336a3d7d8..664bedb9a71f 100644
--- a/init/Kconfig
+++ b/init/Kconfig
@@ -1899,6 +1899,7 @@ config RUST
 	bool "Rust support"
 	depends on HAVE_RUST
 	depends on RUST_IS_AVAILABLE
+	depends on !CFI_CLANG
 	depends on !MODVERSIONS
 	depends on !GCC_PLUGINS
 	depends on !RANDSTRUCT
```

## 23. B444
对应物：include/linux/randomize_kstack.h（各架构熵位过滤）

```
##### B444 6db1208bf95b randomize_kstack: Remove non-functional per-arch entropy filtering
--- 说明 ---
randomize_kstack: Remove non-functional per-arch entropy filtering
An unintended consequence of commit 9c573cd31343 ("randomize_kstack:
Improve entropy diffusion") was that the per-architecture entropy size
filtering reduced how many bits were being added to the mix, rather than
how many bits were being used during the offsetting. All architectures
fell back to the existing default of 0x3FF (10 bits), which will consume
at most 1KiB of stack space. It seems that this is working just fine,
so let's avoid the confusion and update everything to use the default.
The prior intent of the per-architecture limits were:
  arm64: capped at 0x1FF (9 bits), 5 bits effective
  powerpc: uncapped (10 bits), 6 or 7 bits effective
  riscv: uncapped (10 bits), 6 bits effective
  x86: capped at 0xFF (8 bits), 5 (x86_64) or 6 (ia32) bits effective
  s390: capped at 0xFF (8 bits), undocumented effective entropy
--- 改动 ---
diff --git a/arch/arm64/kernel/syscall.c b/arch/arm64/kernel/syscall.c
index ad198262b981..7230f6e20ab8 100644
--- a/arch/arm64/kernel/syscall.c
+++ b/arch/arm64/kernel/syscall.c
@@ -53,17 +53,15 @@ static void invoke_syscall(struct pt_regs *regs, unsigned int scno,
 	syscall_set_return_value(current, regs, 0, ret);
 
 	/*
-	 * Ultimately, this value will get limited by KSTACK_OFFSET_MAX(),
-	 * but not enough for arm64 stack utilization comfort. To keep
-	 * reasonable stack head room, reduce the maximum offset to 9 bits.
+	 * This value will get limited by KSTACK_OFFSET_MAX(), which is 10
+	 * bits. The actual entropy will be further reduced by the compiler
+	 * when applying stack alignment constraints: the AAPCS mandates a
+	 * 16-byte aligned SP at function boundaries, which will remove the
+	 * 4 low bits from any entropy chosen here.
 	 *
-	 * The actual entropy will be further reduced by the compiler when
-	 * applying stack alignment constraints: the AAPCS mandates a
-	 * 16-byte (i.e. 4-bit) aligned SP at function boundaries.
-	 *
-	 * The resulting 5 bits of entropy is seen in SP[8:4].
+	 * The resulting 6 bits of entropy is seen in SP[9:4].
 	 */
-	choose_random_kstack_offset(get_random_u16() & 0x1FF);
+	choose_random_kstack_offset(get_random_u16());
 }
 
 static inline bool has_syscall_work(unsigned long flags)
diff --git a/arch/s390/include/asm/entry-common.h b/arch/s390/include/asm/entry-common.h
index 7f5004065e8a..35555c944630 100644
--- a/arch/s390/include/asm/entry-common.h
+++ b/arch/s390/include/asm/entry-common.h
@@ -54,7 +54,7 @@ static __always_inline void arch_exit_to_user_mode(void)
 static inline void arch_exit_to_user_mode_prepare(struct pt_regs *regs,
 						  unsigned long ti_work)
 {
-	choose_random_kstack_offset(get_tod_clock_fast() & 0xff);
+	choose_random_kstack_offset(get_tod_clock_fast());
 }
 
 #define arch_exit_to_user_mode_prepare arch_exit_to_user_mode_prepare
diff --git a/arch/x86/include/asm/entry-common.h b/arch/x86/include/asm/entry-common.h
index 7e523bb3d2d3..fb2809b20b0a 100644
--- a/arch/x86/include/asm/entry-common.h
+++ b/arch/x86/include/asm/entry-common.h
@@ -73,19 +73,16 @@ static inline void arch_exit_to_user_mode_prepare(struct pt_regs *regs,
 #endif
 
 	/*
-	 * Ultimately, this value will get limited by KSTACK_OFFSET_MAX(),
-	 * but not enough for x86 stack utilization comfort. To keep
-	 * reasonable stack head room, reduce the maximum offset to 8 bits.
-	 *
-	 * The actual entropy will be further reduced by the compiler when
-	 * applying stack alignment constraints (see cc_stack_align4/8 in
+	 * This value will get limited by KSTACK_OFFSET_MAX(), which is 10
+	 * bits. The actual entropy will be further reduced by the compiler
+	 * when applying stack alignment constraints (see cc_stack_align4/8 in
 	 * arch/x86/Makefile), which will remove the 3 (x86_64) or 2 (ia32)
 	 * low bits from any entropy chosen here.
 	 *
-	 * Therefore, final stack offset entropy will be 5 (x86_64) or
-	 * 6 (ia32) bits.
+	 * Therefore, final stack offset entropy will be 7 (x86_64) or
+	 * 8 (ia32) bits.
 	 */
-	choose_random_kstack_offset(rdtsc() & 0xFF);
+	choose_random_kstack_offset(rdtsc());
 }
 #define arch_exit_to_user_mode_prepare arch_exit_to_user_mode_prepare
```

## 24. B455
对应物：fs/binfmt_flat.c（不偏移数据段时仍初始化共享库指针数组）

```
##### B455 3eb3cd5992f7 binfmt_flat: Fix corruption when not offsetting data start
--- 说明 ---
binfmt_flat: Fix corruption when not offsetting data start
Commit 04d82a6d0881 ("binfmt_flat: allow not offsetting data start")
introduced a RISC-V specific variant of the FLAT format which does
not allocate any space for the (obsolete) array of shared library
pointers. However, it did not disable the code which initializes the
array, resulting in the corruption of sizeof(long) bytes before the DATA
segment, generally the end of the TEXT segment.
Introduce MAX_SHARED_LIBS_UPDATE which depends on the state of
CONFIG_BINFMT_FLAT_NO_DATA_START_OFFSET to guard the initialization of
the shared library pointer region so that it will only be initialized
if space is reserved for it.
Fixes: 04d82a6d0881 ("binfmt_flat: allow not offsetting data start")
Co-developed-by: Stefan O'Rear <sorear@fastmail.com>
Signed-off-by: Stefan O'Rear <sorear@fastmail.com>
--- 改动 ---
diff --git a/fs/binfmt_flat.c b/fs/binfmt_flat.c
index c26545d71d39..cd6d5bbb4b9d 100644
--- a/fs/binfmt_flat.c
+++ b/fs/binfmt_flat.c
@@ -72,8 +72,10 @@
 
 #ifdef CONFIG_BINFMT_FLAT_NO_DATA_START_OFFSET
 #define DATA_START_OFFSET_WORDS		(0)
+#define MAX_SHARED_LIBS_UPDATE		(0)
 #else
 #define DATA_START_OFFSET_WORDS		(MAX_SHARED_LIBS)
+#define MAX_SHARED_LIBS_UPDATE		(MAX_SHARED_LIBS)
 #endif
 
 struct lib_info {
@@ -880,7 +882,7 @@ static int load_flat_binary(struct linux_binprm *bprm)
 		return res;
 
 	/* Update data segment pointers for all libraries */
-	for (i = 0; i < MAX_SHARED_LIBS; i++) {
+	for (i = 0; i < MAX_SHARED_LIBS_UPDATE; i++) {
 		if (!libinfo.lib_list[i].loaded)
 			continue;
 		for (j = 0; j < MAX_SHARED_LIBS; j++) {
```

## 25. B492
对应物：arch/arm64/include/asm/memory.h:untagged_addr

```
##### B492 69146a8c893f ubi: ubi_get_ec_info: Fix compiling error 'cast specifies array type'
--- 说明 ---
ubi: ubi_get_ec_info: Fix compiling error 'cast specifies array type'
On risc V platform, there is a type conversion for the return value
(unsigned long type) of __untagged_addr_remote() in function
untagged_addr(). The compiler will complain when the parameter 'addr'
is an array type:
  arch/riscv/include/asm/uaccess.h:33:9: error: cast specifies array type
  (__force  __typeof__(addr))__untagged_addr_remote(current->mm, __addr)
Fix it by converting the input parameter as a pointer.
Fixes: 01099f635a4c ("ubi: Implement ioctl for detailed erase counters")
Reported-by: kernel test robot <lkp@intel.com>
Closes: https://lore.kernel.org/oe-kbuild-all/202501191405.WYnmdL0U-lkp@intel.com/
Signed-off-by: Zhihao Cheng <chengzhihao1@huawei.com>
Signed-off-by: Richard Weinberger <richard@nod.at>
--- 改动 ---
diff --git a/drivers/mtd/ubi/cdev.c b/drivers/mtd/ubi/cdev.c
index 4c3e4edb6853..b700a0efaa93 100644
--- a/drivers/mtd/ubi/cdev.c
+++ b/drivers/mtd/ubi/cdev.c
@@ -851,7 +851,8 @@ static int ubi_get_ec_info(struct ubi_device *ubi, struct ubi_ecinfo_req __user
 		end_peb = ubi->peb_count;
 
 	/* Check access rights before filling erase_counters array */
-	if (!access_ok(ureq->erase_counters, (end_peb-req.start) * sizeof(int32_t)))
+	if (!access_ok((void __user *)ureq->erase_counters,
+		       (end_peb-req.start) * sizeof(int32_t)))
 		return -EFAULT;
 
 	/* Fill erase counter array */
```

## 26. B519
对应物：kernel/trace/rv/monitors（假设存在32位time_t系统调用）

```
##### B519 03ee64b5e525 rv: Support systems with time64-only syscalls
--- 说明 ---
rv: Support systems with time64-only syscalls
Some systems (like 32-bit RISC-V) only have the 64-bit time_t versions
of syscalls.  So handle the 32-bit time_t version of those being
undefined.
Fixes: f74f8bb246cf ("rv: Add rtapp_sleep monitor")
Closes: https://lore.kernel.org/oe-kbuild-all/202508160204.SsFyNfo6-lkp@intel.com
Signed-off-by: Palmer Dabbelt <palmer@dabbelt.com>
Acked-by: Nam Cao <namcao@linutronix.de>
Link: https://lore.kernel.org/r/20250804194518.97620-2-palmer@dabbelt.com
Signed-off-by: Gabriele Monaco <gmonaco@redhat.com>
--- 改动 ---
diff --git a/kernel/trace/rv/monitors/sleep/sleep.c b/kernel/trace/rv/monitors/sleep/sleep.c
index eea447b06907..c1347da69e9d 100644
--- a/kernel/trace/rv/monitors/sleep/sleep.c
+++ b/kernel/trace/rv/monitors/sleep/sleep.c
@@ -127,7 +127,9 @@ static void handle_sys_enter(void *data, struct pt_regs *regs, long id)
 	mon = ltl_get_monitor(current);
 
 	switch (id) {
+#ifdef __NR_clock_nanosleep
 	case __NR_clock_nanosleep:
+#endif
 #ifdef __NR_clock_nanosleep_time64
 	case __NR_clock_nanosleep_time64:
 #endif
@@ -138,7 +140,9 @@ static void handle_sys_enter(void *data, struct pt_regs *regs, long id)
 		ltl_atom_update(current, LTL_CLOCK_NANOSLEEP, true);
 		break;
 
+#ifdef __NR_futex
 	case __NR_futex:
+#endif
 #ifdef __NR_futex_time64
 	case __NR_futex_time64:
 #endif
```

## 27. B524
对应物：kernel/fork.c:copy_sighand（unsigned long标志）

```
##### B524 04ff48239f46 copy_sighand: Handle architectures where sizeof(unsigned long) < sizeof(u64)
--- 说明 ---
copy_sighand: Handle architectures where sizeof(unsigned long) < sizeof(u64)
With the introduction of clone3 in commit 7f192e3cd316 ("fork: add
clone3") the effective bit width of clone_flags on all architectures was
increased from 32-bit to 64-bit. However, the signature of the copy_*
helper functions (e.g., copy_sighand) used by copy_process was not
adapted.
As such, they truncate the flags on any 32-bit architectures that
supports clone3 (arc, arm, csky, m68k, microblaze, mips32, openrisc,
parisc32, powerpc32, riscv32, x86-32 and xtensa).
For copy_sighand with CLONE_CLEAR_SIGHAND being an actual u64
constant, this triggers an observable bug in kernel selftest
clone3_clear_sighand:
        if (clone_flags & CLONE_CLEAR_SIGHAND)
in function copy_sighand within fork.c will always fail given:
--- 改动 ---
diff --git a/kernel/fork.c b/kernel/fork.c
index af673856499d..4e2c5a3e8989 100644
--- a/kernel/fork.c
+++ b/kernel/fork.c
@@ -1596,7 +1596,7 @@ static int copy_files(unsigned long clone_flags, struct task_struct *tsk,
 	return 0;
 }
 
-static int copy_sighand(unsigned long clone_flags, struct task_struct *tsk)
+static int copy_sighand(u64 clone_flags, struct task_struct *tsk)
 {
 	struct sighand_struct *sig;
```

## 28. B527
对应物：init/Kconfig:CC_HAS_ASM_GOTO_OUTPUT（测试用x86助记符jmp）

```
##### B527 fde0ab43b9a3 Fix CC_HAS_ASM_GOTO_OUTPUT on non-x86 architectures
--- 说明 ---
Fix CC_HAS_ASM_GOTO_OUTPUT on non-x86 architectures
There's a silly problem with the CC_HAS_ASM_GOTO_OUTPUT test: even with
a working compiler it will fail on some architectures simply because it
uses the mnemonic "jmp" for testing the inline asm.
And as reported by Geert, not all architectures use that mnemonic, so
the test fails spuriously on such platforms (including arm and riscv,
but also several other architectures).
This issue avoided any obvious test failures because the build still
works thanks to falling back on the old non-asm-goto code, which just
generates worse code.
Just use an empty asm statement instead.
Reported-and-tested-by: Geert Uytterhoeven <geert@linux-m68k.org>
Suggested-by: Peter Zijlstra <peterz@infradead.org>
Fixes: e2ffa15b9baa ("kbuild: Disable CC_HAS_ASM_GOTO_OUTPUT on clang < 17")
--- 改动 ---
diff --git a/init/Kconfig b/init/Kconfig
index ecddb94db8dc..6a91ec742186 100644
--- a/init/Kconfig
+++ b/init/Kconfig
@@ -102,7 +102,7 @@ config CC_HAS_ASM_GOTO_OUTPUT
 	# Detect basic support
 	depends on $(success,echo 'int foo(int x) { asm goto ("": "=r"(x) ::: bar); return x; bar: return 0; }' | $(CC) -x c - -c -o /dev/null)
 	# Detect clang (< v17) scoped label issues
-	depends on $(success,echo 'void b(void **);void* c(void);int f(void){{asm goto("jmp %l0"::::l0);return 0;l0:return 1;}void *x __attribute__((cleanup(b)))=c();{asm goto("jmp %l0"::::l1);return 2;l1:return 3;}}' | $(CC) -x c - -c -o /dev/null)
+	depends on $(success,echo 'void b(void **);void* c(void);int f(void){{asm goto(""::::l0);return 0;l0:return 1;}void *x __attribute__((cleanup(b)))=c();{asm goto(""::::l1);return 2;l1:return 3;}}' | $(CC) -x c - -c -o /dev/null)
 
 config CC_HAS_ASM_GOTO_TIED_OUTPUT
 	depends on CC_HAS_ASM_GOTO_OUTPUT
```

## 29. B577
对应物：kernel/trace/ring_buffer.c:rb_calculate_event_length（RB_FORCE_8BYTE_ALIGNMENT）

```
##### B577 c37e0a4b79a6 ring-buffer: Fix event length with forced 8-byte alignment
--- 说明 ---
ring-buffer: Fix event length with forced 8-byte alignment
When RB_FORCE_8BYTE_ALIGNMENT is true, rb_calculate_event_length()
reserves the space of event->array[0] for placing the data length and
rb_update_event() stores the data length in event->array[0]
accordingly. As a result the whole event length will add extra 4 bytes
for sizeof(event.array[0]) unconditionally.
But ring_buffer_event_length() only subtracts the
sizeof(event->array[0]) for events larger than RB_MAX_SMALL_DATA +
sizeof(event->array[0]). As a result, small events on architectures
with RB_FORCE_8BYTE_ALIGNMENT=true report a data length that is 4
bytes larger than expected.
To fix it, add the RB_FORCE_8BYTE_ALIGNMENT as a condition to subtract
the size of that length field whenever RB_FORCE_8BYTE_ALIGNMENT is
true.
--- 改动 ---
diff --git a/kernel/trace/ring_buffer.c b/kernel/trace/ring_buffer.c
index 56a328e94395..d9af2bbaf9c0 100644
--- a/kernel/trace/ring_buffer.c
+++ b/kernel/trace/ring_buffer.c
@@ -270,7 +270,8 @@ unsigned ring_buffer_event_length(struct ring_buffer_event *event)
 	if (event->type_len > RINGBUF_TYPE_DATA_TYPE_LEN_MAX)
 		return length;
 	length -= RB_EVNT_HDR_SIZE;
-	if (length > RB_MAX_SMALL_DATA + sizeof(event->array[0]))
+	if (length > RB_MAX_SMALL_DATA + sizeof(event->array[0]) ||
+	    RB_FORCE_8BYTE_ALIGNMENT)
                 length -= sizeof(event->array[0]);
 	return length;
 }
```

## 30. B584
对应物：drivers/net/ethernet/mellanox/mlx5（发布指针无屏障）

```
##### B584 5a799714e8ca net/mlx5e: Fix publication race for priv->channel_stats[]
--- 说明 ---
net/mlx5e: Fix publication race for priv->channel_stats[]
mlx5e_channel_stats_alloc() publishes a new entry to
priv->channel_stats[] and then increments priv->stats_nch as a
publication token, but neither store carries any memory barrier:
	priv->channel_stats[ix] = kvzalloc_node(...);
	if (!priv->channel_stats[ix])
		return -ENOMEM;
	priv->stats_nch++;
Concurrent readers compute the loop bound from priv->stats_nch and
then dereference priv->channel_stats[i] using plain accesses, e.g.
	for (i = 0; i < priv->stats_nch; i++) {
		struct mlx5e_channel_stats *cs = priv->channel_stats[i];
		... cs->rq.packets ...
	}
--- 改动 ---
diff --git a/drivers/net/ethernet/mellanox/mlx5/core/en.h b/drivers/net/ethernet/mellanox/mlx5/core/en.h
index 2270e2e550dd..d507289096c2 100644
--- a/drivers/net/ethernet/mellanox/mlx5/core/en.h
+++ b/drivers/net/ethernet/mellanox/mlx5/core/en.h
@@ -987,6 +987,18 @@ struct mlx5e_priv {
 	struct ethtool_fec_hist_range *fec_ranges;
 };
 
+static inline u16 mlx5e_stats_nch_read(const struct mlx5e_priv *priv)
+{
+	/* Pairs with smp_store_release in mlx5e_stats_nch_write(). */
+	return smp_load_acquire(&priv->stats_nch);
+}
+
+static inline void mlx5e_stats_nch_write(struct mlx5e_priv *priv, u16 n)
+{
+	/* Pairs with smp_load_acquire in mlx5e_stats_nch_read(). */
+	smp_store_release(&priv->stats_nch, n);
+}
+
 struct mlx5e_dev {
 	struct net_device *netdev;
 	struct devlink_port dl_port;
diff --git a/drivers/net/ethernet/mellanox/mlx5/core/en/hv_vhca_stats.c b/drivers/net/ethernet/mellanox/mlx5/core/en/hv_vhca_stats.c
index cdaf77650164..631f802105d5 100644
--- a/drivers/net/ethernet/mellanox/mlx5/core/en/hv_vhca_stats.c
+++ b/drivers/net/ethernet/mellanox/mlx5/core/en/hv_vhca_stats.c
@@ -33,9 +33,10 @@ mlx5e_hv_vhca_fill_ring_stats(struct mlx5e_priv *priv, int ch,
 static void mlx5e_hv_vhca_fill_stats(struct mlx5e_priv *priv, void *data,
 				     int buf_len)
 {
+	u16 nch = mlx5e_stats_nch_read(priv);
 	int ch, i = 0;
 
-	for (ch = 0; ch < priv->stats_nch; ch++) {
+	for (ch = 0; ch < nch; ch++) {
 		void *buf = data + i;
 
 		if (WARN_ON_ONCE(buf +
@@ -50,8 +51,9 @@ static void mlx5e_hv_vhca_fill_stats(struct mlx5e_priv *priv, void *data,
 
 static int mlx5e_hv_vhca_stats_buf_size(struct mlx5e_priv *priv)
 {
-	return (sizeof(struct mlx5e_hv_vhca_per_ring_stats) *
-		priv->stats_nch);
+	u16 nch = mlx5e_stats_nch_read(priv);
+
+	return sizeof(struct mlx5e_hv_vhca_per_ring_stats) * nch;
 }
 
 static int mlx5e_hv_vhca_stats_buf_max_size(struct mlx5e_priv *priv)
@@ -106,7 +108,7 @@ static void mlx5e_hv_vhca_stats_control(struct mlx5_hv_vhca_agent *agent,
 	sagent = &priv->stats_agent;
 
 	block->version = MLX5_HV_VHCA_STATS_VERSION;
-	block->rings   = priv->stats_nch;
+	block->rings   = mlx5e_stats_nch_read(priv);
 
 	if (!block->command) {
 		cancel_delayed_work_sync(&priv->stats_agent.work);
diff --git a/drivers/net/ethernet/mellanox/mlx5/core/en_main.c b/drivers/net/ethernet/mellanox/mlx5/core/en_main.c
index 775f0c6e55c9..aa8610cedaa8 100644
--- a/drivers/net/ethernet/mellanox/mlx5/core/en_main.c
+++ b/drivers/net/ethernet/mellanox/mlx5/core/en_main.c
@@ -2773,7 +2773,7 @@ static int mlx5e_channel_stats_alloc(struct mlx5e_priv *priv, int ix, int cpu)
 						GFP_KERNEL, cpu_to_node(cpu));
 	if (!priv->channel_stats[ix])
 		return -ENOMEM;
-	priv->stats_nch++;
+	mlx5e_stats_nch_write(priv, priv->stats_nch + 1);
 
 	return 0;
 }
@@ -4040,9 +4040,10 @@ static int mlx5e_setup_tc(struct net_device *dev, enum tc_setup_type type,
 
 void mlx5e_fold_sw_stats64(struct mlx5e_priv *priv, struct rtnl_link_stats64 *s)
 {
+	u16 nch = mlx5e_stats_nch_read(priv);
 	int i;
 
-	for (i = 0; i < priv->stats_nch; i++) {
+	for (i = 0; i < nch; i++) {
 		struct mlx5e_channel_stats *channel_stats = priv->channel_stats[i];
 		struct mlx5e_rq_stats *xskrq_stats = &channel_stats->xskrq;
 		struct mlx5e_rq_stats *rq_stats = &channel_stats->rq;
@@ -5488,7 +5489,7 @@ static void mlx5e_get_queue_stats_rx(struct net_device *dev, int i,
 	struct mlx5e_rq_stats *xskrq_stats;
 	struct mlx5e_rq_stats *rq_stats;
 
-	if (mlx5e_is_uplink_rep(priv) || !priv->stats_nch)
+	if (mlx5e_is_uplink_rep(priv) || !mlx5e_stats_nch_read(priv))
 		return;
 
 	channel_stats = priv->channel_stats[i];
@@ -5512,7 +5513,7 @@ static void mlx5e_get_queue_stats_tx(struct net_device *dev, int i,
 	struct mlx5e_priv *priv = netdev_priv(dev);
 	struct mlx5e_sq_stats *sq_stats;
 
-	if (!priv->stats_nch)
+	if (!mlx5e_stats_nch_read(priv))
 		return;
 
 	/* no special case needed for ptp htb etc since txq2sq_stats is kept up
@@ -5538,6 +5539,7 @@ static void mlx5e_get_base_stats(struct net_device *dev,
 				 struct netdev_queue_stats_tx *tx)
 {
 	struct mlx5e_priv *priv = netdev_priv(dev);
+	u16 nch = mlx5e_stats_nch_read(priv);
 	struct mlx5e_ptp *ptp_channel;
 	int i, tc;
 
@@ -5549,7 +5551,7 @@ static void mlx5e_get_base_stats(struct net_device *dev,
 		rx->hw_gro_wire_packets = 0;
 		rx->hw_gro_wire_bytes = 0;
 
-		for (i = priv->channels.params.num_channels; i < priv->stats_nch; i++) {
+		for (i = priv->channels.params.num_channels; i < nch; i++) {
 			struct netdev_queue_stats_rx rx_i = {0};
 
 			mlx5e_get_queue_stats_rx(dev, i, &rx_i);
@@ -5585,7 +5587,7 @@ static void mlx5e_get_base_stats(struct net_device *dev,
 	tx->stop = 0;
 	tx->wake = 0;
 
-	for (i = 0; i < priv->stats_nch; i++) {
+	for (i = 0; i < nch; i++) {
 		struct mlx5e_channel_stats *channel_stats = priv->channel_stats[i];
 
 		/* handle two cases:
diff --git a/drivers/net/ethernet/mellanox/mlx5/core/en_stats.c b/drivers/net/ethernet/mellanox/mlx5/core/en_stats.c
index 7f33261ba655..de38b60806c2 100644
--- a/drivers/net/ethernet/mellanox/mlx5/core/en_stats.c
+++ b/drivers/net/ethernet/mellanox/mlx5/core/en_stats.c
@@ -515,6 +515,7 @@ static void mlx5e_stats_update_stats_rq_page_pool(struct mlx5e_channel *c)
 static MLX5E_DECLARE_STATS_GRP_OP_UPDATE_STATS(sw)
 {
 	struct mlx5e_sw_stats *s = &priv->stats.sw;
+	u16 nch = mlx5e_stats_nch_read(priv);
 	int i;
 
 	memset(s, 0, sizeof(*s));
@@ -522,7 +523,7 @@ static MLX5E_DECLARE_STATS_GRP_OP_UPDATE_STATS(sw)
 	for (i = 0; i < priv->channels.num; i++) /* for active channels only */
 		mlx5e_stats_update_stats_rq_page_pool(priv->channels.c[i]);
 
-	for (i = 0; i < priv->stats_nch; i++) {
+	for (i = 0; i < nch; i++) {
 		struct mlx5e_channel_stats *channel_stats =
 			priv->channel_stats[i];
 
@@ -2614,7 +2615,7 @@ static MLX5E_DECLARE_STATS_GRP_OP_UPDATE_STATS(ptp) { return; }
 
 static MLX5E_DECLARE_STATS_GRP_OP_NUM_STATS(channels)
 {
-	int max_nch = priv->stats_nch;
+	int max_nch = mlx5e_stats_nch_read(priv);
 
 	return (NUM_RQ_STATS * max_nch) +
 	       (NUM_CH_STATS * max_nch) +
@@ -2627,8 +2628,8 @@ static MLX5E_DECLARE_STATS_GRP_OP_NUM_STATS(channels)
（改动共196行，只列前160行）
```

