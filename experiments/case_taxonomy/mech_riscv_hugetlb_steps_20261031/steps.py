"""Direction 4, round 2 (criteria.md): compare implementation steps of same-named hugetlb functions in arm64 and riscv.
Steps S1-S6 are fixed regexes over a function body plus the bodies of same-file functions it calls (one level).
Flag = a step arm64 has and riscv lacks. Runs at the parents of 4 design cases, over arm64 fixes after NAPOT support,
and at the range end. WSL; no model calls. Output: steps.json; prints a summary.
"""
from pathlib import Path
import json
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from linux_bug_analyze.sibling_pairs import first_branch_only, header_name  # noqa: E402

REPO = '/root/repos/linux'
END = 'df2908090cda'
NAPOT = '82a1a1f3bfb6'
FILES = {'arm64': 'arch/arm64/mm/hugetlbpage.c', 'riscv': 'arch/riscv/mm/hugetlbpage.c'}
DESIGN = {'83d78ac677b9': 'S4', '1458eb2c9d88': 'S1|S2', '1de195dd0e05': 'S6', '835e5ac3f98e': 'S1|S2'}
DESIGN_FUNC = {'83d78ac677b9': None, '1458eb2c9d88': 'set_huge_pte_at', '1de195dd0e05': 'set_huge_pte_at',
               '835e5ac3f98e': 'huge_ptep_set_wrprotect'}
HUNK = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')


def git(*args):
    return subprocess.run(['git', '-C', REPO, *args], capture_output=True).stdout.decode('utf-8', 'replace')


def header_start(lines, s):
    h = s
    while h > 1 and s - h < 6:
        prev = lines[h - 2].strip()
        if not prev or prev.endswith((';', '}', '*/')) or prev.startswith('#'):
            break
        h -= 1
    return h


def spans(text):
    """Top-level function spans (start, end, name) on the first conditional branch. Unlike sibling_pairs.named_spans,
    which looks back only 4 lines for the header, the header is taken back to the previous ';', '}', blank or
    preprocessor line (at most 15 lines), so long parameter lists keep their name."""
    lines = first_branch_only(text).splitlines()
    out, depth, start, name = [], 0, None, None
    for n, line in enumerate(lines, 1):
        if depth == 0 and '{' in line:
            h = n
            while h > 1 and n - h < 15:
                prev = lines[h - 2].strip()
                if not prev or prev.endswith((';', '}')) or prev.startswith('#'):
                    break
                h -= 1
            start, name = n, header_name(' '.join(lines[h - 1:n]).split('{')[0])
        depth += line.count('{') - line.count('}')
        if depth == 0 and start is not None:
            if name:
                out.append((start, n, name))
            start = None
    return out


def functions(text):
    """{name: {'static': bool, 'body': str, 'span': (start, end)}} of top-level functions (first conditional branch)."""
    lines, out = text.splitlines(), {}
    for s, e, name in spans(text):
        h = header_start(lines, s)
        header = '\n'.join(lines[h - 1:s])
        out[name] = {'static': bool(re.search(r'\bstatic\b', header)), 'body': '\n'.join(lines[s - 1:e]), 'span': (h, e)}
    return out


def expanded(fns, name):
    body = fns[name]['body']
    called = {m.group(1) for m in re.finditer(r'\b([A-Za-z_]\w*)\s*\(', body)} & set(fns) - {name}
    return body + '\n' + '\n'.join(fns[c]['body'] for c in sorted(called)), sorted(called)


def features(text, called):
    f = set()
    if re.search(r'\b(__)?ptep_get_and_clear\s*\(|\b(__)?pte_clear\s*\(|\bptep_clear\s*\(', text):
        f.add('S1')
    if re.search(r'\b(__)?flush_tlb_range\s*\(|\bflush_tlb_page\s*\(|\bflush_tlb_mm\s*\(', text):
        f.add('S2')
    if (re.search(r'\b(for|while)\s*\(', text) and re.search(r'\b(ncontig|pte_num|ncont)\b', text)) or any('contig' in c for c in called):
        f.add('S3')
    if re.search(r'\bpte_present\s*\(', text):
        f.add('S4')
    if re.search(r'\bpte_(dirty|young)\s*\(', text) and re.search(r'\bpte_mk(dirty|young)\s*\(', text):
        f.add('S5')
    if re.search(r'\bnum_contig_ptes\w*\s*\(|\bfind_num_contig\s*\(|\bsz\s*>>|\(\s*sz\s*,|,\s*sz\s*[,)]', text):
        f.add('S6')
    return f


def profile(rev, arch):
    text = git('show', '%s:%s' % (rev, FILES[arch]))
    fns = functions(text)
    out = {}
    for name, info in fns.items():
        if info['static']:
            continue
        body, called = expanded(fns, name)
        out[name] = {'features': sorted(features(body, called)), 'called': called}
    return out, fns


def compare(rev):
    a, _ = profile(rev, 'arm64')
    r, _ = profile(rev, 'riscv')
    flags = []
    for name in sorted(set(a) & set(r)):
        for s in sorted(set(a[name]['features']) - set(r[name]['features'])):
            flags.append({'func': name, 'missing': s, 'arm64': a[name]['features'], 'riscv': r[name]['features']})
    return flags


def changed_functions(commit, path):
    """Names of functions (at commit) whose span contains a new-side hunk line of commit in path."""
    text = git('show', '%s:%s' % (commit, path))
    fns = functions(text)
    names = set()
    for line in git('show', '-U0', '--format=', commit, '--', path).splitlines():
        m = HUNK.match(line)
        if m:
            s, n = int(m.group(3)), int(m.group(4) or 1)
            for name, info in fns.items():
                a, b = info['span']
                if a <= s + max(n, 1) - 1 and s <= b:
                    names.add(name)
    return sorted(names)


def public_targets(rev, arch, names):
    """Changed static helpers are represented by the non-static functions that call them (the comparison unit)."""
    prof, fns = profile(rev, arch)
    out = set()
    for n in names:
        if n in prof:
            out.add(n)
        elif n in fns:
            out |= {p for p, info in prof.items() if n in info['called']}
    return sorted(out)


def main():
    target = HERE / 'steps.json'
    if target.exists():
        raise SystemExit('preserve')
    retro = []
    for c, expect in DESIGN.items():
        parent = c + '^'
        flags = compare(parent)
        funcs = [DESIGN_FUNC[c]] if DESIGN_FUNC[c] else public_targets(parent, 'riscv', changed_functions(c, FILES['riscv']))
        hit = [f for f in flags if f['func'] in funcs and f['missing'] in expect.split('|')]
        retro.append({'commit': c, 'functions': funcs, 'expected': expect, 'hit': bool(hit), 'hits': hit,
                      'flags_at_parent': len(flags), 'all_flags': flags})
        print('retro', c, funcs, expect, bool(hit), len(flags), flush=True)
    arm_fixes = git('log', '--no-merges', '--format=%H %s', '--grep=Fixes:', NAPOT + '..' + END, '--', FILES['arm64']).splitlines()
    independent = []
    for line in arm_fixes:
        c, subject = line.split(' ', 1)
        names = public_targets(c + '^', 'arm64', changed_functions(c, FILES['arm64']))
        before, _ = profile(c + '^', 'arm64')
        after, _ = profile(c, 'arm64')
        rv, _ = profile(c + '^', 'riscv')
        rv_end, _ = profile(END, 'riscv')
        for n in names:
            if n not in rv:
                independent.append({'commit': c[:12], 'subject': subject, 'func': n, 'riscv_has_func': False})
                continue
            added = sorted(set(after.get(n, {}).get('features', [])) - set(before.get(n, {}).get('features', [])))
            lacking = sorted(set(added) - set(rv[n]['features']))
            later = git('log', '--no-merges', '--format=%h %s', c + '..' + END, '-L', ':%s:%s' % (n, FILES['riscv']), '-s')
            independent.append({'commit': c[:12], 'subject': subject, 'func': n, 'riscv_has_func': True, 'arm64_added_steps': added,
                                'riscv_lacked_at_fix': lacking, 'riscv_has_at_end': sorted(set(added) & set(rv_end.get(n, {}).get('features', []))),
                                'riscv_later_commits': [l for l in later.splitlines() if re.match(r'^[0-9a-f]{7,} ', l)][:8]})
        print('arm64 fix', c[:12], names, flush=True)
    end_flags = compare(END)
    summary = {'retro_hit': sum(r['hit'] for r in retro), 'retro_total': len(retro), 'retro_flags_at_parent': [r['flags_at_parent'] for r in retro],
               'arm64_fixes': len(arm_fixes), 'independent_support': [x for x in independent if x.get('riscv_lacked_at_fix')],
               'end_flags': len(end_flags)}
    target.write_text(json.dumps({'summary': summary, 'retro': retro, 'independent': independent, 'end_flags': end_flags}, indent=1) + '\n')
    print(json.dumps(summary)[:3000])


if __name__ == '__main__':
    main()
