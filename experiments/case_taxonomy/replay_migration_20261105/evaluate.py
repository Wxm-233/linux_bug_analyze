"""Program metrics of criteria.md section 3 for one split, and the blind sheet for the "修法一致" judgement.

    python3 -B evaluate.py dev|test

For every answer: the last ```diff block of final.md is saved as patches/<dir>.patch; on a temporary worktree at
T^ it is checked, on a temporary directory holding only its files as they are at T^, with `git apply --check`, then
`git apply --check --recount` (hunk line counts ignored, criteria_amendment1.md), then `patch -p1 --fuzz=3 --dry-run` on
the patch with its hunk line counts recomputed from the hunk bodies (criteria_amendment2.md); the files it
touches are compared with T's (location) and with the candidate files; the +/- lines, without whitespace and
comments, are compared with T's (overlap). The blind sheet lists both conditions' patches of a pair in random order
(Random(1105)) with labels X/Y and T's diff; the key goes to blind_key_<split>.json.
WSL (git); no model calls. Output: patches/, eval_<split>.json, blind_<split>.md, blind_key_<split>.json.
"""
from pathlib import Path
import json
import random
import re
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
SAMPLES = HERE.parent / 'replay_samples_more_20261105'
CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-05' / 'replay_migration_20261105'
REPO = '/root/repos/linux'


def sh(*a, cwd=REPO, check=False):
    r = subprocess.run(list(a), cwd=cwd, capture_output=True)
    if check and r.returncode:
        raise SystemExit(r.stderr.decode('utf-8', 'replace'))
    return r.returncode, r.stdout.decode('utf-8', 'replace') + r.stderr.decode('utf-8', 'replace')


def mini_tree(base, paths):
    """A temporary directory holding only the patch's files as they are at base (absent ones stay absent)."""
    tree = tempfile.mkdtemp(prefix='replay_')
    for f in paths:
        code, text = sh('git', 'show', f'{base}:{f}')
        if code == 0:
            out = Path(tree) / f
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(subprocess.run(['git', '-C', REPO, 'show', f'{base}:{f}'], capture_output=True).stdout)
    return tree


def recount(diff):
    """The same patch with every hunk header's line counts recomputed from the hunk body (start lines kept)."""
    out, lines, k = [], diff.splitlines(), 0
    while k < len(lines):
        m = re.match(r'@@ -([^ ,]+)(?:,[^ ]+)? \+([^ ,]+)(?:,[^ ]+)? @@(.*)$', lines[k])
        if not m:
            out.append(lines[k])
            k += 1
            continue
        body = []
        k += 1
        while k < len(lines) and not lines[k].startswith(('@@', 'diff --git')):
            body.append(lines[k])
            k += 1
        while body and body[-1] == '':
            body.pop()
        old = sum(1 for l in body if l[:1] in (' ', '-') or l == '')
        new = sum(1 for l in body if l[:1] in (' ', '+') or l == '')
        start = [g if g.isdigit() else '1' for g in m.group(1, 2)]  # placeholders such as 'xxx' become 1
        out.append(f'@@ -{start[0]},{old} +{start[1]},{new} @@{m.group(3)}')
        out += [l if l else ' ' for l in body]
    return '\n'.join(out) + '\n'


def extract(text):
    blocks = re.findall(r'```diff\s*\n(.*?)```', text, re.S)
    return blocks[-1] if blocks else ''


def touched(diff):
    return sorted(set(re.findall(r'^diff --git a/(\S+) b/', diff, re.M)) |
                  {m for m in re.findall(r'^\+\+\+ b/(\S+)', diff, re.M)})


def norm_lines(diff):
    out = set()
    for l in diff.splitlines():
        if l[:1] in '+-' and not l.startswith(('+++', '---')):
            t = re.sub(r'/\*.*?\*/|//.*$', '', l[1:])
            t = re.sub(r'\s+', '', t)
            if t and not t.startswith('*'):
                out.add(l[0] + t)
    return out


def main():
    split = sys.argv[1]
    labels = {r['id']: r for r in json.loads((SAMPLES / 'labels_all.json').read_text(encoding='utf-8'))}
    index = json.loads((HERE / f'prompt_index_{split}.json').read_text(encoding='utf-8'))
    cands = json.loads((HERE / f'candidates_{split}.json').read_text(encoding='utf-8'))
    (HERE / 'patches').mkdir(exist_ok=True)
    rows, by_pair = [], {}
    for x in index:
        r = labels[x['id']]
        mdir = (SAMPLES.parent / ('replay_samples_20261105' if r['batch'] == 1 else 'replay_samples_more_20261105'))
        meta = json.loads((mdir / 'replay' / r['id'] / 'meta.json').read_text(encoding='utf-8'))
        truth = (mdir / 'truth' / r['id'] / 'truth.diff').read_text(encoding='utf-8')
        final = CALLS / x['dir'] / 'final.md'
        diff = extract(final.read_text(encoding='utf-8')) if final.exists() else ''
        p = HERE / 'patches' / f'{x["dir"]}.patch'
        p.write_text(diff, encoding='utf-8', newline='\n')
        strict = recount_ok = fuzzy = None
        if diff:
            tree = mini_tree(meta['base'], touched(diff))
            try:
                strict = sh('git', 'apply', '--check', str(p), cwd=tree)[0] == 0
                recount_ok = strict or sh('git', 'apply', '--check', '--recount', str(p), cwd=tree)[0] == 0
                if not recount_ok:
                    fixed = Path(tree) / 'recounted.patch'
                    fixed.write_text(recount(diff), encoding='utf-8', newline='\n')
                    fuzzy = sh('patch', '-p1', '--fuzz=3', '--dry-run', '-i', str(fixed), cwd=tree)[0] == 0
            finally:
                shutil.rmtree(tree)
        t_files = [f for f in touched(truth) if f.startswith(f'arch/{r["target_arch"]}/')]
        g_files = touched(diff)
        gl, tl = norm_lines(diff), norm_lines('\n'.join(l for l in truth.splitlines()))
        row = {'dir': x['dir'], 'id': r['id'], 'cond': x['cond'], 'batch': r['batch'], 'target_arch': r['target_arch'],
               'kind': r['kind'], 'simple': r['simple'], 'has_diff': bool(diff), 'apply_strict': strict, 'apply_recount': recount_ok,
               'apply_fuzzy': fuzzy, 'gen_files': g_files, 'truth_files': t_files,
               'loc_precision': round(len(set(g_files) & set(t_files)) / len(g_files), 2) if g_files else None,
               'loc_recall': round(len(set(g_files) & set(t_files)) / len(t_files), 2) if t_files else None,
               'cand_covers_truth': round(len(set(cands[r['id']]['files']) & set(t_files)) / len(t_files), 2) if t_files else None,
               'line_overlap_truth': round(len(gl & tl) / len(tl), 2) if tl else None}
        rows.append(row)
        by_pair.setdefault(r['id'], {})[x['cond']] = (diff, truth)
    (HERE / f'eval_{split}.json').write_text(json.dumps(rows, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    rnd, sheet, key = random.Random(1105), [], {}
    for pid in sorted(by_pair):
        conds = sorted(by_pair[pid])
        rnd.shuffle(conds)
        key[pid] = dict(zip('XY', conds))
        truth = next(iter(by_pair[pid].values()))[1]
        sheet.append(f'## {pid}\n\n### 真实补丁T\n\n```diff\n{truth.rstrip()}\n```\n')
        for lab, c in zip('XY', conds):
            sheet.append(f'### {lab}\n\n```diff\n{by_pair[pid][c][0].rstrip() or "（没有补丁）"}\n```\n')
    (HERE / f'blind_{split}.md').write_text('\n'.join(sheet), encoding='utf-8')
    (HERE / f'blind_key_{split}.json').write_text(json.dumps(key, indent=1) + '\n', encoding='utf-8')
    for row in rows:
        print(row['dir'], row['apply_strict'], row['apply_recount'], row['apply_fuzzy'], row['loc_recall'], row['line_overlap_truth'])


if __name__ == '__main__':
    main()
