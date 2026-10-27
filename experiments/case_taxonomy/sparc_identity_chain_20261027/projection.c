/*
 * Host projection of the SPARC64 cpuid -> possible -> consumer chain.
 * Original function bodies are #included verbatim from fragments/ (see
 * source_manifest.tsv). Everything defined here is an explicit stand-in:
 * cpumask/bitmap width branch, memblock, printk, per-CPU and cpu_up().
 * Build: -DNR_CPUS=<64|4096> and -DVERSION_FIXED (or not) for parent.
 * Run:   ./proj "<comma separated cpuids>" <L|none>
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>

#ifndef NR_CPUS
#error NR_CPUS required
#endif
#define CONFIG_SMP 1
#define BITS_PER_LONG 64
#define BITS_TO_LONGS(n) (((n) + BITS_PER_LONG - 1) / BITS_PER_LONG)
#define __init
#define KERN_WARNING ""
#define THREAD_SIZE 16384UL
#define WARN_ON(x) (x)

/* ---- cpumask stand-in with the two width branches of include/linux/cpumask.h ---- */
unsigned int nr_cpu_ids = NR_CPUS;          /* kernel/smp.c initialiser */
#if NR_CPUS <= BITS_PER_LONG
#define small_cpumask_bits ((unsigned int)NR_CPUS)
#define WIDTH_BRANCH "small_bits=NR_CPUS"
#else
#define small_cpumask_bits nr_cpu_ids
#define WIDTH_BRANCH "small_bits=nr_cpu_ids"
#endif
struct cpumask { unsigned long bits[BITS_TO_LONGS(NR_CPUS)]; };
static struct cpumask __cpu_possible_mask, __cpu_present_mask, __cpu_online_mask;
#define cpu_possible_mask (&__cpu_possible_mask)
#define cpu_present_mask  (&__cpu_present_mask)
#define cpu_online_mask   (&__cpu_online_mask)
#define cpumask_bits(m) ((m)->bits)

static unsigned int high_bit_writes;        /* set_bit at index >= small_cpumask_bits */
static void set_bit_(unsigned int n, unsigned long *a) { a[n / BITS_PER_LONG] |= 1UL << (n % BITS_PER_LONG); }
static void clear_bit_(unsigned int n, unsigned long *a) { a[n / BITS_PER_LONG] &= ~(1UL << (n % BITS_PER_LONG)); }
static int test_bit_(unsigned int n, const unsigned long *a) { return (a[n / BITS_PER_LONG] >> (n % BITS_PER_LONG)) & 1; }
static unsigned int bitmap_weight(const unsigned long *a, unsigned int size)
{
	unsigned int i, w = 0;
	for (i = 0; i < size; i++)
		w += test_bit_(i, a);
	return w;
}
static unsigned long find_last_bit(const unsigned long *a, unsigned long size)
{
	unsigned long i = size;
	while (i-- > 0)
		if (test_bit_(i, a))
			return i;
	return size;
}
static unsigned int next_set(const struct cpumask *m, unsigned int from)
{
	unsigned int i;
	for (i = from; i < small_cpumask_bits; i++)
		if (test_bit_(i, m->bits))
			return i;
	return small_cpumask_bits;
}
#define for_each_cpu(cpu, mask) \
	for ((cpu) = next_set((mask), 0); (cpu) < small_cpumask_bits; (cpu) = next_set((mask), (cpu) + 1))
#define for_each_possible_cpu(cpu) for_each_cpu((cpu), cpu_possible_mask)
static void cpumask_set_cpu_(unsigned int cpu, struct cpumask *m)
{
	if (cpu >= small_cpumask_bits)
		high_bit_writes++;            /* would hit cpu_max_bits_warn under DEBUG_PER_CPU_MAPS */
	set_bit_(cpu, m->bits);
}
static void set_cpu_possible(unsigned int cpu, bool possible)
{
	if (possible)
		cpumask_set_cpu_(cpu, &__cpu_possible_mask);
	else
		clear_bit_(cpu, __cpu_possible_mask.bits);
}
static void set_cpu_present(unsigned int cpu, bool present)
{
	if (present)
		cpumask_set_cpu_(cpu, &__cpu_present_mask);
}
#define cpu_possible(cpu) test_bit_((cpu), __cpu_possible_mask.bits)
#define cpu_online(cpu)   test_bit_((cpu), __cpu_online_mask.bits)
#define num_possible_cpus() bitmap_weight(cpumask_bits(cpu_possible_mask), small_cpumask_bits)
static void set_nr_cpu_ids(unsigned int nr) { nr_cpu_ids = nr; }
static int get_option(char **str, int *v) { *v = atoi(*str); return 1; }

/* ---- other stand-ins ---- */
struct device_node { int unused; };
static int ncpus_probed;
static int cpu_to_node(unsigned int cpu) { (void)cpu; return 0; }
static void *softirq_stack[NR_CPUS];
static void *hardirq_stack[NR_CPUS];
static void *memblock_alloc_node(unsigned long size, unsigned long align, int nid)
{ (void)align; (void)nid; return malloc(size); }
static void panic(const char *fmt, ...) { (void)fmt; puts("{\"panic\":true}"); exit(3); }
static int percpu_offset_assigned[NR_CPUS];
static int percpu_ptr_without_offset[NR_CPUS];
enum cpuhp_state { CPUHP_OFFLINE, CPUHP_ONLINE };
struct cpuhp_cpu_state { int state; };
static struct cpuhp_cpu_state cpuhp_state[NR_CPUS];
static struct cpuhp_cpu_state *per_cpu_ptr_(struct cpuhp_cpu_state (*p)[NR_CPUS], unsigned int cpu)
{
	if (!percpu_offset_assigned[cpu])
		percpu_ptr_without_offset[cpu] = 1;  /* kernel would use an unset __per_cpu_offset */
	return &(*p)[cpu];
}
#define per_cpu_ptr(p, cpu) per_cpu_ptr_((p), (cpu))
static int can_rollback_cpu(struct cpuhp_cpu_state *st) { (void)st; return 0; }
static int cpuhp_invoke_callback_range(bool up, unsigned int cpu, struct cpuhp_cpu_state *st, enum cpuhp_state t)
{ (void)up; (void)cpu; (void)st; (void)t; return 0; }
static int rejected[NR_CPUS];
/* stand-in: only the first check of kernel/cpu.c cpu_up() (fragments/cpu_up_reference.c) */
static int cpu_up(unsigned int cpu, enum cpuhp_state target)
{
	(void)target;
	if (!cpu_possible(cpu)) {
		rejected[cpu] = 1;            /* pr_err("can't online cpu %d ...") */
		return -22;
	}
	set_bit_(cpu, __cpu_online_mask.bits);
	return 0;
}

/* ---- verbatim original bodies ---- */
#ifdef VERSION_FIXED
#include "fragments/record_one_cpu_fixed.c"
#include "fragments/alloc_irqstack_bootmem_fixed.c"
#define VERSION_NAME "fixed"
#else
#include "fragments/record_one_cpu_parent.c"
#include "fragments/smp_fill_in_cpu_possible_map_parent.c"
#include "fragments/alloc_irqstack_bootmem_parent.c"
#define VERSION_NAME "parent"
#endif
#include "fragments/nrcpus.c"
#include "fragments/setup_nr_cpu_ids.c"
#include "fragments/cpuhp_bringup_mask.c"

/* ---- driver ---- */
static void dump(const char *key, const struct cpumask *m, int last)
{
	unsigned int i, first = 1;
	printf("\"%s\":[", key);
	for (i = 0; i < NR_CPUS; i++)            /* raw bits, independent of small_cpumask_bits */
		if (test_bit_(i, m->bits)) { printf(first ? "%u" : ",%u", i); first = 0; }
	printf("]%s", last ? "" : ",");
}
static void dump_flags(const char *key, int *a, int last)
{
	unsigned int i, first = 1;
	printf("\"%s\":[", key);
	for (i = 0; i < NR_CPUS; i++)
		if (a[i]) { printf(first ? "%u" : ",%u", i); first = 0; }
	printf("]%s", last ? "" : ",");
}
static void stage(const char *name)
{
	printf("{\"stage\":\"%s\",\"nr_cpu_ids\":%u,\"weight_possible\":%u,", name, nr_cpu_ids, num_possible_cpus());
	dump("possible", cpu_possible_mask, 0);
	dump("present", cpu_present_mask, 0);
	dump("online", cpu_online_mask, 1);
	printf("},");
}

int main(int argc, char **argv)
{
	int ids[16], n = 0, i, irq_alloc[NR_CPUS] = {0};
	unsigned int cpu;
	char *s, buf[64];

	if (argc != 3)
		return 2;
	strncpy(buf, argv[1], sizeof(buf) - 1);
	for (s = strtok(buf, ","); s && n < 16; s = strtok(NULL, ","))
		ids[n++] = atoi(s);

	printf("{\"version\":\"%s\",\"NR_CPUS\":%d,\"branch\":\"%s\",\"input\":\"%s\",\"L\":\"%s\",\"stages\":[",
	       VERSION_NAME, NR_CPUS, WIDTH_BRANCH, argv[1], argv[2]);
	/* boot_cpu_init(): boot cpu 0 online/present/possible */
	set_bit_(0, __cpu_online_mask.bits);
	set_cpu_present(0, true);
	set_cpu_possible(0, true);
	/* setup_arch(): parse_early_param() */
	if (strcmp(argv[2], "none") != 0)
		nrcpus(argv[2]);
	stage("early");
	/* paging_init(): of_populate_present_mask() -> of_iterate_over_cpus(record_one_cpu) */
	ncpus_probed = 0;
	for (i = 0; i < n; i++) {
		if (ids[i] >= NR_CPUS)
			continue;
		record_one_cpu(NULL, ids[i], 0);
	}
	stage("after_OF_enumeration");
#ifndef VERSION_FIXED
	smp_fill_in_cpu_possible_map();
	stage("after_arch_possible_fixup");
#endif
	alloc_irqstack_bootmem();
	for (cpu = 0; cpu < NR_CPUS; cpu++)
		irq_alloc[cpu] = hardirq_stack[cpu] != NULL && softirq_stack[cpu] != NULL;
	stage("after_alloc_irqstack");
	setup_nr_cpu_ids();
	stage("after_setup_nr_cpu_ids");
	/* setup_per_cpu_areas(): for_each_possible_cpu(cpu) __per_cpu_offset(cpu) = ... */
	for_each_possible_cpu(cpu)
		percpu_offset_assigned[cpu] = 1;
	/* smp_init() -> bringup_nonboot_cpus(setup_max_cpus) serial path */
	cpuhp_bringup_mask(cpu_present_mask, NR_CPUS, CPUHP_ONLINE);
	stage("after_bringup");
	printf("{\"stage\":\"summary\",");
	dump_flags("irqstack_allocated", irq_alloc, 0);
	dump_flags("percpu_offset_assigned", percpu_offset_assigned, 0);
	dump_flags("cpu_up_rejected", rejected, 0);
	dump_flags("per_cpu_ptr_without_offset", percpu_ptr_without_offset, 0);
	printf("\"ncpus_probed\":%d,\"high_bit_writes\":%u}]}\n", ncpus_probed, high_bit_writes);
	return 0;
}
