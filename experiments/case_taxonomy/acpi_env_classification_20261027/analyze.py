"""Observation adapter for runs_attempt1 and P1/P3 evaluation with the unchanged common core."""
from pathlib import Path
from collections import Counter
import copy
import hashlib
import json
import re
import sys

HERE = Path(__file__).resolve().parent
INNER = HERE.parents[2]
sys.path.insert(0, str(INNER))
from linux_bug_analyze.contract_protocol import CLAIM_ROLES, evaluate_contract  # noqa: E402

CORE = INNER / 'linux_bug_analyze/contract_protocol.py'
CORE_SHA = '42d37cc48d1c87a4c4b938d67a5acaedcc685ceb207deae3f72d7dcc88da830e'
REV = 'adbf61cc47cb72b102682e690ad323e1eda652c2'
RUNS = HERE / 'runs_attempt1'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def cpulist(text):
    out = []
    for part in (text or '').split(','):
        if not part or part.startswith('ERR'):
            continue
        a, _, b = part.partition('-')
        out += list(range(int(a), int(b or a) + 1))
    return out


def observe(name):
    d = RUNS / name
    receipt = json.loads((d / 'receipt.json').read_text())
    text = (d / 'console.log').read_bytes().decode('utf-8', 'replace')
    lba = dict(re.findall(r'^LBA (\w+)=(.*?)\r?$', text, re.M))
    hyp = re.search(r'Hypervisor detected: (\S+)', text)
    allow = re.search(r'Allowing (\d+) present CPUs plus (\d+) hotplug CPUs', text)
    headers = sorted(set(re.findall(r'ACPI: (FACP|APIC) 0x[0-9A-F]+ [0-9A-F]+ \((v\d+) BOCHS', text)))
    hot_lines = [l.strip() for l in text.splitlines()
                 if re.search(r'(Booting Node \d+ Processor [1-9]|cpu.*hotplug|Unable to map|ACPI: CPU|acpi_processor|CPU\d+ has been hot-added|smpboot: CPU [1-9])', l, re.I)]
    da = (receipt.get('hotplug') or {}).get('device_add') or {}
    return {
        'environment': receipt['environment'], 'returncode': receipt['returncode'], 'timed_out': receipt['timed_out'],
        'ready': receipt['ready_seen'], 'done': receipt['done_seen'],
        'hypervisor': hyp.group(1) if hyp else None,
        'allowing_present_plus_hotplug': [int(allow.group(1)), int(allow.group(2))] if allow else None,
        'firmware_headers': headers, 'cmdline': lba.get('cmdline'),
        'boot': {k: cpulist(lba.get('boot_' + k)) for k in ['possible', 'present', 'online']},
        'final': {k: cpulist(lba.get('final_' + k)) for k in ['possible', 'present', 'online']},
        'hotplug_new_cpu_dir': lba.get('hotplug_new_cpu_dir'),
        'hotplug_online_write': lba.get('hotplug_online_write'),
        'hotplug_online_after': lba.get('hotplug_online_after'),
        'qmp_device_add_ok': 'return' in da, 'qmp_device_add_reply': da,
        'qmp_slot': (receipt.get('hotplug') or {}).get('slot'),
        'kernel_hotplug_lines': hot_lines[:20],
        'image_sha256': receipt['image_sha256'], 'console_sha256': receipt['console_sha256'],
    }


def envelope(context, kind, values, evidence):
    if kind == 'P1_policy_reach':
        scope = {'op': 'and', 'args': [{'symbol': 'supported_context'}, {'symbol': 'qemu_guest_with_legacy_slots'}]}
        relation = {'op': 'ge', 'args': [{'symbol': 'boot_possible_count'}, {'symbol': 'required_possible_count'}]}
        sample = 'after_boot_pid1_sysfs'
    else:
        scope = {'symbol': 'supported_context'}
        relation = {'op': 'eq', 'args': [{'symbol': 'online_outside_boot_possible'}, {'literal': []}]}
        sample = 'after_hotplug_online_attempt'
    config = {'supported_context', 'qemu_guest_with_legacy_slots', 'required_possible_count'}
    names = set()
    def walk(e):
        if 'symbol' in e:
            names.add(e['symbol'])
        for a in e.get('args', []):
            walk(a)
    walk(scope); walk(relation)
    symbols = {n: {'type': 'bool' if type(values[n]) is bool else ('int_set' if isinstance(values[n], list) else 'int'),
                   'role': 'configuration' if n in config else 'observation'} for n in sorted(names)}
    ident = f'acpi.env.{context}.{kind}'
    obj = context + '.cpu_possible_domain'
    sample_ev, deadline = context + '.' + sample, context + '.unobserved_later_hotplug_consumer'
    origins = {k: 'researcher_authored' for k in ['scope', 'relation', 'symbols', 'required_claims', 'authority_kind']}
    contract = {'schema': 'architecture_contract_v1', 'id': ident, 'revision': REV, 'authority_kind': 'documented',
                'sufficient_for_correctness': False, 'field_origins': origins, 'symbols': symbols,
                'required_claims': {r: 'review.' + r for r in CLAIM_ROLES}, 'scope': scope, 'relation': relation}
    record = {'id': ident + '.record', 'revision': REV, 'basis': 'archived_runtime', 'context_id': context,
              'object_id': obj, 'sample_event': sample_ev, 'deadline_event': deadline, 'sample_kind': 'sample',
              'facts': {}, 'observation_binding': {'object_id': obj, 'event_id': sample_ev, 'deadline_id': deadline,
                                                   'claim': 'review.observation'}}
    docs = {}
    for dn, path in [('evidence', evidence), ('policy', HERE / 'checking_policy.md')]:
        docs[dn] = {'context_revision': REV, 'source_revision': REV, 'path': str(path.relative_to(INNER)).replace('\\', '/'),
                    'sha256': sha(path), 'start_line': 1, 'end_line': len(path.read_text(encoding='utf-8').splitlines())}
    refs = lambda dn: [{'document': dn, 'start_line': 1, 'end_line': docs[dn]['end_line']}]
    ledger = {'contract_id': ident, 'revision': REV, 'basis': 'archived_runtime', 'context_id': context,
              'field_origins': copy.deepcopy(origins), 'documents': docs, 'claims': {}}
    for r in CLAIM_ROLES:
        ledger['claims']['review.' + r] = {'role': r, 'status': 'supported', 'origin': 'researcher_review', 'context_id': context,
                                           'statement': 'Registered ACPI legacy-slot policy reach relation; QEMU guest runtime tier.',
                                           'references': refs('policy' if r in ['authority', 'consumer_requirement'] else 'evidence')}
    ledger['claims']['review.authority'].update(authority_kind='documented', supports_requirement='review.consumer_requirement')
    ledger['claims']['review.applicability'].update(expression=copy.deepcopy(scope), symbols=copy.deepcopy(symbols))
    ledger['claims']['review.consumer_requirement'].update(expression=copy.deepcopy(relation), symbols=copy.deepcopy(symbols))
    for r in ['consumer_requirement', 'provider_binding', 'object_binding', 'deadline_binding']:
        ledger['claims']['review.' + r]['object_id'] = obj
    ledger['claims']['review.deadline_binding'].update(event_id=deadline, event_kind='content_consumption')
    ledger['claims']['review.observation'] = {'role': 'observation_binding', 'status': 'supported', 'origin': 'researcher_review',
                                              'context_id': context, 'statement': 'PID1 sysfs sample at the declared point.',
                                              'references': refs('evidence'),
                                              'binding': {'object_id': obj, 'event_id': sample_ev, 'deadline_id': deadline,
                                                          'context_id': context, 'event_kind': 'sample'}}
    for n in sorted(names):
        decl = {'symbol': n, 'value': values[n], 'role': symbols[n]['role'], 'context_id': context}
        record['facts'][n] = {'value': values[n], 'claim': 'fact.' + n}
        if symbols[n]['role'] == 'observation':
            decl.update(object_id=obj, event_id=sample_ev)
            record['facts'][n].update(object_id=obj, event_id=sample_ev)
        ledger['claims']['fact.' + n] = {'role': 'fact', 'status': 'supported', 'origin': 'program_projection', 'context_id': context,
                                         'statement': 'Projected from this run console/QMP.', 'references': refs('evidence'), 'fact': decl}
    return {'contract': contract, 'ledger': ledger, 'record': record}


def main():
    if sha(CORE) != CORE_SHA:
        raise SystemExit('common core changed')
    out = HERE / 'analysis'
    out.mkdir(exist_ok=False)
    plan = json.loads((HERE / 'frozen_plan.json').read_text())
    rows, inputs = [], []
    for env in plan['environments']:
        o = observe(env['name'])
        legacy = ('APIC', 'v03') in [tuple(h) for h in o['firmware_headers']]
        values = {'supported_context': o['ready'] and o['done'] and o['returncode'] == 0,
                  'qemu_guest_with_legacy_slots': legacy,
                  'required_possible_count': 4,      # -smp 1,maxcpus=4: 1 present + 3 Enabled=0 slots
                  'boot_possible_count': len(o['boot']['possible']),
                  'online_outside_boot_possible': sorted(set(o['final']['online']) - set(o['boot']['possible']))}
        evidence = out / f"{env['name']}.observation.json"
        evidence.write_text(json.dumps({'observation': o, 'facts': values}, indent=1) + '\n', encoding='utf-8')
        decisions = {}
        for kind in ['P1_policy_reach', 'P3_hotplug_consumption']:
            item = envelope('qemu_' + env['name'], kind, values, evidence)
            inputs.append(item)
            decisions[kind] = evaluate_contract(item['contract'], item['ledger'], item['record'])['relation_at_observation']
        rows.append({'env': env['name'], 'observation': o, 'facts': values, 'decisions': decisions})
    (out / 'contract_inputs.json').write_text(json.dumps(inputs) + '\n', encoding='utf-8')
    res = {'rows': rows, 'core_evaluations': len(inputs),
           'decision_counts': dict(Counter(d for r in rows for d in r['decisions'].values())),
           'kernel_builds': 1, 'boots': len(rows), 'model_calls': 0}
    (out / 'results.json').write_text(json.dumps(res, indent=1) + '\n', encoding='utf-8')
    for r in rows:
        o = r['observation']
        print(r['env'], 'hyp=', o['hypervisor'], 'allow=', o['allowing_present_plus_hotplug'], 'boot=', o['boot'],
              'new=', o['hotplug_new_cpu_dir'], 'write=', o['hotplug_online_write'], 'final=', o['final'],
              'qmp_ok=', o['qmp_device_add_ok'], r['decisions'])


if __name__ == '__main__':
    main()
