"""Test prompts (criteria.md sections 1 and 3): llm_review_v2_dev2_20261104/build.py's prompt (round-1 prompt() with
facts2 and the added bug sentence), one run per item. LoongArch items use it unchanged; MIPS items use the same code
with the architecture set to mips, the facts of facts_test.py and the wording swap RISC-V -> MIPS (R10 references
arm64, x86, RISC-V). Refuses to run unless labels3.json matches labels3_sha256.txt.
WSL (git); no model calls. Output: items.json, step1_index.json and <CALLS>/T1_<cand>/prompt.md."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import facts_test  # noqa: E402  (patches the shared facts module before the prompts are built)

spec = importlib.util.spec_from_file_location('dev2_build', HERE.parent / 'llm_review_v2_dev2_20261104' / 'build.py')
D2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D2)
B = D2.B  # round-1 build module with the round-2 facts and bug sentence
assert B.facts is facts_test.facts
CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-04' / 'llm_review_v2_test_20261104'
LA_SWAP = B.E.swap
R10_MIPS = 'arm64、x86、RISC-V三个实现都调用了某个函数，MIPS的实现没有'


def mips_swap(text):
    text = text.replace(B.E.R10_OLD, '\0R10\0').replace('RISC-V', 'MIPS').replace('\0R10\0', R10_MIPS)
    assert 'RISC-V' not in text.replace(R10_MIPS, '')
    return text


def prompt(r):
    arch = 'mips' if r['cand'].startswith('M') else 'loongarch'
    B.ARCH, B.E.swap = arch, (mips_swap if arch == 'mips' else LA_SWAP)
    return B.prompt(r)


def main():
    if CALLS.exists():
        raise SystemExit('preserve')
    raw = (HERE / 'labels3.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != (HERE / 'labels3_sha256.txt').read_text(encoding='utf-8').split()[0]:
        raise SystemExit('labels3.json changed after its SHA was recorded')
    items, index = [], []
    for r in json.loads(raw.decode('utf-8'))['rows']:
        text, fs = prompt(r)
        d = CALLS / f'T1_{r["cand"]}'
        d.mkdir(parents=True)
        (d / 'prompt.md').write_text(text, encoding='utf-8', newline='\n')
        items.append({'cand': r['cand'], 'group': r['cand'][0], 'dir': d.name, 'rule': r['rule'], 'kind': r.get('kind'),
                      'name': r['name'], 'label3': r['label3'], 'basis3': r['basis3'], 'rev': r['snapshot'], 'facts': fs})
        index.append({'dir': d.name})
    (HERE / 'items.json').write_text(json.dumps(items, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'step1_index.json').write_text(json.dumps(index, indent=1) + '\n', encoding='utf-8')
    print(len(items), 'prompts')


if __name__ == '__main__':
    main()
