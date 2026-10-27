"""Project attempt1 observations into explicit facts; evaluate R1-R5 with the unchanged common core."""
from pathlib import Path
from collections import Counter
import copy
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
INNER = HERE.parents[2]
sys.path.insert(0, str(INNER))
from linux_bug_analyze.contract_protocol import CLAIM_ROLES, evaluate_contract  # noqa: E402

CORE = INNER / 'linux_bug_analyze/contract_protocol.py'
CORE_SHA = '42d37cc48d1c87a4c4b938d67a5acaedcc685ceb207deae3f72d7dcc88da830e'
REVISIONS = {'parent': '95706e717c4f55ca62025c151451ccc28863d085',
             'fixed': '98937707fea8375e8acea0aaa0b68a956dd52719'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sym(name): return {'symbol': name}
def lit(value): return {'literal': value}
def eq(a, b): return {'op': 'eq', 'args': [a, b]}
def le(a, b): return {'op': 'le', 'args': [a, b]}
def both(a, b): return {'op': 'and', 'args': [a, b]}


RELATIONS = {
    'R1_identity': (sym('supported_context'), eq(sym('invented_possible'), lit([]))),
    'R2_count_limit': (both(sym('supported_context'), sym('limit_given')), le(sym('possible_count'), sym('limit'))),
    'R3_preserve': (both(sym('supported_context'), sym('no_truncation_needed')), eq(sym('possible_set'), sym('provided_set'))),
    'R4_irqstack': (sym('supported_context'), eq(sym('online_without_irqstack'), lit([]))),
    'R5_percpu': (sym('supported_context'), eq(sym('online_without_percpu'), lit([]))),
}
SAMPLE = {'R1_identity': 'after_setup_nr_cpu_ids', 'R2_count_limit': 'after_setup_nr_cpu_ids',
          'R3_preserve': 'after_setup_nr_cpu_ids', 'R4_irqstack': 'after_bringup', 'R5_percpu': 'after_bringup'}
CONFIG_SYMBOLS = {'supported_context', 'limit_given', 'no_truncation_needed', 'limit'}


def symbols_of(expr, acc):
    if 'symbol' in expr:
        acc.add(expr['symbol'])
    for arg in expr.get('args', []):
        symbols_of(arg, acc)
    return acc


def envelope(context, revision, basis, kind, values, evidence, allow_fact_origin='program_projection'):
    scope, relation = RELATIONS[kind]
    ident = 'sparc.identity_chain.' + context + '.' + kind
    obj = context + '.cpu_identity_to_consumers'
    sample = context + '.' + SAMPLE[kind]
    deadline = context + '.unobserved_first_hardirq_or_percpu_use'
    names = symbols_of(scope, set()) | symbols_of(relation, set())
    symbols = {}
    for name in sorted(names):
        value = values[name]
        typ = 'bool' if type(value) is bool else ('int_set' if isinstance(value, list) else 'int')
        symbols[name] = {'type': typ, 'role': 'configuration' if name in CONFIG_SYMBOLS else 'observation'}
    origins = {key: 'researcher_authored' for key in ['scope', 'relation', 'symbols', 'required_claims', 'authority_kind']}
    contract = {'schema': 'architecture_contract_v1', 'id': ident, 'revision': revision,
                'authority_kind': 'documented' if kind == 'R2_count_limit' else 'consumer_inferred',
                'sufficient_for_correctness': False, 'field_origins': origins, 'symbols': symbols,
                'required_claims': {role: 'review.' + role for role in CLAIM_ROLES},
                'scope': copy.deepcopy(scope), 'relation': copy.deepcopy(relation)}
    record = {'id': ident + '.record', 'revision': revision, 'basis': basis, 'context_id': context,
              'object_id': obj, 'sample_event': sample, 'deadline_event': deadline, 'sample_kind': 'sample',
              'facts': {}, 'observation_binding': {'object_id': obj, 'event_id': sample, 'deadline_id': deadline,
                                                   'claim': 'review.observation'}}
    documents = {}
    for name, path in [('evidence', evidence), ('policy', HERE / 'checking_policy.md')]:
        documents[name] = {'context_revision': revision, 'source_revision': revision,
                           'path': str(path.relative_to(INNER)).replace('\\', '/'), 'sha256': sha(path),
                           'start_line': 1, 'end_line': len(path.read_text(encoding='utf-8').splitlines())}
    refs = lambda name: [{'document': name, 'start_line': 1, 'end_line': documents[name]['end_line']}]
    ledger = {'contract_id': ident, 'revision': revision, 'basis': basis, 'context_id': context,
              'field_origins': copy.deepcopy(origins), 'documents': documents, 'claims': {},
              'policy_origin': 'researcher_review_of_development_materials'}
    for role in CLAIM_ROLES:
        ledger['claims']['review.' + role] = {
            'role': role, 'status': 'supported', 'origin': 'researcher_review', 'context_id': context,
            'statement': 'Registered SPARC64 cpuid/width/stage relation; host source projection tier, not hardware truth.',
            'references': refs('policy' if role in ['authority', 'consumer_requirement'] else 'evidence')}
    ledger['claims']['review.authority'].update(authority_kind=contract['authority_kind'],
                                                supports_requirement='review.consumer_requirement')
    ledger['claims']['review.applicability'].update(expression=copy.deepcopy(scope), symbols=copy.deepcopy(symbols))
    ledger['claims']['review.consumer_requirement'].update(expression=copy.deepcopy(relation), symbols=copy.deepcopy(symbols))
    for role in ['consumer_requirement', 'provider_binding', 'object_binding', 'deadline_binding']:
        ledger['claims']['review.' + role]['object_id'] = obj
    ledger['claims']['review.deadline_binding'].update(event_id=deadline, event_kind='content_consumption',
                                                      actual_occurrence_proved=False)
    ledger['claims']['review.observation'] = {
        'role': 'observation_binding', 'status': 'supported', 'origin': 'researcher_review', 'context_id': context,
        'statement': 'Sample at the declared projected stage; not promoted to the unobserved first use.',
        'references': refs('evidence'),
        'binding': {'object_id': obj, 'event_id': sample, 'deadline_id': deadline, 'context_id': context, 'event_kind': 'sample'}}
    for name in sorted(names):
        declared = {'symbol': name, 'value': values[name], 'role': symbols[name]['role'], 'context_id': context}
        record['facts'][name] = {'value': values[name], 'claim': 'fact.' + name}
        if symbols[name]['role'] == 'observation':
            declared.update(object_id=obj, event_id=sample)
            record['facts'][name].update(object_id=obj, event_id=sample)
        ledger['claims']['fact.' + name] = {
            'role': 'fact', 'status': 'supported', 'origin': allow_fact_origin, 'context_id': context,
            'statement': 'Projected from the exact stdout of this record.', 'references': refs('evidence'), 'fact': declared}
    return {'kind': kind, 'contract': contract, 'ledger': ledger, 'record': record}


def evaluate(item, allow_synthetic=False):
    if sha(CORE) != CORE_SHA:
        raise ValueError('common_contract_core_changed')
    return evaluate_contract(item['contract'], item['ledger'], item['record'], allow_synthetic=allow_synthetic)


def facts_of(rec):
    obs = rec['observation']
    stages = {s['stage']: s for s in obs['stages']}
    fin, summ = stages['after_setup_nr_cpu_ids'], stages['summary']
    online = stages['after_bringup']['online']
    provided = sorted({int(x) for x in rec['ids'].split(',')})
    limit = None if rec['L'] == 'none' else int(rec['L'])
    possible = fin['possible']
    return {
        'supported_context': True,
        'limit_given': limit is not None,
        'limit': limit if limit is not None else 0,
        'no_truncation_needed': limit is None or len(provided) <= limit,
        'invented_possible': sorted(set(possible) - set(provided)),
        'possible_count': len(possible),
        'possible_set': possible,
        'provided_set': provided,
        'online_without_irqstack': sorted(set(online) - set(summ['irqstack_allocated'])),
        'online_without_percpu': sorted(set(online) - set(summ['percpu_offset_assigned'])),
    }


def main():
    out = HERE / 'analysis'
    out.mkdir(exist_ok=False)
    execution = json.loads((HERE / 'attempt1/execution.json').read_text(encoding='utf-8'))
    rows, inputs = [], []
    for rec in execution['records']:
        if rec['returncode'] != 0 or rec['observation'] is None:
            raise ValueError('incomplete record ' + rec['input'])
        context = f"{rec['version']}.NR{rec['NR_CPUS']}.{rec['input']}.L{rec['L']}"
        values = facts_of(rec)
        evidence = out / (context + '.facts.json')
        evidence.write_text(json.dumps({'record': rec, 'program_facts': values,
                                        'tier': 'host source projection with explicit substitutes'},
                                       ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        decisions = {}
        for kind in RELATIONS:
            item = envelope(context, REVISIONS[rec['version']], 'source_projection', kind, values, evidence)
            inputs.append(item)
            decisions[kind] = evaluate(item)
        summ = rec['observation']['stages'][-1]
        rows.append({'context': context, 'version': rec['version'], 'NR_CPUS': rec['NR_CPUS'],
                     'input': rec['input'], 'L': rec['L'], 'facts': values,
                     'decisions': {k: v['relation_at_observation'] for k, v in decisions.items()},
                     'deadline': {k: v['relation_at_deadline'] for k, v in decisions.items()},
                     'diagnostics': {'cpu_up_rejected': summ['cpu_up_rejected'],
                                     'per_cpu_ptr_without_offset': summ['per_cpu_ptr_without_offset'],
                                     'bit_writes_at_or_above_small_cpumask_bits': summ['high_bit_writes']}})
    (out / 'contract_inputs.json').write_text(json.dumps(inputs, ensure_ascii=False) + '\n', encoding='utf-8')
    counts = {}
    for version in ['parent', 'fixed']:
        for nr in [64, 4096]:
            counts[f'{version}.NR{nr}'] = dict(Counter(d for r in rows if r['version'] == version and r['NR_CPUS'] == nr
                                                       for d in r['decisions'].values()))
    branch_differences = []
    for r in rows:
        if r['NR_CPUS'] != 64:
            continue
        twin = next(x for x in rows if x['version'] == r['version'] and x['NR_CPUS'] == 4096
                    and x['input'] == r['input'] and x['L'] == r['L'])
        if twin['decisions'] != r['decisions'] or twin['facts']['possible_set'] != r['facts']['possible_set']:
            branch_differences.append({'version': r['version'], 'input': r['input'], 'L': r['L'],
                                       'NR64': {'possible': r['facts']['possible_set'], 'decisions': r['decisions']},
                                       'NR4096': {'possible': twin['facts']['possible_set'], 'decisions': twin['decisions']}})
    results = {'core_sha256': CORE_SHA, 'core_evaluations': len(inputs), 'records': len(rows),
               'decision_counts': counts, 'branch_differences': branch_differences, 'rows': rows,
               'deadline_all_insufficient': all(v == 'insufficient' for r in rows for k, v in r['deadline'].items()
                                                     if r['decisions'][k] != 'not_applicable'),
               'not_independent_accuracy': True, 'new_kernel_builds': 0, 'new_boots': 0, 'model_calls': 0}
    (out / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'core_evaluations': len(inputs), 'decision_counts': counts,
                      'branch_differences': len(branch_differences),
                      'deadline_all_insufficient': results['deadline_all_insufficient']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
