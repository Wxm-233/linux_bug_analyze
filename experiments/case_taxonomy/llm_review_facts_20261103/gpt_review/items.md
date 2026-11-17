# 待复核的标记（18条）

## H0_00

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】默认实现规则：公共代码中的某个默认实现，arm64、x86、LoongArch三个架构都提供了自己的版本，只有RISC-V沿用默认实现。

【被标记的位置】init/main.c中的trap_init

【程序给出的理由】weak default overridden by arm64, x86 and loongarch, not by riscv

【trap_init的代码】
```c
  785  void __init __weak trap_init(void)  { }
```

【参照：arm64的trap_init（arch/arm64/kernel/traps.c）】
```c
 1179  void __init trap_init(void)  {
 1180  	register_kernel_break_hook(&bug_break_hook);
 1181  #ifdef CONFIG_CFI_CLANG
 1182  	register_kernel_break_hook(&cfi_break_hook);
 1183  #endif
 1184  	register_kernel_break_hook(&fault_break_hook);
 1185  #ifdef CONFIG_KASAN_SW_TAGS
 1186  	register_kernel_break_hook(&kasan_break_hook);
 1187  #endif
 1188  #ifdef CONFIG_UBSAN_TRAP
 1189  	register_kernel_break_hook(&ubsan_break_hook);
 1190  #endif
 1191  	debug_traps_init();
 1192  }
```

【参照：x86的trap_init（arch/x86/include/asm/traps.h）】
```c
（未取到）
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## H0_01

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】默认实现规则：公共代码中的某个默认实现，arm64、x86、LoongArch三个架构都提供了自己的版本，只有RISC-V沿用默认实现。

【被标记的位置】kernel/bpf/core.c中的bpf_jit_supports_subprog_tailcalls

【程序给出的理由】weak default overridden by arm64, x86 and loongarch, not by riscv

【bpf_jit_supports_subprog_tailcalls的代码】
```c
 2878  bool __weak bpf_jit_supports_subprog_tailcalls(void)  {
 2879  	return false;
 2880  }
```

【参照：arm64的bpf_jit_supports_subprog_tailcalls（arch/arm64/net/bpf_jit_comp.c）】
```c
 1703  bool bpf_jit_supports_subprog_tailcalls(void)  {
 1704  	return true;
 1705  }
```

【参照：x86的bpf_jit_supports_subprog_tailcalls（arch/x86/net/bpf_jit_comp.c）】
```c
 2888  bool bpf_jit_supports_subprog_tailcalls(void)  {
 2889  	return true;
 2890  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## H0_02

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】默认实现规则：公共代码中的某个默认实现，arm64、x86、LoongArch三个架构都提供了自己的版本，只有RISC-V沿用默认实现。

【被标记的位置】include/linux/cache.h中的__read_mostly

【程序给出的理由】ifndef default overridden by arm64, x86 and loongarch, not by riscv

【__read_mostly的代码】
```c
   27  #ifndef __read_mostly
   28  #define __read_mostly
   29  #endif
   30  
   31  /*
   32   * __ro_after_init is used to mark things that are read-only after init (i.e.
   33   * after mark_rodata_ro() has been called). These are effectively read-only,
   34   * but may get written to during init, so can't live in .rodata (via "const").
   35   */
   36  #ifndef __ro_after_init
   37  #define __ro_after_init __section(".data..ro_after_init")
   38  #endif
   39  
   40  #ifndef ____cacheline_aligned
   41  #define ____cacheline_aligned __attribute__((__aligned__(SMP_CACHE_BYTES)))
   42  #endif
   43  
   44  #ifndef ____cacheline_aligned_in_smp
   45  #ifdef CONFIG_SMP
   46  #define ____cacheline_aligned_in_smp ____cacheline_aligned
   47  #else
   48  #define ____cacheline_aligned_in_smp
   49  #endif /* CONFIG_SMP */
   50  #endif
   51  
   52  #ifndef __cacheline_aligned
```

【参照：arm64的__read_mostly（arch/arm64/include/asm/cache.h）】
```c
   83  #define __read_mostly __section(".data..read_mostly")
   84  
   85  static inline int cache_line_size_of_cpu(void)
   86  {
   87  	u32 cwg = cache_type_cwg();
   88  
   89  	return cwg ? 4 << cwg : ARCH_DMA_MINALIGN;
   90  }
   91  
   92  int cache_line_size(void);
   93  
   94  #define dma_get_cache_alignment	cache_line_size
   95  
   96  /*
   97   * Read the effective value of CTR_EL0.
   98   *
   99   * According to ARM ARM for ARMv8-A (ARM DDI 0487C.a),
  100   * section D10.2.33 "CTR_EL0, Cache Type Register" :
  101   *
  102   * CTR_EL0.IDC reports the data cache clean requirements for
  103   * instruction to data coherence.
  104   *
  105   *  0 - dcache clean to PoU is required unless :
  106   *     (CLIDR_EL1.LoC == 0) || (CLIDR_EL1.LoUIS == 0 && CLIDR_EL1.LoUU == 0)
  107   *  1 - dcache clean to PoU is not required for i-to-d coherence.
  108   *
```

【参照：x86的__read_mostly（arch/x86/include/asm/cache.h）】
```c
   11  #define __read_mostly __section(".data..read_mostly")
   12  
   13  #define INTERNODE_CACHE_SHIFT CONFIG_X86_INTERNODE_CACHE_SHIFT
   14  #define INTERNODE_CACHE_BYTES (1 << INTERNODE_CACHE_SHIFT)
   15  
   16  #ifdef CONFIG_X86_VSMP
   17  #ifdef CONFIG_SMP
   18  #define __cacheline_aligned_in_smp					\
   19  	__attribute__((__aligned__(INTERNODE_CACHE_BYTES)))		\
   20  	__page_aligned_data
   21  #endif
   22  #endif
   23  
   24  #endif /* _ASM_X86_CACHE_H */
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## H0_03

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】默认实现规则：公共代码中的某个默认实现，arm64、x86、LoongArch三个架构都提供了自己的版本，只有RISC-V沿用默认实现。

【被标记的位置】include/linux/nospec.h中的array_index_mask_nospec

【程序给出的理由】ifndef default overridden by arm64, x86 and loongarch, not by riscv

【array_index_mask_nospec的代码】
```c
   30  static inline unsigned long array_index_mask_nospec(unsigned long index, 						    unsigned long size)  {
   31  	/*
   32  	 * Always calculate and emit the mask even if the compiler
   33  	 * thinks the mask is not needed. The compiler does not take
   34  	 * into account the value of @index under speculation.
   35  	 */
   36  	OPTIMIZER_HIDE_VAR(index);
   37  	return ~(long)(index | (size - 1UL - index)) >> (BITS_PER_LONG - 1);
   38  }
```

【参照：arm64的array_index_mask_nospec（arch/arm64/include/asm/barrier.h）】
```c
   86  static inline unsigned long array_index_mask_nospec(unsigned long idx, 						    unsigned long sz)  {
   87  	unsigned long mask;
   88  
   89  	asm volatile(
   90  	"	cmp	%1, %2\n"
   91  	"	sbc	%0, xzr, xzr\n"
   92  	: "=r" (mask)
   93  	: "r" (idx), "Ir" (sz)
   94  	: "cc");
   95  
   96  	csdb();
   97  	return mask;
   98  }
```

【参照：x86的array_index_mask_nospec（arch/x86/include/asm/barrier.h）】
```c
   38  static inline unsigned long array_index_mask_nospec(unsigned long index, 		unsigned long size)  {
   39  	unsigned long mask;
   40  
   41  	asm volatile ("cmp %1,%2; sbb %0,%0;"
   42  			:"=r" (mask)
   43  			:"g"(size),"r" (index)
   44  			:"cc");
   45  	return mask;
   46  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## H0_04

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】默认实现规则：公共代码中的某个默认实现，arm64、x86、LoongArch三个架构都提供了自己的版本，只有RISC-V沿用默认实现。

【被标记的位置】include/linux/pgtable.h中的pte_accessible

【程序给出的理由】ifndef default overridden by arm64, x86 and loongarch, not by riscv

【pte_accessible的代码】
```c
  930  #ifndef pte_accessible
  931  # define pte_accessible(mm, pte)	((void)(pte), 1)
  932  #endif
  933  
  934  #ifndef flush_tlb_fix_spurious_fault
  935  #define flush_tlb_fix_spurious_fault(vma, address, ptep) flush_tlb_page(vma, address)
  936  #endif
  937  
  938  /*
  939   * When walking page tables, get the address of the next boundary,
  940   * or the end address of the range if that comes earlier.  Although no
  941   * vma end wraps to 0, rounded up __boundary may wrap to 0 throughout.
  942   */
  943  
  944  #define pgd_addr_end(addr, end)						\
  945  ({	unsigned long __boundary = ((addr) + PGDIR_SIZE) & PGDIR_MASK;	\
  946  	(__boundary - 1 < (end) - 1)? __boundary: (end);		\
  947  })
  948  
  949  #ifndef p4d_addr_end
  950  #define p4d_addr_end(addr, end)						\
  951  ({	unsigned long __boundary = ((addr) + P4D_SIZE) & P4D_MASK;	\
  952  	(__boundary - 1 < (end) - 1)? __boundary: (end);		\
  953  })
  954  #endif
  955  
```

【参照：arm64的pte_accessible（arch/arm64/include/asm/pgtable.h）】
```c
  143  #define pte_accessible(mm, pte)	\
  144  	(mm_tlb_flush_pending(mm) ? pte_present(pte) : pte_valid(pte))
  145  
  146  /*
  147   * p??_access_permitted() is true for valid user mappings (PTE_USER
  148   * bit set, subject to the write permission check). For execute-only
  149   * mappings, like PROT_EXEC with EPAN (both PTE_USER and PTE_UXN bits
  150   * not set) must return false. PROT_NONE mappings do not have the
  151   * PTE_VALID bit set.
  152   */
  153  #define pte_access_permitted(pte, write) \
  154  	(((pte_val(pte) & (PTE_VALID | PTE_USER)) == (PTE_VALID | PTE_USER)) && (!(write) || pte_write(pte)))
  155  #define pmd_access_permitted(pmd, write) \
  156  	(pte_access_permitted(pmd_pte(pmd), (write)))
  157  #define pud_access_permitted(pud, write) \
  158  	(pte_access_permitted(pud_pte(pud), (write)))
  159  
  160  static inline pte_t clear_pte_bit(pte_t pte, pgprot_t prot)
  161  {
  162  	pte_val(pte) &= ~pgprot_val(prot);
  163  	return pte;
  164  }
  165  
  166  static inline pte_t set_pte_bit(pte_t pte, pgprot_t prot)
  167  {
  168  	pte_val(pte) |= pgprot_val(prot);
```

【参照：x86的pte_accessible（arch/x86/include/asm/pgtable.h）】
```c
  980  static inline bool pte_accessible(struct mm_struct *mm, pte_t a)  {
  981  	if (pte_flags(a) & _PAGE_PRESENT)
  982  		return true;
  983  
  984  	if ((pte_flags(a) & _PAGE_PROTNONE) &&
  985  			atomic_read(&mm->tlb_flush_pending))
  986  		return true;
  987  
  988  	return false;
  989  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## H0_05

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】默认实现规则：公共代码中的某个默认实现，arm64、x86、LoongArch三个架构都提供了自己的版本，只有RISC-V沿用默认实现。

【被标记的位置】include/asm-generic/hardirq.h中的ack_bad_irq

【程序给出的理由】ifndef default overridden by arm64, x86 and loongarch, not by riscv

【ack_bad_irq的代码】
```c
   21  static inline void ack_bad_irq(unsigned int irq)  {
   22  	printk(KERN_CRIT "unexpected IRQ trap at vector %02x\n", irq);
   23  }
```

【参照：arm64的ack_bad_irq（arch/arm64/include/asm/hardirq.h）】
```c
   89  static inline void ack_bad_irq(unsigned int irq)  {
   90  	extern unsigned long irq_err_count;
   91  	irq_err_count++;
   92  }
```

【参照：x86的ack_bad_irq（arch/x86/include/asm/hardirq.h）】
```c
（未取到）
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## H0_06

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】默认实现规则：公共代码中的某个默认实现，arm64、x86、LoongArch三个架构都提供了自己的版本，只有RISC-V沿用默认实现。

【被标记的位置】include/asm-generic/io.h中的memset_io

【程序给出的理由】ifndef default overridden by arm64, x86 and loongarch, not by riscv

【memset_io的代码】
```c
 1165  static inline void memset_io(volatile void __iomem *addr, int value, 			     size_t size)  {
 1166  	memset(__io_virt(addr), value, size);
 1167  }
```

【参照：arm64的memset_io（arch/arm64/include/asm/io.h）】
```c
  134  #define memset_io(c,v,l)	__memset_io((c),(v),(l))
  135  #define memcpy_fromio(a,c,l)	__memcpy_fromio((a),(c),(l))
  136  #define memcpy_toio(c,a,l)	__memcpy_toio((c),(a),(l))
  137  
  138  /*
  139   * I/O memory mapping functions.
  140   */
  141  
  142  #define ioremap_prot ioremap_prot
  143  
  144  #define _PAGE_IOREMAP PROT_DEVICE_nGnRE
  145  
  146  #define ioremap_wc(addr, size)	\
  147  	ioremap_prot((addr), (size), PROT_NORMAL_NC)
  148  #define ioremap_np(addr, size)	\
  149  	ioremap_prot((addr), (size), PROT_DEVICE_nGnRnE)
  150  
  151  /*
  152   * io{read,write}{16,32,64}be() macros
  153   */
  154  #define ioread16be(p)		({ __u16 __v = be16_to_cpu((__force __be16)__raw_readw(p)); __iormb(__v); __v; })
  155  #define ioread32be(p)		({ __u32 __v = be32_to_cpu((__force __be32)__raw_readl(p)); __iormb(__v); __v; })
  156  #define ioread64be(p)		({ __u64 __v = be64_to_cpu((__force __be64)__raw_readq(p)); __iormb(__v); __v; })
  157  
  158  #define iowrite16be(v,p)	({ __iowmb(); __raw_writew((__force __u16)cpu_to_be16(v), p); })
  159  #define iowrite32be(v,p)	({ __iowmb(); __raw_writel((__force __u32)cpu_to_be32(v), p); })
```

【参照：x86的memset_io（arch/x86/include/asm/io.h）】
```c
  210  #define memset_io memset_io
  211  
  212  /*
  213   * ISA space is 'always mapped' on a typical x86 system, no need to
  214   * explicitly ioremap() it. The fact that the ISA IO space is mapped
  215   * to PAGE_OFFSET is pure coincidence - it does not mean ISA values
  216   * are physical addresses. The following constant pointer can be
  217   * used as the IO-area pointer (it can be iounmapped as well, so the
  218   * analogy with PCI is quite large):
  219   */
  220  #define __ISA_IO_base ((char __iomem *)(PAGE_OFFSET))
  221  
  222  #endif /* __KERNEL__ */
  223  
  224  extern void native_io_delay(void);
  225  
  226  extern int io_delay_type;
  227  extern void io_delay_init(void);
  228  
  229  #if defined(CONFIG_PARAVIRT)
  230  #include <asm/paravirt.h>
  231  #else
  232  
  233  static inline void slow_down_io(void)
  234  {
  235  	native_io_delay();
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## H0_07

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】推测执行越界规则：函数对一个可能来自客体（虚拟机）或用户的下标做了上界检查，随后用它访问数组，却没有用array_index_nospec，可能被推测执行越界利用（Spectre-v1）。

【被标记的位置】arch/riscv/kernel/cpu_ops_spinwait.c中的cpu_update_secondary_bootdata

【程序给出的理由】line 37: [hartid] after bound check at line 32, no array_index_nospec; line 39: [hartid] after bound check at line 32, no array_index_nospec

【cpu_update_secondary_bootdata的代码】
```c
   22  static void cpu_update_secondary_bootdata(unsigned int cpuid, 				   struct task_struct *tidle)  {
   23  	unsigned long hartid = cpuid_to_hartid_map(cpuid);
   24  
   25  	/*
   26  	 * The hartid must be less than NR_CPUS to avoid out-of-bound access
   27  	 * errors for __cpu_spinwait_stack/task_pointer. That is not always possible
   28  	 * for platforms with discontiguous hartid numbering scheme. That's why
   29  	 * spinwait booting is not the recommended approach for any platforms
   30  	 * booting Linux in S-mode and can be disabled in the future.
   31  	 */
   32  	if (hartid == INVALID_HARTID || hartid >= (unsigned long) NR_CPUS)
   33  		return;
   34  
   35  	/* Make sure tidle is updated */
   36  	smp_mb();
   37  	WRITE_ONCE(__cpu_spinwait_stack_pointer[hartid],
   38  		   task_stack_page(tidle) + THREAD_SIZE);
   39  	WRITE_ONCE(__cpu_spinwait_task_pointer[hartid], tidle);
   40  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## H0_08

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】推测执行越界规则：函数对一个可能来自客体（虚拟机）或用户的下标做了上界检查，随后用它访问数组，却没有用array_index_nospec，可能被推测执行越界利用（Spectre-v1）。

【被标记的位置】arch/riscv/kernel/kgdb.c中的dbg_get_reg

【程序给出的理由】line 212: [regno] after bound check at line 209, no array_index_nospec; line 213: [regno] after bound check at line 209, no array_index_nospec; line 214: [regno] after bound check at line 209, no array_index_nospec

【dbg_get_reg的代码】
```c
  208  char *dbg_get_reg(int regno, void *mem, struct pt_regs *regs)  {
  209  	if (regno >= DBG_MAX_REG_NUM || regno < 0)
  210  		return NULL;
  211  
  212  	if (dbg_reg_def[regno].offset != -1)
  213  		memcpy(mem, (void *)regs + dbg_reg_def[regno].offset,
  214  		       dbg_reg_def[regno].size);
  215  	else
  216  		memset(mem, 0, dbg_reg_def[regno].size);
  217  	return dbg_reg_def[regno].name;
  218  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## H0_09

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】推测执行越界规则：函数对一个可能来自客体（虚拟机）或用户的下标做了上界检查，随后用它访问数组，却没有用array_index_nospec，可能被推测执行越界利用（Spectre-v1）。

【被标记的位置】arch/riscv/kvm/aia_aplic.c中的aplic_read_sourcecfg

【程序给出的理由】line 48: [irq] after bound check at line 46, no array_index_nospec

【aplic_read_sourcecfg的代码】
```c
   41  static u32 aplic_read_sourcecfg(struct aplic *aplic, u32 irq)  {
   42  	u32 ret;
   43  	unsigned long flags;
   44  	struct aplic_irq *irqd;
   45  
   46  	if (!irq || aplic->nr_irqs <= irq)
   47  		return 0;
   48  	irqd = &aplic->irqs[irq];
   49  
   50  	raw_spin_lock_irqsave(&irqd->lock, flags);
   51  	ret = irqd->sourcecfg;
   52  	raw_spin_unlock_irqrestore(&irqd->lock, flags);
   53  
   54  	return ret;
   55  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## H0_10

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】推测执行越界规则：函数对一个可能来自客体（虚拟机）或用户的下标做了上界检查，随后用它访问数组，却没有用array_index_nospec，可能被推测执行越界利用（Spectre-v1）。

【被标记的位置】arch/riscv/kvm/aia_aplic.c中的aplic_read_pending

【程序给出的理由】line 119: [irq] after bound check at line 117, no array_index_nospec

【aplic_read_pending的代码】
```c
  112  static bool aplic_read_pending(struct aplic *aplic, u32 irq)  {
  113  	bool ret;
  114  	unsigned long flags;
  115  	struct aplic_irq *irqd;
  116  
  117  	if (!irq || aplic->nr_irqs <= irq)
  118  		return false;
  119  	irqd = &aplic->irqs[irq];
  120  
  121  	raw_spin_lock_irqsave(&irqd->lock, flags);
  122  	ret = (irqd->state & APLIC_IRQ_STATE_PENDING) ? true : false;
  123  	raw_spin_unlock_irqrestore(&irqd->lock, flags);
  124  
  125  	return ret;
  126  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## H0_11

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】推测执行越界规则：函数对一个可能来自客体（虚拟机）或用户的下标做了上界检查，随后用它访问数组，却没有用array_index_nospec，可能被推测执行越界利用（Spectre-v1）。

【被标记的位置】arch/riscv/kvm/aia_aplic.c中的aplic_write_pending

【程序给出的理由】line 135: [irq] after bound check at line 133, no array_index_nospec

【aplic_write_pending的代码】
```c
  129  static void aplic_write_pending(struct aplic *aplic, u32 irq, bool pending)  {
  130  	unsigned long flags, sm;
  131  	struct aplic_irq *irqd;
  132  
  133  	if (!irq || aplic->nr_irqs <= irq)
  134  		return;
  135  	irqd = &aplic->irqs[irq];
  136  
  137  	raw_spin_lock_irqsave(&irqd->lock, flags);
  138  
  139  	sm = irqd->sourcecfg & APLIC_SOURCECFG_SM_MASK;
  140  	if (!pending &&
  141  	    ((sm == APLIC_SOURCECFG_SM_LEVEL_HIGH) ||
  142  	     (sm == APLIC_SOURCECFG_SM_LEVEL_LOW)))
  143  		goto skip_write_pending;
  144  
  145  	if (pending)
  146  		irqd->state |= APLIC_IRQ_STATE_PENDING;
  147  	else
  148  		irqd->state &= ~APLIC_IRQ_STATE_PENDING;
  149  
  150  skip_write_pending:
  151  	raw_spin_unlock_irqrestore(&irqd->lock, flags);
  152  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## H0_12

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】推测执行越界规则：函数对一个可能来自客体（虚拟机）或用户的下标做了上界检查，随后用它访问数组，却没有用array_index_nospec，可能被推测执行越界利用（Spectre-v1）。

【被标记的位置】arch/riscv/kvm/aia_aplic.c中的kvm_riscv_aia_aplic_inject

【程序给出的理由】line 260: [source] after bound check at line 258, no array_index_nospec

【kvm_riscv_aia_aplic_inject的代码】
```c
  251  int kvm_riscv_aia_aplic_inject(struct kvm *kvm, u32 source, bool level)  {
  252  	u32 target;
  253  	bool inject = false, ie;
  254  	unsigned long flags;
  255  	struct aplic_irq *irqd;
  256  	struct aplic *aplic = kvm->arch.aia.aplic_state;
  257  
  258  	if (!aplic || !source || (aplic->nr_irqs <= source))
  259  		return -ENODEV;
  260  	irqd = &aplic->irqs[source];
  261  	ie = (aplic->domaincfg & APLIC_DOMAINCFG_IE) ? true : false;
  262  
  263  	raw_spin_lock_irqsave(&irqd->lock, flags);
  264  
  265  	if (irqd->sourcecfg & APLIC_SOURCECFG_D)
  266  		goto skip_unlock;
  267  
  268  	switch (irqd->sourcecfg & APLIC_SOURCECFG_SM_MASK) {
  269  	case APLIC_SOURCECFG_SM_EDGE_RISE:
  270  		if (level && !(irqd->state & APLIC_IRQ_STATE_INPUT) &&
  271  		    !(irqd->state & APLIC_IRQ_STATE_PENDING))
  272  			irqd->state |= APLIC_IRQ_STATE_PENDING;
  273  		break;
  274  	case APLIC_SOURCECFG_SM_EDGE_FALL:
  275  		if (!level && (irqd->state & APLIC_IRQ_STATE_INPUT) &&
  276  		    !(irqd->state & APLIC_IRQ_STATE_PENDING))
  277  			irqd->state |= APLIC_IRQ_STATE_PENDING;
  278  		break;
  279  	case APLIC_SOURCECFG_SM_LEVEL_HIGH:
  280  		if (level && !(irqd->state & APLIC_IRQ_STATE_PENDING))
  281  			irqd->state |= APLIC_IRQ_STATE_PENDING;
  282  		break;
  283  	case APLIC_SOURCECFG_SM_LEVEL_LOW:
  284  		if (!level && !(irqd->state & APLIC_IRQ_STATE_PENDING))
  285  			irqd->state |= APLIC_IRQ_STATE_PENDING;
  286  		break;
  287  	}
  288  
  289  	if (level)
  290  		irqd->state |= APLIC_IRQ_STATE_INPUT;
  291  	else
  292  		irqd->state &= ~APLIC_IRQ_STATE_INPUT;
  293  
  294  	target = irqd->target;
  295  	if (ie && ((irqd->state & APLIC_IRQ_STATE_ENPEND) ==
  296  		   APLIC_IRQ_STATE_ENPEND)) {
  297  		irqd->state &= ~APLIC_IRQ_STATE_PENDING;
  298  		inject = true;
  299  	}
  300  
  301  skip_unlock:
  302  	raw_spin_unlock_irqrestore(&irqd->lock, flags);
  303  
  304  	if (inject)
  305  		aplic_inject_msi(kvm, source, target);
  306  
  307  	return 0;
  308  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## H0_13

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】推测执行越界规则：函数对一个可能来自客体（虚拟机）或用户的下标做了上界检查，随后用它访问数组，却没有用array_index_nospec，可能被推测执行越界利用（Spectre-v1）。

【被标记的位置】arch/riscv/kvm/vcpu_onereg.c中的riscv_vcpu_get_isa_ext_single

【程序给出的理由】line 463: [reg_num] after bound check at line 459, no array_index_nospec

【riscv_vcpu_get_isa_ext_single的代码】
```c
  456  static int riscv_vcpu_get_isa_ext_single(struct kvm_vcpu *vcpu, 					 unsigned long reg_num, 					 unsigned long *reg_val)  {
  457  	unsigned long host_isa_ext;
  458  
  459  	if (reg_num >= KVM_RISCV_ISA_EXT_MAX ||
  460  	    reg_num >= ARRAY_SIZE(kvm_isa_ext_arr))
  461  		return -ENOENT;
  462  
  463  	host_isa_ext = kvm_isa_ext_arr[reg_num];
  464  	if (!__riscv_isa_extension_available(NULL, host_isa_ext))
  465  		return -ENOENT;
  466  
  467  	*reg_val = 0;
  468  	if (__riscv_isa_extension_available(vcpu->arch.isa, host_isa_ext))
  469  		*reg_val = 1; /* Mark the given extension as available */
  470  
  471  	return 0;
  472  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## H0_14

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】推测执行越界规则：函数对一个可能来自客体（虚拟机）或用户的下标做了上界检查，随后用它访问数组，却没有用array_index_nospec，可能被推测执行越界利用（Spectre-v1）。

【被标记的位置】arch/riscv/kvm/vcpu_pmu.c中的kvm_riscv_vcpu_pmu_ctr_info

【程序给出的理由】line 333: [cidx] after bound check at line 328, no array_index_nospec

【kvm_riscv_vcpu_pmu_ctr_info的代码】
```c
  325  int kvm_riscv_vcpu_pmu_ctr_info(struct kvm_vcpu *vcpu, unsigned long cidx, 				struct kvm_vcpu_sbi_return *retdata)  {
  326  	struct kvm_pmu *kvpmu = vcpu_to_pmu(vcpu);
  327  
  328  	if (cidx > RISCV_KVM_MAX_COUNTERS || cidx == 1) {
  329  		retdata->err_val = SBI_ERR_INVALID_PARAM;
  330  		return 0;
  331  	}
  332  
  333  	retdata->out_val = kvpmu->pmc[cidx].cinfo.value;
  334  
  335  	return 0;
  336  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## H0_15

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的RISC-V钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/riscv/kernel/kgdb.c中的kgdb_riscv_notify

【程序给出的理由】sleep A:irq: line 332 kgdb_handle_exception -> smp_call_function_single_async

【调用链】kgdb_handle_exception（kernel/debug/debug_core.c第865行调用kgdb_cpu_enter） → kgdb_cpu_enter（kernel/debug/debug_core.c第709行调用kgdb_roundup_cpus） → kgdb_roundup_cpus（kernel/debug/debug_core.c第267行调用smp_call_function_single_async）

【kgdb_riscv_notify的代码】
```c
  317  static int kgdb_riscv_notify(struct notifier_block *self, unsigned long cmd, 			     void *ptr)  {
  318  	struct die_args *args = (struct die_args *)ptr;
  319  	struct pt_regs *regs = args->regs;
  320  	unsigned long flags;
  321  	int type;
  322  
  323  	if (user_mode(regs))
  324  		return NOTIFY_DONE;
  325  
  326  	type = kgdb_riscv_kgdbbreak(regs->epc);
  327  	if (type == NOT_KGDB_BREAK && cmd == DIE_TRAP)
  328  		return NOTIFY_DONE;
  329  
  330  	local_irq_save(flags);
  331  
  332  	if (kgdb_handle_exception(type == KGDB_SW_SINGLE_STEP ? 0 : 1,
  333  				  args->signr, cmd, regs))
  334  		return NOTIFY_DONE;
  335  
  336  	if (type == KGDB_COMPILED_BREAK)
  337  		regs->epc += 4;
  338  
  339  	local_irq_restore(flags);
  340  
  341  	return NOTIFY_STOP;
  342  }
```

【kgdb_handle_exception的代码（kernel/debug/debug_core.c）】
```c
  837  int kgdb_handle_exception(int evector, int signo, int ecode, struct pt_regs *regs)  {
  838  	struct kgdb_state kgdb_var;
  839  	struct kgdb_state *ks = &kgdb_var;
  840  	int ret = 0;
  841  
  842  	if (arch_kgdb_ops.enable_nmi)
  843  		arch_kgdb_ops.enable_nmi(0);
  844  	/*
  845  	 * Avoid entering the debugger if we were triggered due to an oops
  846  	 * but panic_timeout indicates the system should automatically
  847  	 * reboot on panic. We don't want to get stuck waiting for input
  848  	 * on such systems, especially if its "just" an oops.
  849  	 */
  850  	if (signo != SIGTRAP && panic_timeout)
  851  		return 1;
  852  
  853  	memset(ks, 0, sizeof(struct kgdb_state));
  854  	ks->cpu			= raw_smp_processor_id();
  855  	ks->ex_vector		= evector;
  856  	ks->signo		= signo;
  857  	ks->err_code		= ecode;
  858  	ks->linux_regs		= regs;
  859  
  860  	if (kgdb_reenter_check(ks))
  861  		goto out; /* Ouch, double exception ! */
  862  	if (kgdb_info[ks->cpu].enter_kgdb != 0)
  863  		goto out;
  864  
  865  	ret = kgdb_cpu_enter(ks, regs, DCPU_WANT_MASTER);
  866  out:
  867  	if (arch_kgdb_ops.enable_nmi)
  868  		arch_kgdb_ops.enable_nmi(1);
  869  	return ret;
  870  }
```

【kgdb_cpu_enter的代码（kernel/debug/debug_core.c）】
```c
  573  static int kgdb_cpu_enter(struct kgdb_state *ks, struct pt_regs *regs, 		int exception_state)  {
  574  	unsigned long flags;
  575  	int sstep_tries = 100;
  576  	int error;
  577  	int cpu;
  578  	int trace_on = 0;
  579  	int online_cpus = num_online_cpus();
  580  	u64 time_left;
  581  
  582  	kgdb_info[ks->cpu].enter_kgdb++;
  583  	kgdb_info[ks->cpu].exception_state |= exception_state;
  584  
  585  	if (exception_state == DCPU_WANT_MASTER)
  586  		atomic_inc(&masters_in_kgdb);
  587  	else
  588  		atomic_inc(&slaves_in_kgdb);
  589  
  590  	if (arch_kgdb_ops.disable_hw_break)
  591  		arch_kgdb_ops.disable_hw_break(regs);
  592  
  593  acquirelock:
  594  	rcu_read_lock();
  595  	/*
  596  	 * Interrupts will be restored by the 'trap return' code, except when
  597  	 * single stepping.
  598  	 */
  599  	local_irq_save(flags);
  600  
  601  	cpu = ks->cpu;
  602  	kgdb_info[cpu].debuggerinfo = regs;
  603  	kgdb_info[cpu].task = current;
  604  	kgdb_info[cpu].ret_state = 0;
  605  	kgdb_info[cpu].irq_depth = hardirq_count() >> HARDIRQ_SHIFT;
  606  
  607  	/* Make sure the above info reaches the primary CPU */
  608  	smp_mb();
  609  
  610  	if (exception_level == 1) {
  611  		if (raw_spin_trylock(&dbg_master_lock))
  612  			atomic_xchg(&kgdb_active, cpu);
  613  		goto cpu_master_loop;
  614  	}
  615  
  616  	/*
  617  	 * CPU will loop if it is a slave or request to become a kgdb
  618  	 * master cpu and acquire the kgdb_active lock:
  619  	 */
  620  	while (1) {
  621  cpu_loop:
  622  		if (kgdb_info[cpu].exception_state & DCPU_NEXT_MASTER) {
  623  			kgdb_info[cpu].exception_state &= ~DCPU_NEXT_MASTER;
  624  			goto cpu_master_loop;
  625  		} else if (kgdb_info[cpu].exception_state & DCPU_WANT_MASTER) {
  626  			if (raw_spin_trylock(&dbg_master_lock)) {
  627  				atomic_xchg(&kgdb_active, cpu);
  628  				break;
  629  			}
  630  		} else if (kgdb_info[cpu].exception_state & DCPU_WANT_BT) {
  631  			dump_stack();
  632  			kgdb_info[cpu].exception_state &= ~DCPU_WANT_BT;
  633  		} else if (kgdb_info[cpu].exception_state & DCPU_IS_SLAVE) {
  634  			if (!raw_spin_is_locked(&dbg_slave_lock))
  635  				goto return_normal;
  636  		} else {
  637  return_normal:
  638  			/* Return to normal operation by executing any
  639  			 * hw breakpoint fixup.
  640  			 */
  641  			if (arch_kgdb_ops.correct_hw_break)
  642  				arch_kgdb_ops.correct_hw_break();
  643  			if (trace_on)
  644  				tracing_on();
  645  			kgdb_info[cpu].debuggerinfo = NULL;
  646  			kgdb_info[cpu].task = NULL;
  647  			kgdb_info[cpu].exception_state &=
  648  				~(DCPU_WANT_MASTER | DCPU_IS_SLAVE);
  649  			kgdb_info[cpu].enter_kgdb--;
  650  			smp_mb__before_atomic();
  651  			atomic_dec(&slaves_in_kgdb);
  652  			dbg_touch_watchdogs();
...（其余173行省略）
```

【kgdb_roundup_cpus的代码（kernel/debug/debug_core.c）】
```c
  242  void __weak kgdb_roundup_cpus(void)  {
  243  	call_single_data_t *csd;
  244  	int this_cpu = raw_smp_processor_id();
  245  	int cpu;
  246  	int ret;
  247  
  248  	for_each_online_cpu(cpu) {
  249  		/* No need to roundup ourselves */
  250  		if (cpu == this_cpu)
  251  			continue;
  252  
  253  		csd = &per_cpu(kgdb_roundup_csd, cpu);
  254  
  255  		/*
  256  		 * If it didn't round up last time, don't try again
  257  		 * since smp_call_function_single_async() will block.
  258  		 *
  259  		 * If rounding_up is false then we know that the
  260  		 * previous call must have at least started and that
  261  		 * means smp_call_function_single_async() won't block.
  262  		 */
  263  		if (kgdb_info[cpu].rounding_up)
  264  			continue;
  265  		kgdb_info[cpu].rounding_up = true;
  266  
  267  		ret = smp_call_function_single_async(cpu, csd);
  268  		if (ret)
  269  			kgdb_info[cpu].rounding_up = false;
  270  	}
  271  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## H0_16

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的RISC-V钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/riscv/include/asm/kfence.h中的kfence_protect_page

【程序给出的理由】sleep D:hook: line 25 flush_tlb_kernel_range -> on_each_cpu

【调用链】flush_tlb_kernel_range（arch/riscv/include/asm/tlbflush.h第61行调用flush_tlb_all） → flush_tlb_all（arch/riscv/mm/tlbflush.c第52行调用on_each_cpu）

【kfence_protect_page的代码】
```c
   17  static inline bool kfence_protect_page(unsigned long addr, bool protect)  {
   18  	pte_t *pte = virt_to_kpte(addr);
   19  
   20  	if (protect)
   21  		set_pte(pte, __pte(pte_val(*pte) & ~_PAGE_PRESENT));
   22  	else
   23  		set_pte(pte, __pte(pte_val(*pte) | _PAGE_PRESENT));
   24  
   25  	flush_tlb_kernel_range(addr, addr + PAGE_SIZE);
   26  
   27  	return true;
   28  }
```

【flush_tlb_kernel_range的代码（arch/riscv/include/asm/tlbflush.h）】
```c
   60  static inline void flush_tlb_kernel_range(unsigned long start, 	unsigned long end)  {
   61  	flush_tlb_all();
   62  }
```

【flush_tlb_all的代码（arch/riscv/mm/tlbflush.c）】
```c
   50  void flush_tlb_all(void)  {
   51  	if (riscv_use_ipi_for_rfence())
   52  		on_each_cpu(__ipi_flush_tlb_all, NULL, 1);
   53  	else
   54  		sbi_remote_sfence_vma(NULL, 0, -1);
   55  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## H0_17

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的RISC-V钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/riscv/kernel/process.c中的arch_cpu_idle

【程序给出的理由】noinstr N1: line 40 arch_cpu_idle -> called from noinstr/__cpuidle

【arch_cpu_idle的代码】
```c
   40  void arch_cpu_idle(void)  {
   41  	cpu_do_idle();
   42  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。
