"""E4 top-up sampling (evaluation_protocol_addendum_3b.md). WSL; diffs read by program only; prints counts only.

check  : M3-filtered scope on the addendum-3 phase-B samples must reproduce m3_20261028/phase_b_screen.json
select : current reserve -> seed 20261030 order -> M3-filtered scope -> 17 new samples (cap 20 000) -> controls;
         evaluation set C = the 3 in-scope phase-B samples (their addendum-3 controls) + the 17 new ones
"""
from pathlib import Path
import hashlib
import json
import random
import re
import sys

HERE = Path(__file__).resolve().parent
C = HERE.parent
sys.path.insert(0, str(C / 'scoped_sampling_20261028'))
import scoped_select as s3  # noqa: E402  (git, hunks, GEOM/LIMIT/CMP, recent_contacts, control lookback)

SEED, WANT_NEW, SCAN_CAP = 20261030, 17, 20_000
EXCLUDED_DIRS = ('tools/', 'scripts/', 'samples/')


def m3_scope(h):
    """Same rules as m3_20261028/m3_eval.py screen (addendum 3 B + clarification 1 + M3 section 4)."""
    hunks = s3.hunks(h)
    consumers = sorted(p for p in hunks if p.endswith('.c') and not p.startswith(('arch/',) + EXCLUDED_DIRS))
    rules = []
    if consumers:
        for path, blocks in hunks.items():
            if path.startswith('include/') and path.endswith('.h'):
                for block in blocks:
                    body = [l[1:] for l in block]
                    for k, l in enumerate(body):
                        m = re.match(r'\s*#\s*(?:ifndef\s+(\w+)|if\s+!\s*defined\s*\(?\s*(\w+))', l)
                        name = m and (m.group(1) or m.group(2))
                        if not name or re.search(r'_H(?:_|__)?$', name):
                            continue
                        nxt = [x for x in body[k + 1:] if x.strip()][:3]
                        if any(re.match(r'\s*#\s*define\s+%s\b' % re.escape(name), x) for x in nxt):
                            rules.append('S-F1.1')
        for path in consumers:
            for block in hunks[path]:
                for l in block:
                    if l[:1] not in '+-':
                        continue
                    code = l[1:]
                    m = re.match(r'\s*#\s*(?:if|ifdef|ifndef|elif)\b(.*)$', code)
                    if m:
                        if [t for t in re.findall(r'\b[A-Za-z_]\w*\b', m.group(1)) if t != 'defined' and not t.startswith('CONFIG_') and not t.endswith('_H')]:
                            rules.append('S-F1.2')
                    elif not re.match(r'\s*#\s*include', code) and s3.GEOM.search(code) and s3.LIMIT.search(code) and s3.CMP.search(code):
                        rules.append('S-F2')
    return consumers, sorted(set(rules))


def check():
    sel = json.loads((C / 'scoped_sampling_20261028' / 'scoped_selection.json').read_text())
    ref = {r['commit']: r for r in json.loads((C / 'm3_20261028' / 'phase_b_screen.json').read_text())['rows']}
    same = all((bool(m3_scope(h)[0]) and bool(m3_scope(h)[1])) == ref[h]['m3_applicable'] and m3_scope(h)[1] == ref[h]['m3_rules'] for h in sel['phase_b'])
    print(json.dumps({'matches_phase_b_screen': same, 'in_scope': sum(ref[h]['m3_applicable'] for h in sel['phase_b'])}))
    return same


def select():
    target = HERE / 'topup_selection.json'
    if target.exists():
        raise SystemExit('preserve')
    if not check():
        raise SystemExit('selector does not reproduce phase_b_screen.json; stop (addendum 3b B)')
    cand = {l.strip() for l in (s3.INNER / 'candidate_hashes.txt').read_text().splitlines() if l.strip()}
    excluded = set((s3.S1 / 'frozen_sample.txt').read_text().split()) | set((s3.S1 / 'contacted_candidates.txt').read_text().split()) \
        | set((s3.S1 / 'family_linked_candidates.txt').read_text().split())
    s3.HERE = HERE  # recent-contact scan skips this round's own directory
    recent, scan_info = s3.recent_contacts(cand)
    old = json.loads((C / 'scoped_sampling_20261028' / 'scoped_selection.json').read_text())
    used = {s['commit'] for s in old['samples']} | {c['control'] for c in old['controls'] if c['control']}
    reserve = sorted(cand - excluded - recent - used)
    order = list(reserve)
    random.Random(SEED).shuffle(order)
    new, scanned, counts = [], 0, {'applicable': 0, 'S-F1.1': 0, 'S-F1.2': 0, 'S-F2': 0}
    for h in order[:SCAN_CAP]:
        scanned += 1
        consumers, rules = m3_scope(h)
        if consumers:
            counts['applicable'] += 1
        for r in rules:
            counts[r] += 1
        if consumers and rules:
            new.append({'commit': h, 'rules': rules, 'consumer_files': consumers[:3], 'origin': 'addendum_3b'})
            if len(new) == WANT_NEW:
                break
    screen = {r['commit']: r for r in json.loads((C / 'm3_20261028' / 'phase_b_screen.json').read_text())['rows']}
    old_controls = {c['for']: c for c in old['controls']}
    kept = [{'commit': h, 'rules': screen[h]['m3_rules'], 'origin': 'addendum_3_phase_b'} for h in old['phase_b'] if screen[h]['m3_applicable']]
    taken = {s['commit'] for s in new} | {s['commit'] for s in kept} | excluded | recent | used
    controls = [dict(old_controls[s['commit']], origin='addendum_3') for s in kept]
    for s in new:
        f = s['consumer_files'][0]
        parent = s3.git('rev-parse', s['commit'] + '^').stdout.decode().strip()
        log = s3.git('log', '--first-parent', '-n', str(s3.CONTROL_LOOKBACK), '--format=%H%x00%s%x00%(trailers:key=Fixes,valueonly)%x1e',
                     parent, '--', f).stdout.decode('utf-8', 'replace')
        chosen = None
        for rec in log.split('\x1e'):
            parts = rec.strip('\n').split('\x00')
            if len(parts) < 3 or not re.fullmatch(r'[0-9a-f]{40}', parts[0]):
                continue
            if parts[0] in taken or parts[2].strip() or 'fix' in parts[1].lower():
                continue
            chosen = parts[0]
            break
        controls.append({'for': s['commit'], 'file': f, 'control': chosen, 'status': 'ok' if chosen else 'normal_insufficient', 'origin': 'addendum_3b'})
    out = {'pool': len(cand), 'excluded_listed': len(excluded & cand), 'excluded_recent_contact': len(recent - excluded), 'excluded_addendum3_used': len(used & cand),
           'reserve': len(reserve), 'scan_info': scan_info, 'scanned': scanned, 'counts': counts, 'set_c': kept + new, 'controls': controls,
           'addendum_sha256': hashlib.sha256((HERE / 'evaluation_protocol_addendum_3b.md').read_bytes()).hexdigest()}
    target.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: out[k] for k in ('pool', 'excluded_listed', 'excluded_recent_contact', 'excluded_addendum3_used', 'reserve', 'scan_info', 'scanned', 'counts')}))
    print('set_c', len(out['set_c']), 'new', len(new), 'kept_phase_b', len(kept), 'f1', sum(any(r.startswith('S-F1') for r in s['rules']) for s in out['set_c']),
          'f2', sum('S-F2' in s['rules'] for s in out['set_c']), 'controls_ok', sum(c['status'] == 'ok' for c in controls))


if __name__ == '__main__':
    {'check': check, 'select': select}[sys.argv[1]]()
