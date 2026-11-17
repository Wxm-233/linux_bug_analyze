"""Copy the 59 'with facts' prompts of llm_review_facts_20261103 (H1_nn, O1_nn) unchanged into four new run directories
each (R2_..R5_), recording source and copy SHA-256 (criteria.md sections 1-2). Windows Python; no model calls."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
PREV = HERE.parent / 'llm_review_facts_20261103'
SRC = HERE.parents[3] / '模型调用测试' / '2026-11-03' / 'llm_review_facts_20261103'
CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-03' / 'llm_review_majority_20261103'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    if CALLS.exists():
        raise SystemExit('preserve')
    base = [x for x in json.loads((PREV / 'prompt_index.json').read_text(encoding='utf-8')) if x['facts']]
    index, bad = [], 0
    for run in range(2, 6):
        for it in base:
            src = SRC / it['dir'] / 'prompt.md'
            d = CALLS / f'R{run}_{it["dir"]}'
            d.mkdir(parents=True)
            shutil.copyfile(src, d / 'prompt.md')
            bad += sha(src) != sha(d / 'prompt.md')
            index.append({**it, 'run': run, 'base_dir': it['dir'], 'dir': d.name})
    (HERE / 'prompt_index.json').write_text(json.dumps(index, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(len(base), 'prompts x 4 runs =', len(index), 'mismatch', bad)


if __name__ == '__main__':
    main()
