"""Part 2 (criteria.md): "follow other architectures' fixes". Reference fixes are non-merge commits in v6.1..END that
touch arch/ outside arch/riscv and carry a Fixes: tag whose target touches files outside arch/ but none of the
reference fix's own arch directories, and that change a function also defined in arch/riscv. A candidate is such a
(reference, function) pair where no RISC-V commit names the same Fixes target. Also checks, for the five M8 cases,
whether a qualifying reference fix existed before the RISC-V fix. WSL; no model calls. Output: follow_fixes.json.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import random
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'mech_state_size_checker_20261101'))
import checker as CK  # noqa: E402  (git, functions, END)

END, START, RECENT_TAG = CK.END, 'v6.1', 'v6.12'
CASES = {'0c710050c47d': 'mm_fault_error', '8c5fa3764fac': 'kvm_arch_prepare_memory_region',
         '6b60a128c2f4': 'patch_map', '5fc6e7d45373': 'prepare_elf_headers', '81bbcff0c053': 'machine_kexec_prepare'}
FIXES = re.compile(r'^\s*Fixes:\s*([0-9a-f]{8,40})', re.M | re.I)


def riscv_names():
    names = set()
    files = [f for f in CK.git('ls-tree', '-r', '--name-only', END, 'arch/riscv').splitlines() if f.endswith(('.c', '.h'))]
    with ThreadPoolExecutor(max_workers=8) as pool:
        for fns in pool.map(lambda f: CK.functions(END, f), files):
            names |= {n for _, _, n, _ in fns}
    return names


def changed_functions(commit, files):
    out = set()
    parent = commit + '^'
    diff = CK.git('diff', '-U0', parent, commit, '--', *files)
    path = None
    for line in diff.splitlines():
        if line.startswith('+++ '):
            path = line[6:] if line.startswith('+++ b/') else None
        m = re.match(r'@@ -(\d+)(?:,(\d+))? ', line)
        if m and path and path.endswith('.c'):
            start, n = int(m.group(1)), int(m.group(2) or 1)
            for s, e, name, _ in CK.functions(parent, path):
                if s <= start + max(n, 1) - 1 and start <= e:
                    out.add(name)
    return out


def reference(sha, rv):
    try:
        files = CK.git('show', '--no-renames', '--name-only', '--format=', sha).split()
        arches = {f.split('/')[1] for f in files if f.startswith('arch/')}
        if not arches or 'riscv' in arches:
            return None
        msg = CK.git('log', '-1', '--format=%B', sha)
        rows = []
        for t in FIXES.findall(msg):
            full = CK.git('rev-parse', '--verify', '--quiet', t + '^{commit}').strip()
            if not full:
                continue
            tfiles = CK.git('show', '--no-renames', '--name-only', '--format=', full).split()
            touches_common = any(not f.startswith('arch/') for f in tfiles)
            touches_own = any(f.startswith('arch/%s/' % a) for f in tfiles for a in arches)
            if not touches_common or touches_own:
                continue
            fns = changed_functions(sha, [f for f in files if f.startswith('arch/')]) & rv
            if fns:
                rows.append({'ref': sha[:12], 'date': CK.git('log', '-1', '--format=%as', sha).strip(),
                             'subject': msg.splitlines()[0], 'arches': sorted(arches), 'trigger': full[:12],
                             'functions': sorted(fns)})
        return rows
    except Exception as exc:  # recorded, not retried
        return [{'ref': sha[:12], 'error': repr(exc)[:200]}]


def riscv_followed(trigger):
    return bool(CK.git('log', '--no-merges', '--format=%h', '-i', '--grep=Fixes: %s' % trigger[:8],
                       f'{START}..{END}', '--', 'arch/riscv').strip())


def main():
    target = HERE / 'follow_fixes.json'
    if target.exists():
        raise SystemExit('preserve')
    rv = riscv_names()
    shas = CK.git('log', '--no-merges', '--format=%H', '--grep=Fixes:', f'{START}..{END}', '--', 'arch/',
                  ':(exclude)arch/riscv').split()
    with ThreadPoolExecutor(max_workers=8) as pool:
        refs = [r for rows in pool.map(lambda s: reference(s, rv), shas) if rows for r in rows]
    errors = [r for r in refs if 'error' in r]
    refs = [r for r in refs if 'error' not in r]
    for r in refs:
        r['riscv_followed'] = riscv_followed(r['trigger'])
    recent_date = CK.git('log', '-1', '--format=%as', RECENT_TAG).strip()
    cands = [r for r in refs if not r['riscv_followed'] and r['date'] >= recent_date]
    review = cands if len(cands) <= 30 else random.Random(20261102).sample(cands, 30)
    retro = {}
    for c, fn in CASES.items():
        date = CK.git('log', '-1', '--format=%as', c).strip()
        trig = [m[:12] for m in FIXES.findall(CK.git('log', '-1', '--format=%B', c))]
        hits = [r for r in refs if fn in r['functions'] and r['date'] < date]
        retro[c] = {'function': fn, 'riscv_fix_date': date, 'riscv_fixes_targets': trig,
                    'prior_references_same_function': hits,
                    'prior_reference_same_trigger': [r for r in hits if any(r['trigger'].startswith(t[:8]) for t in trig)]}
    summary = {'reference_commits_scanned': len(shas), 'references': len(refs), 'errors': len(errors),
               'riscv_functions': len(rv), 'candidates_recent': len(cands), 'review': len(review),
               'retro_hits_same_function': sum(bool(v['prior_references_same_function']) for v in retro.values()),
               'retro_hits_same_trigger': sum(bool(v['prior_reference_same_trigger']) for v in retro.values())}
    target.write_text(json.dumps({'summary': summary, 'retro': retro, 'references': refs, 'candidates': cands,
                                  'review': review, 'errors': errors}, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(summary))
    for r in review:
        print(r['date'], r['ref'], ','.join(r['arches']), r['trigger'], r['functions'], '|', r['subject'][:80])


if __name__ == '__main__':
    main()
