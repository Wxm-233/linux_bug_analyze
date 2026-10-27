static int __init nrcpus(char *str)
{
	int nr_cpus;

	if (get_option(&str, &nr_cpus) && nr_cpus > 0 && nr_cpus < nr_cpu_ids)
		set_nr_cpu_ids(nr_cpus);

	return 0;
}
