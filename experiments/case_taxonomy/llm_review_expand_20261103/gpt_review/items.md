# 待复核的标记（60条）

## C0_00

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的die

【程序给出的理由】sleep A:raw: line 244 show_registers -> get_user

【调用链】show_registers（arch/loongarch/kernel/traps.c第221行调用show_stacktrace） → show_stacktrace（arch/loongarch/kernel/traps.c第107行调用__get_addr） → __get_addr（arch/loongarch/kernel/access-helper.h第12行调用get_user）

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

【show_registers的代码（arch/loongarch/kernel/traps.c）】
```c
  215  void show_registers(struct pt_regs *regs)  {
  216  	__show_regs(regs);
  217  	print_modules();
  218  	printk("Process %s (pid: %d, threadinfo=%p, task=%p)\n",
  219  	       current->comm, current->pid, current_thread_info(), current);
  220  
  221  	show_stacktrace(current, regs, KERN_DEFAULT, user_mode(regs));
  222  	show_code((void *)regs->csr_era, user_mode(regs));
  223  	printk("\n");
  224  }
```

【show_stacktrace的代码（arch/loongarch/kernel/traps.c）】
```c
   89  static void show_stacktrace(struct task_struct *task, 	const struct pt_regs *regs, const char *loglvl, bool user)  {
   90  	int i;
   91  	const int field = 2 * sizeof(unsigned long);
   92  	unsigned long stackdata;
   93  	unsigned long *sp = (unsigned long *)regs->regs[3];
   94  
   95  	printk("%sStack :", loglvl);
   96  	i = 0;
   97  	while ((unsigned long) sp & (PAGE_SIZE - 1)) {
   98  		if (i && ((i % (64 / field)) == 0)) {
   99  			pr_cont("\n");
  100  			printk("%s       ", loglvl);
  101  		}
  102  		if (i > 39) {
  103  			pr_cont(" ...");
  104  			break;
  105  		}
  106  
  107  		if (__get_addr(&stackdata, sp++, user)) {
  108  			pr_cont(" (Bad stack address)");
  109  			break;
  110  		}
  111  
  112  		pr_cont(" %0*lx", field, stackdata);
  113  		i++;
  114  	}
  115  	pr_cont("\n");
  116  	show_backtrace(task, regs, loglvl, user);
  117  }
```

【__get_addr的代码（arch/loongarch/kernel/access-helper.h）】
```c
   11  static inline int __get_addr(unsigned long *a, unsigned long *p, bool user)  {
   12  	return user ? get_user(*a, (unsigned long __user *)p) : get_kernel_nofault(*a, p);
   13  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_01

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_ade

【程序给出的理由】rt B:trap: line 366 force_sig_fault -> spin_lock_irqsave

【调用链】force_sig_fault（kernel/signal.c第1726行调用force_sig_fault_to_task） → force_sig_fault_to_task（kernel/signal.c第1720行调用force_sig_info_to_task） → force_sig_info_to_task（kernel/signal.c第1329行调用spin_lock_irqsave）

【do_ade的代码】
```c
  362  asmlinkage void noinstr do_ade(struct pt_regs *regs)  {
  363  	irqentry_state_t state = irqentry_enter(regs);
  364  
  365  	die_if_kernel("Kernel ade access", regs);
  366  	force_sig_fault(SIGBUS, BUS_ADRERR, (void __user *)regs->csr_badvaddr);
  367  
  368  	irqentry_exit(regs, state);
  369  }
```

【force_sig_fault的代码（kernel/signal.c）】
```c
 1725  int force_sig_fault(int sig, int code, void __user *addr 	___ARCH_SI_IA64(int imm, unsigned int flags, unsigned long isr))  {
 1726  	return force_sig_fault_to_task(sig, code, addr
 1727  				       ___ARCH_SI_IA64(imm, flags, isr), current);
 1728  }
```

【force_sig_fault_to_task的代码（kernel/signal.c）】
```c
 1707  int force_sig_fault_to_task(int sig, int code, void __user *addr 	___ARCH_SI_IA64(int imm, unsigned int flags, unsigned long isr) 	, struct task_struct *t)  {
 1708  	struct kernel_siginfo info;
 1709  
 1710  	clear_siginfo(&info);
 1711  	info.si_signo = sig;
 1712  	info.si_errno = 0;
 1713  	info.si_code  = code;
 1714  	info.si_addr  = addr;
 1715  #ifdef __ia64__
 1716  	info.si_imm = imm;
 1717  	info.si_flags = flags;
 1718  	info.si_isr = isr;
 1719  #endif
 1720  	return force_sig_info_to_task(&info, t, HANDLER_CURRENT);
 1721  }
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

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_02

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_ade

【程序给出的理由】noinstr N2: line 366 force_sig_fault -> instrumentable callee

【调用链】force_sig_fault（kernel/signal.c第1725行调用）

【do_ade的代码】
```c
  362  asmlinkage void noinstr do_ade(struct pt_regs *regs)  {
  363  	irqentry_state_t state = irqentry_enter(regs);
  364  
  365  	die_if_kernel("Kernel ade access", regs);
  366  	force_sig_fault(SIGBUS, BUS_ADRERR, (void __user *)regs->csr_badvaddr);
  367  
  368  	irqentry_exit(regs, state);
  369  }
```

【force_sig_fault的代码（kernel/signal.c）】
```c
 1725  int force_sig_fault(int sig, int code, void __user *addr 	___ARCH_SI_IA64(int imm, unsigned int flags, unsigned long isr))  {
 1726  	return force_sig_fault_to_task(sig, code, addr
 1727  				       ___ARCH_SI_IA64(imm, flags, isr), current);
 1728  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_03

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_ale

【程序给出的理由】rt B:trap: line 376 force_sig_fault -> spin_lock_irqsave

【调用链】force_sig_fault（kernel/signal.c第1726行调用force_sig_fault_to_task） → force_sig_fault_to_task（kernel/signal.c第1720行调用force_sig_info_to_task） → force_sig_info_to_task（kernel/signal.c第1329行调用spin_lock_irqsave）

【do_ale的代码】
```c
  372  asmlinkage void noinstr do_ale(struct pt_regs *regs)  {
  373  	irqentry_state_t state = irqentry_enter(regs);
  374  
  375  	die_if_kernel("Kernel ale access", regs);
  376  	force_sig_fault(SIGBUS, BUS_ADRALN, (void __user *)regs->csr_badvaddr);
  377  
  378  	irqentry_exit(regs, state);
  379  }
```

【force_sig_fault的代码（kernel/signal.c）】
```c
 1725  int force_sig_fault(int sig, int code, void __user *addr 	___ARCH_SI_IA64(int imm, unsigned int flags, unsigned long isr))  {
 1726  	return force_sig_fault_to_task(sig, code, addr
 1727  				       ___ARCH_SI_IA64(imm, flags, isr), current);
 1728  }
```

【force_sig_fault_to_task的代码（kernel/signal.c）】
```c
 1707  int force_sig_fault_to_task(int sig, int code, void __user *addr 	___ARCH_SI_IA64(int imm, unsigned int flags, unsigned long isr) 	, struct task_struct *t)  {
 1708  	struct kernel_siginfo info;
 1709  
 1710  	clear_siginfo(&info);
 1711  	info.si_signo = sig;
 1712  	info.si_errno = 0;
 1713  	info.si_code  = code;
 1714  	info.si_addr  = addr;
 1715  #ifdef __ia64__
 1716  	info.si_imm = imm;
 1717  	info.si_flags = flags;
 1718  	info.si_isr = isr;
 1719  #endif
 1720  	return force_sig_info_to_task(&info, t, HANDLER_CURRENT);
 1721  }
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

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_04

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_ale

【程序给出的理由】noinstr N2: line 376 force_sig_fault -> instrumentable callee

【调用链】force_sig_fault（kernel/signal.c第1725行调用）

【do_ale的代码】
```c
  372  asmlinkage void noinstr do_ale(struct pt_regs *regs)  {
  373  	irqentry_state_t state = irqentry_enter(regs);
  374  
  375  	die_if_kernel("Kernel ale access", regs);
  376  	force_sig_fault(SIGBUS, BUS_ADRALN, (void __user *)regs->csr_badvaddr);
  377  
  378  	irqentry_exit(regs, state);
  379  }
```

【force_sig_fault的代码（kernel/signal.c）】
```c
 1725  int force_sig_fault(int sig, int code, void __user *addr 	___ARCH_SI_IA64(int imm, unsigned int flags, unsigned long isr))  {
 1726  	return force_sig_fault_to_task(sig, code, addr
 1727  				       ___ARCH_SI_IA64(imm, flags, isr), current);
 1728  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_05

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_bp

【程序给出的理由】noinstr N2: line 457 bug_handler -> instrumentable callee

【调用链】bug_handler（arch/loongarch/kernel/traps.c第389行调用）

【do_bp的代码】
```c
  405  asmlinkage void noinstr do_bp(struct pt_regs *regs)  {
  406  	bool user = user_mode(regs);
  407  	unsigned int opcode, bcode;
  408  	unsigned long era = exception_era(regs);
  409  	irqentry_state_t state = irqentry_enter(regs);
  410  
  411  	local_irq_enable();
  412  	current->thread.trap_nr = read_csr_excode();
  413  	if (__get_inst(&opcode, (u32 *)era, user))
  414  		goto out_sigsegv;
  415  
  416  	bcode = (opcode & 0x7fff);
  417  
  418  	/*
  419  	 * notify the kprobe handlers, if instruction is likely to
  420  	 * pertain to them.
  421  	 */
  422  	switch (bcode) {
  423  	case BRK_KPROBE_BP:
  424  		if (notify_die(DIE_BREAK, "Kprobe", regs, bcode,
  425  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  426  			goto out;
  427  		else
  428  			break;
  429  	case BRK_KPROBE_SSTEPBP:
  430  		if (notify_die(DIE_SSTEPBP, "Kprobe_SingleStep", regs, bcode,
  431  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  432  			goto out;
  433  		else
  434  			break;
  435  	case BRK_UPROBE_BP:
  436  		if (notify_die(DIE_UPROBE, "Uprobe", regs, bcode,
  437  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  438  			goto out;
  439  		else
  440  			break;
  441  	case BRK_UPROBE_XOLBP:
  442  		if (notify_die(DIE_UPROBE_XOL, "Uprobe_XOL", regs, bcode,
  443  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  444  			goto out;
  445  		else
  446  			break;
  447  	default:
  448  		if (notify_die(DIE_TRAP, "Break", regs, bcode,
  449  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  450  			goto out;
  451  		else
  452  			break;
  453  	}
  454  
  455  	switch (bcode) {
  456  	case BRK_BUG:
  457  		bug_handler(regs);
  458  		break;
  459  	case BRK_DIVZERO:
  460  		die_if_kernel("Break instruction in kernel code", regs);
  461  		force_sig_fault(SIGFPE, FPE_INTDIV, (void __user *)regs->csr_era);
  462  		break;
  463  	case BRK_OVERFLOW:
  464  		die_if_kernel("Break instruction in kernel code", regs);
  465  		force_sig_fault(SIGFPE, FPE_INTOVF, (void __user *)regs->csr_era);
  466  		break;
  467  	default:
  468  		die_if_kernel("Break instruction in kernel code", regs);
  469  		force_sig_fault(SIGTRAP, TRAP_BRKPT, (void __user *)regs->csr_era);
  470  		break;
  471  	}
  472  
  473  out:
  474  	local_irq_disable();
  475  	irqentry_exit(regs, state);
  476  	return;
  477  
  478  out_sigsegv:
  479  	force_sig(SIGSEGV);
  480  	goto out;
  481  }
```

【bug_handler的代码（arch/loongarch/kernel/traps.c）】
```c
  389  static void bug_handler(struct pt_regs *regs)  {
  390  	switch (report_bug(regs->csr_era, regs)) {
  391  	case BUG_TRAP_TYPE_BUG:
  392  	case BUG_TRAP_TYPE_NONE:
  393  		die_if_kernel("Oops - BUG", regs);
  394  		force_sig(SIGTRAP);
  395  		break;
  396  
  397  	case BUG_TRAP_TYPE_WARN:
  398  		/* Skip the BUG instruction and continue */
  399  		regs->csr_era += LOONGARCH_INSN_SIZE;
  400  		break;
  401  	}
  402  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_06

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_bp

【程序给出的理由】noinstr N2: line 479 force_sig -> instrumentable callee

【调用链】force_sig（kernel/signal.c第1651行调用）

【do_bp的代码】
```c
  405  asmlinkage void noinstr do_bp(struct pt_regs *regs)  {
  406  	bool user = user_mode(regs);
  407  	unsigned int opcode, bcode;
  408  	unsigned long era = exception_era(regs);
  409  	irqentry_state_t state = irqentry_enter(regs);
  410  
  411  	local_irq_enable();
  412  	current->thread.trap_nr = read_csr_excode();
  413  	if (__get_inst(&opcode, (u32 *)era, user))
  414  		goto out_sigsegv;
  415  
  416  	bcode = (opcode & 0x7fff);
  417  
  418  	/*
  419  	 * notify the kprobe handlers, if instruction is likely to
  420  	 * pertain to them.
  421  	 */
  422  	switch (bcode) {
  423  	case BRK_KPROBE_BP:
  424  		if (notify_die(DIE_BREAK, "Kprobe", regs, bcode,
  425  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  426  			goto out;
  427  		else
  428  			break;
  429  	case BRK_KPROBE_SSTEPBP:
  430  		if (notify_die(DIE_SSTEPBP, "Kprobe_SingleStep", regs, bcode,
  431  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  432  			goto out;
  433  		else
  434  			break;
  435  	case BRK_UPROBE_BP:
  436  		if (notify_die(DIE_UPROBE, "Uprobe", regs, bcode,
  437  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  438  			goto out;
  439  		else
  440  			break;
  441  	case BRK_UPROBE_XOLBP:
  442  		if (notify_die(DIE_UPROBE_XOL, "Uprobe_XOL", regs, bcode,
  443  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  444  			goto out;
  445  		else
  446  			break;
  447  	default:
  448  		if (notify_die(DIE_TRAP, "Break", regs, bcode,
  449  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  450  			goto out;
  451  		else
  452  			break;
  453  	}
  454  
  455  	switch (bcode) {
  456  	case BRK_BUG:
  457  		bug_handler(regs);
  458  		break;
  459  	case BRK_DIVZERO:
  460  		die_if_kernel("Break instruction in kernel code", regs);
  461  		force_sig_fault(SIGFPE, FPE_INTDIV, (void __user *)regs->csr_era);
  462  		break;
  463  	case BRK_OVERFLOW:
  464  		die_if_kernel("Break instruction in kernel code", regs);
  465  		force_sig_fault(SIGFPE, FPE_INTOVF, (void __user *)regs->csr_era);
  466  		break;
  467  	default:
  468  		die_if_kernel("Break instruction in kernel code", regs);
  469  		force_sig_fault(SIGTRAP, TRAP_BRKPT, (void __user *)regs->csr_era);
  470  		break;
  471  	}
  472  
  473  out:
  474  	local_irq_disable();
  475  	irqentry_exit(regs, state);
  476  	return;
  477  
  478  out_sigsegv:
  479  	force_sig(SIGSEGV);
  480  	goto out;
  481  }
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

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_07

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_bp

【程序给出的理由】noinstr N2: line 424 notify_die -> instrumentable callee

【调用链】notify_die（kernel/notifier.c第582行调用）

【do_bp的代码】
```c
  405  asmlinkage void noinstr do_bp(struct pt_regs *regs)  {
  406  	bool user = user_mode(regs);
  407  	unsigned int opcode, bcode;
  408  	unsigned long era = exception_era(regs);
  409  	irqentry_state_t state = irqentry_enter(regs);
  410  
  411  	local_irq_enable();
  412  	current->thread.trap_nr = read_csr_excode();
  413  	if (__get_inst(&opcode, (u32 *)era, user))
  414  		goto out_sigsegv;
  415  
  416  	bcode = (opcode & 0x7fff);
  417  
  418  	/*
  419  	 * notify the kprobe handlers, if instruction is likely to
  420  	 * pertain to them.
  421  	 */
  422  	switch (bcode) {
  423  	case BRK_KPROBE_BP:
  424  		if (notify_die(DIE_BREAK, "Kprobe", regs, bcode,
  425  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  426  			goto out;
  427  		else
  428  			break;
  429  	case BRK_KPROBE_SSTEPBP:
  430  		if (notify_die(DIE_SSTEPBP, "Kprobe_SingleStep", regs, bcode,
  431  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  432  			goto out;
  433  		else
  434  			break;
  435  	case BRK_UPROBE_BP:
  436  		if (notify_die(DIE_UPROBE, "Uprobe", regs, bcode,
  437  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  438  			goto out;
  439  		else
  440  			break;
  441  	case BRK_UPROBE_XOLBP:
  442  		if (notify_die(DIE_UPROBE_XOL, "Uprobe_XOL", regs, bcode,
  443  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  444  			goto out;
  445  		else
  446  			break;
  447  	default:
  448  		if (notify_die(DIE_TRAP, "Break", regs, bcode,
  449  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  450  			goto out;
  451  		else
  452  			break;
  453  	}
  454  
  455  	switch (bcode) {
  456  	case BRK_BUG:
  457  		bug_handler(regs);
  458  		break;
  459  	case BRK_DIVZERO:
  460  		die_if_kernel("Break instruction in kernel code", regs);
  461  		force_sig_fault(SIGFPE, FPE_INTDIV, (void __user *)regs->csr_era);
  462  		break;
  463  	case BRK_OVERFLOW:
  464  		die_if_kernel("Break instruction in kernel code", regs);
  465  		force_sig_fault(SIGFPE, FPE_INTOVF, (void __user *)regs->csr_era);
  466  		break;
  467  	default:
  468  		die_if_kernel("Break instruction in kernel code", regs);
  469  		force_sig_fault(SIGTRAP, TRAP_BRKPT, (void __user *)regs->csr_era);
  470  		break;
  471  	}
  472  
  473  out:
  474  	local_irq_disable();
  475  	irqentry_exit(regs, state);
  476  	return;
  477  
  478  out_sigsegv:
  479  	force_sig(SIGSEGV);
  480  	goto out;
  481  }
```

【notify_die的代码（kernel/notifier.c）】
```c
  582  int notrace notify_die(enum die_val val, const char *str, 	       struct pt_regs *regs, long err, int trap, int sig)  {
  583  	struct die_args args = {
  584  		.regs	= regs,
  585  		.str	= str,
  586  		.err	= err,
  587  		.trapnr	= trap,
  588  		.signr	= sig,
  589  
  590  	};
  591  	RCU_LOCKDEP_WARN(!rcu_is_watching(),
  592  			   "notify_die called but RCU thinks we're quiescent");
  593  	return atomic_notifier_call_chain(&die_chain, val, &args);
  594  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_08

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_bp

【程序给出的理由】noinstr N2: line 461 force_sig_fault -> instrumentable callee

【调用链】force_sig_fault（kernel/signal.c第1725行调用）

【do_bp的代码】
```c
  405  asmlinkage void noinstr do_bp(struct pt_regs *regs)  {
  406  	bool user = user_mode(regs);
  407  	unsigned int opcode, bcode;
  408  	unsigned long era = exception_era(regs);
  409  	irqentry_state_t state = irqentry_enter(regs);
  410  
  411  	local_irq_enable();
  412  	current->thread.trap_nr = read_csr_excode();
  413  	if (__get_inst(&opcode, (u32 *)era, user))
  414  		goto out_sigsegv;
  415  
  416  	bcode = (opcode & 0x7fff);
  417  
  418  	/*
  419  	 * notify the kprobe handlers, if instruction is likely to
  420  	 * pertain to them.
  421  	 */
  422  	switch (bcode) {
  423  	case BRK_KPROBE_BP:
  424  		if (notify_die(DIE_BREAK, "Kprobe", regs, bcode,
  425  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  426  			goto out;
  427  		else
  428  			break;
  429  	case BRK_KPROBE_SSTEPBP:
  430  		if (notify_die(DIE_SSTEPBP, "Kprobe_SingleStep", regs, bcode,
  431  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  432  			goto out;
  433  		else
  434  			break;
  435  	case BRK_UPROBE_BP:
  436  		if (notify_die(DIE_UPROBE, "Uprobe", regs, bcode,
  437  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  438  			goto out;
  439  		else
  440  			break;
  441  	case BRK_UPROBE_XOLBP:
  442  		if (notify_die(DIE_UPROBE_XOL, "Uprobe_XOL", regs, bcode,
  443  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  444  			goto out;
  445  		else
  446  			break;
  447  	default:
  448  		if (notify_die(DIE_TRAP, "Break", regs, bcode,
  449  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  450  			goto out;
  451  		else
  452  			break;
  453  	}
  454  
  455  	switch (bcode) {
  456  	case BRK_BUG:
  457  		bug_handler(regs);
  458  		break;
  459  	case BRK_DIVZERO:
  460  		die_if_kernel("Break instruction in kernel code", regs);
  461  		force_sig_fault(SIGFPE, FPE_INTDIV, (void __user *)regs->csr_era);
  462  		break;
  463  	case BRK_OVERFLOW:
  464  		die_if_kernel("Break instruction in kernel code", regs);
  465  		force_sig_fault(SIGFPE, FPE_INTOVF, (void __user *)regs->csr_era);
  466  		break;
  467  	default:
  468  		die_if_kernel("Break instruction in kernel code", regs);
  469  		force_sig_fault(SIGTRAP, TRAP_BRKPT, (void __user *)regs->csr_era);
  470  		break;
  471  	}
  472  
  473  out:
  474  	local_irq_disable();
  475  	irqentry_exit(regs, state);
  476  	return;
  477  
  478  out_sigsegv:
  479  	force_sig(SIGSEGV);
  480  	goto out;
  481  }
```

【force_sig_fault的代码（kernel/signal.c）】
```c
 1725  int force_sig_fault(int sig, int code, void __user *addr 	___ARCH_SI_IA64(int imm, unsigned int flags, unsigned long isr))  {
 1726  	return force_sig_fault_to_task(sig, code, addr
 1727  				       ___ARCH_SI_IA64(imm, flags, isr), current);
 1728  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_09

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_bp

【程序给出的理由】rt A:irq: line 479 force_sig -> spin_lock_irqsave

【调用链】force_sig（kernel/signal.c第1660行调用force_sig_info） → force_sig_info（kernel/signal.c第1357行调用force_sig_info_to_task） → force_sig_info_to_task（kernel/signal.c第1329行调用spin_lock_irqsave）

【do_bp的代码】
```c
  405  asmlinkage void noinstr do_bp(struct pt_regs *regs)  {
  406  	bool user = user_mode(regs);
  407  	unsigned int opcode, bcode;
  408  	unsigned long era = exception_era(regs);
  409  	irqentry_state_t state = irqentry_enter(regs);
  410  
  411  	local_irq_enable();
  412  	current->thread.trap_nr = read_csr_excode();
  413  	if (__get_inst(&opcode, (u32 *)era, user))
  414  		goto out_sigsegv;
  415  
  416  	bcode = (opcode & 0x7fff);
  417  
  418  	/*
  419  	 * notify the kprobe handlers, if instruction is likely to
  420  	 * pertain to them.
  421  	 */
  422  	switch (bcode) {
  423  	case BRK_KPROBE_BP:
  424  		if (notify_die(DIE_BREAK, "Kprobe", regs, bcode,
  425  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  426  			goto out;
  427  		else
  428  			break;
  429  	case BRK_KPROBE_SSTEPBP:
  430  		if (notify_die(DIE_SSTEPBP, "Kprobe_SingleStep", regs, bcode,
  431  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  432  			goto out;
  433  		else
  434  			break;
  435  	case BRK_UPROBE_BP:
  436  		if (notify_die(DIE_UPROBE, "Uprobe", regs, bcode,
  437  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  438  			goto out;
  439  		else
  440  			break;
  441  	case BRK_UPROBE_XOLBP:
  442  		if (notify_die(DIE_UPROBE_XOL, "Uprobe_XOL", regs, bcode,
  443  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  444  			goto out;
  445  		else
  446  			break;
  447  	default:
  448  		if (notify_die(DIE_TRAP, "Break", regs, bcode,
  449  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  450  			goto out;
  451  		else
  452  			break;
  453  	}
  454  
  455  	switch (bcode) {
  456  	case BRK_BUG:
  457  		bug_handler(regs);
  458  		break;
  459  	case BRK_DIVZERO:
  460  		die_if_kernel("Break instruction in kernel code", regs);
  461  		force_sig_fault(SIGFPE, FPE_INTDIV, (void __user *)regs->csr_era);
  462  		break;
  463  	case BRK_OVERFLOW:
  464  		die_if_kernel("Break instruction in kernel code", regs);
  465  		force_sig_fault(SIGFPE, FPE_INTOVF, (void __user *)regs->csr_era);
  466  		break;
  467  	default:
  468  		die_if_kernel("Break instruction in kernel code", regs);
  469  		force_sig_fault(SIGTRAP, TRAP_BRKPT, (void __user *)regs->csr_era);
  470  		break;
  471  	}
  472  
  473  out:
  474  	local_irq_disable();
  475  	irqentry_exit(regs, state);
  476  	return;
  477  
  478  out_sigsegv:
  479  	force_sig(SIGSEGV);
  480  	goto out;
  481  }
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

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_10

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_fpe

【程序给出的理由】noinstr N2: line 354 process_fpemu_return -> instrumentable callee

【调用链】process_fpemu_return（arch/loongarch/kernel/traps.c第300行调用）

【do_fpe的代码】
```c
  335  asmlinkage void noinstr do_fpe(struct pt_regs *regs, unsigned long fcsr)  {
  336  	int sig;
  337  	void __user *fault_addr;
  338  	irqentry_state_t state = irqentry_enter(regs);
  339  
  340  	if (notify_die(DIE_FP, "FP exception", regs, 0, current->thread.trap_nr,
  341  		       SIGFPE) == NOTIFY_STOP)
  342  		goto out;
  343  
  344  	/* Clear FCSR.Cause before enabling interrupts */
  345  	write_fcsr(LOONGARCH_FCSR0, fcsr & ~mask_fcsr_x(fcsr));
  346  	local_irq_enable();
  347  
  348  	die_if_kernel("FP exception in kernel code", regs);
  349  
  350  	sig = SIGFPE;
  351  	fault_addr = (void __user *) regs->csr_era;
  352  
  353  	/* Send a signal if required.  */
  354  	process_fpemu_return(sig, fault_addr, fcsr);
  355  
  356  out:
  357  	local_irq_disable();
  358  	irqentry_exit(regs, state);
  359  }
```

【process_fpemu_return的代码（arch/loongarch/kernel/traps.c）】
```c
  300  int process_fpemu_return(int sig, void __user *fault_addr, unsigned long fcsr)  {
  301  	int si_code;
  302  
  303  	switch (sig) {
  304  	case 0:
  305  		return 0;
  306  
  307  	case SIGFPE:
  308  		force_fcsr_sig(fcsr, fault_addr, current);
  309  		return 1;
  310  
  311  	case SIGBUS:
  312  		force_sig_fault(SIGBUS, BUS_ADRERR, fault_addr);
  313  		return 1;
  314  
  315  	case SIGSEGV:
  316  		mmap_read_lock(current->mm);
  317  		if (vma_lookup(current->mm, (unsigned long)fault_addr))
  318  			si_code = SEGV_ACCERR;
  319  		else
  320  			si_code = SEGV_MAPERR;
  321  		mmap_read_unlock(current->mm);
  322  		force_sig_fault(SIGSEGV, si_code, fault_addr);
  323  		return 1;
  324  
  325  	default:
  326  		force_sig(sig);
  327  		return 1;
  328  	}
  329  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_11

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_fpe

【程序给出的理由】noinstr N2: line 340 notify_die -> instrumentable callee

【调用链】notify_die（kernel/notifier.c第582行调用）

【do_fpe的代码】
```c
  335  asmlinkage void noinstr do_fpe(struct pt_regs *regs, unsigned long fcsr)  {
  336  	int sig;
  337  	void __user *fault_addr;
  338  	irqentry_state_t state = irqentry_enter(regs);
  339  
  340  	if (notify_die(DIE_FP, "FP exception", regs, 0, current->thread.trap_nr,
  341  		       SIGFPE) == NOTIFY_STOP)
  342  		goto out;
  343  
  344  	/* Clear FCSR.Cause before enabling interrupts */
  345  	write_fcsr(LOONGARCH_FCSR0, fcsr & ~mask_fcsr_x(fcsr));
  346  	local_irq_enable();
  347  
  348  	die_if_kernel("FP exception in kernel code", regs);
  349  
  350  	sig = SIGFPE;
  351  	fault_addr = (void __user *) regs->csr_era;
  352  
  353  	/* Send a signal if required.  */
  354  	process_fpemu_return(sig, fault_addr, fcsr);
  355  
  356  out:
  357  	local_irq_disable();
  358  	irqentry_exit(regs, state);
  359  }
```

【notify_die的代码（kernel/notifier.c）】
```c
  582  int notrace notify_die(enum die_val val, const char *str, 	       struct pt_regs *regs, long err, int trap, int sig)  {
  583  	struct die_args args = {
  584  		.regs	= regs,
  585  		.str	= str,
  586  		.err	= err,
  587  		.trapnr	= trap,
  588  		.signr	= sig,
  589  
  590  	};
  591  	RCU_LOCKDEP_WARN(!rcu_is_watching(),
  592  			   "notify_die called but RCU thinks we're quiescent");
  593  	return atomic_notifier_call_chain(&die_chain, val, &args);
  594  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_12

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_fpu

【程序给出的理由】noinstr N2: line 538 init_restore_fp -> instrumentable callee

【调用链】init_restore_fp（arch/loongarch/kernel/traps.c第517行调用）

【do_fpu的代码】
```c
  531  asmlinkage void noinstr do_fpu(struct pt_regs *regs)  {
  532  	irqentry_state_t state = irqentry_enter(regs);
  533  
  534  	local_irq_enable();
  535  	die_if_kernel("do_fpu invoked from kernel context!", regs);
  536  
  537  	preempt_disable();
  538  	init_restore_fp();
  539  	preempt_enable();
  540  
  541  	local_irq_disable();
  542  	irqentry_exit(regs, state);
  543  }
```

【init_restore_fp的代码（arch/loongarch/kernel/traps.c）】
```c
  517  static void init_restore_fp(void)  {
  518  	if (!used_math()) {
  519  		/* First time FP context user. */
  520  		init_fpu();
  521  	} else {
  522  		/* This task has formerly used the FP context */
  523  		if (!is_fpu_owner())
  524  			own_fpu_inatomic(1);
  525  	}
  526  
  527  	BUG_ON(!is_fp_enabled());
  528  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_13

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_lasx

【程序给出的理由】noinstr N2: line 561 force_sig -> instrumentable callee

【调用链】force_sig（kernel/signal.c第1651行调用）

【do_lasx的代码】
```c
  557  asmlinkage void noinstr do_lasx(struct pt_regs *regs)  {
  558  	irqentry_state_t state = irqentry_enter(regs);
  559  
  560  	local_irq_enable();
  561  	force_sig(SIGILL);
  562  	local_irq_disable();
  563  
  564  	irqentry_exit(regs, state);
  565  }
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

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_14

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_lsx

【程序给出的理由】noinstr N2: line 550 force_sig -> instrumentable callee

【调用链】force_sig（kernel/signal.c第1651行调用）

【do_lsx的代码】
```c
  546  asmlinkage void noinstr do_lsx(struct pt_regs *regs)  {
  547  	irqentry_state_t state = irqentry_enter(regs);
  548  
  549  	local_irq_enable();
  550  	force_sig(SIGILL);
  551  	local_irq_disable();
  552  
  553  	irqentry_exit(regs, state);
  554  }
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

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_15

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/mm/fault.c中的do_page_fault

【程序给出的理由】sleep B:trap: line 260 __do_page_fault -> down_read

【调用链】__do_page_fault（arch/loongarch/mm/fault.c第169行调用mmap_read_lock） → mmap_read_lock（include/linux/mmap_lock.h第117行调用down_read）

【do_page_fault的代码】
```c
  253  asmlinkage void __kprobes do_page_fault(struct pt_regs *regs, 			unsigned long write, unsigned long address)  {
  254  	irqentry_state_t state = irqentry_enter(regs);
  255  
  256  	/* Enable interrupt if enabled in parent context */
  257  	if (likely(regs->csr_prmd & CSR_PRMD_PIE))
  258  		local_irq_enable();
  259  
  260  	__do_page_fault(regs, write, address);
  261  
  262  	local_irq_disable();
  263  
  264  	irqentry_exit(regs, state);
  265  }
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
  138  	/*
  139  	 * We fault-in kernel-space virtual memory on-demand. The
  140  	 * 'reference' page table is init_mm.pgd.
  141  	 *
  142  	 * NOTE! We MUST NOT take any locks for this case. We may
  143  	 * be in an interrupt or a critical region, and should
  144  	 * only copy the information from the master page table,
  145  	 * nothing more.
  146  	 */
  147  	if (address & __UA_LIMIT) {
  148  		if (!user_mode(regs))
  149  			no_context(regs, address);
  150  		else
  151  			do_sigsegv(regs, write, address, si_code);
  152  		return;
  153  	}
  154  
  155  	/*
  156  	 * If we're in an interrupt or have no user
  157  	 * context, we must not take the fault..
  158  	 */
  159  	if (faulthandler_disabled() || !mm) {
  160  		do_sigsegv(regs, write, address, si_code);
  161  		return;
  162  	}
  163  
  164  	if (user_mode(regs))
  165  		flags |= FAULT_FLAG_USER;
  166  
  167  	perf_sw_event(PERF_COUNT_SW_PAGE_FAULTS, 1, regs, address);
  168  retry:
  169  	mmap_read_lock(mm);
  170  	vma = find_vma(mm, address);
  171  	if (!vma)
  172  		goto bad_area;
  173  	if (vma->vm_start <= address)
  174  		goto good_area;
  175  	if (!(vma->vm_flags & VM_GROWSDOWN))
  176  		goto bad_area;
  177  	if (!expand_stack(vma, address))
  178  		goto good_area;
  179  /*
  180   * Something tried to access memory that isn't in our memory map..
  181   * Fix it, but check if it's kernel or user first..
  182   */
  183  bad_area:
  184  	mmap_read_unlock(mm);
  185  	do_sigsegv(regs, write, address, si_code);
  186  	return;
  187  
  188  /*
  189   * Ok, we have a good vm_area for this memory access, so
  190   * we can handle it..
  191   */
  192  good_area:
  193  	si_code = SEGV_ACCERR;
  194  
  195  	if (write) {
  196  		flags |= FAULT_FLAG_WRITE;
  197  		if (!(vma->vm_flags & VM_WRITE))
  198  			goto bad_area;
  199  	} else {
  200  		if (!(vma->vm_flags & VM_READ) && address != exception_era(regs))
  201  			goto bad_area;
  202  		if (!(vma->vm_flags & VM_EXEC) && address == exception_era(regs))
  203  			goto bad_area;
  204  	}
  205  
  206  	/*
  207  	 * If for any reason at all we couldn't handle the fault,
  208  	 * make sure we exit gracefully rather than endlessly redo
  209  	 * the fault.
...（其余40行省略）
```

【mmap_read_lock的代码（include/linux/mmap_lock.h）】
```c
  115  static inline void mmap_read_lock(struct mm_struct *mm)  {
  116  	__mmap_lock_trace_start_locking(mm, false);
  117  	down_read(&mm->mmap_lock);
  118  	__mmap_lock_trace_acquire_returned(mm, false, true);
  119  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_16

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_reserved

【程序给出的理由】noinstr N2: line 590 force_sig -> instrumentable callee

【调用链】force_sig（kernel/signal.c第1651行调用）

【do_reserved的代码】
```c
  579  asmlinkage void noinstr do_reserved(struct pt_regs *regs)  {
  580  	irqentry_state_t state = irqentry_enter(regs);
  581  
  582  	local_irq_enable();
  583  	/*
  584  	 * Game over - no way to handle this if it ever occurs.	Most probably
  585  	 * caused by a fatal error after another hardware/software error.
  586  	 */
  587  	pr_err("Caught reserved exception %u on pid:%d [%s] - should not happen\n",
  588  		read_csr_excode(), current->pid, current->comm);
  589  	die_if_kernel("do_reserved exception", regs);
  590  	force_sig(SIGUNUSED);
  591  
  592  	local_irq_disable();
  593  
  594  	irqentry_exit(regs, state);
  595  }
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

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_17

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_ri

【程序给出的理由】noinstr N2: line 509 force_sig -> instrumentable callee

【调用链】force_sig（kernel/signal.c第1651行调用）

【do_ri的代码】
```c
  489  asmlinkage void noinstr do_ri(struct pt_regs *regs)  {
  490  	int status = SIGILL;
  491  	unsigned int opcode = 0;
  492  	unsigned int __user *era = (unsigned int __user *)exception_era(regs);
  493  	irqentry_state_t state = irqentry_enter(regs);
  494  
  495  	local_irq_enable();
  496  	current->thread.trap_nr = read_csr_excode();
  497  
  498  	if (notify_die(DIE_RI, "RI Fault", regs, 0, current->thread.trap_nr,
  499  		       SIGILL) == NOTIFY_STOP)
  500  		goto out;
  501  
  502  	die_if_kernel("Reserved instruction in kernel code", regs);
  503  
  504  	if (unlikely(get_user(opcode, era) < 0)) {
  505  		status = SIGSEGV;
  506  		current->thread.error_code = 1;
  507  	}
  508  
  509  	force_sig(status);
  510  
  511  out:
  512  	local_irq_disable();
  513  	irqentry_exit(regs, state);
  514  }
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

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_18

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_ri

【程序给出的理由】noinstr N2: line 498 notify_die -> instrumentable callee

【调用链】notify_die（kernel/notifier.c第582行调用）

【do_ri的代码】
```c
  489  asmlinkage void noinstr do_ri(struct pt_regs *regs)  {
  490  	int status = SIGILL;
  491  	unsigned int opcode = 0;
  492  	unsigned int __user *era = (unsigned int __user *)exception_era(regs);
  493  	irqentry_state_t state = irqentry_enter(regs);
  494  
  495  	local_irq_enable();
  496  	current->thread.trap_nr = read_csr_excode();
  497  
  498  	if (notify_die(DIE_RI, "RI Fault", regs, 0, current->thread.trap_nr,
  499  		       SIGILL) == NOTIFY_STOP)
  500  		goto out;
  501  
  502  	die_if_kernel("Reserved instruction in kernel code", regs);
  503  
  504  	if (unlikely(get_user(opcode, era) < 0)) {
  505  		status = SIGSEGV;
  506  		current->thread.error_code = 1;
  507  	}
  508  
  509  	force_sig(status);
  510  
  511  out:
  512  	local_irq_disable();
  513  	irqentry_exit(regs, state);
  514  }
```

【notify_die的代码（kernel/notifier.c）】
```c
  582  int notrace notify_die(enum die_val val, const char *str, 	       struct pt_regs *regs, long err, int trap, int sig)  {
  583  	struct die_args args = {
  584  		.regs	= regs,
  585  		.str	= str,
  586  		.err	= err,
  587  		.trapnr	= trap,
  588  		.signr	= sig,
  589  
  590  	};
  591  	RCU_LOCKDEP_WARN(!rcu_is_watching(),
  592  			   "notify_die called but RCU thinks we're quiescent");
  593  	return atomic_notifier_call_chain(&die_chain, val, &args);
  594  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_19

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的handle_loongarch_irq

【程序给出的理由】noinstr N2: line 614 irq_exit_rcu -> instrumentable callee

【调用链】irq_exit_rcu（kernel/softirq.c第661行调用）

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

【irq_exit_rcu的代码（kernel/softirq.c）】
```c
  661  void irq_exit_rcu(void)  {
  662  	__irq_exit_rcu();
  663  	 /* must be last! */
  664  	lockdep_hardirq_exit();
  665  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_20

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/machine_kexec.c中的machine_crash_shutdown

【程序给出的理由】sleep A:irq: line 250 crash_smp_send_stop -> smp_call_function

【调用链】crash_smp_send_stop（arch/loongarch/kernel/machine_kexec.c第210行调用smp_call_function）

【machine_crash_shutdown的代码】
```c
  241  void machine_crash_shutdown(struct pt_regs *regs)  {
  242  	int crashing_cpu;
  243  
  244  	local_irq_disable();
  245  
  246  	crashing_cpu = smp_processor_id();
  247  	crash_save_cpu(regs, crashing_cpu);
  248  
  249  #ifdef CONFIG_SMP
  250  	crash_smp_send_stop();
  251  #endif
  252  	cpumask_set_cpu(crashing_cpu, &cpus_in_crash);
  253  
  254  	pr_info("Starting crashdump kernel...\n");
  255  }
```

【crash_smp_send_stop的代码（arch/loongarch/kernel/machine_kexec.c）】
```c
  193  void crash_smp_send_stop(void)  {
  194  	unsigned int ncpus;
  195  	unsigned long timeout;
  196  	static int cpus_stopped;
  197  
  198  	/*
  199  	 * This function can be called twice in panic path, but obviously
  200  	 * we should execute this only once.
  201  	 */
  202  	if (cpus_stopped)
  203  		return;
  204  
  205  	cpus_stopped = 1;
  206  
  207  	 /* Excluding the panic cpu */
  208  	ncpus = num_online_cpus() - 1;
  209  
  210  	smp_call_function(crash_shutdown_secondary, NULL, 0);
  211  	smp_wmb();
  212  
  213  	/*
  214  	 * The crash CPU sends an IPI and wait for other CPUs to
  215  	 * respond. Delay of at least 10 seconds.
  216  	 */
  217  	timeout = MSEC_PER_SEC * 10;
  218  	pr_emerg("Sending IPI to other cpus...\n");
  219  	while ((cpumask_weight(&cpus_in_crash) < ncpus) && timeout--) {
  220  		mdelay(1);
  221  		cpu_relax();
  222  	}
  223  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_21

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/reset.c中的machine_halt

【程序给出的理由】sleep A:irq: line 32 console_flush_on_panic -> cond_resched

【调用链】console_flush_on_panic（kernel/printk/printk.c第2950行调用console_unlock） → console_unlock（kernel/printk/printk.c第2860行调用console_flush_all） → console_flush_all（kernel/printk/printk.c第2813行调用cond_resched）

【machine_halt的代码】
```c
   23  void machine_halt(void)  {
   24  #ifdef CONFIG_SMP
   25  	preempt_disable();
   26  	smp_send_stop();
   27  #endif
   28  	local_irq_disable();
   29  	clear_csr_ecfg(ECFG0_IM);
   30  
   31  	pr_notice("\n\n** You can safely turn off the power now **\n\n");
   32  	console_flush_on_panic(CONSOLE_FLUSH_PENDING);
   33  
   34  	while (true) {
   35  		__arch_cpu_idle();
   36  	}
   37  }
```

【console_flush_on_panic的代码（kernel/printk/printk.c）】
```c
 2931  void console_flush_on_panic(enum con_flush_mode mode)  {
 2932  	/*
 2933  	 * If someone else is holding the console lock, trylock will fail
 2934  	 * and may_schedule may be set.  Ignore and proceed to unlock so
 2935  	 * that messages are flushed out.  As this can be called from any
 2936  	 * context and we don't want to get preempted while flushing,
 2937  	 * ensure may_schedule is cleared.
 2938  	 */
 2939  	console_trylock();
 2940  	console_may_schedule = 0;
 2941  
 2942  	if (mode == CONSOLE_REPLAY_ALL) {
 2943  		struct console *c;
 2944  		u64 seq;
 2945  
 2946  		seq = prb_first_valid_seq(prb);
 2947  		for_each_console(c)
 2948  			c->seq = seq;
 2949  	}
 2950  	console_unlock();
 2951  }
```

【console_unlock的代码（kernel/printk/printk.c）】
```c
 2833  void console_unlock(void)  {
 2834  	bool do_cond_resched;
 2835  	bool handover;
 2836  	bool flushed;
 2837  	u64 next_seq;
 2838  
 2839  	if (console_suspended) {
 2840  		up_console_sem();
 2841  		return;
 2842  	}
 2843  
 2844  	/*
 2845  	 * Console drivers are called with interrupts disabled, so
 2846  	 * @console_may_schedule should be cleared before; however, we may
 2847  	 * end up dumping a lot of lines, for example, if called from
 2848  	 * console registration path, and should invoke cond_resched()
 2849  	 * between lines if allowable.  Not doing so can cause a very long
 2850  	 * scheduling stall on a slow console leading to RCU stall and
 2851  	 * softlockup warnings which exacerbate the issue with more
 2852  	 * messages practically incapacitating the system. Therefore, create
 2853  	 * a local to use for the printing loop.
 2854  	 */
 2855  	do_cond_resched = console_may_schedule;
 2856  
 2857  	do {
 2858  		console_may_schedule = 0;
 2859  
 2860  		flushed = console_flush_all(do_cond_resched, &next_seq, &handover);
 2861  		if (!handover)
 2862  			__console_unlock();
 2863  
 2864  		/*
 2865  		 * Abort if there was a failure to flush all messages to all
 2866  		 * usable consoles. Either it is not possible to flush (in
 2867  		 * which case it would be an infinite loop of retrying) or
 2868  		 * another context has taken over printing.
 2869  		 */
 2870  		if (!flushed)
 2871  			break;
 2872  
 2873  		/*
 2874  		 * Some context may have added new records after
 2875  		 * console_flush_all() but before unlocking the console.
 2876  		 * Re-check if there is a new record to flush. If the trylock
 2877  		 * fails, another context is already handling the printing.
 2878  		 */
 2879  	} while (prb_read_valid(prb, next_seq, NULL) && console_trylock());
 2880  }
```

【console_flush_all的代码（kernel/printk/printk.c）】
```c
 2766  static bool console_flush_all(bool do_cond_resched, u64 *next_seq, bool *handover)  {
 2767  	static char dropped_text[DROPPED_TEXT_MAX];
 2768  	static char ext_text[CONSOLE_EXT_LOG_MAX];
 2769  	static char text[CONSOLE_LOG_MAX];
 2770  	bool any_usable = false;
 2771  	struct console *con;
 2772  	bool any_progress;
 2773  
 2774  	*next_seq = 0;
 2775  	*handover = false;
 2776  
 2777  	do {
 2778  		any_progress = false;
 2779  
 2780  		for_each_console(con) {
 2781  			bool progress;
 2782  
 2783  			if (!console_is_usable(con))
 2784  				continue;
 2785  			any_usable = true;
 2786  
 2787  			if (con->flags & CON_EXTENDED) {
 2788  				/* Extended consoles do not print "dropped messages". */
 2789  				progress = console_emit_next_record(con, &text[0],
 2790  								    &ext_text[0], NULL,
 2791  								    handover);
 2792  			} else {
 2793  				progress = console_emit_next_record(con, &text[0],
 2794  								    NULL, &dropped_text[0],
 2795  								    handover);
 2796  			}
 2797  			if (*handover)
 2798  				return false;
 2799  
 2800  			/* Track the next of the highest seq flushed. */
 2801  			if (con->seq > *next_seq)
 2802  				*next_seq = con->seq;
 2803  
 2804  			if (!progress)
 2805  				continue;
 2806  			any_progress = true;
 2807  
 2808  			/* Allow panic_cpu to take over the consoles safely. */
 2809  			if (abandon_console_lock_in_panic())
 2810  				return false;
 2811  
 2812  			if (do_cond_resched)
 2813  				cond_resched();
 2814  		}
 2815  	} while (any_progress);
 2816  
 2817  	return any_usable;
 2818  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_22

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/reset.c中的machine_power_off

【程序给出的理由】sleep A:preempt: line 45 do_kernel_power_off -> down_write

【调用链】do_kernel_power_off（kernel/reboot.c第657行调用unregister_sys_off_handler） → unregister_sys_off_handler（kernel/reboot.c第470行调用blocking_notifier_chain_unregister） → blocking_notifier_chain_unregister（kernel/notifier.c第328行调用down_write）

【machine_power_off的代码】
```c
   40  void machine_power_off(void)  {
   41  #ifdef CONFIG_SMP
   42  	preempt_disable();
   43  	smp_send_stop();
   44  #endif
   45  	do_kernel_power_off();
   46  #ifdef CONFIG_EFI
   47  	efi.reset_system(EFI_RESET_SHUTDOWN, EFI_SUCCESS, 0, NULL);
   48  #endif
   49  
   50  	while (true) {
   51  		__arch_cpu_idle();
   52  	}
   53  }
```

【do_kernel_power_off的代码（kernel/reboot.c）】
```c
  640  void do_kernel_power_off(void)  {
  641  	struct sys_off_handler *sys_off = NULL;
  642  
  643  	/*
  644  	 * Register sys-off handlers for legacy PM callback. This allows
  645  	 * legacy PM callbacks temporary co-exist with the new sys-off API.
  646  	 *
  647  	 * TODO: Remove legacy handlers once all legacy PM users will be
  648  	 *       switched to the sys-off based APIs.
  649  	 */
  650  	if (pm_power_off)
  651  		sys_off = register_sys_off_handler(SYS_OFF_MODE_POWER_OFF,
  652  						   SYS_OFF_PRIO_DEFAULT,
  653  						   legacy_pm_power_off, NULL);
  654  
  655  	atomic_notifier_call_chain(&power_off_handler_list, 0, NULL);
  656  
  657  	unregister_sys_off_handler(sys_off);
  658  }
```

【unregister_sys_off_handler的代码（kernel/reboot.c）】
```c
  463  void unregister_sys_off_handler(struct sys_off_handler *handler)  {
  464  	int err;
  465  
  466  	if (IS_ERR_OR_NULL(handler))
  467  		return;
  468  
  469  	if (handler->blocking)
  470  		err = blocking_notifier_chain_unregister(handler->list,
  471  							 &handler->nb);
  472  	else
  473  		err = atomic_notifier_chain_unregister(handler->list,
  474  						       &handler->nb);
  475  
  476  	/* sanity check, shall never happen */
  477  	WARN_ON(err);
  478  
  479  	free_sys_off_handler(handler);
  480  }
```

【blocking_notifier_chain_unregister的代码（kernel/notifier.c）】
```c
  317  int blocking_notifier_chain_unregister(struct blocking_notifier_head *nh, 		struct notifier_block *n)  {
  318  	int ret;
  319  
  320  	/*
  321  	 * This code gets used during boot-up, when task switching is
  322  	 * not yet working and interrupts must remain disabled.  At
  323  	 * such times we must not call down_write().
  324  	 */
  325  	if (unlikely(system_state == SYSTEM_BOOTING))
  326  		return notifier_chain_unregister(&nh->head, n);
  327  
  328  	down_write(&nh->rwsem);
  329  	ret = notifier_chain_unregister(&nh->head, n);
  330  	up_write(&nh->rwsem);
  331  	return ret;
  332  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_23

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/include/asm/entry-common.h中的on_thread_stack

【程序给出的理由】noinstr N1: line 9 on_thread_stack -> called from noinstr/__cpuidle

【on_thread_stack的代码】
```c
    9  static inline bool on_thread_stack(void)  {
   10  	return !(((unsigned long)(current->stack) ^ current_stack_pointer) & ~(THREAD_SIZE - 1));
   11  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_24

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/include/asm/ptrace.h中的regs_irqs_disabled

【程序给出的理由】noinstr N1: line 36 regs_irqs_disabled -> called from noinstr/__cpuidle

【regs_irqs_disabled的代码】
```c
   36  static inline int regs_irqs_disabled(struct pt_regs *regs)  {
   37  	return arch_irqs_disabled_flags(regs->csr_prmd);
   38  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_25

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】同一约定规则：公共代码调用、各架构各自实现的函数中，arm64、x86、RISC-V三个实现都调用了某个函数，LoongArch的实现没有。

【被标记的位置】arch/loongarch/mm/extable.c中的fixup_exception

【程序给出的理由】all three references call ['BUG'], loongarch does not

【fixup_exception的代码】
```c
   11  int fixup_exception(struct pt_regs *regs)  {
   12  	const struct exception_table_entry *fixup;
   13  
   14  	fixup = search_exception_tables(exception_era(regs));
   15  	if (fixup) {
   16  		regs->csr_era = fixup->fixup;
   17  
   18  		return 1;
   19  	}
   20  
   21  	return 0;
   22  }
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

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_26

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】同一约定规则：公共代码调用、各架构各自实现的函数中，arm64、x86、RISC-V三个实现都调用了某个函数，LoongArch的实现没有。

【被标记的位置】arch/loongarch/include/asm/pgtable.h中的pmdp_huge_get_and_clear

【程序给出的理由】all three references call ['page_table_check_pmd_clear'], loongarch does not

【pmdp_huge_get_and_clear的代码】
```c
  540  static inline pmd_t pmdp_huge_get_and_clear(struct mm_struct *mm, 					    unsigned long address, pmd_t *pmdp)  {
  541  	pmd_t old = *pmdp;
  542  
  543  	pmd_clear(pmdp);
  544  
  545  	return old;
  546  }
```

【参照：arm64的pmdp_huge_get_and_clear（arch/arm64/include/asm/pgtable.h）】
```c
  947  static inline pmd_t pmdp_huge_get_and_clear(struct mm_struct *mm, 					    unsigned long address, pmd_t *pmdp)  {
  948  	pmd_t pmd = __pmd(xchg_relaxed(&pmd_val(*pmdp), 0));
  949  
  950  	page_table_check_pmd_clear(mm, address, pmd);
  951  
  952  	return pmd;
  953  }
```

【参照：x86的pmdp_huge_get_and_clear（arch/x86/include/asm/pgtable.h）】
```c
 1116  static inline pmd_t pmdp_huge_get_and_clear(struct mm_struct *mm, unsigned long addr, 				       pmd_t *pmdp)  {
 1117  	pmd_t pmd = native_pmdp_get_and_clear(pmdp);
 1118  
 1119  	page_table_check_pmd_clear(mm, addr, pmd);
 1120  
 1121  	return pmd;
 1122  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_27

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.1）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】同一约定规则：公共代码调用、各架构各自实现的函数中，arm64、x86、RISC-V三个实现都调用了某个函数，LoongArch的实现没有。

【被标记的位置】arch/loongarch/kernel/setup.c中的setup_arch

【程序给出的理由】all three references call ['jump_label_init', 'setup_initial_init_mm'], loongarch does not

【setup_arch的代码】
```c
  416  void __init setup_arch(char **cmdline_p)  {
  417  	cpu_probe();
  418  	*cmdline_p = boot_command_line;
  419  
  420  	init_environ();
  421  	efi_init();
  422  	memblock_init();
  423  	pagetable_init();
  424  	parse_early_param();
  425  	reserve_initrd_mem();
  426  
  427  	platform_init();
  428  	arch_mem_init(cmdline_p);
  429  
  430  	resource_init();
  431  #ifdef CONFIG_SMP
  432  	plat_smp_setup();
  433  	prefill_possible_map();
  434  #endif
  435  
  436  	paging_init();
  437  }
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

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_28

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.2）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_ale

【程序给出的理由】sleep B:trap: line 389 show_registers -> get_user

【调用链】show_registers（arch/loongarch/kernel/traps.c第218行调用show_stacktrace） → show_stacktrace（arch/loongarch/kernel/traps.c第104行调用__get_addr） → __get_addr（arch/loongarch/kernel/access-helper.h第12行调用get_user）

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

【show_stacktrace的代码（arch/loongarch/kernel/traps.c）】
```c
   86  static void show_stacktrace(struct task_struct *task, 	const struct pt_regs *regs, const char *loglvl, bool user)  {
   87  	int i;
   88  	const int field = 2 * sizeof(unsigned long);
   89  	unsigned long stackdata;
   90  	unsigned long *sp = (unsigned long *)regs->regs[3];
   91  
   92  	printk("%sStack :", loglvl);
   93  	i = 0;
   94  	while ((unsigned long) sp & (PAGE_SIZE - 1)) {
   95  		if (i && ((i % (64 / field)) == 0)) {
   96  			pr_cont("\n");
   97  			printk("%s       ", loglvl);
   98  		}
   99  		if (i > 39) {
  100  			pr_cont(" ...");
  101  			break;
  102  		}
  103  
  104  		if (__get_addr(&stackdata, sp++, user)) {
  105  			pr_cont(" (Bad stack address)");
  106  			break;
  107  		}
  108  
  109  		pr_cont(" %0*lx", field, stackdata);
  110  		i++;
  111  	}
  112  	pr_cont("\n");
  113  	show_backtrace(task, regs, loglvl, user);
  114  }
```

【__get_addr的代码（arch/loongarch/kernel/access-helper.h）】
```c
   11  static inline int __get_addr(unsigned long *a, unsigned long *p, bool user)  {
   12  	return user ? get_user(*a, (unsigned long __user *)p) : get_kernel_nofault(*a, p);
   13  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_29

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.2）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_ale

【程序给出的理由】noinstr N2: line 393 emulate_load_store_insn -> instrumentable callee

【调用链】emulate_load_store_insn（arch/loongarch/kernel/unaligned.c第250行调用）

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

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_30

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.3）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_bp

【程序给出的理由】noinstr N2: line 455 kprobe_breakpoint_handler -> instrumentable callee

【调用链】kprobe_breakpoint_handler（arch/loongarch/kernel/kprobes.c第255行调用）

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

【kprobe_breakpoint_handler的代码（arch/loongarch/kernel/kprobes.c）】
```c
  255  bool kprobe_breakpoint_handler(struct pt_regs *regs)  {
  256  	struct kprobe_ctlblk *kcb;
  257  	struct kprobe *p, *cur_kprobe;
  258  	kprobe_opcode_t *addr = (kprobe_opcode_t *)regs->csr_era;
  259  
  260  	/*
  261  	 * We don't want to be preempted for the entire
  262  	 * duration of kprobe processing.
  263  	 */
  264  	preempt_disable();
  265  	kcb = get_kprobe_ctlblk();
  266  	cur_kprobe = kprobe_running();
  267  
  268  	p = get_kprobe(addr);
  269  	if (p) {
  270  		if (cur_kprobe) {
  271  			if (reenter_kprobe(p, regs, kcb))
  272  				return true;
  273  		} else {
  274  			/* Probe hit */
  275  			set_current_kprobe(p);
  276  			kcb->kprobe_status = KPROBE_HIT_ACTIVE;
  277  
  278  			/*
  279  			 * If we have no pre-handler or it returned 0, we
  280  			 * continue with normal processing.  If we have a
  281  			 * pre-handler and it returned non-zero, it will
  282  			 * modify the execution path and no need to single
  283  			 * stepping. Let's just reset current kprobe and exit.
  284  			 *
  285  			 * pre_handler can hit a breakpoint and can step thru
  286  			 * before return.
  287  			 */
  288  			if (!p->pre_handler || !p->pre_handler(p, regs)) {
  289  				setup_singlestep(p, regs, kcb, 0);
  290  			} else {
  291  				reset_current_kprobe();
  292  				preempt_enable_no_resched();
  293  			}
  294  			return true;
  295  		}
  296  	}
  297  
  298  	if (addr->word != breakpoint_insn.word) {
  299  		/*
  300  		 * The breakpoint instruction was removed right
  301  		 * after we hit it.  Another cpu has removed
  302  		 * either a probepoint or a debugger breakpoint
  303  		 * at this address.  In either case, no further
  304  		 * handling of this interrupt is appropriate.
  305  		 * Return back to original instruction, and continue.
  306  		 */
  307  		regs->csr_era = (unsigned long)addr;
  308  		preempt_enable_no_resched();
  309  		return true;
  310  	}
  311  
  312  	preempt_enable_no_resched();
  313  	return false;
  314  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_31

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.3）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_bp

【程序给出的理由】rt B:trap: line 490 force_sig_fault -> spin_lock_irqsave

【调用链】force_sig_fault（kernel/signal.c第1726行调用force_sig_fault_to_task） → force_sig_fault_to_task（kernel/signal.c第1720行调用force_sig_info_to_task） → force_sig_info_to_task（kernel/signal.c第1329行调用spin_lock_irqsave）

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

【force_sig_fault的代码（kernel/signal.c）】
```c
 1725  int force_sig_fault(int sig, int code, void __user *addr 	___ARCH_SI_IA64(int imm, unsigned int flags, unsigned long isr))  {
 1726  	return force_sig_fault_to_task(sig, code, addr
 1727  				       ___ARCH_SI_IA64(imm, flags, isr), current);
 1728  }
```

【force_sig_fault_to_task的代码（kernel/signal.c）】
```c
 1707  int force_sig_fault_to_task(int sig, int code, void __user *addr 	___ARCH_SI_IA64(int imm, unsigned int flags, unsigned long isr) 	, struct task_struct *t)  {
 1708  	struct kernel_siginfo info;
 1709  
 1710  	clear_siginfo(&info);
 1711  	info.si_signo = sig;
 1712  	info.si_errno = 0;
 1713  	info.si_code  = code;
 1714  	info.si_addr  = addr;
 1715  #ifdef __ia64__
 1716  	info.si_imm = imm;
 1717  	info.si_flags = flags;
 1718  	info.si_isr = isr;
 1719  #endif
 1720  	return force_sig_info_to_task(&info, t, HANDLER_CURRENT);
 1721  }
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

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_32

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.3）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_watch

【程序给出的理由】rt B:trap: line 558 force_sig -> spin_lock_irqsave

【调用链】force_sig（kernel/signal.c第1660行调用force_sig_info） → force_sig_info（kernel/signal.c第1357行调用force_sig_info_to_task） → force_sig_info_to_task（kernel/signal.c第1329行调用spin_lock_irqsave）

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

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_33

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.3）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_watch

【程序给出的理由】noinstr N2: line 555 watchpoint_handler -> instrumentable callee

【调用链】watchpoint_handler（arch/loongarch/kernel/hw_breakpoint.c第483行调用）

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

【watchpoint_handler的代码（arch/loongarch/kernel/hw_breakpoint.c）】
```c
  483  void watchpoint_handler(struct pt_regs *regs)  {
  484  	int i;
  485  	struct perf_event *wp, **slots;
  486  
  487  	slots = this_cpu_ptr(wp_on_reg);
  488  
  489  	for (i = 0; i < boot_cpu_data.watch_dreg_count; ++i) {
  490  		wp = slots[i];
  491  		if (wp == NULL)
  492  			continue;
  493  		perf_bp_event(wp, regs);
  494  	}
  495  	update_bp_registers(regs, 0, 1);
  496  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_34

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.4）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_bce

【程序给出的理由】rt B:trap: line 664 force_sig_bnderr -> spin_lock_irqsave

【调用链】force_sig_bnderr（kernel/signal.c第1790行调用force_sig_info） → force_sig_info（kernel/signal.c第1356行调用force_sig_info_to_task） → force_sig_info_to_task（kernel/signal.c第1328行调用spin_lock_irqsave）

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

【force_sig_info的代码（kernel/signal.c）】
```c
 1355  int force_sig_info(struct kernel_siginfo *info)  {
 1356  	return force_sig_info_to_task(info, current, HANDLER_CURRENT);
 1357  }
```

【force_sig_info_to_task的代码（kernel/signal.c）】
```c
 1322  static int force_sig_info_to_task(struct kernel_siginfo *info, struct task_struct *t, 	enum sig_handler handler)  {
 1323  	unsigned long int flags;
 1324  	int ret, blocked, ignored;
 1325  	struct k_sigaction *action;
 1326  	int sig = info->si_signo;
 1327  
 1328  	spin_lock_irqsave(&t->sighand->siglock, flags);
 1329  	action = &t->sighand->action[sig-1];
 1330  	ignored = action->sa.sa_handler == SIG_IGN;
 1331  	blocked = sigismember(&t->blocked, sig);
 1332  	if (blocked || ignored || (handler != HANDLER_CURRENT)) {
 1333  		action->sa.sa_handler = SIG_DFL;
 1334  		if (handler == HANDLER_EXIT)
 1335  			action->sa.sa_flags |= SA_IMMUTABLE;
 1336  		if (blocked) {
 1337  			sigdelset(&t->blocked, sig);
 1338  			recalc_sigpending_and_wake(t);
 1339  		}
 1340  	}
 1341  	/*
 1342  	 * Don't clear SIGNAL_UNKILLABLE for traced tasks, users won't expect
 1343  	 * debugging to leave init killable. But HANDLER_EXIT is always fatal.
 1344  	 */
 1345  	if (action->sa.sa_handler == SIG_DFL &&
 1346  	    (!t->ptrace || (handler == HANDLER_EXIT)))
 1347  		t->signal->flags &= ~SIGNAL_UNKILLABLE;
 1348  	ret = send_signal_locked(sig, info, t, PIDTYPE_PID);
 1349  	spin_unlock_irqrestore(&t->sighand->siglock, flags);
 1350  
 1351  	return ret;
 1352  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_35

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.4）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_bce

【程序给出的理由】rt B:trap: line 678 force_sig -> spin_lock_irqsave

【调用链】force_sig（kernel/signal.c第1661行调用force_sig_info） → force_sig_info（kernel/signal.c第1356行调用force_sig_info_to_task） → force_sig_info_to_task（kernel/signal.c第1328行调用spin_lock_irqsave）

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

【force_sig_info的代码（kernel/signal.c）】
```c
 1355  int force_sig_info(struct kernel_siginfo *info)  {
 1356  	return force_sig_info_to_task(info, current, HANDLER_CURRENT);
 1357  }
```

【force_sig_info_to_task的代码（kernel/signal.c）】
```c
 1322  static int force_sig_info_to_task(struct kernel_siginfo *info, struct task_struct *t, 	enum sig_handler handler)  {
 1323  	unsigned long int flags;
 1324  	int ret, blocked, ignored;
 1325  	struct k_sigaction *action;
 1326  	int sig = info->si_signo;
 1327  
 1328  	spin_lock_irqsave(&t->sighand->siglock, flags);
 1329  	action = &t->sighand->action[sig-1];
 1330  	ignored = action->sa.sa_handler == SIG_IGN;
 1331  	blocked = sigismember(&t->blocked, sig);
 1332  	if (blocked || ignored || (handler != HANDLER_CURRENT)) {
 1333  		action->sa.sa_handler = SIG_DFL;
 1334  		if (handler == HANDLER_EXIT)
 1335  			action->sa.sa_flags |= SA_IMMUTABLE;
 1336  		if (blocked) {
 1337  			sigdelset(&t->blocked, sig);
 1338  			recalc_sigpending_and_wake(t);
 1339  		}
 1340  	}
 1341  	/*
 1342  	 * Don't clear SIGNAL_UNKILLABLE for traced tasks, users won't expect
 1343  	 * debugging to leave init killable. But HANDLER_EXIT is always fatal.
 1344  	 */
 1345  	if (action->sa.sa_handler == SIG_DFL &&
 1346  	    (!t->ptrace || (handler == HANDLER_EXIT)))
 1347  		t->signal->flags &= ~SIGNAL_UNKILLABLE;
 1348  	ret = send_signal_locked(sig, info, t, PIDTYPE_PID);
 1349  	spin_unlock_irqrestore(&t->sighand->siglock, flags);
 1350  
 1351  	return ret;
 1352  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_36

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.5）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_bp

【程序给出的理由】noinstr N2: line 721 uprobe_singlestep_handler -> instrumentable callee

【调用链】uprobe_singlestep_handler（arch/loongarch/kernel/uprobes.c第132行调用）

【do_bp的代码】
```c
  686  asmlinkage void noinstr do_bp(struct pt_regs *regs)  {
  687  	bool user = user_mode(regs);
  688  	unsigned int opcode, bcode;
  689  	unsigned long era = exception_era(regs);
  690  	irqentry_state_t state = irqentry_enter(regs);
  691  
  692  	if (regs->csr_prmd & CSR_PRMD_PIE)
  693  		local_irq_enable();
  694  
  695  	if (__get_inst(&opcode, (u32 *)era, user))
  696  		goto out_sigsegv;
  697  
  698  	bcode = (opcode & 0x7fff);
  699  
  700  	/*
  701  	 * notify the kprobe handlers, if instruction is likely to
  702  	 * pertain to them.
  703  	 */
  704  	switch (bcode) {
  705  	case BRK_KPROBE_BP:
  706  		if (kprobe_breakpoint_handler(regs))
  707  			goto out;
  708  		else
  709  			break;
  710  	case BRK_KPROBE_SSTEPBP:
  711  		if (kprobe_singlestep_handler(regs))
  712  			goto out;
  713  		else
  714  			break;
  715  	case BRK_UPROBE_BP:
  716  		if (uprobe_breakpoint_handler(regs))
  717  			goto out;
  718  		else
  719  			break;
  720  	case BRK_UPROBE_XOLBP:
  721  		if (uprobe_singlestep_handler(regs))
  722  			goto out;
  723  		else
  724  			break;
  725  	default:
  726  		current->thread.trap_nr = read_csr_excode();
  727  		if (notify_die(DIE_TRAP, "Break", regs, bcode,
  728  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  729  			goto out;
  730  		else
  731  			break;
  732  	}
  733  
  734  	switch (bcode) {
  735  	case BRK_BUG:
  736  		bug_handler(regs);
  737  		break;
  738  	case BRK_DIVZERO:
  739  		die_if_kernel("Break instruction in kernel code", regs);
  740  		force_sig_fault(SIGFPE, FPE_INTDIV, (void __user *)regs->csr_era);
  741  		break;
  742  	case BRK_OVERFLOW:
  743  		die_if_kernel("Break instruction in kernel code", regs);
  744  		force_sig_fault(SIGFPE, FPE_INTOVF, (void __user *)regs->csr_era);
  745  		break;
  746  	default:
  747  		die_if_kernel("Break instruction in kernel code", regs);
  748  		force_sig_fault(SIGTRAP, TRAP_BRKPT, (void __user *)regs->csr_era);
  749  		break;
  750  	}
  751  
  752  out:
  753  	if (regs->csr_prmd & CSR_PRMD_PIE)
  754  		local_irq_disable();
  755  
  756  	irqentry_exit(regs, state);
  757  	return;
  758  
  759  out_sigsegv:
  760  	force_sig(SIGSEGV);
  761  	goto out;
  762  }
```

【uprobe_singlestep_handler的代码（arch/loongarch/kernel/uprobes.c）】
```c
  132  bool uprobe_singlestep_handler(struct pt_regs *regs)  {
  133  	if (uprobe_post_sstep_notifier(regs))
  134  		return true;
  135  
  136  	return false;
  137  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_37

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.5）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_bp

【程序给出的理由】noinstr N2: line 716 uprobe_breakpoint_handler -> instrumentable callee

【调用链】uprobe_breakpoint_handler（arch/loongarch/kernel/uprobes.c第124行调用）

【do_bp的代码】
```c
  686  asmlinkage void noinstr do_bp(struct pt_regs *regs)  {
  687  	bool user = user_mode(regs);
  688  	unsigned int opcode, bcode;
  689  	unsigned long era = exception_era(regs);
  690  	irqentry_state_t state = irqentry_enter(regs);
  691  
  692  	if (regs->csr_prmd & CSR_PRMD_PIE)
  693  		local_irq_enable();
  694  
  695  	if (__get_inst(&opcode, (u32 *)era, user))
  696  		goto out_sigsegv;
  697  
  698  	bcode = (opcode & 0x7fff);
  699  
  700  	/*
  701  	 * notify the kprobe handlers, if instruction is likely to
  702  	 * pertain to them.
  703  	 */
  704  	switch (bcode) {
  705  	case BRK_KPROBE_BP:
  706  		if (kprobe_breakpoint_handler(regs))
  707  			goto out;
  708  		else
  709  			break;
  710  	case BRK_KPROBE_SSTEPBP:
  711  		if (kprobe_singlestep_handler(regs))
  712  			goto out;
  713  		else
  714  			break;
  715  	case BRK_UPROBE_BP:
  716  		if (uprobe_breakpoint_handler(regs))
  717  			goto out;
  718  		else
  719  			break;
  720  	case BRK_UPROBE_XOLBP:
  721  		if (uprobe_singlestep_handler(regs))
  722  			goto out;
  723  		else
  724  			break;
  725  	default:
  726  		current->thread.trap_nr = read_csr_excode();
  727  		if (notify_die(DIE_TRAP, "Break", regs, bcode,
  728  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  729  			goto out;
  730  		else
  731  			break;
  732  	}
  733  
  734  	switch (bcode) {
  735  	case BRK_BUG:
  736  		bug_handler(regs);
  737  		break;
  738  	case BRK_DIVZERO:
  739  		die_if_kernel("Break instruction in kernel code", regs);
  740  		force_sig_fault(SIGFPE, FPE_INTDIV, (void __user *)regs->csr_era);
  741  		break;
  742  	case BRK_OVERFLOW:
  743  		die_if_kernel("Break instruction in kernel code", regs);
  744  		force_sig_fault(SIGFPE, FPE_INTOVF, (void __user *)regs->csr_era);
  745  		break;
  746  	default:
  747  		die_if_kernel("Break instruction in kernel code", regs);
  748  		force_sig_fault(SIGTRAP, TRAP_BRKPT, (void __user *)regs->csr_era);
  749  		break;
  750  	}
  751  
  752  out:
  753  	if (regs->csr_prmd & CSR_PRMD_PIE)
  754  		local_irq_disable();
  755  
  756  	irqentry_exit(regs, state);
  757  	return;
  758  
  759  out_sigsegv:
  760  	force_sig(SIGSEGV);
  761  	goto out;
  762  }
```

【uprobe_breakpoint_handler的代码（arch/loongarch/kernel/uprobes.c）】
```c
  124  bool uprobe_breakpoint_handler(struct pt_regs *regs)  {
  125  	if (uprobe_pre_sstep_notifier(regs))
  126  		return true;
  127  
  128  	return false;
  129  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_38

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.5）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_lasx

【程序给出的理由】noinstr N2: line 961 init_restore_lasx -> instrumentable callee

【调用链】init_restore_lasx（arch/loongarch/kernel/traps.c第883行调用）

【do_lasx的代码】
```c
  949  asmlinkage void noinstr do_lasx(struct pt_regs *regs)  {
  950  	irqentry_state_t state = irqentry_enter(regs);
  951  
  952  	local_irq_enable();
  953  	if (!cpu_has_lasx) {
  954  		force_sig(SIGILL);
  955  		goto out;
  956  	}
  957  
  958  	die_if_kernel("do_lasx invoked from kernel context!", regs);
  959  
  960  	preempt_disable();
  961  	init_restore_lasx();
  962  	preempt_enable();
  963  
  964  out:
  965  	local_irq_disable();
  966  	irqentry_exit(regs, state);
  967  }
```

【init_restore_lasx的代码（arch/loongarch/kernel/traps.c）】
```c
  883  static void init_restore_lasx(void)  {
  884  	enable_lasx();
  885  
  886  	if (!thread_lasx_context_live()) {
  887  		/* First time LASX context user */
  888  		init_restore_lsx();
  889  		init_lasx_upper();
  890  		set_thread_flag(TIF_LASX_CTX_LIVE);
  891  	} else {
  892  		if (is_fpu_owner() || is_simd_owner()) {
  893  			init_restore_lsx();
  894  			restore_lasx_upper(current);
  895  		} else {
  896  			__own_fpu();
  897  			enable_lsx();
  898  			restore_lasx(current);
  899  		}
  900  	}
  901  
  902  	set_thread_flag(TIF_USEDSIMD);
  903  
  904  	BUG_ON(!is_fp_enabled());
  905  	BUG_ON(!is_lsx_enabled());
  906  	BUG_ON(!is_lasx_enabled());
  907  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_39

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.5）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_lsx

【程序给出的理由】noinstr N2: line 940 init_restore_lsx -> instrumentable callee

【调用链】init_restore_lsx（arch/loongarch/kernel/traps.c第857行调用）

【do_lsx的代码】
```c
  927  asmlinkage void noinstr do_lsx(struct pt_regs *regs)  {
  928  	irqentry_state_t state = irqentry_enter(regs);
  929  
  930  	local_irq_enable();
  931  	if (!cpu_has_lsx) {
  932  		force_sig(SIGILL);
  933  		goto out;
  934  	}
  935  
  936  	die_if_kernel("do_lsx invoked from kernel context!", regs);
  937  	BUG_ON(is_lasx_enabled());
  938  
  939  	preempt_disable();
  940  	init_restore_lsx();
  941  	preempt_enable();
  942  
  943  out:
  944  	local_irq_disable();
  945  	irqentry_exit(regs, state);
  946  }
```

【init_restore_lsx的代码（arch/loongarch/kernel/traps.c）】
```c
  857  static void init_restore_lsx(void)  {
  858  	enable_lsx();
  859  
  860  	if (!thread_lsx_context_live()) {
  861  		/* First time LSX context user */
  862  		init_restore_fp();
  863  		init_lsx_upper();
  864  		set_thread_flag(TIF_LSX_CTX_LIVE);
  865  	} else {
  866  		if (!is_simd_owner()) {
  867  			if (is_fpu_owner()) {
  868  				restore_lsx_upper(current);
  869  			} else {
  870  				__own_fpu();
  871  				restore_lsx(current);
  872  			}
  873  		}
  874  	}
  875  
  876  	set_thread_flag(TIF_USEDSIMD);
  877  
  878  	BUG_ON(!is_fp_enabled());
  879  	BUG_ON(!is_lsx_enabled());
  880  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_40

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.5）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】同一约定规则：公共代码调用、各架构各自实现的函数中，arm64、x86、RISC-V三个实现都调用了某个函数，LoongArch的实现没有。

【被标记的位置】arch/loongarch/power/hibernate.c中的swsusp_arch_resume

【程序给出的理由】all three references call ['get_safe_page'], loongarch does not

【swsusp_arch_resume的代码】
```c
   58  int swsusp_arch_resume(void)  {
   59  	/* Avoid TLB mismatch during and after kernel resume */
   60  	local_flush_tlb_all();
   61  	return swsusp_asm_resume();
   62  }
```

【参照：arm64的swsusp_arch_resume（arch/arm64/kernel/hibernate.c）】
```c
  400  int swsusp_arch_resume(void)  {
  401  	int rc;
  402  	void *zero_page;
  403  	size_t exit_size;
  404  	pgd_t *tmp_pg_dir;
  405  	phys_addr_t el2_vectors;
  406  	void __noreturn (*hibernate_exit)(phys_addr_t, phys_addr_t, void *,
  407  					  void *, phys_addr_t, phys_addr_t);
  408  	struct trans_pgd_info trans_info = {
  409  		.trans_alloc_page	= hibernate_page_alloc,
  410  		.trans_alloc_arg	= (void *)GFP_ATOMIC,
  411  	};
  412  
  413  	/*
  414  	 * Restoring the memory image will overwrite the ttbr1 page tables.
  415  	 * Create a second copy of just the linear map, and use this when
  416  	 * restoring.
  417  	 */
  418  	rc = trans_pgd_create_copy(&trans_info, &tmp_pg_dir, PAGE_OFFSET,
  419  				   PAGE_END);
  420  	if (rc)
  421  		return rc;
  422  
  423  	/*
  424  	 * We need a zero page that is zero before & after resume in order
  425  	 * to break before make on the ttbr1 page tables.
  426  	 */
  427  	zero_page = (void *)get_safe_page(GFP_ATOMIC);
  428  	if (!zero_page) {
  429  		pr_err("Failed to allocate zero page.\n");
  430  		return -ENOMEM;
  431  	}
  432  
  433  	if (el2_reset_needed()) {
  434  		rc = trans_pgd_copy_el2_vectors(&trans_info, &el2_vectors);
  435  		if (rc) {
  436  			pr_err("Failed to setup el2 vectors\n");
  437  			return rc;
  438  		}
  439  	}
  440  
  441  	exit_size = __hibernate_exit_text_end - __hibernate_exit_text_start;
  442  	/*
  443  	 * Copy swsusp_arch_suspend_exit() to a safe page. This will generate
  444  	 * a new set of ttbr0 page tables and load them.
  445  	 */
  446  	rc = create_safe_exec_page(__hibernate_exit_text_start, exit_size,
  447  				   (phys_addr_t *)&hibernate_exit);
  448  	if (rc) {
  449  		pr_err("Failed to create safe executable page for hibernate_exit code.\n");
...（其余18行省略）
```

【参照：x86的swsusp_arch_resume（arch/x86/power/hibernate_32.c）】
```c
  172  asmlinkage int swsusp_arch_resume(void)  {
  173  	int error;
  174  
  175  	resume_pg_dir = (pgd_t *)get_safe_page(GFP_ATOMIC);
  176  	if (!resume_pg_dir)
  177  		return -ENOMEM;
  178  
  179  	resume_init_first_level_page_table(resume_pg_dir);
  180  
  181  	error = set_up_temporary_text_mapping(resume_pg_dir);
  182  	if (error)
  183  		return error;
  184  
  185  	error = resume_physical_mapping_init(resume_pg_dir);
  186  	if (error)
  187  		return error;
  188  
  189  	temp_pgt = __pa(resume_pg_dir);
  190  
  191  	error = relocate_restore_code();
  192  	if (error)
  193  		return error;
  194  
  195  	/* We have got enough memory and from now on we cannot recover */
  196  	restore_image();
  197  	return 0;
  198  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_41

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_bp

【程序给出的理由】noinstr N2: line 693 kgdb_breakpoint_handler -> instrumentable callee

【调用链】kgdb_breakpoint_handler（arch/loongarch/kernel/kgdb.c第265行调用）

【do_bp的代码】
```c
  673  asmlinkage void noinstr do_bp(struct pt_regs *regs)  {
  674  	bool user = user_mode(regs);
  675  	unsigned int opcode, bcode;
  676  	unsigned long era = exception_era(regs);
  677  	irqentry_state_t state = irqentry_enter(regs);
  678  
  679  	if (regs->csr_prmd & CSR_PRMD_PIE)
  680  		local_irq_enable();
  681  
  682  	if (__get_inst(&opcode, (u32 *)era, user))
  683  		goto out_sigsegv;
  684  
  685  	bcode = (opcode & 0x7fff);
  686  
  687  	/*
  688  	 * notify the kprobe handlers, if instruction is likely to
  689  	 * pertain to them.
  690  	 */
  691  	switch (bcode) {
  692  	case BRK_KDB:
  693  		if (kgdb_breakpoint_handler(regs))
  694  			goto out;
  695  		else
  696  			break;
  697  	case BRK_KPROBE_BP:
  698  		if (kprobe_breakpoint_handler(regs))
  699  			goto out;
  700  		else
  701  			break;
  702  	case BRK_KPROBE_SSTEPBP:
  703  		if (kprobe_singlestep_handler(regs))
  704  			goto out;
  705  		else
  706  			break;
  707  	case BRK_UPROBE_BP:
  708  		if (uprobe_breakpoint_handler(regs))
  709  			goto out;
  710  		else
  711  			break;
  712  	case BRK_UPROBE_XOLBP:
  713  		if (uprobe_singlestep_handler(regs))
  714  			goto out;
  715  		else
  716  			break;
  717  	default:
  718  		current->thread.trap_nr = read_csr_excode();
  719  		if (notify_die(DIE_TRAP, "Break", regs, bcode,
  720  			       current->thread.trap_nr, SIGTRAP) == NOTIFY_STOP)
  721  			goto out;
  722  		else
  723  			break;
  724  	}
  725  
  726  	switch (bcode) {
  727  	case BRK_BUG:
  728  		bug_handler(regs);
  729  		break;
  730  	case BRK_DIVZERO:
  731  		die_if_kernel("Break instruction in kernel code", regs);
  732  		force_sig_fault(SIGFPE, FPE_INTDIV, (void __user *)regs->csr_era);
  733  		break;
  734  	case BRK_OVERFLOW:
  735  		die_if_kernel("Break instruction in kernel code", regs);
  736  		force_sig_fault(SIGFPE, FPE_INTOVF, (void __user *)regs->csr_era);
  737  		break;
  738  	default:
  739  		die_if_kernel("Break instruction in kernel code", regs);
  740  		force_sig_fault(SIGTRAP, TRAP_BRKPT, (void __user *)regs->csr_era);
  741  		break;
  742  	}
  743  
  744  out:
  745  	if (regs->csr_prmd & CSR_PRMD_PIE)
  746  		local_irq_disable();
  747  
  748  	irqentry_exit(regs, state);
  749  	return;
  750  
  751  out_sigsegv:
  752  	force_sig(SIGSEGV);
...（其余2行省略）
```

【kgdb_breakpoint_handler的代码（arch/loongarch/kernel/kgdb.c）】
```c
  265  bool kgdb_breakpoint_handler(struct pt_regs *regs)  {
  266  	struct die_args args = {
  267  		.regs	= regs,
  268  		.str	= "Break",
  269  		.err	= BRK_KDB,
  270  		.trapnr = read_csr_excode(),
  271  		.signr	= SIGTRAP,
  272  
  273  	};
  274  
  275  	return (kgdb_loongarch_notify(NULL, DIE_TRAP, &args) == NOTIFY_STOP) ? true : false;
  276  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_42

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_lbt

【程序给出的理由】rt B:trap: line 993 force_sig -> spin_lock_irqsave

【调用链】force_sig（kernel/signal.c第1677行调用force_sig_info） → force_sig_info（kernel/signal.c第1372行调用force_sig_info_to_task） → force_sig_info_to_task（kernel/signal.c第1344行调用spin_lock_irqsave）

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

【force_sig的代码（kernel/signal.c）】
```c
 1668  void force_sig(int sig)  {
 1669  	struct kernel_siginfo info;
 1670  
 1671  	clear_siginfo(&info);
 1672  	info.si_signo = sig;
 1673  	info.si_errno = 0;
 1674  	info.si_code = SI_KERNEL;
 1675  	info.si_pid = 0;
 1676  	info.si_uid = 0;
 1677  	force_sig_info(&info);
 1678  }
```

【force_sig_info的代码（kernel/signal.c）】
```c
 1371  int force_sig_info(struct kernel_siginfo *info)  {
 1372  	return force_sig_info_to_task(info, current, HANDLER_CURRENT);
 1373  }
```

【force_sig_info_to_task的代码（kernel/signal.c）】
```c
 1338  static int force_sig_info_to_task(struct kernel_siginfo *info, struct task_struct *t, 	enum sig_handler handler)  {
 1339  	unsigned long int flags;
 1340  	int ret, blocked, ignored;
 1341  	struct k_sigaction *action;
 1342  	int sig = info->si_signo;
 1343  
 1344  	spin_lock_irqsave(&t->sighand->siglock, flags);
 1345  	action = &t->sighand->action[sig-1];
 1346  	ignored = action->sa.sa_handler == SIG_IGN;
 1347  	blocked = sigismember(&t->blocked, sig);
 1348  	if (blocked || ignored || (handler != HANDLER_CURRENT)) {
 1349  		action->sa.sa_handler = SIG_DFL;
 1350  		if (handler == HANDLER_EXIT)
 1351  			action->sa.sa_flags |= SA_IMMUTABLE;
 1352  		if (blocked) {
 1353  			sigdelset(&t->blocked, sig);
 1354  			recalc_sigpending_and_wake(t);
 1355  		}
 1356  	}
 1357  	/*
 1358  	 * Don't clear SIGNAL_UNKILLABLE for traced tasks, users won't expect
 1359  	 * debugging to leave init killable. But HANDLER_EXIT is always fatal.
 1360  	 */
 1361  	if (action->sa.sa_handler == SIG_DFL &&
 1362  	    (!t->ptrace || (handler == HANDLER_EXIT)))
 1363  		t->signal->flags &= ~SIGNAL_UNKILLABLE;
 1364  	ret = send_signal_locked(sig, info, t, PIDTYPE_PID);
 1365  	spin_unlock_irqrestore(&t->sighand->siglock, flags);
 1366  
 1367  	return ret;
 1368  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_43

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.6）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_watch

【程序给出的理由】noinstr N2: line 763 kgdb_breakpoint_handler -> instrumentable callee

【调用链】kgdb_breakpoint_handler（arch/loongarch/kernel/kgdb.c第265行调用）

【do_watch的代码】
```c
  757  asmlinkage void noinstr do_watch(struct pt_regs *regs)  {
  758  	irqentry_state_t state = irqentry_enter(regs);
  759  
  760  #ifndef CONFIG_HAVE_HW_BREAKPOINT
  761  	pr_warn("Hardware watch point handler not implemented!\n");
  762  #else
  763  	if (kgdb_breakpoint_handler(regs))
  764  		goto out;
  765  
  766  	if (test_tsk_thread_flag(current, TIF_SINGLESTEP)) {
  767  		int llbit = (csr_read32(LOONGARCH_CSR_LLBCTL) & 0x1);
  768  		unsigned long pc = instruction_pointer(regs);
  769  		union loongarch_instruction *ip = (union loongarch_instruction *)pc;
  770  
  771  		if (llbit) {
  772  			/*
  773  			 * When the ll-sc combo is encountered, it is regarded as an single
  774  			 * instruction. So don't clear llbit and reset CSR.FWPS.Skip until
  775  			 * the llsc execution is completed.
  776  			 */
  777  			csr_write32(CSR_FWPC_SKIP, LOONGARCH_CSR_FWPS);
  778  			csr_write32(CSR_LLBCTL_KLO, LOONGARCH_CSR_LLBCTL);
  779  			goto out;
  780  		}
  781  
  782  		if (pc == current->thread.single_step) {
  783  			/*
  784  			 * Certain insns are occasionally not skipped when CSR.FWPS.Skip is
  785  			 * set, such as fld.d/fst.d. So singlestep needs to compare whether
  786  			 * the csr_era is equal to the value of singlestep which last time set.
  787  			 */
  788  			if (!is_self_loop_ins(ip, regs)) {
  789  				/*
  790  				 * Check if the given instruction the target pc is equal to the
  791  				 * current pc, If yes, then we should not set the CSR.FWPS.SKIP
  792  				 * bit to break the original instruction stream.
  793  				 */
  794  				csr_write32(CSR_FWPC_SKIP, LOONGARCH_CSR_FWPS);
  795  				goto out;
  796  			}
  797  		}
  798  	} else {
  799  		breakpoint_handler(regs);
  800  		watchpoint_handler(regs);
  801  	}
  802  
  803  	force_sig(SIGTRAP);
  804  out:
  805  #endif
  806  	irqentry_exit(regs, state);
  807  }
```

【kgdb_breakpoint_handler的代码（arch/loongarch/kernel/kgdb.c）】
```c
  265  bool kgdb_breakpoint_handler(struct pt_regs *regs)  {
  266  	struct die_args args = {
  267  		.regs	= regs,
  268  		.str	= "Break",
  269  		.err	= BRK_KDB,
  270  		.trapnr = read_csr_excode(),
  271  		.signr	= SIGTRAP,
  272  
  273  	};
  274  
  275  	return (kgdb_loongarch_notify(NULL, DIE_TRAP, &args) == NOTIFY_STOP) ? true : false;
  276  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_44

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.7）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kvm/vcpu.c中的kvm_arch_vcpu_load

【程序给出的理由】rt A:irq: line 800 kvm_migrate_count -> spin_lock_bh

【调用链】kvm_migrate_count（arch/loongarch/kvm/vcpu.c第260行调用hrtimer_cancel） → hrtimer_cancel（kernel/time/hrtimer.c第1449行调用hrtimer_cancel_wait_running） → hrtimer_cancel_wait_running（kernel/time/hrtimer.c第1418行调用spin_lock_bh）

【kvm_arch_vcpu_load的代码】
```c
  788  void kvm_arch_vcpu_load(struct kvm_vcpu *vcpu, int cpu)  {
  789  	unsigned long flags;
  790  
  791  	local_irq_save(flags);
  792  	if (vcpu->arch.last_sched_cpu != cpu) {
  793  		kvm_debug("[%d->%d]KVM vCPU[%d] switch\n",
  794  				vcpu->arch.last_sched_cpu, cpu, vcpu->vcpu_id);
  795  		/*
  796  		 * Migrate the timer interrupt to the current CPU so that it
  797  		 * always interrupts the guest and synchronously triggers a
  798  		 * guest timer interrupt.
  799  		 */
  800  		kvm_migrate_count(vcpu);
  801  	}
  802  
  803  	/* Restore guest state to registers */
  804  	_kvm_vcpu_load(vcpu, cpu);
  805  	local_irq_restore(flags);
  806  }
```

【kvm_migrate_count的代码（arch/loongarch/kvm/vcpu.c）】
```c
  259  static void kvm_migrate_count(struct kvm_vcpu *vcpu)  {
  260  	if (hrtimer_cancel(&vcpu->arch.swtimer))
  261  		hrtimer_restart(&vcpu->arch.swtimer);
  262  }
```

【hrtimer_cancel的代码（kernel/time/hrtimer.c）】
```c
 1442  int hrtimer_cancel(struct hrtimer *timer)  {
 1443  	int ret;
 1444  
 1445  	do {
 1446  		ret = hrtimer_try_to_cancel(timer);
 1447  
 1448  		if (ret < 0)
 1449  			hrtimer_cancel_wait_running(timer);
 1450  	} while (ret < 0);
 1451  	return ret;
 1452  }
```

【hrtimer_cancel_wait_running的代码（kernel/time/hrtimer.c）】
```c
 1397  void hrtimer_cancel_wait_running(const struct hrtimer *timer)  {
 1398  	/* Lockless read. Prevent the compiler from reloading it below */
 1399  	struct hrtimer_clock_base *base = READ_ONCE(timer->base);
 1400  
 1401  	/*
 1402  	 * Just relax if the timer expires in hard interrupt context or if
 1403  	 * it is currently on the migration base.
 1404  	 */
 1405  	if (!timer->is_soft || is_migration_base(base)) {
 1406  		cpu_relax();
 1407  		return;
 1408  	}
 1409  
 1410  	/*
 1411  	 * Mark the base as contended and grab the expiry lock, which is
 1412  	 * held by the softirq across the timer callback. Drop the lock
 1413  	 * immediately so the softirq can expire the next timer. In theory
 1414  	 * the timer could already be running again, but that's more than
 1415  	 * unlikely and just causes another wait loop.
 1416  	 */
 1417  	atomic_inc(&base->cpu_base->timer_waiters);
 1418  	spin_lock_bh(&base->cpu_base->softirq_expiry_lock);
 1419  	atomic_dec(&base->cpu_base->timer_waiters);
 1420  	spin_unlock_bh(&base->cpu_base->softirq_expiry_lock);
 1421  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_45

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.7）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kvm/vcpu.c中的kvm_pre_enter_guest

【程序给出的理由】rt A:irq: line 98 kvm_acquire_timer -> spin_lock_bh

【调用链】kvm_acquire_timer（arch/loongarch/kvm/timer.c第86行调用hrtimer_cancel） → hrtimer_cancel（kernel/time/hrtimer.c第1449行调用hrtimer_cancel_wait_running） → hrtimer_cancel_wait_running（kernel/time/hrtimer.c第1418行调用spin_lock_bh）

【kvm_pre_enter_guest的代码】
```c
   85  static int kvm_pre_enter_guest(struct kvm_vcpu *vcpu)  {
   86  	int ret;
   87  
   88  	do {
   89  		ret = kvm_enter_guest_check(vcpu);
   90  		if (ret != RESUME_GUEST)
   91  			break;
   92  
   93  		/*
   94  		 * Handle vcpu timer, interrupts, check requests and
   95  		 * check vmid before vcpu enter guest
   96  		 */
   97  		local_irq_disable();
   98  		kvm_acquire_timer(vcpu);
   99  		kvm_deliver_intr(vcpu);
  100  		kvm_deliver_exception(vcpu);
  101  		/* Make sure the vcpu mode has been written */
  102  		smp_store_mb(vcpu->mode, IN_GUEST_MODE);
  103  		kvm_check_vpid(vcpu);
  104  		vcpu->arch.host_eentry = csr_read64(LOONGARCH_CSR_EENTRY);
  105  		/* Clear KVM_LARCH_SWCSR_LATEST as CSR will change when enter guest */
  106  		vcpu->arch.aux_inuse &= ~KVM_LARCH_SWCSR_LATEST;
  107  
  108  		if (kvm_request_pending(vcpu) || xfer_to_guest_mode_work_pending()) {
  109  			/* make sure the vcpu mode has been written */
  110  			smp_store_mb(vcpu->mode, OUTSIDE_GUEST_MODE);
  111  			local_irq_enable();
  112  			ret = -EAGAIN;
  113  		}
  114  	} while (ret != RESUME_GUEST);
  115  
  116  	return ret;
  117  }
```

【kvm_acquire_timer的代码（arch/loongarch/kvm/timer.c）】
```c
   72  void kvm_acquire_timer(struct kvm_vcpu *vcpu)  {
   73  	unsigned long cfg;
   74  
   75  	cfg = read_csr_gcfg();
   76  	if (!(cfg & CSR_GCFG_TIT))
   77  		return;
   78  
   79  	/* Enable guest access to hard timer */
   80  	write_csr_gcfg(cfg & ~CSR_GCFG_TIT);
   81  
   82  	/*
   83  	 * Freeze the soft-timer and sync the guest stable timer with it. We do
   84  	 * this with interrupts disabled to avoid latency.
   85  	 */
   86  	hrtimer_cancel(&vcpu->arch.swtimer);
   87  }
```

【hrtimer_cancel的代码（kernel/time/hrtimer.c）】
```c
 1442  int hrtimer_cancel(struct hrtimer *timer)  {
 1443  	int ret;
 1444  
 1445  	do {
 1446  		ret = hrtimer_try_to_cancel(timer);
 1447  
 1448  		if (ret < 0)
 1449  			hrtimer_cancel_wait_running(timer);
 1450  	} while (ret < 0);
 1451  	return ret;
 1452  }
```

【hrtimer_cancel_wait_running的代码（kernel/time/hrtimer.c）】
```c
 1397  void hrtimer_cancel_wait_running(const struct hrtimer *timer)  {
 1398  	/* Lockless read. Prevent the compiler from reloading it below */
 1399  	struct hrtimer_clock_base *base = READ_ONCE(timer->base);
 1400  
 1401  	/*
 1402  	 * Just relax if the timer expires in hard interrupt context or if
 1403  	 * it is currently on the migration base.
 1404  	 */
 1405  	if (!timer->is_soft || is_migration_base(base)) {
 1406  		cpu_relax();
 1407  		return;
 1408  	}
 1409  
 1410  	/*
 1411  	 * Mark the base as contended and grab the expiry lock, which is
 1412  	 * held by the softirq across the timer callback. Drop the lock
 1413  	 * immediately so the softirq can expire the next timer. In theory
 1414  	 * the timer could already be running again, but that's more than
 1415  	 * unlikely and just causes another wait loop.
 1416  	 */
 1417  	atomic_inc(&base->cpu_base->timer_waiters);
 1418  	spin_lock_bh(&base->cpu_base->softirq_expiry_lock);
 1419  	atomic_dec(&base->cpu_base->timer_waiters);
 1420  	spin_unlock_bh(&base->cpu_base->softirq_expiry_lock);
 1421  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_46

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.7）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】同一约定规则：公共代码调用、各架构各自实现的函数中，arm64、x86、RISC-V三个实现都调用了某个函数，LoongArch的实现没有。

【被标记的位置】arch/loongarch/kvm/vm.c中的kvm_vm_ioctl_check_extension

【程序给出的理由】all three references call ['min_t'], loongarch does not

【kvm_vm_ioctl_check_extension的代码】
```c
   58  int kvm_vm_ioctl_check_extension(struct kvm *kvm, long ext)  {
   59  	int r;
   60  
   61  	switch (ext) {
   62  	case KVM_CAP_ONE_REG:
   63  	case KVM_CAP_ENABLE_CAP:
   64  	case KVM_CAP_READONLY_MEM:
   65  	case KVM_CAP_SYNC_MMU:
   66  	case KVM_CAP_IMMEDIATE_EXIT:
   67  	case KVM_CAP_IOEVENTFD:
   68  	case KVM_CAP_MP_STATE:
   69  		r = 1;
   70  		break;
   71  	case KVM_CAP_NR_VCPUS:
   72  		r = num_online_cpus();
   73  		break;
   74  	case KVM_CAP_MAX_VCPUS:
   75  		r = KVM_MAX_VCPUS;
   76  		break;
   77  	case KVM_CAP_MAX_VCPU_ID:
   78  		r = KVM_MAX_VCPU_IDS;
   79  		break;
   80  	case KVM_CAP_NR_MEMSLOTS:
   81  		r = KVM_USER_MEM_SLOTS;
   82  		break;
   83  	default:
   84  		r = 0;
   85  		break;
   86  	}
   87  
   88  	return r;
   89  }
```

【参照：arm64的kvm_vm_ioctl_check_extension（arch/arm64/kvm/arm.c）】
```c
  217  int kvm_vm_ioctl_check_extension(struct kvm *kvm, long ext)  {
  218  	int r;
  219  	switch (ext) {
  220  	case KVM_CAP_IRQCHIP:
  221  		r = vgic_present;
  222  		break;
  223  	case KVM_CAP_IOEVENTFD:
  224  	case KVM_CAP_DEVICE_CTRL:
  225  	case KVM_CAP_USER_MEMORY:
  226  	case KVM_CAP_SYNC_MMU:
  227  	case KVM_CAP_DESTROY_MEMORY_REGION_WORKS:
  228  	case KVM_CAP_ONE_REG:
  229  	case KVM_CAP_ARM_PSCI:
  230  	case KVM_CAP_ARM_PSCI_0_2:
  231  	case KVM_CAP_READONLY_MEM:
  232  	case KVM_CAP_MP_STATE:
  233  	case KVM_CAP_IMMEDIATE_EXIT:
  234  	case KVM_CAP_VCPU_EVENTS:
  235  	case KVM_CAP_ARM_IRQ_LINE_LAYOUT_2:
  236  	case KVM_CAP_ARM_NISV_TO_USER:
  237  	case KVM_CAP_ARM_INJECT_EXT_DABT:
  238  	case KVM_CAP_SET_GUEST_DEBUG:
  239  	case KVM_CAP_VCPU_ATTRIBUTES:
  240  	case KVM_CAP_PTP_KVM:
  241  	case KVM_CAP_ARM_SYSTEM_SUSPEND:
  242  	case KVM_CAP_IRQFD_RESAMPLE:
  243  	case KVM_CAP_COUNTER_OFFSET:
  244  		r = 1;
  245  		break;
  246  	case KVM_CAP_SET_GUEST_DEBUG2:
  247  		return KVM_GUESTDBG_VALID_MASK;
  248  	case KVM_CAP_ARM_SET_DEVICE_ADDR:
  249  		r = 1;
  250  		break;
  251  	case KVM_CAP_NR_VCPUS:
  252  		/*
  253  		 * ARM64 treats KVM_CAP_NR_CPUS differently from all other
  254  		 * architectures, as it does not always bound it to
  255  		 * KVM_CAP_MAX_VCPUS. It should not matter much because
  256  		 * this is just an advisory value.
  257  		 */
  258  		r = min_t(unsigned int, num_online_cpus(),
  259  			  kvm_arm_default_max_vcpus());
  260  		break;
  261  	case KVM_CAP_MAX_VCPUS:
  262  	case KVM_CAP_MAX_VCPU_ID:
  263  		if (kvm)
  264  			r = kvm->max_vcpus;
  265  		else
  266  			r = kvm_arm_default_max_vcpus();
...（其余63行省略）
```

【参照：x86的kvm_vm_ioctl_check_extension（arch/x86/kvm/x86.c）】
```c
 4552  int kvm_vm_ioctl_check_extension(struct kvm *kvm, long ext)  {
 4553  	int r = 0;
 4554  
 4555  	switch (ext) {
 4556  	case KVM_CAP_IRQCHIP:
 4557  	case KVM_CAP_HLT:
 4558  	case KVM_CAP_MMU_SHADOW_CACHE_CONTROL:
 4559  	case KVM_CAP_SET_TSS_ADDR:
 4560  	case KVM_CAP_EXT_CPUID:
 4561  	case KVM_CAP_EXT_EMUL_CPUID:
 4562  	case KVM_CAP_CLOCKSOURCE:
 4563  	case KVM_CAP_PIT:
 4564  	case KVM_CAP_NOP_IO_DELAY:
 4565  	case KVM_CAP_MP_STATE:
 4566  	case KVM_CAP_SYNC_MMU:
 4567  	case KVM_CAP_USER_NMI:
 4568  	case KVM_CAP_REINJECT_CONTROL:
 4569  	case KVM_CAP_IRQ_INJECT_STATUS:
 4570  	case KVM_CAP_IOEVENTFD:
 4571  	case KVM_CAP_IOEVENTFD_NO_LENGTH:
 4572  	case KVM_CAP_PIT2:
 4573  	case KVM_CAP_PIT_STATE2:
 4574  	case KVM_CAP_SET_IDENTITY_MAP_ADDR:
 4575  	case KVM_CAP_VCPU_EVENTS:
 4576  	case KVM_CAP_HYPERV:
 4577  	case KVM_CAP_HYPERV_VAPIC:
 4578  	case KVM_CAP_HYPERV_SPIN:
 4579  	case KVM_CAP_HYPERV_SYNIC:
 4580  	case KVM_CAP_HYPERV_SYNIC2:
 4581  	case KVM_CAP_HYPERV_VP_INDEX:
 4582  	case KVM_CAP_HYPERV_EVENTFD:
 4583  	case KVM_CAP_HYPERV_TLBFLUSH:
 4584  	case KVM_CAP_HYPERV_SEND_IPI:
 4585  	case KVM_CAP_HYPERV_CPUID:
 4586  	case KVM_CAP_HYPERV_ENFORCE_CPUID:
 4587  	case KVM_CAP_SYS_HYPERV_CPUID:
 4588  	case KVM_CAP_PCI_SEGMENT:
 4589  	case KVM_CAP_DEBUGREGS:
 4590  	case KVM_CAP_X86_ROBUST_SINGLESTEP:
 4591  	case KVM_CAP_XSAVE:
 4592  	case KVM_CAP_ASYNC_PF:
 4593  	case KVM_CAP_ASYNC_PF_INT:
 4594  	case KVM_CAP_GET_TSC_KHZ:
 4595  	case KVM_CAP_KVMCLOCK_CTRL:
 4596  	case KVM_CAP_READONLY_MEM:
 4597  	case KVM_CAP_HYPERV_TIME:
 4598  	case KVM_CAP_IOAPIC_POLARITY_IGNORED:
 4599  	case KVM_CAP_TSC_DEADLINE_TIMER:
 4600  	case KVM_CAP_DISABLE_QUIRKS:
 4601  	case KVM_CAP_SET_BOOT_CPU_ID:
...（其余144行省略）
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_47

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.8）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】同一约定规则：公共代码调用、各架构各自实现的函数中，arm64、x86、RISC-V三个实现都调用了某个函数，LoongArch的实现没有。

【被标记的位置】arch/loongarch/kvm/vcpu.c中的kvm_arch_vcpu_load

【程序给出的理由】all three references call ['kvm_make_request'], loongarch does not

【kvm_arch_vcpu_load的代码】
```c
 1035  void kvm_arch_vcpu_load(struct kvm_vcpu *vcpu, int cpu)  {
 1036  	unsigned long flags;
 1037  
 1038  	local_irq_save(flags);
 1039  	/* Restore guest state to registers */
 1040  	_kvm_vcpu_load(vcpu, cpu);
 1041  	local_irq_restore(flags);
 1042  }
```

【参照：arm64的kvm_arch_vcpu_load（arch/arm64/kvm/arm.c）】
```c
  427  void kvm_arch_vcpu_load(struct kvm_vcpu *vcpu, int cpu)  {
  428  	struct kvm_s2_mmu *mmu;
  429  	int *last_ran;
  430  
  431  	mmu = vcpu->arch.hw_mmu;
  432  	last_ran = this_cpu_ptr(mmu->last_vcpu_ran);
  433  
  434  	/*
  435  	 * We guarantee that both TLBs and I-cache are private to each
  436  	 * vcpu. If detecting that a vcpu from the same VM has
  437  	 * previously run on the same physical CPU, call into the
  438  	 * hypervisor code to nuke the relevant contexts.
  439  	 *
  440  	 * We might get preempted before the vCPU actually runs, but
  441  	 * over-invalidation doesn't affect correctness.
  442  	 */
  443  	if (*last_ran != vcpu->vcpu_idx) {
  444  		kvm_call_hyp(__kvm_flush_cpu_context, mmu);
  445  		*last_ran = vcpu->vcpu_idx;
  446  	}
  447  
  448  	vcpu->cpu = cpu;
  449  
  450  	kvm_vgic_load(vcpu);
  451  	kvm_timer_vcpu_load(vcpu);
  452  	if (has_vhe())
  453  		kvm_vcpu_load_vhe(vcpu);
  454  	kvm_arch_vcpu_load_fp(vcpu);
  455  	kvm_vcpu_pmu_restore_guest(vcpu);
  456  	if (kvm_arm_is_pvtime_enabled(&vcpu->arch))
  457  		kvm_make_request(KVM_REQ_RECORD_STEAL, vcpu);
  458  
  459  	if (single_task_running())
  460  		vcpu_clear_wfx_traps(vcpu);
  461  	else
  462  		vcpu_set_wfx_traps(vcpu);
  463  
  464  	if (vcpu_has_ptrauth(vcpu))
  465  		vcpu_ptrauth_disable(vcpu);
  466  	kvm_arch_vcpu_load_debug_state_flags(vcpu);
  467  
  468  	if (!cpumask_test_cpu(cpu, vcpu->kvm->arch.supported_cpus))
  469  		vcpu_set_on_unsupported_cpu(vcpu);
  470  }
```

【参照：x86的kvm_arch_vcpu_load（arch/x86/kvm/x86.c）】
```c
 4960  void kvm_arch_vcpu_load(struct kvm_vcpu *vcpu, int cpu)  {
 4961  	/* Address WBINVD may be executed by guest */
 4962  	if (need_emulate_wbinvd(vcpu)) {
 4963  		if (static_call(kvm_x86_has_wbinvd_exit)())
 4964  			cpumask_set_cpu(cpu, vcpu->arch.wbinvd_dirty_mask);
 4965  		else if (vcpu->cpu != -1 && vcpu->cpu != cpu)
 4966  			smp_call_function_single(vcpu->cpu,
 4967  					wbinvd_ipi, NULL, 1);
 4968  	}
 4969  
 4970  	static_call(kvm_x86_vcpu_load)(vcpu, cpu);
 4971  
 4972  	/* Save host pkru register if supported */
 4973  	vcpu->arch.host_pkru = read_pkru();
 4974  
 4975  	/* Apply any externally detected TSC adjustments (due to suspend) */
 4976  	if (unlikely(vcpu->arch.tsc_offset_adjustment)) {
 4977  		adjust_tsc_offset_host(vcpu, vcpu->arch.tsc_offset_adjustment);
 4978  		vcpu->arch.tsc_offset_adjustment = 0;
 4979  		kvm_make_request(KVM_REQ_CLOCK_UPDATE, vcpu);
 4980  	}
 4981  
 4982  	if (unlikely(vcpu->cpu != cpu) || kvm_check_tsc_unstable()) {
 4983  		s64 tsc_delta = !vcpu->arch.last_host_tsc ? 0 :
 4984  				rdtsc() - vcpu->arch.last_host_tsc;
 4985  		if (tsc_delta < 0)
 4986  			mark_tsc_unstable("KVM discovered backwards TSC");
 4987  
 4988  		if (kvm_check_tsc_unstable()) {
 4989  			u64 offset = kvm_compute_l1_tsc_offset(vcpu,
 4990  						vcpu->arch.last_guest_tsc);
 4991  			kvm_vcpu_write_tsc_offset(vcpu, offset);
 4992  			vcpu->arch.tsc_catchup = 1;
 4993  		}
 4994  
 4995  		if (kvm_lapic_hv_timer_in_use(vcpu))
 4996  			kvm_lapic_restart_hv_timer(vcpu);
 4997  
 4998  		/*
 4999  		 * On a host with synchronized TSC, there is no need to update
 5000  		 * kvmclock on vcpu->cpu migration
 5001  		 */
 5002  		if (!vcpu->kvm->arch.use_master_clock || vcpu->cpu == -1)
 5003  			kvm_make_request(KVM_REQ_GLOBAL_CLOCK_UPDATE, vcpu);
 5004  		if (vcpu->cpu != cpu)
 5005  			kvm_make_request(KVM_REQ_MIGRATE_TIMER, vcpu);
 5006  		vcpu->cpu = cpu;
 5007  	}
 5008  
 5009  	kvm_make_request(KVM_REQ_STEAL_UPDATE, vcpu);
...（其余1行省略）
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_48

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.9）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】同一约定规则：公共代码调用、各架构各自实现的函数中，arm64、x86、RISC-V三个实现都调用了某个函数，LoongArch的实现没有。

【被标记的位置】arch/loongarch/net/bpf_jit.c中的bpf_int_jit_compile

【程序给出的理由】all three references call ['WARN_ON', 'bpf_arch_text_copy', 'bpf_jit_binary_pack_finalize', 'bpf_jit_binary_pack_free'], loongarch does not

【bpf_int_jit_compile的代码】
```c
 1182  struct bpf_prog *bpf_int_jit_compile(struct bpf_prog *prog)  {
 1183  	bool tmp_blinded = false, extra_pass = false;
 1184  	u8 *image_ptr;
 1185  	int image_size, prog_size, extable_size;
 1186  	struct jit_ctx ctx;
 1187  	struct jit_data *jit_data;
 1188  	struct bpf_binary_header *header;
 1189  	struct bpf_prog *tmp, *orig_prog = prog;
 1190  
 1191  	/*
 1192  	 * If BPF JIT was not enabled then we must fall back to
 1193  	 * the interpreter.
 1194  	 */
 1195  	if (!prog->jit_requested)
 1196  		return orig_prog;
 1197  
 1198  	tmp = bpf_jit_blind_constants(prog);
 1199  	/*
 1200  	 * If blinding was requested and we failed during blinding,
 1201  	 * we must fall back to the interpreter. Otherwise, we save
 1202  	 * the new JITed code.
 1203  	 */
 1204  	if (IS_ERR(tmp))
 1205  		return orig_prog;
 1206  
 1207  	if (tmp != prog) {
 1208  		tmp_blinded = true;
 1209  		prog = tmp;
 1210  	}
 1211  
 1212  	jit_data = prog->aux->jit_data;
 1213  	if (!jit_data) {
 1214  		jit_data = kzalloc(sizeof(*jit_data), GFP_KERNEL);
 1215  		if (!jit_data) {
 1216  			prog = orig_prog;
 1217  			goto out;
 1218  		}
 1219  		prog->aux->jit_data = jit_data;
 1220  	}
 1221  	if (jit_data->ctx.offset) {
 1222  		ctx = jit_data->ctx;
 1223  		image_ptr = jit_data->image;
 1224  		header = jit_data->header;
 1225  		extra_pass = true;
 1226  		prog_size = sizeof(u32) * ctx.idx;
 1227  		goto skip_init_ctx;
 1228  	}
 1229  
 1230  	memset(&ctx, 0, sizeof(ctx));
 1231  	ctx.prog = prog;
 1232  
 1233  	ctx.offset = kvcalloc(prog->len + 1, sizeof(u32), GFP_KERNEL);
 1234  	if (ctx.offset == NULL) {
 1235  		prog = orig_prog;
 1236  		goto out_offset;
 1237  	}
 1238  
 1239  	/* 1. Initial fake pass to compute ctx->idx and set ctx->flags */
 1240  	build_prologue(&ctx);
 1241  	if (build_body(&ctx, extra_pass)) {
 1242  		prog = orig_prog;
 1243  		goto out_offset;
 1244  	}
 1245  	ctx.epilogue_offset = ctx.idx;
 1246  	build_epilogue(&ctx);
 1247  
 1248  	extable_size = prog->aux->num_exentries * sizeof(struct exception_table_entry);
 1249  
 1250  	/* Now we know the actual image size.
 1251  	 * As each LoongArch instruction is of length 32bit,
 1252  	 * we are translating number of JITed intructions into
 1253  	 * the size required to store these JITed code.
 1254  	 */
 1255  	prog_size = sizeof(u32) * ctx.idx;
 1256  	image_size = prog_size + extable_size;
 1257  	/* Now we know the size of the structure to make */
 1258  	header = bpf_jit_binary_alloc(image_size, &image_ptr,
 1259  				      sizeof(u32), jit_fill_hole);
 1260  	if (header == NULL) {
 1261  		prog = orig_prog;
...（其余76行省略）
```

【参照：arm64的bpf_int_jit_compile（arch/arm64/net/bpf_jit_comp.c）】
```c
 1587  struct bpf_prog *bpf_int_jit_compile(struct bpf_prog *prog)  {
 1588  	int image_size, prog_size, extable_size, extable_align, extable_offset;
 1589  	struct bpf_prog *tmp, *orig_prog = prog;
 1590  	struct bpf_binary_header *header;
 1591  	struct bpf_binary_header *ro_header;
 1592  	struct arm64_jit_data *jit_data;
 1593  	bool was_classic = bpf_prog_was_classic(prog);
 1594  	bool tmp_blinded = false;
 1595  	bool extra_pass = false;
 1596  	struct jit_ctx ctx;
 1597  	u8 *image_ptr;
 1598  	u8 *ro_image_ptr;
 1599  
 1600  	if (!prog->jit_requested)
 1601  		return orig_prog;
 1602  
 1603  	tmp = bpf_jit_blind_constants(prog);
 1604  	/* If blinding was requested and we failed during blinding,
 1605  	 * we must fall back to the interpreter.
 1606  	 */
 1607  	if (IS_ERR(tmp))
 1608  		return orig_prog;
 1609  	if (tmp != prog) {
 1610  		tmp_blinded = true;
 1611  		prog = tmp;
 1612  	}
 1613  
 1614  	jit_data = prog->aux->jit_data;
 1615  	if (!jit_data) {
 1616  		jit_data = kzalloc(sizeof(*jit_data), GFP_KERNEL);
 1617  		if (!jit_data) {
 1618  			prog = orig_prog;
 1619  			goto out;
 1620  		}
 1621  		prog->aux->jit_data = jit_data;
 1622  	}
 1623  	if (jit_data->ctx.offset) {
 1624  		ctx = jit_data->ctx;
 1625  		ro_image_ptr = jit_data->ro_image;
 1626  		ro_header = jit_data->ro_header;
 1627  		header = jit_data->header;
 1628  		image_ptr = (void *)header + ((void *)ro_image_ptr
 1629  						 - (void *)ro_header);
 1630  		extra_pass = true;
 1631  		prog_size = sizeof(u32) * ctx.idx;
 1632  		goto skip_init_ctx;
 1633  	}
 1634  	memset(&ctx, 0, sizeof(ctx));
 1635  	ctx.prog = prog;
 1636  
...（其余141行省略）
```

【参照：x86的bpf_int_jit_compile（arch/x86/net/bpf_jit_comp.c）】
```c
 3159  struct bpf_prog *bpf_int_jit_compile(struct bpf_prog *prog)  {
 3160  	struct bpf_binary_header *rw_header = NULL;
 3161  	struct bpf_binary_header *header = NULL;
 3162  	struct bpf_prog *tmp, *orig_prog = prog;
 3163  	struct x64_jit_data *jit_data;
 3164  	int proglen, oldproglen = 0;
 3165  	struct jit_context ctx = {};
 3166  	bool tmp_blinded = false;
 3167  	bool extra_pass = false;
 3168  	bool padding = false;
 3169  	u8 *rw_image = NULL;
 3170  	u8 *image = NULL;
 3171  	int *addrs;
 3172  	int pass;
 3173  	int i;
 3174  
 3175  	if (!prog->jit_requested)
 3176  		return orig_prog;
 3177  
 3178  	tmp = bpf_jit_blind_constants(prog);
 3179  	/*
 3180  	 * If blinding was requested and we failed during blinding,
 3181  	 * we must fall back to the interpreter.
 3182  	 */
 3183  	if (IS_ERR(tmp))
 3184  		return orig_prog;
 3185  	if (tmp != prog) {
 3186  		tmp_blinded = true;
 3187  		prog = tmp;
 3188  	}
 3189  
 3190  	jit_data = prog->aux->jit_data;
 3191  	if (!jit_data) {
 3192  		jit_data = kzalloc(sizeof(*jit_data), GFP_KERNEL);
 3193  		if (!jit_data) {
 3194  			prog = orig_prog;
 3195  			goto out;
 3196  		}
 3197  		prog->aux->jit_data = jit_data;
 3198  	}
 3199  	addrs = jit_data->addrs;
 3200  	if (addrs) {
 3201  		ctx = jit_data->ctx;
 3202  		oldproglen = jit_data->proglen;
 3203  		image = jit_data->image;
 3204  		header = jit_data->header;
 3205  		rw_header = jit_data->rw_header;
 3206  		rw_image = (void *)rw_header + ((void *)image - (void *)header);
 3207  		extra_pass = true;
 3208  		padding = true;
...（其余134行省略）
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_49

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.10）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】推测执行越界规则：函数对一个可能来自客体（虚拟机）或用户的下标做了上界检查，随后用它访问数组，却没有用array_index_nospec，可能被推测执行越界利用（Spectre-v1）。

【被标记的位置】arch/loongarch/kvm/vcpu.c中的kvm_get_vcpu_by_cpuid

【程序给出的理由】line 342: [cpuid] after bound check at line 338, no array_index_nospec; line 345: [cpuid] after bound check at line 338, no array_index_nospec

【kvm_get_vcpu_by_cpuid的代码】
```c
  335  struct kvm_vcpu *kvm_get_vcpu_by_cpuid(struct kvm *kvm, int cpuid)  {
  336  	struct kvm_phyid_map *map;
  337  
  338  	if (cpuid >= KVM_MAX_PHYID)
  339  		return NULL;
  340  
  341  	map = kvm->arch.phyid_map;
  342  	if (!map->phys_map[cpuid].enabled)
  343  		return NULL;
  344  
  345  	return map->phys_map[cpuid].vcpu;
  346  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_50

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.10）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】推测执行越界规则：函数对一个可能来自客体（虚拟机）或用户的下标做了上界检查，随后用它访问数组，却没有用array_index_nospec，可能被推测执行越界利用（Spectre-v1）。

【被标记的位置】arch/loongarch/kvm/vcpu.c中的kvm_set_cpuid

【程序给出的理由】line 290: [val] after bound check at line 268, no array_index_nospec; line 292: [val] after bound check at line 268, no array_index_nospec; line 306: [val] after bound check at line 268, no array_index_nospec

【kvm_set_cpuid的代码】
```c
  263  static inline int kvm_set_cpuid(struct kvm_vcpu *vcpu, u64 val)  {
  264  	int cpuid;
  265  	struct kvm_phyid_map *map;
  266  	struct loongarch_csrs *csr = vcpu->arch.csr;
  267  
  268  	if (val >= KVM_MAX_PHYID)
  269  		return -EINVAL;
  270  
  271  	map = vcpu->kvm->arch.phyid_map;
  272  	cpuid = kvm_read_sw_gcsr(csr, LOONGARCH_CSR_CPUID);
  273  
  274  	spin_lock(&vcpu->kvm->arch.phyid_map_lock);
  275  	if ((cpuid < KVM_MAX_PHYID) && map->phys_map[cpuid].enabled) {
  276  		/* Discard duplicated CPUID set operation */
  277  		if (cpuid == val) {
  278  			spin_unlock(&vcpu->kvm->arch.phyid_map_lock);
  279  			return 0;
  280  		}
  281  
  282  		/*
  283  		 * CPUID is already set before
  284  		 * Forbid changing to a different CPUID at runtime
  285  		 */
  286  		spin_unlock(&vcpu->kvm->arch.phyid_map_lock);
  287  		return -EINVAL;
  288  	}
  289  
  290  	if (map->phys_map[val].enabled) {
  291  		/* Discard duplicated CPUID set operation */
  292  		if (vcpu == map->phys_map[val].vcpu) {
  293  			spin_unlock(&vcpu->kvm->arch.phyid_map_lock);
  294  			return 0;
  295  		}
  296  
  297  		/*
  298  		 * New CPUID is already set with other vcpu
  299  		 * Forbid sharing the same CPUID between different vcpus
  300  		 */
  301  		spin_unlock(&vcpu->kvm->arch.phyid_map_lock);
  302  		return -EINVAL;
  303  	}
  304  
  305  	kvm_write_sw_gcsr(csr, LOONGARCH_CSR_CPUID, val);
  306  	map->phys_map[val].enabled	= true;
  307  	map->phys_map[val].vcpu		= vcpu;
  308  	spin_unlock(&vcpu->kvm->arch.phyid_map_lock);
  309  
  310  	return 0;
  311  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_51

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.13）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kvm/intc/eiointc.c中的kvm_eiointc_ctrl_access

【程序给出的理由】sleep A:spin: line 798 copy_from_user -> copy_from_user

【kvm_eiointc_ctrl_access的代码】
```c
  786  static int kvm_eiointc_ctrl_access(struct kvm_device *dev, 					struct kvm_device_attr *attr)  {
  787  	int ret = 0;
  788  	unsigned long flags;
  789  	unsigned long type = (unsigned long)attr->attr;
  790  	u32 i, start_irq;
  791  	void __user *data;
  792  	struct loongarch_eiointc *s = dev->kvm->arch.eiointc;
  793  
  794  	data = (void __user *)attr->addr;
  795  	spin_lock_irqsave(&s->lock, flags);
  796  	switch (type) {
  797  	case KVM_DEV_LOONGARCH_EXTIOI_CTRL_INIT_NUM_CPU:
  798  		if (copy_from_user(&s->num_cpu, data, 4))
  799  			ret = -EFAULT;
  800  		break;
  801  	case KVM_DEV_LOONGARCH_EXTIOI_CTRL_INIT_FEATURE:
  802  		if (copy_from_user(&s->features, data, 4))
  803  			ret = -EFAULT;
  804  		if (!(s->features & BIT(EIOINTC_HAS_VIRT_EXTENSION)))
  805  			s->status |= BIT(EIOINTC_ENABLE);
  806  		break;
  807  	case KVM_DEV_LOONGARCH_EXTIOI_CTRL_LOAD_FINISHED:
  808  		eiointc_set_sw_coreisr(s);
  809  		for (i = 0; i < (EIOINTC_IRQS / 4); i++) {
  810  			start_irq = i * 4;
  811  			eiointc_update_sw_coremap(s, start_irq,
  812  					(void *)&s->coremap.reg_u32[i], sizeof(u32), false);
  813  		}
  814  		break;
  815  	default:
  816  		break;
  817  	}
  818  	spin_unlock_irqrestore(&s->lock, flags);
  819  
  820  	return ret;
  821  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_52

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.13）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kvm/intc/eiointc.c中的kvm_eiointc_regs_access

【程序给出的理由】sleep A:spin: line 874 copy_from_user -> copy_from_user

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

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_53

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.13）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kvm/intc/eiointc.c中的kvm_eiointc_sw_status_access

【程序给出的理由】sleep A:spin: line 916 copy_from_user -> copy_from_user

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

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_54

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.13）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kvm/intc/pch_pic.c中的kvm_pch_pic_regs_access

【程序给出的理由】sleep A:spin: line 393 copy_from_user -> copy_from_user

【kvm_pch_pic_regs_access的代码】
```c
  340  static int kvm_pch_pic_regs_access(struct kvm_device *dev, 				struct kvm_device_attr *attr, 				bool is_write)  {
  341  	int addr, offset, len = 8, ret = 0;
  342  	void __user *data;
  343  	void *p = NULL;
  344  	struct loongarch_pch_pic *s;
  345  
  346  	s = dev->kvm->arch.pch_pic;
  347  	addr = attr->attr;
  348  	data = (void __user *)attr->addr;
  349  
  350  	/* get pointer to pch pic register by addr */
  351  	switch (addr) {
  352  	case PCH_PIC_MASK_START:
  353  		p = &s->mask;
  354  		break;
  355  	case PCH_PIC_HTMSI_EN_START:
  356  		p = &s->htmsi_en;
  357  		break;
  358  	case PCH_PIC_EDGE_START:
  359  		p = &s->edge;
  360  		break;
  361  	case PCH_PIC_AUTO_CTRL0_START:
  362  		p = &s->auto_ctrl0;
  363  		break;
  364  	case PCH_PIC_AUTO_CTRL1_START:
  365  		p = &s->auto_ctrl1;
  366  		break;
  367  	case PCH_PIC_ROUTE_ENTRY_START ... PCH_PIC_ROUTE_ENTRY_END:
  368  		offset = addr - PCH_PIC_ROUTE_ENTRY_START;
  369  		p = &s->route_entry[offset];
  370  		len = 1;
  371  		break;
  372  	case PCH_PIC_HTMSI_VEC_START ... PCH_PIC_HTMSI_VEC_END:
  373  		offset = addr - PCH_PIC_HTMSI_VEC_START;
  374  		p = &s->htmsi_vector[offset];
  375  		len = 1;
  376  		break;
  377  	case PCH_PIC_INT_IRR_START:
  378  		p = &s->irr;
  379  		break;
  380  	case PCH_PIC_INT_ISR_START:
  381  		p = &s->isr;
  382  		break;
  383  	case PCH_PIC_POLARITY_START:
  384  		p = &s->polarity;
  385  		break;
  386  	default:
  387  		return -EINVAL;
  388  	}
  389  
  390  	spin_lock(&s->lock);
  391  	/* write or read value according to is_write */
  392  	if (is_write) {
  393  		if (copy_from_user(p, data, len))
  394  			ret = -EFAULT;
  395  	} else {
  396  		if (copy_to_user(data, p, len))
  397  			ret = -EFAULT;
  398  	}
  399  	spin_unlock(&s->lock);
  400  
  401  	return ret;
  402  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_55

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.13）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kvm/intc/pch_pic.c中的kvm_pch_pic_regs_access

【程序给出的理由】sleep A:spin: line 396 copy_to_user -> copy_to_user

【kvm_pch_pic_regs_access的代码】
```c
  340  static int kvm_pch_pic_regs_access(struct kvm_device *dev, 				struct kvm_device_attr *attr, 				bool is_write)  {
  341  	int addr, offset, len = 8, ret = 0;
  342  	void __user *data;
  343  	void *p = NULL;
  344  	struct loongarch_pch_pic *s;
  345  
  346  	s = dev->kvm->arch.pch_pic;
  347  	addr = attr->attr;
  348  	data = (void __user *)attr->addr;
  349  
  350  	/* get pointer to pch pic register by addr */
  351  	switch (addr) {
  352  	case PCH_PIC_MASK_START:
  353  		p = &s->mask;
  354  		break;
  355  	case PCH_PIC_HTMSI_EN_START:
  356  		p = &s->htmsi_en;
  357  		break;
  358  	case PCH_PIC_EDGE_START:
  359  		p = &s->edge;
  360  		break;
  361  	case PCH_PIC_AUTO_CTRL0_START:
  362  		p = &s->auto_ctrl0;
  363  		break;
  364  	case PCH_PIC_AUTO_CTRL1_START:
  365  		p = &s->auto_ctrl1;
  366  		break;
  367  	case PCH_PIC_ROUTE_ENTRY_START ... PCH_PIC_ROUTE_ENTRY_END:
  368  		offset = addr - PCH_PIC_ROUTE_ENTRY_START;
  369  		p = &s->route_entry[offset];
  370  		len = 1;
  371  		break;
  372  	case PCH_PIC_HTMSI_VEC_START ... PCH_PIC_HTMSI_VEC_END:
  373  		offset = addr - PCH_PIC_HTMSI_VEC_START;
  374  		p = &s->htmsi_vector[offset];
  375  		len = 1;
  376  		break;
  377  	case PCH_PIC_INT_IRR_START:
  378  		p = &s->irr;
  379  		break;
  380  	case PCH_PIC_INT_ISR_START:
  381  		p = &s->isr;
  382  		break;
  383  	case PCH_PIC_POLARITY_START:
  384  		p = &s->polarity;
  385  		break;
  386  	default:
  387  		return -EINVAL;
  388  	}
  389  
  390  	spin_lock(&s->lock);
  391  	/* write or read value according to is_write */
  392  	if (is_write) {
  393  		if (copy_from_user(p, data, len))
  394  			ret = -EFAULT;
  395  	} else {
  396  		if (copy_to_user(data, p, len))
  397  			ret = -EFAULT;
  398  	}
  399  	spin_unlock(&s->lock);
  400  
  401  	return ret;
  402  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_56

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.13）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】同一约定规则：公共代码调用、各架构各自实现的函数中，arm64、x86、RISC-V三个实现都调用了某个函数，LoongArch的实现没有。

【被标记的位置】arch/loongarch/kvm/vm.c中的kvm_vm_ioctl_irq_line

【程序给出的理由】all three references call ['irqchip_in_kernel'], loongarch does not

【kvm_vm_ioctl_irq_line的代码】
```c
  180  int kvm_vm_ioctl_irq_line(struct kvm *kvm, struct kvm_irq_level *irq_event, bool line_status)  {
  181  	if (!kvm_arch_irqchip_in_kernel(kvm))
  182  		return -ENXIO;
  183  
  184  	irq_event->status = kvm_set_irq(kvm, KVM_USERSPACE_IRQ_SOURCE_ID,
  185  					irq_event->irq, irq_event->level, line_status);
  186  
  187  	return 0;
  188  }
```

【参照：arm64的kvm_vm_ioctl_irq_line（arch/arm64/kvm/arm.c）】
```c
 1342  int kvm_vm_ioctl_irq_line(struct kvm *kvm, struct kvm_irq_level *irq_level, 			  bool line_status)  {
 1343  	u32 irq = irq_level->irq;
 1344  	unsigned int irq_type, vcpu_id, irq_num;
 1345  	struct kvm_vcpu *vcpu = NULL;
 1346  	bool level = irq_level->level;
 1347  
 1348  	irq_type = (irq >> KVM_ARM_IRQ_TYPE_SHIFT) & KVM_ARM_IRQ_TYPE_MASK;
 1349  	vcpu_id = (irq >> KVM_ARM_IRQ_VCPU_SHIFT) & KVM_ARM_IRQ_VCPU_MASK;
 1350  	vcpu_id += ((irq >> KVM_ARM_IRQ_VCPU2_SHIFT) & KVM_ARM_IRQ_VCPU2_MASK) * (KVM_ARM_IRQ_VCPU_MASK + 1);
 1351  	irq_num = (irq >> KVM_ARM_IRQ_NUM_SHIFT) & KVM_ARM_IRQ_NUM_MASK;
 1352  
 1353  	trace_kvm_irq_line(irq_type, vcpu_id, irq_num, irq_level->level);
 1354  
 1355  	switch (irq_type) {
 1356  	case KVM_ARM_IRQ_TYPE_CPU:
 1357  		if (irqchip_in_kernel(kvm))
 1358  			return -ENXIO;
 1359  
 1360  		vcpu = kvm_get_vcpu_by_id(kvm, vcpu_id);
 1361  		if (!vcpu)
 1362  			return -EINVAL;
 1363  
 1364  		if (irq_num > KVM_ARM_IRQ_CPU_FIQ)
 1365  			return -EINVAL;
 1366  
 1367  		return vcpu_interrupt_line(vcpu, irq_num, level);
 1368  	case KVM_ARM_IRQ_TYPE_PPI:
 1369  		if (!irqchip_in_kernel(kvm))
 1370  			return -ENXIO;
 1371  
 1372  		vcpu = kvm_get_vcpu_by_id(kvm, vcpu_id);
 1373  		if (!vcpu)
 1374  			return -EINVAL;
 1375  
 1376  		if (irq_num < VGIC_NR_SGIS || irq_num >= VGIC_NR_PRIVATE_IRQS)
 1377  			return -EINVAL;
 1378  
 1379  		return kvm_vgic_inject_irq(kvm, vcpu, irq_num, level, NULL);
 1380  	case KVM_ARM_IRQ_TYPE_SPI:
 1381  		if (!irqchip_in_kernel(kvm))
 1382  			return -ENXIO;
 1383  
 1384  		if (irq_num < VGIC_NR_PRIVATE_IRQS)
 1385  			return -EINVAL;
 1386  
 1387  		return kvm_vgic_inject_irq(kvm, NULL, irq_num, level, NULL);
 1388  	}
 1389  
 1390  	return -EINVAL;
 1391  }
```

【参照：x86的kvm_vm_ioctl_irq_line（arch/x86/kvm/x86.c）】
```c
 6483  int kvm_vm_ioctl_irq_line(struct kvm *kvm, struct kvm_irq_level *irq_event, 			bool line_status)  {
 6484  	if (!irqchip_in_kernel(kvm))
 6485  		return -ENXIO;
 6486  
 6487  	irq_event->status = kvm_set_irq(kvm, KVM_USERSPACE_IRQ_SOURCE_ID,
 6488  					irq_event->irq, irq_event->level,
 6489  					line_status);
 6490  	return 0;
 6491  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_57

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.14）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】同一约定规则：公共代码调用、各架构各自实现的函数中，arm64、x86、RISC-V三个实现都调用了某个函数，LoongArch的实现没有。

【被标记的位置】arch/loongarch/kernel/smp.c中的hibernate_resume_nonboot_cpu_disable

【程序给出的理由】all three references call ['freeze_secondary_cpus'], loongarch does not

【hibernate_resume_nonboot_cpu_disable的代码】
```c
  484  int hibernate_resume_nonboot_cpu_disable(void)  {
  485  	int ret;
  486  
  487  	play_dead = poll_play_dead;
  488  	ret = suspend_disable_secondary_cpus();
  489  	play_dead = idle_play_dead;
  490  
  491  	return ret;
  492  }
```

【参照：arm64的hibernate_resume_nonboot_cpu_disable（arch/arm64/kernel/hibernate.c）】
```c
  476  int hibernate_resume_nonboot_cpu_disable(void)  {
  477  	if (sleep_cpu < 0) {
  478  		pr_err("Failing to resume from hibernate on an unknown CPU.\n");
  479  		return -ENODEV;
  480  	}
  481  
  482  	return freeze_secondary_cpus(sleep_cpu);
  483  }
```

【参照：x86的hibernate_resume_nonboot_cpu_disable（arch/x86/power/cpu.c）】
```c
  299  int hibernate_resume_nonboot_cpu_disable(void)  {
  300  	void (*play_dead)(void) = smp_ops.play_dead;
  301  	int ret;
  302  
  303  	/*
  304  	 * Ensure that MONITOR/MWAIT will not be used in the "play dead" loop
  305  	 * during hibernate image restoration, because it is likely that the
  306  	 * monitored address will be actually written to at that time and then
  307  	 * the "dead" CPU will attempt to execute instructions again, but the
  308  	 * address in its instruction pointer may not be possible to resolve
  309  	 * any more at that point (the page tables used by it previously may
  310  	 * have been overwritten by hibernate image data).
  311  	 *
  312  	 * First, make sure that we wake up all the potentially disabled SMT
  313  	 * threads which have been initially brought up and then put into
  314  	 * mwait/cpuidle sleep.
  315  	 * Those will be put to proper (not interfering with hibernation
  316  	 * resume) sleep afterwards, and the resumed kernel will decide itself
  317  	 * what to do with them.
  318  	 */
  319  	ret = cpuhp_smt_enable();
  320  	if (ret)
  321  		return ret;
  322  	smp_ops.play_dead = resume_play_dead;
  323  	ret = freeze_secondary_cpus(0);
  324  	smp_ops.play_dead = play_dead;
  325  	return ret;
  326  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_58

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.16）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】同一约定规则：公共代码调用、各架构各自实现的函数中，arm64、x86、RISC-V三个实现都调用了某个函数，LoongArch的实现没有。

【被标记的位置】arch/loongarch/kernel/proc.c中的c_start

【程序给出的理由】all three references call ['cpumask_next'], loongarch does not

【c_start的代码】
```c
   90  static void *c_start(struct seq_file *m, loff_t *pos)  {
   91  	unsigned long i = *pos;
   92  
   93  	return i < nr_cpu_ids ? (void *)(i + 1) : NULL;
   94  }
```

【参照：arm64的c_start（arch/arm64/kernel/cpuinfo.c）】
```c
  276  static void *c_start(struct seq_file *m, loff_t *pos)  {
  277  	*pos = cpumask_next(*pos - 1, cpu_online_mask);
  278  	return *pos < nr_cpu_ids ? &per_cpu(cpu_data, *pos) : NULL;
  279  }
```

【参照：x86的c_start（arch/x86/kernel/cpu/proc.c）】
```c
  160  static void *c_start(struct seq_file *m, loff_t *pos)  {
  161  	*pos = cpumask_next(*pos - 1, cpu_online_mask);
  162  	if ((*pos) < nr_cpu_ids)
  163  		return &cpu_data(*pos);
  164  	return NULL;
  165  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

## C0_59

你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本v6.19）的LoongArch代码中标出的问题。请判断它在这个版本中是不是真问题。

【规则】执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的LoongArch钩子）调用了可能睡眠的操作；或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。

【被标记的位置】arch/loongarch/kernel/traps.c中的do_ade

【程序给出的理由】noinstr N2: line 540 fixup_exception -> instrumentable callee

【调用链】fixup_exception（arch/loongarch/mm/extable.c第46行调用）

【do_ade的代码】
```c
  536  asmlinkage void noinstr do_ade(struct pt_regs *regs)  {
  537  	irqentry_state_t state = irqentry_enter(regs);
  538  	unsigned int esubcode = FIELD_GET(CSR_ESTAT_ESUBCODE, regs->csr_estat);
  539  
  540  	if ((esubcode == EXSUBCODE_ADEM) && fixup_exception(regs))
  541  		goto out;
  542  
  543  	die_if_kernel("Kernel ade access", regs);
  544  	force_sig_fault(SIGBUS, BUS_ADRERR, (void __user *)regs->csr_badvaddr);
  545  
  546  out:
  547  	irqentry_exit(regs, state);
  548  }
```

【fixup_exception的代码（arch/loongarch/mm/extable.c）】
```c
   46  bool fixup_exception(struct pt_regs *regs)  {
   47  	const struct exception_table_entry *ex;
   48  
   49  	ex = search_exception_tables(exception_era(regs));
   50  	if (!ex)
   51  		return false;
   52  
   53  	switch (ex->type) {
   54  	case EX_TYPE_FIXUP:
   55  		return ex_handler_fixup(ex, regs);
   56  	case EX_TYPE_UACCESS_ERR_ZERO:
   57  		return ex_handler_uaccess_err_zero(ex, regs);
   58  	case EX_TYPE_BPF:
   59  		return ex_handler_bpf(ex, regs);
   60  	}
   61  
   62  	BUG();
   63  }
```

请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；下标是否真的来自不可信的一方；这是LoongArch特有的问题，还是所有架构都一样。拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}

