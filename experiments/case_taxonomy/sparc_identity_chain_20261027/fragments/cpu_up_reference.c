static int cpu_up(unsigned int cpu, enum cpuhp_state target)
{
	int err = 0;

	if (!cpu_possible(cpu)) {
		pr_err("can't online cpu %d because it is not configured as may-hotadd at boot time\n",
		       cpu);
		return -EINVAL;
	}

	err = try_online_node(cpu_to_node(cpu));
	if (err)
		return err;

	cpu_maps_update_begin();

	if (cpu_hotplug_disabled) {
		err = -EBUSY;
		goto out;
	}
	if (!cpu_bootable(cpu)) {
		err = -EPERM;
		goto out;
	}

	err = _cpu_up(cpu, 0, target);
out:
	cpu_maps_update_done();
	return err;
}
