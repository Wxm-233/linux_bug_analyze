/* Instrumented finite host projection; not a bootable kernel. */
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define __init
#ifdef __always_inline
#undef __always_inline
#endif
#define __always_inline inline __attribute__((always_inline))
typedef unsigned int u32;
static unsigned int warn_count, setter_calls, setter_requested;
static unsigned int cap_clear_calls, boot_calls, register_calls;
static unsigned int attempted_ids[16];
static int pv_mode, initial_domain, smp_found_config;
static int acpi_disabled, acpi_noirq, acpi_result;
static bool apic_is_disabled;
static unsigned int setup_max_cpus, max_possible_cpus;
static inline bool record_warn(bool condition) { if (condition) warn_count++; return condition; }
#define WARN_ON(condition) record_warn(!!(condition))
#define pr_warn(...) ((void)0)
#define pr_info(...) ((void)0)
#define min_t(type,a,b) ((type)(a) < (type)(b) ? (type)(a) : (type)(b))
#define X86_FEATURE_APIC 0
static void setup_clear_cpu_cap(int ignored) { (void)ignored; cap_clear_calls++; }
static bool xen_pv_domain(void) { return pv_mode != 0; }
#define xen_initial_domain() (initial_domain != 0)
/* Numeric placeholder is only logged/ignored, never interpreted as a real ACPI ID. */
#define CPU_ACPIID_INVALID 0xffffffffU
static void topology_register_boot_apic(u32 id) { (void)id; boot_calls++; }
static void topology_register_apic(u32 id, u32 acpi_id, bool present) {
    (void)acpi_id; (void)present;
    if (register_calls < 16) attempted_ids[register_calls] = id;
    register_calls++;
}
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


#if NR_CPUS > 1 && !defined(CONFIG_FORCE_NR_CPUS)
unsigned int nr_cpu_ids;
#endif
/* Observer records the request, then calls the unmodified setter above. */
static void observed_set_nr_cpu_ids(unsigned int n) {
    setter_calls++; setter_requested = n; set_nr_cpu_ids(n);
}
#line 1730 "arch/x86/kernel/acpi/boot.c"
int __init acpi_mps_check(void)
{
#if defined(CONFIG_X86_LOCAL_APIC) && !defined(CONFIG_X86_MPPARSE)
/* mptable code is not built-in*/

	/*
	 * Xen disables ACPI in PV DomU guests but it still emulates APIC and
	 * supports SMP. Returning early here ensures that APIC is not disabled
	 * unnecessarily and the guest is not limited to a single vCPU.
	 */
	if (xen_pv_domain() && !xen_initial_domain())
		return 0;

	if (acpi_disabled || acpi_noirq) {
		pr_warn("MPS support code is not built-in, using acpi=off or acpi=noirq or pci=noacpi may have problem\n");
		return 1;
	}
#endif
	return 0;
}


static int observed_acpi_mps_check(void) {
    acpi_result = acpi_mps_check(); return acpi_result;
}
#define set_nr_cpu_ids observed_set_nr_cpu_ids
#line 427 "arch/x86/kernel/cpu/topology.c"
void __init topology_apply_cmdline_limits_early(void)
{
	unsigned int possible = nr_cpu_ids;

	/* 'maxcpus=0' 'nosmp' 'nolapic' */
	if (!setup_max_cpus || apic_is_disabled)
		possible = 1;

	/* 'possible_cpus=N' */
	possible = min_t(unsigned int, max_possible_cpus, possible);

	if (possible < nr_cpu_ids) {
		pr_info("Limiting to %u possible CPUs\n", possible);
		set_nr_cpu_ids(possible);
	}
}

#undef set_nr_cpu_ids
#line 444 "arch/x86/kernel/cpu/topology.c"
static __init bool restrict_to_up(void)
{
	if (!smp_found_config)
		return true;
	/*
	 * XEN PV is special as it does not advertise the local APIC
	 * properly, but provides a fake topology for it so that the
	 * infrastructure works. So don't apply the restrictions vs. APIC
	 * here.
	 */
	if (xen_pv_domain())
		return false;

	return apic_is_disabled;
}

#line 149 "arch/x86/xen/smp_pv.c"
static void __init xen_pv_smp_config(void)
{
	u32 apicid = 0;
	int i;

	topology_register_boot_apic(apicid);

	for (i = 0; i < nr_cpu_ids; i++)
		topology_register_apic(apicid++, CPU_ACPIID_INVALID, true);

	/* Pretend to be a proper enumerated system */
	smp_found_config = 1;
}

#define acpi_mps_check observed_acpi_mps_check

static void apply_setup_acpi_fragment(void)
{
#line 955 "arch/x86/kernel/setup.c"
	if (acpi_mps_check()) {
#ifdef CONFIG_X86_LOCAL_APIC
		apic_is_disabled = true;
#endif
		setup_clear_cpu_cap(X86_FEATURE_APIC);
	}

}
#undef acpi_mps_check
#line 1 "projection_stage_driver.c"

/* Manual stage adapter. Omitted setup/firmware code is not asserted inert. */
int main(int argc, char **argv)
{
    if (argc != 9) return 2;
    const char *case_id = argv[1];
    const char *mode = argv[2];
    pv_mode = strcmp(mode, "native") != 0;
    initial_domain = strcmp(mode, "pv_dom0") == 0;
    acpi_disabled = atoi(argv[3]);
    acpi_noirq = atoi(argv[4]);
    setup_max_cpus = (unsigned int)atoi(argv[5]);
    max_possible_cpus = (unsigned int)atoi(argv[6]);
    apic_is_disabled = atoi(argv[7]) != 0;
    const char *version = argv[8];
#if NR_CPUS > 1 && !defined(CONFIG_FORCE_NR_CPUS)
    nr_cpu_ids = NR_CPUS;
#endif
    unsigned int before = nr_cpu_ids;
    apply_setup_acpi_fragment();
    int apic_after = apic_is_disabled;
    topology_apply_cmdline_limits_early();
    unsigned int after_early = nr_cpu_ids;
    int provider_selected = pv_mode && !initial_domain;
    if (provider_selected) xen_pv_smp_config();
    unsigned int after_provider = nr_cpu_ids;
    int restricted = restrict_to_up();
    unsigned int after_late = nr_cpu_ids;
    printf("{\"case\":\"%s\",\"version\":\"%s\",\"mode\":\"%s\","
           "\"nr_before\":%u,\"acpi_check_return\":%d,\"apic_after_check\":%d,"
           "\"nr_after_early\":%u,\"nr_after_provider\":%u,\"nr_after_late\":%u,"
           "\"setter_calls\":%u,\"setter_requested\":%u,\"setter_warn_count\":%u,"
           "\"cap_clear_calls\":%u,\"provider_selected\":%d,"
           "\"boot_registration_calls\":%u,\"registration_attempts\":%u,"
           "\"smp_found_config\":%d,\"late_restrict_to_up\":%d,\"attempted_ids\":[",
           case_id, version, mode, before, acpi_result, apic_after,
           after_early, after_provider, after_late, setter_calls, setter_requested,
           warn_count, cap_clear_calls, provider_selected, boot_calls, register_calls,
           smp_found_config, restricted);
    for (unsigned int i = 0; i < register_calls && i < 16; i++)
        printf("%s%u", i ? "," : "", attempted_ids[i]);
    puts("]}");
    return register_calls > 16 ? 3 : 0;
}
