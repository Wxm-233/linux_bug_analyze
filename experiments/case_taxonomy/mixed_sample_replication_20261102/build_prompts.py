"""Prompts for methods L and RL on the replication sample, using the previous round's prompt() unchanged
(same task text, answer rules and catalog.md). Output: 模型调用测试/2026-11-02/replication_20261102/<method>_<id>/ ;
index prompt_index.json.
"""
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'mixed_sample_llm_assist_20261101'))
import build_prompts as prev  # noqa: E402

CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-02' / 'replication_20261102'


def main():
    if CALLS.exists():
        raise SystemExit('preserve')
    items = json.loads((HERE / 'samples.json').read_text(encoding='utf-8'))['items']
    index = []
    for it in items:
        for method in ('L', 'RL'):
            d = CALLS / ('%s_%s' % (method, it['id']))
            d.mkdir(parents=True)
            (d / 'prompt.md').write_text(prev.prompt(it, method), encoding='utf-8', newline='\n')
            index.append({'dir': d.name, 'method': method, 'id': it['id']})
    (HERE / 'prompt_index.json').write_text(json.dumps(index, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(len(index), 'prompts')


if __name__ == '__main__':
    main()
