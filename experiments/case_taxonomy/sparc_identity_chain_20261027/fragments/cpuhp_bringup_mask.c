static void __init cpuhp_bringup_mask(const struct cpumask *mask, unsigned int ncpus,
				      enum cpuhp_state target)
{
	unsigned int cpu;

	for_each_cpu(cpu, mask) {
		struct cpuhp_cpu_state *st = per_cpu_ptr(&cpuhp_state, cpu);

		if (cpu_up(cpu, target) && can_rollback_cpu(st)) {
			/*
			 * If this failed then cpu_up() might have only
			 * rolled back to CPUHP_BP_KICK_AP for the final
			 * online. Clean it up. NOOP if already rolled back.
			 */
			WARN_ON(cpuhp_invoke_callback_range(false, cpu, st, CPUHP_OFFLINE));
		}

		if (!--ncpus)
			break;
	}
}
