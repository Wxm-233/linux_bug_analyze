"""P1 post-hoc diagnosis (not registered): why each M5 miss missed. WSL; reads p1_results.json and p1_sample.json only.
Category per pair, first applicable: label_unavailable (no target function body found at snapshot S), scope_miss (no target
file inside the pattern's scope), match_miss (no target body matches every `match` regex), fixed_excluded (a target matches
every `match` but also a `fixed` regex), seed_excluded (a qualifying target is an S-changed function), rank_cut (a target
qualifies but is outside the top 20). Output: miss_diagnosis.json.
"""
from pathlib import Path
import json
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import score_p1 as S  # noqa: E402


def main():
    target = HERE / 'miss_diagnosis.json'
    if target.exists():
        raise SystemExit('preserve')
    rows = json.loads((HERE.parent / 'p1_results.json').read_text())['rows']
    sample = json.loads((HERE.parent / 'p1_sample.json').read_text())['sample']
    out, counts = [], {}
    for row, pair in zip(rows, sample):
        if row['hit']['m5']:
            continue
        pat = row['m5'].get('pattern') or {}
        globs = [S.glob_regex(g) for g in pat.get('scope', [])]
        files = sorted({f for f, _ in pair['t_targets']})
        texts = S.read_files(pair['seed'], files)
        excluded = {tuple(x) for x in pair['s_changed']}
        found, in_scope, matched, unfixed, kept = 0, 0, 0, 0, 0
        for f, fn in pair['t_targets']:
            bodies = [b for n, _, b in S.functions(texts.get(f, '')) if n == fn]
            if not bodies:
                continue
            found += 1
            if not any(g.match(f) for g in globs):
                continue
            in_scope += 1
            if not all(re.search(m, bodies[0]) for m in pat.get('match', [])):
                continue
            matched += 1
            if any(re.search(x, bodies[0]) for x in pat.get('fixed', [])):
                continue
            unfixed += 1
            kept += (f, fn) not in excluded
        cat = ('pattern_' + row['m5']['status'] if row['m5']['status'] != 'ok' else
               'label_unavailable' if not found else 'scope_miss' if not in_scope else 'match_miss' if not matched else
               'fixed_excluded' if not unfixed else 'seed_excluded' if not kept else 'rank_cut')
        counts[cat] = counts.get(cat, 0) + 1
        out.append({'n': row['n'], 'category': cat, 'targets': len(pair['t_targets']), 'found': found, 'in_scope': in_scope,
                    'matched': matched, 'unfixed': unfixed, 'scope_files': row['m5'].get('scope_files'), 'm5_matched': row['m5'].get('matched')})
    target.write_text(json.dumps({'counts': counts, 'rows': out}, indent=1) + '\n')
    print(json.dumps(counts))


if __name__ == '__main__':
    main()
