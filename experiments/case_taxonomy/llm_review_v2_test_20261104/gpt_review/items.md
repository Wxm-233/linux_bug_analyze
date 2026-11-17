# 待复核的标记（62条）

## L00

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的die

【程序给出的理由】sleep A:raw: line 241 bust_spinlocks -> might_sleep

【调用链】bust_spinlocks（lib/bust_spinlocks.c第25行调用console_unblank） → console_unblank（kernel/printk/printk.c第2911行调用console_lock） → console_lock（kernel/printk/printk.c第2565行调用might_sleep）

【die的代码】
```c
  229  void __noreturn die(const char *str, struct pt_regs *regs)  {
  230  	static int die_counter;
  231  	int sig = SIGSEGV;
  232  
  233  	oops_enter();
  234  
  235  	if (notify_die(DIE_OOPS, str, regs, 0, current->thread.trap_nr,
  236  		       SIGSEGV) == NOTIFY_STOP)
  237  		sig = 0;
  238  
  239  	console_verbose();
  240  	raw_spin_lock_irq(&die_lock);
  241  	bust_spinlocks(1);
  242  
  243  	printk("%s[#%d]:\n", str, ++die_counter);
  244  	show_registers(regs);
  245  	add_taint(TAINT_DIE, LOCKDEP_NOW_UNRELIABLE);
  246  	raw_spin_unlock_irq(&die_lock);
  247  
  248  	oops_exit();
  249  
  250  	if (regs && kexec_should_crash(current))
  251  		crash_kexec(regs);
  252  
  253  	if (in_interrupt())
  254  		panic("Fatal exception in interrupt");
  255  
  256  	if (panic_on_oops)
  257  		panic("Fatal exception");
  258  
  259  	make_task_dead(sig);
  260  }
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
 2900  void console_unblank(void)  {
 2901  	struct console *c;
 2902  
 2903  	/*
 2904  	 * console_unblank can no longer be called in interrupt context unless
 2905  	 * oops_in_progress is set to 1..
 2906  	 */
 2907  	if (oops_in_progress) {
 2908  		if (down_trylock_console_sem() != 0)
 2909  			return;
 2910  	} else
 2911  		console_lock();
 2912  
 2913  	console_locked = 1;
 2914  	console_may_schedule = 0;
 2915  	for_each_console(c)
 2916  		if ((c->flags & CON_ENABLED) && c->unblank)
 2917  			c->unblank();
 2918  	console_unlock();
 2919  
 2920  	if (!oops_in_progress)
 2921  		pr_flush(1000, true);
 2922  }
```

【console_lock的代码（kernel/printk/printk.c）】
```c
 2564  void console_lock(void)  {
 2565  	might_sleep();
 2566  
 2567  	down_console_sem();
 2568  	if (console_suspended)
 2569  		return;
 2570  	console_locked = 1;
 2571  	console_may_schedule = 1;
 2572  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

## L01

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/sysrq.c中的sysrq_tlbdump_single

【程序给出的理由】rt C:callback: line 26 spin_lock_irqsave -> spin_lock_irqsave

【sysrq_tlbdump_single的代码】
```c
   23  static void sysrq_tlbdump_single(void *dummy)  {
   24  	unsigned long flags;
   25  
   26  	spin_lock_irqsave(&show_lock, flags);
   27  
   28  	pr_info("CPU%d:\n", smp_processor_id());
   29  	dump_tlb_regs();
   30  	pr_info("\n");
   31  	dump_tlb_all();
   32  	pr_info("\n");
   33  
   34  	spin_unlock_irqrestore(&show_lock, flags);
   35  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

## L02

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/smp.c中的smp_send_stop

【程序给出的理由】sleep D:hook: line 524 smp_call_function -> smp_call_function

【smp_send_stop的代码】
```c
  523  void smp_send_stop(void)  {
  524  	smp_call_function(stop_this_cpu, NULL, 0);
  525  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

## L03

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_lbt

【程序给出的理由】noinstr N2: line 572 force_sig -> instrumentable callee

【调用链】force_sig（kernel/signal.c第1651行调用）

【do_lbt的代码】
```c
  568  asmlinkage void noinstr do_lbt(struct pt_regs *regs)  {
  569  	irqentry_state_t state = irqentry_enter(regs);
  570  
  571  	local_irq_enable();
  572  	force_sig(SIGILL);
  573  	local_irq_disable();
  574  
  575  	irqentry_exit(regs, state);
  576  }
```

【force_sig的代码（kernel/signal.c）】
```c
 1651  void force_sig(int sig)  {
 1652  	struct kernel_siginfo info;
 1653  
 1654  	clear_siginfo(&info);
 1655  	info.si_signo = sig;
 1656  	info.si_errno = 0;
 1657  	info.si_code = SI_KERNEL;
 1658  	info.si_pid = 0;
 1659  	info.si_uid = 0;
 1660  	force_sig_info(&info);
 1661  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

## L04

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的handle_loongarch_irq

【程序给出的理由】noinstr N2: line 610 irq_enter_rcu -> instrumentable callee

【调用链】irq_enter_rcu（kernel/softirq.c第608行调用）

【handle_loongarch_irq的代码】
```c
  607  asmlinkage void noinstr handle_loongarch_irq(struct pt_regs *regs)  {
  608  	struct pt_regs *old_regs;
  609  
  610  	irq_enter_rcu();
  611  	old_regs = set_irq_regs(regs);
  612  	handle_arch_irq(regs);
  613  	set_irq_regs(old_regs);
  614  	irq_exit_rcu();
  615  }
```

【irq_enter_rcu的代码（kernel/softirq.c）】
```c
  608  void irq_enter_rcu(void)  {
  609  	__irq_enter_raw();
  610  
  611  	if (tick_nohz_full_cpu(smp_processor_id()) ||
  612  	    (is_idle_task(current) && (irq_count() == HARDIRQ_OFFSET)))
  613  		tick_irq_enter();
  614  
  615  	account_hardirq_enter(current);
  616  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

## L05

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.2）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_ale

【程序给出的理由】sleep B:trap: line 393 emulate_load_store_insn -> get_user

【调用链】emulate_load_store_insn（arch/loongarch/kernel/unaligned.c第260行调用__get_inst） → __get_inst（arch/loongarch/kernel/access-helper.h第7行调用get_user）

【do_ale的代码】
```c
  373  asmlinkage void noinstr do_ale(struct pt_regs *regs)  {
  374  	unsigned int *pc;
  375  	irqentry_state_t state = irqentry_enter(regs);
  376  
  377  	perf_sw_event(PERF_COUNT_SW_ALIGNMENT_FAULTS, 1, regs, regs->csr_badvaddr);
  378  
  379  	/*
  380  	 * Did we catch a fault trying to load an instruction?
  381  	 */
  382  	if (regs->csr_badvaddr == regs->csr_era)
  383  		goto sigbus;
  384  	if (user_mode(regs) && !test_thread_flag(TIF_FIXADE))
  385  		goto sigbus;
  386  	if (!unaligned_enabled)
  387  		goto sigbus;
  388  	if (!no_unaligned_warning)
  389  		show_registers(regs);
  390  
  391  	pc = (unsigned int *)exception_era(regs);
  392  
  393  	emulate_load_store_insn(regs, (void __user *)regs->csr_badvaddr, pc);
  394  
  395  	goto out;
  396  
  397  sigbus:
  398  	die_if_kernel("Kernel ale access", regs);
  399  	force_sig_fault(SIGBUS, BUS_ADRALN, (void __user *)regs->csr_badvaddr);
  400  
  401  out:
  402  	irqentry_exit(regs, state);
  403  }
```

【emulate_load_store_insn的代码（arch/loongarch/kernel/unaligned.c）】
```c
  250  void emulate_load_store_insn(struct pt_regs *regs, void __user *addr, unsigned int *pc)  {
  251  	bool fp = false;
  252  	bool sign, write;
  253  	bool user = user_mode(regs);
  254  	unsigned int res, size = 0;
  255  	unsigned long value = 0;
  256  	union loongarch_instruction insn;
  257  
  258  	perf_sw_event(PERF_COUNT_SW_EMULATION_FAULTS, 1, regs, 0);
  259  
  260  	__get_inst(&insn.word, pc, user);
  261  
  262  	switch (insn.reg2i12_format.opcode) {
  263  	case ldh_op:
  264  		size = 2;
  265  		sign = true;
  266  		write = false;
  267  		break;
  268  	case ldhu_op:
  269  		size = 2;
  270  		sign = false;
  271  		write = false;
  272  		break;
  273  	case sth_op:
  274  		size = 2;
  275  		sign = true;
  276  		write = true;
  277  		break;
  278  	case ldw_op:
  279  		size = 4;
  280  		sign = true;
  281  		write = false;
  282  		break;
  283  	case ldwu_op:
  284  		size = 4;
  285  		sign = false;
  286  		write = false;
  287  		break;
  288  	case stw_op:
  289  		size = 4;
  290  		sign = true;
  291  		write = true;
  292  		break;
  293  	case ldd_op:
  294  		size = 8;
  295  		sign = true;
  296  		write = false;
  297  		break;
  298  	case std_op:
  299  		size = 8;
  300  		sign = true;
  301  		write = true;
  302  		break;
  303  	case flds_op:
  304  		size = 4;
  305  		fp = true;
  306  		sign = true;
  307  		write = false;
  308  		break;
  309  	case fsts_op:
  310  		size = 4;
  311  		fp = true;
  312  		sign = true;
  313  		write = true;
  314  		break;
  315  	case fldd_op:
  316  		size = 8;
  317  		fp = true;
  318  		sign = true;
  319  		write = false;
  320  		break;
  321  	case fstd_op:
  322  		size = 8;
  323  		fp = true;
  324  		sign = true;
  325  		write = true;
  326  		break;
  327  	}
  328  
  329  	switch (insn.reg2i14_format.opcode) {
...（其余151行省略）
```

【__get_inst的代码（arch/loongarch/kernel/access-helper.h）】
```c
    6  static inline int __get_inst(u32 *i, u32 *p, bool user)  {
    7  	return user ? get_user(*i, (u32 __user *)p) : get_kernel_nofault(*i, p);
    8  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

## L06

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.2）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_ale

【程序给出的理由】noinstr N2: line 389 show_registers -> instrumentable callee

【调用链】show_registers（arch/loongarch/kernel/traps.c第212行调用）

【do_ale的代码】
```c
  373  asmlinkage void noinstr do_ale(struct pt_regs *regs)  {
  374  	unsigned int *pc;
  375  	irqentry_state_t state = irqentry_enter(regs);
  376  
  377  	perf_sw_event(PERF_COUNT_SW_ALIGNMENT_FAULTS, 1, regs, regs->csr_badvaddr);
  378  
  379  	/*
  380  	 * Did we catch a fault trying to load an instruction?
  381  	 */
  382  	if (regs->csr_badvaddr == regs->csr_era)
  383  		goto sigbus;
  384  	if (user_mode(regs) && !test_thread_flag(TIF_FIXADE))
  385  		goto sigbus;
  386  	if (!unaligned_enabled)
  387  		goto sigbus;
  388  	if (!no_unaligned_warning)
  389  		show_registers(regs);
  390  
  391  	pc = (unsigned int *)exception_era(regs);
  392  
  393  	emulate_load_store_insn(regs, (void __user *)regs->csr_badvaddr, pc);
  394  
  395  	goto out;
  396  
  397  sigbus:
  398  	die_if_kernel("Kernel ale access", regs);
  399  	force_sig_fault(SIGBUS, BUS_ADRALN, (void __user *)regs->csr_badvaddr);
  400  
  401  out:
  402  	irqentry_exit(regs, state);
  403  }
```

【show_registers的代码（arch/loongarch/kernel/traps.c）】
```c
  212  void show_registers(struct pt_regs *regs)  {
  213  	__show_regs(regs);
  214  	print_modules();
  215  	printk("Process %s (pid: %d, threadinfo=%p, task=%p)\n",
  216  	       current->comm, current->pid, current_thread_info(), current);
  217  
  218  	show_stacktrace(current, regs, KERN_DEFAULT, user_mode(regs));
  219  	show_code((void *)regs->csr_era, user_mode(regs));
  220  	printk("\n");
  221  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

## L07

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.2）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】同一约定规则：公共代码调用、各架构各自实现的函数中，arm64、x86、RISC-V三个实现都调用了某个函数，LoongArch的实现没有。

【被标记的位置】arch/loongarch/include/asm/stackprotector.h中的boot_init_stack_canary

【程序给出的理由】all three references call ['get_random_canary'], loongarch does not

【boot_init_stack_canary的代码】
```c
   27  static __always_inline void boot_init_stack_canary(void)  {
   28  	unsigned long canary;
   29  
   30  	/* Try to get a semi random initial value. */
   31  	get_random_bytes(&canary, sizeof(canary));
   32  	canary ^= LINUX_VERSION_CODE;
   33  
   34  	current->stack_canary = canary;
   35  	__stack_chk_guard = current->stack_canary;
   36  }
```

【参照：arm64的boot_init_stack_canary（arch/arm64/include/asm/stackprotector.h）】
```c
   27  static __always_inline void boot_init_stack_canary(void)  {
   28  #if defined(CONFIG_STACKPROTECTOR)
   29  	unsigned long canary = get_random_canary();
   30  
   31  	current->stack_canary = canary;
   32  	if (!IS_ENABLED(CONFIG_STACKPROTECTOR_PER_TASK))
   33  		__stack_chk_guard = current->stack_canary;
   34  #endif
   35  	ptrauth_thread_init_kernel(current);
   36  	ptrauth_thread_switch_kernel(current);
   37  	ptrauth_enable();
   38  }
```

【参照：x86的boot_init_stack_canary（arch/x86/include/asm/stackprotector.h）】
```c
   51  static __always_inline void boot_init_stack_canary(void)  {
   52  	unsigned long canary = get_random_canary();
   53  
   54  #ifdef CONFIG_X86_64
   55  	BUILD_BUG_ON(offsetof(struct fixed_percpu_data, stack_canary) != 40);
   56  #endif
   57  
   58  	current->stack_canary = canary;
   59  #ifdef CONFIG_X86_64
   60  	this_cpu_write(fixed_percpu_data.stack_canary, canary);
   61  #else
   62  	this_cpu_write(__stack_chk_guard, canary);
   63  #endif
   64  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

## L08

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.3）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_bp

【程序给出的理由】sleep B:trap: line 444 __get_inst -> get_user

【调用链】__get_inst（arch/loongarch/kernel/access-helper.h第7行调用get_user）

【do_bp的代码】
```c
  434  asmlinkage void noinstr do_bp(struct pt_regs *regs)  {
  435  	bool user = user_mode(regs);
  436  	unsigned int opcode, bcode;
  437  	unsigned long era = exception_era(regs);
  438  	irqentry_state_t state = irqentry_enter(regs);
  439  
  440  	if (regs->csr_prmd & CSR_PRMD_PIE)
  441  		local_irq_enable();
  442  
  443  	current->thread.trap_nr = read_csr_excode();
  444  	if (__get_inst(&opcode, (u32 *)era, user))
  445  		goto out_sigsegv;
  446  
  447  	bcode = (opcode & 0x7fff);
  448  
  449  	/*
  450  	 * notify the kprobe handlers, if instruction is likely to
  451  	 * pertain to them.
  452  	 */
  453  	switch (bcode) {
  454  	case BRK_KPROBE_BP:
  455  		if (kprobe_breakpoint_handler(regs))
  456  			goto out;
  457  		else
  458  			break;
  459  	case BRK_KPROBE_SSTEPBP:
  460  		if (kprobe_singlestep_handler(regs))
  461  			goto out;
  462  		else
  463  			break;
  464  	case BRK_UPROBE_BP:
  465  		if (notify_die(DIE_UPROBE, "Uprobe", regs, bcode,
  466  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  467  			goto out;
  468  		else
  469  			break;
  470  	case BRK_UPROBE_XOLBP:
  471  		if (notify_die(DIE_UPROBE_XOL, "Uprobe_XOL", regs, bcode,
  472  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  473  			goto out;
  474  		else
  475  			break;
  476  	default:
  477  		if (notify_die(DIE_TRAP, "Break", regs, bcode,
  478  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  479  			goto out;
  480  		else
  481  			break;
  482  	}
  483  
  484  	switch (bcode) {
  485  	case BRK_BUG:
  486  		bug_handler(regs);
  487  		break;
  488  	case BRK_DIVZERO:
  489  		die_if_kernel("Break instruction in kernel code", regs);
  490  		force_sig_fault(SIGFPE, FPE_INTDIV, (void __user *)regs->csr_era);
  491  		break;
  492  	case BRK_OVERFLOW:
  493  		die_if_kernel("Break instruction in kernel code", regs);
  494  		force_sig_fault(SIGFPE, FPE_INTOVF, (void __user *)regs->csr_era);
  495  		break;
  496  	default:
  497  		die_if_kernel("Break instruction in kernel code", regs);
  498  		force_sig_fault(SIGTRAP, TRAP_BRKPT, (void __user *)regs->csr_era);
  499  		break;
  500  	}
  501  
  502  out:
  503  	if (regs->csr_prmd & CSR_PRMD_PIE)
  504  		local_irq_disable();
  505  
  506  	irqentry_exit(regs, state);
  507  	return;
  508  
  509  out_sigsegv:
  510  	force_sig(SIGSEGV);
  511  	goto out;
  512  }
```

【__get_inst的代码（arch/loongarch/kernel/access-helper.h）】
```c
    6  static inline int __get_inst(u32 *i, u32 *p, bool user)  {
    7  	return user ? get_user(*i, (u32 __user *)p) : get_kernel_nofault(*i, p);
    8  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

## L09

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.3）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_bp

【程序给出的理由】noinstr N2: line 460 kprobe_singlestep_handler -> instrumentable callee

【调用链】kprobe_singlestep_handler（arch/loongarch/kernel/kprobes.c第318行调用）

【do_bp的代码】
```c
  434  asmlinkage void noinstr do_bp(struct pt_regs *regs)  {
  435  	bool user = user_mode(regs);
  436  	unsigned int opcode, bcode;
  437  	unsigned long era = exception_era(regs);
  438  	irqentry_state_t state = irqentry_enter(regs);
  439  
  440  	if (regs->csr_prmd & CSR_PRMD_PIE)
  441  		local_irq_enable();
  442  
  443  	current->thread.trap_nr = read_csr_excode();
  444  	if (__get_inst(&opcode, (u32 *)era, user))
  445  		goto out_sigsegv;
  446  
  447  	bcode = (opcode & 0x7fff);
  448  
  449  	/*
  450  	 * notify the kprobe handlers, if instruction is likely to
  451  	 * pertain to them.
  452  	 */
  453  	switch (bcode) {
  454  	case BRK_KPROBE_BP:
  455  		if (kprobe_breakpoint_handler(regs))
  456  			goto out;
  457  		else
  458  			break;
  459  	case BRK_KPROBE_SSTEPBP:
  460  		if (kprobe_singlestep_handler(regs))
  461  			goto out;
  462  		else
  463  			break;
  464  	case BRK_UPROBE_BP:
  465  		if (notify_die(DIE_UPROBE, "Uprobe", regs, bcode,
  466  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  467  			goto out;
  468  		else
  469  			break;
  470  	case BRK_UPROBE_XOLBP:
  471  		if (notify_die(DIE_UPROBE_XOL, "Uprobe_XOL", regs, bcode,
  472  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  473  			goto out;
  474  		else
  475  			break;
  476  	default:
  477  		if (notify_die(DIE_TRAP, "Break", regs, bcode,
  478  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  479  			goto out;
  480  		else
  481  			break;
  482  	}
  483  
  484  	switch (bcode) {
  485  	case BRK_BUG:
  486  		bug_handler(regs);
  487  		break;
  488  	case BRK_DIVZERO:
  489  		die_if_kernel("Break instruction in kernel code", regs);
  490  		force_sig_fault(SIGFPE, FPE_INTDIV, (void __user *)regs->csr_era);
  491  		break;
  492  	case BRK_OVERFLOW:
  493  		die_if_kernel("Break instruction in kernel code", regs);
  494  		force_sig_fault(SIGFPE, FPE_INTOVF, (void __user *)regs->csr_era);
  495  		break;
  496  	default:
  497  		die_if_kernel("Break instruction in kernel code", regs);
  498  		force_sig_fault(SIGTRAP, TRAP_BRKPT, (void __user *)regs->csr_era);
  499  		break;
  500  	}
  501  
  502  out:
  503  	if (regs->csr_prmd & CSR_PRMD_PIE)
  504  		local_irq_disable();
  505  
  506  	irqentry_exit(regs, state);
  507  	return;
  508  
  509  out_sigsegv:
  510  	force_sig(SIGSEGV);
  511  	goto out;
  512  }
```

【kprobe_singlestep_handler的代码（arch/loongarch/kernel/kprobes.c）】
```c
  318  bool kprobe_singlestep_handler(struct pt_regs *regs)  {
  319  	struct kprobe *cur = kprobe_running();
  320  	struct kprobe_ctlblk *kcb = get_kprobe_ctlblk();
  321  	unsigned long addr = instruction_pointer(regs);
  322  
  323  	if (cur && (kcb->kprobe_status & (KPROBE_HIT_SS | KPROBE_REENTER)) &&
  324  	    ((unsigned long)&cur->ainsn.insn[1] == addr)) {
  325  		restore_local_irqflag(kcb, regs);
  326  		post_kprobe_handler(cur, kcb, regs);
  327  		return true;
  328  	}
  329  
  330  	preempt_enable_no_resched();
  331  	return false;
  332  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

## L10

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.3）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_watch

【程序给出的理由】noinstr N2: line 554 breakpoint_handler -> instrumentable callee

【调用链】breakpoint_handler（arch/loongarch/kernel/hw_breakpoint.c第466行调用）

【do_watch的代码】
```c
  515  asmlinkage void noinstr do_watch(struct pt_regs *regs)  {
  516  	irqentry_state_t state = irqentry_enter(regs);
  517  
  518  #ifndef CONFIG_HAVE_HW_BREAKPOINT
  519  	pr_warn("Hardware watch point handler not implemented!\n");
  520  #else
  521  	if (test_tsk_thread_flag(current, TIF_SINGLESTEP)) {
  522  		int llbit = (csr_read32(LOONGARCH_CSR_LLBCTL) & 0x1);
  523  		unsigned long pc = instruction_pointer(regs);
  524  		union loongarch_instruction *ip = (union loongarch_instruction *)pc;
  525  
  526  		if (llbit) {
  527  			/*
  528  			 * When the ll-sc combo is encountered, it is regarded as an single
  529  			 * instruction. So don't clear llbit and reset CSR.FWPS.Skip until
  530  			 * the llsc execution is completed.
  531  			 */
  532  			csr_write32(CSR_FWPC_SKIP, LOONGARCH_CSR_FWPS);
  533  			csr_write32(CSR_LLBCTL_KLO, LOONGARCH_CSR_LLBCTL);
  534  			goto out;
  535  		}
  536  
  537  		if (pc == current->thread.single_step) {
  538  			/*
  539  			 * Certain insns are occasionally not skipped when CSR.FWPS.Skip is
  540  			 * set, such as fld.d/fst.d. So singlestep needs to compare whether
  541  			 * the csr_era is equal to the value of singlestep which last time set.
  542  			 */
  543  			if (!is_self_loop_ins(ip, regs)) {
  544  				/*
  545  				 * Check if the given instruction the target pc is equal to the
  546  				 * current pc, If yes, then we should not set the CSR.FWPS.SKIP
  547  				 * bit to break the original instruction stream.
  548  				 */
  549  				csr_write32(CSR_FWPC_SKIP, LOONGARCH_CSR_FWPS);
  550  				goto out;
  551  			}
  552  		}
  553  	} else {
  554  		breakpoint_handler(regs);
  555  		watchpoint_handler(regs);
  556  	}
  557  
  558  	force_sig(SIGTRAP);
  559  out:
  560  #endif
  561  	irqentry_exit(regs, state);
  562  }
```

【breakpoint_handler的代码（arch/loongarch/kernel/hw_breakpoint.c）】
```c
  466  void breakpoint_handler(struct pt_regs *regs)  {
  467  	int i;
  468  	struct perf_event *bp, **slots;
  469  
  470  	slots = this_cpu_ptr(bp_on_reg);
  471  
  472  	for (i = 0; i < boot_cpu_data.watch_ireg_count; ++i) {
  473  		bp = slots[i];
  474  		if (bp == NULL)
  475  			continue;
  476  		perf_bp_event(bp, regs);
  477  	}
  478  	update_bp_registers(regs, 0, 0);
  479  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

## L11

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.3）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_watch

【程序给出的理由】noinstr N2: line 558 force_sig -> instrumentable callee

【调用链】force_sig（kernel/signal.c第1651行调用）

【do_watch的代码】
```c
  515  asmlinkage void noinstr do_watch(struct pt_regs *regs)  {
  516  	irqentry_state_t state = irqentry_enter(regs);
  517  
  518  #ifndef CONFIG_HAVE_HW_BREAKPOINT
  519  	pr_warn("Hardware watch point handler not implemented!\n");
  520  #else
  521  	if (test_tsk_thread_flag(current, TIF_SINGLESTEP)) {
  522  		int llbit = (csr_read32(LOONGARCH_CSR_LLBCTL) & 0x1);
  523  		unsigned long pc = instruction_pointer(regs);
  524  		union loongarch_instruction *ip = (union loongarch_instruction *)pc;
  525  
  526  		if (llbit) {
  527  			/*
  528  			 * When the ll-sc combo is encountered, it is regarded as an single
  529  			 * instruction. So don't clear llbit and reset CSR.FWPS.Skip until
  530  			 * the llsc execution is completed.
  531  			 */
  532  			csr_write32(CSR_FWPC_SKIP, LOONGARCH_CSR_FWPS);
  533  			csr_write32(CSR_LLBCTL_KLO, LOONGARCH_CSR_LLBCTL);
  534  			goto out;
  535  		}
  536  
  537  		if (pc == current->thread.single_step) {
  538  			/*
  539  			 * Certain insns are occasionally not skipped when CSR.FWPS.Skip is
  540  			 * set, such as fld.d/fst.d. So singlestep needs to compare whether
  541  			 * the csr_era is equal to the value of singlestep which last time set.
  542  			 */
  543  			if (!is_self_loop_ins(ip, regs)) {
  544  				/*
  545  				 * Check if the given instruction the target pc is equal to the
  546  				 * current pc, If yes, then we should not set the CSR.FWPS.SKIP
  547  				 * bit to break the original instruction stream.
  548  				 */
  549  				csr_write32(CSR_FWPC_SKIP, LOONGARCH_CSR_FWPS);
  550  				goto out;
  551  			}
  552  		}
  553  	} else {
  554  		breakpoint_handler(regs);
  555  		watchpoint_handler(regs);
  556  	}
  557  
  558  	force_sig(SIGTRAP);
  559  out:
  560  #endif
  561  	irqentry_exit(regs, state);
  562  }
```

【force_sig的代码（kernel/signal.c）】
```c
 1651  void force_sig(int sig)  {
 1652  	struct kernel_siginfo info;
 1653  
 1654  	clear_siginfo(&info);
 1655  	info.si_signo = sig;
 1656  	info.si_errno = 0;
 1657  	info.si_code = SI_KERNEL;
 1658  	info.si_pid = 0;
 1659  	info.si_uid = 0;
 1660  	force_sig_info(&info);
 1661  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

## L12

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.4）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_bce

【程序给出的理由】sleep B:trap: line 613 __get_inst -> get_user

【调用链】__get_inst（arch/loongarch/kernel/access-helper.h第7行调用get_user）

【do_bce的代码】
```c
  594  asmlinkage void noinstr do_bce(struct pt_regs *regs)  {
  595  	bool user = user_mode(regs);
  596  	unsigned long era = exception_era(regs);
  597  	u64 badv = 0, lower = 0, upper = ULONG_MAX;
  598  	union loongarch_instruction insn;
  599  	irqentry_state_t state = irqentry_enter(regs);
  600  
  601  	if (regs->csr_prmd & CSR_PRMD_PIE)
  602  		local_irq_enable();
  603  
  604  	current->thread.trap_nr = read_csr_excode();
  605  
  606  	die_if_kernel("Bounds check error in kernel code", regs);
  607  
  608  	/*
  609  	 * Pull out the address that failed bounds checking, and the lower /
  610  	 * upper bound, by minimally looking at the faulting instruction word
  611  	 * and reading from the correct register.
  612  	 */
  613  	if (__get_inst(&insn.word, (u32 *)era, user))
  614  		goto bad_era;
  615  
  616  	switch (insn.reg3_format.opcode) {
  617  	case asrtle_op:
  618  		if (insn.reg3_format.rd != 0)
  619  			break;	/* not asrtle */
  620  		badv = regs->regs[insn.reg3_format.rj];
  621  		upper = regs->regs[insn.reg3_format.rk];
  622  		break;
  623  
  624  	case asrtgt_op:
  625  		if (insn.reg3_format.rd != 0)
  626  			break;	/* not asrtgt */
  627  		badv = regs->regs[insn.reg3_format.rj];
  628  		lower = regs->regs[insn.reg3_format.rk];
  629  		break;
  630  
  631  	case ldleb_op:
  632  	case ldleh_op:
  633  	case ldlew_op:
  634  	case ldled_op:
  635  	case stleb_op:
  636  	case stleh_op:
  637  	case stlew_op:
  638  	case stled_op:
  639  	case fldles_op:
  640  	case fldled_op:
  641  	case fstles_op:
  642  	case fstled_op:
  643  		badv = regs->regs[insn.reg3_format.rj];
  644  		upper = regs->regs[insn.reg3_format.rk];
  645  		break;
  646  
  647  	case ldgtb_op:
  648  	case ldgth_op:
  649  	case ldgtw_op:
  650  	case ldgtd_op:
  651  	case stgtb_op:
  652  	case stgth_op:
  653  	case stgtw_op:
  654  	case stgtd_op:
  655  	case fldgts_op:
  656  	case fldgtd_op:
  657  	case fstgts_op:
  658  	case fstgtd_op:
  659  		badv = regs->regs[insn.reg3_format.rj];
  660  		lower = regs->regs[insn.reg3_format.rk];
  661  		break;
  662  	}
  663  
  664  	force_sig_bnderr((void __user *)badv, (void __user *)lower, (void __user *)upper);
  665  
  666  out:
  667  	if (regs->csr_prmd & CSR_PRMD_PIE)
  668  		local_irq_disable();
  669  
  670  	irqentry_exit(regs, state);
  671  	return;
  672  
  673  bad_era:
...（其余7行省略）
```

【__get_inst的代码（arch/loongarch/kernel/access-helper.h）】
```c
    6  static inline int __get_inst(u32 *i, u32 *p, bool user)  {
    7  	return user ? get_user(*i, (u32 __user *)p) : get_kernel_nofault(*i, p);
    8  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

## L13

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.4）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_bce

【程序给出的理由】noinstr N2: line 664 force_sig_bnderr -> instrumentable callee

【调用链】force_sig_bnderr（kernel/signal.c第1780行调用）

【do_bce的代码】
```c
  594  asmlinkage void noinstr do_bce(struct pt_regs *regs)  {
  595  	bool user = user_mode(regs);
  596  	unsigned long era = exception_era(regs);
  597  	u64 badv = 0, lower = 0, upper = ULONG_MAX;
  598  	union loongarch_instruction insn;
  599  	irqentry_state_t state = irqentry_enter(regs);
  600  
  601  	if (regs->csr_prmd & CSR_PRMD_PIE)
  602  		local_irq_enable();
  603  
  604  	current->thread.trap_nr = read_csr_excode();
  605  
  606  	die_if_kernel("Bounds check error in kernel code", regs);
  607  
  608  	/*
  609  	 * Pull out the address that failed bounds checking, and the lower /
  610  	 * upper bound, by minimally looking at the faulting instruction word
  611  	 * and reading from the correct register.
  612  	 */
  613  	if (__get_inst(&insn.word, (u32 *)era, user))
  614  		goto bad_era;
  615  
  616  	switch (insn.reg3_format.opcode) {
  617  	case asrtle_op:
  618  		if (insn.reg3_format.rd != 0)
  619  			break;	/* not asrtle */
  620  		badv = regs->regs[insn.reg3_format.rj];
  621  		upper = regs->regs[insn.reg3_format.rk];
  622  		break;
  623  
  624  	case asrtgt_op:
  625  		if (insn.reg3_format.rd != 0)
  626  			break;	/* not asrtgt */
  627  		badv = regs->regs[insn.reg3_format.rj];
  628  		lower = regs->regs[insn.reg3_format.rk];
  629  		break;
  630  
  631  	case ldleb_op:
  632  	case ldleh_op:
  633  	case ldlew_op:
  634  	case ldled_op:
  635  	case stleb_op:
  636  	case stleh_op:
  637  	case stlew_op:
  638  	case stled_op:
  639  	case fldles_op:
  640  	case fldled_op:
  641  	case fstles_op:
  642  	case fstled_op:
  643  		badv = regs->regs[insn.reg3_format.rj];
  644  		upper = regs->regs[insn.reg3_format.rk];
  645  		break;
  646  
  647  	case ldgtb_op:
  648  	case ldgth_op:
  649  	case ldgtw_op:
  650  	case ldgtd_op:
  651  	case stgtb_op:
  652  	case stgth_op:
  653  	case stgtw_op:
  654  	case stgtd_op:
  655  	case fldgts_op:
  656  	case fldgtd_op:
  657  	case fstgts_op:
  658  	case fstgtd_op:
  659  		badv = regs->regs[insn.reg3_format.rj];
  660  		lower = regs->regs[insn.reg3_format.rk];
  661  		break;
  662  	}
  663  
  664  	force_sig_bnderr((void __user *)badv, (void __user *)lower, (void __user *)upper);
  665  
  666  out:
  667  	if (regs->csr_prmd & CSR_PRMD_PIE)
  668  		local_irq_disable();
  669  
  670  	irqentry_exit(regs, state);
  671  	return;
  672  
  673  bad_era:
...（其余7行省略）
```

【force_sig_bnderr的代码（kernel/signal.c）】
```c
 1780  int force_sig_bnderr(void __user *addr, void __user *lower, void __user *upper)  {
 1781  	struct kernel_siginfo info;
 1782  
 1783  	clear_siginfo(&info);
 1784  	info.si_signo = SIGSEGV;
 1785  	info.si_errno = 0;
 1786  	info.si_code  = SEGV_BNDERR;
 1787  	info.si_addr  = addr;
 1788  	info.si_lower = lower;
 1789  	info.si_upper = upper;
 1790  	return force_sig_info(&info);
 1791  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

## L14

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.4）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_bce

【程序给出的理由】noinstr N2: line 678 force_sig -> instrumentable callee

【调用链】force_sig（kernel/signal.c第1652行调用）

【do_bce的代码】
```c
  594  asmlinkage void noinstr do_bce(struct pt_regs *regs)  {
  595  	bool user = user_mode(regs);
  596  	unsigned long era = exception_era(regs);
  597  	u64 badv = 0, lower = 0, upper = ULONG_MAX;
  598  	union loongarch_instruction insn;
  599  	irqentry_state_t state = irqentry_enter(regs);
  600  
  601  	if (regs->csr_prmd & CSR_PRMD_PIE)
  602  		local_irq_enable();
  603  
  604  	current->thread.trap_nr = read_csr_excode();
  605  
  606  	die_if_kernel("Bounds check error in kernel code", regs);
  607  
  608  	/*
  609  	 * Pull out the address that failed bounds checking, and the lower /
  610  	 * upper bound, by minimally looking at the faulting instruction word
  611  	 * and reading from the correct register.
  612  	 */
  613  	if (__get_inst(&insn.word, (u32 *)era, user))
  614  		goto bad_era;
  615  
  616  	switch (insn.reg3_format.opcode) {
  617  	case asrtle_op:
  618  		if (insn.reg3_format.rd != 0)
  619  			break;	/* not asrtle */
  620  		badv = regs->regs[insn.reg3_format.rj];
  621  		upper = regs->regs[insn.reg3_format.rk];
  622  		break;
  623  
  624  	case asrtgt_op:
  625  		if (insn.reg3_format.rd != 0)
  626  			break;	/* not asrtgt */
  627  		badv = regs->regs[insn.reg3_format.rj];
  628  		lower = regs->regs[insn.reg3_format.rk];
  629  		break;
  630  
  631  	case ldleb_op:
  632  	case ldleh_op:
  633  	case ldlew_op:
  634  	case ldled_op:
  635  	case stleb_op:
  636  	case stleh_op:
  637  	case stlew_op:
  638  	case stled_op:
  639  	case fldles_op:
  640  	case fldled_op:
  641  	case fstles_op:
  642  	case fstled_op:
  643  		badv = regs->regs[insn.reg3_format.rj];
  644  		upper = regs->regs[insn.reg3_format.rk];
  645  		break;
  646  
  647  	case ldgtb_op:
  648  	case ldgth_op:
  649  	case ldgtw_op:
  650  	case ldgtd_op:
  651  	case stgtb_op:
  652  	case stgth_op:
  653  	case stgtw_op:
  654  	case stgtd_op:
  655  	case fldgts_op:
  656  	case fldgtd_op:
  657  	case fstgts_op:
  658  	case fstgtd_op:
  659  		badv = regs->regs[insn.reg3_format.rj];
  660  		lower = regs->regs[insn.reg3_format.rk];
  661  		break;
  662  	}
  663  
  664  	force_sig_bnderr((void __user *)badv, (void __user *)lower, (void __user *)upper);
  665  
  666  out:
  667  	if (regs->csr_prmd & CSR_PRMD_PIE)
  668  		local_irq_disable();
  669  
  670  	irqentry_exit(regs, state);
  671  	return;
  672  
  673  bad_era:
...（其余7行省略）
```

【force_sig的代码（kernel/signal.c）】
```c
 1652  void force_sig(int sig)  {
 1653  	struct kernel_siginfo info;
 1654  
 1655  	clear_siginfo(&info);
 1656  	info.si_signo = sig;
 1657  	info.si_errno = 0;
 1658  	info.si_code = SI_KERNEL;
 1659  	info.si_pid = 0;
 1660  	info.si_uid = 0;
 1661  	force_sig_info(&info);
 1662  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

## L15

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.5）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/mm/fault.c中的do_page_fault

【程序给出的理由】sleep B:trap: line 259 __do_page_fault -> mutex_lock

【调用链】__do_page_fault（arch/loongarch/mm/fault.c第210行调用handle_mm_fault） → handle_mm_fault（mm/memory.c第5231行调用hugetlb_fault） → hugetlb_fault（mm/hugetlb.c第6104行调用mutex_lock）

【do_page_fault的代码】
```c
  252  asmlinkage void __kprobes do_page_fault(struct pt_regs *regs, 			unsigned long write, unsigned long address)  {
  253  	irqentry_state_t state = irqentry_enter(regs);
  254  
  255  	/* Enable interrupt if enabled in parent context */
  256  	if (likely(regs->csr_prmd & CSR_PRMD_PIE))
  257  		local_irq_enable();
  258  
  259  	__do_page_fault(regs, write, address);
  260  
  261  	local_irq_disable();
  262  
  263  	irqentry_exit(regs, state);
  264  }
```

【__do_page_fault的代码（arch/loongarch/mm/fault.c）】
```c
  130  static void __kprobes __do_page_fault(struct pt_regs *regs, 			unsigned long write, unsigned long address)  {
  131  	int si_code = SEGV_MAPERR;
  132  	unsigned int flags = FAULT_FLAG_DEFAULT;
  133  	struct task_struct *tsk = current;
  134  	struct mm_struct *mm = tsk->mm;
  135  	struct vm_area_struct *vma = NULL;
  136  	vm_fault_t fault;
  137  
  138  	if (kprobe_page_fault(regs, current->thread.trap_nr))
  139  		return;
  140  
  141  	/*
  142  	 * We fault-in kernel-space virtual memory on-demand. The
  143  	 * 'reference' page table is init_mm.pgd.
  144  	 *
  145  	 * NOTE! We MUST NOT take any locks for this case. We may
  146  	 * be in an interrupt or a critical region, and should
  147  	 * only copy the information from the master page table,
  148  	 * nothing more.
  149  	 */
  150  	if (address & __UA_LIMIT) {
  151  		if (!user_mode(regs))
  152  			no_context(regs, address);
  153  		else
  154  			do_sigsegv(regs, write, address, si_code);
  155  		return;
  156  	}
  157  
  158  	/*
  159  	 * If we're in an interrupt or have no user
  160  	 * context, we must not take the fault..
  161  	 */
  162  	if (faulthandler_disabled() || !mm) {
  163  		do_sigsegv(regs, write, address, si_code);
  164  		return;
  165  	}
  166  
  167  	if (user_mode(regs))
  168  		flags |= FAULT_FLAG_USER;
  169  
  170  	perf_sw_event(PERF_COUNT_SW_PAGE_FAULTS, 1, regs, address);
  171  retry:
  172  	vma = lock_mm_and_find_vma(mm, address, regs);
  173  	if (unlikely(!vma))
  174  		goto bad_area_nosemaphore;
  175  	goto good_area;
  176  
  177  /*
  178   * Something tried to access memory that isn't in our memory map..
  179   * Fix it, but check if it's kernel or user first..
  180   */
  181  bad_area:
  182  	mmap_read_unlock(mm);
  183  bad_area_nosemaphore:
  184  	do_sigsegv(regs, write, address, si_code);
  185  	return;
  186  
  187  /*
  188   * Ok, we have a good vm_area for this memory access, so
  189   * we can handle it..
  190   */
  191  good_area:
  192  	si_code = SEGV_ACCERR;
  193  
  194  	if (write) {
  195  		flags |= FAULT_FLAG_WRITE;
  196  		if (!(vma->vm_flags & VM_WRITE))
  197  			goto bad_area;
  198  	} else {
  199  		if (!(vma->vm_flags & VM_READ) && address != exception_era(regs))
  200  			goto bad_area;
  201  		if (!(vma->vm_flags & VM_EXEC) && address == exception_era(regs))
  202  			goto bad_area;
  203  	}
  204  
  205  	/*
  206  	 * If for any reason at all we couldn't handle the fault,
  207  	 * make sure we exit gracefully rather than endlessly redo
  208  	 * the fault.
  209  	 */
...（其余39行省略）
```

【handle_mm_fault的代码（mm/memory.c）】
```c
 5203  vm_fault_t handle_mm_fault(struct vm_area_struct *vma, unsigned long address, 			   unsigned int flags, struct pt_regs *regs)  {
 5204  	/* If the fault handler drops the mmap_lock, vma may be freed */
 5205  	struct mm_struct *mm = vma->vm_mm;
 5206  	vm_fault_t ret;
 5207  
 5208  	__set_current_state(TASK_RUNNING);
 5209  
 5210  	ret = sanitize_fault_flags(vma, &flags);
 5211  	if (ret)
 5212  		goto out;
 5213  
 5214  	if (!arch_vma_access_permitted(vma, flags & FAULT_FLAG_WRITE,
 5215  					    flags & FAULT_FLAG_INSTRUCTION,
 5216  					    flags & FAULT_FLAG_REMOTE)) {
 5217  		ret = VM_FAULT_SIGSEGV;
 5218  		goto out;
 5219  	}
 5220  
 5221  	/*
 5222  	 * Enable the memcg OOM handling for faults triggered in user
 5223  	 * space.  Kernel faults are handled more gracefully.
 5224  	 */
 5225  	if (flags & FAULT_FLAG_USER)
 5226  		mem_cgroup_enter_user_fault();
 5227  
 5228  	lru_gen_enter_fault(vma);
 5229  
 5230  	if (unlikely(is_vm_hugetlb_page(vma)))
 5231  		ret = hugetlb_fault(vma->vm_mm, vma, address, flags);
 5232  	else
 5233  		ret = __handle_mm_fault(vma, address, flags);
 5234  
 5235  	lru_gen_exit_fault();
 5236  
 5237  	if (flags & FAULT_FLAG_USER) {
 5238  		mem_cgroup_exit_user_fault();
 5239  		/*
 5240  		 * The task may have entered a memcg OOM situation but
 5241  		 * if the allocation error was handled gracefully (no
 5242  		 * VM_FAULT_OOM), there is no need to kill anything.
 5243  		 * Just clean up the OOM state peacefully.
 5244  		 */
 5245  		if (task_in_memcg_oom(current) && !(ret & VM_FAULT_OOM))
 5246  			mem_cgroup_oom_synchronize(false);
 5247  	}
 5248  out:
 5249  	mm_account_fault(mm, regs, address, flags, ret);
 5250  
 5251  	return ret;
 5252  }
```

【hugetlb_fault的代码（mm/hugetlb.c）】
```c
 6083  vm_fault_t hugetlb_fault(struct mm_struct *mm, struct vm_area_struct *vma, 			unsigned long address, unsigned int flags)  {
 6084  	pte_t *ptep, entry;
 6085  	spinlock_t *ptl;
 6086  	vm_fault_t ret;
 6087  	u32 hash;
 6088  	pgoff_t idx;
 6089  	struct folio *folio = NULL;
 6090  	struct folio *pagecache_folio = NULL;
 6091  	struct hstate *h = hstate_vma(vma);
 6092  	struct address_space *mapping;
 6093  	int need_wait_lock = 0;
 6094  	unsigned long haddr = address & huge_page_mask(h);
 6095  
 6096  	/*
 6097  	 * Serialize hugepage allocation and instantiation, so that we don't
 6098  	 * get spurious allocation failures if two CPUs race to instantiate
 6099  	 * the same page in the page cache.
 6100  	 */
 6101  	mapping = vma->vm_file->f_mapping;
 6102  	idx = vma_hugecache_offset(h, vma, haddr);
 6103  	hash = hugetlb_fault_mutex_hash(mapping, idx);
 6104  	mutex_lock(&hugetlb_fault_mutex_table[hash]);
 6105  
 6106  	/*
 6107  	 * Acquire vma lock before calling huge_pte_alloc and hold
 6108  	 * until finished with ptep.  This prevents huge_pmd_unshare from
 6109  	 * being called elsewhere and making the ptep no longer valid.
 6110  	 */
 6111  	hugetlb_vma_lock_read(vma);
 6112  	ptep = huge_pte_alloc(mm, vma, haddr, huge_page_size(h));
 6113  	if (!ptep) {
 6114  		hugetlb_vma_unlock_read(vma);
 6115  		mutex_unlock(&hugetlb_fault_mutex_table[hash]);
 6116  		return VM_FAULT_OOM;
 6117  	}
 6118  
 6119  	entry = huge_ptep_get(ptep);
 6120  	/* PTE markers should be handled the same way as none pte */
 6121  	if (huge_pte_none_mostly(entry))
 6122  		/*
 6123  		 * hugetlb_no_page will drop vma lock and hugetlb fault
 6124  		 * mutex internally, which make us return immediately.
 6125  		 */
 6126  		return hugetlb_no_page(mm, vma, mapping, idx, address, ptep,
 6127  				      entry, flags);
 6128  
 6129  	ret = 0;
 6130  
 6131  	/*
 6132  	 * entry could be a migration/hwpoison entry at this point, so this
 6133  	 * check prevents the kernel from going below assuming that we have
 6134  	 * an active hugepage in pagecache. This goto expects the 2nd page
 6135  	 * fault, and is_hugetlb_entry_(migration|hwpoisoned) check will
 6136  	 * properly handle it.
 6137  	 */
 6138  	if (!pte_present(entry)) {
 6139  		if (unlikely(is_hugetlb_entry_migration(entry))) {
 6140  			/*
 6141  			 * Release the hugetlb fault lock now, but retain
 6142  			 * the vma lock, because it is needed to guard the
 6143  			 * huge_pte_lockptr() later in
 6144  			 * migration_entry_wait_huge(). The vma lock will
 6145  			 * be released there.
 6146  			 */
 6147  			mutex_unlock(&hugetlb_fault_mutex_table[hash]);
 6148  			migration_entry_wait_huge(vma, ptep);
 6149  			return 0;
 6150  		} else if (unlikely(is_hugetlb_entry_hwpoisoned(entry)))
 6151  			ret = VM_FAULT_HWPOISON_LARGE |
 6152  			    VM_FAULT_SET_HINDEX(hstate_index(h));
 6153  		goto out_mutex;
 6154  	}
 6155  
 6156  	/*
 6157  	 * If we are going to COW/unshare the mapping later, we examine the
 6158  	 * pending reservations for this page now. This will ensure that any
 6159  	 * allocations necessary to record that reservation occur outside the
 6160  	 * spinlock. Also lookup the pagecache page now as it is used to
 6161  	 * determine if a reservation has been consumed.
 6162  	 */
...（其余92行省略）
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

## L16

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_lbt

【程序给出的理由】noinstr N2: line 999 init_restore_lbt -> instrumentable callee

【调用链】init_restore_lbt（arch/loongarch/kernel/traps.c第965行调用）

【do_lbt的代码】
```c
  979  asmlinkage void noinstr do_lbt(struct pt_regs *regs)  {
  980  	irqentry_state_t state = irqentry_enter(regs);
  981  
  982  	/*
  983  	 * BTD (Binary Translation Disable exception) can be triggered
  984  	 * during FP save/restore if TM (Top Mode) is on, which may
  985  	 * cause irq_enable during 'switch_to'. To avoid this situation
  986  	 * (including the user using 'MOVGR2GCSR' to turn on TM, which
  987  	 * will not trigger the BTE), we need to check PRMD first.
  988  	 */
  989  	if (regs->csr_prmd & CSR_PRMD_PIE)
  990  		local_irq_enable();
  991  
  992  	if (!cpu_has_lbt) {
  993  		force_sig(SIGILL);
  994  		goto out;
  995  	}
  996  	BUG_ON(is_lbt_enabled());
  997  
  998  	preempt_disable();
  999  	init_restore_lbt();
 1000  	preempt_enable();
 1001  
 1002  out:
 1003  	if (regs->csr_prmd & CSR_PRMD_PIE)
 1004  		local_irq_disable();
 1005  
 1006  	irqentry_exit(regs, state);
 1007  }
```

【init_restore_lbt的代码（arch/loongarch/kernel/traps.c）】
```c
  965  static void init_restore_lbt(void)  {
  966  	if (!thread_lbt_context_live()) {
  967  		/* First time LBT context user */
  968  		init_lbt();
  969  		set_thread_flag(TIF_LBT_CTX_LIVE);
  970  	} else {
  971  		if (!is_lbt_owner())
  972  			own_lbt_inatomic(1);
  973  	}
  974  
  975  	BUG_ON(!is_lbt_enabled());
  976  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

## L17

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.7）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】推测执行越界规则：函数对一个可能来自客体（虚拟机）或用户的下标做了上界检查，随后用它访问数组，却没有用array_index_nospec，可能被推测执行越界利用（Spectre-v1）。

【被标记的位置】arch/loongarch/kvm/main.c中的get_gcsr_flag

【程序给出的理由】line 22: [csr] after bound check at line 21, no array_index_nospec

【get_gcsr_flag的代码】
```c
   20  int get_gcsr_flag(int csr)  {
   21  	if (csr < CSR_MAX_NUMS)
   22  		return gcsr_flag[csr];
   23  
   24  	return INVALID_GCSR;
   25  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

## L18

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.13）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kvm/intc/eiointc.c中的kvm_eiointc_regs_access

【程序给出的理由】sleep A:spin: line 877 copy_to_user -> copy_to_user

【kvm_eiointc_regs_access的代码】
```c
  826  static int kvm_eiointc_regs_access(struct kvm_device *dev, 					struct kvm_device_attr *attr, 					bool is_write)  {
  827  	int addr, cpuid, offset, ret = 0;
  828  	unsigned long flags;
  829  	void *p = NULL;
  830  	void __user *data;
  831  	struct loongarch_eiointc *s;
  832  
  833  	s = dev->kvm->arch.eiointc;
  834  	addr = attr->attr;
  835  	cpuid = addr >> 16;
  836  	addr &= 0xffff;
  837  	data = (void __user *)attr->addr;
  838  	switch (addr) {
  839  	case EIOINTC_NODETYPE_START ... EIOINTC_NODETYPE_END:
  840  		offset = (addr - EIOINTC_NODETYPE_START) / 4;
  841  		p = &s->nodetype.reg_u32[offset];
  842  		break;
  843  	case EIOINTC_IPMAP_START ... EIOINTC_IPMAP_END:
  844  		offset = (addr - EIOINTC_IPMAP_START) / 4;
  845  		p = &s->ipmap.reg_u32[offset];
  846  		break;
  847  	case EIOINTC_ENABLE_START ... EIOINTC_ENABLE_END:
  848  		offset = (addr - EIOINTC_ENABLE_START) / 4;
  849  		p = &s->enable.reg_u32[offset];
  850  		break;
  851  	case EIOINTC_BOUNCE_START ... EIOINTC_BOUNCE_END:
  852  		offset = (addr - EIOINTC_BOUNCE_START) / 4;
  853  		p = &s->bounce.reg_u32[offset];
  854  		break;
  855  	case EIOINTC_ISR_START ... EIOINTC_ISR_END:
  856  		offset = (addr - EIOINTC_ISR_START) / 4;
  857  		p = &s->isr.reg_u32[offset];
  858  		break;
  859  	case EIOINTC_COREISR_START ... EIOINTC_COREISR_END:
  860  		offset = (addr - EIOINTC_COREISR_START) / 4;
  861  		p = &s->coreisr.reg_u32[cpuid][offset];
  862  		break;
  863  	case EIOINTC_COREMAP_START ... EIOINTC_COREMAP_END:
  864  		offset = (addr - EIOINTC_COREMAP_START) / 4;
  865  		p = &s->coremap.reg_u32[offset];
  866  		break;
  867  	default:
  868  		kvm_err("%s: unknown eiointc register, addr = %d\n", __func__, addr);
  869  		return -EINVAL;
  870  	}
  871  
  872  	spin_lock_irqsave(&s->lock, flags);
  873  	if (is_write) {
  874  		if (copy_from_user(p, data, 4))
  875  			ret = -EFAULT;
  876  	} else {
  877  		if (copy_to_user(data, p, 4))
  878  			ret = -EFAULT;
  879  	}
  880  	spin_unlock_irqrestore(&s->lock, flags);
  881  
  882  	return ret;
  883  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

## L19

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.13）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kvm/intc/eiointc.c中的kvm_eiointc_sw_status_access

【程序给出的理由】sleep A:spin: line 919 copy_to_user -> copy_to_user

【kvm_eiointc_sw_status_access的代码】
```c
  888  static int kvm_eiointc_sw_status_access(struct kvm_device *dev, 					struct kvm_device_attr *attr, 					bool is_write)  {
  889  	int addr, ret = 0;
  890  	unsigned long flags;
  891  	void *p = NULL;
  892  	void __user *data;
  893  	struct loongarch_eiointc *s;
  894  
  895  	s = dev->kvm->arch.eiointc;
  896  	addr = attr->attr;
  897  	addr &= 0xffff;
  898  
  899  	data = (void __user *)attr->addr;
  900  	switch (addr) {
  901  	case KVM_DEV_LOONGARCH_EXTIOI_SW_STATUS_NUM_CPU:
  902  		p = &s->num_cpu;
  903  		break;
  904  	case KVM_DEV_LOONGARCH_EXTIOI_SW_STATUS_FEATURE:
  905  		p = &s->features;
  906  		break;
  907  	case KVM_DEV_LOONGARCH_EXTIOI_SW_STATUS_STATE:
  908  		p = &s->status;
  909  		break;
  910  	default:
  911  		kvm_err("%s: unknown eiointc register, addr = %d\n", __func__, addr);
  912  		return -EINVAL;
  913  	}
  914  	spin_lock_irqsave(&s->lock, flags);
  915  	if (is_write) {
  916  		if (copy_from_user(p, data, 4))
  917  			ret = -EFAULT;
  918  	} else {
  919  		if (copy_to_user(data, p, 4))
  920  			ret = -EFAULT;
  921  	}
  922  	spin_unlock_irqrestore(&s->lock, flags);
  923  
  924  	return ret;
  925  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

## L20

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.13）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】同一约定规则：公共代码调用、各架构各自实现的函数中，arm64、x86、RISC-V三个实现都调用了某个函数，LoongArch的实现没有。

【被标记的位置】arch/loongarch/kvm/vm.c中的kvm_arch_irqchip_in_kernel

【程序给出的理由】all three references call ['irqchip_in_kernel'], loongarch does not

【kvm_arch_irqchip_in_kernel的代码】
```c
  191  bool kvm_arch_irqchip_in_kernel(struct kvm *kvm)  {
  192  	return (kvm->arch.ipi && kvm->arch.eiointc && kvm->arch.pch_pic);
  193  }
```

【参照：arm64的kvm_arch_irqchip_in_kernel（arch/arm64/kvm/arm.c）】
```c
 2704  bool kvm_arch_irqchip_in_kernel(struct kvm *kvm)  {
 2705  	return irqchip_in_kernel(kvm);
 2706  }
```

【参照：x86的kvm_arch_irqchip_in_kernel（arch/x86/kvm/irq.c）】
```c
  175  bool kvm_arch_irqchip_in_kernel(struct kvm *kvm)  {
  176  	return irqchip_in_kernel(kvm);
  177  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

## L21

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v7.0）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/smp.c中的loongson_cpu_disable

【程序给出的理由】sleep A:irq: line 460 irq_migrate_all_off_this_cpu -> schedule_work

【调用链】irq_migrate_all_off_this_cpu（kernel/irq/cpuhotplug.c第183行调用irq_affinity_schedule_notify_work） → irq_affinity_schedule_notify_work（kernel/irq/manage.c第370行调用schedule_work）

【loongson_cpu_disable的代码】
```c
  445  int loongson_cpu_disable(void)  {
  446  	unsigned long flags;
  447  	unsigned int cpu = smp_processor_id();
  448  
  449  	if (io_master(cpu))
  450  		return -EBUSY;
  451  
  452  #ifdef CONFIG_NUMA
  453  	numa_remove_cpu(cpu);
  454  #endif
  455  	set_cpu_online(cpu, false);
  456  	clear_cpu_sibling_map(cpu);
  457  	clear_cpu_llc_shared_map(cpu);
  458  	calculate_cpu_foreign_map();
  459  	local_irq_save(flags);
  460  	irq_migrate_all_off_this_cpu();
  461  	clear_csr_ecfg(ECFG0_IM);
  462  	local_irq_restore(flags);
  463  	local_flush_tlb_all();
  464  
  465  	return 0;
  466  }
```

【irq_migrate_all_off_this_cpu的代码（kernel/irq/cpuhotplug.c）】
```c
  172  void irq_migrate_all_off_this_cpu(void)  {
  173  	struct irq_desc *desc;
  174  	unsigned int irq;
  175  
  176  	for_each_active_irq(irq) {
  177  		bool affinity_broken;
  178  
  179  		desc = irq_to_desc(irq);
  180  		scoped_guard(raw_spinlock, &desc->lock) {
  181  			affinity_broken = migrate_one_irq(desc);
  182  			if (affinity_broken && desc->affinity_notify)
  183  				irq_affinity_schedule_notify_work(desc);
  184  		}
  185  		if (affinity_broken) {
  186  			pr_debug_ratelimited("IRQ %u: no longer affine to CPU%u\n",
  187  					    irq, smp_processor_id());
  188  		}
  189  	}
  190  }
```

【irq_affinity_schedule_notify_work的代码（kernel/irq/manage.c）】
```c
  366  void irq_affinity_schedule_notify_work(struct irq_desc *desc)  {
  367  	lockdep_assert_held(&desc->lock);
  368  
  369  	kref_get(&desc->affinity_notify->kref);
  370  	if (!schedule_work(&desc->affinity_notify->work)) {
  371  		/* Work was already scheduled, drop our extra ref */
  372  		kref_put(&desc->affinity_notify->kref, desc->affinity_notify->release);
  373  	}
  374  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M00

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kvm/vz.c中的_kvm_vz_restore_htimer

【程序给出的理由】rt A:irq: line 398 kvm_mips_freeze_hrtimer -> spin_lock_bh

【调用链】kvm_mips_freeze_hrtimer（arch/mips/kvm/emulate.c第477行调用hrtimer_cancel） → hrtimer_cancel（kernel/time/hrtimer.c第1446行调用hrtimer_cancel_wait_running） → hrtimer_cancel_wait_running（kernel/time/hrtimer.c第1415行调用spin_lock_bh）

【_kvm_vz_restore_htimer的代码】
```c
  389  static void _kvm_vz_restore_htimer(struct kvm_vcpu *vcpu, 				   u32 compare, u32 cause)  {
  390  	u32 start_count, after_count;
  391  	unsigned long flags;
  392  
  393  	/*
  394  	 * Freeze the soft-timer and sync the guest CP0_Count with it. We do
  395  	 * this with interrupts disabled to avoid latency.
  396  	 */
  397  	local_irq_save(flags);
  398  	kvm_mips_freeze_hrtimer(vcpu, &start_count);
  399  	write_c0_gtoffset(start_count - read_c0_count());
  400  	local_irq_restore(flags);
  401  
  402  	/* restore guest CP0_Cause, as TI may already be set */
  403  	back_to_back_c0_hazard();
  404  	write_gc0_cause(cause);
  405  
  406  	/*
  407  	 * The above sequence isn't atomic and would result in lost timer
  408  	 * interrupts if we're not careful. Detect if a timer interrupt is due
  409  	 * and assert it.
  410  	 */
  411  	back_to_back_c0_hazard();
  412  	after_count = read_gc0_count();
  413  	if (after_count - start_count > compare - start_count - 1)
  414  		kvm_vz_queue_irq(vcpu, MIPS_EXC_INT_TIMER);
  415  }
```

【kvm_mips_freeze_hrtimer的代码（arch/mips/kvm/emulate.c）】
```c
  473  ktime_t kvm_mips_freeze_hrtimer(struct kvm_vcpu *vcpu, u32 *count)  {
  474  	ktime_t now;
  475  
  476  	/* stop hrtimer before finding time */
  477  	hrtimer_cancel(&vcpu->arch.comparecount_timer);
  478  	now = ktime_get();
  479  
  480  	/* find count at this point and handle pending hrtimer */
  481  	*count = kvm_mips_read_count_running(vcpu, now);
  482  
  483  	return now;
  484  }
```

【hrtimer_cancel的代码（kernel/time/hrtimer.c）】
```c
 1439  int hrtimer_cancel(struct hrtimer *timer)  {
 1440  	int ret;
 1441  
 1442  	do {
 1443  		ret = hrtimer_try_to_cancel(timer);
 1444  
 1445  		if (ret < 0)
 1446  			hrtimer_cancel_wait_running(timer);
 1447  	} while (ret < 0);
 1448  	return ret;
 1449  }
```

【hrtimer_cancel_wait_running的代码（kernel/time/hrtimer.c）】
```c
 1394  void hrtimer_cancel_wait_running(const struct hrtimer *timer)  {
 1395  	/* Lockless read. Prevent the compiler from reloading it below */
 1396  	struct hrtimer_clock_base *base = READ_ONCE(timer->base);
 1397  
 1398  	/*
 1399  	 * Just relax if the timer expires in hard interrupt context or if
 1400  	 * it is currently on the migration base.
 1401  	 */
 1402  	if (!timer->is_soft || is_migration_base(base)) {
 1403  		cpu_relax();
 1404  		return;
 1405  	}
 1406  
 1407  	/*
 1408  	 * Mark the base as contended and grab the expiry lock, which is
 1409  	 * held by the softirq across the timer callback. Drop the lock
 1410  	 * immediately so the softirq can expire the next timer. In theory
 1411  	 * the timer could already be running again, but that's more than
 1412  	 * unlikely and just causes another wait loop.
 1413  	 */
 1414  	atomic_inc(&base->cpu_base->timer_waiters);
 1415  	spin_lock_bh(&base->cpu_base->softirq_expiry_lock);
 1416  	atomic_dec(&base->cpu_base->timer_waiters);
 1417  	spin_unlock_bh(&base->cpu_base->softirq_expiry_lock);
 1418  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M01

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/idle.c中的arch_cpu_idle

【程序给出的理由】noinstr N1: line 245 arch_cpu_idle -> called from noinstr/__cpuidle

【arch_cpu_idle的代码】
```c
  245  void arch_cpu_idle(void)  {
  246  	if (cpu_wait)
  247  		cpu_wait();
  248  	else
  249  		raw_local_irq_enable();
  250  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M02

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/crash.c中的default_machine_crash_shutdown

【程序给出的理由】sleep A:irq: line 101 crash_kexec_prepare_cpus -> smp_call_function

【调用链】crash_kexec_prepare_cpus（arch/mips/kernel/crash.c第66行调用smp_call_function）

【default_machine_crash_shutdown的代码】
```c
   97  void default_machine_crash_shutdown(struct pt_regs *regs)  {
   98  	local_irq_disable();
   99  	crashing_cpu = smp_processor_id();
  100  	crash_save_cpu(regs, crashing_cpu);
  101  	crash_kexec_prepare_cpus();
  102  	cpumask_set_cpu(crashing_cpu, &cpus_in_crash);
  103  }
```

【crash_kexec_prepare_cpus的代码（arch/mips/kernel/crash.c）】
```c
   56  static void crash_kexec_prepare_cpus(void)  {
   57  	static int cpus_stopped;
   58  	unsigned int msecs;
   59  	unsigned int ncpus;
   60  
   61  	if (cpus_stopped)
   62  		return;
   63  
   64  	ncpus = num_online_cpus() - 1;/* Excluding the panic cpu */
   65  
   66  	smp_call_function(crash_shutdown_secondary, NULL, 0);
   67  	smp_wmb();
   68  
   69  	/*
   70  	 * The crash CPU sends an IPI and wait for other CPUs to
   71  	 * respond. Delay of at least 10 seconds.
   72  	 */
   73  	pr_emerg("Sending IPI to other cpus...\n");
   74  	msecs = 10000;
   75  	while ((cpumask_weight(&cpus_in_crash) < ncpus) && (--msecs > 0)) {
   76  		cpu_relax();
   77  		mdelay(1);
   78  	}
   79  
   80  	cpus_stopped = 1;
   81  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M03

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/traps.c中的die

【程序给出的理由】sleep A:raw: line 407 bust_spinlocks -> might_sleep

【调用链】bust_spinlocks（lib/bust_spinlocks.c第25行调用console_unblank） → console_unblank（kernel/printk/printk.c第2911行调用console_lock） → console_lock（kernel/printk/printk.c第2565行调用might_sleep）

【die的代码】
```c
  395  void __noreturn die(const char *str, struct pt_regs *regs)  {
  396  	static int die_counter;
  397  	int sig = SIGSEGV;
  398  
  399  	oops_enter();
  400  
  401  	if (notify_die(DIE_OOPS, str, regs, 0, current->thread.trap_nr,
  402  		       SIGSEGV) == NOTIFY_STOP)
  403  		sig = 0;
  404  
  405  	console_verbose();
  406  	raw_spin_lock_irq(&die_lock);
  407  	bust_spinlocks(1);
  408  
  409  	printk("%s[#%d]:\n", str, ++die_counter);
  410  	show_registers(regs);
  411  	add_taint(TAINT_DIE, LOCKDEP_NOW_UNRELIABLE);
  412  	raw_spin_unlock_irq(&die_lock);
  413  
  414  	oops_exit();
  415  
  416  	if (in_interrupt())
  417  		panic("Fatal exception in interrupt");
  418  
  419  	if (panic_on_oops)
  420  		panic("Fatal exception");
  421  
  422  	if (regs && kexec_should_crash(current))
  423  		crash_kexec(regs);
  424  
  425  	make_task_dead(sig);
  426  }
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
 2900  void console_unblank(void)  {
 2901  	struct console *c;
 2902  
 2903  	/*
 2904  	 * console_unblank can no longer be called in interrupt context unless
 2905  	 * oops_in_progress is set to 1..
 2906  	 */
 2907  	if (oops_in_progress) {
 2908  		if (down_trylock_console_sem() != 0)
 2909  			return;
 2910  	} else
 2911  		console_lock();
 2912  
 2913  	console_locked = 1;
 2914  	console_may_schedule = 0;
 2915  	for_each_console(c)
 2916  		if ((c->flags & CON_ENABLED) && c->unblank)
 2917  			c->unblank();
 2918  	console_unlock();
 2919  
 2920  	if (!oops_in_progress)
 2921  		pr_flush(1000, true);
 2922  }
```

【console_lock的代码（kernel/printk/printk.c）】
```c
 2564  void console_lock(void)  {
 2565  	might_sleep();
 2566  
 2567  	down_console_sem();
 2568  	if (console_suspended)
 2569  		return;
 2570  	console_locked = 1;
 2571  	console_may_schedule = 1;
 2572  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M04

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/traps.c中的die

【程序给出的理由】sleep A:raw: line 410 show_registers -> get_user

【调用链】show_registers（arch/mips/kernel/traps.c第387行调用show_stacktrace） → show_stacktrace（arch/mips/kernel/traps.c第196行调用__get_addr） → __get_addr（arch/mips/kernel/access-helper.h第7行调用get_user）

【die的代码】
```c
  395  void __noreturn die(const char *str, struct pt_regs *regs)  {
  396  	static int die_counter;
  397  	int sig = SIGSEGV;
  398  
  399  	oops_enter();
  400  
  401  	if (notify_die(DIE_OOPS, str, regs, 0, current->thread.trap_nr,
  402  		       SIGSEGV) == NOTIFY_STOP)
  403  		sig = 0;
  404  
  405  	console_verbose();
  406  	raw_spin_lock_irq(&die_lock);
  407  	bust_spinlocks(1);
  408  
  409  	printk("%s[#%d]:\n", str, ++die_counter);
  410  	show_registers(regs);
  411  	add_taint(TAINT_DIE, LOCKDEP_NOW_UNRELIABLE);
  412  	raw_spin_unlock_irq(&die_lock);
  413  
  414  	oops_exit();
  415  
  416  	if (in_interrupt())
  417  		panic("Fatal exception in interrupt");
  418  
  419  	if (panic_on_oops)
  420  		panic("Fatal exception");
  421  
  422  	if (regs && kexec_should_crash(current))
  423  		crash_kexec(regs);
  424  
  425  	make_task_dead(sig);
  426  }
```

【show_registers的代码（arch/mips/kernel/traps.c）】
```c
  371  void show_registers(struct pt_regs *regs)  {
  372  	const int field = 2 * sizeof(unsigned long);
  373  
  374  	__show_regs(regs);
  375  	print_modules();
  376  	printk("Process %s (pid: %d, threadinfo=%p, task=%p, tls=%0*lx)\n",
  377  	       current->comm, current->pid, current_thread_info(), current,
  378  	      field, current_thread_info()->tp_value);
  379  	if (cpu_has_userlocal) {
  380  		unsigned long tls;
  381  
  382  		tls = read_c0_userlocal();
  383  		if (tls != current_thread_info()->tp_value)
  384  			printk("*HwTLS: %0*lx\n", field, tls);
  385  	}
  386  
  387  	show_stacktrace(current, regs, KERN_DEFAULT, user_mode(regs));
  388  	show_code((void *)regs->cp0_epc, user_mode(regs));
  389  	printk("\n");
  390  }
```

【show_stacktrace的代码（arch/mips/kernel/traps.c）】
```c
  178  static void show_stacktrace(struct task_struct *task, 	const struct pt_regs *regs, const char *loglvl, bool user)  {
  179  	const int field = 2 * sizeof(unsigned long);
  180  	unsigned long stackdata;
  181  	int i;
  182  	unsigned long *sp = (unsigned long *)regs->regs[29];
  183  
  184  	printk("%sStack :", loglvl);
  185  	i = 0;
  186  	while ((unsigned long) sp & (PAGE_SIZE - 1)) {
  187  		if (i && ((i % (64 / field)) == 0)) {
  188  			pr_cont("\n");
  189  			printk("%s       ", loglvl);
  190  		}
  191  		if (i > 39) {
  192  			pr_cont(" ...");
  193  			break;
  194  		}
  195  
  196  		if (__get_addr(&stackdata, sp++, user)) {
  197  			pr_cont(" (Bad stack address)");
  198  			break;
  199  		}
  200  
  201  		pr_cont(" %0*lx", field, stackdata);
  202  		i++;
  203  	}
  204  	pr_cont("\n");
  205  	show_backtrace(task, regs, loglvl, user);
  206  }
```

【__get_addr的代码（arch/mips/kernel/access-helper.h）】
```c
    6  static inline int __get_addr(unsigned long *a, unsigned long *p, bool user)  {
    7  	return user ? get_user(*a, (unsigned long __user *)p) :
    8  		      get_kernel_nofault(*a, p);
    9  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M05

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/unaligned.c中的do_ade

【程序给出的理由】sleep B:trap: line 1492 fixup_exception -> __get_user

【调用链】fixup_exception（arch/mips/mm/extable.c第17行调用exception_epc） → exception_epc（arch/mips/include/asm/branch.h第66行调用__isa_exception_epc） → __isa_exception_epc（arch/mips/kernel/branch.c第35行调用__get_user）

【do_ade的代码】
```c
 1476  asmlinkage void do_ade(struct pt_regs *regs)  {
 1477  	enum ctx_state prev_state;
 1478  	unsigned int *pc;
 1479  
 1480  	prev_state = exception_enter();
 1481  	perf_sw_event(PERF_COUNT_SW_ALIGNMENT_FAULTS,
 1482  			1, regs, regs->cp0_badvaddr);
 1483  
 1484  #ifdef CONFIG_64BIT
 1485  	/*
 1486  	 * check, if we are hitting space between CPU implemented maximum
 1487  	 * virtual user address and 64bit maximum virtual user address
 1488  	 * and do exception handling to get EFAULTs for get_user/put_user
 1489  	 */
 1490  	if ((regs->cp0_badvaddr >= (1UL << cpu_vmbits)) &&
 1491  	    (regs->cp0_badvaddr < XKSSEG)) {
 1492  		if (fixup_exception(regs)) {
 1493  			current->thread.cp0_baduaddr = regs->cp0_badvaddr;
 1494  			return;
 1495  		}
 1496  		goto sigbus;
 1497  	}
 1498  #endif
 1499  
 1500  	/*
 1501  	 * Did we catch a fault trying to load an instruction?
 1502  	 */
 1503  	if (regs->cp0_badvaddr == regs->cp0_epc)
 1504  		goto sigbus;
 1505  
 1506  	if (user_mode(regs) && !test_thread_flag(TIF_FIXADE))
 1507  		goto sigbus;
 1508  	if (unaligned_action == UNALIGNED_ACTION_SIGNAL)
 1509  		goto sigbus;
 1510  
 1511  	/*
 1512  	 * Do branch emulation only if we didn't forward the exception.
 1513  	 * This is all so but ugly ...
 1514  	 */
 1515  
 1516  	/*
 1517  	 * Are we running in microMIPS mode?
 1518  	 */
 1519  	if (get_isa16_mode(regs->cp0_epc)) {
 1520  		/*
 1521  		 * Did we catch a fault trying to load an instruction in
 1522  		 * 16-bit mode?
 1523  		 */
 1524  		if (regs->cp0_badvaddr == msk_isa16_mode(regs->cp0_epc))
 1525  			goto sigbus;
 1526  		if (unaligned_action == UNALIGNED_ACTION_SHOW)
 1527  			show_registers(regs);
 1528  
 1529  		if (cpu_has_mmips) {
 1530  			emulate_load_store_microMIPS(regs,
 1531  				(void __user *)regs->cp0_badvaddr);
 1532  			return;
 1533  		}
 1534  
 1535  		if (cpu_has_mips16) {
 1536  			emulate_load_store_MIPS16e(regs,
 1537  				(void __user *)regs->cp0_badvaddr);
 1538  			return;
 1539  		}
 1540  
 1541  		goto sigbus;
 1542  	}
 1543  
 1544  	if (unaligned_action == UNALIGNED_ACTION_SHOW)
 1545  		show_registers(regs);
 1546  	pc = (unsigned int *)exception_epc(regs);
 1547  
 1548  	emulate_load_store_insn(regs, (void __user *)regs->cp0_badvaddr, pc);
 1549  
 1550  	return;
 1551  
 1552  sigbus:
 1553  	die_if_kernel("Kernel unaligned instruction access", regs);
 1554  	force_sig(SIGBUS);
 1555  
...（其余5行省略）
```

【fixup_exception的代码（arch/mips/mm/extable.c）】
```c
   14  int fixup_exception(struct pt_regs *regs)  {
   15  	const struct exception_table_entry *fixup;
   16  
   17  	fixup = search_exception_tables(exception_epc(regs));
   18  	if (fixup) {
   19  		regs->cp0_epc = fixup->nextinsn;
   20  
   21  		return 1;
   22  	}
   23  
   24  	return 0;
   25  }
```

【exception_epc的代码（arch/mips/include/asm/branch.h）】
```c
   61  static inline unsigned long exception_epc(struct pt_regs *regs)  {
   62  	if (likely(!delay_slot(regs)))
   63  		return regs->cp0_epc;
   64  
   65  	if (get_isa16_mode(regs->cp0_epc))
   66  		return __isa_exception_epc(regs);
   67  
   68  	return regs->cp0_epc + 4;
   69  }
```

【__isa_exception_epc的代码（arch/mips/kernel/branch.c）】
```c
   30  int __isa_exception_epc(struct pt_regs *regs)  {
   31  	unsigned short inst;
   32  	long epc = regs->cp0_epc;
   33  
   34  	/* Calculate exception PC in branch delay slot. */
   35  	if (__get_user(inst, (u16 __user *) msk_isa16_mode(epc))) {
   36  		/* This should never happen because delay slot was checked. */
   37  		force_sig(SIGSEGV);
   38  		return epc;
   39  	}
   40  	if (cpu_has_mips16) {
   41  		union mips16e_instruction inst_mips16e;
   42  
   43  		inst_mips16e.full = inst;
   44  		if (inst_mips16e.ri.opcode == MIPS16e_jal_op)
   45  			epc += 4;
   46  		else
   47  			epc += 2;
   48  	} else if (mm_insn_16bit(inst))
   49  		epc += 2;
   50  	else
   51  		epc += 4;
   52  
   53  	return epc;
   54  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M06

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/unaligned.c中的do_ade

【程序给出的理由】sleep B:trap: line 1548 emulate_load_store_insn -> get_user

【调用链】emulate_load_store_insn（arch/mips/kernel/unaligned.c第127行调用__get_inst32） → __get_inst32（arch/mips/kernel/access-helper.h第18行调用get_user）

【do_ade的代码】
```c
 1476  asmlinkage void do_ade(struct pt_regs *regs)  {
 1477  	enum ctx_state prev_state;
 1478  	unsigned int *pc;
 1479  
 1480  	prev_state = exception_enter();
 1481  	perf_sw_event(PERF_COUNT_SW_ALIGNMENT_FAULTS,
 1482  			1, regs, regs->cp0_badvaddr);
 1483  
 1484  #ifdef CONFIG_64BIT
 1485  	/*
 1486  	 * check, if we are hitting space between CPU implemented maximum
 1487  	 * virtual user address and 64bit maximum virtual user address
 1488  	 * and do exception handling to get EFAULTs for get_user/put_user
 1489  	 */
 1490  	if ((regs->cp0_badvaddr >= (1UL << cpu_vmbits)) &&
 1491  	    (regs->cp0_badvaddr < XKSSEG)) {
 1492  		if (fixup_exception(regs)) {
 1493  			current->thread.cp0_baduaddr = regs->cp0_badvaddr;
 1494  			return;
 1495  		}
 1496  		goto sigbus;
 1497  	}
 1498  #endif
 1499  
 1500  	/*
 1501  	 * Did we catch a fault trying to load an instruction?
 1502  	 */
 1503  	if (regs->cp0_badvaddr == regs->cp0_epc)
 1504  		goto sigbus;
 1505  
 1506  	if (user_mode(regs) && !test_thread_flag(TIF_FIXADE))
 1507  		goto sigbus;
 1508  	if (unaligned_action == UNALIGNED_ACTION_SIGNAL)
 1509  		goto sigbus;
 1510  
 1511  	/*
 1512  	 * Do branch emulation only if we didn't forward the exception.
 1513  	 * This is all so but ugly ...
 1514  	 */
 1515  
 1516  	/*
 1517  	 * Are we running in microMIPS mode?
 1518  	 */
 1519  	if (get_isa16_mode(regs->cp0_epc)) {
 1520  		/*
 1521  		 * Did we catch a fault trying to load an instruction in
 1522  		 * 16-bit mode?
 1523  		 */
 1524  		if (regs->cp0_badvaddr == msk_isa16_mode(regs->cp0_epc))
 1525  			goto sigbus;
 1526  		if (unaligned_action == UNALIGNED_ACTION_SHOW)
 1527  			show_registers(regs);
 1528  
 1529  		if (cpu_has_mmips) {
 1530  			emulate_load_store_microMIPS(regs,
 1531  				(void __user *)regs->cp0_badvaddr);
 1532  			return;
 1533  		}
 1534  
 1535  		if (cpu_has_mips16) {
 1536  			emulate_load_store_MIPS16e(regs,
 1537  				(void __user *)regs->cp0_badvaddr);
 1538  			return;
 1539  		}
 1540  
 1541  		goto sigbus;
 1542  	}
 1543  
 1544  	if (unaligned_action == UNALIGNED_ACTION_SHOW)
 1545  		show_registers(regs);
 1546  	pc = (unsigned int *)exception_epc(regs);
 1547  
 1548  	emulate_load_store_insn(regs, (void __user *)regs->cp0_badvaddr, pc);
 1549  
 1550  	return;
 1551  
 1552  sigbus:
 1553  	die_if_kernel("Kernel unaligned instruction access", regs);
 1554  	force_sig(SIGBUS);
 1555  
...（其余5行省略）
```

【emulate_load_store_insn的代码（arch/mips/kernel/unaligned.c）】
```c
  113  static void emulate_load_store_insn(struct pt_regs *regs, 	void __user *addr, unsigned int *pc)  {
  114  	unsigned long origpc, orig31, value;
  115  	union mips_instruction insn;
  116  	unsigned int res;
  117  	bool user = user_mode(regs);
  118  
  119  	origpc = (unsigned long)pc;
  120  	orig31 = regs->regs[31];
  121  
  122  	perf_sw_event(PERF_COUNT_SW_EMULATION_FAULTS, 1, regs, 0);
  123  
  124  	/*
  125  	 * This load never faults.
  126  	 */
  127  	__get_inst32(&insn.word, pc, user);
  128  
  129  	switch (insn.i_format.opcode) {
  130  		/*
  131  		 * These are instructions that a compiler doesn't generate.  We
  132  		 * can assume therefore that the code is MIPS-aware and
  133  		 * really buggy.  Emulating these instructions would break the
  134  		 * semantics anyway.
  135  		 */
  136  	case ll_op:
  137  	case lld_op:
  138  	case sc_op:
  139  	case scd_op:
  140  
  141  		/*
  142  		 * For these instructions the only way to create an address
  143  		 * error is an attempted access to kernel/supervisor address
  144  		 * space.
  145  		 */
  146  	case ldl_op:
  147  	case ldr_op:
  148  	case lwl_op:
  149  	case lwr_op:
  150  	case sdl_op:
  151  	case sdr_op:
  152  	case swl_op:
  153  	case swr_op:
  154  	case lb_op:
  155  	case lbu_op:
  156  	case sb_op:
  157  		goto sigbus;
  158  
  159  		/*
  160  		 * The remaining opcodes are the ones that are really of
  161  		 * interest.
  162  		 */
  163  	case spec3_op:
  164  		if (insn.dsp_format.func == lx_op) {
  165  			switch (insn.dsp_format.op) {
  166  			case lwx_op:
  167  				if (user && !access_ok(addr, 4))
  168  					goto sigbus;
  169  				LoadW(addr, value, res);
  170  				if (res)
  171  					goto fault;
  172  				compute_return_epc(regs);
  173  				regs->regs[insn.dsp_format.rd] = value;
  174  				break;
  175  			case lhx_op:
  176  				if (user && !access_ok(addr, 2))
  177  					goto sigbus;
  178  				LoadHW(addr, value, res);
  179  				if (res)
  180  					goto fault;
  181  				compute_return_epc(regs);
  182  				regs->regs[insn.dsp_format.rd] = value;
  183  				break;
  184  			default:
  185  				goto sigill;
  186  			}
  187  		}
  188  #ifdef CONFIG_EVA
  189  		else {
  190  			/*
  191  			 * we can land here only from kernel accessing user
  192  			 * memory, so we need to "switch" the address limit to
...（其余373行省略）
```

【__get_inst32的代码（arch/mips/kernel/access-helper.h）】
```c
   17  static inline int __get_inst32(u32 *i, u32 *p, bool user)  {
   18  	return user ? get_user(*i, (u32 __user *)p) : get_kernel_nofault(*i, p);
   19  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M07

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/unaligned.c中的do_ade

【程序给出的理由】sleep B:trap: line 1536 emulate_load_store_MIPS16e -> __get_user

【调用链】emulate_load_store_MIPS16e（arch/mips/kernel/unaligned.c第1213行调用__get_user）

【do_ade的代码】
```c
 1476  asmlinkage void do_ade(struct pt_regs *regs)  {
 1477  	enum ctx_state prev_state;
 1478  	unsigned int *pc;
 1479  
 1480  	prev_state = exception_enter();
 1481  	perf_sw_event(PERF_COUNT_SW_ALIGNMENT_FAULTS,
 1482  			1, regs, regs->cp0_badvaddr);
 1483  
 1484  #ifdef CONFIG_64BIT
 1485  	/*
 1486  	 * check, if we are hitting space between CPU implemented maximum
 1487  	 * virtual user address and 64bit maximum virtual user address
 1488  	 * and do exception handling to get EFAULTs for get_user/put_user
 1489  	 */
 1490  	if ((regs->cp0_badvaddr >= (1UL << cpu_vmbits)) &&
 1491  	    (regs->cp0_badvaddr < XKSSEG)) {
 1492  		if (fixup_exception(regs)) {
 1493  			current->thread.cp0_baduaddr = regs->cp0_badvaddr;
 1494  			return;
 1495  		}
 1496  		goto sigbus;
 1497  	}
 1498  #endif
 1499  
 1500  	/*
 1501  	 * Did we catch a fault trying to load an instruction?
 1502  	 */
 1503  	if (regs->cp0_badvaddr == regs->cp0_epc)
 1504  		goto sigbus;
 1505  
 1506  	if (user_mode(regs) && !test_thread_flag(TIF_FIXADE))
 1507  		goto sigbus;
 1508  	if (unaligned_action == UNALIGNED_ACTION_SIGNAL)
 1509  		goto sigbus;
 1510  
 1511  	/*
 1512  	 * Do branch emulation only if we didn't forward the exception.
 1513  	 * This is all so but ugly ...
 1514  	 */
 1515  
 1516  	/*
 1517  	 * Are we running in microMIPS mode?
 1518  	 */
 1519  	if (get_isa16_mode(regs->cp0_epc)) {
 1520  		/*
 1521  		 * Did we catch a fault trying to load an instruction in
 1522  		 * 16-bit mode?
 1523  		 */
 1524  		if (regs->cp0_badvaddr == msk_isa16_mode(regs->cp0_epc))
 1525  			goto sigbus;
 1526  		if (unaligned_action == UNALIGNED_ACTION_SHOW)
 1527  			show_registers(regs);
 1528  
 1529  		if (cpu_has_mmips) {
 1530  			emulate_load_store_microMIPS(regs,
 1531  				(void __user *)regs->cp0_badvaddr);
 1532  			return;
 1533  		}
 1534  
 1535  		if (cpu_has_mips16) {
 1536  			emulate_load_store_MIPS16e(regs,
 1537  				(void __user *)regs->cp0_badvaddr);
 1538  			return;
 1539  		}
 1540  
 1541  		goto sigbus;
 1542  	}
 1543  
 1544  	if (unaligned_action == UNALIGNED_ACTION_SHOW)
 1545  		show_registers(regs);
 1546  	pc = (unsigned int *)exception_epc(regs);
 1547  
 1548  	emulate_load_store_insn(regs, (void __user *)regs->cp0_badvaddr, pc);
 1549  
 1550  	return;
 1551  
 1552  sigbus:
 1553  	die_if_kernel("Kernel unaligned instruction access", regs);
 1554  	force_sig(SIGBUS);
 1555  
...（其余5行省略）
```

【emulate_load_store_MIPS16e的代码（arch/mips/kernel/unaligned.c）】
```c
 1195  static void emulate_load_store_MIPS16e(struct pt_regs *regs, void __user * addr)  {
 1196  	unsigned long value;
 1197  	unsigned int res;
 1198  	int reg;
 1199  	unsigned long orig31;
 1200  	u16 __user *pc16;
 1201  	unsigned long origpc;
 1202  	union mips16e_instruction mips16inst, oldinst;
 1203  	unsigned int opcode;
 1204  	int extended = 0;
 1205  	bool user = user_mode(regs);
 1206  
 1207  	origpc = regs->cp0_epc;
 1208  	orig31 = regs->regs[31];
 1209  	pc16 = (unsigned short __user *)msk_isa16_mode(origpc);
 1210  	/*
 1211  	 * This load never faults.
 1212  	 */
 1213  	__get_user(mips16inst.full, pc16);
 1214  	oldinst = mips16inst;
 1215  
 1216  	/* skip EXTEND instruction */
 1217  	if (mips16inst.ri.opcode == MIPS16e_extend_op) {
 1218  		extended = 1;
 1219  		pc16++;
 1220  		__get_user(mips16inst.full, pc16);
 1221  	} else if (delay_slot(regs)) {
 1222  		/*  skip jump instructions */
 1223  		/*  JAL/JALX are 32 bits but have OPCODE in first short int */
 1224  		if (mips16inst.ri.opcode == MIPS16e_jal_op)
 1225  			pc16++;
 1226  		pc16++;
 1227  		if (get_user(mips16inst.full, pc16))
 1228  			goto sigbus;
 1229  	}
 1230  
 1231  	opcode = mips16inst.ri.opcode;
 1232  	switch (opcode) {
 1233  	case MIPS16e_i64_op:	/* I64 or RI64 instruction */
 1234  		switch (mips16inst.i64.func) {	/* I64/RI64 func field check */
 1235  		case MIPS16e_ldpc_func:
 1236  		case MIPS16e_ldsp_func:
 1237  			reg = reg16to32[mips16inst.ri64.ry];
 1238  			goto loadDW;
 1239  
 1240  		case MIPS16e_sdsp_func:
 1241  			reg = reg16to32[mips16inst.ri64.ry];
 1242  			goto writeDW;
 1243  
 1244  		case MIPS16e_sdrasp_func:
 1245  			reg = 29;	/* GPRSP */
 1246  			goto writeDW;
 1247  		}
 1248  
 1249  		goto sigbus;
 1250  
 1251  	case MIPS16e_swsp_op:
 1252  		reg = reg16to32[mips16inst.ri.rx];
 1253  		if (extended && cpu_has_mips16e2)
 1254  			switch (mips16inst.ri.imm >> 5) {
 1255  			case 0:		/* SWSP */
 1256  			case 1:		/* SWGP */
 1257  				break;
 1258  			case 2:		/* SHGP */
 1259  				opcode = MIPS16e_sh_op;
 1260  				break;
 1261  			default:
 1262  				goto sigbus;
 1263  			}
 1264  		break;
 1265  
 1266  	case MIPS16e_lwpc_op:
 1267  		reg = reg16to32[mips16inst.ri.rx];
 1268  		break;
 1269  
 1270  	case MIPS16e_lwsp_op:
 1271  		reg = reg16to32[mips16inst.ri.rx];
 1272  		if (extended && cpu_has_mips16e2)
 1273  			switch (mips16inst.ri.imm >> 5) {
 1274  			case 0:		/* LWSP */
...（其余199行省略）
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M08

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/unaligned.c中的do_ade

【程序给出的理由】sleep B:trap: line 1527 show_registers -> get_user

【调用链】show_registers（arch/mips/kernel/traps.c第387行调用show_stacktrace） → show_stacktrace（arch/mips/kernel/traps.c第196行调用__get_addr） → __get_addr（arch/mips/kernel/access-helper.h第7行调用get_user）

【do_ade的代码】
```c
 1476  asmlinkage void do_ade(struct pt_regs *regs)  {
 1477  	enum ctx_state prev_state;
 1478  	unsigned int *pc;
 1479  
 1480  	prev_state = exception_enter();
 1481  	perf_sw_event(PERF_COUNT_SW_ALIGNMENT_FAULTS,
 1482  			1, regs, regs->cp0_badvaddr);
 1483  
 1484  #ifdef CONFIG_64BIT
 1485  	/*
 1486  	 * check, if we are hitting space between CPU implemented maximum
 1487  	 * virtual user address and 64bit maximum virtual user address
 1488  	 * and do exception handling to get EFAULTs for get_user/put_user
 1489  	 */
 1490  	if ((regs->cp0_badvaddr >= (1UL << cpu_vmbits)) &&
 1491  	    (regs->cp0_badvaddr < XKSSEG)) {
 1492  		if (fixup_exception(regs)) {
 1493  			current->thread.cp0_baduaddr = regs->cp0_badvaddr;
 1494  			return;
 1495  		}
 1496  		goto sigbus;
 1497  	}
 1498  #endif
 1499  
 1500  	/*
 1501  	 * Did we catch a fault trying to load an instruction?
 1502  	 */
 1503  	if (regs->cp0_badvaddr == regs->cp0_epc)
 1504  		goto sigbus;
 1505  
 1506  	if (user_mode(regs) && !test_thread_flag(TIF_FIXADE))
 1507  		goto sigbus;
 1508  	if (unaligned_action == UNALIGNED_ACTION_SIGNAL)
 1509  		goto sigbus;
 1510  
 1511  	/*
 1512  	 * Do branch emulation only if we didn't forward the exception.
 1513  	 * This is all so but ugly ...
 1514  	 */
 1515  
 1516  	/*
 1517  	 * Are we running in microMIPS mode?
 1518  	 */
 1519  	if (get_isa16_mode(regs->cp0_epc)) {
 1520  		/*
 1521  		 * Did we catch a fault trying to load an instruction in
 1522  		 * 16-bit mode?
 1523  		 */
 1524  		if (regs->cp0_badvaddr == msk_isa16_mode(regs->cp0_epc))
 1525  			goto sigbus;
 1526  		if (unaligned_action == UNALIGNED_ACTION_SHOW)
 1527  			show_registers(regs);
 1528  
 1529  		if (cpu_has_mmips) {
 1530  			emulate_load_store_microMIPS(regs,
 1531  				(void __user *)regs->cp0_badvaddr);
 1532  			return;
 1533  		}
 1534  
 1535  		if (cpu_has_mips16) {
 1536  			emulate_load_store_MIPS16e(regs,
 1537  				(void __user *)regs->cp0_badvaddr);
 1538  			return;
 1539  		}
 1540  
 1541  		goto sigbus;
 1542  	}
 1543  
 1544  	if (unaligned_action == UNALIGNED_ACTION_SHOW)
 1545  		show_registers(regs);
 1546  	pc = (unsigned int *)exception_epc(regs);
 1547  
 1548  	emulate_load_store_insn(regs, (void __user *)regs->cp0_badvaddr, pc);
 1549  
 1550  	return;
 1551  
 1552  sigbus:
 1553  	die_if_kernel("Kernel unaligned instruction access", regs);
 1554  	force_sig(SIGBUS);
 1555  
...（其余5行省略）
```

【show_registers的代码（arch/mips/kernel/traps.c）】
```c
  371  void show_registers(struct pt_regs *regs)  {
  372  	const int field = 2 * sizeof(unsigned long);
  373  
  374  	__show_regs(regs);
  375  	print_modules();
  376  	printk("Process %s (pid: %d, threadinfo=%p, task=%p, tls=%0*lx)\n",
  377  	       current->comm, current->pid, current_thread_info(), current,
  378  	      field, current_thread_info()->tp_value);
  379  	if (cpu_has_userlocal) {
  380  		unsigned long tls;
  381  
  382  		tls = read_c0_userlocal();
  383  		if (tls != current_thread_info()->tp_value)
  384  			printk("*HwTLS: %0*lx\n", field, tls);
  385  	}
  386  
  387  	show_stacktrace(current, regs, KERN_DEFAULT, user_mode(regs));
  388  	show_code((void *)regs->cp0_epc, user_mode(regs));
  389  	printk("\n");
  390  }
```

【show_stacktrace的代码（arch/mips/kernel/traps.c）】
```c
  178  static void show_stacktrace(struct task_struct *task, 	const struct pt_regs *regs, const char *loglvl, bool user)  {
  179  	const int field = 2 * sizeof(unsigned long);
  180  	unsigned long stackdata;
  181  	int i;
  182  	unsigned long *sp = (unsigned long *)regs->regs[29];
  183  
  184  	printk("%sStack :", loglvl);
  185  	i = 0;
  186  	while ((unsigned long) sp & (PAGE_SIZE - 1)) {
  187  		if (i && ((i % (64 / field)) == 0)) {
  188  			pr_cont("\n");
  189  			printk("%s       ", loglvl);
  190  		}
  191  		if (i > 39) {
  192  			pr_cont(" ...");
  193  			break;
  194  		}
  195  
  196  		if (__get_addr(&stackdata, sp++, user)) {
  197  			pr_cont(" (Bad stack address)");
  198  			break;
  199  		}
  200  
  201  		pr_cont(" %0*lx", field, stackdata);
  202  		i++;
  203  	}
  204  	pr_cont("\n");
  205  	show_backtrace(task, regs, loglvl, user);
  206  }
```

【__get_addr的代码（arch/mips/kernel/access-helper.h）】
```c
    6  static inline int __get_addr(unsigned long *a, unsigned long *p, bool user)  {
    7  	return user ? get_user(*a, (unsigned long __user *)p) :
    8  		      get_kernel_nofault(*a, p);
    9  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M09

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/traps.c中的do_be

【程序给出的理由】sleep B:trap: line 458 exception_epc -> __get_user

【调用链】exception_epc（arch/mips/include/asm/branch.h第66行调用__isa_exception_epc） → __isa_exception_epc（arch/mips/kernel/branch.c第35行调用__get_user）

【do_be的代码】
```c
  448  asmlinkage void do_be(struct pt_regs *regs)  {
  449  	const int field = 2 * sizeof(unsigned long);
  450  	const struct exception_table_entry *fixup = NULL;
  451  	int data = regs->cp0_cause & 4;
  452  	int action = MIPS_BE_FATAL;
  453  	enum ctx_state prev_state;
  454  
  455  	prev_state = exception_enter();
  456  	/* XXX For now.	 Fixme, this searches the wrong table ...  */
  457  	if (data && !user_mode(regs))
  458  		fixup = search_dbe_tables(exception_epc(regs));
  459  
  460  	if (fixup)
  461  		action = MIPS_BE_FIXUP;
  462  
  463  	if (board_be_handler)
  464  		action = board_be_handler(regs, fixup != NULL);
  465  	else
  466  		mips_cm_error_report();
  467  
  468  	switch (action) {
  469  	case MIPS_BE_DISCARD:
  470  		goto out;
  471  	case MIPS_BE_FIXUP:
  472  		if (fixup) {
  473  			regs->cp0_epc = fixup->nextinsn;
  474  			goto out;
  475  		}
  476  		break;
  477  	default:
  478  		break;
  479  	}
  480  
  481  	/*
  482  	 * Assume it would be too dangerous to continue ...
  483  	 */
  484  	printk(KERN_ALERT "%s bus error, epc == %0*lx, ra == %0*lx\n",
  485  	       data ? "Data" : "Instruction",
  486  	       field, regs->cp0_epc, field, regs->regs[31]);
  487  	if (notify_die(DIE_OOPS, "bus error", regs, 0, current->thread.trap_nr,
  488  		       SIGBUS) == NOTIFY_STOP)
  489  		goto out;
  490  
  491  	die_if_kernel("Oops", regs);
  492  	force_sig(SIGBUS);
  493  
  494  out:
  495  	exception_exit(prev_state);
  496  }
```

【exception_epc的代码（arch/mips/include/asm/branch.h）】
```c
   61  static inline unsigned long exception_epc(struct pt_regs *regs)  {
   62  	if (likely(!delay_slot(regs)))
   63  		return regs->cp0_epc;
   64  
   65  	if (get_isa16_mode(regs->cp0_epc))
   66  		return __isa_exception_epc(regs);
   67  
   68  	return regs->cp0_epc + 4;
   69  }
```

【__isa_exception_epc的代码（arch/mips/kernel/branch.c）】
```c
   30  int __isa_exception_epc(struct pt_regs *regs)  {
   31  	unsigned short inst;
   32  	long epc = regs->cp0_epc;
   33  
   34  	/* Calculate exception PC in branch delay slot. */
   35  	if (__get_user(inst, (u16 __user *) msk_isa16_mode(epc))) {
   36  		/* This should never happen because delay slot was checked. */
   37  		force_sig(SIGSEGV);
   38  		return epc;
   39  	}
   40  	if (cpu_has_mips16) {
   41  		union mips16e_instruction inst_mips16e;
   42  
   43  		inst_mips16e.full = inst;
   44  		if (inst_mips16e.ri.opcode == MIPS16e_jal_op)
   45  			epc += 4;
   46  		else
   47  			epc += 2;
   48  	} else if (mm_insn_16bit(inst))
   49  		epc += 2;
   50  	else
   51  		epc += 4;
   52  
   53  	return epc;
   54  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M10

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/traps.c中的do_bp

【程序给出的理由】sleep B:trap: line 1029 exception_epc -> __get_user

【调用链】exception_epc（arch/mips/include/asm/branch.h第66行调用__isa_exception_epc） → __isa_exception_epc（arch/mips/kernel/branch.c第35行调用__get_user）

【do_bp的代码】
```c
 1028  asmlinkage void do_bp(struct pt_regs *regs)  {
 1029  	unsigned long epc = msk_isa16_mode(exception_epc(regs));
 1030  	unsigned int opcode, bcode;
 1031  	enum ctx_state prev_state;
 1032  	bool user = user_mode(regs);
 1033  
 1034  	prev_state = exception_enter();
 1035  	current->thread.trap_nr = (regs->cp0_cause >> 2) & 0x1f;
 1036  	if (get_isa16_mode(regs->cp0_epc)) {
 1037  		u16 instr[2];
 1038  
 1039  		if (__get_inst16(&instr[0], (u16 *)epc, user))
 1040  			goto out_sigsegv;
 1041  
 1042  		if (!cpu_has_mmips) {
 1043  			/* MIPS16e mode */
 1044  			bcode = (instr[0] >> 5) & 0x3f;
 1045  		} else if (mm_insn_16bit(instr[0])) {
 1046  			/* 16-bit microMIPS BREAK */
 1047  			bcode = instr[0] & 0xf;
 1048  		} else {
 1049  			/* 32-bit microMIPS BREAK */
 1050  			if (__get_inst16(&instr[1], (u16 *)(epc + 2), user))
 1051  				goto out_sigsegv;
 1052  			opcode = (instr[0] << 16) | instr[1];
 1053  			bcode = (opcode >> 6) & ((1 << 20) - 1);
 1054  		}
 1055  	} else {
 1056  		if (__get_inst32(&opcode, (u32 *)epc, user))
 1057  			goto out_sigsegv;
 1058  		bcode = (opcode >> 6) & ((1 << 20) - 1);
 1059  	}
 1060  
 1061  	/*
 1062  	 * There is the ancient bug in the MIPS assemblers that the break
 1063  	 * code starts left to bit 16 instead to bit 6 in the opcode.
 1064  	 * Gas is bug-compatible, but not always, grrr...
 1065  	 * We handle both cases with a simple heuristics.  --macro
 1066  	 */
 1067  	if (bcode >= (1 << 10))
 1068  		bcode = ((bcode & ((1 << 10) - 1)) << 10) | (bcode >> 10);
 1069  
 1070  	/*
 1071  	 * notify the kprobe handlers, if instruction is likely to
 1072  	 * pertain to them.
 1073  	 */
 1074  	switch (bcode) {
 1075  	case BRK_UPROBE:
 1076  		if (notify_die(DIE_UPROBE, "uprobe", regs, bcode,
 1077  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
 1078  			goto out;
 1079  		else
 1080  			break;
 1081  	case BRK_UPROBE_XOL:
 1082  		if (notify_die(DIE_UPROBE_XOL, "uprobe_xol", regs, bcode,
 1083  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
 1084  			goto out;
 1085  		else
 1086  			break;
 1087  	case BRK_KPROBE_BP:
 1088  		if (notify_die(DIE_BREAK, "debug", regs, bcode,
 1089  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
 1090  			goto out;
 1091  		else
 1092  			break;
 1093  	case BRK_KPROBE_SSTEPBP:
 1094  		if (notify_die(DIE_SSTEPBP, "single_step", regs, bcode,
 1095  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
 1096  			goto out;
 1097  		else
 1098  			break;
 1099  	default:
 1100  		break;
 1101  	}
 1102  
 1103  	do_trap_or_bp(regs, bcode, TRAP_BRKPT, "Break");
 1104  
 1105  out:
 1106  	exception_exit(prev_state);
 1107  	return;
...（其余5行省略）
```

【exception_epc的代码（arch/mips/include/asm/branch.h）】
```c
   61  static inline unsigned long exception_epc(struct pt_regs *regs)  {
   62  	if (likely(!delay_slot(regs)))
   63  		return regs->cp0_epc;
   64  
   65  	if (get_isa16_mode(regs->cp0_epc))
   66  		return __isa_exception_epc(regs);
   67  
   68  	return regs->cp0_epc + 4;
   69  }
```

【__isa_exception_epc的代码（arch/mips/kernel/branch.c）】
```c
   30  int __isa_exception_epc(struct pt_regs *regs)  {
   31  	unsigned short inst;
   32  	long epc = regs->cp0_epc;
   33  
   34  	/* Calculate exception PC in branch delay slot. */
   35  	if (__get_user(inst, (u16 __user *) msk_isa16_mode(epc))) {
   36  		/* This should never happen because delay slot was checked. */
   37  		force_sig(SIGSEGV);
   38  		return epc;
   39  	}
   40  	if (cpu_has_mips16) {
   41  		union mips16e_instruction inst_mips16e;
   42  
   43  		inst_mips16e.full = inst;
   44  		if (inst_mips16e.ri.opcode == MIPS16e_jal_op)
   45  			epc += 4;
   46  		else
   47  			epc += 2;
   48  	} else if (mm_insn_16bit(inst))
   49  		epc += 2;
   50  	else
   51  		epc += 4;
   52  
   53  	return epc;
   54  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M11

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/traps.c中的do_cpu

【程序给出的理由】sleep B:trap: line 1429 get_user -> get_user

【do_cpu的代码】
```c
 1403  asmlinkage void do_cpu(struct pt_regs *regs)  {
 1404  	enum ctx_state prev_state;
 1405  	unsigned int __user *epc;
 1406  	unsigned long old_epc, old31;
 1407  	unsigned int opcode;
 1408  	unsigned int cpid;
 1409  	int status;
 1410  
 1411  	prev_state = exception_enter();
 1412  	cpid = (regs->cp0_cause >> CAUSEB_CE) & 3;
 1413  
 1414  	if (cpid != 2)
 1415  		die_if_kernel("do_cpu invoked from kernel context!", regs);
 1416  
 1417  	switch (cpid) {
 1418  	case 0:
 1419  		epc = (unsigned int __user *)exception_epc(regs);
 1420  		old_epc = regs->cp0_epc;
 1421  		old31 = regs->regs[31];
 1422  		opcode = 0;
 1423  		status = -1;
 1424  
 1425  		if (unlikely(compute_return_epc(regs) < 0))
 1426  			break;
 1427  
 1428  		if (!get_isa16_mode(regs->cp0_epc)) {
 1429  			if (unlikely(get_user(opcode, epc) < 0))
 1430  				status = SIGSEGV;
 1431  
 1432  			if (!cpu_has_llsc && status < 0)
 1433  				status = simulate_llsc(regs, opcode);
 1434  		}
 1435  
 1436  		if (status < 0)
 1437  			status = SIGILL;
 1438  
 1439  		if (unlikely(status > 0)) {
 1440  			regs->cp0_epc = old_epc;	/* Undo skip-over.  */
 1441  			regs->regs[31] = old31;
 1442  			force_sig(status);
 1443  		}
 1444  
 1445  		break;
 1446  
 1447  #ifdef CONFIG_MIPS_FP_SUPPORT
 1448  	case 3:
 1449  		/*
 1450  		 * The COP3 opcode space and consequently the CP0.Status.CU3
 1451  		 * bit and the CP0.Cause.CE=3 encoding have been removed as
 1452  		 * of the MIPS III ISA.  From the MIPS IV and MIPS32r2 ISAs
 1453  		 * up the space has been reused for COP1X instructions, that
 1454  		 * are enabled by the CP0.Status.CU1 bit and consequently
 1455  		 * use the CP0.Cause.CE=1 encoding for Coprocessor Unusable
 1456  		 * exceptions.  Some FPU-less processors that implement one
 1457  		 * of these ISAs however use this code erroneously for COP1X
 1458  		 * instructions.  Therefore we redirect this trap to the FP
 1459  		 * emulator too.
 1460  		 */
 1461  		if (raw_cpu_has_fpu || !cpu_has_mips_4_5_64_r2_r6) {
 1462  			force_sig(SIGILL);
 1463  			break;
 1464  		}
 1465  		fallthrough;
 1466  	case 1: {
 1467  		void __user *fault_addr;
 1468  		unsigned long fcr31;
 1469  		int err, sig;
 1470  
 1471  		err = enable_restore_fp_context(0);
 1472  
 1473  		if (raw_cpu_has_fpu && !err)
 1474  			break;
 1475  
 1476  		sig = fpu_emulator_cop1Handler(regs, &current->thread.fpu, 0,
 1477  					       &fault_addr);
 1478  
 1479  		/*
 1480  		 * We can't allow the emulated instruction to leave
 1481  		 * any enabled Cause bits set in $fcr31.
 1482  		 */
...（其余23行省略）
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M12

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/traps.c中的do_cpu

【程序给出的理由】sleep B:trap: line 1476 fpu_emulator_cop1Handler -> get_user

【调用链】fpu_emulator_cop1Handler（arch/mips/math-emu/cp1emu.c第2862行调用get_user）

【do_cpu的代码】
```c
 1403  asmlinkage void do_cpu(struct pt_regs *regs)  {
 1404  	enum ctx_state prev_state;
 1405  	unsigned int __user *epc;
 1406  	unsigned long old_epc, old31;
 1407  	unsigned int opcode;
 1408  	unsigned int cpid;
 1409  	int status;
 1410  
 1411  	prev_state = exception_enter();
 1412  	cpid = (regs->cp0_cause >> CAUSEB_CE) & 3;
 1413  
 1414  	if (cpid != 2)
 1415  		die_if_kernel("do_cpu invoked from kernel context!", regs);
 1416  
 1417  	switch (cpid) {
 1418  	case 0:
 1419  		epc = (unsigned int __user *)exception_epc(regs);
 1420  		old_epc = regs->cp0_epc;
 1421  		old31 = regs->regs[31];
 1422  		opcode = 0;
 1423  		status = -1;
 1424  
 1425  		if (unlikely(compute_return_epc(regs) < 0))
 1426  			break;
 1427  
 1428  		if (!get_isa16_mode(regs->cp0_epc)) {
 1429  			if (unlikely(get_user(opcode, epc) < 0))
 1430  				status = SIGSEGV;
 1431  
 1432  			if (!cpu_has_llsc && status < 0)
 1433  				status = simulate_llsc(regs, opcode);
 1434  		}
 1435  
 1436  		if (status < 0)
 1437  			status = SIGILL;
 1438  
 1439  		if (unlikely(status > 0)) {
 1440  			regs->cp0_epc = old_epc;	/* Undo skip-over.  */
 1441  			regs->regs[31] = old31;
 1442  			force_sig(status);
 1443  		}
 1444  
 1445  		break;
 1446  
 1447  #ifdef CONFIG_MIPS_FP_SUPPORT
 1448  	case 3:
 1449  		/*
 1450  		 * The COP3 opcode space and consequently the CP0.Status.CU3
 1451  		 * bit and the CP0.Cause.CE=3 encoding have been removed as
 1452  		 * of the MIPS III ISA.  From the MIPS IV and MIPS32r2 ISAs
 1453  		 * up the space has been reused for COP1X instructions, that
 1454  		 * are enabled by the CP0.Status.CU1 bit and consequently
 1455  		 * use the CP0.Cause.CE=1 encoding for Coprocessor Unusable
 1456  		 * exceptions.  Some FPU-less processors that implement one
 1457  		 * of these ISAs however use this code erroneously for COP1X
 1458  		 * instructions.  Therefore we redirect this trap to the FP
 1459  		 * emulator too.
 1460  		 */
 1461  		if (raw_cpu_has_fpu || !cpu_has_mips_4_5_64_r2_r6) {
 1462  			force_sig(SIGILL);
 1463  			break;
 1464  		}
 1465  		fallthrough;
 1466  	case 1: {
 1467  		void __user *fault_addr;
 1468  		unsigned long fcr31;
 1469  		int err, sig;
 1470  
 1471  		err = enable_restore_fp_context(0);
 1472  
 1473  		if (raw_cpu_has_fpu && !err)
 1474  			break;
 1475  
 1476  		sig = fpu_emulator_cop1Handler(regs, &current->thread.fpu, 0,
 1477  					       &fault_addr);
 1478  
 1479  		/*
 1480  		 * We can't allow the emulated instruction to leave
 1481  		 * any enabled Cause bits set in $fcr31.
 1482  		 */
...（其余23行省略）
```

【fpu_emulator_cop1Handler的代码（arch/mips/math-emu/cp1emu.c）】
```c
 2839  int fpu_emulator_cop1Handler(struct pt_regs *xcp, struct mips_fpu_struct *ctx, 	int has_fpu, void __user **fault_addr)  {
 2840  	unsigned long oldepc, prevepc;
 2841  	struct mm_decoded_insn dec_insn;
 2842  	u16 instr[4];
 2843  	u16 *instr_ptr;
 2844  	int sig = 0;
 2845  
 2846  	/*
 2847  	 * Initialize context if it hasn't been used already, otherwise ensure
 2848  	 * it has been saved to struct thread_struct.
 2849  	 */
 2850  	if (!init_fp_ctx(current))
 2851  		lose_fpu(1);
 2852  
 2853  	oldepc = xcp->cp0_epc;
 2854  	do {
 2855  		prevepc = xcp->cp0_epc;
 2856  
 2857  		if (get_isa16_mode(prevepc) && cpu_has_mmips) {
 2858  			/*
 2859  			 * Get next 2 microMIPS instructions and convert them
 2860  			 * into 32-bit instructions.
 2861  			 */
 2862  			if ((get_user(instr[0], (u16 __user *)msk_isa16_mode(xcp->cp0_epc))) ||
 2863  			    (get_user(instr[1], (u16 __user *)msk_isa16_mode(xcp->cp0_epc + 2))) ||
 2864  			    (get_user(instr[2], (u16 __user *)msk_isa16_mode(xcp->cp0_epc + 4))) ||
 2865  			    (get_user(instr[3], (u16 __user *)msk_isa16_mode(xcp->cp0_epc + 6)))) {
 2866  				MIPS_FPU_EMU_INC_STATS(errors);
 2867  				return SIGBUS;
 2868  			}
 2869  			instr_ptr = instr;
 2870  
 2871  			/* Get first instruction. */
 2872  			if (mm_insn_16bit(*instr_ptr)) {
 2873  				/* Duplicate the half-word. */
 2874  				dec_insn.insn = (*instr_ptr << 16) |
 2875  					(*instr_ptr);
 2876  				/* 16-bit instruction. */
 2877  				dec_insn.pc_inc = 2;
 2878  				instr_ptr += 1;
 2879  			} else {
 2880  				dec_insn.insn = (*instr_ptr << 16) |
 2881  					*(instr_ptr+1);
 2882  				/* 32-bit instruction. */
 2883  				dec_insn.pc_inc = 4;
 2884  				instr_ptr += 2;
 2885  			}
 2886  			/* Get second instruction. */
 2887  			if (mm_insn_16bit(*instr_ptr)) {
 2888  				/* Duplicate the half-word. */
 2889  				dec_insn.next_insn = (*instr_ptr << 16) |
 2890  					(*instr_ptr);
 2891  				/* 16-bit instruction. */
 2892  				dec_insn.next_pc_inc = 2;
 2893  			} else {
 2894  				dec_insn.next_insn = (*instr_ptr << 16) |
 2895  					*(instr_ptr+1);
 2896  				/* 32-bit instruction. */
 2897  				dec_insn.next_pc_inc = 4;
 2898  			}
 2899  			dec_insn.micro_mips_mode = 1;
 2900  		} else {
 2901  			if ((get_user(dec_insn.insn,
 2902  			    (mips_instruction __user *) xcp->cp0_epc)) ||
 2903  			    (get_user(dec_insn.next_insn,
 2904  			    (mips_instruction __user *)(xcp->cp0_epc+4)))) {
 2905  				MIPS_FPU_EMU_INC_STATS(errors);
 2906  				return SIGBUS;
 2907  			}
 2908  			dec_insn.pc_inc = 4;
 2909  			dec_insn.next_pc_inc = 4;
 2910  			dec_insn.micro_mips_mode = 0;
 2911  		}
 2912  
 2913  		if ((dec_insn.insn == 0) ||
 2914  		   ((dec_insn.pc_inc == 2) &&
 2915  		   ((dec_insn.insn & 0xffff) == MM_NOP16)))
 2916  			xcp->cp0_epc += dec_insn.pc_inc;	/* Skip NOPs */
 2917  		else {
 2918  			/*
...（其余30行省略）
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M13

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/traps.c中的do_cpu

【程序给出的理由】sleep B:trap: line 1419 exception_epc -> __get_user

【调用链】exception_epc（arch/mips/include/asm/branch.h第66行调用__isa_exception_epc） → __isa_exception_epc（arch/mips/kernel/branch.c第35行调用__get_user）

【do_cpu的代码】
```c
 1403  asmlinkage void do_cpu(struct pt_regs *regs)  {
 1404  	enum ctx_state prev_state;
 1405  	unsigned int __user *epc;
 1406  	unsigned long old_epc, old31;
 1407  	unsigned int opcode;
 1408  	unsigned int cpid;
 1409  	int status;
 1410  
 1411  	prev_state = exception_enter();
 1412  	cpid = (regs->cp0_cause >> CAUSEB_CE) & 3;
 1413  
 1414  	if (cpid != 2)
 1415  		die_if_kernel("do_cpu invoked from kernel context!", regs);
 1416  
 1417  	switch (cpid) {
 1418  	case 0:
 1419  		epc = (unsigned int __user *)exception_epc(regs);
 1420  		old_epc = regs->cp0_epc;
 1421  		old31 = regs->regs[31];
 1422  		opcode = 0;
 1423  		status = -1;
 1424  
 1425  		if (unlikely(compute_return_epc(regs) < 0))
 1426  			break;
 1427  
 1428  		if (!get_isa16_mode(regs->cp0_epc)) {
 1429  			if (unlikely(get_user(opcode, epc) < 0))
 1430  				status = SIGSEGV;
 1431  
 1432  			if (!cpu_has_llsc && status < 0)
 1433  				status = simulate_llsc(regs, opcode);
 1434  		}
 1435  
 1436  		if (status < 0)
 1437  			status = SIGILL;
 1438  
 1439  		if (unlikely(status > 0)) {
 1440  			regs->cp0_epc = old_epc;	/* Undo skip-over.  */
 1441  			regs->regs[31] = old31;
 1442  			force_sig(status);
 1443  		}
 1444  
 1445  		break;
 1446  
 1447  #ifdef CONFIG_MIPS_FP_SUPPORT
 1448  	case 3:
 1449  		/*
 1450  		 * The COP3 opcode space and consequently the CP0.Status.CU3
 1451  		 * bit and the CP0.Cause.CE=3 encoding have been removed as
 1452  		 * of the MIPS III ISA.  From the MIPS IV and MIPS32r2 ISAs
 1453  		 * up the space has been reused for COP1X instructions, that
 1454  		 * are enabled by the CP0.Status.CU1 bit and consequently
 1455  		 * use the CP0.Cause.CE=1 encoding for Coprocessor Unusable
 1456  		 * exceptions.  Some FPU-less processors that implement one
 1457  		 * of these ISAs however use this code erroneously for COP1X
 1458  		 * instructions.  Therefore we redirect this trap to the FP
 1459  		 * emulator too.
 1460  		 */
 1461  		if (raw_cpu_has_fpu || !cpu_has_mips_4_5_64_r2_r6) {
 1462  			force_sig(SIGILL);
 1463  			break;
 1464  		}
 1465  		fallthrough;
 1466  	case 1: {
 1467  		void __user *fault_addr;
 1468  		unsigned long fcr31;
 1469  		int err, sig;
 1470  
 1471  		err = enable_restore_fp_context(0);
 1472  
 1473  		if (raw_cpu_has_fpu && !err)
 1474  			break;
 1475  
 1476  		sig = fpu_emulator_cop1Handler(regs, &current->thread.fpu, 0,
 1477  					       &fault_addr);
 1478  
 1479  		/*
 1480  		 * We can't allow the emulated instruction to leave
 1481  		 * any enabled Cause bits set in $fcr31.
 1482  		 */
...（其余23行省略）
```

【exception_epc的代码（arch/mips/include/asm/branch.h）】
```c
   61  static inline unsigned long exception_epc(struct pt_regs *regs)  {
   62  	if (likely(!delay_slot(regs)))
   63  		return regs->cp0_epc;
   64  
   65  	if (get_isa16_mode(regs->cp0_epc))
   66  		return __isa_exception_epc(regs);
   67  
   68  	return regs->cp0_epc + 4;
   69  }
```

【__isa_exception_epc的代码（arch/mips/kernel/branch.c）】
```c
   30  int __isa_exception_epc(struct pt_regs *regs)  {
   31  	unsigned short inst;
   32  	long epc = regs->cp0_epc;
   33  
   34  	/* Calculate exception PC in branch delay slot. */
   35  	if (__get_user(inst, (u16 __user *) msk_isa16_mode(epc))) {
   36  		/* This should never happen because delay slot was checked. */
   37  		force_sig(SIGSEGV);
   38  		return epc;
   39  	}
   40  	if (cpu_has_mips16) {
   41  		union mips16e_instruction inst_mips16e;
   42  
   43  		inst_mips16e.full = inst;
   44  		if (inst_mips16e.ri.opcode == MIPS16e_jal_op)
   45  			epc += 4;
   46  		else
   47  			epc += 2;
   48  	} else if (mm_insn_16bit(inst))
   49  		epc += 2;
   50  	else
   51  		epc += 4;
   52  
   53  	return epc;
   54  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M14

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/traps.c中的do_cpu

【程序给出的理由】rt B:trap: line 1442 force_sig -> spin_lock_irqsave

【调用链】force_sig（kernel/signal.c第1660行调用force_sig_info） → force_sig_info（kernel/signal.c第1357行调用force_sig_info_to_task） → force_sig_info_to_task（kernel/signal.c第1329行调用spin_lock_irqsave）

【do_cpu的代码】
```c
 1403  asmlinkage void do_cpu(struct pt_regs *regs)  {
 1404  	enum ctx_state prev_state;
 1405  	unsigned int __user *epc;
 1406  	unsigned long old_epc, old31;
 1407  	unsigned int opcode;
 1408  	unsigned int cpid;
 1409  	int status;
 1410  
 1411  	prev_state = exception_enter();
 1412  	cpid = (regs->cp0_cause >> CAUSEB_CE) & 3;
 1413  
 1414  	if (cpid != 2)
 1415  		die_if_kernel("do_cpu invoked from kernel context!", regs);
 1416  
 1417  	switch (cpid) {
 1418  	case 0:
 1419  		epc = (unsigned int __user *)exception_epc(regs);
 1420  		old_epc = regs->cp0_epc;
 1421  		old31 = regs->regs[31];
 1422  		opcode = 0;
 1423  		status = -1;
 1424  
 1425  		if (unlikely(compute_return_epc(regs) < 0))
 1426  			break;
 1427  
 1428  		if (!get_isa16_mode(regs->cp0_epc)) {
 1429  			if (unlikely(get_user(opcode, epc) < 0))
 1430  				status = SIGSEGV;
 1431  
 1432  			if (!cpu_has_llsc && status < 0)
 1433  				status = simulate_llsc(regs, opcode);
 1434  		}
 1435  
 1436  		if (status < 0)
 1437  			status = SIGILL;
 1438  
 1439  		if (unlikely(status > 0)) {
 1440  			regs->cp0_epc = old_epc;	/* Undo skip-over.  */
 1441  			regs->regs[31] = old31;
 1442  			force_sig(status);
 1443  		}
 1444  
 1445  		break;
 1446  
 1447  #ifdef CONFIG_MIPS_FP_SUPPORT
 1448  	case 3:
 1449  		/*
 1450  		 * The COP3 opcode space and consequently the CP0.Status.CU3
 1451  		 * bit and the CP0.Cause.CE=3 encoding have been removed as
 1452  		 * of the MIPS III ISA.  From the MIPS IV and MIPS32r2 ISAs
 1453  		 * up the space has been reused for COP1X instructions, that
 1454  		 * are enabled by the CP0.Status.CU1 bit and consequently
 1455  		 * use the CP0.Cause.CE=1 encoding for Coprocessor Unusable
 1456  		 * exceptions.  Some FPU-less processors that implement one
 1457  		 * of these ISAs however use this code erroneously for COP1X
 1458  		 * instructions.  Therefore we redirect this trap to the FP
 1459  		 * emulator too.
 1460  		 */
 1461  		if (raw_cpu_has_fpu || !cpu_has_mips_4_5_64_r2_r6) {
 1462  			force_sig(SIGILL);
 1463  			break;
 1464  		}
 1465  		fallthrough;
 1466  	case 1: {
 1467  		void __user *fault_addr;
 1468  		unsigned long fcr31;
 1469  		int err, sig;
 1470  
 1471  		err = enable_restore_fp_context(0);
 1472  
 1473  		if (raw_cpu_has_fpu && !err)
 1474  			break;
 1475  
 1476  		sig = fpu_emulator_cop1Handler(regs, &current->thread.fpu, 0,
 1477  					       &fault_addr);
 1478  
 1479  		/*
 1480  		 * We can't allow the emulated instruction to leave
 1481  		 * any enabled Cause bits set in $fcr31.
 1482  		 */
...（其余23行省略）
```

【force_sig的代码（kernel/signal.c）】
```c
 1651  void force_sig(int sig)  {
 1652  	struct kernel_siginfo info;
 1653  
 1654  	clear_siginfo(&info);
 1655  	info.si_signo = sig;
 1656  	info.si_errno = 0;
 1657  	info.si_code = SI_KERNEL;
 1658  	info.si_pid = 0;
 1659  	info.si_uid = 0;
 1660  	force_sig_info(&info);
 1661  }
```

【force_sig_info的代码（kernel/signal.c）】
```c
 1356  int force_sig_info(struct kernel_siginfo *info)  {
 1357  	return force_sig_info_to_task(info, current, HANDLER_CURRENT);
 1358  }
```

【force_sig_info_to_task的代码（kernel/signal.c）】
```c
 1323  static int force_sig_info_to_task(struct kernel_siginfo *info, struct task_struct *t, 	enum sig_handler handler)  {
 1324  	unsigned long int flags;
 1325  	int ret, blocked, ignored;
 1326  	struct k_sigaction *action;
 1327  	int sig = info->si_signo;
 1328  
 1329  	spin_lock_irqsave(&t->sighand->siglock, flags);
 1330  	action = &t->sighand->action[sig-1];
 1331  	ignored = action->sa.sa_handler == SIG_IGN;
 1332  	blocked = sigismember(&t->blocked, sig);
 1333  	if (blocked || ignored || (handler != HANDLER_CURRENT)) {
 1334  		action->sa.sa_handler = SIG_DFL;
 1335  		if (handler == HANDLER_EXIT)
 1336  			action->sa.sa_flags |= SA_IMMUTABLE;
 1337  		if (blocked) {
 1338  			sigdelset(&t->blocked, sig);
 1339  			recalc_sigpending_and_wake(t);
 1340  		}
 1341  	}
 1342  	/*
 1343  	 * Don't clear SIGNAL_UNKILLABLE for traced tasks, users won't expect
 1344  	 * debugging to leave init killable. But HANDLER_EXIT is always fatal.
 1345  	 */
 1346  	if (action->sa.sa_handler == SIG_DFL &&
 1347  	    (!t->ptrace || (handler == HANDLER_EXIT)))
 1348  		t->signal->flags &= ~SIGNAL_UNKILLABLE;
 1349  	ret = send_signal_locked(sig, info, t, PIDTYPE_PID);
 1350  	spin_unlock_irqrestore(&t->sighand->siglock, flags);
 1351  
 1352  	return ret;
 1353  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M15

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/traps.c中的do_cpu

【程序给出的理由】sleep B:trap: line 1487 process_fpemu_return -> down_read

【调用链】process_fpemu_return（arch/mips/kernel/traps.c第807行调用mmap_read_lock） → mmap_read_lock（include/linux/mmap_lock.h第117行调用down_read）

【do_cpu的代码】
```c
 1403  asmlinkage void do_cpu(struct pt_regs *regs)  {
 1404  	enum ctx_state prev_state;
 1405  	unsigned int __user *epc;
 1406  	unsigned long old_epc, old31;
 1407  	unsigned int opcode;
 1408  	unsigned int cpid;
 1409  	int status;
 1410  
 1411  	prev_state = exception_enter();
 1412  	cpid = (regs->cp0_cause >> CAUSEB_CE) & 3;
 1413  
 1414  	if (cpid != 2)
 1415  		die_if_kernel("do_cpu invoked from kernel context!", regs);
 1416  
 1417  	switch (cpid) {
 1418  	case 0:
 1419  		epc = (unsigned int __user *)exception_epc(regs);
 1420  		old_epc = regs->cp0_epc;
 1421  		old31 = regs->regs[31];
 1422  		opcode = 0;
 1423  		status = -1;
 1424  
 1425  		if (unlikely(compute_return_epc(regs) < 0))
 1426  			break;
 1427  
 1428  		if (!get_isa16_mode(regs->cp0_epc)) {
 1429  			if (unlikely(get_user(opcode, epc) < 0))
 1430  				status = SIGSEGV;
 1431  
 1432  			if (!cpu_has_llsc && status < 0)
 1433  				status = simulate_llsc(regs, opcode);
 1434  		}
 1435  
 1436  		if (status < 0)
 1437  			status = SIGILL;
 1438  
 1439  		if (unlikely(status > 0)) {
 1440  			regs->cp0_epc = old_epc;	/* Undo skip-over.  */
 1441  			regs->regs[31] = old31;
 1442  			force_sig(status);
 1443  		}
 1444  
 1445  		break;
 1446  
 1447  #ifdef CONFIG_MIPS_FP_SUPPORT
 1448  	case 3:
 1449  		/*
 1450  		 * The COP3 opcode space and consequently the CP0.Status.CU3
 1451  		 * bit and the CP0.Cause.CE=3 encoding have been removed as
 1452  		 * of the MIPS III ISA.  From the MIPS IV and MIPS32r2 ISAs
 1453  		 * up the space has been reused for COP1X instructions, that
 1454  		 * are enabled by the CP0.Status.CU1 bit and consequently
 1455  		 * use the CP0.Cause.CE=1 encoding for Coprocessor Unusable
 1456  		 * exceptions.  Some FPU-less processors that implement one
 1457  		 * of these ISAs however use this code erroneously for COP1X
 1458  		 * instructions.  Therefore we redirect this trap to the FP
 1459  		 * emulator too.
 1460  		 */
 1461  		if (raw_cpu_has_fpu || !cpu_has_mips_4_5_64_r2_r6) {
 1462  			force_sig(SIGILL);
 1463  			break;
 1464  		}
 1465  		fallthrough;
 1466  	case 1: {
 1467  		void __user *fault_addr;
 1468  		unsigned long fcr31;
 1469  		int err, sig;
 1470  
 1471  		err = enable_restore_fp_context(0);
 1472  
 1473  		if (raw_cpu_has_fpu && !err)
 1474  			break;
 1475  
 1476  		sig = fpu_emulator_cop1Handler(regs, &current->thread.fpu, 0,
 1477  					       &fault_addr);
 1478  
 1479  		/*
 1480  		 * We can't allow the emulated instruction to leave
 1481  		 * any enabled Cause bits set in $fcr31.
 1482  		 */
...（其余23行省略）
```

【process_fpemu_return的代码（arch/mips/kernel/traps.c）】
```c
  791  int process_fpemu_return(int sig, void __user *fault_addr, unsigned long fcr31)  {
  792  	int si_code;
  793  
  794  	switch (sig) {
  795  	case 0:
  796  		return 0;
  797  
  798  	case SIGFPE:
  799  		force_fcr31_sig(fcr31, fault_addr, current);
  800  		return 1;
  801  
  802  	case SIGBUS:
  803  		force_sig_fault(SIGBUS, BUS_ADRERR, fault_addr);
  804  		return 1;
  805  
  806  	case SIGSEGV:
  807  		mmap_read_lock(current->mm);
  808  		if (vma_lookup(current->mm, (unsigned long)fault_addr))
  809  			si_code = SEGV_ACCERR;
  810  		else
  811  			si_code = SEGV_MAPERR;
  812  		mmap_read_unlock(current->mm);
  813  		force_sig_fault(SIGSEGV, si_code, fault_addr);
  814  		return 1;
  815  
  816  	default:
  817  		force_sig(sig);
  818  		return 1;
  819  	}
  820  }
```

【mmap_read_lock的代码（include/linux/mmap_lock.h）】
```c
  115  static inline void mmap_read_lock(struct mm_struct *mm)  {
  116  	__mmap_lock_trace_start_locking(mm, false);
  117  	down_read(&mm->mmap_lock);
  118  	__mmap_lock_trace_acquire_returned(mm, false, true);
  119  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M16

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/traps.c中的do_dsp

【程序给出的理由】rt B:trap: line 1653 force_sig -> spin_lock_irqsave

【调用链】force_sig（kernel/signal.c第1660行调用force_sig_info） → force_sig_info（kernel/signal.c第1357行调用force_sig_info_to_task） → force_sig_info_to_task（kernel/signal.c第1329行调用spin_lock_irqsave）

【do_dsp的代码】
```c
 1649  asmlinkage void do_dsp(struct pt_regs *regs)  {
 1650  	if (cpu_has_dsp)
 1651  		panic("Unexpected DSP exception");
 1652  
 1653  	force_sig(SIGILL);
 1654  }
```

【force_sig的代码（kernel/signal.c）】
```c
 1651  void force_sig(int sig)  {
 1652  	struct kernel_siginfo info;
 1653  
 1654  	clear_siginfo(&info);
 1655  	info.si_signo = sig;
 1656  	info.si_errno = 0;
 1657  	info.si_code = SI_KERNEL;
 1658  	info.si_pid = 0;
 1659  	info.si_uid = 0;
 1660  	force_sig_info(&info);
 1661  }
```

【force_sig_info的代码（kernel/signal.c）】
```c
 1356  int force_sig_info(struct kernel_siginfo *info)  {
 1357  	return force_sig_info_to_task(info, current, HANDLER_CURRENT);
 1358  }
```

【force_sig_info_to_task的代码（kernel/signal.c）】
```c
 1323  static int force_sig_info_to_task(struct kernel_siginfo *info, struct task_struct *t, 	enum sig_handler handler)  {
 1324  	unsigned long int flags;
 1325  	int ret, blocked, ignored;
 1326  	struct k_sigaction *action;
 1327  	int sig = info->si_signo;
 1328  
 1329  	spin_lock_irqsave(&t->sighand->siglock, flags);
 1330  	action = &t->sighand->action[sig-1];
 1331  	ignored = action->sa.sa_handler == SIG_IGN;
 1332  	blocked = sigismember(&t->blocked, sig);
 1333  	if (blocked || ignored || (handler != HANDLER_CURRENT)) {
 1334  		action->sa.sa_handler = SIG_DFL;
 1335  		if (handler == HANDLER_EXIT)
 1336  			action->sa.sa_flags |= SA_IMMUTABLE;
 1337  		if (blocked) {
 1338  			sigdelset(&t->blocked, sig);
 1339  			recalc_sigpending_and_wake(t);
 1340  		}
 1341  	}
 1342  	/*
 1343  	 * Don't clear SIGNAL_UNKILLABLE for traced tasks, users won't expect
 1344  	 * debugging to leave init killable. But HANDLER_EXIT is always fatal.
 1345  	 */
 1346  	if (action->sa.sa_handler == SIG_DFL &&
 1347  	    (!t->ptrace || (handler == HANDLER_EXIT)))
 1348  		t->signal->flags &= ~SIGNAL_UNKILLABLE;
 1349  	ret = send_signal_locked(sig, info, t, PIDTYPE_PID);
 1350  	spin_unlock_irqrestore(&t->sighand->siglock, flags);
 1351  
 1352  	return ret;
 1353  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M17

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/traps.c中的do_gsexc

【程序给出的理由】rt B:trap: line 1925 force_sig -> spin_lock_irqsave

【调用链】force_sig（kernel/signal.c第1660行调用force_sig_info） → force_sig_info（kernel/signal.c第1357行调用force_sig_info_to_task） → force_sig_info_to_task（kernel/signal.c第1329行调用spin_lock_irqsave）

【do_gsexc的代码】
```c
 1910  asmlinkage void do_gsexc(struct pt_regs *regs, u32 diag1)  {
 1911  	u32 exccode = (diag1 & LOONGSON_DIAG1_EXCCODE) >>
 1912  			LOONGSON_DIAG1_EXCCODE_SHIFT;
 1913  	enum ctx_state prev_state;
 1914  
 1915  	prev_state = exception_enter();
 1916  
 1917  	switch (exccode) {
 1918  	case 0x08:
 1919  		/* Undocumented exception, will trigger on certain
 1920  		 * also-undocumented instructions accessible from userspace.
 1921  		 * Processor state is not otherwise corrupted, but currently
 1922  		 * we don't know how to proceed. Maybe there is some
 1923  		 * undocumented control flag to enable the instructions?
 1924  		 */
 1925  		force_sig(SIGILL);
 1926  		break;
 1927  
 1928  	default:
 1929  		/* None of the other exceptions, documented or not, have
 1930  		 * further details given; none are encountered in the wild
 1931  		 * either. Panic in case some of them turn out to be fatal.
 1932  		 */
 1933  		show_regs(regs);
 1934  		panic("Unhandled Loongson exception - GSCause = %08x", diag1);
 1935  	}
 1936  
 1937  	exception_exit(prev_state);
 1938  }
```

【force_sig的代码（kernel/signal.c）】
```c
 1651  void force_sig(int sig)  {
 1652  	struct kernel_siginfo info;
 1653  
 1654  	clear_siginfo(&info);
 1655  	info.si_signo = sig;
 1656  	info.si_errno = 0;
 1657  	info.si_code = SI_KERNEL;
 1658  	info.si_pid = 0;
 1659  	info.si_uid = 0;
 1660  	force_sig_info(&info);
 1661  }
```

【force_sig_info的代码（kernel/signal.c）】
```c
 1356  int force_sig_info(struct kernel_siginfo *info)  {
 1357  	return force_sig_info_to_task(info, current, HANDLER_CURRENT);
 1358  }
```

【force_sig_info_to_task的代码（kernel/signal.c）】
```c
 1323  static int force_sig_info_to_task(struct kernel_siginfo *info, struct task_struct *t, 	enum sig_handler handler)  {
 1324  	unsigned long int flags;
 1325  	int ret, blocked, ignored;
 1326  	struct k_sigaction *action;
 1327  	int sig = info->si_signo;
 1328  
 1329  	spin_lock_irqsave(&t->sighand->siglock, flags);
 1330  	action = &t->sighand->action[sig-1];
 1331  	ignored = action->sa.sa_handler == SIG_IGN;
 1332  	blocked = sigismember(&t->blocked, sig);
 1333  	if (blocked || ignored || (handler != HANDLER_CURRENT)) {
 1334  		action->sa.sa_handler = SIG_DFL;
 1335  		if (handler == HANDLER_EXIT)
 1336  			action->sa.sa_flags |= SA_IMMUTABLE;
 1337  		if (blocked) {
 1338  			sigdelset(&t->blocked, sig);
 1339  			recalc_sigpending_and_wake(t);
 1340  		}
 1341  	}
 1342  	/*
 1343  	 * Don't clear SIGNAL_UNKILLABLE for traced tasks, users won't expect
 1344  	 * debugging to leave init killable. But HANDLER_EXIT is always fatal.
 1345  	 */
 1346  	if (action->sa.sa_handler == SIG_DFL &&
 1347  	    (!t->ptrace || (handler == HANDLER_EXIT)))
 1348  		t->signal->flags &= ~SIGNAL_UNKILLABLE;
 1349  	ret = send_signal_locked(sig, info, t, PIDTYPE_PID);
 1350  	spin_unlock_irqrestore(&t->sighand->siglock, flags);
 1351  
 1352  	return ret;
 1353  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M18

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/traps.c中的do_mcheck

【程序给出的理由】sleep B:trap: line 1601 show_code -> get_user

【调用链】show_code（arch/mips/kernel/traps.c第243行调用__get_inst16） → __get_inst16（arch/mips/kernel/access-helper.h第13行调用get_user）

【do_mcheck的代码】
```c
 1588  asmlinkage void do_mcheck(struct pt_regs *regs)  {
 1589  	int multi_match = regs->cp0_status & ST0_TS;
 1590  	enum ctx_state prev_state;
 1591  
 1592  	prev_state = exception_enter();
 1593  	show_regs(regs);
 1594  
 1595  	if (multi_match) {
 1596  		dump_tlb_regs();
 1597  		pr_info("\n");
 1598  		dump_tlb_all();
 1599  	}
 1600  
 1601  	show_code((void *)regs->cp0_epc, user_mode(regs));
 1602  
 1603  	/*
 1604  	 * Some chips may have other causes of machine check (e.g. SB1
 1605  	 * graduation timer)
 1606  	 */
 1607  	panic("Caught Machine Check exception - %scaused by multiple "
 1608  	      "matching entries in the TLB.",
 1609  	      (multi_match) ? "" : "not ");
 1610  }
```

【show_code的代码（arch/mips/kernel/traps.c）】
```c
  230  static void show_code(void *pc, bool user)  {
  231  	long i;
  232  	unsigned short *pc16 = NULL;
  233  
  234  	printk("Code:");
  235  
  236  	if ((unsigned long)pc & 1)
  237  		pc16 = (u16 *)((unsigned long)pc & ~1);
  238  
  239  	for(i = -3 ; i < 6 ; i++) {
  240  		if (pc16) {
  241  			u16 insn16;
  242  
  243  			if (__get_inst16(&insn16, pc16 + i, user))
  244  				goto bad_address;
  245  
  246  			pr_cont("%c%04x%c", (i?' ':'<'), insn16, (i?' ':'>'));
  247  		} else {
  248  			u32 insn32;
  249  
  250  			if (__get_inst32(&insn32, (u32 *)pc + i, user))
  251  				goto bad_address;
  252  
  253  			pr_cont("%c%08x%c", (i?' ':'<'), insn32, (i?' ':'>'));
  254  		}
  255  	}
  256  	pr_cont("\n");
  257  	return;
  258  
  259  bad_address:
  260  	pr_cont(" (Bad address in epc)\n\n");
  261  }
```

【__get_inst16的代码（arch/mips/kernel/access-helper.h）】
```c
   12  static inline int __get_inst16(u16 *i, u16 *p, bool user)  {
   13  	return user ? get_user(*i, (u16 __user *)p) : get_kernel_nofault(*i, p);
   14  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M19

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/traps.c中的do_mdmx

【程序给出的理由】rt B:trap: line 1553 force_sig -> spin_lock_irqsave

【调用链】force_sig（kernel/signal.c第1660行调用force_sig_info） → force_sig_info（kernel/signal.c第1357行调用force_sig_info_to_task） → force_sig_info_to_task（kernel/signal.c第1329行调用spin_lock_irqsave）

【do_mdmx的代码】
```c
 1549  asmlinkage void do_mdmx(struct pt_regs *regs)  {
 1550  	enum ctx_state prev_state;
 1551  
 1552  	prev_state = exception_enter();
 1553  	force_sig(SIGILL);
 1554  	exception_exit(prev_state);
 1555  }
```

【force_sig的代码（kernel/signal.c）】
```c
 1651  void force_sig(int sig)  {
 1652  	struct kernel_siginfo info;
 1653  
 1654  	clear_siginfo(&info);
 1655  	info.si_signo = sig;
 1656  	info.si_errno = 0;
 1657  	info.si_code = SI_KERNEL;
 1658  	info.si_pid = 0;
 1659  	info.si_uid = 0;
 1660  	force_sig_info(&info);
 1661  }
```

【force_sig_info的代码（kernel/signal.c）】
```c
 1356  int force_sig_info(struct kernel_siginfo *info)  {
 1357  	return force_sig_info_to_task(info, current, HANDLER_CURRENT);
 1358  }
```

【force_sig_info_to_task的代码（kernel/signal.c）】
```c
 1323  static int force_sig_info_to_task(struct kernel_siginfo *info, struct task_struct *t, 	enum sig_handler handler)  {
 1324  	unsigned long int flags;
 1325  	int ret, blocked, ignored;
 1326  	struct k_sigaction *action;
 1327  	int sig = info->si_signo;
 1328  
 1329  	spin_lock_irqsave(&t->sighand->siglock, flags);
 1330  	action = &t->sighand->action[sig-1];
 1331  	ignored = action->sa.sa_handler == SIG_IGN;
 1332  	blocked = sigismember(&t->blocked, sig);
 1333  	if (blocked || ignored || (handler != HANDLER_CURRENT)) {
 1334  		action->sa.sa_handler = SIG_DFL;
 1335  		if (handler == HANDLER_EXIT)
 1336  			action->sa.sa_flags |= SA_IMMUTABLE;
 1337  		if (blocked) {
 1338  			sigdelset(&t->blocked, sig);
 1339  			recalc_sigpending_and_wake(t);
 1340  		}
 1341  	}
 1342  	/*
 1343  	 * Don't clear SIGNAL_UNKILLABLE for traced tasks, users won't expect
 1344  	 * debugging to leave init killable. But HANDLER_EXIT is always fatal.
 1345  	 */
 1346  	if (action->sa.sa_handler == SIG_DFL &&
 1347  	    (!t->ptrace || (handler == HANDLER_EXIT)))
 1348  		t->signal->flags &= ~SIGNAL_UNKILLABLE;
 1349  	ret = send_signal_locked(sig, info, t, PIDTYPE_PID);
 1350  	spin_unlock_irqrestore(&t->sighand->siglock, flags);
 1351  
 1352  	return ret;
 1353  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M20

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/traps.c中的do_msa

【程序给出的理由】rt B:trap: line 1535 force_sig -> spin_lock_irqsave

【调用链】force_sig（kernel/signal.c第1660行调用force_sig_info） → force_sig_info（kernel/signal.c第1357行调用force_sig_info_to_task） → force_sig_info_to_task（kernel/signal.c第1329行调用spin_lock_irqsave）

【do_msa的代码】
```c
 1528  asmlinkage void do_msa(struct pt_regs *regs)  {
 1529  	enum ctx_state prev_state;
 1530  	int err;
 1531  
 1532  	prev_state = exception_enter();
 1533  
 1534  	if (!cpu_has_msa || test_thread_flag(TIF_32BIT_FPREGS)) {
 1535  		force_sig(SIGILL);
 1536  		goto out;
 1537  	}
 1538  
 1539  	die_if_kernel("do_msa invoked from kernel context!", regs);
 1540  
 1541  	err = enable_restore_fp_context(1);
 1542  	if (err)
 1543  		force_sig(SIGILL);
 1544  out:
 1545  	exception_exit(prev_state);
 1546  }
```

【force_sig的代码（kernel/signal.c）】
```c
 1651  void force_sig(int sig)  {
 1652  	struct kernel_siginfo info;
 1653  
 1654  	clear_siginfo(&info);
 1655  	info.si_signo = sig;
 1656  	info.si_errno = 0;
 1657  	info.si_code = SI_KERNEL;
 1658  	info.si_pid = 0;
 1659  	info.si_uid = 0;
 1660  	force_sig_info(&info);
 1661  }
```

【force_sig_info的代码（kernel/signal.c）】
```c
 1356  int force_sig_info(struct kernel_siginfo *info)  {
 1357  	return force_sig_info_to_task(info, current, HANDLER_CURRENT);
 1358  }
```

【force_sig_info_to_task的代码（kernel/signal.c）】
```c
 1323  static int force_sig_info_to_task(struct kernel_siginfo *info, struct task_struct *t, 	enum sig_handler handler)  {
 1324  	unsigned long int flags;
 1325  	int ret, blocked, ignored;
 1326  	struct k_sigaction *action;
 1327  	int sig = info->si_signo;
 1328  
 1329  	spin_lock_irqsave(&t->sighand->siglock, flags);
 1330  	action = &t->sighand->action[sig-1];
 1331  	ignored = action->sa.sa_handler == SIG_IGN;
 1332  	blocked = sigismember(&t->blocked, sig);
 1333  	if (blocked || ignored || (handler != HANDLER_CURRENT)) {
 1334  		action->sa.sa_handler = SIG_DFL;
 1335  		if (handler == HANDLER_EXIT)
 1336  			action->sa.sa_flags |= SA_IMMUTABLE;
 1337  		if (blocked) {
 1338  			sigdelset(&t->blocked, sig);
 1339  			recalc_sigpending_and_wake(t);
 1340  		}
 1341  	}
 1342  	/*
 1343  	 * Don't clear SIGNAL_UNKILLABLE for traced tasks, users won't expect
 1344  	 * debugging to leave init killable. But HANDLER_EXIT is always fatal.
 1345  	 */
 1346  	if (action->sa.sa_handler == SIG_DFL &&
 1347  	    (!t->ptrace || (handler == HANDLER_EXIT)))
 1348  		t->signal->flags &= ~SIGNAL_UNKILLABLE;
 1349  	ret = send_signal_locked(sig, info, t, PIDTYPE_PID);
 1350  	spin_unlock_irqrestore(&t->sighand->siglock, flags);
 1351  
 1352  	return ret;
 1353  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M21

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/traps.c中的do_ri

【程序给出的理由】sleep B:trap: line 1177 process_fpemu_return -> down_read

【调用链】process_fpemu_return（arch/mips/kernel/traps.c第807行调用mmap_read_lock） → mmap_read_lock（include/linux/mmap_lock.h第117行调用down_read）

【do_ri的代码】
```c
 1152  asmlinkage void do_ri(struct pt_regs *regs)  {
 1153  	unsigned int __user *epc = (unsigned int __user *)exception_epc(regs);
 1154  	unsigned long old_epc = regs->cp0_epc;
 1155  	unsigned long old31 = regs->regs[31];
 1156  	enum ctx_state prev_state;
 1157  	unsigned int opcode = 0;
 1158  	int status = -1;
 1159  
 1160  	/*
 1161  	 * Avoid any kernel code. Just emulate the R2 instruction
 1162  	 * as quickly as possible.
 1163  	 */
 1164  	if (mipsr2_emulation && cpu_has_mips_r6 &&
 1165  	    likely(user_mode(regs)) &&
 1166  	    likely(get_user(opcode, epc) >= 0)) {
 1167  		unsigned long fcr31 = 0;
 1168  
 1169  		status = mipsr2_decoder(regs, opcode, &fcr31);
 1170  		switch (status) {
 1171  		case 0:
 1172  		case SIGEMT:
 1173  			return;
 1174  		case SIGILL:
 1175  			goto no_r2_instr;
 1176  		default:
 1177  			process_fpemu_return(status,
 1178  					     &current->thread.cp0_baduaddr,
 1179  					     fcr31);
 1180  			return;
 1181  		}
 1182  	}
 1183  
 1184  no_r2_instr:
 1185  
 1186  	prev_state = exception_enter();
 1187  	current->thread.trap_nr = (regs->cp0_cause >> 2) & 0x1f;
 1188  
 1189  	if (notify_die(DIE_RI, "RI Fault", regs, 0, current->thread.trap_nr,
 1190  		       SIGILL) == NOTIFY_STOP)
 1191  		goto out;
 1192  
 1193  	die_if_kernel("Reserved instruction in kernel code", regs);
 1194  
 1195  	if (unlikely(compute_return_epc(regs) < 0))
 1196  		goto out;
 1197  
 1198  	if (!get_isa16_mode(regs->cp0_epc)) {
 1199  		if (unlikely(get_user(opcode, epc) < 0))
 1200  			status = SIGSEGV;
 1201  
 1202  		if (!cpu_has_llsc && status < 0)
 1203  			status = simulate_llsc(regs, opcode);
 1204  
 1205  		if (status < 0)
 1206  			status = simulate_rdhwr_normal(regs, opcode);
 1207  
 1208  		if (status < 0)
 1209  			status = simulate_sync(regs, opcode);
 1210  
 1211  		if (status < 0)
 1212  			status = simulate_fp(regs, opcode, old_epc, old31);
 1213  
 1214  #ifdef CONFIG_CPU_LOONGSON3_CPUCFG_EMULATION
 1215  		if (status < 0)
 1216  			status = simulate_loongson3_cpucfg(regs, opcode);
 1217  #endif
 1218  	} else if (cpu_has_mmips) {
 1219  		unsigned short mmop[2] = { 0 };
 1220  
 1221  		if (unlikely(get_user(mmop[0], (u16 __user *)epc + 0) < 0))
 1222  			status = SIGSEGV;
 1223  		if (unlikely(get_user(mmop[1], (u16 __user *)epc + 1) < 0))
 1224  			status = SIGSEGV;
 1225  		opcode = mmop[0];
 1226  		opcode = (opcode << 16) | mmop[1];
 1227  
 1228  		if (status < 0)
 1229  			status = simulate_rdhwr_mm(regs, opcode);
 1230  	}
 1231  
...（其余12行省略）
```

【process_fpemu_return的代码（arch/mips/kernel/traps.c）】
```c
  791  int process_fpemu_return(int sig, void __user *fault_addr, unsigned long fcr31)  {
  792  	int si_code;
  793  
  794  	switch (sig) {
  795  	case 0:
  796  		return 0;
  797  
  798  	case SIGFPE:
  799  		force_fcr31_sig(fcr31, fault_addr, current);
  800  		return 1;
  801  
  802  	case SIGBUS:
  803  		force_sig_fault(SIGBUS, BUS_ADRERR, fault_addr);
  804  		return 1;
  805  
  806  	case SIGSEGV:
  807  		mmap_read_lock(current->mm);
  808  		if (vma_lookup(current->mm, (unsigned long)fault_addr))
  809  			si_code = SEGV_ACCERR;
  810  		else
  811  			si_code = SEGV_MAPERR;
  812  		mmap_read_unlock(current->mm);
  813  		force_sig_fault(SIGSEGV, si_code, fault_addr);
  814  		return 1;
  815  
  816  	default:
  817  		force_sig(sig);
  818  		return 1;
  819  	}
  820  }
```

【mmap_read_lock的代码（include/linux/mmap_lock.h）】
```c
  115  static inline void mmap_read_lock(struct mm_struct *mm)  {
  116  	__mmap_lock_trace_start_locking(mm, false);
  117  	down_read(&mm->mmap_lock);
  118  	__mmap_lock_trace_acquire_returned(mm, false, true);
  119  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M22

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/traps.c中的do_ri

【程序给出的理由】sleep B:trap: line 1203 simulate_llsc -> get_user

【调用链】simulate_llsc（arch/mips/kernel/traps.c第620行调用simulate_ll） → simulate_ll（arch/mips/kernel/traps.c第548行调用get_user）

【do_ri的代码】
```c
 1152  asmlinkage void do_ri(struct pt_regs *regs)  {
 1153  	unsigned int __user *epc = (unsigned int __user *)exception_epc(regs);
 1154  	unsigned long old_epc = regs->cp0_epc;
 1155  	unsigned long old31 = regs->regs[31];
 1156  	enum ctx_state prev_state;
 1157  	unsigned int opcode = 0;
 1158  	int status = -1;
 1159  
 1160  	/*
 1161  	 * Avoid any kernel code. Just emulate the R2 instruction
 1162  	 * as quickly as possible.
 1163  	 */
 1164  	if (mipsr2_emulation && cpu_has_mips_r6 &&
 1165  	    likely(user_mode(regs)) &&
 1166  	    likely(get_user(opcode, epc) >= 0)) {
 1167  		unsigned long fcr31 = 0;
 1168  
 1169  		status = mipsr2_decoder(regs, opcode, &fcr31);
 1170  		switch (status) {
 1171  		case 0:
 1172  		case SIGEMT:
 1173  			return;
 1174  		case SIGILL:
 1175  			goto no_r2_instr;
 1176  		default:
 1177  			process_fpemu_return(status,
 1178  					     &current->thread.cp0_baduaddr,
 1179  					     fcr31);
 1180  			return;
 1181  		}
 1182  	}
 1183  
 1184  no_r2_instr:
 1185  
 1186  	prev_state = exception_enter();
 1187  	current->thread.trap_nr = (regs->cp0_cause >> 2) & 0x1f;
 1188  
 1189  	if (notify_die(DIE_RI, "RI Fault", regs, 0, current->thread.trap_nr,
 1190  		       SIGILL) == NOTIFY_STOP)
 1191  		goto out;
 1192  
 1193  	die_if_kernel("Reserved instruction in kernel code", regs);
 1194  
 1195  	if (unlikely(compute_return_epc(regs) < 0))
 1196  		goto out;
 1197  
 1198  	if (!get_isa16_mode(regs->cp0_epc)) {
 1199  		if (unlikely(get_user(opcode, epc) < 0))
 1200  			status = SIGSEGV;
 1201  
 1202  		if (!cpu_has_llsc && status < 0)
 1203  			status = simulate_llsc(regs, opcode);
 1204  
 1205  		if (status < 0)
 1206  			status = simulate_rdhwr_normal(regs, opcode);
 1207  
 1208  		if (status < 0)
 1209  			status = simulate_sync(regs, opcode);
 1210  
 1211  		if (status < 0)
 1212  			status = simulate_fp(regs, opcode, old_epc, old31);
 1213  
 1214  #ifdef CONFIG_CPU_LOONGSON3_CPUCFG_EMULATION
 1215  		if (status < 0)
 1216  			status = simulate_loongson3_cpucfg(regs, opcode);
 1217  #endif
 1218  	} else if (cpu_has_mmips) {
 1219  		unsigned short mmop[2] = { 0 };
 1220  
 1221  		if (unlikely(get_user(mmop[0], (u16 __user *)epc + 0) < 0))
 1222  			status = SIGSEGV;
 1223  		if (unlikely(get_user(mmop[1], (u16 __user *)epc + 1) < 0))
 1224  			status = SIGSEGV;
 1225  		opcode = mmop[0];
 1226  		opcode = (opcode << 16) | mmop[1];
 1227  
 1228  		if (status < 0)
 1229  			status = simulate_rdhwr_mm(regs, opcode);
 1230  	}
 1231  
...（其余12行省略）
```

【simulate_llsc的代码（arch/mips/kernel/traps.c）】
```c
  616  static int simulate_llsc(struct pt_regs *regs, unsigned int opcode)  {
  617  	if ((opcode & OPCODE) == LL) {
  618  		perf_sw_event(PERF_COUNT_SW_EMULATION_FAULTS,
  619  				1, regs, 0);
  620  		return simulate_ll(regs, opcode);
  621  	}
  622  	if ((opcode & OPCODE) == SC) {
  623  		perf_sw_event(PERF_COUNT_SW_EMULATION_FAULTS,
  624  				1, regs, 0);
  625  		return simulate_sc(regs, opcode);
  626  	}
  627  
  628  	return -1;			/* Must be something else ... */
  629  }
```

【simulate_ll的代码（arch/mips/kernel/traps.c）】
```c
  529  static inline int simulate_ll(struct pt_regs *regs, unsigned int opcode)  {
  530  	unsigned long value, __user *vaddr;
  531  	long offset;
  532  
  533  	/*
  534  	 * analyse the ll instruction that just caused a ri exception
  535  	 * and put the referenced address to addr.
  536  	 */
  537  
  538  	/* sign extend offset */
  539  	offset = opcode & OFFSET;
  540  	offset <<= 16;
  541  	offset >>= 16;
  542  
  543  	vaddr = (unsigned long __user *)
  544  		((unsigned long)(regs->regs[(opcode & BASE) >> 21]) + offset);
  545  
  546  	if ((unsigned long)vaddr & 3)
  547  		return SIGBUS;
  548  	if (get_user(value, vaddr))
  549  		return SIGSEGV;
  550  
  551  	preempt_disable();
  552  
  553  	if (ll_task == NULL || ll_task == current) {
  554  		ll_bit = 1;
  555  	} else {
  556  		ll_bit = 0;
  557  	}
  558  	ll_task = current;
  559  
  560  	preempt_enable();
  561  
  562  	regs->regs[(opcode & RT) >> 16] = value;
  563  
  564  	return 0;
  565  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M23

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/traps.c中的do_ri

【程序给出的理由】rt B:trap: line 1238 force_sig -> spin_lock_irqsave

【调用链】force_sig（kernel/signal.c第1660行调用force_sig_info） → force_sig_info（kernel/signal.c第1357行调用force_sig_info_to_task） → force_sig_info_to_task（kernel/signal.c第1329行调用spin_lock_irqsave）

【do_ri的代码】
```c
 1152  asmlinkage void do_ri(struct pt_regs *regs)  {
 1153  	unsigned int __user *epc = (unsigned int __user *)exception_epc(regs);
 1154  	unsigned long old_epc = regs->cp0_epc;
 1155  	unsigned long old31 = regs->regs[31];
 1156  	enum ctx_state prev_state;
 1157  	unsigned int opcode = 0;
 1158  	int status = -1;
 1159  
 1160  	/*
 1161  	 * Avoid any kernel code. Just emulate the R2 instruction
 1162  	 * as quickly as possible.
 1163  	 */
 1164  	if (mipsr2_emulation && cpu_has_mips_r6 &&
 1165  	    likely(user_mode(regs)) &&
 1166  	    likely(get_user(opcode, epc) >= 0)) {
 1167  		unsigned long fcr31 = 0;
 1168  
 1169  		status = mipsr2_decoder(regs, opcode, &fcr31);
 1170  		switch (status) {
 1171  		case 0:
 1172  		case SIGEMT:
 1173  			return;
 1174  		case SIGILL:
 1175  			goto no_r2_instr;
 1176  		default:
 1177  			process_fpemu_return(status,
 1178  					     &current->thread.cp0_baduaddr,
 1179  					     fcr31);
 1180  			return;
 1181  		}
 1182  	}
 1183  
 1184  no_r2_instr:
 1185  
 1186  	prev_state = exception_enter();
 1187  	current->thread.trap_nr = (regs->cp0_cause >> 2) & 0x1f;
 1188  
 1189  	if (notify_die(DIE_RI, "RI Fault", regs, 0, current->thread.trap_nr,
 1190  		       SIGILL) == NOTIFY_STOP)
 1191  		goto out;
 1192  
 1193  	die_if_kernel("Reserved instruction in kernel code", regs);
 1194  
 1195  	if (unlikely(compute_return_epc(regs) < 0))
 1196  		goto out;
 1197  
 1198  	if (!get_isa16_mode(regs->cp0_epc)) {
 1199  		if (unlikely(get_user(opcode, epc) < 0))
 1200  			status = SIGSEGV;
 1201  
 1202  		if (!cpu_has_llsc && status < 0)
 1203  			status = simulate_llsc(regs, opcode);
 1204  
 1205  		if (status < 0)
 1206  			status = simulate_rdhwr_normal(regs, opcode);
 1207  
 1208  		if (status < 0)
 1209  			status = simulate_sync(regs, opcode);
 1210  
 1211  		if (status < 0)
 1212  			status = simulate_fp(regs, opcode, old_epc, old31);
 1213  
 1214  #ifdef CONFIG_CPU_LOONGSON3_CPUCFG_EMULATION
 1215  		if (status < 0)
 1216  			status = simulate_loongson3_cpucfg(regs, opcode);
 1217  #endif
 1218  	} else if (cpu_has_mmips) {
 1219  		unsigned short mmop[2] = { 0 };
 1220  
 1221  		if (unlikely(get_user(mmop[0], (u16 __user *)epc + 0) < 0))
 1222  			status = SIGSEGV;
 1223  		if (unlikely(get_user(mmop[1], (u16 __user *)epc + 1) < 0))
 1224  			status = SIGSEGV;
 1225  		opcode = mmop[0];
 1226  		opcode = (opcode << 16) | mmop[1];
 1227  
 1228  		if (status < 0)
 1229  			status = simulate_rdhwr_mm(regs, opcode);
 1230  	}
 1231  
...（其余12行省略）
```

【force_sig的代码（kernel/signal.c）】
```c
 1651  void force_sig(int sig)  {
 1652  	struct kernel_siginfo info;
 1653  
 1654  	clear_siginfo(&info);
 1655  	info.si_signo = sig;
 1656  	info.si_errno = 0;
 1657  	info.si_code = SI_KERNEL;
 1658  	info.si_pid = 0;
 1659  	info.si_uid = 0;
 1660  	force_sig_info(&info);
 1661  }
```

【force_sig_info的代码（kernel/signal.c）】
```c
 1356  int force_sig_info(struct kernel_siginfo *info)  {
 1357  	return force_sig_info_to_task(info, current, HANDLER_CURRENT);
 1358  }
```

【force_sig_info_to_task的代码（kernel/signal.c）】
```c
 1323  static int force_sig_info_to_task(struct kernel_siginfo *info, struct task_struct *t, 	enum sig_handler handler)  {
 1324  	unsigned long int flags;
 1325  	int ret, blocked, ignored;
 1326  	struct k_sigaction *action;
 1327  	int sig = info->si_signo;
 1328  
 1329  	spin_lock_irqsave(&t->sighand->siglock, flags);
 1330  	action = &t->sighand->action[sig-1];
 1331  	ignored = action->sa.sa_handler == SIG_IGN;
 1332  	blocked = sigismember(&t->blocked, sig);
 1333  	if (blocked || ignored || (handler != HANDLER_CURRENT)) {
 1334  		action->sa.sa_handler = SIG_DFL;
 1335  		if (handler == HANDLER_EXIT)
 1336  			action->sa.sa_flags |= SA_IMMUTABLE;
 1337  		if (blocked) {
 1338  			sigdelset(&t->blocked, sig);
 1339  			recalc_sigpending_and_wake(t);
 1340  		}
 1341  	}
 1342  	/*
 1343  	 * Don't clear SIGNAL_UNKILLABLE for traced tasks, users won't expect
 1344  	 * debugging to leave init killable. But HANDLER_EXIT is always fatal.
 1345  	 */
 1346  	if (action->sa.sa_handler == SIG_DFL &&
 1347  	    (!t->ptrace || (handler == HANDLER_EXIT)))
 1348  		t->signal->flags &= ~SIGNAL_UNKILLABLE;
 1349  	ret = send_signal_locked(sig, info, t, PIDTYPE_PID);
 1350  	spin_unlock_irqrestore(&t->sighand->siglock, flags);
 1351  
 1352  	return ret;
 1353  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M24

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/traps.c中的do_ri

【程序给出的理由】sleep B:trap: line 1212 simulate_fp -> get_user

【调用链】simulate_fp（arch/mips/kernel/traps.c第852行调用fpu_emulator_cop1Handler） → fpu_emulator_cop1Handler（arch/mips/math-emu/cp1emu.c第2862行调用get_user）

【do_ri的代码】
```c
 1152  asmlinkage void do_ri(struct pt_regs *regs)  {
 1153  	unsigned int __user *epc = (unsigned int __user *)exception_epc(regs);
 1154  	unsigned long old_epc = regs->cp0_epc;
 1155  	unsigned long old31 = regs->regs[31];
 1156  	enum ctx_state prev_state;
 1157  	unsigned int opcode = 0;
 1158  	int status = -1;
 1159  
 1160  	/*
 1161  	 * Avoid any kernel code. Just emulate the R2 instruction
 1162  	 * as quickly as possible.
 1163  	 */
 1164  	if (mipsr2_emulation && cpu_has_mips_r6 &&
 1165  	    likely(user_mode(regs)) &&
 1166  	    likely(get_user(opcode, epc) >= 0)) {
 1167  		unsigned long fcr31 = 0;
 1168  
 1169  		status = mipsr2_decoder(regs, opcode, &fcr31);
 1170  		switch (status) {
 1171  		case 0:
 1172  		case SIGEMT:
 1173  			return;
 1174  		case SIGILL:
 1175  			goto no_r2_instr;
 1176  		default:
 1177  			process_fpemu_return(status,
 1178  					     &current->thread.cp0_baduaddr,
 1179  					     fcr31);
 1180  			return;
 1181  		}
 1182  	}
 1183  
 1184  no_r2_instr:
 1185  
 1186  	prev_state = exception_enter();
 1187  	current->thread.trap_nr = (regs->cp0_cause >> 2) & 0x1f;
 1188  
 1189  	if (notify_die(DIE_RI, "RI Fault", regs, 0, current->thread.trap_nr,
 1190  		       SIGILL) == NOTIFY_STOP)
 1191  		goto out;
 1192  
 1193  	die_if_kernel("Reserved instruction in kernel code", regs);
 1194  
 1195  	if (unlikely(compute_return_epc(regs) < 0))
 1196  		goto out;
 1197  
 1198  	if (!get_isa16_mode(regs->cp0_epc)) {
 1199  		if (unlikely(get_user(opcode, epc) < 0))
 1200  			status = SIGSEGV;
 1201  
 1202  		if (!cpu_has_llsc && status < 0)
 1203  			status = simulate_llsc(regs, opcode);
 1204  
 1205  		if (status < 0)
 1206  			status = simulate_rdhwr_normal(regs, opcode);
 1207  
 1208  		if (status < 0)
 1209  			status = simulate_sync(regs, opcode);
 1210  
 1211  		if (status < 0)
 1212  			status = simulate_fp(regs, opcode, old_epc, old31);
 1213  
 1214  #ifdef CONFIG_CPU_LOONGSON3_CPUCFG_EMULATION
 1215  		if (status < 0)
 1216  			status = simulate_loongson3_cpucfg(regs, opcode);
 1217  #endif
 1218  	} else if (cpu_has_mmips) {
 1219  		unsigned short mmop[2] = { 0 };
 1220  
 1221  		if (unlikely(get_user(mmop[0], (u16 __user *)epc + 0) < 0))
 1222  			status = SIGSEGV;
 1223  		if (unlikely(get_user(mmop[1], (u16 __user *)epc + 1) < 0))
 1224  			status = SIGSEGV;
 1225  		opcode = mmop[0];
 1226  		opcode = (opcode << 16) | mmop[1];
 1227  
 1228  		if (status < 0)
 1229  			status = simulate_rdhwr_mm(regs, opcode);
 1230  	}
 1231  
...（其余12行省略）
```

【simulate_fp的代码（arch/mips/kernel/traps.c）】
```c
  824  static int simulate_fp(struct pt_regs *regs, unsigned int opcode, 		       unsigned long old_epc, unsigned long old_ra)  {
  825  	union mips_instruction inst = { .word = opcode };
  826  	void __user *fault_addr;
  827  	unsigned long fcr31;
  828  	int sig;
  829  
  830  	/* If it's obviously not an FP instruction, skip it */
  831  	switch (inst.i_format.opcode) {
  832  	case cop1_op:
  833  	case cop1x_op:
  834  	case lwc1_op:
  835  	case ldc1_op:
  836  	case swc1_op:
  837  	case sdc1_op:
  838  		break;
  839  
  840  	default:
  841  		return -1;
  842  	}
  843  
  844  	/*
  845  	 * do_ri skipped over the instruction via compute_return_epc, undo
  846  	 * that for the FPU emulator.
  847  	 */
  848  	regs->cp0_epc = old_epc;
  849  	regs->regs[31] = old_ra;
  850  
  851  	/* Run the emulator */
  852  	sig = fpu_emulator_cop1Handler(regs, &current->thread.fpu, 1,
  853  				       &fault_addr);
  854  
  855  	/*
  856  	 * We can't allow the emulated instruction to leave any
  857  	 * enabled Cause bits set in $fcr31.
  858  	 */
  859  	fcr31 = mask_fcr31_x(current->thread.fpu.fcr31);
  860  	current->thread.fpu.fcr31 &= ~fcr31;
  861  
  862  	/* Restore the hardware register state */
  863  	own_fpu(1);
  864  
  865  	/* Send a signal if required.  */
  866  	process_fpemu_return(sig, fault_addr, fcr31);
  867  
  868  	return 0;
  869  }
```

【fpu_emulator_cop1Handler的代码（arch/mips/math-emu/cp1emu.c）】
```c
 2839  int fpu_emulator_cop1Handler(struct pt_regs *xcp, struct mips_fpu_struct *ctx, 	int has_fpu, void __user **fault_addr)  {
 2840  	unsigned long oldepc, prevepc;
 2841  	struct mm_decoded_insn dec_insn;
 2842  	u16 instr[4];
 2843  	u16 *instr_ptr;
 2844  	int sig = 0;
 2845  
 2846  	/*
 2847  	 * Initialize context if it hasn't been used already, otherwise ensure
 2848  	 * it has been saved to struct thread_struct.
 2849  	 */
 2850  	if (!init_fp_ctx(current))
 2851  		lose_fpu(1);
 2852  
 2853  	oldepc = xcp->cp0_epc;
 2854  	do {
 2855  		prevepc = xcp->cp0_epc;
 2856  
 2857  		if (get_isa16_mode(prevepc) && cpu_has_mmips) {
 2858  			/*
 2859  			 * Get next 2 microMIPS instructions and convert them
 2860  			 * into 32-bit instructions.
 2861  			 */
 2862  			if ((get_user(instr[0], (u16 __user *)msk_isa16_mode(xcp->cp0_epc))) ||
 2863  			    (get_user(instr[1], (u16 __user *)msk_isa16_mode(xcp->cp0_epc + 2))) ||
 2864  			    (get_user(instr[2], (u16 __user *)msk_isa16_mode(xcp->cp0_epc + 4))) ||
 2865  			    (get_user(instr[3], (u16 __user *)msk_isa16_mode(xcp->cp0_epc + 6)))) {
 2866  				MIPS_FPU_EMU_INC_STATS(errors);
 2867  				return SIGBUS;
 2868  			}
 2869  			instr_ptr = instr;
 2870  
 2871  			/* Get first instruction. */
 2872  			if (mm_insn_16bit(*instr_ptr)) {
 2873  				/* Duplicate the half-word. */
 2874  				dec_insn.insn = (*instr_ptr << 16) |
 2875  					(*instr_ptr);
 2876  				/* 16-bit instruction. */
 2877  				dec_insn.pc_inc = 2;
 2878  				instr_ptr += 1;
 2879  			} else {
 2880  				dec_insn.insn = (*instr_ptr << 16) |
 2881  					*(instr_ptr+1);
 2882  				/* 32-bit instruction. */
 2883  				dec_insn.pc_inc = 4;
 2884  				instr_ptr += 2;
 2885  			}
 2886  			/* Get second instruction. */
 2887  			if (mm_insn_16bit(*instr_ptr)) {
 2888  				/* Duplicate the half-word. */
 2889  				dec_insn.next_insn = (*instr_ptr << 16) |
 2890  					(*instr_ptr);
 2891  				/* 16-bit instruction. */
 2892  				dec_insn.next_pc_inc = 2;
 2893  			} else {
 2894  				dec_insn.next_insn = (*instr_ptr << 16) |
 2895  					*(instr_ptr+1);
 2896  				/* 32-bit instruction. */
 2897  				dec_insn.next_pc_inc = 4;
 2898  			}
 2899  			dec_insn.micro_mips_mode = 1;
 2900  		} else {
 2901  			if ((get_user(dec_insn.insn,
 2902  			    (mips_instruction __user *) xcp->cp0_epc)) ||
 2903  			    (get_user(dec_insn.next_insn,
 2904  			    (mips_instruction __user *)(xcp->cp0_epc+4)))) {
 2905  				MIPS_FPU_EMU_INC_STATS(errors);
 2906  				return SIGBUS;
 2907  			}
 2908  			dec_insn.pc_inc = 4;
 2909  			dec_insn.next_pc_inc = 4;
 2910  			dec_insn.micro_mips_mode = 0;
 2911  		}
 2912  
 2913  		if ((dec_insn.insn == 0) ||
 2914  		   ((dec_insn.pc_inc == 2) &&
 2915  		   ((dec_insn.insn & 0xffff) == MM_NOP16)))
 2916  			xcp->cp0_epc += dec_insn.pc_inc;	/* Skip NOPs */
 2917  		else {
 2918  			/*
...（其余30行省略）
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M25

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/traps.c中的do_ri

【程序给出的理由】sleep B:trap: line 1153 exception_epc -> __get_user

【调用链】exception_epc（arch/mips/include/asm/branch.h第66行调用__isa_exception_epc） → __isa_exception_epc（arch/mips/kernel/branch.c第35行调用__get_user）

【do_ri的代码】
```c
 1152  asmlinkage void do_ri(struct pt_regs *regs)  {
 1153  	unsigned int __user *epc = (unsigned int __user *)exception_epc(regs);
 1154  	unsigned long old_epc = regs->cp0_epc;
 1155  	unsigned long old31 = regs->regs[31];
 1156  	enum ctx_state prev_state;
 1157  	unsigned int opcode = 0;
 1158  	int status = -1;
 1159  
 1160  	/*
 1161  	 * Avoid any kernel code. Just emulate the R2 instruction
 1162  	 * as quickly as possible.
 1163  	 */
 1164  	if (mipsr2_emulation && cpu_has_mips_r6 &&
 1165  	    likely(user_mode(regs)) &&
 1166  	    likely(get_user(opcode, epc) >= 0)) {
 1167  		unsigned long fcr31 = 0;
 1168  
 1169  		status = mipsr2_decoder(regs, opcode, &fcr31);
 1170  		switch (status) {
 1171  		case 0:
 1172  		case SIGEMT:
 1173  			return;
 1174  		case SIGILL:
 1175  			goto no_r2_instr;
 1176  		default:
 1177  			process_fpemu_return(status,
 1178  					     &current->thread.cp0_baduaddr,
 1179  					     fcr31);
 1180  			return;
 1181  		}
 1182  	}
 1183  
 1184  no_r2_instr:
 1185  
 1186  	prev_state = exception_enter();
 1187  	current->thread.trap_nr = (regs->cp0_cause >> 2) & 0x1f;
 1188  
 1189  	if (notify_die(DIE_RI, "RI Fault", regs, 0, current->thread.trap_nr,
 1190  		       SIGILL) == NOTIFY_STOP)
 1191  		goto out;
 1192  
 1193  	die_if_kernel("Reserved instruction in kernel code", regs);
 1194  
 1195  	if (unlikely(compute_return_epc(regs) < 0))
 1196  		goto out;
 1197  
 1198  	if (!get_isa16_mode(regs->cp0_epc)) {
 1199  		if (unlikely(get_user(opcode, epc) < 0))
 1200  			status = SIGSEGV;
 1201  
 1202  		if (!cpu_has_llsc && status < 0)
 1203  			status = simulate_llsc(regs, opcode);
 1204  
 1205  		if (status < 0)
 1206  			status = simulate_rdhwr_normal(regs, opcode);
 1207  
 1208  		if (status < 0)
 1209  			status = simulate_sync(regs, opcode);
 1210  
 1211  		if (status < 0)
 1212  			status = simulate_fp(regs, opcode, old_epc, old31);
 1213  
 1214  #ifdef CONFIG_CPU_LOONGSON3_CPUCFG_EMULATION
 1215  		if (status < 0)
 1216  			status = simulate_loongson3_cpucfg(regs, opcode);
 1217  #endif
 1218  	} else if (cpu_has_mmips) {
 1219  		unsigned short mmop[2] = { 0 };
 1220  
 1221  		if (unlikely(get_user(mmop[0], (u16 __user *)epc + 0) < 0))
 1222  			status = SIGSEGV;
 1223  		if (unlikely(get_user(mmop[1], (u16 __user *)epc + 1) < 0))
 1224  			status = SIGSEGV;
 1225  		opcode = mmop[0];
 1226  		opcode = (opcode << 16) | mmop[1];
 1227  
 1228  		if (status < 0)
 1229  			status = simulate_rdhwr_mm(regs, opcode);
 1230  	}
 1231  
...（其余12行省略）
```

【exception_epc的代码（arch/mips/include/asm/branch.h）】
```c
   61  static inline unsigned long exception_epc(struct pt_regs *regs)  {
   62  	if (likely(!delay_slot(regs)))
   63  		return regs->cp0_epc;
   64  
   65  	if (get_isa16_mode(regs->cp0_epc))
   66  		return __isa_exception_epc(regs);
   67  
   68  	return regs->cp0_epc + 4;
   69  }
```

【__isa_exception_epc的代码（arch/mips/kernel/branch.c）】
```c
   30  int __isa_exception_epc(struct pt_regs *regs)  {
   31  	unsigned short inst;
   32  	long epc = regs->cp0_epc;
   33  
   34  	/* Calculate exception PC in branch delay slot. */
   35  	if (__get_user(inst, (u16 __user *) msk_isa16_mode(epc))) {
   36  		/* This should never happen because delay slot was checked. */
   37  		force_sig(SIGSEGV);
   38  		return epc;
   39  	}
   40  	if (cpu_has_mips16) {
   41  		union mips16e_instruction inst_mips16e;
   42  
   43  		inst_mips16e.full = inst;
   44  		if (inst_mips16e.ri.opcode == MIPS16e_jal_op)
   45  			epc += 4;
   46  		else
   47  			epc += 2;
   48  	} else if (mm_insn_16bit(inst))
   49  		epc += 2;
   50  	else
   51  		epc += 4;
   52  
   53  	return epc;
   54  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M26

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/traps.c中的do_ri

【程序给出的理由】sleep B:trap: line 1195 compute_return_epc -> __get_user

【调用链】compute_return_epc（arch/mips/include/asm/branch.h第77行调用__microMIPS_compute_return_epc） → __microMIPS_compute_return_epc（arch/mips/kernel/branch.c第274行调用__get_user）

【do_ri的代码】
```c
 1152  asmlinkage void do_ri(struct pt_regs *regs)  {
 1153  	unsigned int __user *epc = (unsigned int __user *)exception_epc(regs);
 1154  	unsigned long old_epc = regs->cp0_epc;
 1155  	unsigned long old31 = regs->regs[31];
 1156  	enum ctx_state prev_state;
 1157  	unsigned int opcode = 0;
 1158  	int status = -1;
 1159  
 1160  	/*
 1161  	 * Avoid any kernel code. Just emulate the R2 instruction
 1162  	 * as quickly as possible.
 1163  	 */
 1164  	if (mipsr2_emulation && cpu_has_mips_r6 &&
 1165  	    likely(user_mode(regs)) &&
 1166  	    likely(get_user(opcode, epc) >= 0)) {
 1167  		unsigned long fcr31 = 0;
 1168  
 1169  		status = mipsr2_decoder(regs, opcode, &fcr31);
 1170  		switch (status) {
 1171  		case 0:
 1172  		case SIGEMT:
 1173  			return;
 1174  		case SIGILL:
 1175  			goto no_r2_instr;
 1176  		default:
 1177  			process_fpemu_return(status,
 1178  					     &current->thread.cp0_baduaddr,
 1179  					     fcr31);
 1180  			return;
 1181  		}
 1182  	}
 1183  
 1184  no_r2_instr:
 1185  
 1186  	prev_state = exception_enter();
 1187  	current->thread.trap_nr = (regs->cp0_cause >> 2) & 0x1f;
 1188  
 1189  	if (notify_die(DIE_RI, "RI Fault", regs, 0, current->thread.trap_nr,
 1190  		       SIGILL) == NOTIFY_STOP)
 1191  		goto out;
 1192  
 1193  	die_if_kernel("Reserved instruction in kernel code", regs);
 1194  
 1195  	if (unlikely(compute_return_epc(regs) < 0))
 1196  		goto out;
 1197  
 1198  	if (!get_isa16_mode(regs->cp0_epc)) {
 1199  		if (unlikely(get_user(opcode, epc) < 0))
 1200  			status = SIGSEGV;
 1201  
 1202  		if (!cpu_has_llsc && status < 0)
 1203  			status = simulate_llsc(regs, opcode);
 1204  
 1205  		if (status < 0)
 1206  			status = simulate_rdhwr_normal(regs, opcode);
 1207  
 1208  		if (status < 0)
 1209  			status = simulate_sync(regs, opcode);
 1210  
 1211  		if (status < 0)
 1212  			status = simulate_fp(regs, opcode, old_epc, old31);
 1213  
 1214  #ifdef CONFIG_CPU_LOONGSON3_CPUCFG_EMULATION
 1215  		if (status < 0)
 1216  			status = simulate_loongson3_cpucfg(regs, opcode);
 1217  #endif
 1218  	} else if (cpu_has_mmips) {
 1219  		unsigned short mmop[2] = { 0 };
 1220  
 1221  		if (unlikely(get_user(mmop[0], (u16 __user *)epc + 0) < 0))
 1222  			status = SIGSEGV;
 1223  		if (unlikely(get_user(mmop[1], (u16 __user *)epc + 1) < 0))
 1224  			status = SIGSEGV;
 1225  		opcode = mmop[0];
 1226  		opcode = (opcode << 16) | mmop[1];
 1227  
 1228  		if (status < 0)
 1229  			status = simulate_rdhwr_mm(regs, opcode);
 1230  	}
 1231  
...（其余12行省略）
```

【compute_return_epc的代码（arch/mips/include/asm/branch.h）】
```c
   74  static inline int compute_return_epc(struct pt_regs *regs)  {
   75  	if (get_isa16_mode(regs->cp0_epc)) {
   76  		if (cpu_has_mmips)
   77  			return __microMIPS_compute_return_epc(regs);
   78  		if (cpu_has_mips16)
   79  			return __MIPS16e_compute_return_epc(regs);
   80  	} else if (!delay_slot(regs)) {
   81  		regs->cp0_epc += 4;
   82  		return 0;
   83  	}
   84  
   85  	return __compute_return_epc(regs);
   86  }
```

【__microMIPS_compute_return_epc的代码（arch/mips/kernel/branch.c）】
```c
  263  int __microMIPS_compute_return_epc(struct pt_regs *regs)  {
  264  	u16 __user *pc16;
  265  	u16 halfword;
  266  	unsigned int word;
  267  	unsigned long contpc;
  268  	struct mm_decoded_insn mminsn = { 0 };
  269  
  270  	mminsn.micro_mips_mode = 1;
  271  
  272  	/* This load never faults. */
  273  	pc16 = (unsigned short __user *)msk_isa16_mode(regs->cp0_epc);
  274  	__get_user(halfword, pc16);
  275  	pc16++;
  276  	contpc = regs->cp0_epc + 2;
  277  	word = ((unsigned int)halfword << 16);
  278  	mminsn.pc_inc = 2;
  279  
  280  	if (!mm_insn_16bit(halfword)) {
  281  		__get_user(halfword, pc16);
  282  		pc16++;
  283  		contpc = regs->cp0_epc + 4;
  284  		mminsn.pc_inc = 4;
  285  		word |= halfword;
  286  	}
  287  	mminsn.insn = word;
  288  
  289  	if (get_user(halfword, pc16))
  290  		goto sigsegv;
  291  	mminsn.next_pc_inc = 2;
  292  	word = ((unsigned int)halfword << 16);
  293  
  294  	if (!mm_insn_16bit(halfword)) {
  295  		pc16++;
  296  		if (get_user(halfword, pc16))
  297  			goto sigsegv;
  298  		mminsn.next_pc_inc = 4;
  299  		word |= halfword;
  300  	}
  301  	mminsn.next_insn = word;
  302  
  303  	mm_isBranchInstr(regs, mminsn, &contpc);
  304  
  305  	regs->cp0_epc = contpc;
  306  
  307  	return 0;
  308  
  309  sigsegv:
  310  	force_sig(SIGSEGV);
  311  	return -EFAULT;
  312  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M27

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/traps.c中的do_tr

【程序给出的理由】sleep B:trap: line 1125 __get_inst16 -> get_user

【调用链】__get_inst16（arch/mips/kernel/access-helper.h第13行调用get_user）

【do_tr的代码】
```c
 1115  asmlinkage void do_tr(struct pt_regs *regs)  {
 1116  	u32 opcode, tcode = 0;
 1117  	enum ctx_state prev_state;
 1118  	u16 instr[2];
 1119  	bool user = user_mode(regs);
 1120  	unsigned long epc = msk_isa16_mode(exception_epc(regs));
 1121  
 1122  	prev_state = exception_enter();
 1123  	current->thread.trap_nr = (regs->cp0_cause >> 2) & 0x1f;
 1124  	if (get_isa16_mode(regs->cp0_epc)) {
 1125  		if (__get_inst16(&instr[0], (u16 *)(epc + 0), user) ||
 1126  		    __get_inst16(&instr[1], (u16 *)(epc + 2), user))
 1127  			goto out_sigsegv;
 1128  		opcode = (instr[0] << 16) | instr[1];
 1129  		/* Immediate versions don't provide a code.  */
 1130  		if (!(opcode & OPCODE))
 1131  			tcode = (opcode >> 12) & ((1 << 4) - 1);
 1132  	} else {
 1133  		if (__get_inst32(&opcode, (u32 *)epc, user))
 1134  			goto out_sigsegv;
 1135  		/* Immediate versions don't provide a code.  */
 1136  		if (!(opcode & OPCODE))
 1137  			tcode = (opcode >> 6) & ((1 << 10) - 1);
 1138  	}
 1139  
 1140  	do_trap_or_bp(regs, tcode, 0, "Trap");
 1141  
 1142  out:
 1143  	exception_exit(prev_state);
 1144  	return;
 1145  
 1146  out_sigsegv:
 1147  	force_sig(SIGSEGV);
 1148  	goto out;
 1149  }
```

【__get_inst16的代码（arch/mips/kernel/access-helper.h）】
```c
   12  static inline int __get_inst16(u16 *i, u16 *p, bool user)  {
   13  	return user ? get_user(*i, (u16 __user *)p) : get_kernel_nofault(*i, p);
   14  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M28

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/traps.c中的do_tr

【程序给出的理由】rt B:trap: line 1147 force_sig -> spin_lock_irqsave

【调用链】force_sig（kernel/signal.c第1660行调用force_sig_info） → force_sig_info（kernel/signal.c第1357行调用force_sig_info_to_task） → force_sig_info_to_task（kernel/signal.c第1329行调用spin_lock_irqsave）

【do_tr的代码】
```c
 1115  asmlinkage void do_tr(struct pt_regs *regs)  {
 1116  	u32 opcode, tcode = 0;
 1117  	enum ctx_state prev_state;
 1118  	u16 instr[2];
 1119  	bool user = user_mode(regs);
 1120  	unsigned long epc = msk_isa16_mode(exception_epc(regs));
 1121  
 1122  	prev_state = exception_enter();
 1123  	current->thread.trap_nr = (regs->cp0_cause >> 2) & 0x1f;
 1124  	if (get_isa16_mode(regs->cp0_epc)) {
 1125  		if (__get_inst16(&instr[0], (u16 *)(epc + 0), user) ||
 1126  		    __get_inst16(&instr[1], (u16 *)(epc + 2), user))
 1127  			goto out_sigsegv;
 1128  		opcode = (instr[0] << 16) | instr[1];
 1129  		/* Immediate versions don't provide a code.  */
 1130  		if (!(opcode & OPCODE))
 1131  			tcode = (opcode >> 12) & ((1 << 4) - 1);
 1132  	} else {
 1133  		if (__get_inst32(&opcode, (u32 *)epc, user))
 1134  			goto out_sigsegv;
 1135  		/* Immediate versions don't provide a code.  */
 1136  		if (!(opcode & OPCODE))
 1137  			tcode = (opcode >> 6) & ((1 << 10) - 1);
 1138  	}
 1139  
 1140  	do_trap_or_bp(regs, tcode, 0, "Trap");
 1141  
 1142  out:
 1143  	exception_exit(prev_state);
 1144  	return;
 1145  
 1146  out_sigsegv:
 1147  	force_sig(SIGSEGV);
 1148  	goto out;
 1149  }
```

【force_sig的代码（kernel/signal.c）】
```c
 1651  void force_sig(int sig)  {
 1652  	struct kernel_siginfo info;
 1653  
 1654  	clear_siginfo(&info);
 1655  	info.si_signo = sig;
 1656  	info.si_errno = 0;
 1657  	info.si_code = SI_KERNEL;
 1658  	info.si_pid = 0;
 1659  	info.si_uid = 0;
 1660  	force_sig_info(&info);
 1661  }
```

【force_sig_info的代码（kernel/signal.c）】
```c
 1356  int force_sig_info(struct kernel_siginfo *info)  {
 1357  	return force_sig_info_to_task(info, current, HANDLER_CURRENT);
 1358  }
```

【force_sig_info_to_task的代码（kernel/signal.c）】
```c
 1323  static int force_sig_info_to_task(struct kernel_siginfo *info, struct task_struct *t, 	enum sig_handler handler)  {
 1324  	unsigned long int flags;
 1325  	int ret, blocked, ignored;
 1326  	struct k_sigaction *action;
 1327  	int sig = info->si_signo;
 1328  
 1329  	spin_lock_irqsave(&t->sighand->siglock, flags);
 1330  	action = &t->sighand->action[sig-1];
 1331  	ignored = action->sa.sa_handler == SIG_IGN;
 1332  	blocked = sigismember(&t->blocked, sig);
 1333  	if (blocked || ignored || (handler != HANDLER_CURRENT)) {
 1334  		action->sa.sa_handler = SIG_DFL;
 1335  		if (handler == HANDLER_EXIT)
 1336  			action->sa.sa_flags |= SA_IMMUTABLE;
 1337  		if (blocked) {
 1338  			sigdelset(&t->blocked, sig);
 1339  			recalc_sigpending_and_wake(t);
 1340  		}
 1341  	}
 1342  	/*
 1343  	 * Don't clear SIGNAL_UNKILLABLE for traced tasks, users won't expect
 1344  	 * debugging to leave init killable. But HANDLER_EXIT is always fatal.
 1345  	 */
 1346  	if (action->sa.sa_handler == SIG_DFL &&
 1347  	    (!t->ptrace || (handler == HANDLER_EXIT)))
 1348  		t->signal->flags &= ~SIGNAL_UNKILLABLE;
 1349  	ret = send_signal_locked(sig, info, t, PIDTYPE_PID);
 1350  	spin_unlock_irqrestore(&t->sighand->siglock, flags);
 1351  
 1352  	return ret;
 1353  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M29

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/traps.c中的do_tr

【程序给出的理由】sleep B:trap: line 1133 __get_inst32 -> get_user

【调用链】__get_inst32（arch/mips/kernel/access-helper.h第18行调用get_user）

【do_tr的代码】
```c
 1115  asmlinkage void do_tr(struct pt_regs *regs)  {
 1116  	u32 opcode, tcode = 0;
 1117  	enum ctx_state prev_state;
 1118  	u16 instr[2];
 1119  	bool user = user_mode(regs);
 1120  	unsigned long epc = msk_isa16_mode(exception_epc(regs));
 1121  
 1122  	prev_state = exception_enter();
 1123  	current->thread.trap_nr = (regs->cp0_cause >> 2) & 0x1f;
 1124  	if (get_isa16_mode(regs->cp0_epc)) {
 1125  		if (__get_inst16(&instr[0], (u16 *)(epc + 0), user) ||
 1126  		    __get_inst16(&instr[1], (u16 *)(epc + 2), user))
 1127  			goto out_sigsegv;
 1128  		opcode = (instr[0] << 16) | instr[1];
 1129  		/* Immediate versions don't provide a code.  */
 1130  		if (!(opcode & OPCODE))
 1131  			tcode = (opcode >> 12) & ((1 << 4) - 1);
 1132  	} else {
 1133  		if (__get_inst32(&opcode, (u32 *)epc, user))
 1134  			goto out_sigsegv;
 1135  		/* Immediate versions don't provide a code.  */
 1136  		if (!(opcode & OPCODE))
 1137  			tcode = (opcode >> 6) & ((1 << 10) - 1);
 1138  	}
 1139  
 1140  	do_trap_or_bp(regs, tcode, 0, "Trap");
 1141  
 1142  out:
 1143  	exception_exit(prev_state);
 1144  	return;
 1145  
 1146  out_sigsegv:
 1147  	force_sig(SIGSEGV);
 1148  	goto out;
 1149  }
```

【__get_inst32的代码（arch/mips/kernel/access-helper.h）】
```c
   17  static inline int __get_inst32(u32 *i, u32 *p, bool user)  {
   18  	return user ? get_user(*i, (u32 __user *)p) : get_kernel_nofault(*i, p);
   19  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M30

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kvm/mips.c中的kvm_mips_handle_exit

【程序给出的理由】noinstr N2: line 1396 __kvm_mips_handle_exit -> instrumentable callee

【调用链】__kvm_mips_handle_exit（arch/mips/kvm/mips.c第1203行调用）

【kvm_mips_handle_exit的代码】
```c
 1392  int noinstr kvm_mips_handle_exit(struct kvm_vcpu *vcpu)  {
 1393  	int ret;
 1394  
 1395  	guest_state_exit_irqoff();
 1396  	ret = __kvm_mips_handle_exit(vcpu);
 1397  	guest_state_enter_irqoff();
 1398  
 1399  	return ret;
 1400  }
```

【__kvm_mips_handle_exit的代码（arch/mips/kvm/mips.c）】
```c
 1203  static int __kvm_mips_handle_exit(struct kvm_vcpu *vcpu)  {
 1204  	struct kvm_run *run = vcpu->run;
 1205  	u32 cause = vcpu->arch.host_cp0_cause;
 1206  	u32 exccode = (cause >> CAUSEB_EXCCODE) & 0x1f;
 1207  	u32 __user *opc = (u32 __user *) vcpu->arch.pc;
 1208  	unsigned long badvaddr = vcpu->arch.host_cp0_badvaddr;
 1209  	enum emulation_result er = EMULATE_DONE;
 1210  	u32 inst;
 1211  	int ret = RESUME_GUEST;
 1212  
 1213  	vcpu->mode = OUTSIDE_GUEST_MODE;
 1214  
 1215  	/* Set a default exit reason */
 1216  	run->exit_reason = KVM_EXIT_UNKNOWN;
 1217  	run->ready_for_interrupt_injection = 1;
 1218  
 1219  	/*
 1220  	 * Set the appropriate status bits based on host CPU features,
 1221  	 * before we hit the scheduler
 1222  	 */
 1223  	kvm_mips_set_c0_status();
 1224  
 1225  	local_irq_enable();
 1226  
 1227  	kvm_debug("kvm_mips_handle_exit: cause: %#x, PC: %p, kvm_run: %p, kvm_vcpu: %p\n",
 1228  			cause, opc, run, vcpu);
 1229  	trace_kvm_exit(vcpu, exccode);
 1230  
 1231  	switch (exccode) {
 1232  	case EXCCODE_INT:
 1233  		kvm_debug("[%d]EXCCODE_INT @ %p\n", vcpu->vcpu_id, opc);
 1234  
 1235  		++vcpu->stat.int_exits;
 1236  
 1237  		if (need_resched())
 1238  			cond_resched();
 1239  
 1240  		ret = RESUME_GUEST;
 1241  		break;
 1242  
 1243  	case EXCCODE_CPU:
 1244  		kvm_debug("EXCCODE_CPU: @ PC: %p\n", opc);
 1245  
 1246  		++vcpu->stat.cop_unusable_exits;
 1247  		ret = kvm_mips_callbacks->handle_cop_unusable(vcpu);
 1248  		/* XXXKYMA: Might need to return to user space */
 1249  		if (run->exit_reason == KVM_EXIT_IRQ_WINDOW_OPEN)
 1250  			ret = RESUME_HOST;
 1251  		break;
 1252  
 1253  	case EXCCODE_MOD:
 1254  		++vcpu->stat.tlbmod_exits;
 1255  		ret = kvm_mips_callbacks->handle_tlb_mod(vcpu);
 1256  		break;
 1257  
 1258  	case EXCCODE_TLBS:
 1259  		kvm_debug("TLB ST fault:  cause %#x, status %#x, PC: %p, BadVaddr: %#lx\n",
 1260  			  cause, kvm_read_c0_guest_status(vcpu->arch.cop0), opc,
 1261  			  badvaddr);
 1262  
 1263  		++vcpu->stat.tlbmiss_st_exits;
 1264  		ret = kvm_mips_callbacks->handle_tlb_st_miss(vcpu);
 1265  		break;
 1266  
 1267  	case EXCCODE_TLBL:
 1268  		kvm_debug("TLB LD fault: cause %#x, PC: %p, BadVaddr: %#lx\n",
 1269  			  cause, opc, badvaddr);
 1270  
 1271  		++vcpu->stat.tlbmiss_ld_exits;
 1272  		ret = kvm_mips_callbacks->handle_tlb_ld_miss(vcpu);
 1273  		break;
 1274  
 1275  	case EXCCODE_ADES:
 1276  		++vcpu->stat.addrerr_st_exits;
 1277  		ret = kvm_mips_callbacks->handle_addr_err_st(vcpu);
 1278  		break;
 1279  
 1280  	case EXCCODE_ADEL:
 1281  		++vcpu->stat.addrerr_ld_exits;
 1282  		ret = kvm_mips_callbacks->handle_addr_err_ld(vcpu);
...（其余107行省略）
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M31

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/lantiq/xway/sysctrl.c中的pmu_enable

【程序给出的理由】rt D:hook: line 214 spin_lock -> spin_lock

【pmu_enable的代码】
```c
  204  static int pmu_enable(struct clk *clk)  {
  205  	int retry = 1000000;
  206  
  207  	if (of_machine_is_compatible("lantiq,ar10")
  208  	    || of_machine_is_compatible("lantiq,grx390")) {
  209  		pmu_w32(clk->bits, PWDCR_EN_XRX(clk->module));
  210  		do {} while (--retry &&
  211  			     (!(pmu_r32(PWDSR_XRX(clk->module)) & clk->bits)));
  212  
  213  	} else {
  214  		spin_lock(&g_pmu_lock);
  215  		pmu_w32(pmu_r32(PWDCR(clk->module)) & ~clk->bits,
  216  				PWDCR(clk->module));
  217  		do {} while (--retry &&
  218  			     (pmu_r32(PWDSR(clk->module)) & clk->bits));
  219  		spin_unlock(&g_pmu_lock);
  220  	}
  221  
  222  	if (!retry)
  223  		panic("activating PMU module failed!");
  224  
  225  	return 0;
  226  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M32

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/kernel/sysrq.c中的sysrq_tlbdump_single

【程序给出的理由】rt C:callback: line 27 spin_lock_irqsave -> spin_lock_irqsave

【sysrq_tlbdump_single的代码】
```c
   24  static void sysrq_tlbdump_single(void *dummy)  {
   25  	unsigned long flags;
   26  
   27  	spin_lock_irqsave(&show_lock, flags);
   28  
   29  	pr_info("CPU%d:\n", smp_processor_id());
   30  	dump_tlb_regs();
   31  	pr_info("\n");
   32  	dump_tlb_all();
   33  	pr_info("\n");
   34  
   35  	spin_unlock_irqrestore(&show_lock, flags);
   36  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M33

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/txx9/generic/setup_tx4938.c中的tx4938_machine_restart

【程序给出的理由】sleep A:irq: line 55 txx9_wdt_now -> mutex_lock

【调用链】txx9_wdt_now（arch/mips/txx9/generic/setup.c第333行调用ioremap） → ioremap（lib/logic_iomem.c第92行调用mutex_lock）

【tx4938_machine_restart的代码】
```c
   48  static void tx4938_machine_restart(char *command)  {
   49  	local_irq_disable();
   50  	pr_emerg("Rebooting (with %s watchdog reset)...\n",
   51  		 (____raw_readq(&tx4938_ccfgptr->ccfg) & TX4938_CCFG_WDREXEN) ?
   52  		 "external" : "internal");
   53  	/* clear watchdog status */
   54  	tx4938_ccfg_set(TX4938_CCFG_WDRST);	/* W1C */
   55  	txx9_wdt_now(TX4938_TMR_REG(2) & 0xfffffffffULL);
   56  	while (!(____raw_readq(&tx4938_ccfgptr->ccfg) & TX4938_CCFG_WDRST))
   57  		;
   58  	mdelay(10);
   59  	if (____raw_readq(&tx4938_ccfgptr->ccfg) & TX4938_CCFG_WDREXEN) {
   60  		pr_emerg("Rebooting (with internal watchdog reset)...\n");
   61  		/* External WDRST failed.  Do internal watchdog reset */
   62  		tx4938_ccfg_clear(TX4938_CCFG_WDREXEN);
   63  	}
   64  	/* fallback */
   65  	(*_machine_halt)();
   66  }
```

【txx9_wdt_now的代码（arch/mips/txx9/generic/setup.c）】
```c
  331  void txx9_wdt_now(unsigned long base)  {
  332  	struct txx9_tmr_reg __iomem *tmrptr =
  333  		ioremap(base, sizeof(struct txx9_tmr_reg));
  334  	/* disable watch dog timer */
  335  	__raw_writel(TXx9_TMWTMR_WDIS | TXx9_TMWTMR_TWC, &tmrptr->wtmr);
  336  	__raw_writel(0, &tmrptr->tcr);
  337  	/* kick watchdog */
  338  	__raw_writel(TXx9_TMWTMR_TWIE, &tmrptr->wtmr);
  339  	__raw_writel(1, &tmrptr->cpra); /* immediate */
  340  	__raw_writel(TXx9_TMTCR_TCE | TXx9_TMTCR_CCDE | TXx9_TMTCR_TMODE_WDOG,
  341  		     &tmrptr->tcr);
  342  }
```

【ioremap的代码（lib/logic_iomem.c）】
```c
   87  void __iomem *ioremap(phys_addr_t offset, size_t size)  {
   88  	void __iomem *ret = NULL;
   89  	struct logic_iomem_region *rreg, *found = NULL;
   90  	int i;
   91  
   92  	mutex_lock(&regions_mtx);
   93  	list_for_each_entry(rreg, &regions_list, list) {
   94  		if (rreg->res->start > offset)
   95  			continue;
   96  		if (rreg->res->end < offset + size - 1)
   97  			continue;
   98  		found = rreg;
   99  		break;
  100  	}
  101  
  102  	if (!found)
  103  		goto out;
  104  
  105  	for (i = 0; i < MAX_AREAS; i++) {
  106  		long offs;
  107  
  108  		if (mapped_areas[i].ops)
  109  			continue;
  110  
  111  		offs = rreg->ops->map(offset - found->res->start,
  112  				      size, &mapped_areas[i].ops,
  113  				      &mapped_areas[i].priv);
  114  		if (offs < 0) {
  115  			mapped_areas[i].ops = NULL;
  116  			break;
  117  		}
  118  
  119  		if (WARN_ON(!mapped_areas[i].ops)) {
  120  			mapped_areas[i].ops = NULL;
  121  			break;
  122  		}
  123  
  124  		ret = (void __iomem *)(IOREMAP_BIAS + (i << AREA_SHIFT) + offs);
  125  		break;
  126  	}
  127  out:
  128  	mutex_unlock(&regions_mtx);
  129  	if (ret)
  130  		return ret;
  131  	return real_ioremap(offset, size);
  132  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M34

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】同一约定规则：公共代码调用、各架构各自实现的函数中，arm64、x86、RISC-V三个实现都调用了某个函数，MIPS的实现没有。

【被标记的位置】arch/mips/kernel/uprobes.c中的arch_uprobe_post_xol

【程序给出的理由】all three references call ['WARN_ON_ONCE'], mips does not

【arch_uprobe_post_xol的代码】
```c
  127  int arch_uprobe_post_xol(struct arch_uprobe *aup, struct pt_regs *regs)  {
  128  	struct uprobe_task *utask = current->utask;
  129  
  130  	current->thread.trap_nr = utask->autask.saved_trap_nr;
  131  	regs->cp0_epc = aup->resume_epc;
  132  
  133  	return 0;
  134  }
```

【参照：arm64的arch_uprobe_post_xol（arch/arm64/kernel/probes/uprobes.c）】
```c
   78  int arch_uprobe_post_xol(struct arch_uprobe *auprobe, struct pt_regs *regs)  {
   79  	struct uprobe_task *utask = current->utask;
   80  
   81  	WARN_ON_ONCE(current->thread.fault_code != UPROBE_INV_FAULT_CODE);
   82  
   83  	/* Instruction points to execute next to breakpoint address */
   84  	instruction_pointer_set(regs, utask->vaddr + 4);
   85  
   86  	user_disable_single_step(current);
   87  
   88  	return 0;
   89  }
```

【参照：x86的arch_uprobe_post_xol（arch/x86/kernel/uprobes.c）】
```c
  962  int arch_uprobe_post_xol(struct arch_uprobe *auprobe, struct pt_regs *regs)  {
  963  	struct uprobe_task *utask = current->utask;
  964  	bool send_sigtrap = utask->autask.saved_tf;
  965  	int err = 0;
  966  
  967  	WARN_ON_ONCE(current->thread.trap_nr != UPROBE_TRAP_NR);
  968  	current->thread.trap_nr = utask->autask.saved_trap_nr;
  969  
  970  	if (auprobe->ops->post_xol) {
  971  		err = auprobe->ops->post_xol(auprobe, regs);
  972  		if (err) {
  973  			/*
  974  			 * Restore ->ip for restart or post mortem analysis.
  975  			 * ->post_xol() must not return -ERESTART unless this
  976  			 * is really possible.
  977  			 */
  978  			regs->ip = utask->vaddr;
  979  			if (err == -ERESTART)
  980  				err = 0;
  981  			send_sigtrap = false;
  982  		}
  983  	}
  984  	/*
  985  	 * arch_uprobe_pre_xol() doesn't save the state of TIF_BLOCKSTEP
  986  	 * so we can get an extra SIGTRAP if we do not clear TF. We need
  987  	 * to examine the opcode to make it right.
  988  	 */
  989  	if (send_sigtrap)
  990  		send_sig(SIGTRAP, current, 0);
  991  
  992  	if (!utask->autask.saved_tf)
  993  		regs->flags &= ~X86_EFLAGS_TF;
  994  
  995  	return err;
  996  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M35

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】同一约定规则：公共代码调用、各架构各自实现的函数中，arm64、x86、RISC-V三个实现都调用了某个函数，MIPS的实现没有。

【被标记的位置】arch/mips/mm/extable.c中的fixup_exception

【程序给出的理由】all three references call ['BUG'], mips does not

【fixup_exception的代码】
```c
   14  int fixup_exception(struct pt_regs *regs)  {
   15  	const struct exception_table_entry *fixup;
   16  
   17  	fixup = search_exception_tables(exception_epc(regs));
   18  	if (fixup) {
   19  		regs->cp0_epc = fixup->nextinsn;
   20  
   21  		return 1;
   22  	}
   23  
   24  	return 0;
   25  }
```

【参照：arm64的fixup_exception（arch/arm64/mm/extable.c）】
```c
   60  bool fixup_exception(struct pt_regs *regs)  {
   61  	const struct exception_table_entry *ex;
   62  
   63  	ex = search_exception_tables(instruction_pointer(regs));
   64  	if (!ex)
   65  		return false;
   66  
   67  	switch (ex->type) {
   68  	case EX_TYPE_BPF:
   69  		return ex_handler_bpf(ex, regs);
   70  	case EX_TYPE_UACCESS_ERR_ZERO:
   71  	case EX_TYPE_KACCESS_ERR_ZERO:
   72  		return ex_handler_uaccess_err_zero(ex, regs);
   73  	case EX_TYPE_LOAD_UNALIGNED_ZEROPAD:
   74  		return ex_handler_load_unaligned_zeropad(ex, regs);
   75  	}
   76  
   77  	BUG();
   78  }
```

【参照：x86的fixup_exception（arch/x86/mm/extable.c）】
```c
  207  int fixup_exception(struct pt_regs *regs, int trapnr, unsigned long error_code, 		    unsigned long fault_addr)  {
  208  	const struct exception_table_entry *e;
  209  	int type, reg, imm;
  210  
  211  #ifdef CONFIG_PNPBIOS
  212  	if (unlikely(SEGMENT_IS_PNP_CODE(regs->cs))) {
  213  		extern u32 pnp_bios_fault_eip, pnp_bios_fault_esp;
  214  		extern u32 pnp_bios_is_utter_crap;
  215  		pnp_bios_is_utter_crap = 1;
  216  		printk(KERN_CRIT "PNPBIOS fault.. attempting recovery.\n");
  217  		__asm__ volatile(
  218  			"movl %0, %%esp\n\t"
  219  			"jmp *%1\n\t"
  220  			: : "g" (pnp_bios_fault_esp), "g" (pnp_bios_fault_eip));
  221  		panic("do_trap: can't hit this");
  222  	}
  223  #endif
  224  
  225  	e = search_exception_tables(regs->ip);
  226  	if (!e)
  227  		return 0;
  228  
  229  	type = FIELD_GET(EX_DATA_TYPE_MASK, e->data);
  230  	reg  = FIELD_GET(EX_DATA_REG_MASK,  e->data);
  231  	imm  = FIELD_GET(EX_DATA_IMM_MASK,  e->data);
  232  
  233  	switch (type) {
  234  	case EX_TYPE_DEFAULT:
  235  	case EX_TYPE_DEFAULT_MCE_SAFE:
  236  		return ex_handler_default(e, regs);
  237  	case EX_TYPE_FAULT:
  238  	case EX_TYPE_FAULT_MCE_SAFE:
  239  		return ex_handler_fault(e, regs, trapnr);
  240  	case EX_TYPE_UACCESS:
  241  		return ex_handler_uaccess(e, regs, trapnr);
  242  	case EX_TYPE_COPY:
  243  		return ex_handler_copy(e, regs, trapnr);
  244  	case EX_TYPE_CLEAR_FS:
  245  		return ex_handler_clear_fs(e, regs);
  246  	case EX_TYPE_FPU_RESTORE:
  247  		return ex_handler_fprestore(e, regs);
  248  	case EX_TYPE_BPF:
  249  		return ex_handler_bpf(e, regs);
  250  	case EX_TYPE_WRMSR:
  251  		return ex_handler_msr(e, regs, true, false, reg);
  252  	case EX_TYPE_RDMSR:
  253  		return ex_handler_msr(e, regs, false, false, reg);
  254  	case EX_TYPE_WRMSR_SAFE:
  255  		return ex_handler_msr(e, regs, true, true, reg);
  256  	case EX_TYPE_RDMSR_SAFE:
...（其余21行省略）
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M36

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】同一约定规则：公共代码调用、各架构各自实现的函数中，arm64、x86、RISC-V三个实现都调用了某个函数，MIPS的实现没有。

【被标记的位置】arch/mips/kernel/setup.c中的setup_arch

【程序给出的理由】all three references call ['efi_init', 'jump_label_init', 'parse_early_param', 'setup_initial_init_mm'], mips does not

【setup_arch的代码】
```c
  779  void __init setup_arch(char **cmdline_p)  {
  780  	cpu_probe();
  781  	mips_cm_probe();
  782  	prom_init();
  783  
  784  	setup_early_fdc_console();
  785  #ifdef CONFIG_EARLY_PRINTK
  786  	setup_early_printk();
  787  #endif
  788  	cpu_report();
  789  	check_bugs_early();
  790  
  791  #if defined(CONFIG_VT)
  792  #if defined(CONFIG_VGA_CONSOLE)
  793  	conswitchp = &vga_con;
  794  #endif
  795  #endif
  796  
  797  	arch_mem_init(cmdline_p);
  798  	dmi_setup();
  799  
  800  	resource_init();
  801  	plat_smp_setup();
  802  	prefill_possible_map();
  803  
  804  	cpu_cache_init();
  805  	paging_init();
  806  
  807  	memblock_dump_all();
  808  
  809  	setup_rng_seed();
  810  }
```

【参照：arm64的setup_arch（arch/arm64/kernel/setup.c）】
```c
  291  void __init __no_sanitize_address setup_arch(char **cmdline_p)  {
  292  	setup_initial_init_mm(_stext, _etext, _edata, _end);
  293  
  294  	*cmdline_p = boot_command_line;
  295  
  296  	/*
  297  	 * If know now we are going to need KPTI then use non-global
  298  	 * mappings from the start, avoiding the cost of rewriting
  299  	 * everything later.
  300  	 */
  301  	arm64_use_ng_mappings = kaslr_requires_kpti();
  302  
  303  	early_fixmap_init();
  304  	early_ioremap_init();
  305  
  306  	setup_machine_fdt(__fdt_pointer);
  307  
  308  	/*
  309  	 * Initialise the static keys early as they may be enabled by the
  310  	 * cpufeature code and early parameters.
  311  	 */
  312  	jump_label_init();
  313  	parse_early_param();
  314  
  315  	/*
  316  	 * Unmask asynchronous aborts and fiq after bringing up possible
  317  	 * earlycon. (Report possible System Errors once we can report this
  318  	 * occurred).
  319  	 */
  320  	local_daif_restore(DAIF_PROCCTX_NOIRQ);
  321  
  322  	/*
  323  	 * TTBR0 is only used for the identity mapping at this stage. Make it
  324  	 * point to zero page to avoid speculatively fetching new entries.
  325  	 */
  326  	cpu_uninstall_idmap();
  327  
  328  	xen_early_init();
  329  	efi_init();
  330  
  331  	if (!efi_enabled(EFI_BOOT) && ((u64)_text % MIN_KIMG_ALIGN) != 0)
  332  	     pr_warn(FW_BUG "Kernel image misaligned at boot, please fix your bootloader!");
  333  
  334  	arm64_memblock_init();
  335  
  336  	paging_init();
  337  
  338  	acpi_table_upgrade();
  339  
  340  	/* Parse the ACPI tables for possible boot-time configuration */
...（其余41行省略）
```

【参照：x86的setup_arch（arch/x86/kernel/setup.c）】
```c
  865  void __init setup_arch(char **cmdline_p)  {
  866  #ifdef CONFIG_X86_32
  867  	memcpy(&boot_cpu_data, &new_cpu_data, sizeof(new_cpu_data));
  868  
  869  	/*
  870  	 * copy kernel address range established so far and switch
  871  	 * to the proper swapper page table
  872  	 */
  873  	clone_pgd_range(swapper_pg_dir     + KERNEL_PGD_BOUNDARY,
  874  			initial_page_table + KERNEL_PGD_BOUNDARY,
  875  			KERNEL_PGD_PTRS);
  876  
  877  	load_cr3(swapper_pg_dir);
  878  	/*
  879  	 * Note: Quark X1000 CPUs advertise PGE incorrectly and require
  880  	 * a cr3 based tlb flush, so the following __flush_tlb_all()
  881  	 * will not flush anything because the CPU quirk which clears
  882  	 * X86_FEATURE_PGE has not been invoked yet. Though due to the
  883  	 * load_cr3() above the TLB has been flushed already. The
  884  	 * quirk is invoked before subsequent calls to __flush_tlb_all()
  885  	 * so proper operation is guaranteed.
  886  	 */
  887  	__flush_tlb_all();
  888  #else
  889  	printk(KERN_INFO "Command line: %s\n", boot_command_line);
  890  	boot_cpu_data.x86_phys_bits = MAX_PHYSMEM_BITS;
  891  #endif
  892  
  893  	/*
  894  	 * If we have OLPC OFW, we might end up relocating the fixmap due to
  895  	 * reserve_top(), so do this before touching the ioremap area.
  896  	 */
  897  	olpc_ofw_detect();
  898  
  899  	idt_setup_early_traps();
  900  	early_cpu_init();
  901  	jump_label_init();
  902  	static_call_init();
  903  	early_ioremap_init();
  904  
  905  	setup_olpc_ofw_pgd();
  906  
  907  	ROOT_DEV = old_decode_dev(boot_params.hdr.root_dev);
  908  	screen_info = boot_params.screen_info;
  909  	edid_info = boot_params.edid_info;
  910  #ifdef CONFIG_X86_32
  911  	apm_info.bios = boot_params.apm_bios_info;
  912  	ist_info = boot_params.ist_info;
  913  #endif
  914  	saved_video_mode = boot_params.hdr.vid_mode;
...（其余420行省略）
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M37

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】同一约定规则：公共代码调用、各架构各自实现的函数中，arm64、x86、RISC-V三个实现都调用了某个函数，MIPS的实现没有。

【被标记的位置】arch/mips/include/asm/syscall.h中的syscall_get_error

【程序给出的理由】all three references call ['IS_ERR_VALUE'], mips does not

【syscall_get_error的代码】
```c
   95  static inline long syscall_get_error(struct task_struct *task, 				     struct pt_regs *regs)  {
   96  	return regs->regs[7] ? -regs->regs[2] : 0;
   97  }
```

【参照：arm64的syscall_get_error（arch/arm64/include/asm/syscall.h）】
```c
   45  static inline long syscall_get_error(struct task_struct *task, 				     struct pt_regs *regs)  {
   46  	unsigned long error = syscall_get_return_value(task, regs);
   47  
   48  	return IS_ERR_VALUE(error) ? error : 0;
   49  }
```

【参照：x86的syscall_get_error（arch/x86/include/asm/syscall.h）】
```c
   51  static inline long syscall_get_error(struct task_struct *task, 				     struct pt_regs *regs)  {
   52  	unsigned long error = regs->ax;
   53  #ifdef CONFIG_IA32_EMULATION
   54  	/*
   55  	 * TS_COMPAT is set for 32-bit syscall entries and then
   56  	 * remains set until we return to user mode.
   57  	 */
   58  	if (task->thread_info.status & (TS_COMPAT|TS_I386_REGS_POKED))
   59  		/*
   60  		 * Sign-extend the value so (int)-EFOO becomes (long)-EFOO
   61  		 * and will match correctly in comparisons.
   62  		 */
   63  		error = (long) (int) error;
   64  #endif
   65  	return IS_ERR_VALUE(error) ? error : 0;
   66  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M38

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】推测执行越界规则：函数对一个可能来自客体（虚拟机）或用户的下标做了上界检查，随后用它访问数组，却没有用array_index_nospec，可能被推测执行越界利用（Spectre-v1）。

【被标记的位置】arch/mips/kvm/vz.c中的kvm_vz_set_one_reg

【程序给出的理由】line 2356: [idx] after bound check at line 2354, no array_index_nospec

【kvm_vz_set_one_reg的代码】
```c
 2137  static int kvm_vz_set_one_reg(struct kvm_vcpu *vcpu, 			      const struct kvm_one_reg *reg, 			      s64 v)  {
 2138  	struct mips_coproc *cop0 = vcpu->arch.cop0;
 2139  	unsigned int idx;
 2140  	int ret = 0;
 2141  	unsigned int cur, change;
 2142  
 2143  	switch (reg->id) {
 2144  	case KVM_REG_MIPS_CP0_INDEX:
 2145  		write_gc0_index(v);
 2146  		break;
 2147  	case KVM_REG_MIPS_CP0_ENTRYLO0:
 2148  		write_gc0_entrylo0(entrylo_user_to_kvm(v));
 2149  		break;
 2150  	case KVM_REG_MIPS_CP0_ENTRYLO1:
 2151  		write_gc0_entrylo1(entrylo_user_to_kvm(v));
 2152  		break;
 2153  	case KVM_REG_MIPS_CP0_CONTEXT:
 2154  		write_gc0_context(v);
 2155  		break;
 2156  	case KVM_REG_MIPS_CP0_CONTEXTCONFIG:
 2157  		if (!cpu_guest_has_contextconfig)
 2158  			return -EINVAL;
 2159  		write_gc0_contextconfig(v);
 2160  		break;
 2161  	case KVM_REG_MIPS_CP0_USERLOCAL:
 2162  		if (!cpu_guest_has_userlocal)
 2163  			return -EINVAL;
 2164  		write_gc0_userlocal(v);
 2165  		break;
 2166  #ifdef CONFIG_64BIT
 2167  	case KVM_REG_MIPS_CP0_XCONTEXTCONFIG:
 2168  		if (!cpu_guest_has_contextconfig)
 2169  			return -EINVAL;
 2170  		write_gc0_xcontextconfig(v);
 2171  		break;
 2172  #endif
 2173  	case KVM_REG_MIPS_CP0_PAGEMASK:
 2174  		write_gc0_pagemask(v);
 2175  		break;
 2176  	case KVM_REG_MIPS_CP0_PAGEGRAIN:
 2177  		write_gc0_pagegrain(v);
 2178  		break;
 2179  	case KVM_REG_MIPS_CP0_SEGCTL0:
 2180  		if (!cpu_guest_has_segments)
 2181  			return -EINVAL;
 2182  		write_gc0_segctl0(v);
 2183  		break;
 2184  	case KVM_REG_MIPS_CP0_SEGCTL1:
 2185  		if (!cpu_guest_has_segments)
 2186  			return -EINVAL;
 2187  		write_gc0_segctl1(v);
 2188  		break;
 2189  	case KVM_REG_MIPS_CP0_SEGCTL2:
 2190  		if (!cpu_guest_has_segments)
 2191  			return -EINVAL;
 2192  		write_gc0_segctl2(v);
 2193  		break;
 2194  	case KVM_REG_MIPS_CP0_PWBASE:
 2195  		if (!cpu_guest_has_htw && !cpu_guest_has_ldpte)
 2196  			return -EINVAL;
 2197  		write_gc0_pwbase(v);
 2198  		break;
 2199  	case KVM_REG_MIPS_CP0_PWFIELD:
 2200  		if (!cpu_guest_has_htw && !cpu_guest_has_ldpte)
 2201  			return -EINVAL;
 2202  		write_gc0_pwfield(v);
 2203  		break;
 2204  	case KVM_REG_MIPS_CP0_PWSIZE:
 2205  		if (!cpu_guest_has_htw && !cpu_guest_has_ldpte)
 2206  			return -EINVAL;
 2207  		write_gc0_pwsize(v);
 2208  		break;
 2209  	case KVM_REG_MIPS_CP0_WIRED:
 2210  		change_gc0_wired(MIPSR6_WIRED_WIRED, v);
 2211  		break;
 2212  	case KVM_REG_MIPS_CP0_PWCTL:
 2213  		if (!cpu_guest_has_htw && !cpu_guest_has_ldpte)
 2214  			return -EINVAL;
 2215  		write_gc0_pwctl(v);
 2216  		break;
...（其余193行省略）
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

## M39

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.3）的MIPS代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的MIPS钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/mips/cavium-octeon/csrc-octeon.c中的sched_clock

【程序给出的理由】noinstr N1: line 115 sched_clock -> called from noinstr/__cpuidle

【sched_clock的代码】
```c
  115  unsigned long long notrace sched_clock(void)  {
  116  	/* 64-bit arithmatic can overflow, so use 128-bit.  */
  117  	u64 t1, t2, t3;
  118  	unsigned long long rv;
  119  	u64 mult = clocksource_mips.mult;
  120  	u64 shift = clocksource_mips.shift;
  121  	u64 cnt = read_c0_cvmcount();
  122  
  123  	asm (
  124  		"dmultu\t%[cnt],%[mult]\n\t"
  125  		"nor\t%[t1],$0,%[shift]\n\t"
  126  		"mfhi\t%[t2]\n\t"
  127  		"mflo\t%[t3]\n\t"
  128  		"dsll\t%[t2],%[t2],1\n\t"
  129  		"dsrlv\t%[rv],%[t3],%[shift]\n\t"
  130  		"dsllv\t%[t1],%[t2],%[t1]\n\t"
  131  		"or\t%[rv],%[t1],%[rv]\n\t"
  132  		: [rv] "=&r" (rv), [t1] "=&r" (t1), [t2] "=&r" (t2), [t3] "=&r" (t3)
  133  		: [cnt] "r" (cnt), [mult] "r" (mult), [shift] "r" (shift)
  134  		: "hi", "lo");
  135  	return rv;
  136  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是MIPS特有的问题，还是所有架构都一样。拿不准就回答unsure。

