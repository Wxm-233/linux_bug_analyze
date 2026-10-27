"""Constructed controls on the P1/P3 envelopes; expected outcomes fixed here before running."""
from pathlib import Path
import copy
import json

import analyze

HERE = Path(__file__).resolve().parent


def main():
    out = HERE / 'controls'
    out.mkdir(exist_ok=False)
    res = json.loads((HERE / 'analysis/results.json').read_text())
    rows = {r['env']: r for r in res['rows']}

    def item(env, kind='P1_policy_reach', facts=None, basis=None):
        values = copy.deepcopy(facts or rows[env]['facts'])
        it = analyze.envelope('qemu_' + env, kind, values, HERE / 'analysis' / f'{env}.observation.json')
        if basis:
            for part in ('ledger', 'record'):
                it[part]['basis'] = basis
            for claim in it['ledger']['claims'].values():
                if claim['role'] == 'fact':
                    claim['origin'] = 'synthetic_assumption'
        return it

    cases = []
    it = item('tcg'); del it['record']['facts']['boot_possible_count']
    cases.append(('missing_possible_fact', it, False, 'insufficient'))
    it = item('tcg'); it['ledger']['context_id'] = 'qemu_kvm'
    cases.append(('tcg_record_with_kvm_ledger', it, False, 'insufficient'))
    it = item('kvm'); it['record']['facts']['boot_possible_count']['object_id'] = 'qemu_tcg.cpu_possible_domain'
    cases.append(('kvm_fact_bound_to_other_object', it, False, 'insufficient'))
    it = item('tcg'); it['ledger']['claims']['fact.boot_possible_count']['origin'] = 'model_proposal'
    cases.append(('unreviewed_model_fact', it, False, 'insufficient'))
    it = item('tcg'); it['ledger']['revision'] = '8f0b4cce4481fb22653697cced8d0d04027cb1e8'
    cases.append(('parent_revision_ledger', it, False, 'insufficient'))
    f = copy.deepcopy(rows['tcg']['facts']); f['qemu_guest_with_legacy_slots'] = False
    cases.append(('online_capable_table_scope', item('tcg', facts=f), False, 'not_applicable'))
    f = copy.deepcopy(rows['kvm']['facts']); f['boot_possible_count'] = 1
    cases.append(('synthetic_slots_dropped', item('kvm', facts=f, basis='synthetic'), True, 'violated'))
    f = copy.deepcopy(rows['tcg']['facts']); f['boot_possible_count'] = 4
    cases.append(('synthetic_slots_kept', item('tcg', facts=f, basis='synthetic'), True, 'satisfied'))
    cases.append(('synthetic_without_opt_in', item('tcg', facts=f, basis='synthetic'), False, 'insufficient'))
    f = copy.deepcopy(rows['kvm']['facts']); f['online_outside_boot_possible'] = [1]
    cases.append(('synthetic_online_outside_possible', item('kvm', 'P3_hotplug_consumption', f, 'synthetic'), True, 'violated'))

    results = []
    for name, it, allow, expected in cases:
        d = analyze.evaluate_contract(it['contract'], it['ledger'], it['record'], allow_synthetic=allow)
        got = d['relation_at_observation']
        results.append({'control': name, 'expected': expected, 'got': got, 'as_expected': got == expected, 'reasons': d['reasons'][:1]})
        (out / f'{name}.json').write_text(json.dumps({'input': it, 'decision': d}) + '\n')
    summary = {'controls': len(results), 'as_expected': sum(r['as_expected'] for r in results), 'results': results}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1) + '\n')
    print(json.dumps({'controls': summary['controls'], 'as_expected': summary['as_expected'],
                      'unexpected': [r for r in results if not r['as_expected']]}))


if __name__ == '__main__':
    main()
