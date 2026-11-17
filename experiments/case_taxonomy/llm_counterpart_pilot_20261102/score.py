"""Scoring (criteria.md section 3 with criteria_amendment1.md). WSL (git needed for the later-fix check and the F1
comparison). Labels are read only here. Output: flags.json, scores.json, manual_review_sample.json.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from math import comb
import json
import random
import re

import locate as L
from common import CALLS, HERE, ROOT, W_END, W_START, git, parse_answer

LABELS = ROOT / 'cross_arch_sample_set_20261102' / 'labels_v2_1.json'
EVAL = ROOT / 'method_eval_testset_20261102' / 'results.json'
END = 'df2908090cda'


def fisher(a, b, c, d):
    n, r1, c1 = a + b + c + d, a + b, a + c
    p = lambda x: comb(r1, x) * comb(n - r1, c1 - x) / comb(n, c1)
    obs = p(a)
    lo, hi = max(0, c1 - (n - r1)), min(r1, c1)
    return round(min(1.0, sum(p(x) for x in range(lo, hi + 1) if p(x) <= obs * (1 + 1e-9))), 4) if n else 1.0


def later_fixed(path, name, since):
    """Fixes-tagged commit after `since` (before END) that changed function `name` in `path`."""
    out = git('log', '--format=%H %cI', f'--since={since}', '-s', '-L', f':{name}:{path}', END)
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and re.fullmatch(r'[0-9a-f]{40}', parts[0]) and parts[1] > since:
            if re.search(r'^\s*Fixes:', git('log', '-1', '--format=%B', parts[0]), re.M | re.I):
                return parts[0][:12]
    return None


def flags_from(store, refs):
    flags, unflagged = [], []
    for rid, loc in store.items():
        if 'error' in loc or not loc.get('picked'):
            continue
        ans = parse_answer(CALLS / f's2d_{rid}') or {}
        verdicts = ans.get('verdicts') if isinstance(ans.get('verdicts'), list) else []
        by = {f'{p["path"]}:{p["name"]}': p for p in loc['picked']}
        flagged = set()
        for v in verdicts:
            if not isinstance(v, dict):
                continue
            key = str(v.get('candidate', '')).strip()
            p = by.get(key)
            lines = [x for x in v.get('lines') or [] if isinstance(x, int)]
            if (p and v.get('applies') == 'yes' and v.get('guarantee_provided') == 'no'
                    and any(p['start'] <= x <= p['end'] for x in lines)):
                flags.append({'ref': rid, 'ref_date': refs[rid]['date'], 'path': p['path'], 'function': p['name'],
                              'route': p['route'], 'lines': lines, 'why': v.get('why', '')})
                flagged.add(key)
        for x in loc.get('rule_flags', []):
            key = f'{x["file"]}:{x["function"]}'
            if key not in flagged:
                flags.append({'ref': rid, 'ref_date': refs[rid]['date'], 'path': x['file'], 'function': x['function'],
                              'route': 'M2规则', 'lines': [x['line']], 'why': x['verdict']})
                flagged.add(key)
        unflagged += [{'ref': rid, 'ref_date': refs[rid]['date'], 'path': p['path'], 'function': p['name']}
                      for k, p in by.items() if k not in flagged]
    return flags, unflagged


def added_names(sha):
    """Function or macro names a fix defines in arch/riscv ('+' lines), for matching M1 flags on defaults."""
    names = set()
    for l in git('show', '--format=', sha, '--', 'arch/riscv').splitlines():
        if l.startswith('+') and not l.startswith('+++'):
            m = re.match(r'\+\s*#\s*define\s+([A-Za-z_]\w*)', l) or re.match(r'\+[A-Za-z_].*?([A-Za-z_]\w*)\s*\(', l)
            if m:
                names.add(m.group(1))
    return names


def f1_window(refs):
    """F1 rule applied forward in W: for each P1 ref, every other-arch .c function it changes that has a same-name
    RISC-V .c definition at the ref's version gives a flag (ref, RISC-V path, name)."""
    out = []
    for r in refs.values():
        if not r['P1']:
            continue
        changed, _ = L.ref_changes(r['sha'])
        rev = L.ref_rev(r['sha'])
        names = [n for p, n in changed if p.startswith(L.REF_PREFIXES) and p.endswith('.c')
                 and n not in L.GENERIC and not n.endswith('__init')]
        for n, paths in L.definitions(rev, names, ('arch/riscv/*.c',)).items():
            out += [{'ref': r['id'], 'ref_date': r['date'], 'path': p, 'function': n} for p in paths]
    return out


def main():
    refs = {r['id']: r for r in json.loads((HERE / 'refs.json').read_text(encoding='utf-8'))}
    store = json.loads((HERE / 'locate.json').read_text(encoding='utf-8'))
    s1 = json.loads((HERE / 'stage1_summary.json').read_text(encoding='utf-8'))
    flags, unflagged = flags_from(store, refs)
    f1 = f1_window(refs)
    with ThreadPoolExecutor(max_workers=8) as pool:
        for rows in (flags, unflagged, f1):
            for r, fx in zip(rows, pool.map(lambda r: later_fixed(r['path'], r['function'], r['ref_date']), rows)):
                r['later_fixed'] = fx
    labels = {r['id']: r for r in json.loads(LABELS.read_text(encoding='utf-8'))}
    funcs = {r['id']: r['functions'] for r in json.loads(EVAL.read_text(encoding='utf-8'))}
    pos = [r for r in labels.values() if not r['dev'] and r['flag'] not in ('无关', '构建错误') and r['cross'] == 'C'
           and r['date'] >= W_START]

    def hits(rows, strict):
        found = []
        for p in pos:
            fix_date = p['date']
            fx = [f.rsplit(':', 1) for f in funcs.get(p['id'], [])]
            files = {f for f in p['files'] if f.startswith('arch/riscv/')}
            for f in rows:
                if f['ref_date'][:10] >= fix_date:
                    continue
                if not f['path'].startswith('arch/riscv/'):  # M1 flag on a common default
                    ok = f['function'] in added_names(p['commit'])
                else:
                    ok = [f['path'], f['function']] in fx if strict else f['path'] in files
                if ok:
                    found.append({'id': p['id'], 'ref': f['ref'], 'lead_days': (date.fromisoformat(fix_date) -
                                                                               date.fromisoformat(f['ref_date'][:10])).days})
                    break
        return found

    def located(route=None):
        found = []
        for p in pos:
            fx = [f.rsplit(':', 1) for f in funcs.get(p['id'], [])]
            for rid, loc in store.items():
                if 'error' in loc or refs[rid]['date'][:10] >= p['date']:
                    continue
                cands = [c for c in loc.get('all_candidates', []) if route is None or c['route'] == route]
                if any([c['path'], c['name']] in fx for c in cands):
                    found.append(p['id'])
                    break
        return found

    a_ok = sum(all(store[r].get('stage2a', {}).get(k) for k in ('condition', 'guarantee', 'kind', 'hooks'))
               for r in store)
    fl, uf = sum(bool(f['later_fixed']) for f in flags), sum(bool(u['later_fixed']) for u in unflagged)
    out = {
        'stage1': {k: s1[k] for k in ('refs', 'answers', 'passed')} | {'no_answer': len(s1['no_answer']),
                                                                      'stage2_refs': len(s1['chosen'])},
        'stage2a_complete': [a_ok, len(store)],
        'stage2b': {'with_candidates': sum(bool(v.get('picked')) for v in store.values()),
                    'errors': sum('error' in v for v in store.values()),
                    'candidates_by_route': {r: sum(c['route'] == r for v in store.values()
                                                   for c in v.get('all_candidates', [])) for r in (1, 2, 3)}},
        'stage2d': {'flags': len(flags), 'unflagged_candidates': len(unflagged),
                    'no_answer': sum(1 for r, v in store.items() if v.get('picked') and
                                     parse_answer(CALLS / f's2d_{r}') is None)},
        'positives_since_window': len(pos),
        'hits_strict': hits(flags, True), 'hits_loose': hits(flags, False),
        'located_any': located(), 'located_by_route': {r: located(r) for r in (1, 2, 3)},
        'by_dispatch': {m: {'refs': sum(v.get('dispatch') == m for v in store.values()),
                            'flags': sum(1 for f in flags if store[f['ref']].get('dispatch') == m)}
                        for m in ('M1', 'M2', 'M5', 'M8', 'M10', 'generic')},
        'later_fixed': {'flagged': [fl, len(flags)], 'unflagged': [uf, len(unflagged)],
                        'fisher_p': fisher(fl, len(flags) - fl, uf, len(unflagged) - uf)},
        'F1_window': {'flags': len(f1), 'later_fixed': sum(bool(x['later_fixed']) for x in f1),
                      'hits_strict': hits(f1, True)},
    }
    rate = lambda k, n: k / n if n else 0
    out['reference_line'] = ('值得扩大' if len(out['hits_strict']) >= 3 and rate(fl, len(flags)) >= 2 * rate(uf, len(unflagged))
                             and out['later_fixed']['fisher_p'] < 0.05 else '未达到')
    (HERE / 'flags.json').write_text(json.dumps({'flags': flags, 'unflagged': unflagged, 'F1': f1}, indent=1,
                                                ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'scores.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    sample = flags if len(flags) <= 20 else random.Random(20261104).sample(flags, 20)
    (HERE / 'manual_review_sample.json').write_text(json.dumps(sample, indent=1, ensure_ascii=False) + '\n',
                                                    encoding='utf-8')
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
