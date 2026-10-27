static inline __attribute__((always_inline)) void *set_hardirq_stack(void)
{
	void *orig_sp, *sp = hardirq_stack[smp_processor_id()];

	__asm__ __volatile__("mov %%sp, %0" : "=r" (orig_sp));
	if (orig_sp < sp ||
	    orig_sp > (sp + THREAD_SIZE)) {
		sp += THREAD_SIZE - 192 - STACK_BIAS;
		__asm__ __volatile__("mov %0, %%sp" : : "r" (sp));
	}

	return orig_sp;
}
