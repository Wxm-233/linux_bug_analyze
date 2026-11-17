# 待复核的标记（Linux v6.12，RISC-V）

## K00

**问题种类**：可能睡眠

**为什么认为这里不能睡眠/需要不可插桩**：本函数自己的关中断区间内

**被标记的函数**：`arch/riscv/kernel/machine_kexec.c`中的`machine_shutdown`，第113行调用`smp_shutdown_nonboot_cpus`，最终到达`smp_shutdown_nonboot_cpus`

**调用链**：
（直接调用）

**代码**：

```c
  105  void machine_shutdown(void)  {
  106  	/*
  107  	 * No more interrupts on this hart
  108  	 * until we are back up.
  109  	 */
  110  	local_irq_disable();
  111  
  112  #if defined(CONFIG_HOTPLUG_CPU)
  113  	smp_shutdown_nonboot_cpus(smp_processor_id());
  114  #endif
  115  }
```

## K01

**问题种类**：可能睡眠

**为什么认为这里不能睡眠/需要不可插桩**：本函数持有自旋锁的区间内

**被标记的函数**：`arch/riscv/kernel/traps.c`中的`die`，第86行调用`bust_spinlocks`，最终到达`might_sleep`

**调用链**：
- `bust_spinlocks`（lib/bust_spinlocks.c第25行调用`console_unblank`）
- `console_unblank`（kernel/printk/printk.c第3345行调用`console_lock`）
- `console_lock`（kernel/printk/printk.c第2802行调用`might_sleep`）

**代码**：

```c
   76  void die(struct pt_regs *regs, const char *str)  {
   77  	static int die_counter;
   78  	int ret;
   79  	long cause;
   80  	unsigned long flags;
   81  
   82  	oops_enter();
   83  
   84  	spin_lock_irqsave(&die_lock, flags);
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
  103  	spin_unlock_irqrestore(&die_lock, flags);
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
 3302  void console_unblank(void)  {
 3303  	bool found_unblank = false;
 3304  	struct console *c;
 3305  	int cookie;
 3306  
 3307  	/*
 3308  	 * First check if there are any consoles implementing the unblank()
 3309  	 * callback. If not, there is no reason to continue and take the
 3310  	 * console lock, which in particular can be dangerous if
 3311  	 * @oops_in_progress is set.
 3312  	 */
 3313  	cookie = console_srcu_read_lock();
 3314  	for_each_console_srcu(c) {
 3315  		if ((console_srcu_read_flags(c) & CON_ENABLED) && c->unblank) {
 3316  			found_unblank = true;
 3317  			break;
 3318  		}
 3319  	}
 3320  	console_srcu_read_unlock(cookie);
 3321  	if (!found_unblank)
 3322  		return;
 3323  
 3324  	/*
 3325  	 * Stop console printing because the unblank() callback may
 3326  	 * assume the console is not within its write() callback.
 3327  	 *
 3328  	 * If @oops_in_progress is set, this may be an atomic context.
 3329  	 * In that case, attempt a trylock as best-effort.
 3330  	 */
 3331  	if (oops_in_progress) {
 3332  		/* Semaphores are not NMI-safe. */
 3333  		if (in_nmi())
 3334  			return;
 3335  
 3336  		/*
 3337  		 * Attempting to trylock the console lock can deadlock
 3338  		 * if another CPU was stopped while modifying the
 3339  		 * semaphore. "Hope and pray" that this is not the
 3340  		 * current situation.
 3341  		 */
 3342  		if (down_trylock_console_sem() != 0)
 3343  			return;
 3344  	} else
 3345  		console_lock();
 3346  
 3347  	console_locked = 1;
 3348  	console_may_schedule = 0;
 3349  
 3350  	cookie = console_srcu_read_lock();
 3351  	for_each_console_srcu(c) {
 3352  		if ((console_srcu_read_flags(c) & CON_ENABLED) && c->unblank)
 3353  			c->unblank();
 3354  	}
 3355  	console_srcu_read_unlock(cookie);
 3356  
 3357  	console_unlock();
 3358  
 3359  	if (!oops_in_progress)
 3360  		pr_flush(1000, true);
 3361  }
```

`console_lock`（kernel/printk/printk.c）：

```c
 2801  void console_lock(void)  {
 2802  	might_sleep();
 2803  
 2804  	/* On panic, the console_lock must be left to the panic cpu. */
 2805  	while (other_cpu_in_panic())
 2806  		msleep(1000);
 2807  
 2808  	down_console_sem();
 2809  	console_locked = 1;
 2810  	console_may_schedule = 1;
 2811  }
```

## K02

**问题种类**：可能睡眠

**为什么认为这里不能睡眠/需要不可插桩**：本函数持有自旋锁的区间内

**被标记的函数**：`arch/riscv/kernel/traps.c`中的`die`，第101行调用`bust_spinlocks`，最终到达`might_sleep`

**调用链**：
- `bust_spinlocks`（lib/bust_spinlocks.c第25行调用`console_unblank`）
- `console_unblank`（kernel/printk/printk.c第3345行调用`console_lock`）
- `console_lock`（kernel/printk/printk.c第2802行调用`might_sleep`）

**代码**：

```c
   76  void die(struct pt_regs *regs, const char *str)  {
   77  	static int die_counter;
   78  	int ret;
   79  	long cause;
   80  	unsigned long flags;
   81  
   82  	oops_enter();
   83  
   84  	spin_lock_irqsave(&die_lock, flags);
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
  103  	spin_unlock_irqrestore(&die_lock, flags);
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
 3302  void console_unblank(void)  {
 3303  	bool found_unblank = false;
 3304  	struct console *c;
 3305  	int cookie;
 3306  
 3307  	/*
 3308  	 * First check if there are any consoles implementing the unblank()
 3309  	 * callback. If not, there is no reason to continue and take the
 3310  	 * console lock, which in particular can be dangerous if
 3311  	 * @oops_in_progress is set.
 3312  	 */
 3313  	cookie = console_srcu_read_lock();
 3314  	for_each_console_srcu(c) {
 3315  		if ((console_srcu_read_flags(c) & CON_ENABLED) && c->unblank) {
 3316  			found_unblank = true;
 3317  			break;
 3318  		}
 3319  	}
 3320  	console_srcu_read_unlock(cookie);
 3321  	if (!found_unblank)
 3322  		return;
 3323  
 3324  	/*
 3325  	 * Stop console printing because the unblank() callback may
 3326  	 * assume the console is not within its write() callback.
 3327  	 *
 3328  	 * If @oops_in_progress is set, this may be an atomic context.
 3329  	 * In that case, attempt a trylock as best-effort.
 3330  	 */
 3331  	if (oops_in_progress) {
 3332  		/* Semaphores are not NMI-safe. */
 3333  		if (in_nmi())
 3334  			return;
 3335  
 3336  		/*
 3337  		 * Attempting to trylock the console lock can deadlock
 3338  		 * if another CPU was stopped while modifying the
 3339  		 * semaphore. "Hope and pray" that this is not the
 3340  		 * current situation.
 3341  		 */
 3342  		if (down_trylock_console_sem() != 0)
 3343  			return;
 3344  	} else
 3345  		console_lock();
 3346  
 3347  	console_locked = 1;
 3348  	console_may_schedule = 0;
 3349  
 3350  	cookie = console_srcu_read_lock();
 3351  	for_each_console_srcu(c) {
 3352  		if ((console_srcu_read_flags(c) & CON_ENABLED) && c->unblank)
 3353  			c->unblank();
 3354  	}
 3355  	console_srcu_read_unlock(cookie);
 3356  
 3357  	console_unlock();
 3358  
 3359  	if (!oops_in_progress)
 3360  		pr_flush(1000, true);
 3361  }
```

`console_lock`（kernel/printk/printk.c）：

```c
 2801  void console_lock(void)  {
 2802  	might_sleep();
 2803  
 2804  	/* On panic, the console_lock must be left to the panic cpu. */
 2805  	while (other_cpu_in_panic())
 2806  		msleep(1000);
 2807  
 2808  	down_console_sem();
 2809  	console_locked = 1;
 2810  	console_may_schedule = 1;
 2811  }
```

## K03

**问题种类**：在PREEMPT_RT下会睡眠的普通自旋锁

**为什么认为这里不能睡眠/需要不可插桩**：本函数自己的关中断区间内

**被标记的函数**：`arch/riscv/kernel/traps.c`中的`do_trap_insn_illegal`，第184行调用`do_trap_error`，最终到达`spin_lock_irqsave`

**调用链**：
- `do_trap_error`（arch/riscv/kernel/traps.c第140行调用`die`）
- `die`（arch/riscv/kernel/traps.c第84行调用`spin_lock_irqsave`）

**代码**：

```c
  171  asmlinkage __visible __trap_section void do_trap_insn_illegal(struct pt_regs *regs)  {
  172  	bool handled;
  173  
  174  	if (user_mode(regs)) {
  175  		irqentry_enter_from_user_mode(regs);
  176  
  177  		local_irq_enable();
  178  
  179  		handled = riscv_v_first_use_handler(regs);
  180  
  181  		local_irq_disable();
  182  
  183  		if (!handled)
  184  			do_trap_error(regs, SIGILL, ILL_ILLOPC, regs->epc,
  185  				      "Oops - illegal instruction");
  186  
  187  		irqentry_exit_to_user_mode(regs);
  188  	} else {
  189  		irqentry_state_t state = irqentry_nmi_enter(regs);
  190  
  191  		do_trap_error(regs, SIGILL, ILL_ILLOPC, regs->epc,
  192  			      "Oops - illegal instruction");
  193  
  194  		irqentry_nmi_exit(regs, state);
  195  	}
  196  }
```

`do_trap_error`（arch/riscv/kernel/traps.c）：

```c
  133  static void do_trap_error(struct pt_regs *regs, int signo, int code, 	unsigned long addr, const char *str)  {
  134  	current->thread.bad_cause = regs->cause;
  135  
  136  	if (user_mode(regs)) {
  137  		do_trap(regs, signo, code, addr);
  138  	} else {
  139  		if (!fixup_exception(regs))
  140  			die(regs, str);
  141  	}
  142  }
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
   84  	spin_lock_irqsave(&die_lock, flags);
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
  103  	spin_unlock_irqrestore(&die_lock, flags);
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

## K04

**问题种类**：在PREEMPT_RT下会睡眠的普通自旋锁

**为什么认为这里不能睡眠/需要不可插桩**：本函数自己的关中断区间内

**被标记的函数**：`arch/riscv/kernel/traps.c`中的`do_trap_insn_illegal`，第191行调用`do_trap_error`，最终到达`spin_lock_irqsave`

**调用链**：
- `do_trap_error`（arch/riscv/kernel/traps.c第140行调用`die`）
- `die`（arch/riscv/kernel/traps.c第84行调用`spin_lock_irqsave`）

**代码**：

```c
  171  asmlinkage __visible __trap_section void do_trap_insn_illegal(struct pt_regs *regs)  {
  172  	bool handled;
  173  
  174  	if (user_mode(regs)) {
  175  		irqentry_enter_from_user_mode(regs);
  176  
  177  		local_irq_enable();
  178  
  179  		handled = riscv_v_first_use_handler(regs);
  180  
  181  		local_irq_disable();
  182  
  183  		if (!handled)
  184  			do_trap_error(regs, SIGILL, ILL_ILLOPC, regs->epc,
  185  				      "Oops - illegal instruction");
  186  
  187  		irqentry_exit_to_user_mode(regs);
  188  	} else {
  189  		irqentry_state_t state = irqentry_nmi_enter(regs);
  190  
  191  		do_trap_error(regs, SIGILL, ILL_ILLOPC, regs->epc,
  192  			      "Oops - illegal instruction");
  193  
  194  		irqentry_nmi_exit(regs, state);
  195  	}
  196  }
```

`do_trap_error`（arch/riscv/kernel/traps.c）：

```c
  133  static void do_trap_error(struct pt_regs *regs, int signo, int code, 	unsigned long addr, const char *str)  {
  134  	current->thread.bad_cause = regs->cause;
  135  
  136  	if (user_mode(regs)) {
  137  		do_trap(regs, signo, code, addr);
  138  	} else {
  139  		if (!fixup_exception(regs))
  140  			die(regs, str);
  141  	}
  142  }
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
   84  	spin_lock_irqsave(&die_lock, flags);
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
  103  	spin_unlock_irqrestore(&die_lock, flags);
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

## K05

**问题种类**：在PREEMPT_RT下会睡眠的普通自旋锁

**为什么认为这里不能睡眠/需要不可插桩**：陷入处理函数开头到开中断之前（RISC-V进入陷入处理时中断是关着的）

**被标记的函数**：`arch/riscv/kernel/traps.c`中的`do_page_fault`，第362行调用`handle_page_fault`，最终到达`spin_lock_irqsave`

**调用链**：
- `handle_page_fault`（arch/riscv/mm/fault.c第278行调用`die_kernel_fault`）
- `die_kernel_fault`（arch/riscv/mm/fault.c第34行调用`die`）
- `die`（arch/riscv/kernel/traps.c第84行调用`spin_lock_irqsave`）

**代码**：

```c
  359  asmlinkage __visible noinstr void do_page_fault(struct pt_regs *regs)  {
  360  	irqentry_state_t state = irqentry_enter(regs);
  361  
  362  	handle_page_fault(regs);
  363  
  364  	local_irq_disable();
  365  
  366  	irqentry_exit(regs, state);
  367  }
```

`handle_page_fault`（arch/riscv/mm/fault.c）：

```c
  224  void handle_page_fault(struct pt_regs *regs)  {
  225  	struct task_struct *tsk;
  226  	struct vm_area_struct *vma;
  227  	struct mm_struct *mm;
  228  	unsigned long addr, cause;
  229  	unsigned int flags = FAULT_FLAG_DEFAULT;
  230  	int code = SEGV_MAPERR;
  231  	vm_fault_t fault;
  232  
  233  	cause = regs->cause;
  234  	addr = regs->badaddr;
  235  
  236  	tsk = current;
  237  	mm = tsk->mm;
  238  
  239  	if (kprobe_page_fault(regs, cause))
  240  		return;
  241  
  242  	/*
  243  	 * Fault-in kernel-space virtual memory on-demand.
  244  	 * The 'reference' page table is init_mm.pgd.
  245  	 *
  246  	 * NOTE! We MUST NOT take any locks for this case. We may
  247  	 * be in an interrupt or a critical region, and should
  248  	 * only copy the information from the master page table,
  249  	 * nothing more.
  250  	 */
  251  	if ((!IS_ENABLED(CONFIG_MMU) || !IS_ENABLED(CONFIG_64BIT)) &&
  252  	    unlikely(addr >= VMALLOC_START && addr < VMALLOC_END)) {
  253  		vmalloc_fault(regs, code, addr);
  254  		return;
  255  	}
  256  
  257  	/* Enable interrupts if they were enabled in the parent context. */
  258  	if (!regs_irqs_disabled(regs))
  259  		local_irq_enable();
  260  
  261  	/*
  262  	 * If we're in an interrupt, have no user context, or are running
  263  	 * in an atomic region, then we must not take the fault.
  264  	 */
  265  	if (unlikely(faulthandler_disabled() || !mm)) {
  266  		tsk->thread.bad_cause = cause;
  267  		no_context(regs, addr);
  268  		return;
  269  	}
  270  
  271  	if (user_mode(regs))
  272  		flags |= FAULT_FLAG_USER;
  273  
  274  	if (!user_mode(regs) && addr < TASK_SIZE && unlikely(!(regs->status & SR_SUM))) {
  275  		if (fixup_exception(regs))
  276  			return;
  277  
  278  		die_kernel_fault("access to user memory without uaccess routines", addr, regs);
  279  	}
  280  
  281  	perf_sw_event(PERF_COUNT_SW_PAGE_FAULTS, 1, regs, addr);
  282  
  283  	if (cause == EXC_STORE_PAGE_FAULT)
  284  		flags |= FAULT_FLAG_WRITE;
  285  	else if (cause == EXC_INST_PAGE_FAULT)
  286  		flags |= FAULT_FLAG_INSTRUCTION;
  287  	if (!(flags & FAULT_FLAG_USER))
  288  		goto lock_mmap;
  289  
  290  	vma = lock_vma_under_rcu(mm, addr);
  291  	if (!vma)
  292  		goto lock_mmap;
  293  
  294  	if (unlikely(access_error(cause, vma))) {
  295  		vma_end_read(vma);
  296  		count_vm_vma_lock_event(VMA_LOCK_SUCCESS);
  297  		tsk->thread.bad_cause = cause;
  298  		bad_area_nosemaphore(regs, SEGV_ACCERR, addr);
  299  		return;
  300  	}
  301  
  302  	fault = handle_mm_fault(vma, addr, flags | FAULT_FLAG_VMA_LOCK, regs);
  303  	if (!(fault & (VM_FAULT_RETRY | VM_FAULT_COMPLETED)))
...
```

`die_kernel_fault`（arch/riscv/mm/fault.c）：

```c
   27  static void die_kernel_fault(const char *msg, unsigned long addr, 		struct pt_regs *regs)  {
   28  	bust_spinlocks(1);
   29  
   30  	pr_alert("Unable to handle kernel %s at virtual address " REG_FMT "\n", msg,
   31  		addr);
   32  
   33  	bust_spinlocks(0);
   34  	die(regs, "Oops");
   35  	make_task_dead(SIGKILL);
   36  }
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
   84  	spin_lock_irqsave(&die_lock, flags);
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
  103  	spin_unlock_irqrestore(&die_lock, flags);
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

## K06

**问题种类**：在PREEMPT_RT下会睡眠的普通自旋锁

**为什么认为这里不能睡眠/需要不可插桩**：陷入处理函数开头到开中断之前（RISC-V进入陷入处理时中断是关着的）

**被标记的函数**：`arch/riscv/kernel/traps.c`中的`do_trap_break`，第302行调用`handle_break`，最终到达`spin_lock_irqsave`

**调用链**：
- `handle_break`（arch/riscv/kernel/traps.c第294行调用`die`）
- `die`（arch/riscv/kernel/traps.c第84行调用`spin_lock_irqsave`）

**代码**：

```c
  298  asmlinkage __visible __trap_section void do_trap_break(struct pt_regs *regs)  {
  299  	if (user_mode(regs)) {
  300  		irqentry_enter_from_user_mode(regs);
  301  
  302  		handle_break(regs);
  303  
  304  		irqentry_exit_to_user_mode(regs);
  305  	} else {
  306  		irqentry_state_t state = irqentry_nmi_enter(regs);
  307  
  308  		handle_break(regs);
  309  
  310  		irqentry_nmi_exit(regs, state);
  311  	}
  312  }
```

`handle_break`（arch/riscv/kernel/traps.c）：

```c
  274  void handle_break(struct pt_regs *regs)  {
  275  	if (probe_single_step_handler(regs))
  276  		return;
  277  
  278  	if (probe_breakpoint_handler(regs))
  279  		return;
  280  
  281  	current->thread.bad_cause = regs->cause;
  282  
  283  	if (user_mode(regs))
  284  		force_sig_fault(SIGTRAP, TRAP_BRKPT, (void __user *)regs->epc);
  285  #ifdef CONFIG_KGDB
  286  	else if (notify_die(DIE_TRAP, "EBREAK", regs, 0, regs->cause, SIGTRAP)
  287  								== NOTIFY_STOP)
  288  		return;
  289  #endif
  290  	else if (report_bug(regs->epc, regs) == BUG_TRAP_TYPE_WARN ||
  291  		 handle_cfi_failure(regs) == BUG_TRAP_TYPE_WARN)
  292  		regs->epc += get_break_insn_length(regs->epc);
  293  	else
  294  		die(regs, "Kernel BUG");
  295  }
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
   84  	spin_lock_irqsave(&die_lock, flags);
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
  103  	spin_unlock_irqrestore(&die_lock, flags);
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

## K07

**问题种类**：在PREEMPT_RT下会睡眠的普通自旋锁

**为什么认为这里不能睡眠/需要不可插桩**：陷入处理函数开头到开中断之前（RISC-V进入陷入处理时中断是关着的）

**被标记的函数**：`arch/riscv/kernel/traps.c`中的`do_trap_break`，第308行调用`handle_break`，最终到达`spin_lock_irqsave`

**调用链**：
- `handle_break`（arch/riscv/kernel/traps.c第294行调用`die`）
- `die`（arch/riscv/kernel/traps.c第84行调用`spin_lock_irqsave`）

**代码**：

```c
  298  asmlinkage __visible __trap_section void do_trap_break(struct pt_regs *regs)  {
  299  	if (user_mode(regs)) {
  300  		irqentry_enter_from_user_mode(regs);
  301  
  302  		handle_break(regs);
  303  
  304  		irqentry_exit_to_user_mode(regs);
  305  	} else {
  306  		irqentry_state_t state = irqentry_nmi_enter(regs);
  307  
  308  		handle_break(regs);
  309  
  310  		irqentry_nmi_exit(regs, state);
  311  	}
  312  }
```

`handle_break`（arch/riscv/kernel/traps.c）：

```c
  274  void handle_break(struct pt_regs *regs)  {
  275  	if (probe_single_step_handler(regs))
  276  		return;
  277  
  278  	if (probe_breakpoint_handler(regs))
  279  		return;
  280  
  281  	current->thread.bad_cause = regs->cause;
  282  
  283  	if (user_mode(regs))
  284  		force_sig_fault(SIGTRAP, TRAP_BRKPT, (void __user *)regs->epc);
  285  #ifdef CONFIG_KGDB
  286  	else if (notify_die(DIE_TRAP, "EBREAK", regs, 0, regs->cause, SIGTRAP)
  287  								== NOTIFY_STOP)
  288  		return;
  289  #endif
  290  	else if (report_bug(regs->epc, regs) == BUG_TRAP_TYPE_WARN ||
  291  		 handle_cfi_failure(regs) == BUG_TRAP_TYPE_WARN)
  292  		regs->epc += get_break_insn_length(regs->epc);
  293  	else
  294  		die(regs, "Kernel BUG");
  295  }
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
   84  	spin_lock_irqsave(&die_lock, flags);
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
  103  	spin_unlock_irqrestore(&die_lock, flags);
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

## K08

**问题种类**：在PREEMPT_RT下会睡眠的普通自旋锁

**为什么认为这里不能睡眠/需要不可插桩**：陷入处理函数开头到开中断之前（RISC-V进入陷入处理时中断是关着的）

**被标记的函数**：`arch/riscv/kernel/traps.c`中的`do_trap_ecall_u`，第349行调用`do_trap_error`，最终到达`spin_lock_irqsave`

**调用链**：
- `do_trap_error`（arch/riscv/kernel/traps.c第140行调用`die`）
- `die`（arch/riscv/kernel/traps.c第84行调用`spin_lock_irqsave`）

**代码**：

```c
  316  asmlinkage __visible __trap_section  __no_stack_protector void do_trap_ecall_u(struct pt_regs *regs)  {
  317  	if (user_mode(regs)) {
  318  		long syscall = regs->a7;
  319  
  320  		regs->epc += 4;
  321  		regs->orig_a0 = regs->a0;
  322  		regs->a0 = -ENOSYS;
  323  
  324  		riscv_v_vstate_discard(regs);
  325  
  326  		syscall = syscall_enter_from_user_mode(regs, syscall);
  327  
  328  		add_random_kstack_offset();
  329  
  330  		if (syscall >= 0 && syscall < NR_syscalls)
  331  			syscall_handler(regs, syscall);
  332  
  333  		/*
  334  		 * Ultimately, this value will get limited by KSTACK_OFFSET_MAX(),
  335  		 * so the maximum stack offset is 1k bytes (10 bits).
  336  		 *
  337  		 * The actual entropy will be further reduced by the compiler when
  338  		 * applying stack alignment constraints: 16-byte (i.e. 4-bit) aligned
  339  		 * for RV32I or RV64I.
  340  		 *
  341  		 * The resulting 6 bits of entropy is seen in SP[9:4].
  342  		 */
  343  		choose_random_kstack_offset(get_random_u16());
  344  
  345  		syscall_exit_to_user_mode(regs);
  346  	} else {
  347  		irqentry_state_t state = irqentry_nmi_enter(regs);
  348  
  349  		do_trap_error(regs, SIGILL, ILL_ILLTRP, regs->epc,
  350  			"Oops - environment call from U-mode");
  351  
  352  		irqentry_nmi_exit(regs, state);
  353  	}
  354  
  355  }
```

`do_trap_error`（arch/riscv/kernel/traps.c）：

```c
  133  static void do_trap_error(struct pt_regs *regs, int signo, int code, 	unsigned long addr, const char *str)  {
  134  	current->thread.bad_cause = regs->cause;
  135  
  136  	if (user_mode(regs)) {
  137  		do_trap(regs, signo, code, addr);
  138  	} else {
  139  		if (!fixup_exception(regs))
  140  			die(regs, str);
  141  	}
  142  }
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
   84  	spin_lock_irqsave(&die_lock, flags);
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
  103  	spin_unlock_irqrestore(&die_lock, flags);
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

## K09

**问题种类**：可能睡眠

**为什么认为这里不能睡眠/需要不可插桩**：陷入处理函数开头到开中断之前（RISC-V进入陷入处理时中断是关着的）

**被标记的函数**：`arch/riscv/kernel/traps.c`中的`do_trap_load_misaligned`，第206行调用`handle_misaligned_load`，最终到达`copy_from_user`

**调用链**：
- `handle_misaligned_load`（arch/riscv/kernel/traps_misaligned.c第418行调用`copy_from_user`）

**代码**：

```c
  202  asmlinkage __visible __trap_section void do_trap_load_misaligned(struct pt_regs *regs)  {
  203  	if (user_mode(regs)) {
  204  		irqentry_enter_from_user_mode(regs);
  205  
  206  		if (handle_misaligned_load(regs))
  207  			do_trap_error(regs, SIGBUS, BUS_ADRALN, regs->epc,
  208  			      "Oops - load address misaligned");
  209  
  210  		irqentry_exit_to_user_mode(regs);
  211  	} else {
  212  		irqentry_state_t state = irqentry_nmi_enter(regs);
  213  
  214  		if (handle_misaligned_load(regs))
  215  			do_trap_error(regs, SIGBUS, BUS_ADRALN, regs->epc,
  216  			      "Oops - load address misaligned");
  217  
  218  		irqentry_nmi_exit(regs, state);
  219  	}
  220  }
```

`handle_misaligned_load`（arch/riscv/kernel/traps_misaligned.c）：

```c
  329  int handle_misaligned_load(struct pt_regs *regs)  {
  330  	union reg_data val;
  331  	unsigned long epc = regs->epc;
  332  	unsigned long insn;
  333  	unsigned long addr = regs->badaddr;
  334  	int fp = 0, shift = 0, len = 0;
  335  
  336  	perf_sw_event(PERF_COUNT_SW_ALIGNMENT_FAULTS, 1, regs, addr);
  337  
  338  #ifdef CONFIG_RISCV_PROBE_UNALIGNED_ACCESS
  339  	*this_cpu_ptr(&misaligned_access_speed) = RISCV_HWPROBE_MISALIGNED_SCALAR_EMULATED;
  340  #endif
  341  
  342  	if (!unaligned_enabled)
  343  		return -1;
  344  
  345  	if (user_mode(regs) && (current->thread.align_ctl & PR_UNALIGN_SIGBUS))
  346  		return -1;
  347  
  348  	if (get_insn(regs, epc, &insn))
  349  		return -1;
  350  
  351  	regs->epc = 0;
  352  
  353  	if ((insn & INSN_MASK_LW) == INSN_MATCH_LW) {
  354  		len = 4;
  355  		shift = 8 * (sizeof(unsigned long) - len);
  356  #if defined(CONFIG_64BIT)
  357  	} else if ((insn & INSN_MASK_LD) == INSN_MATCH_LD) {
  358  		len = 8;
  359  		shift = 8 * (sizeof(unsigned long) - len);
  360  	} else if ((insn & INSN_MASK_LWU) == INSN_MATCH_LWU) {
  361  		len = 4;
  362  #endif
  363  	} else if ((insn & INSN_MASK_FLD) == INSN_MATCH_FLD) {
  364  		fp = 1;
  365  		len = 8;
  366  	} else if ((insn & INSN_MASK_FLW) == INSN_MATCH_FLW) {
  367  		fp = 1;
  368  		len = 4;
  369  	} else if ((insn & INSN_MASK_LH) == INSN_MATCH_LH) {
  370  		len = 2;
  371  		shift = 8 * (sizeof(unsigned long) - len);
  372  	} else if ((insn & INSN_MASK_LHU) == INSN_MATCH_LHU) {
  373  		len = 2;
  374  #if defined(CONFIG_64BIT)
  375  	} else if ((insn & INSN_MASK_C_LD) == INSN_MATCH_C_LD) {
  376  		len = 8;
  377  		shift = 8 * (sizeof(unsigned long) - len);
  378  		insn = RVC_RS2S(insn) << SH_RD;
  379  	} else if ((insn & INSN_MASK_C_LDSP) == INSN_MATCH_C_LDSP &&
  380  		   ((insn >> SH_RD) & 0x1f)) {
  381  		len = 8;
  382  		shift = 8 * (sizeof(unsigned long) - len);
  383  #endif
  384  	} else if ((insn & INSN_MASK_C_LW) == INSN_MATCH_C_LW) {
  385  		len = 4;
  386  		shift = 8 * (sizeof(unsigned long) - len);
  387  		insn = RVC_RS2S(insn) << SH_RD;
  388  	} else if ((insn & INSN_MASK_C_LWSP) == INSN_MATCH_C_LWSP &&
  389  		   ((insn >> SH_RD) & 0x1f)) {
  390  		len = 4;
  391  		shift = 8 * (sizeof(unsigned long) - len);
  392  	} else if ((insn & INSN_MASK_C_FLD) == INSN_MATCH_C_FLD) {
  393  		fp = 1;
  394  		len = 8;
  395  		insn = RVC_RS2S(insn) << SH_RD;
  396  	} else if ((insn & INSN_MASK_C_FLDSP) == INSN_MATCH_C_FLDSP) {
  397  		fp = 1;
  398  		len = 8;
  399  #if defined(CONFIG_32BIT)
  400  	} else if ((insn & INSN_MASK_C_FLW) == INSN_MATCH_C_FLW) {
  401  		fp = 1;
  402  		len = 4;
  403  		insn = RVC_RS2S(insn) << SH_RD;
  404  	} else if ((insn & INSN_MASK_C_FLWSP) == INSN_MATCH_C_FLWSP) {
  405  		fp = 1;
  406  		len = 4;
  407  #endif
  408  	} else {
...
```

## K10

**问题种类**：在PREEMPT_RT下会睡眠的普通自旋锁

**为什么认为这里不能睡眠/需要不可插桩**：陷入处理函数开头到开中断之前（RISC-V进入陷入处理时中断是关着的）

**被标记的函数**：`arch/riscv/kernel/traps.c`中的`do_trap_load_misaligned`，第207行调用`do_trap_error`，最终到达`spin_lock_irqsave`

**调用链**：
- `do_trap_error`（arch/riscv/kernel/traps.c第140行调用`die`）
- `die`（arch/riscv/kernel/traps.c第84行调用`spin_lock_irqsave`）

**代码**：

```c
  202  asmlinkage __visible __trap_section void do_trap_load_misaligned(struct pt_regs *regs)  {
  203  	if (user_mode(regs)) {
  204  		irqentry_enter_from_user_mode(regs);
  205  
  206  		if (handle_misaligned_load(regs))
  207  			do_trap_error(regs, SIGBUS, BUS_ADRALN, regs->epc,
  208  			      "Oops - load address misaligned");
  209  
  210  		irqentry_exit_to_user_mode(regs);
  211  	} else {
  212  		irqentry_state_t state = irqentry_nmi_enter(regs);
  213  
  214  		if (handle_misaligned_load(regs))
  215  			do_trap_error(regs, SIGBUS, BUS_ADRALN, regs->epc,
  216  			      "Oops - load address misaligned");
  217  
  218  		irqentry_nmi_exit(regs, state);
  219  	}
  220  }
```

`do_trap_error`（arch/riscv/kernel/traps.c）：

```c
  133  static void do_trap_error(struct pt_regs *regs, int signo, int code, 	unsigned long addr, const char *str)  {
  134  	current->thread.bad_cause = regs->cause;
  135  
  136  	if (user_mode(regs)) {
  137  		do_trap(regs, signo, code, addr);
  138  	} else {
  139  		if (!fixup_exception(regs))
  140  			die(regs, str);
  141  	}
  142  }
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
   84  	spin_lock_irqsave(&die_lock, flags);
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
  103  	spin_unlock_irqrestore(&die_lock, flags);
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

## K11

**问题种类**：可能睡眠

**为什么认为这里不能睡眠/需要不可插桩**：陷入处理函数开头到开中断之前（RISC-V进入陷入处理时中断是关着的）

**被标记的函数**：`arch/riscv/kernel/traps.c`中的`do_trap_load_misaligned`，第214行调用`handle_misaligned_load`，最终到达`copy_from_user`

**调用链**：
- `handle_misaligned_load`（arch/riscv/kernel/traps_misaligned.c第418行调用`copy_from_user`）

**代码**：

```c
  202  asmlinkage __visible __trap_section void do_trap_load_misaligned(struct pt_regs *regs)  {
  203  	if (user_mode(regs)) {
  204  		irqentry_enter_from_user_mode(regs);
  205  
  206  		if (handle_misaligned_load(regs))
  207  			do_trap_error(regs, SIGBUS, BUS_ADRALN, regs->epc,
  208  			      "Oops - load address misaligned");
  209  
  210  		irqentry_exit_to_user_mode(regs);
  211  	} else {
  212  		irqentry_state_t state = irqentry_nmi_enter(regs);
  213  
  214  		if (handle_misaligned_load(regs))
  215  			do_trap_error(regs, SIGBUS, BUS_ADRALN, regs->epc,
  216  			      "Oops - load address misaligned");
  217  
  218  		irqentry_nmi_exit(regs, state);
  219  	}
  220  }
```

`handle_misaligned_load`（arch/riscv/kernel/traps_misaligned.c）：

```c
  329  int handle_misaligned_load(struct pt_regs *regs)  {
  330  	union reg_data val;
  331  	unsigned long epc = regs->epc;
  332  	unsigned long insn;
  333  	unsigned long addr = regs->badaddr;
  334  	int fp = 0, shift = 0, len = 0;
  335  
  336  	perf_sw_event(PERF_COUNT_SW_ALIGNMENT_FAULTS, 1, regs, addr);
  337  
  338  #ifdef CONFIG_RISCV_PROBE_UNALIGNED_ACCESS
  339  	*this_cpu_ptr(&misaligned_access_speed) = RISCV_HWPROBE_MISALIGNED_SCALAR_EMULATED;
  340  #endif
  341  
  342  	if (!unaligned_enabled)
  343  		return -1;
  344  
  345  	if (user_mode(regs) && (current->thread.align_ctl & PR_UNALIGN_SIGBUS))
  346  		return -1;
  347  
  348  	if (get_insn(regs, epc, &insn))
  349  		return -1;
  350  
  351  	regs->epc = 0;
  352  
  353  	if ((insn & INSN_MASK_LW) == INSN_MATCH_LW) {
  354  		len = 4;
  355  		shift = 8 * (sizeof(unsigned long) - len);
  356  #if defined(CONFIG_64BIT)
  357  	} else if ((insn & INSN_MASK_LD) == INSN_MATCH_LD) {
  358  		len = 8;
  359  		shift = 8 * (sizeof(unsigned long) - len);
  360  	} else if ((insn & INSN_MASK_LWU) == INSN_MATCH_LWU) {
  361  		len = 4;
  362  #endif
  363  	} else if ((insn & INSN_MASK_FLD) == INSN_MATCH_FLD) {
  364  		fp = 1;
  365  		len = 8;
  366  	} else if ((insn & INSN_MASK_FLW) == INSN_MATCH_FLW) {
  367  		fp = 1;
  368  		len = 4;
  369  	} else if ((insn & INSN_MASK_LH) == INSN_MATCH_LH) {
  370  		len = 2;
  371  		shift = 8 * (sizeof(unsigned long) - len);
  372  	} else if ((insn & INSN_MASK_LHU) == INSN_MATCH_LHU) {
  373  		len = 2;
  374  #if defined(CONFIG_64BIT)
  375  	} else if ((insn & INSN_MASK_C_LD) == INSN_MATCH_C_LD) {
  376  		len = 8;
  377  		shift = 8 * (sizeof(unsigned long) - len);
  378  		insn = RVC_RS2S(insn) << SH_RD;
  379  	} else if ((insn & INSN_MASK_C_LDSP) == INSN_MATCH_C_LDSP &&
  380  		   ((insn >> SH_RD) & 0x1f)) {
  381  		len = 8;
  382  		shift = 8 * (sizeof(unsigned long) - len);
  383  #endif
  384  	} else if ((insn & INSN_MASK_C_LW) == INSN_MATCH_C_LW) {
  385  		len = 4;
  386  		shift = 8 * (sizeof(unsigned long) - len);
  387  		insn = RVC_RS2S(insn) << SH_RD;
  388  	} else if ((insn & INSN_MASK_C_LWSP) == INSN_MATCH_C_LWSP &&
  389  		   ((insn >> SH_RD) & 0x1f)) {
  390  		len = 4;
  391  		shift = 8 * (sizeof(unsigned long) - len);
  392  	} else if ((insn & INSN_MASK_C_FLD) == INSN_MATCH_C_FLD) {
  393  		fp = 1;
  394  		len = 8;
  395  		insn = RVC_RS2S(insn) << SH_RD;
  396  	} else if ((insn & INSN_MASK_C_FLDSP) == INSN_MATCH_C_FLDSP) {
  397  		fp = 1;
  398  		len = 8;
  399  #if defined(CONFIG_32BIT)
  400  	} else if ((insn & INSN_MASK_C_FLW) == INSN_MATCH_C_FLW) {
  401  		fp = 1;
  402  		len = 4;
  403  		insn = RVC_RS2S(insn) << SH_RD;
  404  	} else if ((insn & INSN_MASK_C_FLWSP) == INSN_MATCH_C_FLWSP) {
  405  		fp = 1;
  406  		len = 4;
  407  #endif
  408  	} else {
...
```

## K12

**问题种类**：在PREEMPT_RT下会睡眠的普通自旋锁

**为什么认为这里不能睡眠/需要不可插桩**：陷入处理函数开头到开中断之前（RISC-V进入陷入处理时中断是关着的）

**被标记的函数**：`arch/riscv/kernel/traps.c`中的`do_trap_load_misaligned`，第215行调用`do_trap_error`，最终到达`spin_lock_irqsave`

**调用链**：
- `do_trap_error`（arch/riscv/kernel/traps.c第140行调用`die`）
- `die`（arch/riscv/kernel/traps.c第84行调用`spin_lock_irqsave`）

**代码**：

```c
  202  asmlinkage __visible __trap_section void do_trap_load_misaligned(struct pt_regs *regs)  {
  203  	if (user_mode(regs)) {
  204  		irqentry_enter_from_user_mode(regs);
  205  
  206  		if (handle_misaligned_load(regs))
  207  			do_trap_error(regs, SIGBUS, BUS_ADRALN, regs->epc,
  208  			      "Oops - load address misaligned");
  209  
  210  		irqentry_exit_to_user_mode(regs);
  211  	} else {
  212  		irqentry_state_t state = irqentry_nmi_enter(regs);
  213  
  214  		if (handle_misaligned_load(regs))
  215  			do_trap_error(regs, SIGBUS, BUS_ADRALN, regs->epc,
  216  			      "Oops - load address misaligned");
  217  
  218  		irqentry_nmi_exit(regs, state);
  219  	}
  220  }
```

`do_trap_error`（arch/riscv/kernel/traps.c）：

```c
  133  static void do_trap_error(struct pt_regs *regs, int signo, int code, 	unsigned long addr, const char *str)  {
  134  	current->thread.bad_cause = regs->cause;
  135  
  136  	if (user_mode(regs)) {
  137  		do_trap(regs, signo, code, addr);
  138  	} else {
  139  		if (!fixup_exception(regs))
  140  			die(regs, str);
  141  	}
  142  }
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
   84  	spin_lock_irqsave(&die_lock, flags);
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
  103  	spin_unlock_irqrestore(&die_lock, flags);
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

## K13

**问题种类**：可能睡眠

**为什么认为这里不能睡眠/需要不可插桩**：陷入处理函数开头到开中断之前（RISC-V进入陷入处理时中断是关着的）

**被标记的函数**：`arch/riscv/kernel/traps.c`中的`do_trap_store_misaligned`，第227行调用`handle_misaligned_store`，最终到达`copy_to_user`

**调用链**：
- `handle_misaligned_store`（arch/riscv/kernel/traps_misaligned.c第516行调用`copy_to_user`）

**代码**：

```c
  223  asmlinkage __visible __trap_section void do_trap_store_misaligned(struct pt_regs *regs)  {
  224  	if (user_mode(regs)) {
  225  		irqentry_enter_from_user_mode(regs);
  226  
  227  		if (handle_misaligned_store(regs))
  228  			do_trap_error(regs, SIGBUS, BUS_ADRALN, regs->epc,
  229  				"Oops - store (or AMO) address misaligned");
  230  
  231  		irqentry_exit_to_user_mode(regs);
  232  	} else {
  233  		irqentry_state_t state = irqentry_nmi_enter(regs);
  234  
  235  		if (handle_misaligned_store(regs))
  236  			do_trap_error(regs, SIGBUS, BUS_ADRALN, regs->epc,
  237  				"Oops - store (or AMO) address misaligned");
  238  
  239  		irqentry_nmi_exit(regs, state);
  240  	}
  241  }
```

`handle_misaligned_store`（arch/riscv/kernel/traps_misaligned.c）：

```c
  437  int handle_misaligned_store(struct pt_regs *regs)  {
  438  	union reg_data val;
  439  	unsigned long epc = regs->epc;
  440  	unsigned long insn;
  441  	unsigned long addr = regs->badaddr;
  442  	int len = 0, fp = 0;
  443  
  444  	perf_sw_event(PERF_COUNT_SW_ALIGNMENT_FAULTS, 1, regs, addr);
  445  
  446  	if (!unaligned_enabled)
  447  		return -1;
  448  
  449  	if (user_mode(regs) && (current->thread.align_ctl & PR_UNALIGN_SIGBUS))
  450  		return -1;
  451  
  452  	if (get_insn(regs, epc, &insn))
  453  		return -1;
  454  
  455  	regs->epc = 0;
  456  
  457  	val.data_ulong = GET_RS2(insn, regs);
  458  
  459  	if ((insn & INSN_MASK_SW) == INSN_MATCH_SW) {
  460  		len = 4;
  461  #if defined(CONFIG_64BIT)
  462  	} else if ((insn & INSN_MASK_SD) == INSN_MATCH_SD) {
  463  		len = 8;
  464  #endif
  465  	} else if ((insn & INSN_MASK_FSD) == INSN_MATCH_FSD) {
  466  		fp = 1;
  467  		len = 8;
  468  		val.data_u64 = GET_F64_RS2(insn, regs);
  469  	} else if ((insn & INSN_MASK_FSW) == INSN_MATCH_FSW) {
  470  		fp = 1;
  471  		len = 4;
  472  		val.data_ulong = GET_F32_RS2(insn, regs);
  473  	} else if ((insn & INSN_MASK_SH) == INSN_MATCH_SH) {
  474  		len = 2;
  475  #if defined(CONFIG_64BIT)
  476  	} else if ((insn & INSN_MASK_C_SD) == INSN_MATCH_C_SD) {
  477  		len = 8;
  478  		val.data_ulong = GET_RS2S(insn, regs);
  479  	} else if ((insn & INSN_MASK_C_SDSP) == INSN_MATCH_C_SDSP) {
  480  		len = 8;
  481  		val.data_ulong = GET_RS2C(insn, regs);
  482  #endif
  483  	} else if ((insn & INSN_MASK_C_SW) == INSN_MATCH_C_SW) {
  484  		len = 4;
  485  		val.data_ulong = GET_RS2S(insn, regs);
  486  	} else if ((insn & INSN_MASK_C_SWSP) == INSN_MATCH_C_SWSP) {
  487  		len = 4;
  488  		val.data_ulong = GET_RS2C(insn, regs);
  489  	} else if ((insn & INSN_MASK_C_FSD) == INSN_MATCH_C_FSD) {
  490  		fp = 1;
  491  		len = 8;
  492  		val.data_u64 = GET_F64_RS2S(insn, regs);
  493  	} else if ((insn & INSN_MASK_C_FSDSP) == INSN_MATCH_C_FSDSP) {
  494  		fp = 1;
  495  		len = 8;
  496  		val.data_u64 = GET_F64_RS2C(insn, regs);
  497  #if !defined(CONFIG_64BIT)
  498  	} else if ((insn & INSN_MASK_C_FSW) == INSN_MATCH_C_FSW) {
  499  		fp = 1;
  500  		len = 4;
  501  		val.data_ulong = GET_F32_RS2S(insn, regs);
  502  	} else if ((insn & INSN_MASK_C_FSWSP) == INSN_MATCH_C_FSWSP) {
  503  		fp = 1;
  504  		len = 4;
  505  		val.data_ulong = GET_F32_RS2C(insn, regs);
  506  #endif
  507  	} else {
  508  		regs->epc = epc;
  509  		return -1;
  510  	}
  511  
  512  	if (!IS_ENABLED(CONFIG_FPU) && fp)
  513  		return -EOPNOTSUPP;
  514  
  515  	if (user_mode(regs)) {
  516  		if (copy_to_user((u8 __user *)addr, &val, len))
...
```

## K14

**问题种类**：在PREEMPT_RT下会睡眠的普通自旋锁

**为什么认为这里不能睡眠/需要不可插桩**：陷入处理函数开头到开中断之前（RISC-V进入陷入处理时中断是关着的）

**被标记的函数**：`arch/riscv/kernel/traps.c`中的`do_trap_store_misaligned`，第228行调用`do_trap_error`，最终到达`spin_lock_irqsave`

**调用链**：
- `do_trap_error`（arch/riscv/kernel/traps.c第140行调用`die`）
- `die`（arch/riscv/kernel/traps.c第84行调用`spin_lock_irqsave`）

**代码**：

```c
  223  asmlinkage __visible __trap_section void do_trap_store_misaligned(struct pt_regs *regs)  {
  224  	if (user_mode(regs)) {
  225  		irqentry_enter_from_user_mode(regs);
  226  
  227  		if (handle_misaligned_store(regs))
  228  			do_trap_error(regs, SIGBUS, BUS_ADRALN, regs->epc,
  229  				"Oops - store (or AMO) address misaligned");
  230  
  231  		irqentry_exit_to_user_mode(regs);
  232  	} else {
  233  		irqentry_state_t state = irqentry_nmi_enter(regs);
  234  
  235  		if (handle_misaligned_store(regs))
  236  			do_trap_error(regs, SIGBUS, BUS_ADRALN, regs->epc,
  237  				"Oops - store (or AMO) address misaligned");
  238  
  239  		irqentry_nmi_exit(regs, state);
  240  	}
  241  }
```

`do_trap_error`（arch/riscv/kernel/traps.c）：

```c
  133  static void do_trap_error(struct pt_regs *regs, int signo, int code, 	unsigned long addr, const char *str)  {
  134  	current->thread.bad_cause = regs->cause;
  135  
  136  	if (user_mode(regs)) {
  137  		do_trap(regs, signo, code, addr);
  138  	} else {
  139  		if (!fixup_exception(regs))
  140  			die(regs, str);
  141  	}
  142  }
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
   84  	spin_lock_irqsave(&die_lock, flags);
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
  103  	spin_unlock_irqrestore(&die_lock, flags);
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

## K15

**问题种类**：可能睡眠

**为什么认为这里不能睡眠/需要不可插桩**：陷入处理函数开头到开中断之前（RISC-V进入陷入处理时中断是关着的）

**被标记的函数**：`arch/riscv/kernel/traps.c`中的`do_trap_store_misaligned`，第235行调用`handle_misaligned_store`，最终到达`copy_to_user`

**调用链**：
- `handle_misaligned_store`（arch/riscv/kernel/traps_misaligned.c第516行调用`copy_to_user`）

**代码**：

```c
  223  asmlinkage __visible __trap_section void do_trap_store_misaligned(struct pt_regs *regs)  {
  224  	if (user_mode(regs)) {
  225  		irqentry_enter_from_user_mode(regs);
  226  
  227  		if (handle_misaligned_store(regs))
  228  			do_trap_error(regs, SIGBUS, BUS_ADRALN, regs->epc,
  229  				"Oops - store (or AMO) address misaligned");
  230  
  231  		irqentry_exit_to_user_mode(regs);
  232  	} else {
  233  		irqentry_state_t state = irqentry_nmi_enter(regs);
  234  
  235  		if (handle_misaligned_store(regs))
  236  			do_trap_error(regs, SIGBUS, BUS_ADRALN, regs->epc,
  237  				"Oops - store (or AMO) address misaligned");
  238  
  239  		irqentry_nmi_exit(regs, state);
  240  	}
  241  }
```

`handle_misaligned_store`（arch/riscv/kernel/traps_misaligned.c）：

```c
  437  int handle_misaligned_store(struct pt_regs *regs)  {
  438  	union reg_data val;
  439  	unsigned long epc = regs->epc;
  440  	unsigned long insn;
  441  	unsigned long addr = regs->badaddr;
  442  	int len = 0, fp = 0;
  443  
  444  	perf_sw_event(PERF_COUNT_SW_ALIGNMENT_FAULTS, 1, regs, addr);
  445  
  446  	if (!unaligned_enabled)
  447  		return -1;
  448  
  449  	if (user_mode(regs) && (current->thread.align_ctl & PR_UNALIGN_SIGBUS))
  450  		return -1;
  451  
  452  	if (get_insn(regs, epc, &insn))
  453  		return -1;
  454  
  455  	regs->epc = 0;
  456  
  457  	val.data_ulong = GET_RS2(insn, regs);
  458  
  459  	if ((insn & INSN_MASK_SW) == INSN_MATCH_SW) {
  460  		len = 4;
  461  #if defined(CONFIG_64BIT)
  462  	} else if ((insn & INSN_MASK_SD) == INSN_MATCH_SD) {
  463  		len = 8;
  464  #endif
  465  	} else if ((insn & INSN_MASK_FSD) == INSN_MATCH_FSD) {
  466  		fp = 1;
  467  		len = 8;
  468  		val.data_u64 = GET_F64_RS2(insn, regs);
  469  	} else if ((insn & INSN_MASK_FSW) == INSN_MATCH_FSW) {
  470  		fp = 1;
  471  		len = 4;
  472  		val.data_ulong = GET_F32_RS2(insn, regs);
  473  	} else if ((insn & INSN_MASK_SH) == INSN_MATCH_SH) {
  474  		len = 2;
  475  #if defined(CONFIG_64BIT)
  476  	} else if ((insn & INSN_MASK_C_SD) == INSN_MATCH_C_SD) {
  477  		len = 8;
  478  		val.data_ulong = GET_RS2S(insn, regs);
  479  	} else if ((insn & INSN_MASK_C_SDSP) == INSN_MATCH_C_SDSP) {
  480  		len = 8;
  481  		val.data_ulong = GET_RS2C(insn, regs);
  482  #endif
  483  	} else if ((insn & INSN_MASK_C_SW) == INSN_MATCH_C_SW) {
  484  		len = 4;
  485  		val.data_ulong = GET_RS2S(insn, regs);
  486  	} else if ((insn & INSN_MASK_C_SWSP) == INSN_MATCH_C_SWSP) {
  487  		len = 4;
  488  		val.data_ulong = GET_RS2C(insn, regs);
  489  	} else if ((insn & INSN_MASK_C_FSD) == INSN_MATCH_C_FSD) {
  490  		fp = 1;
  491  		len = 8;
  492  		val.data_u64 = GET_F64_RS2S(insn, regs);
  493  	} else if ((insn & INSN_MASK_C_FSDSP) == INSN_MATCH_C_FSDSP) {
  494  		fp = 1;
  495  		len = 8;
  496  		val.data_u64 = GET_F64_RS2C(insn, regs);
  497  #if !defined(CONFIG_64BIT)
  498  	} else if ((insn & INSN_MASK_C_FSW) == INSN_MATCH_C_FSW) {
  499  		fp = 1;
  500  		len = 4;
  501  		val.data_ulong = GET_F32_RS2S(insn, regs);
  502  	} else if ((insn & INSN_MASK_C_FSWSP) == INSN_MATCH_C_FSWSP) {
  503  		fp = 1;
  504  		len = 4;
  505  		val.data_ulong = GET_F32_RS2C(insn, regs);
  506  #endif
  507  	} else {
  508  		regs->epc = epc;
  509  		return -1;
  510  	}
  511  
  512  	if (!IS_ENABLED(CONFIG_FPU) && fp)
  513  		return -EOPNOTSUPP;
  514  
  515  	if (user_mode(regs)) {
  516  		if (copy_to_user((u8 __user *)addr, &val, len))
...
```

## K16

**问题种类**：在PREEMPT_RT下会睡眠的普通自旋锁

**为什么认为这里不能睡眠/需要不可插桩**：陷入处理函数开头到开中断之前（RISC-V进入陷入处理时中断是关着的）

**被标记的函数**：`arch/riscv/kernel/traps.c`中的`do_trap_store_misaligned`，第236行调用`do_trap_error`，最终到达`spin_lock_irqsave`

**调用链**：
- `do_trap_error`（arch/riscv/kernel/traps.c第140行调用`die`）
- `die`（arch/riscv/kernel/traps.c第84行调用`spin_lock_irqsave`）

**代码**：

```c
  223  asmlinkage __visible __trap_section void do_trap_store_misaligned(struct pt_regs *regs)  {
  224  	if (user_mode(regs)) {
  225  		irqentry_enter_from_user_mode(regs);
  226  
  227  		if (handle_misaligned_store(regs))
  228  			do_trap_error(regs, SIGBUS, BUS_ADRALN, regs->epc,
  229  				"Oops - store (or AMO) address misaligned");
  230  
  231  		irqentry_exit_to_user_mode(regs);
  232  	} else {
  233  		irqentry_state_t state = irqentry_nmi_enter(regs);
  234  
  235  		if (handle_misaligned_store(regs))
  236  			do_trap_error(regs, SIGBUS, BUS_ADRALN, regs->epc,
  237  				"Oops - store (or AMO) address misaligned");
  238  
  239  		irqentry_nmi_exit(regs, state);
  240  	}
  241  }
```

`do_trap_error`（arch/riscv/kernel/traps.c）：

```c
  133  static void do_trap_error(struct pt_regs *regs, int signo, int code, 	unsigned long addr, const char *str)  {
  134  	current->thread.bad_cause = regs->cause;
  135  
  136  	if (user_mode(regs)) {
  137  		do_trap(regs, signo, code, addr);
  138  	} else {
  139  		if (!fixup_exception(regs))
  140  			die(regs, str);
  141  	}
  142  }
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
   84  	spin_lock_irqsave(&die_lock, flags);
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
  103  	spin_unlock_irqrestore(&die_lock, flags);
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

## K17

**问题种类**：可能睡眠

**为什么认为这里不能睡眠/需要不可插桩**：本函数作为stop_machine或跨核调用的回调执行（中断关闭）；经由：arch/riscv/kernel/ftrace.c:arch_ftrace_update_code

**被标记的函数**：`arch/riscv/kernel/ftrace.c`中的`__ftrace_modify_code`，第144行调用`ftrace_modify_all_code`，最终到达`cond_resched`

**调用链**：
- `ftrace_modify_all_code`（kernel/trace/ftrace.c第2889行调用`ftrace_replace_code`）
- `ftrace_replace_code`（kernel/trace/ftrace.c第2741行调用`cond_resched`）

**代码**：

```c
  140  static int __ftrace_modify_code(void *data)  {
  141  	struct ftrace_modify_param *param = data;
  142  
  143  	if (atomic_inc_return(&param->cpu_count) == num_online_cpus()) {
  144  		ftrace_modify_all_code(param->command);
  145  		/*
  146  		 * Make sure the patching store is effective *before* we
  147  		 * increment the counter which releases all waiting CPUs
  148  		 * by using the release variant of atomic increment. The
  149  		 * release pairs with the call to local_flush_icache_all()
  150  		 * on the waiting CPU.
  151  		 */
  152  		atomic_inc_return_release(&param->cpu_count);
  153  	} else {
  154  		while (atomic_read(&param->cpu_count) <= num_online_cpus())
  155  			cpu_relax();
  156  
  157  		local_flush_icache_all();
  158  	}
  159  
  160  	return 0;
  161  }
```

`ftrace_modify_all_code`（kernel/trace/ftrace.c）：

```c
 2864  void ftrace_modify_all_code(int command)  {
 2865  	int update = command & FTRACE_UPDATE_TRACE_FUNC;
 2866  	int mod_flags = 0;
 2867  	int err = 0;
 2868  
 2869  	if (command & FTRACE_MAY_SLEEP)
 2870  		mod_flags = FTRACE_MODIFY_MAY_SLEEP_FL;
 2871  
 2872  	/*
 2873  	 * If the ftrace_caller calls a ftrace_ops func directly,
 2874  	 * we need to make sure that it only traces functions it
 2875  	 * expects to trace. When doing the switch of functions,
 2876  	 * we need to update to the ftrace_ops_list_func first
 2877  	 * before the transition between old and new calls are set,
 2878  	 * as the ftrace_ops_list_func will check the ops hashes
 2879  	 * to make sure the ops are having the right functions
 2880  	 * traced.
 2881  	 */
 2882  	if (update) {
 2883  		err = update_ftrace_func(ftrace_ops_list_func);
 2884  		if (FTRACE_WARN_ON(err))
 2885  			return;
 2886  	}
 2887  
 2888  	if (command & FTRACE_UPDATE_CALLS)
 2889  		ftrace_replace_code(mod_flags | FTRACE_MODIFY_ENABLE_FL);
 2890  	else if (command & FTRACE_DISABLE_CALLS)
 2891  		ftrace_replace_code(mod_flags);
 2892  
 2893  	if (update && ftrace_trace_function != ftrace_ops_list_func) {
 2894  		function_trace_op = set_function_trace_op;
 2895  		smp_wmb();
 2896  		/* If irqs are disabled, we are in stop machine */
 2897  		if (!irqs_disabled())
 2898  			smp_call_function(ftrace_sync_ipi, NULL, 1);
 2899  		err = update_ftrace_func(ftrace_trace_function);
 2900  		if (FTRACE_WARN_ON(err))
 2901  			return;
 2902  	}
 2903  
 2904  	if (command & FTRACE_START_FUNC_RET)
 2905  		err = ftrace_enable_ftrace_graph_caller();
 2906  	else if (command & FTRACE_STOP_FUNC_RET)
 2907  		err = ftrace_disable_ftrace_graph_caller();
 2908  	FTRACE_WARN_ON(err);
 2909  }
```

`ftrace_replace_code`（kernel/trace/ftrace.c）：

```c
 2719  void __weak ftrace_replace_code(int mod_flags)  {
 2720  	struct dyn_ftrace *rec;
 2721  	struct ftrace_page *pg;
 2722  	bool enable = mod_flags & FTRACE_MODIFY_ENABLE_FL;
 2723  	int schedulable = mod_flags & FTRACE_MODIFY_MAY_SLEEP_FL;
 2724  	int failed;
 2725  
 2726  	if (unlikely(ftrace_disabled))
 2727  		return;
 2728  
 2729  	do_for_each_ftrace_rec(pg, rec) {
 2730  
 2731  		if (skip_record(rec))
 2732  			continue;
 2733  
 2734  		failed = __ftrace_replace_code(rec, enable);
 2735  		if (failed) {
 2736  			ftrace_bug(failed, rec);
 2737  			/* Stop processing */
 2738  			return;
 2739  		}
 2740  		if (schedulable)
 2741  			cond_resched();
 2742  	} while_for_each_ftrace_rec();
 2743  }
```

## K18

**问题种类**：在PREEMPT_RT下会睡眠的普通自旋锁

**为什么认为这里不能睡眠/需要不可插桩**：公共代码在原子区间内调用本函数（见“经由”）；经由：kernel/power/hibernate.c:create_image [irq]

**被标记的函数**：`arch/riscv/kernel/hibernate.c`中的`swsusp_arch_suspend`，第152行调用`swsusp_save`，最终到达`spin_lock`

**调用链**：
- `swsusp_save`（kernel/power/snapshot.c第2120行调用`drain_local_pages`）
- `drain_local_pages`（mm/page_alloc.c第2427行调用`drain_pages_zone`）
- `drain_pages_zone`（mm/page_alloc.c第2394行调用`spin_lock`）

**代码**：

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
 2115  asmlinkage __visible int swsusp_save(void)  {
 2116  	unsigned int nr_pages, nr_highmem;
 2117  
 2118  	pr_info("Creating image:\n");
 2119  
 2120  	drain_local_pages(NULL);
 2121  	nr_pages = count_data_pages();
 2122  	nr_highmem = count_highmem_pages();
 2123  	pr_info("Need to copy %u pages\n", nr_pages + nr_highmem);
 2124  
 2125  	if (!enough_free_mem(nr_pages, nr_highmem)) {
 2126  		pr_err("Not enough free memory\n");
 2127  		return -ENOMEM;
 2128  	}
 2129  
 2130  	if (swsusp_alloc(&copy_bm, nr_pages, nr_highmem)) {
 2131  		pr_err("Memory allocation failed\n");
 2132  		return -ENOMEM;
 2133  	}
 2134  
 2135  	/*
 2136  	 * During allocating of suspend pagedir, new cold pages may appear.
 2137  	 * Kill them.
 2138  	 */
 2139  	drain_local_pages(NULL);
 2140  	nr_copy_pages = copy_data_pages(&copy_bm, &orig_bm, &zero_bm);
 2141  
 2142  	/*
 2143  	 * End of critical section. From now on, we can write to memory,
 2144  	 * but we should not touch disk. This specially means we must _not_
 2145  	 * touch swap space! Except we must write out our image of course.
 2146  	 */
 2147  	nr_pages += nr_highmem;
 2148  	/* We don't actually copy the zero pages */
 2149  	nr_zero_pages = nr_pages - nr_copy_pages;
 2150  	nr_meta_pages = DIV_ROUND_UP(nr_pages * sizeof(long), PAGE_SIZE);
 2151  
 2152  	pr_info("Image created (%d pages copied, %d zero pages)\n", nr_copy_pages, nr_zero_pages);
 2153  
 2154  	return 0;
 2155  }
```

`drain_local_pages`（mm/page_alloc.c）：

```c
 2423  void drain_local_pages(struct zone *zone)  {
 2424  	int cpu = smp_processor_id();
 2425  
 2426  	if (zone)
 2427  		drain_pages_zone(cpu, zone);
 2428  	else
 2429  		drain_pages(cpu);
 2430  }
```

`drain_pages_zone`（mm/page_alloc.c）：

```c
 2389  static void drain_pages_zone(unsigned int cpu, struct zone *zone)  {
 2390  	struct per_cpu_pages *pcp = per_cpu_ptr(zone->per_cpu_pageset, cpu);
 2391  	int count;
 2392  
 2393  	do {
 2394  		spin_lock(&pcp->lock);
 2395  		count = pcp->count;
 2396  		if (count) {
 2397  			int to_drain = min(count,
 2398  				pcp->batch << CONFIG_PCP_BATCH_SCALE_MAX);
 2399  
 2400  			free_pcppages_bulk(zone, to_drain, pcp, 0);
 2401  			count -= to_drain;
 2402  		}
 2403  		spin_unlock(&pcp->lock);
 2404  	} while (count);
 2405  }
```

## K19

**问题种类**：可能睡眠

**为什么认为这里不能睡眠/需要不可插桩**：公共代码在原子区间内调用本函数（见“经由”）；经由：kernel/power/hibernate.c:create_image [irq]

**被标记的函数**：`arch/riscv/kernel/hibernate.c`中的`swsusp_arch_suspend`，第155行调用`flush_tlb_all`，最终到达`on_each_cpu`

**调用链**：
- `flush_tlb_all`（arch/riscv/mm/tlbflush.c第64行调用`on_each_cpu`）

**代码**：

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
   58  void flush_tlb_all(void)  {
   59  	if (num_online_cpus() < 2)
   60  		local_flush_tlb_all();
   61  	else if (riscv_use_sbi_for_rfence())
   62  		sbi_remote_sfence_vma_asid(NULL, 0, FLUSH_TLB_MAX_SIZE, FLUSH_TLB_NO_ASID);
   63  	else
   64  		on_each_cpu(__ipi_flush_tlb_all, NULL, 1);
   65  }
```

## K20

**问题种类**：可能睡眠

**为什么认为这里不能睡眠/需要不可插桩**：公共代码在原子区间内调用本函数（见“经由”）；经由：kernel/power/hibernate.c:create_image [irq]

**被标记的函数**：`arch/riscv/kernel/hibernate.c`中的`swsusp_arch_suspend`，第156行调用`flush_icache_all`，最终到达`on_each_cpu`

**调用链**：
- `flush_icache_all`（arch/riscv/mm/cacheflush.c第30行调用`on_each_cpu`）

**代码**：

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
   27  	else if (riscv_use_sbi_for_rfence())
   28  		sbi_remote_fence_i(NULL);
   29  	else
   30  		on_each_cpu(ipi_remote_fence_i, NULL, 1);
   31  }
```

## K21

**问题种类**：不可插桩约定

**为什么认为这里不能睡眠/需要不可插桩**：公共代码中标了noinstr/__cpuidle的函数调用了本函数，而参照架构的同名函数标了noinstr/__cpuidle/__always_inline；经由：kernel/entry/common.c:irqentry_exit

**被标记的函数**：`arch/riscv/include/asm/ptrace.h`中的`regs_irqs_disabled`，第177行调用`regs_irqs_disabled`，最终到达`called from noinstr/__cpuidle`

**调用链**：
（直接调用）

**代码**：

```c
  177  static inline int regs_irqs_disabled(struct pt_regs *regs)  {
  178  	return !(regs->status & SR_PIE);
  179  }
```

## K22

**问题种类**：不可插桩约定

**为什么认为这里不能睡眠/需要不可插桩**：公共代码中标了noinstr/__cpuidle的函数调用了本函数，而参照架构的同名函数标了noinstr/__cpuidle/__always_inline；经由：kernel/stackleak.c:stackleak_erase

**被标记的函数**：`arch/riscv/include/asm/stacktrace.h`中的`on_thread_stack`，第20行调用`on_thread_stack`，最终到达`called from noinstr/__cpuidle`

**调用链**：
（直接调用）

**代码**：

```c
   20  static inline bool on_thread_stack(void)  {
   21  	return !(((unsigned long)(current->stack) ^ current_stack_pointer) & ~(THREAD_SIZE - 1));
   22  }
```

## K23

**问题种类**：不可插桩约定

**为什么认为这里不能睡眠/需要不可插桩**：本函数标了noinstr，却在instrumentation_begin/end之外调用了可插桩的函数

**被标记的函数**：`arch/riscv/kernel/stacktrace.c`中的`arch_stack_walk`，第163行调用`walk_stackframe`，最终到达`instrumentable callee`

**调用链**：
- `walk_stackframe`（arch/riscv/kernel/stacktrace.c第33行调用``）

**代码**：

```c
  162  noinline noinstr void arch_stack_walk(stack_trace_consume_fn consume_entry, void *cookie, 		     struct task_struct *task, struct pt_regs *regs)  {
  163  	walk_stackframe(task, regs, consume_entry, cookie);
  164  }
```

`walk_stackframe`（arch/riscv/kernel/stacktrace.c）：

```c
   33  void notrace walk_stackframe(struct task_struct *task, struct pt_regs *regs, 			     bool (*fn)(void *, unsigned long), void *arg)  {
   34  	unsigned long fp, sp, pc;
   35  	int graph_idx = 0;
   36  	int level = 0;
   37  
   38  	if (regs) {
   39  		fp = frame_pointer(regs);
   40  		sp = user_stack_pointer(regs);
   41  		pc = instruction_pointer(regs);
   42  	} else if (task == NULL || task == current) {
   43  		fp = (unsigned long)__builtin_frame_address(0);
   44  		sp = current_stack_pointer;
   45  		pc = (unsigned long)walk_stackframe;
   46  		level = -1;
   47  	} else {
   48  		/* task blocked in __switch_to */
   49  		fp = task->thread.s[0];
   50  		sp = task->thread.sp;
   51  		pc = task->thread.ra;
   52  	}
   53  
   54  	for (;;) {
   55  		struct stackframe *frame;
   56  
   57  		if (unlikely(!__kernel_text_address(pc) || (level++ >= 0 && !fn(arg, pc))))
   58  			break;
   59  
   60  		if (unlikely(!fp_is_valid(fp, sp)))
   61  			break;
   62  
   63  		/* Unwind stack frame */
   64  		frame = (struct stackframe *)fp - 1;
   65  		sp = fp;
   66  		if (regs && (regs->epc == pc) && fp_is_valid(frame->ra, sp)) {
   67  			/* We hit function where ra is not saved on the stack */
   68  			fp = frame->ra;
   69  			pc = regs->ra;
   70  		} else {
   71  			fp = frame->fp;
   72  			pc = ftrace_graph_ret_addr(current, &graph_idx, frame->ra,
   73  						   &frame->ra);
   74  			if (pc == (unsigned long)handle_exception) {
   75  				if (unlikely(!__kernel_text_address(pc) || !fn(arg, pc)))
   76  					break;
   77  
   78  				pc = ((struct pt_regs *)sp)->epc;
   79  				fp = ((struct pt_regs *)sp)->s0;
   80  			}
   81  		}
   82  
   83  	}
   84  }
```

## K24

**问题种类**：不可插桩约定

**为什么认为这里不能睡眠/需要不可插桩**：本函数标了noinstr，却在instrumentation_begin/end之外调用了可插桩的函数

**被标记的函数**：`arch/riscv/kernel/traps.c`中的`do_page_fault`，第362行调用`handle_page_fault`，最终到达`instrumentable callee`

**调用链**：
- `handle_page_fault`（arch/riscv/mm/fault.c第224行调用``）

**代码**：

```c
  359  asmlinkage __visible noinstr void do_page_fault(struct pt_regs *regs)  {
  360  	irqentry_state_t state = irqentry_enter(regs);
  361  
  362  	handle_page_fault(regs);
  363  
  364  	local_irq_disable();
  365  
  366  	irqentry_exit(regs, state);
  367  }
```

`handle_page_fault`（arch/riscv/mm/fault.c）：

```c
  224  void handle_page_fault(struct pt_regs *regs)  {
  225  	struct task_struct *tsk;
  226  	struct vm_area_struct *vma;
  227  	struct mm_struct *mm;
  228  	unsigned long addr, cause;
  229  	unsigned int flags = FAULT_FLAG_DEFAULT;
  230  	int code = SEGV_MAPERR;
  231  	vm_fault_t fault;
  232  
  233  	cause = regs->cause;
  234  	addr = regs->badaddr;
  235  
  236  	tsk = current;
  237  	mm = tsk->mm;
  238  
  239  	if (kprobe_page_fault(regs, cause))
  240  		return;
  241  
  242  	/*
  243  	 * Fault-in kernel-space virtual memory on-demand.
  244  	 * The 'reference' page table is init_mm.pgd.
  245  	 *
  246  	 * NOTE! We MUST NOT take any locks for this case. We may
  247  	 * be in an interrupt or a critical region, and should
  248  	 * only copy the information from the master page table,
  249  	 * nothing more.
  250  	 */
  251  	if ((!IS_ENABLED(CONFIG_MMU) || !IS_ENABLED(CONFIG_64BIT)) &&
  252  	    unlikely(addr >= VMALLOC_START && addr < VMALLOC_END)) {
  253  		vmalloc_fault(regs, code, addr);
  254  		return;
  255  	}
  256  
  257  	/* Enable interrupts if they were enabled in the parent context. */
  258  	if (!regs_irqs_disabled(regs))
  259  		local_irq_enable();
  260  
  261  	/*
  262  	 * If we're in an interrupt, have no user context, or are running
  263  	 * in an atomic region, then we must not take the fault.
  264  	 */
  265  	if (unlikely(faulthandler_disabled() || !mm)) {
  266  		tsk->thread.bad_cause = cause;
  267  		no_context(regs, addr);
  268  		return;
  269  	}
  270  
  271  	if (user_mode(regs))
  272  		flags |= FAULT_FLAG_USER;
  273  
  274  	if (!user_mode(regs) && addr < TASK_SIZE && unlikely(!(regs->status & SR_SUM))) {
  275  		if (fixup_exception(regs))
  276  			return;
  277  
  278  		die_kernel_fault("access to user memory without uaccess routines", addr, regs);
  279  	}
  280  
  281  	perf_sw_event(PERF_COUNT_SW_PAGE_FAULTS, 1, regs, addr);
  282  
  283  	if (cause == EXC_STORE_PAGE_FAULT)
  284  		flags |= FAULT_FLAG_WRITE;
  285  	else if (cause == EXC_INST_PAGE_FAULT)
  286  		flags |= FAULT_FLAG_INSTRUCTION;
  287  	if (!(flags & FAULT_FLAG_USER))
  288  		goto lock_mmap;
  289  
  290  	vma = lock_vma_under_rcu(mm, addr);
  291  	if (!vma)
  292  		goto lock_mmap;
  293  
  294  	if (unlikely(access_error(cause, vma))) {
  295  		vma_end_read(vma);
  296  		count_vm_vma_lock_event(VMA_LOCK_SUCCESS);
  297  		tsk->thread.bad_cause = cause;
  298  		bad_area_nosemaphore(regs, SEGV_ACCERR, addr);
  299  		return;
  300  	}
  301  
  302  	fault = handle_mm_fault(vma, addr, flags | FAULT_FLAG_VMA_LOCK, regs);
  303  	if (!(fault & (VM_FAULT_RETRY | VM_FAULT_COMPLETED)))
...
```

## K25

**问题种类**：不可插桩约定

**为什么认为这里不能睡眠/需要不可插桩**：本函数标了noinstr，却在instrumentation_begin/end之外调用了可插桩的函数

**被标记的函数**：`arch/riscv/kernel/traps.c`中的`handle_riscv_irq`，第374行调用`irq_enter_rcu`，最终到达`instrumentable callee`

**调用链**：
- `irq_enter_rcu`（kernel/softirq.c第595行调用``）

**代码**：

```c
  371  static void noinstr handle_riscv_irq(struct pt_regs *regs)  {
  372  	struct pt_regs *old_regs;
  373  
  374  	irq_enter_rcu();
  375  	old_regs = set_irq_regs(regs);
  376  	handle_arch_irq(regs);
  377  	set_irq_regs(old_regs);
  378  	irq_exit_rcu();
  379  }
```

`irq_enter_rcu`（kernel/softirq.c）：

```c
  595  void irq_enter_rcu(void)  {
  596  	__irq_enter_raw();
  597  
  598  	if (tick_nohz_full_cpu(smp_processor_id()) ||
  599  	    (is_idle_task(current) && (irq_count() == HARDIRQ_OFFSET)))
  600  		tick_irq_enter();
  601  
  602  	account_hardirq_enter(current);
  603  }
```

## K26

**问题种类**：不可插桩约定

**为什么认为这里不能睡眠/需要不可插桩**：本函数标了noinstr，却在instrumentation_begin/end之外调用了可插桩的函数

**被标记的函数**：`arch/riscv/kernel/traps.c`中的`handle_riscv_irq`，第378行调用`irq_exit_rcu`，最终到达`instrumentable callee`

**调用链**：
- `irq_exit_rcu`（kernel/softirq.c第648行调用``）

**代码**：

```c
  371  static void noinstr handle_riscv_irq(struct pt_regs *regs)  {
  372  	struct pt_regs *old_regs;
  373  
  374  	irq_enter_rcu();
  375  	old_regs = set_irq_regs(regs);
  376  	handle_arch_irq(regs);
  377  	set_irq_regs(old_regs);
  378  	irq_exit_rcu();
  379  }
```

`irq_exit_rcu`（kernel/softirq.c）：

```c
  648  void irq_exit_rcu(void)  {
  649  	__irq_exit_rcu();
  650  	 /* must be last! */
  651  	lockdep_hardirq_exit();
  652  }
```
