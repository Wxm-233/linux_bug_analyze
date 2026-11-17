"""Scoring of a rules2.py flags file (criteria.md sections 2-4). WSL (git).
  python3 score2.py dev FLAGS.json      snapshot v6.6 or v6.12 (from the file): labelled positives of that window
  python3 score2.py eval FLAGS.json     snapshot v6.1: Fixes commits in v6.1..v6.6 touching arch/riscv; once
A hit is a fix whose old-side lines, mapped back to the snapshot (mech_rules_riscv_20261103/score.py to_snap), fall
in a flag's range or, for CTX, in a function on its chain.
"""
from pathlib import Path
import importlib.util
import json
import re
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ms', HERE.parent / 'mech_rules_riscv_20261103' / 'score.py')
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)
WINDOWS = {'v6.6': ('2023-10-30', '2024-11-17'), 'v6.12': ('2024-11-18', '2099-01-01')}
EVAL_SNAP, EVAL_END = 'v6.1', 'v6.6'


def hit(flag, sha):
    fl = S.fix_lines(sha)
    spans = [(flag['path'], flag['start'] - 4, flag['end'])]  # amendment 1b: include the signature lines
    for c in flag.get('chain') or []:
        rg = S.func_range(c[0], c[1])
        if rg:
            spans.append((c[0], rg[0] - 4, rg[1]))
    return any(any(s <= x <= e for x in fl.get(p, ())) for p, s, e in spans)


def summary(flags, hits_by_flag):
    out = {}
    for rule in ('CTX', 'R7', 'R10'):
        fs = [f for f in flags if f['rule'] == rule]
        hit_issues = sorted({f['issue'] for i, f in enumerate(flags) if f['rule'] == rule and hits_by_flag.get(i)})
        out[rule] = {'flags': len(fs), 'issues': len({f['issue'] for f in fs}), 'issues_hit': hit_issues}
    return out


def main():
    mode, flags_file = sys.argv[1], sys.argv[2]
    data = json.loads((HERE / flags_file).read_text(encoding='utf-8'))
    snap, flags = data['stats']['snapshot'], data['flags']
    S.SNAP = snap
    if mode == 'dev':
        lo, hi = WINDOWS[snap]
        labels = json.loads(S.LABELS.read_text(encoding='utf-8'))
        pos = [r for r in labels if r['cross'] == 'C' and r['flag'] not in ('无关', '构建错误') and lo <= r['date'] <= hi]
        commits = [(r['commit'], r['id'], r['mechanism']) for r in pos]
    else:
        if snap != EVAL_SNAP:
            raise SystemExit('eval needs the v6.1 flags')
        if (HERE / 'scores_eval.json').exists():
            raise SystemExit('evaluation already scored once; preserve')
        log = S.M.git('log', '--format=%h %s', '--grep=Fixes:', f'{EVAL_SNAP}..{EVAL_END}', '--', 'arch/riscv')
        commits = [(l.split(' ', 1)[0], l.split(' ', 1)[1], '') for l in log.splitlines() if l.strip()]
    hits_by_flag, rows = {}, []
    for sha, ident, mech in commits:
        hs = [i for i, f in enumerate(flags) if hit(f, sha)]
        for i in hs:
            hits_by_flag.setdefault(i, []).append(sha)
        if hs:
            rows.append({'commit': sha, 'id': ident, 'mechanism': mech,
                         'flags': [{'rule': flags[i]['rule'], 'issue': flags[i]['issue'],
                                    'where': f'{flags[i]["path"]}:{flags[i]["name"]}',
                                    'reason': flags[i]['reason'][:200]} for i in hs]})
    out = {'mode': mode, 'snapshot': snap, 'outcomes': len(commits), 'by_rule': summary(flags, hits_by_flag),
           'hits': rows}
    name = 'scores_eval.json' if mode == 'eval' else f'scores_dev_{Path(flags_file).stem}.json'
    (HERE / name).write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(out['by_rule'], indent=1, ensure_ascii=False), out['outcomes'])
    for r in rows:
        print(r['commit'], r['id'][:70], r['mechanism'], [(x['rule'], x['where'].split(':')[-1]) for x in r['flags']][:4])


if __name__ == '__main__':
    main()
