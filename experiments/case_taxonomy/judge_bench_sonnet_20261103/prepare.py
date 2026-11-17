"""Copy the 154 prompts of judge_bench_dev_20261103 unchanged into this round's call directory (criteria.md section
1) and record the SHA-256 of every source and copy. Windows Python; no model calls. Output: prompt_copy.json.
"""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
SRC_ROUND = HERE.parent / 'judge_bench_dev_20261103'
SRC = HERE.parents[3] / '模型调用测试' / '2026-11-03' / 'judge_bench_dev_20261103'
CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-03' / 'judge_bench_sonnet_20261103'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    if CALLS.exists():
        raise SystemExit('preserve')
    index = json.loads((SRC_ROUND / 'prompt_index.json').read_text(encoding='utf-8'))
    rows = []
    for it in index:
        src = SRC / it['dir'] / 'prompt.md'
        dst = CALLS / it['dir'] / 'prompt.md'
        dst.parent.mkdir(parents=True)
        shutil.copyfile(src, dst)
        rows.append({'dir': it['dir'], 'source_sha256': sha(src), 'copy_sha256': sha(dst)})
    bad = [r['dir'] for r in rows if r['source_sha256'] != r['copy_sha256']]
    (HERE / 'prompt_copy.json').write_text(json.dumps({'copied': len(rows), 'mismatch': bad, 'rows': rows}, indent=1)
                                           + '\n', encoding='utf-8')
    print(len(rows), 'copied', len(bad), 'mismatch')


if __name__ == '__main__':
    main()
