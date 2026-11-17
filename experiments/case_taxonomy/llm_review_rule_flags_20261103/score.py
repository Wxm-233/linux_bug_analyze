"""Scoring (criteria.md section 4). Windows or WSL, no git. Output: scores.json, answers.json."""
from collections import Counter
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-03' / 'llm_review_rule_flags_20261103'


def parse(d):
    p = CALLS / d / 'final.md'
    if not p.exists():
        return None
    text = p.read_text(encoding='utf-8', errors='replace')
    dec = json.JSONDecoder()
    for k in range(len(text) - 1, -1, -1):
        if text[k] == '{':
            try:
                obj, _ = dec.raw_decode(text, k)
            except ValueError:
                continue
            if isinstance(obj, dict) and 'verdict' in obj:
                return obj
    return None


def rates(rows):
    real = [r for r in rows if r['label'] == 'a']
    fa = [r for r in rows if r['label'] == 'b']
    kept = [r for r in rows if r['verdict'] != 'false_alarm']
    return {'real': len(real), 'false': len(fa),
            'keep_rate': round(sum(r['verdict'] != 'false_alarm' for r in real) / len(real), 3) if real else None,
            'remove_rate': round(sum(r['verdict'] == 'false_alarm' for r in fa) / len(fa), 3) if fa else None,
            'precision_before': round(len(real) / len(rows), 3) if rows else None,
            'precision_after': round(sum(r['label'] == 'a' for r in kept) / len(kept), 3) if kept else None,
            'verdicts_real': dict(Counter(r['verdict'] for r in real)),
            'verdicts_false': dict(Counter(r['verdict'] for r in fa))}


def main():
    items = json.loads((HERE / 'items.json').read_text(encoding='utf-8'))
    rows = []
    for it in items:
        a = parse(it['dir'])
        v = str((a or {}).get('verdict', 'no_answer')).strip().lower()
        rows.append({'dir': it['dir'], 'src': it['src'], 'rule': it['rule'], 'name': it['name'], 'label': it['label'],
                     'basis': it['basis'], 'verdict': v, 'reason': (a or {}).get('reason', '')})
    out = {'all': rates(rows),
           'by_rule': {r: rates([x for x in rows if x['rule'] == r]) for r in sorted({x['rule'] for x in rows})},
           'by_basis': {b: rates([x for x in rows if x['basis'] == b]) for b in sorted({x['basis'] for x in rows})},
           'no_answer': sum(r['verdict'] == 'no_answer' for r in rows)}
    al = out['all']
    out['decision'] = {'keep_rate_ge_0.9': (al['keep_rate'] or 0) >= 0.9, 'remove_rate_ge_0.5': (al['remove_rate'] or 0) >= 0.5}
    (HERE / 'answers.json').write_text(json.dumps(rows, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'scores.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
