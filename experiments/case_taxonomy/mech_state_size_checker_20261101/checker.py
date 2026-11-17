"""State-size checker (criteria.md). For each architecture's hugetlb files at a revision: find calls of the
architecture's size/contiguity decoders (consumption sites), decide whether a present check guards them locally,
otherwise classify every common-code call site of the enclosing hook as NP / P / U from its path conditions or the
constructor of the value passed in, and give a verdict per site. Runs E1 (end version), E2 (fix parents), E3
(release tags). WSL; no model calls; sources via git show. Output: checker.json; prints summaries.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
import fnmatch
import json
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from linux_bug_analyze.candidate_bridge import header_window  # noqa: E402
from linux_bug_analyze.path_conditions import analyze, params  # noqa: E402
from linux_bug_analyze.sibling_pairs import named_spans  # noqa: E402

REPO = '/root/repos/linux'
END = 'df2908090cda'
TAGS = ['v4.14', 'v4.19', 'v5.10', 'v5.15', 'v6.1', 'v6.6', 'v6.12', 'v6.18', 'v7.0', 'v7.2', END]
FIXES = {'6f1bace9a9fb': 'arm64', '1de195dd0e05': 'riscv', '49c87f767774': 'arm64', '83d78ac677b9': 'riscv'}
HELD_OUT = {'20156ce2365d': 'arm64'}
ARCH_GLOBS = ['arch/*/mm/hugetlbpage*.c', 'arch/*/mm/hugetlb*.c', 'arch/*/include/asm/hugetlb*.h',
              'arch/*/include/asm/*/hugetlb*.h', 'arch/*/include/asm/*/*/hugetlb*.h', 'arch/powerpc/mm/nohash/8xx.c']
DECODERS = {'arm64': {'pte_cont'}, 'riscv': {'pte_napot', 'napot_cont_order'},
            'sparc': {'tte_to_shift', 'huge_tte_to_shift', 'huge_tte_to_size'}}
COMMON = ['mm', 'include/linux', 'include/asm-generic', 'fs']
PRESENT = re.compile(r'(!\s*)?\b(pte_present|pte_valid)\s*\(')
NP_PRED = re.compile(r'(!\s*)?\b(is_swap_pte|pte_is_marker|is_pte_marker|pte_marker_\w+|is_hugetlb_entry_migration'
                     r'|is_hugetlb_entry_hwpoisoned|softleaf_\w+|is_migration_entry|is_hwpoison_entry'
                     r'|pte_is_uffd_wp_marker|pte_swp_\w+|huge_pte_none_mostly)\s*\(')
NP_CTOR = re.compile(r'\b(swp_entry_to_pte|make_pte_marker|make_\w*_entry\w*)\s*\(')
P_CTOR = re.compile(r'\b(make_huge_pte|arch_make_huge_pte|pte_mk\w+|huge_pte_mk\w+|huge_pte_modify|huge_pte_wrprotect'
                    r'|mk_pte|pfn_pte|mk_huge_pte)\s*\(')
ENTRY_READ = re.compile(r'\b(ptep_get|__ptep_get|huge_ptep_get|READ_ONCE)\s*\(|\*\s*\w*ptep\b')
GUARD_PREFIX = re.compile(r'!\s*(pte_present|pte_valid)\s*\(.*\)\s*\|\|\s*!?$|(?<![!\w])(pte_present|pte_valid)\s*\(.*\)\s*&&\s*!?$')


def git(*args):
    return subprocess.run(['git', '-C', REPO, *args], capture_output=True).stdout.decode('utf-8', 'replace')


@lru_cache(maxsize=None)
def show(rev, path):
    return git('show', f'{rev}:{path}')


@lru_cache(maxsize=None)
def functions(rev, path):
    """[(start, end, name, text)] for path at rev. named_spans starts at the '{' line, so the header from
    header_window is put in front of that line; line k of text is file line start+k-1."""
    text = show(rev, path)
    lines = text.splitlines()
    out = []
    for s, e, n in named_spans(text):
        first = lines[s - 1]
        body = [header_window(lines, s) + ' ' + first[first.index('{'):] if '{' in first else first]
        out.append((s, e, n, '\n'.join(body + lines[s:e])))
    return out


def arch_files(rev):
    out = []
    for f in git('ls-tree', '-r', '--name-only', rev, 'arch').splitlines():
        if any(fnmatch.fnmatch(f, g) and f.count('/') == g.count('/') for g in ARCH_GLOBS):
            out.append(f)
    return out


def _uses(rx, text):
    """(positive, negated) occurrences of the predicates in rx within a condition text."""
    pos = neg = False
    for m in rx.finditer(text):
        if m.group(1):
            neg = True
        else:
            pos = True
    return pos, neg


def classify_conds(conds):
    """'NP' if the path admits a non-present entry, 'P' if it guarantees a present one, else None."""
    np_ = p = False
    for text, pol in conds:
        pos_p, neg_p = _uses(PRESENT, text)
        pos_np, _ = _uses(NP_PRED, text)
        if pol:
            if neg_p or pos_np:
                np_ = True
            elif pos_p and '||' not in text:
                p = True
        else:
            if neg_p or pos_np:
                p = True
            elif pos_p and '&&' not in text:
                np_ = True
    return 'NP' if np_ else ('P' if p else None)


def classify_value(expr):
    if NP_CTOR.search(expr):
        return 'NP'
    if P_CTOR.search(expr):
        return 'P'
    return None


def last_assignment(fn_text, var, before_line):
    """Expression last assigned to var before a (function-relative) line, or None."""
    best = None
    for n, line in enumerate(fn_text.splitlines(), 1):
        if n >= before_line:
            break
        m = re.search(r'\b%s\s*=(?!=)\s*(.+)' % re.escape(var), line)
        if m:
            best = m.group(1)
    return best


def value_source(fn_text, arg, line):
    """('param', index) when the decoded value comes from a parameter, else ('entry', None)."""
    names = params(fn_text)
    var = arg.strip()
    if var in names:
        return 'param', names.index(var)
    if re.fullmatch(r'[A-Za-z_]\w*', var):
        expr = last_assignment(fn_text, var, line)
        if expr and not ENTRY_READ.search(expr):
            hit = [p for p in names if re.search(r'\b%s\b' % re.escape(p), expr)]
            pte_like = [p for p in hit if p != 'ptep' and not p.endswith('ptep')]
            if pte_like:
                return 'param', names.index(pte_like[0])
    return 'entry', None


@lru_cache(maxsize=None)
def common_callers(rev, name):
    """[(path, caller function, Call, caller text)] for calls of name in common code."""
    out = []
    hits = git('grep', '-l', '-w', name, rev, '--', *COMMON).splitlines()
    for h in hits:
        path = h.split(':', 1)[1]
        if not path.endswith(('.c', '.h')):
            continue
        for s, e, fname, text in functions(rev, path):
            if fname == name or name not in text:
                continue
            for c in analyze(text):
                if c.name == name:
                    out.append((path, fname, c, text, s))
    return out


def classify_site(c, text, src):
    if src[0] == 'param' and src[1] < len(c.args):
        expr = c.args[src[1]]
        v = classify_value(expr)
        if v is None and re.fullmatch(r'[A-Za-z_]\w*', expr.strip()):
            assigned = last_assignment(text, expr.strip(), c.line)
            v = classify_value(assigned) if assigned else None
        if v:
            return v
    return classify_conds(c.conds) or 'U'


def caller_sites(rev, arch, fname, src, files):
    """Classified common call sites of fname; one level of arch-internal propagation when there are none."""
    rows = [{'file': p, 'caller': f, 'line': s + c.line - 1, 'class': classify_site(c, t, src)}
            for p, f, c, t, s in common_callers(rev, fname)]
    if rows:
        return rows
    for path in files:
        for s, e, g, text in functions(rev, path):
            if g == fname:
                continue
            for c in analyze(text):
                if c.name != fname:
                    continue
                gsrc = ('entry', None)
                if src[0] == 'param' and src[1] < len(c.args):
                    expr = c.args[src[1]].strip()
                    gp = params(text)
                    if expr in gp:
                        gsrc = ('param', gp.index(expr))
                for p, f, cc, t, ss in common_callers(rev, g):
                    rows.append({'file': p, 'caller': f, 'line': ss + cc.line - 1, 'via': g,
                                 'class': classify_site(cc, t, gsrc)})
    return rows


def check(rev, only_arch=None):
    files = arch_files(rev)
    out = []
    for path in files:
        arch = path.split('/')[1]
        if arch not in DECODERS or (only_arch and arch != only_arch):
            continue
        same_arch = [f for f in files if f.split('/')[1] == arch]
        for s, e, fname, text in functions(rev, path):
            for c in analyze(text):
                if c.name not in DECODERS[arch] or not c.args:
                    continue
                row = {'rev': rev, 'arch': arch, 'file': path, 'function': fname, 'line': s + c.line - 1,
                       'decoder': c.name, 'arg': c.args[0]}
                local = classify_conds(c.conds)
                if local == 'P' or (c.cond_prefix and GUARD_PREFIX.search(c.cond_prefix)):
                    row['verdict'] = 'local'
                elif local == 'NP':
                    row['verdict'] = 'strong'
                    row['why'] = 'decoder inside a non-present branch'
                else:
                    src = value_source(text, c.args[0], c.line)
                    row['source'] = list(src)
                    callers = caller_sites(rev, arch, fname, src, same_arch)
                    row['callers'] = callers
                    kinds = {r['class'] for r in callers}
                    row['verdict'] = ('unknown' if not callers else 'strong' if 'NP' in kinds else
                                      'weak' if 'U' in kinds else 'callers')
                out.append(row)
    return out


def changed_old_lines(parent, commit, path):
    lines = set()
    for m in re.finditer(r'^@@ -(\d+)(?:,(\d+))? ', git('diff', '-U0', parent, commit, '--', path), re.M):
        start, n = int(m.group(1)), int(m.group(2) or 1)
        lines |= set(range(start, start + max(n, 1)))
    return lines


def retro(commit, arch):
    parent = commit + '^'
    files = [f for f in git('diff', '--name-only', parent, commit).split() if f.startswith(f'arch/{arch}/')]
    rows = check(git('rev-parse', parent).strip()[:12], arch)
    changed = {f: changed_old_lines(parent, commit, f) for f in files}
    spans = {f: functions(parent, f) for f in files}
    fixed_fns = {(f, n) for f in files for s, e, n, _ in spans[f] if changed[f] & set(range(s, e + 1))}
    hits = [r for r in rows if r['verdict'] in ('strong', 'weak') and (r['file'], r['function']) in fixed_fns
            and r['line'] in changed.get(r['file'], set())]
    in_fn = [r for r in rows if r['verdict'] in ('strong', 'weak') and (r['file'], r['function']) in fixed_fns]
    after = check(git('rev-parse', commit).strip()[:12], arch)
    still = [r for r in after if r['verdict'] in ('strong', 'weak') and (r['file'], r['function']) in fixed_fns]
    return {'commit': commit, 'arch': arch, 'fixed_functions': sorted(n for _, n in fixed_fns),
            'hit_changed_site': bool(hits), 'flagged_in_fixed_function': bool(in_fn),
            'hits': hits, 'flags_at_parent': sum(r['verdict'] in ('strong', 'weak') for r in rows),
            'still_flagged_after': [(r['function'], r['line'], r['verdict']) for r in still]}


def summarize(rows):
    by = {}
    for r in rows:
        if r['verdict'] in ('strong', 'weak'):
            by.setdefault(r['arch'], {'strong': 0, 'weak': 0})[r['verdict']] += 1
    return by


def main():
    target = HERE / 'checker.json'
    if target.exists():
        raise SystemExit('preserve')
    end_rows = check(END)
    retro_rows = [retro(c, a) for c, a in FIXES.items()]
    held = [retro(c, a) for c, a in HELD_OUT.items()]
    with ThreadPoolExecutor(max_workers=8) as pool:
        tag_rows = dict(zip(TAGS, pool.map(check, TAGS)))
    out = {'end': end_rows, 'retro': retro_rows, 'held_out': held,
           'tags': {t: summarize(r) for t, r in tag_rows.items()}, 'tag_rows': tag_rows}
    target.write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8')
    for r in end_rows:
        print('END', r['arch'], r['function'], r['line'], r['decoder'], r['verdict'],
              sorted({c['class'] for c in r.get('callers', [])}))
    for r in retro_rows + held:
        print('RETRO', r['commit'], r['arch'], r['fixed_functions'], 'hit' if r['hit_changed_site'] else 'miss',
              'in_fn' if r['flagged_in_fixed_function'] else '-', 'after', r['still_flagged_after'])
    for t in TAGS:
        print('TAG', t, json.dumps(out['tags'][t]))


if __name__ == '__main__':
    main()
