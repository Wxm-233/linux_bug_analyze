void __init setup_nr_cpu_ids(void)
{
	set_nr_cpu_ids(find_last_bit(cpumask_bits(cpu_possible_mask), NR_CPUS) + 1);
}
