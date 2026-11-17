/* amendment 3: bodies of NO_DESCEND functions and of primitives are not expanded (criteria 3.3).
 * This file must add no flag at all: EXPECTED in verify.py is unchanged. */
void msleep(unsigned int ms);
void on_each_cpu(void (*func)(void *), void *info, int wait);
void local_irq_disable(void);
void local_irq_enable(void);

static void opq_nop(void *info)
{
}

/* a tracepoint-like function whose body sleeps: calling it must not count as "may sleep" */
void trace_opq_event(void)
{
	msleep(1);
}

/* a primitive whose body sends an IPI: calling it must count only as its own primitive kind */
void mutex_lock(void *lock)
{
	on_each_cpu(opq_nop, 0, 1);
}

void opq_caller(void)
{
	local_irq_disable();
	trace_opq_event();
	local_irq_enable();
}
