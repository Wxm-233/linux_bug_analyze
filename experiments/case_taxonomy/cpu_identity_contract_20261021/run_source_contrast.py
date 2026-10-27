"""Exact known-source units with explicit bitmap API substitutes.

This is not a kernel/configuration reproduction or an automatic C detector.
Prepare and review precede compilation. No source/body rewrites or retries.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
INNER = HERE.parents[2]
OUTER = INNER.parent
BUILD = INNER / 'analysis_out/cpu-identity-20261021'
sha = lambda data: hashlib.sha256(data).hexdigest()

HEADER = r'''#include <assert.h>
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
'''

MAIN = r'''
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
    PARENT_POSTPROCESS
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
'''


def load(path):
    return json.loads(path.read_bytes())


def prepare():
    plan = load(HERE / 'experiment_pre.json')
    assert sha((HERE / 'sources.json').read_bytes()) == plan['sources_sha256']
    sources = load(HERE / 'sources.json')['documents']
    old = load(BASE / 'bounded_mechanism_transfer_20261020/documents_G.json')['documents']
    extracted = []
    for spec in plan['source_extracts']:
        docs = old if spec.get('document') else sources
        document = next(d for d in docs if d['path'] == spec['path'] and
                        (d.get('id') == spec['document'] if spec.get('document')
                         else d.get('revision') == spec['revision']))
        fragment = ''.join(document['text'].splitlines(keepends=True)[spec['start'] - 1:spec['end']])
        assert spec['function'] + '(' in fragment
        assert fragment.count('{') == fragment.count('}') == 1
        if spec['function'] == 'smp_fill_in_cpu_possible_map':
            assert fragment.count('{') == 1  # original for bodies are single statements
        row = dict(spec, fragment=fragment, fragment_sha256=sha(fragment.encode('utf-8')),
                   source_sha256=sha(document['text'].encode('utf-8')))
        extracted.append(row)
    # The common setup body was not changed by this architecture-only repair.
    setup = next(e for e in extracted if e['function'] == 'setup_nr_cpu_ids')
    fixed_smp = next(d for d in sources if d['revision'] == load(HERE / 'source_plan.json')['child']
                     and d['path'] == 'kernel/smp.c')
    assert setup['fragment'] == ''.join(fixed_smp['text'].splitlines(keepends=True)[964:968])
    generated = HERE / 'generated'
    generated.mkdir(exist_ok=False)
    units = []
    for version in ['parent', 'fixed']:
        fragments = [e for e in extracted if e['version'] in [version, 'both']]
        main = MAIN.replace('PARENT_POSTPROCESS',
                            'smp_fill_in_cpu_possible_map();' if version == 'parent' else
                            '/* fixed revision has no post-enumeration compaction */')
        content = (HEADER + '\n' + '\n'.join(e['fragment'] for e in fragments) + main).encode('utf-8')
        path = generated / (version + '_harness.c')
        path.write_bytes(content)
        for e in fragments:
            assert content.count(e['fragment'].encode('utf-8')) == 1
        units.append({'version': version, 'path': str(path.relative_to(INNER)).replace('\\', '/'),
                      'sha256': sha(content), 'functions': [e['function'] for e in fragments]})
    manifest = {'experiment_sha256': sha((HERE / 'experiment_pre.json').read_bytes()),
                'source_extracts': extracted, 'generated_units': units,
                'api_semantics': 'explicit substitutes from experiment_pre; original function bodies unchanged',
                'no_compilation_or_execution_yet': True}
    with (HERE / 'prepared_units.json').open('x', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({'status': 'prepared_unmodified_source_units', 'units': len(units),
                      'fragments': len(extracted)}))


def wsl(path):
    absolute = path.resolve()
    assert absolute.is_relative_to(OUTER)
    return '/mnt/d/homework/software/linux_bug_analyze/' + str(absolute.relative_to(OUTER)).replace('\\', '/')


def invoke(command, timeout, record):
    record.update(argv=command, status='invoking')
    decode = lambda data: data.decode('utf-8', 'replace') if isinstance(data, bytes) else (data or '')
    try:
        done = subprocess.run(command, capture_output=True, timeout=timeout)
        record.update(status='returned', returncode=done.returncode,
                      stdout=decode(done.stdout), stderr=decode(done.stderr))
        return done
    except subprocess.TimeoutExpired as error:
        record.update(status='timeout', returncode=None, stdout=decode(error.stdout),
                      stderr=decode(error.stderr), timeout_seconds=timeout)
        raise
    except OSError as error:
        record.update(status='launch_error', returncode=None, error=str(error))
        raise


def run():
    assert not (HERE / 'execution.json').exists(), 'No implicit reruns'
    gate = load(HERE / 'execution_gate.json')
    for relative, digest in gate['files'].items():
        assert sha((HERE / relative).read_bytes()) == digest, relative
    plan = load(HERE / 'experiment_pre.json')
    manifest = load(HERE / 'prepared_units.json')
    assert sha((HERE / 'experiment_pre.json').read_bytes()) == manifest['experiment_sha256']
    BUILD.mkdir(parents=True, exist_ok=False)
    result = {'task': 'N2.18', 'gate_sha256': sha((HERE / 'execution_gate.json').read_bytes()),
              'builds': [], 'runs': [], 'status': 'started', 'new_kernel_builds': 0, 'new_boots': 0}
    try:
        result['compiler_version'] = {}
        version = invoke(['wsl.exe', '-d', 'Ubuntu', '--', 'gcc', '--version'],
                         30, result['compiler_version'])
        assert version.returncode == 0
        for unit in manifest['generated_units']:
            source = INNER / unit['path']
            assert sha(source.read_bytes()) == unit['sha256']
            binary = BUILD / (unit['version'] + '.bin')
            command = ['wsl.exe', '-d', 'Ubuntu', '--', *plan['compiler_plan'], wsl(source), '-o', wsl(binary)]
            build = {'version': unit['version'], 'source_sha256': unit['sha256']}
            result['builds'].append(build)
            done = invoke(command, 60, build)
            build['binary_sha256'] = sha(binary.read_bytes()) if binary.exists() else None
            assert done.returncode == 0, 'preserve failed first build; no automatic retry'
        for trial in plan['runs']:
            command = ['wsl.exe', '-d', 'Ubuntu', '--', wsl(BUILD / (trial['version'] + '.bin')),
                       str(trial['selection_limit']), *map(str, trial['firmware_order'])]
            row = dict(trial)
            result['runs'].append(row)
            done = invoke(command, 30, row)
            assert done.returncode == 0
            row['observation'] = json.loads(row['stdout'])
        result['status'] = 'twelve_source_projection_runs_complete'
    except (AssertionError, subprocess.TimeoutExpired, OSError, ValueError) as error:
        result['status'] = 'first_failure_preserved'
        result['error'] = str(error)
    finally:
        with (HERE / 'execution.json').open('x', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            f.write('\n')
    print(json.dumps({'status': result['status'], 'host_builds': len(result['builds']),
                      'runs': len(result['runs'])}))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--prepare', action='store_true')
    p.add_argument('--run', action='store_true')
    args = p.parse_args()
    assert args.prepare != args.run
    prepare() if args.prepare else run()
