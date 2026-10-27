static void *record_one_cpu(struct device_node *dp, int cpuid, int arg)
{
	ncpus_probed++;
#ifdef CONFIG_SMP
	set_cpu_present(cpuid, true);
	set_cpu_possible(cpuid, true);
#endif
	return NULL;
}
