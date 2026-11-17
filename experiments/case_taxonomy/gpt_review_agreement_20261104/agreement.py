"""Agreement between GPT's blind review (each round's gpt_review/answers.csv) and the first annotator's labels of the
10 review packages. Labels are read from each round's own files; nothing is modified there. GPT's two-class `real`
was defined to include convention violations, so where the first annotator has three classes, convention is
compared as real. No git, no model. Output: agreement.json, disagreements.json."""
from collections import Counter
from pathlib import Path
import csv
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
AB = {'a': 'real', 'b': 'false_alarm'}


def load(p):
    return json.loads((ROOT / p).read_text(encoding='utf-8'))


def gpt(d):
    with open(ROOT / d / 'gpt_review' / 'answers.csv', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def kappa(pairs):
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n / n
    return round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0


def compare(rows, note=''):
    """rows: [(item, ours, gpt, ours_detail, gpt_reason)]"""
    pairs = [(o, g) for _, o, g, _, _ in rows]
    dis = [{'item': i, 'ours': o, 'gpt': g, 'ours_detail': od, 'gpt_reason': gr} for i, o, g, od, gr in rows if o != g]
    res = {'n': len(rows), 'agree': len(rows) - len(dis), 'rate': round((len(rows) - len(dis)) / len(rows), 3),
           'kappa': kappa(pairs), 'ours': dict(Counter(o for o, _ in pairs)), 'gpt': dict(Counter(g for _, g in pairs)),
           'confusion': dict(Counter(f'{o}->{g}' for o, g in pairs)), 'note': note}
    return res, dis


def main():
    out, dis = {}, {}

    # 1 fix strategy: follow, main action, layer, cites
    key = {r['id']: r for r in load('fix_strategy_20261104/gpt_review_key.json')}
    g = gpt('fix_strategy_20261104')
    fields = (('follow', lambda k, a: (k['follow'], a['follow'].strip())),
              ('main_action', lambda k, a: (k['action'][0], a['action'].split(';')[0].strip())),
              ('layer', lambda k, a: (k['layer'], a['layer'].strip())),
              ('cites', lambda k, a: (k['cites'], a['cites'].strip())),
              ('follow_F1_or_not', lambda k, a: (k['follow'] == 'F1', a['follow'].strip() == 'F1')))
    for field, get in fields:
        rows = [(a['id'], *get(key[a['id']], a), key[a['id']]['note'], a['reason']) for a in g]
        out[f'fix_strategy.{field}'], dis[f'fix_strategy.{field}'] = compare(rows)

    # 2 test round: four classes
    lab = {r['cand']: r for r in load('llm_review_v2_test_20261104/labels3.json')['rows']}
    g = gpt('llm_review_v2_test_20261104')
    rows = [(a['item'], lab[a['item']]['label3'], a['label'].strip(), lab[a['item']]['reason3'], a['reason']) for a in g]
    out['test_labels3'], dis['test_labels3'] = compare(rows)
    out['test_labels3_scored'], dis['test_labels3_scored'] = compare([r for r in rows if r[1] != 'unsure'],
                                                                      'first-annotator unsure left out')

    # 3 expand: GPT real/false_alarm vs the development three-class labels (amended), convention counted as real
    lab = {r['cand']: r for r in load('llm_review_v2_dev2_20261104/labels3_amended.json')['rows']}
    m = {'bug': 'real', 'convention': 'real', 'not_issue': 'false_alarm'}
    g = gpt('llm_review_expand_20261103')
    rows = []
    for a in g:
        r = lab[int(a['item'][3:])]
        rows.append((a['item'] + ' ' + r['name'], m[r['label3']], a['label'].strip(), r['label3'] + '：' + r['reason3'],
                     a['reason']))
    out['expand_vs_labels3'], dis['expand_vs_labels3'] = compare(rows, 'convention counted as real')

    # 4 RISC-V rule flags (a/b)
    items = load('llm_review_rule_flags_20261103/items.json')
    g = gpt('llm_review_rule_flags_20261103')
    rows = [(a['item'] + ' ' + it['name'], AB.get(it['label'], it['label']), a['label'].strip(),
             f"{it['label']} {it.get('basis', '')} {it.get('note', '')}", a['reason']) for it, a in zip(items, g)]
    out['rule_flags'], dis['rule_flags'] = compare(rows, 'labels as in items.json')

    # 5 RISC-V held-out 18
    rs = load('llm_review_facts_20261103/heldout_labels.json')['rows']
    g = gpt('llm_review_facts_20261103')
    rows = [(a['item'] + ' ' + r['name'], AB.get(r.get('label'), r.get('label')), a['label'].strip(),
             f"{r.get('label')} {r.get('basis', '')} {r.get('label_reason', r.get('note', ''))}", a['reason'])
            for r, a in zip(rs, g)]
    out['heldout18'], dis['heldout18'] = compare(rows)

    # 6-9 a/b/c rounds
    for name, d, src in (('ctx_v612', 'ctx_rules_riscv_20261103', 'rows'),
                         ('forward_end', 'rules_v2_forward_end_20261103', 'rows'),
                         ('mech_v66', 'mech_rules_riscv_20261103', 'rows'),
                         ('unified_v61', 'rules_v2_unified_20261103', 'issues')):
        mr = load(f'{d}/manual_review.json')[src]
        g = gpt(d)
        assert len(mr) == len(g), (name, len(mr), len(g))
        rows = [(a['item'] + ' ' + str(r.get('issue', r.get('name', ''))), r['label'], a['label'].strip(),
                 r.get('reason', ''), a['reason']) for r, a in zip(mr, g)]
        out[name], dis[name] = compare(rows)
        if name == 'forward_end':
            m2 = {'a': 'real', 'a2': 'real', 'b': 'b', 'c': 'c'}
            rows2 = [(i, m2[o], m2[x], od, gr) for i, o, x, od, gr in rows]
            out['forward_end_real'], dis['forward_end_real'] = compare(rows2, 'a and a2 merged')

    # 10 judge
    mr = load('judge_bench_context_20261103/manual_review.json')['rows']
    g = gpt('judge_bench_context_20261103')
    rows = [(a['id'], r['label'], a['label'].strip(), r['reason'], a['reason']) for r, a in zip(mr, g)]
    out['judge_context'], dis['judge_context'] = compare(rows)

    (HERE / 'agreement.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'disagreements.json').write_text(json.dumps(dis, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    for k, v in out.items():
        print(f"{k:30s} {v['agree']}/{v['n']} kappa={v['kappa']} ours={v['ours']} gpt={v['gpt']}")


if __name__ == '__main__':
    main()
