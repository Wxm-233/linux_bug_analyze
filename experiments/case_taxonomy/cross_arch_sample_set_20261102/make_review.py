"""Second-review package for GPT (criteria_amendment.md): for the 40 rows of second_sample.json, writes each commit's
message (trailers dropped) and diff (first 200 lines, device-tree files excluded) to second_review/材料/, one file per
commit and one combined file, plus a blank answer sheet. Does not read or copy the first-pass labels. WSL.
"""
from pathlib import Path
import csv
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'mech_state_size_checker_20261101'))
import checker as CK  # noqa: E402  (git)
from collect import TRAILER  # noqa: E402

ARGS = sys.argv[1:] or ['second_sample.json', 'second_review']
OUT = HERE / ARGS[1]
DIFF_LINES = 200


def text(n, row):
    sha = row['commit']
    msg = [l for l in CK.git('log', '-1', '--format=%B', sha).splitlines() if not TRAILER.match(l.strip())]
    stat = CK.git('show', '--format=', '--stat=100', sha).rstrip()
    diff = CK.git('show', '--format=', '-U3', sha, '--', '.', ':(exclude)arch/riscv/boot/dts').splitlines()
    more = f'\n...（改动其余{len(diff) - DIFF_LINES}行省略）' if len(diff) > DIFF_LINES else ''
    date = CK.git('log', '-1', '--format=%as', sha).strip()
    return (f'########## 第{n}条  编号 {row["id"]}  提交 {sha}  日期 {date}\n\n【提交说明】\n'
            + '\n'.join(msg).strip() + f'\n\n【改动统计】\n{stat}\n\n【改动内容】\n' + '\n'.join(diff[:DIFF_LINES]) + more + '\n')


def main():
    rows = json.loads((HERE / ARGS[0]).read_text(encoding='utf-8'))
    mat = OUT / '材料'
    if mat.exists():
        raise SystemExit('preserve')
    mat.mkdir(parents=True)
    texts = []
    for n, row in enumerate(rows, 1):
        t = text(n, row)
        (mat / f'{n:02d}_{row["id"]}.txt').write_text(t, encoding='utf-8')
        texts.append(t)
    (OUT / '全部40条材料.txt').write_text('\n\n'.join(texts), encoding='utf-8')
    with open(OUT / 'answers_template.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['序号', '编号', '提交', '机制', '跨架构', '对应物种类', '对应物位置', '理由'])
        for n, row in enumerate(rows, 1):
            w.writerow([n, row['id'], row['commit'], '', '', '', '', ''])
    print(len(rows), sum(len(t) for t in texts))


if __name__ == '__main__':
    main()
