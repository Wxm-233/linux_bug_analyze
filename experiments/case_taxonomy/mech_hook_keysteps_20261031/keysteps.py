"""Method 1, second version (criteria.md): compare hook implementations by key-step categories K1-K5 (callee names
and asm mnemonics in string literals), body plus two levels of same-file callees. Reuses the first version's hook
definition and helpers. Part 1: retrospective recall over RISC-V Fixes commits (v5.10..end) that make a hook
implementation gain a category. Part 2: v6.6 majority-category flags and their fate, against minority categories.
Part 3: flags at the range end. 8 workers. WSL; no model calls. Output: keysteps.json; prints summaries.
"""
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import math
import random
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'mech_hook_consensus_20261031'))
import consensus as C1  # noqa: E402  (git, show, arch_of, referenced_outside_arch, changed_target_functions)

named_spans = C1.named_spans
END, SNAP, TGT = C1.END, C1.SNAP, C1.TGT
CALLEE = re.compile(r'\b([A-Za-z_]\w*)\s*\(')
STRING = re.compile(r'"(?:\\.|[^"\\])*"')
NAMES = {
    'K1': r'smp_(r|w)?mb\w*|(r|w)?mb|dma_(r|w)?mb|\w*_acquire|\w*_release|(try_)?cmpxchg\w*|xchg\w*'
          r'|atomic\w*_(xchg|cmpxchg|fetch_\w+|add_return\w*|sub_return\w*|inc_return\w*|dec_return\w*)',
    'K2': r'(local_)?flush_tlb\w*|__flush_tlb\w*|flush_(i|d)?cache\w*|__flush_(i|d)?cache\w*|update_mmu_cache\w*'
          r'|tlb_flush\w*|sync_icache\w*|flush_icache\w*',
    'K3': r'\w+_present|\w+_none|\w+_bad|pfn_valid|virt_addr_valid|access_ok|\w+_leaf',
    'K4': r'(raw_)?spin_(try)?lock\w*|(raw_)?spin_unlock\w*|mutex_(try)?lock\w*|mutex_unlock|local_irq_\w+'
          r'|preempt_disable\w*|preempt_enable\w*|rcu_read_(un)?lock\w*|mmap_\w*lock\w*|local_bh_\w+|lockdep_assert\w*'
          r'|guard|scoped_guard|ftrace_test_recursion_\w+|(down|up)_(read|write)\w*',
    'K5': r'k(v)?free\w*|vfree|(__)?free_pages?\w*|put_page|folio_put\w*|\w+_put|put_\w+|memblock_free\w*'
          r'|(early_)?memunmap|iounmap',
}
K5_EXCLUDE = re.compile(r'(__)?(get|put)_user\w*|(get|put)_unaligned\w*')  # amendment before implementation
ASM = {
    'K1': r'\b(fence|dmb|dsb|mfence|sfence|lfence|lwsync|hwsync|eieio|membar|amoswap\w*|lr\.\w+|sc\.\w+)\b',
    'K2': r'sfence\.vma|\btlbi\b|\binvlpg\b|\btlbie\b|\bic\s+ivau\b|\bdc\s+c\w+',
}
NAME_RE = {k: re.compile(r'(%s)' % v) for k, v in NAMES.items()}
ASM_RE = {k: re.compile(v) for k, v in ASM.items()}


def categories(body):
    cats = set()
    for name in {c for c in CALLEE.findall(body)}:
        for k, rx in NAME_RE.items():
            if rx.fullmatch(name) and not (k == 'K5' and K5_EXCLUDE.fullmatch(name)):
                cats.add(k)
    strings = ' '.join(STRING.findall(body))
    for k, rx in ASM_RE.items():
        if rx.search(strings):
            cats.add(k)
    return cats


def file_cats(text):
    """{function: categories over body plus two levels of same-file callees}."""
    lines, direct, calls = text.splitlines(), defaultdict(set), defaultdict(set)
    for s, e, name in named_spans(text):
        body = '\n'.join(lines[s - 1:e])
        direct[name] |= categories(body)
        calls[name] |= set(CALLEE.findall(body))
    out = {}
    for name in direct:
        cats = set(direct[name])
        for c in calls[name] & set(direct):
            if c == name:
                continue
            cats |= direct[c]
            for d in calls[c] & set(direct):
                if d not in (name, c):
                    cats |= direct[d]
        out[name] = cats
    return out


def impls(rev, name):
    out = defaultdict(set)
    for line in C1.git('grep', '-l', '-w', name, rev, '--', 'arch/*.c', 'arch/*.h').splitlines():
        path = line.split(':', 1)[1]
        fc = file_cats(C1.show(rev, path))
        if name in fc:
            out[C1.arch_of(path)] |= fc[name]
    return out


def split_cats(per_arch):
    others = {a: c for a, c in per_arch.items() if a != TGT}
    count = defaultdict(int)
    for cats in others.values():
        for k in cats:
            count[k] += 1
    need = max(3, math.ceil(0.5 * len(others)))
    return {k for k, n in count.items() if n >= need}, {k for k, n in count.items() if 1 <= n <= 2}


def retro_one(commit):
    try:
        parent, rows = commit + '^', []
        for path, name in sorted(C1.changed_target_functions(commit)):
            before = file_cats(C1.show(parent, path)).get(name)
            after = file_cats(C1.show(commit, path)).get(name)
            if before is None or after is None or not (after - before):
                continue
            per = impls(parent, name)
            if TGT not in per or len([a for a in per if a != TGT]) < 3 or not C1.referenced_outside_arch(parent, {name}):
                continue
            majority, _ = split_cats(per)
            for k in sorted(after - before):
                rows.append({'fix': commit[:12], 'hook': name, 'category': k, 'majority_at_parent': k in majority,
                             'implementing_arches': len(per) - 1})
        return rows
    except Exception as exc:  # recorded, not retried
        return [{'fix': commit[:12], 'error': repr(exc)[:200]}]


def index(rev):
    files = [f for f in C1.git('ls-tree', '-r', '--name-only', rev, 'arch').splitlines() if f.endswith(('.c', '.h'))]

    def per_file(f):
        return C1.arch_of(f), file_cats(C1.show(rev, f))
    out = defaultdict(lambda: defaultdict(set))
    with ThreadPoolExecutor(max_workers=8) as pool:
        for arch, fc in pool.map(per_file, files):
            for name, cats in fc.items():
                out[name][arch] |= cats
    return out


def snapshot_flags(rev, idx):
    names = [n for n, per in idx.items() if TGT in per and len([a for a in per if a != TGT]) >= 3]
    hooks = set(names) & C1.referenced_outside_arch(rev, set(names))
    rows = []
    for h in sorted(hooks):
        maj, mino = split_cats(idx[h])
        others = len([a for a in idx[h] if a != TGT])
        for k in sorted(maj - idx[h][TGT]):
            rows.append({'hook': h, 'category': k, 'kind': 'majority', 'implementing_arches': others})
        for k in sorted(mino - idx[h][TGT]):
            rows.append({'hook': h, 'category': k, 'kind': 'minority', 'implementing_arches': others})
    return len(hooks), rows


def main():
    target = HERE / 'keysteps.json'
    if target.exists():
        raise SystemExit('preserve')
    fixes = C1.git('log', '--no-merges', '--format=%H', '--grep=Fixes:', 'v5.10..' + END, '--', 'arch/%s/' % TGT).split()
    truth = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for k, rows in enumerate(pool.map(retro_one, fixes), 1):
            truth += rows
            if k % 100 == 0:
                print('retro', k, len(fixes), flush=True)
    good = [r for r in truth if 'error' not in r]
    recall = {'entries': len(good), 'fixes': len({r['fix'] for r in good}), 'hit': sum(r['majority_at_parent'] for r in good),
              'errors': sum(1 for r in truth if 'error' in r)}
    print('recall', recall, flush=True)
    idx_snap = index(SNAP)
    n_snap, snap_rows = snapshot_flags(SNAP, idx_snap)
    idx_end = index(END)
    for r in snap_rows:
        per = idx_end.get(r['hook'], {})
        r['state'] = 'gone' if TGT not in per else ('followed' if r['category'] in per[TGT] else 'open')
    rate = lambda kind: (sum(1 for r in snap_rows if r['kind'] == kind and r['state'] == 'followed'),
                         sum(1 for r in snap_rows if r['kind'] == kind and r['state'] != 'gone'))
    n_end, end_rows = snapshot_flags(END, idx_end)
    end_major = [r for r in end_rows if r['kind'] == 'majority']
    review = end_major if len(end_major) <= 40 else random.Random(20261031).sample(end_major, 40)
    summary = {'retro': recall, 'snapshot': SNAP, 'snapshot_hooks': n_snap,
               'snapshot_followed_majority': rate('majority'), 'snapshot_followed_minority': rate('minority'),
               'end_hooks': n_end, 'end_majority_flags': len(end_major), 'review_items': len(review)}
    target.write_text(json.dumps({'summary': summary, 'truth': truth, 'snapshot_rows': snap_rows, 'end_majority': end_major,
                                  'review': review}, indent=1) + '\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
