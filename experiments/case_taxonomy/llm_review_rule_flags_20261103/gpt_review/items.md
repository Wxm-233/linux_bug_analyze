# 待复核的标记（41条）

## Q_00

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.12）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的RISC-V钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/riscv/kernel/machine_kexec.c中的machine_shutdown

【程序给出的理由】sleep A:irq: line 113 smp_shutdown_nonboot_cpus -> smp_shutdown_nonboot_cpus

【machine_shutdown的代码】
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

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_01

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.12）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的RISC-V钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/riscv/kernel/traps.c中的die

【程序给出的理由】sleep A:spin: line 86 bust_spinlocks -> might_sleep

【调用链】bust_spinlocks（lib/bust_spinlocks.c第25行调用console_unblank） → console_unblank（kernel/printk/printk.c第3345行调用console_lock） → console_lock（kernel/printk/printk.c第2802行调用might_sleep）

【die的代码】
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

【bust_spinlocks的代码（lib/bust_spinlocks.c）】
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

【console_unblank的代码（kernel/printk/printk.c）】
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

【console_lock的代码（kernel/printk/printk.c）】
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

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_02

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.12）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的RISC-V钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/riscv/kernel/traps.c中的do_trap_insn_illegal

【程序给出的理由】rt A:irq: line 184 do_trap_error -> spin_lock_irqsave

【调用链】do_trap_error（arch/riscv/kernel/traps.c第140行调用die） → die（arch/riscv/kernel/traps.c第84行调用spin_lock_irqsave）

【do_trap_insn_illegal的代码】
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

【do_trap_error的代码（arch/riscv/kernel/traps.c）】
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

【die的代码（arch/riscv/kernel/traps.c）】
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

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_03

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.12）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的RISC-V钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/riscv/kernel/traps.c中的do_trap_load_misaligned

【程序给出的理由】sleep B:trap: line 206 handle_misaligned_load -> copy_from_user

【调用链】handle_misaligned_load（arch/riscv/kernel/traps_misaligned.c第418行调用copy_from_user）

【do_trap_load_misaligned的代码】
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

【handle_misaligned_load的代码（arch/riscv/kernel/traps_misaligned.c）】
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
...（其余26行省略）
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_04

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.12）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的RISC-V钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/riscv/kernel/ftrace.c中的__ftrace_modify_code

【程序给出的理由】sleep C:callback: line 144 ftrace_modify_all_code -> cond_resched

【调用链】ftrace_modify_all_code（kernel/trace/ftrace.c第2889行调用ftrace_replace_code） → ftrace_replace_code（kernel/trace/ftrace.c第2741行调用cond_resched）

【__ftrace_modify_code的代码】
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

【ftrace_modify_all_code的代码（kernel/trace/ftrace.c）】
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

【ftrace_replace_code的代码（kernel/trace/ftrace.c）】
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

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_05

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.12）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的RISC-V钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/riscv/kernel/hibernate.c中的swsusp_arch_suspend

【程序给出的理由】sleep D:hook: line 155 flush_tlb_all -> on_each_cpu

【调用链】flush_tlb_all（arch/riscv/mm/tlbflush.c第64行调用on_each_cpu）

【swsusp_arch_suspend的代码】
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

【flush_tlb_all的代码（arch/riscv/mm/tlbflush.c）】
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

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_06

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】默认实现规则：公共代码中的某个默认实现，arm64、x86、LoongArch三个架构都提供了自己的版本，只有RISC-V沿用默认实现。

【被标记的位置】kernel/trace/ftrace.c中的arch_ftrace_update_code

【程序给出的理由】weak default overridden by arm64, x86 and loongarch, not by riscv

【arch_ftrace_update_code的代码】
```c
 2943  void __weak arch_ftrace_update_code(int command)  {
 2944  	ftrace_run_stop_machine(command);
 2945  }
```

【参照：arm64的arch_ftrace_update_code（arch/arm64/kernel/ftrace.c）】
```c
  446  void arch_ftrace_update_code(int command)  {
  447  	command |= FTRACE_MAY_SLEEP;
  448  	ftrace_modify_all_code(command);
  449  }
```

【参照：x86的arch_ftrace_update_code（arch/x86/kernel/ftrace.c）】
```c
  256  void arch_ftrace_update_code(int command)  {
  257  	ftrace_modify_all_code(command);
  258  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_07

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】默认实现规则：公共代码中的某个默认实现，arm64、x86、LoongArch三个架构都提供了自己的版本，只有RISC-V沿用默认实现。

【被标记的位置】include/asm-generic/io.h中的memcpy_fromio

【程序给出的理由】ifndef default overridden by arm64, x86 and loongarch, not by riscv

【memcpy_fromio的代码】
```c
 1183  static inline void memcpy_fromio(void *buffer, 				 const volatile void __iomem *addr, 				 size_t size)  {
 1184  	memcpy(buffer, __io_virt(addr), size);
 1185  }
```

【参照：arm64的memcpy_fromio（arch/arm64/include/asm/io.h）】
```c
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
  160  #define iowrite64be(v,p)	({ __iowmb(); __raw_writeq((__force __u64)cpu_to_be64(v), p); })
```

【参照：x86的memcpy_fromio（arch/x86/include/asm/io.h）】
```c
  208  #define memcpy_fromio memcpy_fromio
  209  #define memcpy_toio memcpy_toio
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
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_08

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】默认实现规则：公共代码中的某个默认实现，arm64、x86、LoongArch三个架构都提供了自己的版本，只有RISC-V沿用默认实现。

【被标记的位置】include/linux/ftrace.h中的ftrace_graph_func

【程序给出的理由】ifndef default overridden by arm64, x86 and loongarch, not by riscv

【ftrace_graph_func的代码】
```c
  907  #ifndef ftrace_graph_func
  908  #define ftrace_graph_func ftrace_stub
  909  #define FTRACE_OPS_GRAPH_STUB FTRACE_OPS_FL_STUB
  910  #else
  911  #define FTRACE_OPS_GRAPH_STUB 0
  912  #endif
  913  #endif /* CONFIG_FUNCTION_GRAPH_TRACER */
  914  
  915  /* totally disable ftrace - can not re-enable after this */
  916  void ftrace_kill(void);
  917  
  918  static inline void tracer_disable(void)
  919  {
  920  #ifdef CONFIG_FUNCTION_TRACER
  921  	ftrace_enabled = 0;
  922  #endif
  923  }
  924  
  925  /*
  926   * Ftrace disable/restore without lock. Some synchronization mechanism
  927   * must be used to prevent ftrace_enabled to be changed between
  928   * disable/restore.
  929   */
  930  static inline int __ftrace_enabled_save(void)
  931  {
  932  #ifdef CONFIG_FUNCTION_TRACER
```

【参照：arm64的ftrace_graph_func（arch/arm64/include/asm/ftrace.h）】
```c
  147  #define ftrace_graph_func ftrace_graph_func
  148  
  149  #ifdef CONFIG_DYNAMIC_FTRACE_WITH_DIRECT_CALLS
  150  static inline void arch_ftrace_set_direct_caller(struct ftrace_regs *fregs,
  151  						 unsigned long addr)
  152  {
  153  	/*
  154  	 * The ftrace trampoline will return to this address instead of the
  155  	 * instrumented function.
  156  	 */
  157  	fregs->direct_tramp = addr;
  158  }
  159  #endif /* CONFIG_DYNAMIC_FTRACE_WITH_DIRECT_CALLS */
  160  
  161  #endif
  162  
  163  #define ftrace_return_address(n) return_address(n)
  164  
  165  /*
  166   * Because AArch32 mode does not share the same syscall table with AArch64,
  167   * tracing compat syscalls may result in reporting bogus syscalls or even
  168   * hang-up, so just do not trace them.
  169   * See kernel/trace/trace_syscalls.c
  170   *
  171   * x86 code says:
  172   * If the user really wants these, then they should use the
```

【参照：x86的ftrace_graph_func（arch/x86/include/asm/ftrace.h）】
```c
   71  #define ftrace_graph_func ftrace_graph_func
   72  void ftrace_graph_func(unsigned long ip, unsigned long parent_ip,
   73  		       struct ftrace_ops *op, struct ftrace_regs *fregs);
   74  #else
   75  #define FTRACE_GRAPH_TRAMP_ADDR FTRACE_GRAPH_ADDR
   76  #endif
   77  
   78  #ifdef CONFIG_DYNAMIC_FTRACE_WITH_DIRECT_CALLS
   79  /*
   80   * When a ftrace registered caller is tracing a function that is
   81   * also set by a register_ftrace_direct() call, it needs to be
   82   * differentiated in the ftrace_caller trampoline. To do this, we
   83   * place the direct caller in the ORIG_AX part of pt_regs. This
   84   * tells the ftrace_caller that there's a direct caller.
   85   */
   86  static inline void
   87  __arch_ftrace_set_direct_caller(struct pt_regs *regs, unsigned long addr)
   88  {
   89  	/* Emulate a call */
   90  	regs->orig_ax = addr;
   91  }
   92  #define arch_ftrace_set_direct_caller(fregs, addr) \
   93  	__arch_ftrace_set_direct_caller(&(fregs)->regs, addr)
   94  #endif /* CONFIG_DYNAMIC_FTRACE_WITH_DIRECT_CALLS */
   95  
   96  #ifdef CONFIG_DYNAMIC_FTRACE
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_09

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】默认实现规则：公共代码中的某个默认实现，arm64、x86、LoongArch三个架构都提供了自己的版本，只有RISC-V沿用默认实现。

【被标记的位置】include/asm-generic/io.h中的memcpy_toio

【程序给出的理由】ifndef default overridden by arm64, x86 and loongarch, not by riscv

【memcpy_toio的代码】
```c
 1200  static inline void memcpy_toio(volatile void __iomem *addr, const void *buffer, 			       size_t size)  {
 1201  	memcpy(__io_virt(addr), buffer, size);
 1202  }
```

【参照：arm64的memcpy_toio（arch/arm64/include/asm/io.h）】
```c
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
  160  #define iowrite64be(v,p)	({ __iowmb(); __raw_writeq((__force __u64)cpu_to_be64(v), p); })
  161  
```

【参照：x86的memcpy_toio（arch/x86/include/asm/io.h）】
```c
  209  #define memcpy_toio memcpy_toio
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
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_10

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】默认实现规则：公共代码中的某个默认实现，arm64、x86、LoongArch三个架构都提供了自己的版本，只有RISC-V沿用默认实现。

【被标记的位置】mm/sparse-vmemmap.c中的vmemmap_set_pmd

【程序给出的理由】weak default overridden by arm64, x86 and loongarch, not by riscv

【vmemmap_set_pmd的代码】
```c
  300  void __weak __meminit vmemmap_set_pmd(pmd_t *pmd, void *p, int node, 				      unsigned long addr, unsigned long next)  {
  301  }
```

【参照：arm64的vmemmap_set_pmd（arch/arm64/mm/mmu.c）】
```c
 1138  void __meminit vmemmap_set_pmd(pmd_t *pmdp, void *p, int node, 			       unsigned long addr, unsigned long next)  {
 1139  	pmd_set_huge(pmdp, __pa(p), __pgprot(PROT_SECT_NORMAL));
 1140  }
```

【参照：x86的vmemmap_set_pmd（arch/x86/mm/init_64.c）】
```c
 1497  void __meminit vmemmap_set_pmd(pmd_t *pmd, void *p, int node, 			       unsigned long addr, unsigned long next)  {
 1498  	pte_t entry;
 1499  
 1500  	entry = pfn_pte(__pa(p) >> PAGE_SHIFT,
 1501  			PAGE_KERNEL_LARGE);
 1502  	set_pmd(pmd, __pmd(pte_val(entry)));
 1503  
 1504  	/* check to see if we have contiguous blocks */
 1505  	if (p_end != p || node_start != node) {
 1506  		if (p_start)
 1507  			pr_debug(" [%lx-%lx] PMD -> [%p-%p] on node %d\n",
 1508  				addr_start, addr_end-1, p_start, p_end-1, node_start);
 1509  		addr_start = addr;
 1510  		node_start = node;
 1511  		p_start = p;
 1512  	}
 1513  
 1514  	addr_end = addr + PMD_SIZE;
 1515  	p_end = p + PMD_SIZE;
 1516  
 1517  	if (!IS_ALIGNED(addr, PMD_SIZE) ||
 1518  		!IS_ALIGNED(next, PMD_SIZE))
 1519  		vmemmap_use_new_sub_pmd(addr, next);
 1520  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_11

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】默认实现规则：公共代码中的某个默认实现，arm64、x86、LoongArch三个架构都提供了自己的版本，只有RISC-V沿用默认实现。

【被标记的位置】include/asm-generic/pci.h中的pcibios_assign_all_busses

【程序给出的理由】ifndef default overridden by arm64, x86 and loongarch, not by riscv

【pcibios_assign_all_busses的代码】
```c
   14  #ifndef pcibios_assign_all_busses
   15  /* For bootloaders that do not initialize the PCI bus */
   16  #define pcibios_assign_all_busses() 1
   17  #endif
   18  
   19  /* Enable generic resource mapping code in drivers/pci/ */
   20  #define ARCH_GENERIC_PCI_MMAP_RESOURCE
   21  
   22  #ifdef CONFIG_PCI_DOMAINS
   23  static inline int pci_proc_domain(struct pci_bus *bus)
   24  {
   25  	/* always show the domain in /proc */
   26  	return 1;
   27  }
   28  #endif /* CONFIG_PCI_DOMAINS */
   29  
   30  #endif /* __ASM_GENERIC_PCI_H */
```

【参照：arm64的pcibios_assign_all_busses（arch/arm64/include/asm/pci.h）】
```c
   16  #define pcibios_assign_all_busses() \
   17  	(pci_has_flag(PCI_REASSIGN_ALL_BUS))
   18  
   19  #define arch_can_pci_mmap_wc() 1
   20  
   21  /* Generic PCI */
   22  #include <asm-generic/pci.h>
   23  
   24  #endif  /* __ASM_PCI_H */
```

【参照：x86的pcibios_assign_all_busses（arch/x86/include/asm/pci.h）】
```c
（未取到）
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_12

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】默认实现规则：公共代码中的某个默认实现，arm64、x86、LoongArch三个架构都提供了自己的版本，只有RISC-V沿用默认实现。

【被标记的位置】include/asm-generic/io.h中的ioremap_wc

【程序给出的理由】ifndef default overridden by arm64, x86 and loongarch, not by riscv

【ioremap_wc的代码】
```c
 1068  #ifndef ioremap_wc
 1069  #define ioremap_wc ioremap
 1070  #endif
 1071  
 1072  #ifndef ioremap_wt
 1073  #define ioremap_wt ioremap
 1074  #endif
 1075  
 1076  /*
 1077   * ioremap_uc is special in that we do require an explicit architecture
 1078   * implementation.  In general you do not want to use this function in a
 1079   * driver and use plain ioremap, which is uncached by default.  Similarly
 1080   * architectures should not implement it unless they have a very good
 1081   * reason.
 1082   */
 1083  #ifndef ioremap_uc
 1084  #define ioremap_uc ioremap_uc
 1085  static inline void __iomem *ioremap_uc(phys_addr_t offset, size_t size)
 1086  {
 1087  	return NULL;
 1088  }
 1089  #endif
 1090  
 1091  /*
 1092   * ioremap_np needs an explicit architecture implementation, as it
 1093   * requests stronger semantics than regular ioremap(). Portable drivers
```

【参照：arm64的ioremap_wc（arch/arm64/include/asm/io.h）】
```c
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
  160  #define iowrite64be(v,p)	({ __iowmb(); __raw_writeq((__force __u64)cpu_to_be64(v), p); })
  161  
  162  #include <asm-generic/io.h>
  163  
  164  #define ioremap_cache ioremap_cache
  165  static inline void __iomem *ioremap_cache(phys_addr_t addr, size_t size)
  166  {
  167  	if (pfn_is_map_memory(__phys_to_pfn(addr)))
  168  		return (void __iomem *)__phys_to_virt(addr);
  169  
  170  	return ioremap_prot(addr, size, PROT_NORMAL);
  171  }
```

【参照：x86的ioremap_wc（arch/x86/include/asm/io.h）】
```c
  319  #define ioremap_wc ioremap_wc
  320  extern void __iomem *ioremap_wt(resource_size_t offset, unsigned long size);
  321  #define ioremap_wt ioremap_wt
  322  
  323  extern bool is_early_ioremap_ptep(pte_t *ptep);
  324  
  325  #define IO_SPACE_LIMIT 0xffff
  326  
  327  #include <asm-generic/io.h>
  328  #undef PCI_IOBASE
  329  
  330  #ifdef CONFIG_MTRR
  331  extern int __must_check arch_phys_wc_index(int handle);
  332  #define arch_phys_wc_index arch_phys_wc_index
  333  
  334  extern int __must_check arch_phys_wc_add(unsigned long base,
  335  					 unsigned long size);
  336  extern void arch_phys_wc_del(int handle);
  337  #define arch_phys_wc_add arch_phys_wc_add
  338  #endif
  339  
  340  #ifdef CONFIG_X86_PAT
  341  extern int arch_io_reserve_memtype_wc(resource_size_t start, resource_size_t size);
  342  extern void arch_io_free_memtype_wc(resource_size_t start, resource_size_t size);
  343  #define arch_io_reserve_memtype_wc arch_io_reserve_memtype_wc
  344  #endif
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_13

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】默认实现规则：公共代码中的某个默认实现，arm64、x86、LoongArch三个架构都提供了自己的版本，只有RISC-V沿用默认实现。

【被标记的位置】mm/sparse-vmemmap.c中的vmemmap_check_pmd

【程序给出的理由】weak default overridden by arm64, x86 and loongarch, not by riscv

【vmemmap_check_pmd的代码】
```c
  305  int __weak __meminit vmemmap_check_pmd(pmd_t *pmd, int node, 				       unsigned long addr, unsigned long next)  {
  306  	return 0;
  307  }
```

【参照：arm64的vmemmap_check_pmd（arch/arm64/mm/mmu.c）】
```c
 1144  int __meminit vmemmap_check_pmd(pmd_t *pmdp, int node, 				unsigned long addr, unsigned long next)  {
 1145  	vmemmap_verify((pte_t *)pmdp, node, addr, next);
 1146  	return 1;
 1147  }
```

【参照：x86的vmemmap_check_pmd（arch/x86/mm/init_64.c）】
```c
 1524  int __meminit vmemmap_check_pmd(pmd_t *pmd, int node, 				unsigned long addr, unsigned long next)  {
 1525  	int large = pmd_large(*pmd);
 1526  
 1527  	if (pmd_large(*pmd)) {
 1528  		vmemmap_verify((pte_t *)pmd, node, addr, next);
 1529  		vmemmap_use_sub_pmd(addr, next);
 1530  	}
 1531  
 1532  	return large;
 1533  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_14

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】默认实现规则：公共代码中的某个默认实现，arm64、x86、LoongArch三个架构都提供了自己的版本，只有RISC-V沿用默认实现。

【被标记的位置】include/asm-generic/mmu_context.h中的enter_lazy_tlb

【程序给出的理由】ifndef default overridden by arm64, x86 and loongarch, not by riscv

【enter_lazy_tlb的代码】
```c
   23  static inline void enter_lazy_tlb(struct mm_struct *mm, 			struct task_struct *tsk)  {
   24  }
```

【参照：arm64的enter_lazy_tlb（arch/arm64/include/asm/mmu_context.h）】
```c
  238  static inline void enter_lazy_tlb(struct mm_struct *mm, struct task_struct *tsk)  {
  239  	/*
  240  	 * We don't actually care about the ttbr0 mapping, so point it at the
  241  	 * zero page.
  242  	 */
  243  	update_saved_ttbr0(tsk, &init_mm);
  244  }
```

【参照：x86的enter_lazy_tlb（arch/x86/include/asm/mmu_context.h）】
```c
  133  #define enter_lazy_tlb enter_lazy_tlb
  134  extern void enter_lazy_tlb(struct mm_struct *mm, struct task_struct *tsk);
  135  
  136  /*
  137   * Init a new mm.  Used on mm copies, like at fork()
  138   * and on mm's that are brand-new, like at execve().
  139   */
  140  #define init_new_context init_new_context
  141  static inline int init_new_context(struct task_struct *tsk,
  142  				   struct mm_struct *mm)
  143  {
  144  	mutex_init(&mm->context.lock);
  145  
  146  	mm->context.ctx_id = atomic64_inc_return(&last_mm_ctx_id);
  147  	atomic64_set(&mm->context.tlb_gen, 0);
  148  
  149  #ifdef CONFIG_X86_INTEL_MEMORY_PROTECTION_KEYS
  150  	if (cpu_feature_enabled(X86_FEATURE_OSPKE)) {
  151  		/* pkey 0 is the default and allocated implicitly */
  152  		mm->context.pkey_allocation_map = 0x1;
  153  		/* -1 means unallocated or invalid */
  154  		mm->context.execute_only_pkey = -1;
  155  	}
  156  #endif
  157  	mm_reset_untag_mask(mm);
  158  	init_new_context_ldt(mm);
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_15

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】推测执行越界规则：函数对一个可能来自客体（虚拟机）或用户的下标做了上界检查，随后用它访问数组，却没有用array_index_nospec，可能被推测执行越界利用（Spectre-v1）。

【被标记的位置】arch/riscv/kvm/aia_aplic.c中的aplic_write_target

【程序给出的理由】line 100: [irq] after bound check at line 98, no array_index_nospec

【aplic_write_target的代码】
```c
   94  static void aplic_write_target(struct aplic *aplic, u32 irq, u32 val)  {
   95  	unsigned long flags;
   96  	struct aplic_irq *irqd;
   97  
   98  	if (!irq || aplic->nr_irqs <= irq)
   99  		return;
  100  	irqd = &aplic->irqs[irq];
  101  
  102  	val &= APLIC_TARGET_EIID_MASK |
  103  	       (APLIC_TARGET_HART_IDX_MASK << APLIC_TARGET_HART_IDX_SHIFT) |
  104  	       (APLIC_TARGET_GUEST_IDX_MASK << APLIC_TARGET_GUEST_IDX_SHIFT);
  105  
  106  	raw_spin_lock_irqsave(&irqd->lock, flags);
  107  	irqd->target = val;
  108  	raw_spin_unlock_irqrestore(&irqd->lock, flags);
  109  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_16

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】推测执行越界规则：函数对一个可能来自客体（虚拟机）或用户的下标做了上界检查，随后用它访问数组，却没有用array_index_nospec，可能被推测执行越界利用（Spectre-v1）。

【被标记的位置】arch/riscv/kvm/vcpu_pmu.c中的kvm_riscv_vcpu_pmu_incr_fw

【程序给出的理由】line 271: [fid] after bound check at line 268, no array_index_nospec

【kvm_riscv_vcpu_pmu_incr_fw的代码】
```c
  264  int kvm_riscv_vcpu_pmu_incr_fw(struct kvm_vcpu *vcpu, unsigned long fid)  {
  265  	struct kvm_pmu *kvpmu = vcpu_to_pmu(vcpu);
  266  	struct kvm_fw_event *fevent;
  267  
  268  	if (!kvpmu || fid >= SBI_PMU_FW_MAX)
  269  		return -EINVAL;
  270  
  271  	fevent = &kvpmu->fw_event[fid];
  272  	if (fevent->started)
  273  		fevent->value++;
  274  
  275  	return 0;
  276  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_17

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】推测执行越界规则：函数对一个可能来自客体（虚拟机）或用户的下标做了上界检查，随后用它访问数组，却没有用array_index_nospec，可能被推测执行越界利用（Spectre-v1）。

【被标记的位置】arch/riscv/kvm/vcpu_pmu.c中的kvm_riscv_vcpu_pmu_ctr_cfg_match

【程序给出的理由】line 512: [ctr_idx] after bound check at line 506, no array_index_nospec; line 517: [event_code] after bound check at line 489, no array_index_nospec

【kvm_riscv_vcpu_pmu_ctr_cfg_match的代码】
```c
  460  int kvm_riscv_vcpu_pmu_ctr_cfg_match(struct kvm_vcpu *vcpu, unsigned long ctr_base, 				     unsigned long ctr_mask, unsigned long flags, 				     unsigned long eidx, u64 evtdata, 				     struct kvm_vcpu_sbi_return *retdata)  {
  461  	int ctr_idx, ret, sbiret = 0;
  462  	bool is_fevent;
  463  	unsigned long event_code;
  464  	u32 etype = kvm_pmu_get_perf_event_type(eidx);
  465  	struct kvm_pmu *kvpmu = vcpu_to_pmu(vcpu);
  466  	struct kvm_pmc *pmc = NULL;
  467  	struct perf_event_attr attr = {
  468  		.type = etype,
  469  		.size = sizeof(struct perf_event_attr),
  470  		.pinned = true,
  471  		/*
  472  		 * It should never reach here if the platform doesn't support the sscofpmf
  473  		 * extension as mode filtering won't work without it.
  474  		 */
  475  		.exclude_host = true,
  476  		.exclude_hv = true,
  477  		.exclude_user = !!(flags & SBI_PMU_CFG_FLAG_SET_UINH),
  478  		.exclude_kernel = !!(flags & SBI_PMU_CFG_FLAG_SET_SINH),
  479  		.config1 = RISCV_PMU_CONFIG1_GUEST_EVENTS,
  480  	};
  481  
  482  	if (kvm_pmu_validate_counter_mask(kvpmu, ctr_base, ctr_mask) < 0) {
  483  		sbiret = SBI_ERR_INVALID_PARAM;
  484  		goto out;
  485  	}
  486  
  487  	event_code = get_event_code(eidx);
  488  	is_fevent = kvm_pmu_is_fw_event(eidx);
  489  	if (is_fevent && event_code >= SBI_PMU_FW_MAX) {
  490  		sbiret = SBI_ERR_NOT_SUPPORTED;
  491  		goto out;
  492  	}
  493  
  494  	/*
  495  	 * SKIP_MATCH flag indicates the caller is aware of the assigned counter
  496  	 * for this event. Just do a sanity check if it already marked used.
  497  	 */
  498  	if (flags & SBI_PMU_CFG_FLAG_SKIP_MATCH) {
  499  		if (!test_bit(ctr_base + __ffs(ctr_mask), kvpmu->pmc_in_use)) {
  500  			sbiret = SBI_ERR_FAILURE;
  501  			goto out;
  502  		}
  503  		ctr_idx = ctr_base + __ffs(ctr_mask);
  504  	} else  {
  505  		ctr_idx = pmu_get_pmc_index(kvpmu, eidx, ctr_base, ctr_mask);
  506  		if (ctr_idx < 0) {
  507  			sbiret = SBI_ERR_NOT_SUPPORTED;
  508  			goto out;
  509  		}
  510  	}
  511  
  512  	pmc = &kvpmu->pmc[ctr_idx];
  513  	pmc->idx = ctr_idx;
  514  
  515  	if (is_fevent) {
  516  		if (flags & SBI_PMU_CFG_FLAG_AUTO_START)
  517  			kvpmu->fw_event[event_code].started = true;
  518  	} else {
  519  		ret = kvm_pmu_create_perf_event(pmc, &attr, flags, eidx, evtdata);
  520  		if (ret)
  521  			return ret;
  522  	}
  523  
  524  	set_bit(ctr_idx, kvpmu->pmc_in_use);
  525  	pmc->event_idx = eidx;
  526  	retdata->out_val = ctr_idx;
  527  out:
  528  	retdata->err_val = sbiret;
  529  
  530  	return 0;
  531  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_18

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】推测执行越界规则：函数对一个可能来自客体（虚拟机）或用户的下标做了上界检查，随后用它访问数组，却没有用array_index_nospec，可能被推测执行越界利用（Spectre-v1）。

【被标记的位置】arch/riscv/kvm/aia_aplic.c中的aplic_read_input

【程序给出的理由】line 196: [irq] after bound check at line 194, no array_index_nospec

【aplic_read_input的代码】
```c
  189  static bool aplic_read_input(struct aplic *aplic, u32 irq)  {
  190  	bool ret;
  191  	unsigned long flags;
  192  	struct aplic_irq *irqd;
  193  
  194  	if (!irq || aplic->nr_irqs <= irq)
  195  		return false;
  196  	irqd = &aplic->irqs[irq];
  197  
  198  	raw_spin_lock_irqsave(&irqd->lock, flags);
  199  	ret = (irqd->state & APLIC_IRQ_STATE_INPUT) ? true : false;
  200  	raw_spin_unlock_irqrestore(&irqd->lock, flags);
  201  
  202  	return ret;
  203  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_19

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】推测执行越界规则：函数对一个可能来自客体（虚拟机）或用户的下标做了上界检查，随后用它访问数组，却没有用array_index_nospec，可能被推测执行越界利用（Spectre-v1）。

【被标记的位置】arch/riscv/kvm/aia_aplic.c中的aplic_read_target

【程序给出的理由】line 84: [irq] after bound check at line 82, no array_index_nospec

【aplic_read_target的代码】
```c
   77  static u32 aplic_read_target(struct aplic *aplic, u32 irq)  {
   78  	u32 ret;
   79  	unsigned long flags;
   80  	struct aplic_irq *irqd;
   81  
   82  	if (!irq || aplic->nr_irqs <= irq)
   83  		return 0;
   84  	irqd = &aplic->irqs[irq];
   85  
   86  	raw_spin_lock_irqsave(&irqd->lock, flags);
   87  	ret = irqd->target;
   88  	raw_spin_unlock_irqrestore(&irqd->lock, flags);
   89  
   90  	return ret;
   91  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_20

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】推测执行越界规则：函数对一个可能来自客体（虚拟机）或用户的下标做了上界检查，随后用它访问数组，却没有用array_index_nospec，可能被推测执行越界利用（Spectre-v1）。

【被标记的位置】arch/riscv/kvm/vcpu_pmu.c中的kvm_riscv_vcpu_pmu_ctr_stop

【程序给出的理由】line 422: [fevent_code] after bound check at line 417, no array_index_nospec; line 425: [fevent_code] after bound check at line 417, no array_index_nospec

【kvm_riscv_vcpu_pmu_ctr_stop的代码】
```c
  397  int kvm_riscv_vcpu_pmu_ctr_stop(struct kvm_vcpu *vcpu, unsigned long ctr_base, 				unsigned long ctr_mask, unsigned long flags, 				struct kvm_vcpu_sbi_return *retdata)  {
  398  	struct kvm_pmu *kvpmu = vcpu_to_pmu(vcpu);
  399  	int i, pmc_index, sbiret = 0;
  400  	u64 enabled, running;
  401  	struct kvm_pmc *pmc;
  402  	int fevent_code;
  403  
  404  	if (kvm_pmu_validate_counter_mask(kvpmu, ctr_base, ctr_mask) < 0) {
  405  		sbiret = SBI_ERR_INVALID_PARAM;
  406  		goto out;
  407  	}
  408  
  409  	/* Stop the counters that have been configured and requested by the guest */
  410  	for_each_set_bit(i, &ctr_mask, RISCV_MAX_COUNTERS) {
  411  		pmc_index = i + ctr_base;
  412  		if (!test_bit(pmc_index, kvpmu->pmc_in_use))
  413  			continue;
  414  		pmc = &kvpmu->pmc[pmc_index];
  415  		if (pmc->cinfo.type == SBI_PMU_CTR_TYPE_FW) {
  416  			fevent_code = get_event_code(pmc->event_idx);
  417  			if (fevent_code >= SBI_PMU_FW_MAX) {
  418  				sbiret = SBI_ERR_INVALID_PARAM;
  419  				goto out;
  420  			}
  421  
  422  			if (!kvpmu->fw_event[fevent_code].started)
  423  				sbiret = SBI_ERR_ALREADY_STOPPED;
  424  
  425  			kvpmu->fw_event[fevent_code].started = false;
  426  		} else if (pmc->perf_event) {
  427  			if (pmc->started) {
  428  				/* Stop counting the counter */
  429  				perf_event_disable(pmc->perf_event);
  430  				pmc->started = false;
  431  			} else {
  432  				sbiret = SBI_ERR_ALREADY_STOPPED;
  433  			}
  434  
  435  			if (flags & SBI_PMU_STOP_FLAG_RESET) {
  436  				/* Relase the counter if this is a reset request */
  437  				pmc->counter_val += perf_event_read_value(pmc->perf_event,
  438  									  &enabled, &running);
  439  				kvm_pmu_release_perf_event(pmc);
  440  			}
  441  		} else {
  442  			sbiret = SBI_ERR_INVALID_PARAM;
  443  		}
  444  		if (flags & SBI_PMU_STOP_FLAG_RESET) {
  445  			pmc->event_idx = SBI_PMU_EVENT_IDX_INVALID;
  446  			clear_bit(pmc_index, kvpmu->pmc_in_use);
  447  		}
  448  	}
  449  
  450  out:
  451  	retdata->err_val = sbiret;
  452  
  453  	return 0;
  454  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_21

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】推测执行越界规则：函数对一个可能来自客体（虚拟机）或用户的下标做了上界检查，随后用它访问数组，却没有用array_index_nospec，可能被推测执行越界利用（Spectre-v1）。

【被标记的位置】arch/riscv/kvm/aia_aplic.c中的aplic_write_enabled

【程序给出的理由】line 178: [irq] after bound check at line 176, no array_index_nospec

【aplic_write_enabled的代码】
```c
  172  static void aplic_write_enabled(struct aplic *aplic, u32 irq, bool enabled)  {
  173  	unsigned long flags;
  174  	struct aplic_irq *irqd;
  175  
  176  	if (!irq || aplic->nr_irqs <= irq)
  177  		return;
  178  	irqd = &aplic->irqs[irq];
  179  
  180  	raw_spin_lock_irqsave(&irqd->lock, flags);
  181  	if (enabled)
  182  		irqd->state |= APLIC_IRQ_STATE_ENABLED;
  183  	else
  184  		irqd->state &= ~APLIC_IRQ_STATE_ENABLED;
  185  	raw_spin_unlock_irqrestore(&irqd->lock, flags);
  186  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_22

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】推测执行越界规则：函数对一个可能来自客体（虚拟机）或用户的下标做了上界检查，随后用它访问数组，却没有用array_index_nospec，可能被推测执行越界利用（Spectre-v1）。

【被标记的位置】arch/riscv/kvm/aia_aplic.c中的aplic_write_sourcecfg

【程序给出的理由】line 64: [irq] after bound check at line 62, no array_index_nospec

【aplic_write_sourcecfg的代码】
```c
   58  static void aplic_write_sourcecfg(struct aplic *aplic, u32 irq, u32 val)  {
   59  	unsigned long flags;
   60  	struct aplic_irq *irqd;
   61  
   62  	if (!irq || aplic->nr_irqs <= irq)
   63  		return;
   64  	irqd = &aplic->irqs[irq];
   65  
   66  	if (val & APLIC_SOURCECFG_D)
   67  		val = 0;
   68  	else
   69  		val &= APLIC_SOURCECFG_SM_MASK;
   70  
   71  	raw_spin_lock_irqsave(&irqd->lock, flags);
   72  	irqd->sourcecfg = val;
   73  	raw_spin_unlock_irqrestore(&irqd->lock, flags);
   74  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_23

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】推测执行越界规则：函数对一个可能来自客体（虚拟机）或用户的下标做了上界检查，随后用它访问数组，却没有用array_index_nospec，可能被推测执行越界利用（Spectre-v1）。

【被标记的位置】arch/riscv/kernel/kgdb.c中的dbg_set_reg

【程序给出的理由】line 225: [regno] after bound check at line 222, no array_index_nospec; line 226: [regno] after bound check at line 222, no array_index_nospec; line 227: [regno] after bound check at line 222, no array_index_nospec

【dbg_set_reg的代码】
```c
  221  int dbg_set_reg(int regno, void *mem, struct pt_regs *regs)  {
  222  	if (regno >= DBG_MAX_REG_NUM || regno < 0)
  223  		return -EINVAL;
  224  
  225  	if (dbg_reg_def[regno].offset != -1)
  226  		memcpy((void *)regs + dbg_reg_def[regno].offset, mem,
  227  		       dbg_reg_def[regno].size);
  228  	return 0;
  229  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_24

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】推测执行越界规则：函数对一个可能来自客体（虚拟机）或用户的下标做了上界检查，随后用它访问数组，却没有用array_index_nospec，可能被推测执行越界利用（Spectre-v1）。

【被标记的位置】arch/riscv/kvm/vcpu_onereg.c中的riscv_vcpu_set_isa_ext_single

【程序给出的理由】line 484: [reg_num] after bound check at line 480, no array_index_nospec

【riscv_vcpu_set_isa_ext_single的代码】
```c
  477  static int riscv_vcpu_set_isa_ext_single(struct kvm_vcpu *vcpu, 					 unsigned long reg_num, 					 unsigned long reg_val)  {
  478  	unsigned long host_isa_ext;
  479  
  480  	if (reg_num >= KVM_RISCV_ISA_EXT_MAX ||
  481  	    reg_num >= ARRAY_SIZE(kvm_isa_ext_arr))
  482  		return -ENOENT;
  483  
  484  	host_isa_ext = kvm_isa_ext_arr[reg_num];
  485  	if (!__riscv_isa_extension_available(NULL, host_isa_ext))
  486  		return -ENOENT;
  487  
  488  	if (reg_val == test_bit(host_isa_ext, vcpu->arch.isa))
  489  		return 0;
  490  
  491  	if (!vcpu->arch.ran_atleast_once) {
  492  		/*
  493  		 * All multi-letter extension and a few single letter
  494  		 * extension can be disabled
  495  		 */
  496  		if (reg_val == 1 &&
  497  		    kvm_riscv_vcpu_isa_enable_allowed(reg_num))
  498  			set_bit(host_isa_ext, vcpu->arch.isa);
  499  		else if (!reg_val &&
  500  			 kvm_riscv_vcpu_isa_disable_allowed(reg_num))
  501  			clear_bit(host_isa_ext, vcpu->arch.isa);
  502  		else
  503  			return -EINVAL;
  504  		kvm_riscv_vcpu_fp_reset(vcpu);
  505  	} else {
  506  		return -EBUSY;
  507  	}
  508  
  509  	return 0;
  510  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_25

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】推测执行越界规则：函数对一个可能来自客体（虚拟机）或用户的下标做了上界检查，随后用它访问数组，却没有用array_index_nospec，可能被推测执行越界利用（Spectre-v1）。

【被标记的位置】arch/riscv/kvm/vcpu_pmu.c中的kvm_riscv_vcpu_pmu_ctr_start

【程序给出的理由】line 368: [fevent_code] after bound check at line 362, no array_index_nospec; line 373: [fevent_code] after bound check at line 362, no array_index_nospec; line 374: [fevent_code] after bound check at line 362, no array_index_nospec

【kvm_riscv_vcpu_pmu_ctr_start的代码】
```c
  341  int kvm_riscv_vcpu_pmu_ctr_start(struct kvm_vcpu *vcpu, unsigned long ctr_base, 				 unsigned long ctr_mask, unsigned long flags, u64 ival, 				 struct kvm_vcpu_sbi_return *retdata)  {
  342  	struct kvm_pmu *kvpmu = vcpu_to_pmu(vcpu);
  343  	int i, pmc_index, sbiret = 0;
  344  	struct kvm_pmc *pmc;
  345  	int fevent_code;
  346  
  347  	if (kvm_pmu_validate_counter_mask(kvpmu, ctr_base, ctr_mask) < 0) {
  348  		sbiret = SBI_ERR_INVALID_PARAM;
  349  		goto out;
  350  	}
  351  
  352  	/* Start the counters that have been configured and requested by the guest */
  353  	for_each_set_bit(i, &ctr_mask, RISCV_MAX_COUNTERS) {
  354  		pmc_index = i + ctr_base;
  355  		if (!test_bit(pmc_index, kvpmu->pmc_in_use))
  356  			continue;
  357  		pmc = &kvpmu->pmc[pmc_index];
  358  		if (flags & SBI_PMU_START_FLAG_SET_INIT_VALUE)
  359  			pmc->counter_val = ival;
  360  		if (pmc->cinfo.type == SBI_PMU_CTR_TYPE_FW) {
  361  			fevent_code = get_event_code(pmc->event_idx);
  362  			if (fevent_code >= SBI_PMU_FW_MAX) {
  363  				sbiret = SBI_ERR_INVALID_PARAM;
  364  				goto out;
  365  			}
  366  
  367  			/* Check if the counter was already started for some reason */
  368  			if (kvpmu->fw_event[fevent_code].started) {
  369  				sbiret = SBI_ERR_ALREADY_STARTED;
  370  				continue;
  371  			}
  372  
  373  			kvpmu->fw_event[fevent_code].started = true;
  374  			kvpmu->fw_event[fevent_code].value = pmc->counter_val;
  375  		} else if (pmc->perf_event) {
  376  			if (unlikely(pmc->started)) {
  377  				sbiret = SBI_ERR_ALREADY_STARTED;
  378  				continue;
  379  			}
  380  			perf_event_period(pmc->perf_event, kvm_pmu_get_sample_period(pmc));
  381  			perf_event_enable(pmc->perf_event);
  382  			pmc->started = true;
  383  		} else {
  384  			sbiret = SBI_ERR_INVALID_PARAM;
  385  		}
  386  	}
  387  
  388  out:
  389  	retdata->err_val = sbiret;
  390  
  391  	return 0;
  392  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_26

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】推测执行越界规则：函数对一个可能来自客体（虚拟机）或用户的下标做了上界检查，随后用它访问数组，却没有用array_index_nospec，可能被推测执行越界利用（Spectre-v1）。

【被标记的位置】arch/riscv/kvm/aia_aplic.c中的aplic_read_enabled

【程序给出的理由】line 162: [irq] after bound check at line 160, no array_index_nospec

【aplic_read_enabled的代码】
```c
  155  static bool aplic_read_enabled(struct aplic *aplic, u32 irq)  {
  156  	bool ret;
  157  	unsigned long flags;
  158  	struct aplic_irq *irqd;
  159  
  160  	if (!irq || aplic->nr_irqs <= irq)
  161  		return false;
  162  	irqd = &aplic->irqs[irq];
  163  
  164  	raw_spin_lock_irqsave(&irqd->lock, flags);
  165  	ret = (irqd->state & APLIC_IRQ_STATE_ENABLED) ? true : false;
  166  	raw_spin_unlock_irqrestore(&irqd->lock, flags);
  167  
  168  	return ret;
  169  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_27

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】参照修掉的写法规则：参照架构的某次修复删掉了一行写法，RISC-V的同名函数里还保留着完全相同的一行。

【被标记的位置】arch/riscv/kvm/mmu.c中的kvm_age_gfn

【程序给出的理由】df6556adf27b in arch/arm64/kvm/mmu.c removed "WARN_ON(size != PAGE_SIZE && size != PMD_SIZE && size != PUD_SIZE);", still in riscv; added ['kvm_pgtable_stage2_test_clear_young', 'mmu', 'pgt']

【kvm_age_gfn的代码】
```c
  574  bool kvm_age_gfn(struct kvm *kvm, struct kvm_gfn_range *range)  {
  575  	pte_t *ptep;
  576  	u32 ptep_level = 0;
  577  	u64 size = (range->end - range->start) << PAGE_SHIFT;
  578  
  579  	if (!kvm->arch.pgd)
  580  		return false;
  581  
  582  	WARN_ON(size != PAGE_SIZE && size != PMD_SIZE && size != PUD_SIZE);
  583  
  584  	if (!gstage_get_leaf_entry(kvm, range->start << PAGE_SHIFT,
  585  				   &ptep, &ptep_level))
  586  		return false;
  587  
  588  	return ptep_test_and_clear_young(NULL, 0, ptep);
  589  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_28

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】参照修掉的写法规则：参照架构的某次修复删掉了一行写法，RISC-V的同名函数里还保留着完全相同的一行。

【被标记的位置】arch/riscv/net/bpf_jit_core.c中的bpf_jit_alloc_exec

【程序给出的理由】b89ddf4cca43 in arch/arm64/net/bpf_jit_comp.c removed "return __vmalloc_node_range(size, PAGE_SIZE, BPF_JIT_REGION_START,", still in riscv; added ['vmalloc']

【bpf_jit_alloc_exec的代码】
```c
  222  void *bpf_jit_alloc_exec(unsigned long size)  {
  223  	return __vmalloc_node_range(size, PAGE_SIZE, BPF_JIT_REGION_START,
  224  				    BPF_JIT_REGION_END, GFP_KERNEL,
  225  				    PAGE_KERNEL, 0, NUMA_NO_NODE,
  226  				    __builtin_return_address(0));
  227  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_29

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】同一约定规则：公共代码调用、各架构各自实现的函数中，arm64、x86、LoongArch三个实现都调用了某个函数，RISC-V的实现没有。

【被标记的位置】arch/riscv/kernel/acpi.c中的__acpi_map_table

【程序给出的理由】all three references call ['early_memremap'], riscv does not

【__acpi_map_table的代码】
```c
  203  void __init __iomem *__acpi_map_table(unsigned long phys, unsigned long size)  {
  204  	if (!size)
  205  		return NULL;
  206  
  207  	return early_ioremap(phys, size);
  208  }
```

【参照：arm64的__acpi_map_table（arch/arm64/kernel/acpi.c）】
```c
   90  void __init __iomem *__acpi_map_table(unsigned long phys, unsigned long size)  {
   91  	if (!size)
   92  		return NULL;
   93  
   94  	return early_memremap(phys, size);
   95  }
```

【参照：x86的__acpi_map_table（arch/x86/kernel/acpi/boot.c）】
```c
  115  void __init __iomem *__acpi_map_table(unsigned long phys, unsigned long size)  {
  116  
  117  	if (!phys || !size)
  118  		return NULL;
  119  
  120  	return early_memremap(phys, size);
  121  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_30

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】同一约定规则：公共代码调用、各架构各自实现的函数中，arm64、x86、LoongArch三个实现都调用了某个函数，RISC-V的实现没有。

【被标记的位置】arch/riscv/kernel/acpi.c中的__acpi_unmap_table

【程序给出的理由】all three references call ['early_memunmap'], riscv does not

【__acpi_unmap_table的代码】
```c
  211  void __init __acpi_unmap_table(void __iomem *map, unsigned long size)  {
  212  	if (!map || !size)
  213  		return;
  214  
  215  	early_iounmap(map, size);
  216  }
```

【参照：arm64的__acpi_unmap_table（arch/arm64/kernel/acpi.c）】
```c
   98  void __init __acpi_unmap_table(void __iomem *map, unsigned long size)  {
   99  	if (!map || !size)
  100  		return;
  101  
  102  	early_memunmap(map, size);
  103  }
```

【参照：x86的__acpi_unmap_table（arch/x86/kernel/acpi/boot.c）】
```c
  124  void __init __acpi_unmap_table(void __iomem *map, unsigned long size)  {
  125  	if (!map || !size)
  126  		return;
  127  
  128  	early_memunmap(map, size);
  129  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_31

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】同一约定规则：公共代码调用、各架构各自实现的函数中，arm64、x86、LoongArch三个实现都调用了某个函数，RISC-V的实现没有。

【被标记的位置】arch/riscv/kernel/process.c中的flush_thread

【程序给出的理由】all three references call ['flush_ptrace_hw_breakpoint'], riscv does not

【flush_thread的代码】
```c
  140  void flush_thread(void)  {
  141  #ifdef CONFIG_FPU
  142  	/*
  143  	 * Reset FPU state and context
  144  	 *	frm: round to nearest, ties to even (IEEE default)
  145  	 *	fflags: accrued exceptions cleared
  146  	 */
  147  	fstate_off(current, task_pt_regs(current));
  148  	memset(&current->thread.fstate, 0, sizeof(current->thread.fstate));
  149  #endif
  150  #ifdef CONFIG_RISCV_ISA_V
  151  	/* Reset vector state */
  152  	riscv_v_vstate_ctrl_init(current);
  153  	riscv_v_vstate_off(task_pt_regs(current));
  154  	kfree(current->thread.vstate.datap);
  155  	memset(&current->thread.vstate, 0, sizeof(struct __riscv_v_ext_state));
  156  #endif
  157  }
```

【参照：arm64的flush_thread（arch/arm64/kernel/process.c）】
```c
  275  void flush_thread(void)  {
  276  	fpsimd_flush_thread();
  277  	tls_thread_flush();
  278  	flush_ptrace_hw_breakpoint(current);
  279  	flush_tagged_addr_state();
  280  }
```

【参照：x86的flush_thread（arch/x86/kernel/process.c）】
```c
  273  void flush_thread(void)  {
  274  	struct task_struct *tsk = current;
  275  
  276  	flush_ptrace_hw_breakpoint(tsk);
  277  	memset(tsk->thread.tls_array, 0, sizeof(tsk->thread.tls_array));
  278  
  279  	fpu_flush_thread();
  280  	pkru_flush_thread();
  281  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_32

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】同一约定规则：公共代码调用、各架构各自实现的函数中，arm64、x86、LoongArch三个实现都调用了某个函数，RISC-V的实现没有。

【被标记的位置】arch/riscv/kernel/acpi.c中的pci_acpi_scan_root

【程序给出的理由】all three references call ['acpi_pci_root_create', 'pcie_bus_configure_settings'], riscv does not

【pci_acpi_scan_root的代码】
```c
  248  struct pci_bus *pci_acpi_scan_root(struct acpi_pci_root *root)  {
  249  	return NULL;
  250  }
```

【参照：arm64的pci_acpi_scan_root（arch/arm64/kernel/pci.c）】
```c
  176  struct pci_bus *pci_acpi_scan_root(struct acpi_pci_root *root)  {
  177  	struct acpi_pci_generic_root_info *ri;
  178  	struct pci_bus *bus, *child;
  179  	struct acpi_pci_root_ops *root_ops;
  180  	struct pci_host_bridge *host;
  181  
  182  	ri = kzalloc(sizeof(*ri), GFP_KERNEL);
  183  	if (!ri)
  184  		return NULL;
  185  
  186  	root_ops = kzalloc(sizeof(*root_ops), GFP_KERNEL);
  187  	if (!root_ops) {
  188  		kfree(ri);
  189  		return NULL;
  190  	}
  191  
  192  	ri->cfg = pci_acpi_setup_ecam_mapping(root);
  193  	if (!ri->cfg) {
  194  		kfree(ri);
  195  		kfree(root_ops);
  196  		return NULL;
  197  	}
  198  
  199  	root_ops->release_info = pci_acpi_generic_release_info;
  200  	root_ops->prepare_resources = pci_acpi_root_prepare_resources;
  201  	root_ops->pci_ops = (struct pci_ops *)&ri->cfg->ops->pci_ops;
  202  	bus = acpi_pci_root_create(root, root_ops, &ri->common, ri->cfg);
  203  	if (!bus)
  204  		return NULL;
  205  
  206  	/* If we must preserve the resource configuration, claim now */
  207  	host = pci_find_host_bridge(bus);
  208  	if (host->preserve_config)
  209  		pci_bus_claim_resources(bus);
  210  
  211  	/*
  212  	 * Assign whatever was left unassigned. If we didn't claim above,
  213  	 * this will reassign everything.
  214  	 */
  215  	pci_assign_unassigned_root_bus_resources(bus);
  216  
  217  	list_for_each_entry(child, &bus->children, node)
  218  		pcie_bus_configure_settings(child);
  219  
  220  	return bus;
  221  }
```

【参照：x86的pci_acpi_scan_root（arch/x86/pci/acpi.c）】
```c
  412  struct pci_bus *pci_acpi_scan_root(struct acpi_pci_root *root)  {
  413  	int domain = root->segment;
  414  	int busnum = root->secondary.start;
  415  	int node = pci_acpi_root_get_node(root);
  416  	struct pci_bus *bus;
  417  
  418  	if (pci_ignore_seg)
  419  		root->segment = domain = 0;
  420  
  421  	if (domain && !pci_domains_supported) {
  422  		pr_warn("pci_bus %04x:%02x: ignored (multiple domains not supported)\n",
  423  		        domain, busnum);
  424  		return NULL;
  425  	}
  426  
  427  	bus = pci_find_bus(domain, busnum);
  428  	if (bus) {
  429  		/*
  430  		 * If the desired bus has been scanned already, replace
  431  		 * its bus->sysdata.
  432  		 */
  433  		struct pci_sysdata sd = {
  434  			.domain = domain,
  435  			.node = node,
  436  			.companion = root->device
  437  		};
  438  
  439  		memcpy(bus->sysdata, &sd, sizeof(sd));
  440  	} else {
  441  		struct pci_root_info *info;
  442  
  443  		info = kzalloc(sizeof(*info), GFP_KERNEL);
  444  		if (!info)
  445  			dev_err(&root->device->dev,
  446  				"pci_bus %04x:%02x: ignored (out of memory)\n",
  447  				domain, busnum);
  448  		else {
  449  			info->sd.domain = domain;
  450  			info->sd.node = node;
  451  			info->sd.companion = root->device;
  452  			bus = acpi_pci_root_create(root, &acpi_pci_root_ops,
  453  						   &info->common, &info->sd);
  454  		}
  455  	}
  456  
  457  	/* After the PCI-E bus has been walked and all devices discovered,
  458  	 * configure any settings of the fabric that might be necessary.
  459  	 */
  460  	if (bus) {
  461  		struct pci_bus *child;
...（其余6行省略）
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_33

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】同一约定规则：公共代码调用、各架构各自实现的函数中，arm64、x86、LoongArch三个实现都调用了某个函数，RISC-V的实现没有。

【被标记的位置】arch/riscv/kernel/acpi.c中的raw_pci_read

【程序给出的理由】all three references call ['read'], riscv does not

【raw_pci_read的代码】
```c
  232  int raw_pci_read(unsigned int domain, unsigned int bus, unsigned int devfn, 		 int reg, int len, u32 *val)  {
  233  	return PCIBIOS_DEVICE_NOT_FOUND;
  234  }
```

【参照：arm64的raw_pci_read（arch/arm64/kernel/pci.c）】
```c
   37  int raw_pci_read(unsigned int domain, unsigned int bus, 		  unsigned int devfn, int reg, int len, u32 *val)  {
   38  	struct pci_bus *b = pci_find_bus(domain, bus);
   39  
   40  	if (!b)
   41  		return PCIBIOS_DEVICE_NOT_FOUND;
   42  	return b->ops->read(b, devfn, reg, len, val);
   43  }
```

【参照：x86的raw_pci_read（arch/x86/pci/common.c）】
```c
   42  int raw_pci_read(unsigned int domain, unsigned int bus, unsigned int devfn, 						int reg, int len, u32 *val)  {
   43  	if (domain == 0 && reg < 256 && raw_pci_ops)
   44  		return raw_pci_ops->read(domain, bus, devfn, reg, len, val);
   45  	if (raw_pci_ext_ops)
   46  		return raw_pci_ext_ops->read(domain, bus, devfn, reg, len, val);
   47  	return -EINVAL;
   48  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_34

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】同一约定规则：公共代码调用、各架构各自实现的函数中，arm64、x86、LoongArch三个实现都调用了某个函数，RISC-V的实现没有。

【被标记的位置】arch/riscv/kernel/acpi.c中的raw_pci_write

【程序给出的理由】all three references call ['write'], riscv does not

【raw_pci_write的代码】
```c
  238  int raw_pci_write(unsigned int domain, unsigned int bus, unsigned int devfn, 		  int reg, int len, u32 val)  {
  239  	return PCIBIOS_DEVICE_NOT_FOUND;
  240  }
```

【参照：arm64的raw_pci_write（arch/arm64/kernel/pci.c）】
```c
   47  int raw_pci_write(unsigned int domain, unsigned int bus, 		unsigned int devfn, int reg, int len, u32 val)  {
   48  	struct pci_bus *b = pci_find_bus(domain, bus);
   49  
   50  	if (!b)
   51  		return PCIBIOS_DEVICE_NOT_FOUND;
   52  	return b->ops->write(b, devfn, reg, len, val);
   53  }
```

【参照：x86的raw_pci_write（arch/x86/pci/common.c）】
```c
   52  int raw_pci_write(unsigned int domain, unsigned int bus, unsigned int devfn, 						int reg, int len, u32 val)  {
   53  	if (domain == 0 && reg < 256 && raw_pci_ops)
   54  		return raw_pci_ops->write(domain, bus, devfn, reg, len, val);
   55  	if (raw_pci_ext_ops)
   56  		return raw_pci_ext_ops->write(domain, bus, devfn, reg, len, val);
   57  	return -EINVAL;
   58  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_35

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】同一约定规则：公共代码调用、各架构各自实现的函数中，arm64、x86、LoongArch三个实现都调用了某个函数，RISC-V的实现没有。

【被标记的位置】arch/riscv/mm/init.c中的vmemmap_populate

【程序给出的理由】all three references call ['vmemmap_populate_hugepages'], riscv does not

【vmemmap_populate的代码】
```c
 1505  int __meminit vmemmap_populate(unsigned long start, unsigned long end, int node, 			       struct vmem_altmap *altmap)  {
 1506  	return vmemmap_populate_basepages(start, end, node, NULL);
 1507  }
```

【参照：arm64的vmemmap_populate（arch/arm64/mm/mmu.c）】
```c
 1151  int __meminit vmemmap_populate(unsigned long start, unsigned long end, int node, 		struct vmem_altmap *altmap)  {
 1152  	WARN_ON((start < VMEMMAP_START) || (end > VMEMMAP_END));
 1153  
 1154  	if (!IS_ENABLED(CONFIG_ARM64_4K_PAGES))
 1155  		return vmemmap_populate_basepages(start, end, node, altmap);
 1156  	else
 1157  		return vmemmap_populate_hugepages(start, end, node, altmap);
 1158  }
```

【参照：x86的vmemmap_populate（arch/x86/mm/init_64.c）】
```c
 1537  int __meminit vmemmap_populate(unsigned long start, unsigned long end, int node, 		struct vmem_altmap *altmap)  {
 1538  	int err;
 1539  
 1540  	VM_BUG_ON(!PAGE_ALIGNED(start));
 1541  	VM_BUG_ON(!PAGE_ALIGNED(end));
 1542  
 1543  	if (end - start < PAGES_PER_SECTION * sizeof(struct page))
 1544  		err = vmemmap_populate_basepages(start, end, node, NULL);
 1545  	else if (boot_cpu_has(X86_FEATURE_PSE))
 1546  		err = vmemmap_populate_hugepages(start, end, node, altmap);
 1547  	else if (altmap) {
 1548  		pr_err_once("%s: no cpu support for altmap allocations\n",
 1549  				__func__);
 1550  		err = -ENOMEM;
 1551  	} else
 1552  		err = vmemmap_populate_basepages(start, end, node, NULL);
 1553  	if (!err)
 1554  		sync_global_pgds(start, end - 1);
 1555  	return err;
 1556  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_36

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本df2908090cda）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的RISC-V钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/riscv/kvm/mmu.c中的mmu_split_memory_region

【程序给出的理由】sleep A:spin: line 232 mmu_split_huge_pages -> cond_resched

【调用链】mmu_split_huge_pages（arch/riscv/kvm/mmu.c第138行调用cond_resched）

【mmu_split_memory_region的代码】
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

【mmu_split_huge_pages的代码（arch/riscv/kvm/mmu.c）】
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

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_37

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本df2908090cda）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的RISC-V钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/riscv/kernel/traps.c中的do_page_fault

【程序给出的理由】sleep B:trap: line 415 handle_page_fault -> mutex_lock

【调用链】handle_page_fault（arch/riscv/mm/fault.c第362行调用handle_mm_fault） → handle_mm_fault（mm/memory.c第6874行调用hugetlb_fault） → hugetlb_fault（mm/hugetlb.c第6032行调用mutex_lock）

【do_page_fault的代码】
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

【handle_page_fault的代码（arch/riscv/mm/fault.c）】
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
  329  	}
  330  
  331  	if (user_mode(regs))
  332  		flags |= FAULT_FLAG_USER;
  333  
  334  	if (!user_mode(regs) && addr < TASK_SIZE && unlikely(!(regs->status & SR_SUM))) {
  335  		if (fixup_exception(regs))
  336  			return;
  337  
  338  		die_kernel_fault("access to user memory without uaccess routines", addr, regs);
  339  	}
  340  
  341  	perf_sw_event(PERF_COUNT_SW_PAGE_FAULTS, 1, regs, addr);
  342  
  343  	if (cause == EXC_STORE_PAGE_FAULT)
  344  		flags |= FAULT_FLAG_WRITE;
  345  	else if (cause == EXC_INST_PAGE_FAULT)
  346  		flags |= FAULT_FLAG_INSTRUCTION;
  347  	if (!(flags & FAULT_FLAG_USER))
  348  		goto lock_mmap;
  349  
  350  	vma = lock_vma_under_rcu(mm, addr);
  351  	if (!vma)
  352  		goto lock_mmap;
  353  
  354  	if (unlikely(access_error(cause, vma))) {
  355  		vma_end_read(vma);
  356  		count_vm_vma_lock_event(VMA_LOCK_SUCCESS);
  357  		tsk->thread.bad_cause = cause;
  358  		bad_area_nosemaphore(regs, SEGV_ACCERR, addr);
...（其余85行省略）
```

【handle_mm_fault的代码（mm/memory.c）】
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
 6893  		 * The task may have entered a memcg OOM situation but
 6894  		 * if the allocation error was handled gracefully (no
 6895  		 * VM_FAULT_OOM), there is no need to kill anything.
 6896  		 * Just clean up the OOM state peacefully.
 6897  		 */
 6898  		if (task_in_memcg_oom(current) && !(ret & VM_FAULT_OOM))
 6899  			mem_cgroup_oom_synchronize(false);
 6900  	}
 6901  out:
 6902  	mm_account_fault(mm, regs, address, flags, ret);
 6903  
 6904  	return ret;
 6905  }
```

【hugetlb_fault的代码（mm/hugetlb.c）】
```c
 6003  vm_fault_t hugetlb_fault(struct mm_struct *mm, struct vm_area_struct *vma, 			unsigned long address, unsigned int flags)  {
 6004  	vm_fault_t ret;
 6005  	u32 hash;
 6006  	struct folio *folio = NULL;
 6007  	struct hstate *h = hstate_vma(vma);
 6008  	struct address_space *mapping;
 6009  	bool need_wait_lock = false;
 6010  	struct vm_fault vmf = {
 6011  		.vma = vma,
 6012  		.address = address & huge_page_mask(h),
 6013  		.real_address = address,
 6014  		.flags = flags,
 6015  		.pgoff = vma_hugecache_offset(h, vma,
 6016  				address & huge_page_mask(h)),
 6017  		/* TODO: Track hugetlb faults using vm_fault */
 6018  
 6019  		/*
 6020  		 * Some fields may not be initialized, be careful as it may
 6021  		 * be hard to debug if called functions make assumptions
 6022  		 */
 6023  	};
 6024  
 6025  	/*
 6026  	 * Serialize hugepage allocation and instantiation, so that we don't
 6027  	 * get spurious allocation failures if two CPUs race to instantiate
 6028  	 * the same page in the page cache.
 6029  	 */
 6030  	mapping = vma->vm_file->f_mapping;
 6031  	hash = hugetlb_fault_mutex_hash(mapping, vmf.pgoff);
 6032  	mutex_lock(&hugetlb_fault_mutex_table[hash]);
 6033  
 6034  	/*
 6035  	 * Acquire vma lock before calling huge_pte_alloc and hold
 6036  	 * until finished with vmf.pte.  This prevents huge_pmd_unshare from
 6037  	 * being called elsewhere and making the vmf.pte no longer valid.
 6038  	 */
 6039  	hugetlb_vma_lock_read(vma);
 6040  	vmf.pte = huge_pte_alloc(mm, vma, vmf.address, huge_page_size(h));
 6041  	if (!vmf.pte) {
 6042  		hugetlb_vma_unlock_read(vma);
 6043  		mutex_unlock(&hugetlb_fault_mutex_table[hash]);
 6044  		return VM_FAULT_OOM;
 6045  	}
 6046  
 6047  	vmf.orig_pte = huge_ptep_get(mm, vmf.address, vmf.pte);
 6048  	if (huge_pte_none(vmf.orig_pte))
 6049  		/*
 6050  		 * hugetlb_no_page will drop vma lock and hugetlb fault
 6051  		 * mutex internally, which make us return immediately.
 6052  		 */
 6053  		return hugetlb_no_page(mapping, &vmf);
 6054  
 6055  	if (pte_is_marker(vmf.orig_pte)) {
 6056  		const pte_marker marker =
 6057  			softleaf_to_marker(softleaf_from_pte(vmf.orig_pte));
 6058  
 6059  		if (marker & PTE_MARKER_POISONED) {
 6060  			ret = VM_FAULT_HWPOISON_LARGE |
 6061  				VM_FAULT_SET_HINDEX(hstate_index(h));
 6062  			goto out_mutex;
 6063  		} else if (WARN_ON_ONCE(marker & PTE_MARKER_GUARD)) {
 6064  			/* This isn't supported in hugetlb. */
 6065  			ret = VM_FAULT_SIGSEGV;
 6066  			goto out_mutex;
 6067  		}
 6068  
 6069  		return hugetlb_no_page(mapping, &vmf);
 6070  	}
 6071  
 6072  	ret = 0;
 6073  
 6074  	/* Not present, either a migration or a hwpoisoned entry */
 6075  	if (!pte_present(vmf.orig_pte) && !huge_pte_none(vmf.orig_pte)) {
 6076  		const softleaf_t softleaf = softleaf_from_pte(vmf.orig_pte);
 6077  
 6078  		if (softleaf_is_migration(softleaf)) {
 6079  			/*
 6080  			 * Release the hugetlb fault lock now, but retain
 6081  			 * the vma lock, because it is needed to guard the
 6082  			 * huge_pte_lockptr() later in
...（其余149行省略）
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_38

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本df2908090cda）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的RISC-V钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/riscv/kernel/hibernate.c中的swsusp_arch_suspend

【程序给出的理由】sleep D:hook: line 156 flush_icache_all -> on_each_cpu

【调用链】flush_icache_all（arch/riscv/mm/cacheflush.c第43行调用on_each_cpu）

【swsusp_arch_suspend的代码】
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

【flush_icache_all的代码（arch/riscv/mm/cacheflush.c）】
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

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_39

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本df2908090cda）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】推测执行越界规则：函数对一个可能来自客体（虚拟机）或用户的下标做了上界检查，随后用它访问数组，却没有用array_index_nospec，可能被推测执行越界利用（Spectre-v1）。

【被标记的位置】arch/riscv/kvm/vcpu_pmu.c中的pmu_fw_ctr_read_hi

【程序给出的理由】line 240: [fevent_code] after bound check at line 236, no array_index_nospec

【pmu_fw_ctr_read_hi的代码】
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

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。

## Q_40

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本df2908090cda）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】推测执行越界规则：函数对一个可能来自客体（虚拟机）或用户的下标做了上界检查，随后用它访问数组，却没有用array_index_nospec，可能被推测执行越界利用（Spectre-v1）。

【被标记的位置】arch/riscv/kvm/vcpu_pmu.c中的pmu_ctr_read

【程序给出的理由】line 272: [fevent_code] after bound check at line 268, no array_index_nospec

【pmu_ctr_read的代码】
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

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。
