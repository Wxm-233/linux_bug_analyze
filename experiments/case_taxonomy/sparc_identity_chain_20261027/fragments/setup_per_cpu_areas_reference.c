void __init setup_per_cpu_areas(void)
{
	unsigned long delta;
	unsigned int cpu;
	int rc = -EINVAL;

	if (pcpu_chosen_fc != PCPU_FC_PAGE) {
		rc = pcpu_embed_first_chunk(PERCPU_MODULE_RESERVE,
					    PERCPU_DYNAMIC_RESERVE, 4 << 20,
					    pcpu_cpu_distance,
					    pcpu_cpu_to_node);
		if (rc)
			pr_warn("PERCPU: %s allocator failed (%d), "
				"falling back to page size\n",
				pcpu_fc_names[pcpu_chosen_fc], rc);
	}
	if (rc < 0)
		rc = pcpu_page_first_chunk(PERCPU_MODULE_RESERVE,
					   pcpu_cpu_to_node);
	if (rc < 0)
		panic("cannot initialize percpu area (err=%d)", rc);

	delta = (unsigned long)pcpu_base_addr - (unsigned long)__per_cpu_start;
	for_each_possible_cpu(cpu)
		__per_cpu_offset(cpu) = delta + pcpu_unit_offsets[cpu];

	/* Setup %g5 for the boot cpu.  */
	__local_per_cpu_offset = __per_cpu_offset(smp_processor_id());

	of_fill_in_cpu_data();
	if (tlb_type == hypervisor)
		mdesc_fill_in_cpu_data(cpu_all_mask);
}
