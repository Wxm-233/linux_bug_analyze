"""New pools LA2 and RV2 (criteria.md section 1): non-merge commits of v6.1..END touching arch/loongarch/ (resp.
arch/riscv/), other than device-tree-only ones, whose message matches the source's pattern. Commits seen in earlier
records are excluded with fix_strategy_test_20261105/collect.py's scan (amendment 1 there), which also covers the
first pool. Item fields and reading material come from that same module. WSL; no model calls.
Output: items.json, excluded.json, dump/batch_NN.txt.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import importlib.util
import json
import re

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('pool1', HERE.parent / 'fix_strategy_test_20261105' / 'collect.py')
P1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P1)
CK = P1.CK
SOURCES = [('RV2', 'arch/riscv/', r'(like|similar to|same as|as) (arm64|x86|loongarch)'),
           ('LA2', 'arch/loongarch/', r'arm64|riscv|risc-v|x86')]
BATCH = 25


def log(path, pattern):
    return CK.git('log', '--no-merges', '--format=%H', '-i', '-E', f'--grep={pattern}', f'v6.1..{CK.END}', '--', path,
                  f':(exclude){path}boot/dts').split()


def seen_ids():
    found = set()
    for f in HERE.parent.rglob('*'):
        if f.is_file() and f.suffix in P1.SUFFIXES and HERE not in f.parents and not P1.raw_pool(f):
            found |= set(re.findall(r'\b[0-9a-f]{12}', f.read_text(encoding='utf-8', errors='replace')))
    return found


def main():
    if (HERE / 'items.json').exists():
        raise SystemExit('preserve')
    seen = seen_ids()
    picked, excluded, taken = [], [], set()
    for source, path, pattern in SOURCES:
        for sha in log(path, pattern):
            if sha in taken:
                continue
            taken.add(sha)
            (excluded if sha[:12] in seen else picked).append((sha, source))
    with ThreadPoolExecutor(max_workers=8) as pool:
        items = list(pool.map(lambda x: P1.item(*x), picked))
    items.sort(key=lambda it: (it['source'] != 'RV2', it['date'], it['commit']))
    for k, it in enumerate(items):
        it['id'] = f"{'V' if it['source'] == 'RV2' else 'A'}{k:03d}"
    with ThreadPoolExecutor(max_workers=8) as pool:
        texts = list(pool.map(P1.material, items))
    (HERE / 'dump').mkdir()
    for n in range(0, len(items), BATCH):
        (HERE / 'dump' / f'batch_{n // BATCH:02d}.txt').write_text(
            ''.join(f"\n##### {it['id']}\n{t}" for it, t in zip(items[n:n + BATCH], texts[n:n + BATCH])),
            encoding='utf-8')
    (HERE / 'items.json').write_text(json.dumps(items, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'excluded.json').write_text(json.dumps([{'commit': s[:12], 'source': src} for s, src in excluded],
                                                   indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'kept': {s: sum(it['source'] == s for it in items) for s in ('RV2', 'LA2')},
                      'excluded': {s: sum(src == s for _, src in excluded) for s in ('RV2', 'LA2')}}))


if __name__ == '__main__':
    main()
