#ifndef _LINUX_R4_OBSERVE_H
#define _LINUX_R4_OBSERVE_H
#include <linux/printk.h>
#include <linux/smp.h>
#include <linux/cpuhotplug.h>
#include <linux/sched/topology.h>
unsigned int r4_next_seq(unsigned int cpu);
static inline void r4_note(const char *phase, unsigned int cpu,
                          int known, int prepared, int state, int target, int ret)
{
    const struct cpumask *mask = cpu_smt_mask(cpu);
    pr_info("R4 phase=%s cpu=%u current=%u seq=%u online=%u mask=%lx self=%u weight=%u prepared_known=%d prepared=%d state=%d target=%d ret=%d sched_state=%d\n",
        phase, cpu, raw_smp_processor_id(), r4_next_seq(cpu), cpu_online(cpu),
        cpumask_bits(mask)[0], cpumask_test_cpu(cpu, mask), cpumask_weight(mask),
        known, prepared, state, target, ret, CPUHP_AP_SCHED_STARTING);
}
#endif
