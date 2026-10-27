static void __init alloc_irqstack_bootmem(void)
{
	unsigned int i, node;

	for_each_possible_cpu(i) {
		node = cpu_to_node(i);

		softirq_stack[i] = memblock_alloc_node(THREAD_SIZE,
						       THREAD_SIZE, node);
		if (!softirq_stack[i])
			panic("%s: Failed to allocate %lu bytes align=%lx nid=%d\n",
			      __func__, THREAD_SIZE, THREAD_SIZE, node);
		hardirq_stack[i] = memblock_alloc_node(THREAD_SIZE,
						       THREAD_SIZE, node);
		if (!hardirq_stack[i])
			panic("%s: Failed to allocate %lu bytes align=%lx nid=%d\n",
			      __func__, THREAD_SIZE, THREAD_SIZE, node);
	}
}
