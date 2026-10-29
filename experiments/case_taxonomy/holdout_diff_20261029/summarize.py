"""Stratified B3@20 summary from features.json (plan.md). Output: summary.json; prints it."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent


def main():
    rows = json.loads((HERE / 'features.json').read_text())
    rate = lambda rs: [len(rs), sum(r['b3_20'] for r in rs)]
    out = {}
    for st in ('dev', 'holdout'):
        rs = [r for r in rows if r['set'] == st]
        d = {'all': rate(rs)}
        for k in ('same_rel_target', 'same_dir_target', 'same_name_target', 'b3_pool_empty', 'early', 's_touches_common'):
            d[k] = {'true': rate([r for r in rs if r[k]]), 'false': rate([r for r in rs if not r[k]])}
        d['sibling'] = {lab: rate([r for r in rs if r['sibling'] == lab]) for lab in ('yes', 'partial', 'no')}
        d['source'] = {src: rate([r for r in rs if r['source'] == src]) for src in ('A', 'B')}
        d['generic_ids_ge3'] = {'true': rate([r for r in rs if r['generic_ids'] >= 3]), 'false': rate([r for r in rs if r['generic_ids'] < 3])}
        d['label_issue'] = rate([r for r in rs if r['label_issue']])
        d['same_rel_or_dir'] = {'true': rate([r for r in rs if r['same_rel_target'] or r['same_dir_target']]),
                                'false': rate([r for r in rs if not (r['same_rel_target'] or r['same_dir_target'])])}
        out[st] = d
    (HERE / 'summary.json').write_text(json.dumps(out, indent=1) + '\n')
    for st, d in out.items():
        print('==', st)
        for k, v in d.items():
            print(' ', k, v)


if __name__ == '__main__':
    main()
