#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <limits.h>
#define CONFIG_SMP 1
#define NR_CPUS 8
#define __init
struct device_node { int unused; };
struct cpumask { unsigned long bits[1]; };
static struct cpumask possible_mask, present_mask;
#define cpu_possible_mask (&possible_mask)
#define cpumask_bits(p) ((p)->bits)
static unsigned int nr_cpu_ids;
static int ncpus_probed;
static void set_cpu_possible(unsigned int cpu, bool value) {
    assert(cpu < NR_CPUS);
    if (value) possible_mask.bits[0] |= 1UL << cpu;
    else possible_mask.bits[0] &= ~(1UL << cpu);
}
static void set_cpu_present(unsigned int cpu, bool value) {
    assert(cpu < NR_CPUS);
    if (value) present_mask.bits[0] |= 1UL << cpu;
    else present_mask.bits[0] &= ~(1UL << cpu);
}
/* Only the NR_CPUS <= BITS_PER_LONG branch is supported here. */
static unsigned int cpumask_weight(const struct cpumask *p) {
    return (unsigned int)__builtin_popcountl(p->bits[0] & ((1UL << NR_CPUS) - 1));
}
#define num_possible_cpus() cpumask_weight(cpu_possible_mask)
static void set_nr_cpu_ids(unsigned int value) {
    assert(value >= 1 && value <= NR_CPUS);
    nr_cpu_ids = value;
}
static unsigned long find_last_bit(const unsigned long *bits, unsigned long size) {
    assert(size == NR_CPUS);
    for (unsigned long i = size; i > 0; --i)
        if ((*bits >> (i - 1)) & 1UL) return i - 1;
    return size;
}

static void *record_one_cpu(struct device_node *dp, int cpuid, int arg)
{
	ncpus_probed++;
#ifdef CONFIG_SMP
	set_cpu_present(cpuid, true);
	set_cpu_possible(cpuid, true);
#endif
	return NULL;
}

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

void __init setup_nr_cpu_ids(void)
{
	set_nr_cpu_ids(find_last_bit(cpumask_bits(cpu_possible_mask), NR_CPUS) + 1);
}

int main(int argc, char **argv) {
    assert(sizeof(unsigned long) * CHAR_BIT == 64);
    assert(argc >= 3);
    nr_cpu_ids = (unsigned int)strtoul(argv[1], NULL, 10);
    assert(nr_cpu_ids == 2 || nr_cpu_ids == 8);
    possible_mask.bits[0] = present_mask.bits[0] = 1UL;
    ncpus_probed = 0;
    for (int i = 2; i < argc; ++i) {
        unsigned int cpu = (unsigned int)strtoul(argv[i], NULL, 10);
        assert(cpu < NR_CPUS);
        record_one_cpu(NULL, (int)cpu, 0);
    }
    smp_fill_in_cpu_possible_map();
    unsigned long pre_possible = possible_mask.bits[0];
    unsigned int pre_nr = nr_cpu_ids;
    setup_nr_cpu_ids();
    printf("{\"pre_possible\":%lu,\"post_possible\":%lu,"
           "\"present\":%lu,\"pre_nr_cpu_ids\":%u,"
           "\"post_nr_cpu_ids\":%u,\"probed\":%d,"
           "\"NR_CPUS\":8,\"BITS_PER_LONG\":64}\n",
           pre_possible, possible_mask.bits[0], present_mask.bits[0],
           pre_nr, nr_cpu_ids, ncpus_probed);
    return 0;
}
