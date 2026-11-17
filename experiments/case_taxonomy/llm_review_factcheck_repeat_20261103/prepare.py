"""Copy the 18 held-out step-1 prompts of llm_review_factcheck_20261103 (S1_H1_nn) unchanged into four run directories
each (R2_..R5_), recording SHA-256 (criteria.md section 1). Windows Python; no model calls."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
PREV = HERE.parent / 'llm_review_factcheck_20261103'
SRC = HERE.parents[3] / '模型调用测试' / '2026-11-03' / 'llm_review_factcheck_20261103'
CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-03' / 'llm_review_factcheck_repeat_20261103'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    if CALLS.exists():
        raise SystemExit('preserve')
    base = [x for x in json.loads((PREV / 'items.json').read_text(encoding='utf-8')) if x['set'] == 'heldout']
    out, bad = [], 0
    for run in range(2, 6):
        for it in base:
            src = SRC / it['dir'] / 'prompt.md'
            d = CALLS / f'R{run}_{it["base"]}'
            d.mkdir(parents=True)
            shutil.copyfile(src, d / 'prompt.md')
            bad += sha(src) != sha(d / 'prompt.md')
            out.append({**it, 'run': run, 'dir': d.name})
    (HERE / 'items.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    json.dump([{'dir': x['dir']} for x in out], open(HERE / 'step1_index.json', 'w'))
    print(len(base), 'x 4 =', len(out), 'mismatch', bad)


if __name__ == '__main__':
    main()
