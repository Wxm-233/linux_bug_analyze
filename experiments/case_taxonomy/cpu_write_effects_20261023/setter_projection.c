/* N2.22 finite compiler projection; not a kernel translation unit. */
#define __always_inline inline __attribute__((always_inline))
unsigned int n222_warning_count;
#define WARN_ON(condition) ((condition) ? (++n222_warning_count, 1) : 0)
#line 27 "include/linux/cpumask.h"
#if (NR_CPUS == 1) || defined(CONFIG_FORCE_NR_CPUS)
#define nr_cpu_ids ((unsigned int)NR_CPUS)
#else
extern unsigned int nr_cpu_ids;
#endif

static __always_inline void set_nr_cpu_ids(unsigned int nr)
{
#if (NR_CPUS == 1) || defined(CONFIG_FORCE_NR_CPUS)
	WARN_ON(nr != nr_cpu_ids);
#else
	nr_cpu_ids = nr;
#endif
}

#line 1 "n222_observation_wrapper.c"
void n222_observe(unsigned int n) { set_nr_cpu_ids(n); }
