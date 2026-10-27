void __init smp_fill_in_cpu_possible_map(void)
{
	int possible_cpus = num_possible_cpus();
	int i;

	if (possible_cpus > nr_cpu_ids)
		possible_cpus = nr_cpu_ids;

	for (i = 0; i < possible_cpus; i++)
		set_cpu_possible(i, true);
	for (; i < NR_CPUS; i++)
		set_cpu_possible(i, false);
}
