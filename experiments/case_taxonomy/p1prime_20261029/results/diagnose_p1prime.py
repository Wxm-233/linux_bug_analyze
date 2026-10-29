"""P1' post-hoc diagnosis (not registered): why each M5 miss missed. WSL; reads run/p1prime_results.json and the sample only.
First applicable category: scope_miss (no target file inside scope within the candidate range), match_miss (no target body
matches every `match`), fixed_excluded (a target matches every `match` but also a `fixed`), rank_cut (a target qualifies but is
outside the top 20). Also counts M5 patterns that matched nothing. Output: miss_diagnosis.json.
"""
from pathlib import Path
import json
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'run'))
import score_p1prime as S  # noqa: E402


def main():
    target = HERE / 'miss_diagnosis.json'
    if target.exists():
        raise SystemExit('preserve')
    rows = json.loads((HERE.parent / 'run' / 'p1prime_results.json').read_text())['rows']
    sample = json.loads((HERE.parent / 'p1prime_sample.json').read_text())['sample']
    out, counts = [], {}
    for row, pair in zip(rows, sample):
        if row['hit']['m5']:
            continue
        pat = row['m5']['pattern']
        globs = [S.P.glob_regex(g) for g in pat['scope']]
        files = sorted({f for f, _ in pair['t_targets']})
        texts = S.P.read_files(pair['seed'], files)
        in_scope = matched = unfixed = 0
        for f, fn in pair['t_targets']:
            bodies = [b for n, _, b in S.P.functions(texts.get(f, '')) if n == fn]
            if not bodies or not any(g.match(f) for g in globs):
                continue
            in_scope += 1
            if not all(re.search(m, bodies[0]) for m in pat['match']):
                continue
            matched += 1
            if any(re.search(x, bodies[0]) for x in pat['fixed']):
                continue
            unfixed += 1
        cat = 'scope_miss' if not in_scope else 'match_miss' if not matched else 'fixed_excluded' if not unfixed else 'rank_cut'
        counts[cat] = counts.get(cat, 0) + 1
        out.append({'n': row['n'], 'category': cat, 'scope_files': row['m5'].get('scope_files'), 'm5_matched': row['m5'].get('matched'),
                    'targets': len(pair['t_targets']), 'in_scope': in_scope, 'matched': matched, 'unfixed': unfixed})
    summary = {'misses': len(out), 'categories': counts,
               'patterns_matching_nothing_all_pairs': sum(1 for r in rows if r['m5'].get('matched') == 0),
               'm5_only_hits_vs_b3': sum(1 for r in rows if r['hit']['m5'] and not r['hit']['b3']),
               'b3_fallback_dir_pairs': sum(1 for r in rows if r['b3'].get('fallback_dir'))}
    target.write_text(json.dumps({'summary': summary, 'rows': out}, indent=1) + '\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
