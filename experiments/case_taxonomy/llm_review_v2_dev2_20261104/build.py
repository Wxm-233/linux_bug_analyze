"""Development round-2 prompts (criteria.md section 1): llm_review_v2_dev_20261104/build.py's prompt() with the
round-2 facts (facts2.py) and one added sentence in the bug definition, written identically to D1_nn and D2_nn.
Refuses to run unless the round-1 labels3.json matches its recorded SHA. WSL (git); no model calls.
Output: items.json, step1_index.json and <CALLS>/D{1,2}_nn/prompt.md."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
DEV1 = HERE.parent / 'llm_review_v2_dev_20261104'
sys.path.insert(0, str(HERE))
import facts2  # noqa: E402

spec = importlib.util.spec_from_file_location('dev1_build', DEV1 / 'build.py')
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
B.facts = facts2.facts
OLD_BUG = '- bug：在该版本某个能选到的配置、能走到的路径下，会造成实际错误：崩溃、死锁、“在原子上下文中睡眠”一类的警告、错误数据或返回值、安全问题（含推测执行越界）。'
assert B.TAIL.count(OLD_BUG) == 1
B.TAIL = B.TAIL.replace(OLD_BUG, OLD_BUG + '返回给用户态的值违反该接口的文档说明，也算错误的返回值。')
CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-04' / 'llm_review_v2_dev2_20261104'


def main():
    if CALLS.exists():
        raise SystemExit('preserve')
    raw = (DEV1 / 'labels3.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != (DEV1 / 'labels3_sha256.txt').read_text(encoding='utf-8').split()[0]:
        raise SystemExit('labels3.json changed after its SHA was recorded')
    items, index = [], []
    for r in json.loads(raw.decode('utf-8'))['rows']:
        text, fs = B.prompt(r)
        for run in (1, 2):
            d = CALLS / f'D{run}_{r["cand"]:02d}'
            d.mkdir(parents=True)
            (d / 'prompt.md').write_text(text, encoding='utf-8', newline='\n')
            items.append({'cand': r['cand'], 'run': run, 'dir': d.name, 'rule': r['rule'], 'kind': r.get('kind'),
                          'name': r['name'], 'label3': r['label3'], 'basis3': r['basis3'], 'rev': r['snapshot'],
                          'facts': fs})
            index.append({'dir': d.name})
    (HERE / 'items.json').write_text(json.dumps(items, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'step1_index.json').write_text(json.dumps(index, indent=1) + '\n', encoding='utf-8')
    print(len(items), 'prompts')


if __name__ == '__main__':
    main()
