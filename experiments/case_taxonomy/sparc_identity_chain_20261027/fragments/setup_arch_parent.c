void __init setup_arch(char **cmdline_p)
{
	/* Initialize PROM console and command line. */
	*cmdline_p = prom_getbootargs();
	strscpy(boot_command_line, *cmdline_p, COMMAND_LINE_SIZE);
	parse_early_param();

	boot_flags_init(*cmdline_p);
#ifdef CONFIG_EARLYFB
	if (btext_find_display())
#endif
		register_console(&prom_early_console);

	if (tlb_type == hypervisor)
		pr_info("ARCH: SUN4V\n");
	else
		pr_info("ARCH: SUN4U\n");

	idprom_init();

	if (!root_flags)
		root_mountflags &= ~MS_RDONLY;
	ROOT_DEV = old_decode_dev(root_dev);
#ifdef CONFIG_BLK_DEV_RAM
	rd_image_start = ram_flags & RAMDISK_IMAGE_START_MASK;
#endif

#ifdef CONFIG_IP_PNP
	if (!ic_set_manually) {
		phandle chosen = prom_finddevice("/chosen");
		u32 cl, sv, gw;

		cl = prom_getintdefault (chosen, "client-ip", 0);
		sv = prom_getintdefault (chosen, "server-ip", 0);
		gw = prom_getintdefault (chosen, "gateway-ip", 0);
		if (cl && sv) {
			ic_myaddr = cl;
			ic_servaddr = sv;
			if (gw)
				ic_gateway = gw;
#if defined(CONFIG_IP_PNP_BOOTP) || defined(CONFIG_IP_PNP_RARP)
			ic_proto_enabled = 0;
#endif
		}
	}
#endif

	/* Get boot processor trap_block[] setup.  */
	init_cur_cpu_trap(current_thread_info());

	paging_init();
	init_sparc64_elf_hwcap();
	smp_fill_in_cpu_possible_map();
	/*
	 * Once the OF device tree and MDESC have been setup and nr_cpus has
	 * been parsed, we know the list of possible cpus.  Therefore we can
	 * allocate the IRQ stacks.
	 */
	alloc_irqstack_bootmem();
}
