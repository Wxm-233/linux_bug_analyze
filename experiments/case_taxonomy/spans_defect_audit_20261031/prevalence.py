"""Audit step 1 (criteria.md): named functions found by the original and the corrected recognisers in every .c file at
the range end, grouped by top-level directory. WSL; counts only. Output: prevalence.json.
"""
from collections import defaultdict
from pathlib import Path
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2]))
import wide_spans as W  # noqa: E402
from linux_bug_analyze.candidate_bridge import function_spans  # noqa: E402
from linux_bug_analyze.check_families import _without_directives  # noqa: E402
from linux_bug_analyze.sibling_pairs import named_spans  # noqa: E402

REPO = '/root/repos/linux'
END = 'df2908090cda'
GROUPS = ('arch', 'mm', 'kernel', 'drivers', 'fs', 'net')


def blobs(paths):
    raw = subprocess.run(['git', '-C', REPO, 'cat-file', '--batch'], input=''.join('%s:%s\n' % (END, p) for p in paths).encode(),
                         capture_output=True).stdout
    out, pos = {}, 0
    for p in paths:
        nl = raw.index(b'\n', pos)
        head = raw[pos:nl].split()
        pos = nl + 1
        if len(head) < 3 or head[1] != b'blob':
            continue
        size = int(head[2])
        out[p] = raw[pos:pos + size].decode('utf-8', 'replace')
        pos += size + 1
    return out


def main():
    target = HERE / 'prevalence.json'
    if target.exists():
        raise SystemExit('preserve')
    files = [f for f in subprocess.run(['git', '-C', REPO, 'ls-tree', '-r', '--name-only', END], capture_output=True, text=True).stdout.splitlines()
             if f.endswith('.c')]
    tot = defaultdict(lambda: defaultdict(int))
    examples = []
    for k in range(0, len(files), 2000):
        for path, text in blobs(files[k:k + 2000]).items():
            g = path.split('/')[0] if path.split('/')[0] in GROUPS else 'other'
            plain = _without_directives(text)
            a = {s for s, _, h in function_spans(plain) if h}
            a2 = {s for s, _, h in W.function_spans(plain) if h}
            b = {s for s, _, h in named_spans(text)}
            b2 = {s for s, _, h in W.named_spans(text)}
            for key, val in (('files', 1), ('bridge_orig', len(a)), ('bridge_wide', len(a2)), ('bridge_lost', len(a2 - a)),
                             ('strict_orig', len(b)), ('strict_wide', len(b2)), ('strict_lost', len(b2 - b)),
                             ('files_with_strict_loss', int(bool(b2 - b)))):
                tot[g][key] += val
                tot['all'][key] += val
            if b2 - b and len(examples) < 20 and path.startswith('arch/riscv'):
                names = {s: h for s, _, h in W.named_spans(text)}
                examples.append([path, sorted(names[s] for s in b2 - b)])
        print('progress', min(k + 2000, len(files)), len(files), flush=True)
    out = {g: dict(v) for g, v in tot.items()}
    for v in out.values():
        v['bridge_lost_share'] = round(v['bridge_lost'] / max(1, v['bridge_wide']), 4)
        v['strict_lost_share'] = round(v['strict_lost'] / max(1, v['strict_wide']), 4)
    target.write_text(json.dumps({'end': END, 'groups': out, 'riscv_examples': examples}, indent=1) + '\n')
    print(json.dumps(out['all']))


if __name__ == '__main__':
    main()
