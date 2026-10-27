"""Separate runtime-local source candidates from actual per-CPU observations."""
from collections import Counter
from pathlib import Path
import argparse
import copy
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
INNER = HERE.parents[2]
BASE = HERE.parent / 'die_arch_contract_20261013/runtime/profiles'
LEGACY = HERE.parent / 'die_contract_transfer_20261019'
sys.path.insert(0, str(LEGACY))
import transfer as legacy
from binding import bind_run


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads(p.read_bytes())
def save(p, value):
    with p.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2); f.write('\n')


def cpu_projection(runtime, cpu):
    """A complete observed trio never supplies effective macro origin."""
    valid = (runtime.get('status') == 'supported' and type(cpu.get('cpu')) is int and cpu['cpu'] >= 0
             and type(cpu.get('count')) is int
             and cpu.get('status') in {'all_success', 'all_enoent'}
             and type(cpu.get('listed_any')) is bool
             and ((cpu['status'] == 'all_success' and cpu.get('count') == 3 and cpu['listed_any'] is True)
                  or (cpu['status'] == 'all_enoent' and cpu.get('count') == 0 and cpu['listed_any'] is False)))
    return {'status': 'supported' if valid else 'insufficient',
            'listed_any': cpu['listed_any'] if valid else None,
            'id_native': None, 'mask_native': None, 'provider_body_reviewed': False,
            'cpu': cpu.get('cpu'), 'unknowns': ['runtime_effective_macro_closure_unproved']}


def validate_cpu_scope(runtime):
    rows = runtime.get('cpus')
    if not isinstance(rows, list) or any(not isinstance(r, dict) or type(r.get('cpu')) is not int for r in rows):
        raise ValueError('Malformed archived CPU scope')
    if [r['cpu'] for r in rows] != [0, 1]:
        raise ValueError('This archived-pair trial requires exactly CPU 0 and 1')


def prepare():
    hashes = {}
    def read(p): hashes[str(p.relative_to(INNER))] = sha(p); return load(p)
    protocol = read(HERE / 'protocol_pre.json')
    assert sha(INNER / 'linux_bug_analyze/contract_protocol.py') == protocol['core_sha256']
    for file in ('binding.py', 'run_binding.py', 'source_review.md', 'next_validation_protocol.md'):
        hashes[str((HERE / file).relative_to(INNER))] = sha(HERE / file)
    for file in ('transfer.py', 'projection.py', 'policy_card.md'):
        hashes[str((LEGACY / file).relative_to(INNER))] = sha(LEGACY / file)
    packet = read(HERE / 'cached_source_packet.json')
    assert packet['runtime_effective_macro_closure_proved'] is False
    rows = []
    for profile in protocol['profiles']:
        folder = BASE / profile
        build, boot = read(folder / 'build.json'), read(folder / 'boot.json')
        config, autoconf, raw = folder / 'kernel.config', folder / 'autoconf.h', folder / 'qemu_boot.stdout.log'
        for path in (config, autoconf, raw): hashes[str(path.relative_to(INNER))] = sha(path)
        events = []
        for line in raw.read_text(encoding='utf-8').splitlines():
            start = line.find('{"event":')
            if start >= 0: events.append(json.loads(line[start:]))
        assert events == boot['observations']['events']
        assert legacy.validate_runtime_identity(profile, boot, build, events)
        binding = bind_run(profile, build, boot, config.read_text(), autoconf.read_text(), packet)
        assert binding['runtime_facts'] == {'id_native': None, 'mask_native': None, 'provider_binding': 'unknown'}
        runtime = legacy.project_runtime(events)
        validate_cpu_scope(runtime)
        evaluations = []
        for cpu in runtime['cpus']:
            context = 'runtime.' + profile + '.' + sha(config)[:12] + '.' + build['image_sha256'][:12] + '.cpu' + str(cpu['cpu'])
            evidence = cpu_projection(runtime, cpu)
            envelope = legacy.envelope(profile, build['revision'], 'archived_runtime', context,
                                       evidence, legacy.config_value(config.read_text(), 'CONFIG_SYSFS'), folder / 'boot.json')
            assert 'native_id' not in envelope['record']['facts'] and 'native_mask' not in envelope['record']['facts']
            evaluations.append({'cpu': cpu['cpu'], 'observed_trio_status': cpu['status'],
                                'observation': copy.deepcopy(cpu), 'input': envelope})
        rows.append({'profile': profile, 'binding': binding, 'runtime_projection_status': runtime['status'],
                     'runtime_unknowns': runtime['unknowns'], 'per_cpu': evaluations,
                     'runtime_identity': {'config_sha256': sha(config), 'image_sha256': build['image_sha256'], 'raw_log_sha256': sha(raw)}})
    save(HERE / 'binding_inputs.json', {'rows': rows, 'input_sha256': hashes,
          'core_sha256': protocol['core_sha256'], 'scope': 'four already-read runs, per-CPU samples; candidate diagnostics are not native facts'})
    print(json.dumps({'prepared_runs': len(rows), 'cpu_records': sum(len(r['per_cpu']) for r in rows)}))


def execute():
    packet = load(HERE / 'binding_inputs.json')
    for path, digest in packet['input_sha256'].items(): assert sha(INNER / path) == digest, path
    assert sha(INNER / 'linux_bug_analyze/contract_protocol.py') == packet['core_sha256']
    rows = []
    for run in packet['rows']:
        cpu_rows = []
        for record in run['per_cpu']:
            e = record['input']
            result = legacy.evaluate_contract(e['contract'], e['ledger'], e['record'])
            cpu_rows.append({'cpu': record['cpu'], 'observed_trio_status': record['observed_trio_status'],
                            'evaluator': result, 'policy_application': e['policy_application'], 'historical_normative_verdict': 'insufficient'})
        states = [r['evaluator']['relation_at_observation'] for r in cpu_rows]
        group = states[0] if states and len(set(states)) == 1 else 'insufficient'
        rows.append({'profile': run['profile'], 'source_candidate_status': run['binding']['status'],
                     'source_candidate': run['binding'].get('source_candidate'), 'runtime_effective_native': [None, None],
                     'per_cpu': cpu_rows, 'run_relation_at_observation': group,
                     'meaning': 'group aggregation requires equal per-CPU results; no existential success aggregation'})
    save(HERE / 'binding_results.json', {'rows': rows, 'input_sha256': sha(HERE / 'binding_inputs.json'),
          'core_sha256': packet['core_sha256'], 'run_counts': dict(Counter(r['run_relation_at_observation'] for r in rows)),
          'source_candidate_counts': dict(Counter(r['source_candidate_status'] for r in rows)),
          'per_cpu_counts': dict(Counter(c['evaluator']['relation_at_observation'] for r in rows for c in r['per_cpu'])),
          'new_model_calls': 0, 'new_preprocessing': 0, 'new_builds': 0, 'new_boots': 0,
          'new_defects': 0, 'formal_independent_positive_normal': [0, 0]})
    print(json.dumps({'runs': len(rows), 'run_counts': dict(Counter(r['run_relation_at_observation'] for r in rows)),
                     'candidate_counts': dict(Counter(r['source_candidate_status'] for r in rows))}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--prepare', action='store_true')
    prepare() if parser.parse_args().prepare else execute()
