"""Read saved R4 build artifacts; never invoke make or launch a guest."""
from __future__ import annotations
import hashlib
import json
import os
import re
import sys
from pathlib import Path
import run_build as rb


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_binding(variant, arch):
    out = rb.HERE/'profiles'/(variant+'_'+arch)
    binding = json.loads((out/'artifact_binding.json').read_text())
    assert binding['revision'] == rb.VERSIONS[variant]
    assert binding['variant'] == variant and binding['arch'] == arch
    assert binding['status'] == 'SAVED_ARTIFACTS_VERIFIED'
    for item in binding['artifacts']:
        path = Path(item['path'])
        assert path.is_file() and digest(path) == item['sha256'], str(path)
    return binding


def certify_unit(row):
    variant, arch = row['variant'], row['arch']
    out = rb.HERE/'profiles'/(variant+'_'+arch)
    build = rb.BASE/(variant+'_'+arch)/'build'
    tree = rb.BASE/variant/'linux'
    assert row['revision'] == rb.VERSIONS[variant]
    assert (rb.BASE/variant/'source_revision').read_text().strip() == row['revision']
    assert row['cache_build'] == str(build) and row['status'] == 'CONFIG_BUILD_VERIFIED'
    actual = rb.configuration(build/'.config')
    generated = (build/'include/generated/autoconf.h').read_text()
    required = ['SMP', 'SCHED_SMT', 'SCHED_CORE', 'HOTPLUG_CPU', 'SYSFS']
    required += ['SCHED_TOPOLOGY'] if arch == 's390' else []
    target_flag = 'S390' if arch == 's390' else 'X86_64'
    for name in required+[target_flag]:
        assert actual.get('CONFIG_'+name) == 'y', name
        assert re.search(r'^#define CONFIG_'+name+r' 1$', generated, re.M), name
    assert actual['CONFIG_NR_CPUS'] == '4'
    assert re.search(r'^#define CONFIG_NR_CPUS 4$', generated, re.M)
    assert (out/'kernel.config').read_bytes() == (build/'.config').read_bytes()
    assert (out/'autoconf.h').read_bytes() == (build/'include/generated/autoconf.h').read_bytes()
    facts = json.loads((out/'preprocessed_facts.json').read_text())
    assert all(facts['checks'].values())
    core = (build/'kernel/sched/core.i').read_text()
    cpu = (build/'kernel/cpu.i').read_text()
    provider_path = 'arch/s390/kernel/smp.i' if arch == 's390' else 'arch/x86/kernel/smpboot.i'
    provider = (build/provider_path).read_text()
    # Check saved snippets against the actual preprocessor output, not a second model.
    for name in ['cpu_smt_mask', 'sched_core_cpu_starting', 'sched_cpu_starting']:
        assert facts['functions'][name] == rb.body(core, name), name
    start_name = 'smp_start_secondary' if arch == 's390' else 'smp_callin'
    assert facts['functions']['architecture_start'] == rb.body(provider, start_name)
    if arch == 's390':
        topology = (build/'arch/s390/kernel/topology.i').read_text()
        assert facts['functions']['thread_map'] == rb.body(topology, 'cpu_thread_map')
        assert facts['functions']['topology_init_early'] == rb.body(topology, 'topology_init_early')
    else:
        assert facts['functions']['sibling_map'] == rb.body(provider, 'set_cpu_sibling_map')
    markers = re.findall(r'^#\s+\d+\s+"([^"\n]+)"', core, re.M)
    header = tree/f'arch/{arch}/include/asm/topology.h'
    assert any((Path(p) if Path(p).is_absolute() else tree/p).resolve() == header.resolve()
               for p in markers if not p.startswith('<'))
    extra = {'notify_cpu_starting': rb.body(cpu, 'notify_cpu_starting'),
             'sched_core_lock': rb.body(core, 'sched_core_lock')}
    callback = re.search(r'\[CPUHP_AP_SCHED_STARTING\]\s*=\s*\{[^}]*\}', cpu)
    assert callback and re.search(r'startup.single\s*=\s*sched_cpu_starting', callback.group())
    extra['CPUHP_AP_SCHED_STARTING_table_entry'] = callback.group()
    assert 'cpuhp_invoke_callback' in extra['notify_cpu_starting']
    assert 'cpu_smt_mask(cpu)' in extra['sched_core_lock']
    if arch == 's390':
        extra['__cpu_disable'] = rb.body(provider, '__cpu_disable')
        assert ('cpu_setup_mask' in extra['__cpu_disable']) == (variant == 'fixed')
    rb.save(out/'supplemental_preprocessed_facts.json', {
        'revision': row['revision'], 'target_flag': target_flag, 'nr_cpus': 4,
        'functions': extra, 'kernel_boots': 0,
        'scope': 'actual saved preprocessing; known-chain evidence, not detector accuracy'})
    paths = [out/'result.json', out/'kernel.config', out/'autoconf.h', out/'preprocessed_facts.json',
             out/'supplemental_preprocessed_facts.json', out/'commands.json',
             build/'.config', build/'include/generated/autoconf.h']
    for index, obj in enumerate(row['objects']):
        assert obj['machine'] == ('IBM S/390' if arch == 's390' else 'Advanced Micro Devices X86-64')
        obj_path = build/obj['path']
        assert obj_path.stat().st_size == obj['bytes']
        paths += [obj_path, obj_path.with_suffix('.i'), out/f'elf_{index}.stdout.log',
                  out/f'symbols_{index}.stdout.log']
    rb.save(out/'artifact_binding.json', {'status': 'SAVED_ARTIFACTS_VERIFIED',
        'variant': variant, 'arch': arch, 'revision': row['revision'],
        'artifacts': [{'path': str(p), 'sha256': digest(p)} for p in paths],
        'scope': 'this R4 unit only; no historical tree audit'})
    return verify_binding(variant, arch)


def main():
    if os.name != 'posix':
        raise RuntimeError('Run within WSL')
    results = json.loads((rb.HERE/'results.json').read_text())
    assert results['status'] == 'FOUR_CONFIG_BUILD_UNITS_VERIFIED'
    assert {(r['variant'], r['arch']) for r in results['units']} == {
        (v, a) for v in ['old', 'fixed'] for a in ['s390', 'x86']}
    verify_only = '--verify-only' in sys.argv[1:]
    bindings = [verify_binding(r['variant'], r['arch']) if verify_only else certify_unit(r)
                for r in results['units']]
    pairs = []
    for arch in ['s390', 'x86']:
        a = rb.configuration(rb.HERE/'profiles'/('old_'+arch)/'kernel.config')
        b = rb.configuration(rb.HERE/'profiles'/('fixed_'+arch)/'kernel.config')
        differences = {k: [a.get(k), b.get(k)] for k in sorted(set(a)|set(b)) if a.get(k) != b.get(k)}
        assert set(differences) == {'CONFIG_LOCALVERSION'}
        pairs.append({'arch': arch, 'differences': differences})
    report = {'status': 'SAVED_ARTIFACTS_VERIFIED', 'mode': 'verify-only' if verify_only else 'certify',
        'units': 4, 'configuration_pairs': pairs,
        'target_objects': sum(len(r['objects']) for r in results['units']),
        'preprocessor_outputs': sum(len(r['objects']) for r in results['units']),
        'bound_artifacts': sum(len(b['artifacts']) for b in bindings),
        'new_make_commands': 0, 'new_kernel_boots': 0, 'new_cases': 0,
        'independent_detection_positives': 0}
    rb.save(rb.HERE/('saved_artifact_verify.json' if verify_only else 'postbuild_verification.json'), report)
    print(json.dumps(report))


if __name__ == '__main__':
    main()
