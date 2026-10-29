"""Rebuild the cross-architecture sibling candidate set (plan.md): strict targets, patch-id dedupe, three pair types,
contact flags, a blank screening sheet and the earlier Claude labels kept apart. WSL; no model calls; prints counts only.
Outputs: sibling_dataset.json, screening_sheet.csv, claude_labels.json, label_impact.json.
"""
from pathlib import Path
import csv
import itertools
import json
import random
import sys

HERE = Path(__file__).resolve().parent
C = HERE.parent
INNER = HERE.parents[2]
sys.path.insert(0, str(INNER))
sys.path.insert(0, str(C / 'xarch_source_v419_20261029'))
import count_v419 as V  # noqa: E402
from linux_bug_analyze.sibling_pairs import named_spans, patch_id  # noqa: E402

X = V.X
X.RANGE = 'v4.0..df2908090cda'
V.HERE = HERE
V.PROGRAM_LISTS = V.PROGRAM_LISTS | {C / 'xarch_source_v419_20261029' / 'xarch_pairs_v419.json', C / 'p1pp_design_20261029' / 'holdout_pool.json'}
HUNK = X.body_targets.__globals__['HUNK']


def body_targets_strict(t, s):
    """count_pool.body_targets with the strict function index (sibling_pairs.named_spans)."""
    hunks, path = {}, None
    for line in X.git('show', '--format=', '-U0', '--no-renames', t).splitlines():
        if line.startswith('--- '):
            path = line[6:] if line.startswith('--- a/') and line.endswith(('.c', '.h')) else None
        elif path and (m := HUNK.match(line)):
            hunks.setdefault(path, []).append((int(m.group(1)), int(m.group(2) or 1)))
    files = sorted(hunks)
    blobs = X.body_targets.__globals__['blobs']
    parent = blobs(['%s^:%s' % (t, f) for f in files])
    snap = blobs(['%s:%s' % (s, f) for f in files])
    out = set()
    for f in files:
        kp, ks = '%s^:%s' % (t, f), '%s:%s' % (s, f)
        if kp not in parent or ks not in snap:
            continue
        sp = named_spans(parent[kp])
        at_s = {h for _, _, h in named_spans(snap[ks])}
        for a, b in hunks[f]:
            for st, en, h in sp:
                inside = (st <= a < en) if b == 0 else any(st < l < en for l in range(a, a + b))
                if inside and h in at_s:
                    out.add((f, h))
    return out


def main():
    target = HERE / 'sibling_dataset.json'
    if target.exists():
        raise SystemExit('preserve')
    fixers = X.log_fixes()
    res = X.resolve({t for r in fixers.values() for t in r['fixes']})
    groups = {}
    for h, r in fixers.items():
        for x in sorted({res[t] for t in r['fixes'] if t in res}):
            groups.setdefault(x, []).append(h)
    cache = dict(fixers)
    raw = {'A_common_cause': [], 'B_fix_of_fix': [], 'B_introducer': []}
    for x, hs in groups.items():
        hs = sorted(set(hs), key=lambda h: (fixers[h]['time'], h))
        if not x.startswith(X.ROOT_COMMIT):
            raw['A_common_cause'] += [(s, t, x) for s, t in itertools.combinations(hs, 2)]
        raw['B_fix_of_fix' if x in fixers else 'B_introducer'] += [(x, t, x) for t in hs]
    funnel = {k: dict.fromkeys(['pairs', 'arch', 'disjoint_arch', 'valid_target', 'not_all_seed'], 0) for k in raw}
    final = []
    for typ, pairs in raw.items():
        for s, t, x in pairs:
            funnel[typ]['pairs'] += 1
            sm, tm = X.meta_of(s, cache), X.meta_of(t, cache)
            sa, ta = X.arches(sm['files']), X.arches(tm['files'])
            if not sa or not ta:
                continue
            funnel[typ]['arch'] += 1
            if not ta - sa:
                continue
            funnel[typ]['disjoint_arch'] += 1
            xt = sorted(y for y in body_targets_strict(t, s) if X.arch_of(y[0]) and X.arch_of(y[0]) not in sa)
            if not xt:
                continue
            funnel[typ]['valid_target'] += 1
            if set(xt) <= X.changed_functions(s):
                continue
            funnel[typ]['not_all_seed'] += 1
            final.append({'type': typ, 'seed': s, 'target': t, 'x': x, 'time_s': sm['time'], 'time_t': tm['time'],
                          'different_author': sm['author'] != tm['author'], 'xarch_targets': xt})
    chosen = {}
    for f in final:
        key = (f['target'], f['type'])
        if f['type'] == 'A_common_cause' and f['time_s'] >= f['time_t']:
            continue
        if key not in chosen or (f['time_s'], f['seed']) > (chosen[key]['time_s'], chosen[key]['seed']):
            chosen[key] = f
    rows = sorted(chosen.values(), key=lambda f: (f['time_t'], f['target'], f['type']))
    pids = {}
    for f in rows:
        for h in (f['seed'], f['target']):
            if h not in pids:
                pids[h] = patch_id(X.REPO, h)
    seen, dups = {}, 0
    for f in rows:
        key = (pids[f['seed']], pids[f['target']], f['type'])
        f['self_duplicate'] = pids[f['seed']] is not None and pids[f['seed']] == pids[f['target']]
        f['dup_of'] = seen.get(key)
        if f['dup_of'] is None:
            seen[key] = f['target']
        else:
            dups += 1
    dev = json.loads((C / 'p1prime_20261029' / 'p1prime_sample.json').read_text())['sample']
    hold = json.loads((C / 'p1pp_design_20261029' / 'holdout_pool.json').read_text())['usable']
    dev_c = {h for p in dev for h in (p['seed'], p['target'])}
    hold_c = {h for p in hold for h in (p['seed'], p['target'])}
    p0b = json.loads((C / 'p0b_20261029' / 'pairs_b.json').read_text())
    p0b_dev = {h for p in p0b['dev'] for h in (p['seed'], p['target'])}
    held = sorted(p0b['held_out'], key=lambda p: (p['seed'], p['target']))
    random.Random(20261030).shuffle(held)
    p1_seen = {h for p in held[:124] for h in (p['seed'], p['target'])}
    listed = set()
    for name in ('frozen_sample.txt', 'contacted_candidates.txt', 'family_linked_candidates.txt'):
        listed |= set((X.s3.S1 / name).read_text().split())
    cand = {h for f in rows for h in (f['seed'], f['target'])}
    alltime, scan_info = V.scan(cand, 0)
    other = (p0b_dev | p1_seen | listed | alltime) - dev_c - hold_c
    for f in rows:
        ends = {f['seed'], f['target']}
        f['dev_used'] = bool(ends & dev_c)
        f['holdout_read'] = bool(ends & hold_c)
        f['contacted_other'] = bool(ends & other)
    uniq = [f for f in rows if f['dup_of'] is None and not f['self_duplicate']]
    for i, f in enumerate(uniq, 1):
        f['id'] = 'S%03d' % i
    subject = lambda h: X.git('log', '-1', '--format=%s', h).strip()
    with open(HERE / 'screening_sheet.csv', 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['id', 'type', 'seed', 'seed_subject', 'target', 'target_subject', 'xarch_targets', 'view', 'dev_used', 'holdout_read',
                    'contacted_other', 'sibling(yes/partial/no)', 'seed_role(fix/culprit)', 'note'])
        for f in uniq:
            w.writerow([f['id'], f['type'], f['seed'][:12], subject(f['seed']), f['target'][:12], subject(f['target']),
                        '; '.join('%s:%s' % t for t in f['xarch_targets']), 'git show %s; git show %s' % (f['seed'][:12], f['target'][:12]),
                        int(f['dev_used']), int(f['holdout_read']), int(f['contacted_other']), '', '', ''])
    labels = []
    dev_aud = {p['n']: p for p in json.loads((C / 'p1prime_20261029' / 'run' / 'audit_first20.json').read_text())['pairs']}
    for n, p in enumerate(dev, 1):
        if n in dev_aud:
            labels.append({'set': 'p1prime_dev', 'n': n, 'seed': p['seed'], 'target': p['target'], 'sibling': dev_aud[n]['sibling'], 'seed_role': dev_aud[n]['seed_role']})
    hold_aud = {p['n']: p for p in json.loads((C / 'holdout_diff_20261029' / 'audit_holdout22.json').read_text())['pairs']}
    for n, p in enumerate(hold, 1):
        labels.append({'set': 'holdout22', 'n': n, 'seed': p['seed'], 'target': p['target'], 'sibling': hold_aud[n]['sibling'], 'seed_role': hold_aud[n]['seed_role']})
    (HERE / 'claude_labels.json').write_text(json.dumps({'note': 'Claude single-annotator labels; kept apart from the blank screening sheet for an independent second annotation.', 'labels': labels}, indent=1) + '\n')
    impact = {'changed': 0, 'became_empty': 0, 'pairs': 0}
    for p, old in [(p, p['t_targets']) for p in dev] + [(p, p['xarch_targets']) for p in hold]:
        sa = X.arches(X.meta_of(p['seed'], cache)['files'])
        new = sorted(y for y in body_targets_strict(p['target'], p['seed']) if X.arch_of(y[0]) and X.arch_of(y[0]) not in sa)
        impact['pairs'] += 1
        impact['changed'] += sorted(map(tuple, old)) != new
        impact['became_empty'] += not new
    (HERE / 'label_impact.json').write_text(json.dumps(impact, indent=1) + '\n')
    by_type = {t: sum(f['type'] == t for f in uniq) for t in raw}
    out = {'range': X.RANGE, 'fixers_in_range': len(fixers), 'funnel': funnel, 'per_target_type': len(rows), 'duplicates': dups,
           'self_duplicates': sum(f['self_duplicate'] for f in rows), 'unique': len(uniq), 'unique_by_type': by_type,
           'unique_distinct_targets': len({f['target'] for f in uniq}),
           'flags': {'dev_used': sum(f['dev_used'] for f in uniq), 'holdout_read': sum(f['holdout_read'] for f in uniq),
                     'contacted_other': sum(f['contacted_other'] for f in uniq),
                     'untouched': sum(not (f['dev_used'] or f['holdout_read'] or f['contacted_other']) for f in uniq)},
           'scan': scan_info, 'label_impact': impact}
    target.write_text(json.dumps({**out, 'pairs': rows}, indent=1) + '\n')
    print(json.dumps(out))


if __name__ == '__main__':
    main()
