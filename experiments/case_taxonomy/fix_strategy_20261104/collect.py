"""Reading material for the fix-strategy labels (criteria.md section 2): for every cross-arch defect (cross == 'C') of
cross_arch_sample_set_20261102/labels_v2_1.json, the fix commit's message and diff (git show -U3, at most 160 diff
lines), with the sample-set labels shown for reference. Development items first, then test items, 15 per batch file.
WSL (git); no model. Output: items.json, dump/{dev,test}_NN.txt."""
from pathlib import Path
import json
import subprocess

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / 'cross_arch_sample_set_20261102' / 'labels_v2_1.json'
REPO = '/root/repos/linux'
KEEP = ('id', 'commit', 'source', 'dev', 'subject', 'files', 'added', 'removed', 'mechanism', 'counterpart_kind',
        'counterpart', 'state', 'masking', 'reason')


def git(*a):
    return subprocess.run(['git', '-C', REPO, *a], capture_output=True).stdout.decode('utf-8', 'replace')


def main():
    if (HERE / 'items.json').exists():
        raise SystemExit('preserve')
    rows = [{k: r[k] for k in KEEP} for r in json.loads(SRC.read_text(encoding='utf-8')) if r['cross'] == 'C']
    rows.sort(key=lambda r: (not r['dev'], r['id']))
    (HERE / 'items.json').write_text(json.dumps(rows, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    for group in ('dev', 'test'):
        part = [r for r in rows if r['dev'] == (group == 'dev')]
        for b in range(0, len(part), 15):
            out = []
            for r in part[b:b + 15]:
                msg = git('log', '-1', '--format=%B', r['commit']).strip().splitlines()
                diff = git('show', '--format=', '-U3', r['commit']).splitlines()
                out += [f'##### {r["id"]} {r["commit"]} {r["subject"]}',
                        f'样本集标签：{r["mechanism"]} {r["counterpart_kind"]} {r["state"]} 掩盖{r["masking"]}；对应物：{r["counterpart"]}；理由：{r["reason"]}',
                        '--- 说明 ---', *[l for l in msg if l.strip()][:14], '--- 改动 ---', *diff[:160]]
                if len(diff) > 160:
                    out.append(f'（改动共{len(diff)}行，只列前160行）')
                out.append('')
            (HERE / 'dump' / f'{group}_{b // 15:02d}.txt').write_text('\n'.join(out) + '\n', encoding='utf-8')
    print(len(rows), 'items', sum(r['dev'] for r in rows), 'dev')


if __name__ == '__main__':
    main()
