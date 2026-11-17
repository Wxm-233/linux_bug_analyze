"""List held-out candidates (criteria.md section 2): rule flags from earlier runs that are neither among the 41
reviewed items of llm_review_rule_flags_20261103 nor labelled in any earlier review. No git, no model."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCES = [('v6.6', 'mech_rules_riscv_20261103/flags_run2.json'),
           ('v6.6', 'rules_v2_unified_20261103/flags_dev_v6.6_run2.json'),
           ('v6.12', 'rules_v2_unified_20261103/flags_dev_v6.12_run2.json')]


def key(f):
    if f['rule'] == 'CTX':
        parts = f['reason'].split(' ')
        return ('CTX', f['name'], f['reason'].split('-> ')[-1].strip(), parts[4] if len(parts) > 4 else '')
    if f['rule'] == 'R1':
        return ('R1', f['name'])
    return (f['rule'], f['name'])


def main():
    seen = {tuple(it['key']) for it in json.loads((ROOT / 'llm_review_rule_flags_20261103/items.json').read_text(encoding='utf-8'))}
    # anything labelled earlier (by function name and rule family) is also excluded
    labelled = set()
    for r in json.loads((ROOT / 'ctx_rules_riscv_20261103/manual_review.json').read_text(encoding='utf-8'))['rows']:
        f = json.loads((ROOT / 'ctx_rules_riscv_20261103/flags_run2.json').read_text(encoding='utf-8'))['flags'][r['i']]
        labelled.add(('CTX', f['function'], f['sink'], f['call']))
    for r in json.loads((ROOT / 'mech_rules_riscv_20261103/review_sample.json').read_text(encoding='utf-8')):
        labelled.add((r['rule'], r['name']))
    for f in json.loads((ROOT / 'rules_v2_forward_end_20261103/flags_end.json').read_text(encoding='utf-8'))['flags']:
        labelled.add(key(f))
    out, keys = [], set()
    for snap, p in SOURCES:
        for f in json.loads((ROOT / p).read_text(encoding='utf-8'))['flags']:
            k = key(f)
            if k in seen or k in labelled or k in keys:
                continue
            keys.add(k)
            out.append({'snapshot': snap, 'source': p, **{x: f.get(x) for x in ('rule', 'path', 'name', 'start', 'end', 'reason', 'chain', 'refs', 'kind', 'source')}, 'key': list(k)})
    (HERE / 'candidates.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    for k, c in enumerate(out):
        print(k, c['snapshot'], c['rule'], c['path'].replace('arch/riscv/', ''), c['name'], '|', c['reason'][:90])


if __name__ == '__main__':
    main()
