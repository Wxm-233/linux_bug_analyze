"""Build an instrumented host projection from fixed, verbatim source ranges.

This is a researcher-written development experiment, not an automatic detector.
No source code, configuration, or observation outside the declared scope is read.
"""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
PRIOR = HERE.parent / 'cpu_domain_qualification_20261022'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def function_fragment(text, name):
    lines = text.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines)
              if line and not line[0].isspace() and name + '(' in line
              and i + 1 < len(lines) and lines[i + 1].strip() == '{']
    if len(starts) != 1:
        raise ValueError(('nonunique exact function', name, starts))
    start = starts[0]
    # These fixed functions have a column-zero closing brace. This deliberately
    # limited range locator is not a C parser or a claim of general extraction.
    end = next(i for i in range(start + 2, len(lines)) if lines[i].rstrip() == '}')
    return start + 1, end + 1, ''.join(lines[start:end + 1])


def generate():
    out = HERE / 'source_fragments.json'
    if out.exists():
        raise RuntimeError('preserve first generated material')
    protocol = json.loads((HERE / 'protocol_pre.json').read_text(encoding='utf-8'))
    parents = json.loads((PRIOR / 'documents_P01.json').read_text(encoding='utf-8'))
    docs = {d['id']: d for d in parents['documents']}
    child = (HERE / 'child_acpi_boot.c').read_text(encoding='utf-8')
    rows = []

    def fragment(key, doc_id, name=None, bounds=None, fixed=False):
        d = docs[doc_id]
        text = child if fixed else d['text']
        if name:
            first, last, raw = function_fragment(text, name)
        else:
            first, last = bounds
            raw = ''.join(text.splitlines(keepends=True)[first - 1:last])
        row = {'id': key, 'revision': protocol['child' if fixed else 'parent'],
               'path': d['path'], 'first_line': first, 'last_line': last,
               'source_file_sha256': sha(text.encode('utf-8')),
               'fragment_sha256': sha(raw.encode('utf-8')), 'text': raw}
        rows.append(row)
        return row

    acpi_parent = fragment('acpi_parent', 'D01', 'acpi_mps_check')
    acpi_fixed = fragment('acpi_fixed', 'D01', 'acpi_mps_check', fixed=True)
    setter = fragment('setter_and_binding', 'D05', bounds=(27, 40))
    early = fragment('early', 'D02', 'topology_apply_cmdline_limits_early')
    late = fragment('late', 'D02', 'restrict_to_up')
    provider = fragment('provider', 'D04', 'xen_pv_smp_config')
    setup = fragment('setup_acpi_fragment', 'D03', bounds=(955, 960))
    fragment('setup_order_witness', 'D03', bounds=(1199, 1211))
    fragment('provider_hook_witness', 'D04', bounds=(443, 456))

    prelude = r'''/* Instrumented finite host projection; not a bootable kernel. */
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
'''
    main = r'''
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
'''

    def source(row):
        return '#line {} "{}"\n'.format(row['first_line'], row['path']) + row['text'] + '\n'

    for version, acpi in [('parent', acpi_parent), ('fixed', acpi_fixed)]:
        code = prelude + source(setter)
        code += '''
#if NR_CPUS > 1 && !defined(CONFIG_FORCE_NR_CPUS)
unsigned int nr_cpu_ids;
#endif
/* Observer records the request, then calls the unmodified setter above. */
static void observed_set_nr_cpu_ids(unsigned int n) {
    setter_calls++; setter_requested = n; set_nr_cpu_ids(n);
}
'''
        code += source(acpi)
        code += '''
static int observed_acpi_mps_check(void) {
    acpi_result = acpi_mps_check(); return acpi_result;
}
'''
        code += '#define set_nr_cpu_ids observed_set_nr_cpu_ids\n' + source(early)
        code += '#undef set_nr_cpu_ids\n' + source(late) + source(provider)
        code += '#define acpi_mps_check observed_acpi_mps_check\n'
        code += '\nstatic void apply_setup_acpi_fragment(void)\n{\n' + source(setup) + '}\n'
        code += '#undef acpi_mps_check\n'
        code += '#line 1 "projection_stage_driver.c"\n' + main
        (HERE / ('projection_' + version + '.c')).write_text(code, encoding='utf-8')
    out.write_text(json.dumps({'task': 'N2.21', 'fragments': rows,
                              'locator_scope': 'fixed named functions only, no generic C claim',
                              'parent_documents_sha256': sha((PRIOR / 'documents_P01.json').read_bytes()),
                              'instrumentation': 'setter and ACPI-return observers call original functions once; WARN counted; setup fragment wrapped; Xen predicates explicit; APIC registration stubs record attempts'},
                             ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'generated_versions': 2, 'verbatim_fragments': len(rows)}))


if __name__ == '__main__':
    generate()
