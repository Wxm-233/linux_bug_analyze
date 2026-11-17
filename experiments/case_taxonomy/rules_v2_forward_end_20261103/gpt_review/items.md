# 待复核的问题（Linux终点版本df2908090cda，RISC-V）

## E00

**规则**：执行上下文：在不能睡眠或不能插桩的地方，做了可能睡眠或会被插桩的事。

**原子上下文的来源**：本函数自己的原子区间内（关中断、持锁或禁抢占）

**被标记的位置**：`arch/riscv/kernel/machine_kexec.c`中的`machine_shutdown`（sleep A:irq: line 116 smp_shutdown_nonboot_cpus -> smp_shutdown_nonboot_cpus）

**调用链**：（直接）

```c
  108  void machine_shutdown(void)  {
  109  	/*
  110  	 * No more interrupts on this hart
  111  	 * until we are back up.
  112  	 */
  113  	local_irq_disable();
  114  
  115  #if defined(CONFIG_HOTPLUG_CPU)
  116  	smp_shutdown_nonboot_cpus(smp_processor_id());
  117  #endif
  118  }
```

## E01

**规则**：执行上下文：在不能睡眠或不能插桩的地方，做了可能睡眠或会被插桩的事。

**原子上下文的来源**：本函数自己的原子区间内（关中断、持锁或禁抢占）

**被标记的位置**：`arch/riscv/kernel/traps.c`中的`die`（sleep A:raw: line 86 bust_spinlocks -> might_sleep）；`arch/riscv/kernel/traps.c`中的`die`（sleep A:raw: line 101 bust_spinlocks -> might_sleep）

**调用链**：`bust_spinlocks`调用`console_unblank` → `console_unblank`调用`console_lock` → `console_lock`调用`might_sleep`

```c
   76  void die(struct pt_regs *regs, const char *str)  {
   77  	static int die_counter;
   78  	int ret;
   79  	long cause;
   80  	unsigned long flags;
   81  
   82  	oops_enter();
   83  
   84  	raw_spin_lock_irqsave(&die_lock, flags);
   85  	console_verbose();
   86  	bust_spinlocks(1);
   87  
   88  	pr_emerg("%s [#%d]\n", str, ++die_counter);
   89  	print_modules();
   90  	if (regs) {
   91  		show_regs(regs);
   92  		dump_instr(KERN_EMERG, regs);
   93  	}
   94  
   95  	cause = regs ? regs->cause : -1;
   96  	ret = notify_die(DIE_OOPS, str, regs, 0, cause, SIGSEGV);
   97  
   98  	if (kexec_should_crash(current))
   99  		crash_kexec(regs);
  100  
  101  	bust_spinlocks(0);
  102  	add_taint(TAINT_DIE, LOCKDEP_NOW_UNRELIABLE);
  103  	raw_spin_unlock_irqrestore(&die_lock, flags);
  104  	oops_exit();
  105  
  106  	if (in_interrupt())
  107  		panic("Fatal exception in interrupt");
  108  	if (panic_on_oops)
  109  		panic("Fatal exception");
  110  	if (ret != NOTIFY_STOP)
  111  		make_task_dead(SIGSEGV);
  112  }
```

`bust_spinlocks`（lib/bust_spinlocks.c）：
```c
   21  void bust_spinlocks(int yes)  {
   22  	if (yes) {
   23  		++oops_in_progress;
   24  	} else {
   25  		console_unblank();
   26  		if (--oops_in_progress == 0)
   27  			wake_up_klogd();
   28  	}
   29  }
```

`console_unblank`（kernel/printk/printk.c）：
```c
 3427  void console_unblank(void)  {
 3428  	bool found_unblank = false;
 3429  	struct console *c;
 3430  	int cookie;
 3431  
 3432  	/*
 3433  	 * First check if there are any consoles implementing the unblank()
 3434  	 * callback. If not, there is no reason to continue and take the
 3435  	 * console lock, which in particular can be dangerous if
 3436  	 * @oops_in_progress is set.
 3437  	 */
 3438  	cookie = console_srcu_read_lock();
 3439  	for_each_console_srcu(c) {
 3440  		if (!console_is_usable(c, console_srcu_read_flags(c), true))
 3441  			continue;
 3442  
 3443  		if (c->unblank) {
 3444  			found_unblank = true;
 3445  			break;
 3446  		}
 3447  	}
 3448  	console_srcu_read_unlock(cookie);
 3449  	if (!found_unblank)
 3450  		return;
 3451  
 3452  	/*
 3453  	 * Stop console printing because the unblank() callback may
 3454  	 * assume the console is not within its write() callback.
 3455  	 *
 3456  	 * If @oops_in_progress is set, this may be an atomic context.
 3457  	 * In that case, attempt a trylock as best-effort.
 3458  	 */
 3459  	if (oops_in_progress) {
 3460  		/* Semaphores are not NMI-safe. */
 3461  		if (in_nmi())
 3462  			return;
 3463  
 3464  		/*
 3465  		 * Attempting to trylock the console lock can deadlock
 3466  		 * if another CPU was stopped while modifying the
 3467  		 * semaphore. "Hope and pray" that this is not the
 3468  		 * current situation.
 3469  		 */
 3470  		if (down_trylock_console_sem() != 0)
 3471  			return;
 3472  	} else
 3473  		console_lock();
 3474  
 3475  	console_locked = 1;
 3476  	console_may_schedule = 0;
...
```

## E02

**规则**：执行上下文：在不能睡眠或不能插桩的地方，做了可能睡眠或会被插桩的事。

**原子上下文的来源**：本函数自己的原子区间内（关中断、持锁或禁抢占）

**被标记的位置**：`arch/riscv/kvm/mmu.c`中的`mmu_split_memory_region`（sleep A:spin: line 232 mmu_split_huge_pages -> cond_resched）

**调用链**：`mmu_split_huge_pages`调用`cond_resched`

```c
  221  static void mmu_split_memory_region(struct kvm *kvm, int slot)  {
  222  	struct kvm_memslots *slots = kvm_memslots(kvm);
  223  	struct kvm_memory_slot *memslot = id_to_memslot(slots, slot);
  224  	phys_addr_t start = memslot->base_gfn << PAGE_SHIFT;
  225  	phys_addr_t end = (memslot->base_gfn + memslot->npages) << PAGE_SHIFT;
  226  	struct kvm_gstage gstage;
  227  	bool flush;
  228  
  229  	kvm_riscv_gstage_init(&gstage, kvm);
  230  
  231  	write_lock(&kvm->mmu_lock);
  232  	flush = mmu_split_huge_pages(&gstage, start, end);
  233  	write_unlock(&kvm->mmu_lock);
  234  
  235  	if (flush)
  236  		kvm_flush_remote_tlbs_memslot(kvm, memslot);
  237  }
```

`mmu_split_huge_pages`（arch/riscv/kvm/mmu.c）：
```c
  117  static bool mmu_split_huge_pages(struct kvm_gstage *gstage, 				 phys_addr_t start, phys_addr_t end)  {
  118  	struct kvm *kvm = gstage->kvm;
  119  	struct kvm_mmu_memory_cache *pcache = &kvm->arch.pgd_split_page_cache;
  120  	phys_addr_t addr = ALIGN_DOWN(start, PMD_SIZE);
  121  	phys_addr_t last_flush_gfn = addr >> PAGE_SHIFT;
  122  	int count = gstage->pgd_levels;
  123  	bool flush = false;
  124  	int ret;
  125  
  126  	lockdep_assert_held_write(&kvm->mmu_lock);
  127  
  128  	while (addr < end) {
  129  		if (need_topup_split_caches_or_resched(kvm, count)) {
  130  			if (flush) {
  131  				kvm_flush_remote_tlbs_range(kvm, last_flush_gfn,
  132  					  (addr >> PAGE_SHIFT) - last_flush_gfn);
  133  				last_flush_gfn = addr >> PAGE_SHIFT;
  134  				flush = false;
  135  			}
  136  
  137  			write_unlock(&kvm->mmu_lock);
  138  			cond_resched();
  139  
  140  			ret = kvm_mmu_topup_memory_cache(pcache, count);
  141  			if (ret) {
  142  				kvm_err("Failed to toup split page cache\n");
  143  				write_lock(&kvm->mmu_lock);
  144  				return flush;
  145  			}
  146  			write_lock(&kvm->mmu_lock);
  147  		}
  148  
  149  		if (!kvm->arch.pgd)
  150  			return flush;
  151  
  152  		flush |= kvm_riscv_gstage_split_huge(gstage, pcache, addr, 0, false);
  153  
  154  		addr += PMD_SIZE;
  155  	}
  156  
  157  	return flush;
  158  }
```

## E03

**规则**：执行上下文：在不能睡眠或不能插桩的地方，做了可能睡眠或会被插桩的事。

**原子上下文的来源**：陷入处理函数开中断之前（RISC-V进入陷入处理时中断关闭）

**被标记的位置**：`arch/riscv/kernel/traps.c`中的`do_page_fault`（sleep B:trap: line 415 handle_page_fault -> mutex_lock）

**调用链**：`handle_page_fault`调用`handle_mm_fault` → `handle_mm_fault`调用`hugetlb_fault` → `hugetlb_fault`调用`mutex_lock`

```c
  412  asmlinkage __visible noinstr void do_page_fault(struct pt_regs *regs)  {
  413  	irqentry_state_t state = irqentry_enter(regs);
  414  
  415  	handle_page_fault(regs);
  416  
  417  	local_irq_disable();
  418  
  419  	irqentry_exit(regs, state);
  420  }
```

`handle_page_fault`（arch/riscv/mm/fault.c）：
```c
  279  void handle_page_fault(struct pt_regs *regs)  {
  280  	struct task_struct *tsk;
  281  	struct vm_area_struct *vma;
  282  	struct mm_struct *mm;
  283  	unsigned long addr, cause;
  284  	unsigned int flags = FAULT_FLAG_DEFAULT;
  285  	int code = SEGV_MAPERR;
  286  	vm_fault_t fault;
  287  
  288  	cause = regs->cause;
  289  	addr = regs->badaddr;
  290  
  291  	tsk = current;
  292  	mm = tsk->mm;
  293  
  294  	if (kprobe_page_fault(regs, cause))
  295  		return;
  296  
  297  	if (user_mode(regs))
  298  		trace_page_fault_user(addr, regs, cause);
  299  	else
  300  		trace_page_fault_kernel(addr, regs, cause);
  301  
  302  	/*
  303  	 * Fault-in kernel-space virtual memory on-demand.
  304  	 * The 'reference' page table is init_mm.pgd.
  305  	 *
  306  	 * NOTE! We MUST NOT take any locks for this case. We may
  307  	 * be in an interrupt or a critical region, and should
  308  	 * only copy the information from the master page table,
  309  	 * nothing more.
  310  	 */
  311  	if ((!IS_ENABLED(CONFIG_MMU) || !IS_ENABLED(CONFIG_64BIT)) &&
  312  	    unlikely(addr >= VMALLOC_START && addr < VMALLOC_END)) {
  313  		vmalloc_fault(regs, code, addr);
  314  		return;
  315  	}
  316  
  317  	/* Enable interrupts if they were enabled in the parent context. */
  318  	if (!regs_irqs_disabled(regs))
  319  		local_irq_enable();
  320  
  321  	/*
  322  	 * If we're in an interrupt, have no user context, or are running
  323  	 * in an atomic region, then we must not take the fault.
  324  	 */
  325  	if (unlikely(faulthandler_disabled() || !mm)) {
  326  		tsk->thread.bad_cause = cause;
  327  		no_context(regs, addr);
  328  		return;
...
```

`handle_mm_fault`（mm/memory.c）：
```c
 6843  vm_fault_t handle_mm_fault(struct vm_area_struct *vma, unsigned long address, 			   unsigned int flags, struct pt_regs *regs)  {
 6844  	/* If the fault handler drops the mmap_lock, vma may be freed */
 6845  	struct mm_struct *mm = vma->vm_mm;
 6846  	vm_fault_t ret;
 6847  	bool is_droppable;
 6848  
 6849  	__set_current_state(TASK_RUNNING);
 6850  
 6851  	ret = sanitize_fault_flags(vma, &flags);
 6852  	if (ret)
 6853  		goto out;
 6854  
 6855  	if (!arch_vma_access_permitted(vma, flags & FAULT_FLAG_WRITE,
 6856  					    flags & FAULT_FLAG_INSTRUCTION,
 6857  					    flags & FAULT_FLAG_REMOTE)) {
 6858  		ret = VM_FAULT_SIGSEGV;
 6859  		goto out;
 6860  	}
 6861  
 6862  	is_droppable = !!(vma->vm_flags & VM_DROPPABLE);
 6863  
 6864  	/*
 6865  	 * Enable the memcg OOM handling for faults triggered in user
 6866  	 * space.  Kernel faults are handled more gracefully.
 6867  	 */
 6868  	if (flags & FAULT_FLAG_USER)
 6869  		mem_cgroup_enter_user_fault();
 6870  
 6871  	lru_gen_enter_fault(vma);
 6872  
 6873  	if (unlikely(is_vm_hugetlb_page(vma)))
 6874  		ret = hugetlb_fault(vma->vm_mm, vma, address, flags);
 6875  	else
 6876  		ret = __handle_mm_fault(vma, address, flags);
 6877  
 6878  	/*
 6879  	 * Warning: It is no longer safe to dereference vma-> after this point,
 6880  	 * because mmap_lock might have been dropped by __handle_mm_fault(), so
 6881  	 * vma might be destroyed from underneath us.
 6882  	 */
 6883  
 6884  	lru_gen_exit_fault();
 6885  
 6886  	/* If the mapping is droppable, then errors due to OOM aren't fatal. */
 6887  	if (is_droppable)
 6888  		ret &= ~VM_FAULT_OOM;
 6889  
 6890  	if (flags & FAULT_FLAG_USER) {
 6891  		mem_cgroup_exit_user_fault();
 6892  		/*
...
```

## E04

**规则**：执行上下文：在不能睡眠或不能插桩的地方，做了可能睡眠或会被插桩的事。

**原子上下文的来源**：陷入处理函数开中断之前（RISC-V进入陷入处理时中断关闭）

**被标记的位置**：`arch/riscv/kernel/traps.c`中的`do_trap_software_check`（rt B:trap: line 406 die -> spin_lock_irqsave）

**调用链**：`die`调用`oops_enter` → `oops_enter`调用`do_oops_enter_exit` → `do_oops_enter_exit`调用`spin_lock_irqsave`

```c
  395  asmlinkage __visible __trap_section void do_trap_software_check(struct pt_regs *regs)  {
  396  	if (user_mode(regs)) {
  397  		irqentry_enter_from_user_mode(regs);
  398  
  399  		/* not a cfi violation, then merge into flow of unknown trap handler */
  400  		if (!handle_user_cfi_violation(regs))
  401  			do_trap_unknown(regs);
  402  
  403  		irqentry_exit_to_user_mode(regs);
  404  	} else {
  405  		/* sw check exception coming from kernel is a bug in kernel */
  406  		die(regs, "Kernel BUG");
  407  	}
  408  }
```

`die`（arch/riscv/kernel/traps.c）：
```c
   76  void die(struct pt_regs *regs, const char *str)  {
   77  	static int die_counter;
   78  	int ret;
   79  	long cause;
   80  	unsigned long flags;
   81  
   82  	oops_enter();
   83  
   84  	raw_spin_lock_irqsave(&die_lock, flags);
   85  	console_verbose();
   86  	bust_spinlocks(1);
   87  
   88  	pr_emerg("%s [#%d]\n", str, ++die_counter);
   89  	print_modules();
   90  	if (regs) {
   91  		show_regs(regs);
   92  		dump_instr(KERN_EMERG, regs);
   93  	}
   94  
   95  	cause = regs ? regs->cause : -1;
   96  	ret = notify_die(DIE_OOPS, str, regs, 0, cause, SIGSEGV);
   97  
   98  	if (kexec_should_crash(current))
   99  		crash_kexec(regs);
  100  
  101  	bust_spinlocks(0);
  102  	add_taint(TAINT_DIE, LOCKDEP_NOW_UNRELIABLE);
  103  	raw_spin_unlock_irqrestore(&die_lock, flags);
  104  	oops_exit();
  105  
  106  	if (in_interrupt())
  107  		panic("Fatal exception in interrupt");
  108  	if (panic_on_oops)
  109  		panic("Fatal exception");
  110  	if (ret != NOTIFY_STOP)
  111  		make_task_dead(SIGSEGV);
  112  }
```

`oops_enter`（kernel/panic.c）：
```c
 1041  void oops_enter(void)  {
 1042  	nbcon_cpu_emergency_enter();
 1043  	tracing_off();
 1044  	/* can't trust the integrity of the kernel anymore: */
 1045  	debug_locks_off();
 1046  	do_oops_enter_exit();
 1047  
 1048  	if (sysctl_oops_all_cpu_backtrace)
 1049  		trigger_all_cpu_backtrace();
 1050  }
```

## E05

**规则**：执行上下文：在不能睡眠或不能插桩的地方，做了可能睡眠或会被插桩的事。

**原子上下文的来源**：公共代码在原子区间内调用本函数

**被标记的位置**：`arch/riscv/kernel/hibernate.c`中的`swsusp_arch_suspend`（rt D:hook: line 152 swsusp_save -> spin_lock_irqsave）

**调用链**：`swsusp_save`调用`count_data_pages` → `count_data_pages`调用`mark_free_pages` → `mark_free_pages`调用`spin_lock_irqsave`

```c
  146  int swsusp_arch_suspend(void)  {
  147  	int ret = 0;
  148  
  149  	if (__cpu_suspend_enter(hibernate_cpu_context)) {
  150  		sleep_cpu = smp_processor_id();
  151  		suspend_save_csrs(hibernate_cpu_context);
  152  		ret = swsusp_save();
  153  	} else {
  154  		suspend_restore_csrs(hibernate_cpu_context);
  155  		flush_tlb_all();
  156  		flush_icache_all();
  157  
  158  		/*
  159  		 * Tell the hibernation core that we've just restored the memory.
  160  		 */
  161  		in_suspend = 0;
  162  		sleep_cpu = -EINVAL;
  163  	}
  164  
  165  	return ret;
  166  }
```

`swsusp_save`（kernel/power/snapshot.c）：
```c
 2110  asmlinkage __visible int swsusp_save(void)  {
 2111  	unsigned int nr_pages, nr_highmem;
 2112  
 2113  	pm_deferred_pr_dbg("Creating image\n");
 2114  
 2115  	drain_local_pages(NULL);
 2116  	nr_pages = count_data_pages();
 2117  	nr_highmem = count_highmem_pages();
 2118  	pm_deferred_pr_dbg("Need to copy %u pages\n", nr_pages + nr_highmem);
 2119  
 2120  	if (!enough_free_mem(nr_pages, nr_highmem)) {
 2121  		pm_deferred_pr_dbg("Not enough free memory for image creation\n");
 2122  		return -ENOMEM;
 2123  	}
 2124  
 2125  	if (swsusp_alloc(&copy_bm, nr_pages, nr_highmem))
 2126  		return -ENOMEM;
 2127  
 2128  	/*
 2129  	 * During allocating of suspend pagedir, new cold pages may appear.
 2130  	 * Kill them.
 2131  	 */
 2132  	drain_local_pages(NULL);
 2133  	nr_copy_pages = copy_data_pages(&copy_bm, &orig_bm, &zero_bm);
 2134  
 2135  	/*
 2136  	 * End of critical section. From now on, we can write to memory,
 2137  	 * but we should not touch disk. This specially means we must _not_
 2138  	 * touch swap space! Except we must write out our image of course.
 2139  	 */
 2140  	nr_pages += nr_highmem;
 2141  	/* We don't actually copy the zero pages */
 2142  	nr_zero_pages = nr_pages - nr_copy_pages;
 2143  	nr_meta_pages = DIV_ROUND_UP(nr_pages * sizeof(long), PAGE_SIZE);
 2144  
 2145  	pm_deferred_pr_dbg("Image created (%d pages copied, %d zero pages)\n",
 2146  			   nr_copy_pages, nr_zero_pages);
 2147  
 2148  	return 0;
 2149  }
```

`count_data_pages`（kernel/power/snapshot.c）：
```c
 1408  static unsigned int count_data_pages(void)  {
 1409  	struct zone *zone;
 1410  	unsigned long pfn, max_zone_pfn;
 1411  	unsigned int n = 0;
 1412  
 1413  	for_each_populated_zone(zone) {
 1414  		if (is_highmem(zone))
 1415  			continue;
 1416  
 1417  		mark_free_pages(zone);
 1418  		max_zone_pfn = zone_end_pfn(zone);
 1419  		for (pfn = zone->zone_start_pfn; pfn < max_zone_pfn; pfn++)
 1420  			if (saveable_page(zone, pfn))
 1421  				n++;
 1422  	}
 1423  	return n;
 1424  }
```

## E06

**规则**：执行上下文：在不能睡眠或不能插桩的地方，做了可能睡眠或会被插桩的事。

**原子上下文的来源**：公共代码在原子区间内调用本函数

**被标记的位置**：`arch/riscv/kernel/hibernate.c`中的`swsusp_arch_suspend`（sleep D:hook: line 155 flush_tlb_all -> on_each_cpu）

**调用链**：`flush_tlb_all`调用`on_each_cpu`

```c
  146  int swsusp_arch_suspend(void)  {
  147  	int ret = 0;
  148  
  149  	if (__cpu_suspend_enter(hibernate_cpu_context)) {
  150  		sleep_cpu = smp_processor_id();
  151  		suspend_save_csrs(hibernate_cpu_context);
  152  		ret = swsusp_save();
  153  	} else {
  154  		suspend_restore_csrs(hibernate_cpu_context);
  155  		flush_tlb_all();
  156  		flush_icache_all();
  157  
  158  		/*
  159  		 * Tell the hibernation core that we've just restored the memory.
  160  		 */
  161  		in_suspend = 0;
  162  		sleep_cpu = -EINVAL;
  163  	}
  164  
  165  	return ret;
  166  }
```

`flush_tlb_all`（arch/riscv/mm/tlbflush.c）：
```c
   72  void flush_tlb_all(void)  {
   73  	if (num_online_cpus() < 2)
   74  		local_flush_tlb_all();
   75  	else if (riscv_use_sbi_for_rfence())
   76  		sbi_remote_sfence_vma_asid(NULL, 0, FLUSH_TLB_MAX_SIZE, FLUSH_TLB_NO_ASID);
   77  	else
   78  		on_each_cpu(__ipi_flush_tlb_all, NULL, 1);
   79  }
```

## E07

**规则**：执行上下文：在不能睡眠或不能插桩的地方，做了可能睡眠或会被插桩的事。

**原子上下文的来源**：公共代码在原子区间内调用本函数

**被标记的位置**：`arch/riscv/kernel/hibernate.c`中的`swsusp_arch_suspend`（sleep D:hook: line 156 flush_icache_all -> on_each_cpu）

**调用链**：`flush_icache_all`调用`on_each_cpu`

```c
  146  int swsusp_arch_suspend(void)  {
  147  	int ret = 0;
  148  
  149  	if (__cpu_suspend_enter(hibernate_cpu_context)) {
  150  		sleep_cpu = smp_processor_id();
  151  		suspend_save_csrs(hibernate_cpu_context);
  152  		ret = swsusp_save();
  153  	} else {
  154  		suspend_restore_csrs(hibernate_cpu_context);
  155  		flush_tlb_all();
  156  		flush_icache_all();
  157  
  158  		/*
  159  		 * Tell the hibernation core that we've just restored the memory.
  160  		 */
  161  		in_suspend = 0;
  162  		sleep_cpu = -EINVAL;
  163  	}
  164  
  165  	return ret;
  166  }
```

`flush_icache_all`（arch/riscv/mm/cacheflush.c）：
```c
   22  void flush_icache_all(void)  {
   23  	local_flush_icache_all();
   24  
   25  	if (num_online_cpus() < 2)
   26  		return;
   27  
   28  	/*
   29  	 * Make sure all previous writes to the D$ are ordered before making
   30  	 * the IPI. The RISC-V spec states that a hart must execute a data fence
   31  	 * before triggering a remote fence.i in order to make the modification
   32  	 * visible for remote harts.
   33  	 *
   34  	 * IPIs on RISC-V are triggered by MMIO writes to either CLINT or
   35  	 * S-IMSIC, so the fence ensures previous data writes "happen before"
   36  	 * the MMIO.
   37  	 */
   38  	RISCV_FENCE(w, o);
   39  
   40  	if (riscv_use_sbi_for_rfence())
   41  		sbi_remote_fence_i(NULL);
   42  	else
   43  		on_each_cpu(ipi_remote_fence_i, NULL, 1);
   44  }
```

## E08

**规则**：执行上下文：在不能睡眠或不能插桩的地方，做了可能睡眠或会被插桩的事。

**原子上下文的来源**：不可插桩（noinstr）约定

**被标记的位置**：`arch/riscv/include/asm/stacktrace.h`中的`on_thread_stack`（noinstr N1: line 20 on_thread_stack -> called from noinstr/__cpuidle）

**调用链**：（直接）

```c
   20  static inline bool on_thread_stack(void)  {
   21  	return !(((unsigned long)(current->stack) ^ current_stack_pointer) & ~(THREAD_SIZE - 1));
   22  }
```

## E09

**规则**：执行上下文：在不能睡眠或不能插桩的地方，做了可能睡眠或会被插桩的事。

**原子上下文的来源**：不可插桩（noinstr）约定

**被标记的位置**：`arch/riscv/include/asm/vdso/processor.h`中的`cpu_relax`（noinstr N1: line 12 cpu_relax -> called from noinstr/__cpuidle）

**调用链**：（直接）

```c
   12  static inline void cpu_relax(void)  {
   13  #ifdef __riscv_muldiv
   14  	int dummy;
   15  	/* In lieu of a halt instruction, induce a long-latency stall. */
   16  	__asm__ __volatile__ ("div %0, %0, zero" : "=r" (dummy));
   17  #endif
   18  
   19  	/*
   20  	 * Reduce instruction retirement.
   21  	 * This assumes the PC changes.
   22  	 */
   23  	ALT_RISCV_PAUSE();
   24  	barrier();
   25  }
```

## E10

**规则**：执行上下文：在不能睡眠或不能插桩的地方，做了可能睡眠或会被插桩的事。

**原子上下文的来源**：不可插桩（noinstr）约定

**被标记的位置**：`arch/riscv/kernel/stacktrace.c`中的`arch_stack_walk`（noinstr N2: line 182 walk_stackframe -> instrumentable callee）

**调用链**：`walk_stackframe`调用``

```c
  181  noinline noinstr void arch_stack_walk(stack_trace_consume_fn consume_entry, void *cookie, 		     struct task_struct *task, struct pt_regs *regs)  {
  182  	walk_stackframe(task, regs, consume_entry, cookie);
  183  }
```

`walk_stackframe`（arch/riscv/kernel/stacktrace.c）：
```c
   50  void notrace walk_stackframe(struct task_struct *task, struct pt_regs *regs, 			     bool (*fn)(void *, unsigned long), void *arg)  {
   51  	unsigned long fp, sp, pc;
   52  	int graph_idx = 0;
   53  	int level = 0;
   54  
   55  	if (regs) {
   56  		fp = frame_pointer(regs);
   57  		sp = user_stack_pointer(regs);
   58  		pc = instruction_pointer(regs);
   59  	} else if (task == NULL || task == current) {
   60  		fp = (unsigned long)__builtin_frame_address(0);
   61  		sp = current_stack_pointer;
   62  		pc = (unsigned long)walk_stackframe;
   63  		level = -1;
   64  	} else {
   65  		/* task blocked in __switch_to */
   66  		fp = task->thread.s[0];
   67  		sp = task->thread.sp;
   68  		pc = task->thread.ra;
   69  	}
   70  
   71  	for (;;) {
   72  		struct stackframe *frame;
   73  
   74  		if (unlikely(!__kernel_text_address(pc) || (level++ >= 0 && !fn(arg, pc))))
   75  			break;
   76  
   77  		if (unlikely(!fp_is_valid(fp, sp)))
   78  			break;
   79  
   80  		/* Unwind stack frame */
   81  		frame = (struct stackframe *)fp - 1;
   82  		sp = fp;
   83  		if (regs && (regs->epc == pc) && fp_is_valid(frame->ra, sp)) {
   84  			/* We hit function where ra is not saved on the stack */
   85  			fp = frame->ra;
   86  			pc = regs->ra;
   87  		} else {
   88  			fp = READ_ONCE_TASK_STACK(task, frame->fp);
   89  			pc = READ_ONCE_TASK_STACK(task, frame->ra);
   90  			pc = ftrace_graph_ret_addr(task, &graph_idx, pc,
   91  						   &frame->ra);
   92  			if (pc >= (unsigned long)handle_exception &&
   93  			    pc < (unsigned long)&ret_from_exception_end) {
   94  				if (unlikely(!fn(arg, pc)))
   95  					break;
   96  
   97  				pc = ((struct pt_regs *)sp)->epc;
   98  				fp = ((struct pt_regs *)sp)->s0;
   99  			}
...
```

## E11

**规则**：执行上下文：在不能睡眠或不能插桩的地方，做了可能睡眠或会被插桩的事。

**原子上下文的来源**：不可插桩（noinstr）约定

**被标记的位置**：`arch/riscv/kernel/traps.c`中的`do_page_fault`（noinstr N2: line 415 handle_page_fault -> instrumentable callee）

**调用链**：`handle_page_fault`调用``

```c
  412  asmlinkage __visible noinstr void do_page_fault(struct pt_regs *regs)  {
  413  	irqentry_state_t state = irqentry_enter(regs);
  414  
  415  	handle_page_fault(regs);
  416  
  417  	local_irq_disable();
  418  
  419  	irqentry_exit(regs, state);
  420  }
```

`handle_page_fault`（arch/riscv/mm/fault.c）：
```c
  279  void handle_page_fault(struct pt_regs *regs)  {
  280  	struct task_struct *tsk;
  281  	struct vm_area_struct *vma;
  282  	struct mm_struct *mm;
  283  	unsigned long addr, cause;
  284  	unsigned int flags = FAULT_FLAG_DEFAULT;
  285  	int code = SEGV_MAPERR;
  286  	vm_fault_t fault;
  287  
  288  	cause = regs->cause;
  289  	addr = regs->badaddr;
  290  
  291  	tsk = current;
  292  	mm = tsk->mm;
  293  
  294  	if (kprobe_page_fault(regs, cause))
  295  		return;
  296  
  297  	if (user_mode(regs))
  298  		trace_page_fault_user(addr, regs, cause);
  299  	else
  300  		trace_page_fault_kernel(addr, regs, cause);
  301  
  302  	/*
  303  	 * Fault-in kernel-space virtual memory on-demand.
  304  	 * The 'reference' page table is init_mm.pgd.
  305  	 *
  306  	 * NOTE! We MUST NOT take any locks for this case. We may
  307  	 * be in an interrupt or a critical region, and should
  308  	 * only copy the information from the master page table,
  309  	 * nothing more.
  310  	 */
  311  	if ((!IS_ENABLED(CONFIG_MMU) || !IS_ENABLED(CONFIG_64BIT)) &&
  312  	    unlikely(addr >= VMALLOC_START && addr < VMALLOC_END)) {
  313  		vmalloc_fault(regs, code, addr);
  314  		return;
  315  	}
  316  
  317  	/* Enable interrupts if they were enabled in the parent context. */
  318  	if (!regs_irqs_disabled(regs))
  319  		local_irq_enable();
  320  
  321  	/*
  322  	 * If we're in an interrupt, have no user context, or are running
  323  	 * in an atomic region, then we must not take the fault.
  324  	 */
  325  	if (unlikely(faulthandler_disabled() || !mm)) {
  326  		tsk->thread.bad_cause = cause;
  327  		no_context(regs, addr);
  328  		return;
...
```

## E12

**规则**：执行上下文：在不能睡眠或不能插桩的地方，做了可能睡眠或会被插桩的事。

**原子上下文的来源**：不可插桩（noinstr）约定

**被标记的位置**：`arch/riscv/kernel/traps.c`中的`handle_riscv_irq`（noinstr N2: line 427 irq_enter_rcu -> instrumentable callee）

**调用链**：`irq_enter_rcu`调用``

```c
  424  static void noinstr handle_riscv_irq(struct pt_regs *regs)  {
  425  	struct pt_regs *old_regs;
  426  
  427  	irq_enter_rcu();
  428  	old_regs = set_irq_regs(regs);
  429  	handle_arch_irq(regs);
  430  	set_irq_regs(old_regs);
  431  	irq_exit_rcu();
  432  }
```

`irq_enter_rcu`（kernel/softirq.c）：
```c
  686  void irq_enter_rcu(void)  {
  687  	__irq_enter_raw();
  688  
  689  	/*
  690  	 * If this is a nested interrupt that hits the exit_to_user_mode_loop
  691  	 * where it has enabled interrupts but before it has hit schedule() we
  692  	 * could have hrtimers in an undefined state. Fix it up here.
  693  	 */
  694  	hrtimer_rearm_deferred();
  695  
  696  	if (tick_nohz_full_cpu(smp_processor_id()) ||
  697  	    (is_idle_task(current) && (irq_count() == HARDIRQ_OFFSET)))
  698  		tick_irq_enter();
  699  
  700  	account_hardirq_enter(current);
  701  }
```

## E13

**规则**：执行上下文：在不能睡眠或不能插桩的地方，做了可能睡眠或会被插桩的事。

**原子上下文的来源**：不可插桩（noinstr）约定

**被标记的位置**：`arch/riscv/kernel/traps.c`中的`handle_riscv_irq`（noinstr N2: line 431 irq_exit_rcu -> instrumentable callee）

**调用链**：`irq_exit_rcu`调用``

```c
  424  static void noinstr handle_riscv_irq(struct pt_regs *regs)  {
  425  	struct pt_regs *old_regs;
  426  
  427  	irq_enter_rcu();
  428  	old_regs = set_irq_regs(regs);
  429  	handle_arch_irq(regs);
  430  	set_irq_regs(old_regs);
  431  	irq_exit_rcu();
  432  }
```

`irq_exit_rcu`（kernel/softirq.c）：
```c
  774  void irq_exit_rcu(void)  {
  775  	__irq_exit_rcu();
  776  	 /* must be last! */
  777  	lockdep_hardirq_exit();
  778  }
```

## E14

**规则**：推测执行越界（Spectre-v1）：检查过上界的、可能来自客体或用户的下标，没有用array_index_nospec就访问数组。

**被标记的位置**：`arch/riscv/kvm/vcpu_pmu.c`中的`pmu_fw_ctr_read_hi`（line 240: [fevent_code] after bound check at line 236, no array_index_nospec）

**调用链**：（直接）

```c
  211  static int pmu_fw_ctr_read_hi(struct kvm_vcpu *vcpu, unsigned long cidx, 			      unsigned long *out_val)  {
  212  	struct kvm_pmu *kvpmu = vcpu_to_pmu(vcpu);
  213  	struct kvm_pmc *pmc;
  214  	int fevent_code;
  215  
  216  	if (!IS_ENABLED(CONFIG_32BIT)) {
  217  		pr_warn("%s: should be invoked for only RV32\n", __func__);
  218  		return -EINVAL;
  219  	}
  220  
  221  	if (cidx >= kvm_pmu_num_counters(kvpmu) || cidx == 1) {
  222  		pr_warn("Invalid counter id [%ld]during read\n", cidx);
  223  		return -EINVAL;
  224  	}
  225  
  226  	cidx = array_index_nospec(cidx, RISCV_KVM_MAX_COUNTERS);
  227  	pmc = &kvpmu->pmc[cidx];
  228  
  229  	if (pmc->cinfo.type != SBI_PMU_CTR_TYPE_FW)
  230  		return -EINVAL;
  231  
  232  	if (pmc->event_idx == SBI_PMU_EVENT_IDX_INVALID)
  233  		return -EINVAL;
  234  
  235  	fevent_code = get_event_code(pmc->event_idx);
  236  	if (WARN_ONCE(fevent_code >= SBI_PMU_FW_MAX,
  237  	    "Invalid firmware event code: %d\n", fevent_code))
  238  		return -EINVAL;
  239  
  240  	pmc->counter_val = kvpmu->fw_event[fevent_code].value;
  241  
  242  	*out_val = pmc->counter_val >> 32;
  243  
  244  	return 0;
  245  }
```

## E15

**规则**：推测执行越界（Spectre-v1）：检查过上界的、可能来自客体或用户的下标，没有用array_index_nospec就访问数组。

**被标记的位置**：`arch/riscv/kvm/vcpu_pmu.c`中的`pmu_ctr_read`（line 272: [fevent_code] after bound check at line 268, no array_index_nospec）

**调用链**：（直接）

```c
  249  static int pmu_ctr_read(struct kvm_vcpu *vcpu, unsigned long cidx, 			unsigned long *out_val)  {
  250  	struct kvm_pmu *kvpmu = vcpu_to_pmu(vcpu);
  251  	struct kvm_pmc *pmc;
  252  	u64 enabled, running;
  253  	int fevent_code;
  254  
  255  	if (cidx >= kvm_pmu_num_counters(kvpmu) || cidx == 1) {
  256  		pr_warn("Invalid counter id [%ld] during read\n", cidx);
  257  		return -EINVAL;
  258  	}
  259  
  260  	cidx = array_index_nospec(cidx, RISCV_KVM_MAX_COUNTERS);
  261  	pmc = &kvpmu->pmc[cidx];
  262  
  263  	if (pmc->cinfo.type == SBI_PMU_CTR_TYPE_FW) {
  264  		if (pmc->event_idx == SBI_PMU_EVENT_IDX_INVALID)
  265  			return -EINVAL;
  266  
  267  		fevent_code = get_event_code(pmc->event_idx);
  268  		if (WARN_ONCE(fevent_code >= SBI_PMU_FW_MAX,
  269  		    "Invalid firmware event code: %d\n", fevent_code))
  270  			return -EINVAL;
  271  
  272  		pmc->counter_val = kvpmu->fw_event[fevent_code].value;
  273  	} else if (pmc->perf_event) {
  274  		pmc->counter_val += perf_event_read_value(pmc->perf_event, &enabled, &running);
  275  	} else {
  276  		return -EINVAL;
  277  	}
  278  	*out_val = pmc->counter_val;
  279  
  280  	return 0;
  281  }
```

## E16

**规则**：推测执行越界（Spectre-v1）：检查过上界的、可能来自客体或用户的下标，没有用array_index_nospec就访问数组。

**被标记的位置**：`arch/riscv/kvm/vcpu_pmu.c`中的`kvm_riscv_vcpu_pmu_incr_fw`（line 376: [fid] after bound check at line 373, no array_index_nospec）

**调用链**：（直接）

```c
  369  int kvm_riscv_vcpu_pmu_incr_fw(struct kvm_vcpu *vcpu, unsigned long fid)  {
  370  	struct kvm_pmu *kvpmu = vcpu_to_pmu(vcpu);
  371  	struct kvm_fw_event *fevent;
  372  
  373  	if (!kvpmu || fid >= SBI_PMU_FW_MAX)
  374  		return -EINVAL;
  375  
  376  	fevent = &kvpmu->fw_event[fid];
  377  	if (fevent->started)
  378  		fevent->value++;
  379  
  380  	return 0;
  381  }
```

## E17

**规则**：推测执行越界（Spectre-v1）：检查过上界的、可能来自客体或用户的下标，没有用array_index_nospec就访问数组。

**被标记的位置**：`arch/riscv/kvm/vcpu_pmu.c`中的`kvm_riscv_vcpu_pmu_ctr_start`（line 616: [fevent_code] after bound check at line 610, no array_index_nospec; line 621: [fevent_code] after bound check at line 610, no array_index_nospec; line）

**调用链**：（直接）

```c
  568  int kvm_riscv_vcpu_pmu_ctr_start(struct kvm_vcpu *vcpu, unsigned long ctr_base, 				 unsigned long ctr_mask, unsigned long flags, u64 ival, 				 struct kvm_vcpu_sbi_return *retdata)  {
  569  	struct kvm_pmu *kvpmu = vcpu_to_pmu(vcpu);
  570  	int i, pmc_index, sbiret = 0;
  571  	struct kvm_pmc *pmc;
  572  	int fevent_code;
  573  	bool snap_flag_set = flags & SBI_PMU_START_FLAG_INIT_SNAPSHOT;
  574  
  575  	if (kvm_pmu_validate_counter_mask(kvpmu, ctr_base, ctr_mask) < 0) {
  576  		sbiret = SBI_ERR_INVALID_PARAM;
  577  		goto out;
  578  	}
  579  
  580  	if (snap_flag_set) {
  581  		if (kvpmu->snapshot_addr == INVALID_GPA) {
  582  			sbiret = SBI_ERR_NO_SHMEM;
  583  			goto out;
  584  		}
  585  		if (kvm_vcpu_read_guest(vcpu, kvpmu->snapshot_addr, kvpmu->sdata,
  586  					sizeof(struct riscv_pmu_snapshot_data))) {
  587  			pr_warn("Unable to read snapshot shared memory while starting counters\n");
  588  			sbiret = SBI_ERR_FAILURE;
  589  			goto out;
  590  		}
  591  	}
  592  	/* Start the counters that have been configured and requested by the guest */
  593  	for_each_set_bit(i, &ctr_mask, BITS_PER_LONG) {
  594  		pmc_index = array_index_nospec(i + ctr_base,
  595  					       RISCV_KVM_MAX_COUNTERS);
  596  		if (!test_bit(pmc_index, kvpmu->pmc_in_use))
  597  			continue;
  598  		/* The guest started the counter again. Reset the overflow status */
  599  		clear_bit(pmc_index, kvpmu->pmc_overflown);
  600  		pmc = &kvpmu->pmc[pmc_index];
  601  		if (flags & SBI_PMU_START_FLAG_SET_INIT_VALUE) {
  602  			pmc->counter_val = ival;
  603  		} else if (snap_flag_set) {
  604  			/* The counter index in the snapshot are relative to the counter base */
  605  			pmc->counter_val = kvpmu->sdata->ctr_values[i];
  606  		}
  607  
  608  		if (pmc->cinfo.type == SBI_PMU_CTR_TYPE_FW) {
  609  			fevent_code = get_event_code(pmc->event_idx);
  610  			if (fevent_code >= SBI_PMU_FW_MAX) {
  611  				sbiret = SBI_ERR_INVALID_PARAM;
  612  				goto out;
  613  			}
  614  
  615  			/* Check if the counter was already started for some reason */
  616  			if (kvpmu->fw_event[fevent_code].started) {
  617  				sbiret = SBI_ERR_ALREADY_STARTED;
  618  				continue;
  619  			}
  620  
  621  			kvpmu->fw_event[fevent_code].started = true;
  622  			kvpmu->fw_event[fevent_code].value = pmc->counter_val;
  623  		} else if (pmc->perf_event) {
  624  			if (unlikely(pmc->started)) {
  625  				sbiret = SBI_ERR_ALREADY_STARTED;
  626  				continue;
  627  			}
  628  			perf_event_period(pmc->perf_event, kvm_pmu_get_sample_period(pmc));
  629  			perf_event_enable(pmc->perf_event);
  630  			pmc->started = true;
  631  		} else {
  632  			sbiret = SBI_ERR_INVALID_PARAM;
  633  		}
  634  	}
  635  
  636  out:
  637  	retdata->err_val = sbiret;
...
```

## E18

**规则**：推测执行越界（Spectre-v1）：检查过上界的、可能来自客体或用户的下标，没有用array_index_nospec就访问数组。

**被标记的位置**：`arch/riscv/kvm/vcpu_pmu.c`中的`kvm_riscv_vcpu_pmu_ctr_stop`（line 678: [fevent_code] after bound check at line 673, no array_index_nospec; line 681: [fevent_code] after bound check at line 673, no array_index_nospec; line）

**调用链**：（直接）

```c
  645  int kvm_riscv_vcpu_pmu_ctr_stop(struct kvm_vcpu *vcpu, unsigned long ctr_base, 				unsigned long ctr_mask, unsigned long flags, 				struct kvm_vcpu_sbi_return *retdata)  {
  646  	struct kvm_pmu *kvpmu = vcpu_to_pmu(vcpu);
  647  	int i, pmc_index, sbiret = 0;
  648  	u64 enabled, running;
  649  	struct kvm_pmc *pmc;
  650  	int fevent_code;
  651  	bool snap_flag_set = flags & SBI_PMU_STOP_FLAG_TAKE_SNAPSHOT;
  652  	bool shmem_needs_update = false;
  653  
  654  	if (kvm_pmu_validate_counter_mask(kvpmu, ctr_base, ctr_mask) < 0) {
  655  		sbiret = SBI_ERR_INVALID_PARAM;
  656  		goto out;
  657  	}
  658  
  659  	if (snap_flag_set && kvpmu->snapshot_addr == INVALID_GPA) {
  660  		sbiret = SBI_ERR_NO_SHMEM;
  661  		goto out;
  662  	}
  663  
  664  	/* Stop the counters that have been configured and requested by the guest */
  665  	for_each_set_bit(i, &ctr_mask, BITS_PER_LONG) {
  666  		pmc_index = array_index_nospec(i + ctr_base,
  667  					       RISCV_KVM_MAX_COUNTERS);
  668  		if (!test_bit(pmc_index, kvpmu->pmc_in_use))
  669  			continue;
  670  		pmc = &kvpmu->pmc[pmc_index];
  671  		if (pmc->cinfo.type == SBI_PMU_CTR_TYPE_FW) {
  672  			fevent_code = get_event_code(pmc->event_idx);
  673  			if (fevent_code >= SBI_PMU_FW_MAX) {
  674  				sbiret = SBI_ERR_INVALID_PARAM;
  675  				goto out;
  676  			}
  677  
  678  			if (!kvpmu->fw_event[fevent_code].started)
  679  				sbiret = SBI_ERR_ALREADY_STOPPED;
  680  
  681  			kvpmu->fw_event[fevent_code].started = false;
  682  		} else if (pmc->perf_event) {
  683  			if (pmc->started) {
  684  				/* Stop counting the counter */
  685  				perf_event_disable(pmc->perf_event);
  686  				pmc->started = false;
  687  			} else {
  688  				sbiret = SBI_ERR_ALREADY_STOPPED;
  689  			}
  690  
  691  			if (flags & SBI_PMU_STOP_FLAG_RESET)
  692  				/* Release the counter if this is a reset request */
  693  				kvm_pmu_release_perf_event(pmc);
  694  		} else {
  695  			sbiret = SBI_ERR_INVALID_PARAM;
  696  		}
  697  
  698  		if (snap_flag_set && !sbiret) {
  699  			if (pmc->cinfo.type == SBI_PMU_CTR_TYPE_FW)
  700  				pmc->counter_val = kvpmu->fw_event[fevent_code].value;
  701  			else if (pmc->perf_event)
  702  				pmc->counter_val += perf_event_read_value(pmc->perf_event,
  703  									  &enabled, &running);
  704  			/*
  705  			 * The counter and overflow indices in the snapshot region are w.r.to
  706  			 * cbase. Modify the set bit in the counter mask instead of the pmc_index
  707  			 * which indicates the absolute counter index.
  708  			 */
  709  			if (test_bit(pmc_index, kvpmu->pmc_overflown))
  710  				kvpmu->sdata->ctr_overflow_mask |= BIT(i);
  711  			kvpmu->sdata->ctr_values[i] = pmc->counter_val;
  712  			shmem_needs_update = true;
  713  		}
  714  
...
```

## E19

**规则**：推测执行越界（Spectre-v1）：检查过上界的、可能来自客体或用户的下标，没有用array_index_nospec就访问数组。

**被标记的位置**：`arch/riscv/kvm/vcpu_pmu.c`中的`kvm_riscv_vcpu_pmu_ctr_cfg_match`（line 804: [event_code] after bound check at line 775, no array_index_nospec）

**调用链**：（直接）

```c
  744  int kvm_riscv_vcpu_pmu_ctr_cfg_match(struct kvm_vcpu *vcpu, unsigned long ctr_base, 				     unsigned long ctr_mask, unsigned long flags, 				     unsigned long eidx, u64 evtdata, 				     struct kvm_vcpu_sbi_return *retdata)  {
  745  	int ctr_idx, sbiret = 0;
  746  	long ret;
  747  	bool is_fevent;
  748  	unsigned long event_code;
  749  	u32 etype = kvm_pmu_get_perf_event_type(eidx);
  750  	struct kvm_pmu *kvpmu = vcpu_to_pmu(vcpu);
  751  	struct kvm_pmc *pmc = NULL;
  752  	struct perf_event_attr attr = {
  753  		.type = etype,
  754  		.size = sizeof(struct perf_event_attr),
  755  		.pinned = true,
  756  		.disabled = true,
  757  		/*
  758  		 * It should never reach here if the platform doesn't support the sscofpmf
  759  		 * extension as mode filtering won't work without it.
  760  		 */
  761  		.exclude_host = true,
  762  		.exclude_hv = true,
  763  		.exclude_user = !!(flags & SBI_PMU_CFG_FLAG_SET_UINH),
  764  		.exclude_kernel = !!(flags & SBI_PMU_CFG_FLAG_SET_SINH),
  765  		.config1 = RISCV_PMU_CONFIG1_GUEST_EVENTS,
  766  	};
  767  
  768  	if (kvm_pmu_validate_counter_mask(kvpmu, ctr_base, ctr_mask) < 0) {
  769  		sbiret = SBI_ERR_INVALID_PARAM;
  770  		goto out;
  771  	}
  772  
  773  	event_code = get_event_code(eidx);
  774  	is_fevent = kvm_pmu_is_fw_event(eidx);
  775  	if (is_fevent && event_code >= SBI_PMU_FW_MAX) {
  776  		sbiret = SBI_ERR_NOT_SUPPORTED;
  777  		goto out;
  778  	}
  779  
  780  	/*
  781  	 * SKIP_MATCH flag indicates the caller is aware of the assigned counter
  782  	 * for this event. Just do a sanity check if it already marked used.
  783  	 */
  784  	if (flags & SBI_PMU_CFG_FLAG_SKIP_MATCH) {
  785  		if (!test_bit(ctr_base + __ffs(ctr_mask), kvpmu->pmc_in_use)) {
  786  			sbiret = SBI_ERR_FAILURE;
  787  			goto out;
  788  		}
  789  		ctr_idx = ctr_base + __ffs(ctr_mask);
  790  	} else  {
  791  		ctr_idx = pmu_get_pmc_index(kvpmu, eidx, ctr_base, ctr_mask);
  792  		if (ctr_idx < 0) {
  793  			sbiret = SBI_ERR_NOT_SUPPORTED;
  794  			goto out;
  795  		}
  796  	}
  797  
  798  	ctr_idx = array_index_nospec(ctr_idx, RISCV_KVM_MAX_COUNTERS);
  799  	pmc = &kvpmu->pmc[ctr_idx];
  800  	pmc->idx = ctr_idx;
  801  
  802  	if (is_fevent) {
  803  		if (flags & SBI_PMU_CFG_FLAG_AUTO_START)
  804  			kvpmu->fw_event[event_code].started = true;
  805  	} else {
  806  		ret = kvm_pmu_create_perf_event(pmc, &attr, flags, eidx, evtdata);
  807  		if (ret) {
  808  			sbiret = SBI_ERR_NOT_SUPPORTED;
  809  			goto out;
  810  		}
  811  	}
  812  
  813  	set_bit(ctr_idx, kvpmu->pmc_in_use);
...
```

## E20

**规则**：同一约定：arm64、x86、LoongArch三个实现都调用了某个函数，RISC-V的实现没有。

**被标记的位置**：`arch/riscv/kernel/cacheinfo.c`中的`init_cache_level`（all three references call ['get_cpu_cacheinfo'], riscv does not）

**调用链**：（直接）

```c
   75  int init_cache_level(unsigned int cpu)  {
   76  	return init_of_cache_level(cpu);
   77  }
```

## E21

**规则**：同一约定：arm64、x86、LoongArch三个实现都调用了某个函数，RISC-V的实现没有。

**被标记的位置**：`arch/riscv/mm/init.c`中的`vmemmap_populate`（all three references call ['vmemmap_populate_basepages'], riscv does not）

**调用链**：（直接）

```c
 1372  int __meminit vmemmap_populate(unsigned long start, unsigned long end, int node, 			       struct vmem_altmap *altmap)  {
 1373  	WARN_ON((start < VMEMMAP_START) || (end > VMEMMAP_END));
 1374  
 1375  	/*
 1376  	 * Note that SPARSEMEM_VMEMMAP is only selected for rv64 and that we
 1377  	 * can't use hugepage mappings for 2-level page table because in case of
 1378  	 * memory hotplug, we are not able to update all the page tables with
 1379  	 * the new PMDs.
 1380  	 */
 1381  	return vmemmap_populate_hugepages(start, end, node, altmap);
 1382  }
```
