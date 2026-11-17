"""Prompts (criteria.md section 3 as changed by criteria_amendment1.md section 3) for every labelled LoongArch
candidate: prompt() of llm_review_rule_flags_20261103/build.py at the candidate's snapshot with the architecture
wording swapped (RISC-V -> LoongArch; R10 references arm64, x86, RISC-V), no facts.md, output requirement replaced by
NEW_TAIL of llm_review_factcheck_20261103/build_step1.py, written identically to R1_nn, R2_nn, R3_nn; and the swapped
plain prompt() text as the optional control C0_nn. Refuses to run unless labels.json matches labels_sha256.txt.
WSL (git); no model calls. Output: items.json, step1_index.json, control_index.json and <CALLS>/<dir>/prompt.md."""
from pathlib import Path
import hashlib
import importlib.util
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


P = mod('prev_build', ROOT / 'llm_review_rule_flags_20261103' / 'build.py')
S1 = mod('step1_build', ROOT / 'llm_review_factcheck_20261103' / 'build_step1.py')
CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-03' / 'llm_review_expand_20261103'
R10_OLD = 'arm64、x86、LoongArch三个实现都调用了某个函数，RISC-V的实现没有'
R10_NEW = 'arm64、x86、RISC-V三个实现都调用了某个函数，LoongArch的实现没有'


def swap(text):
    """Amendment 1 section 3: RISC-V -> LoongArch everywhere, except the R10 reference list."""
    text = text.replace(R10_OLD, '\0R10\0').replace('RISC-V', 'LoongArch').replace('\0R10\0', R10_NEW)
    assert 'RISC-V' not in text.replace(R10_NEW, '')
    return text


def main():
    if CALLS.exists():
        raise SystemExit('preserve')
    raw = (HERE / 'labels.json').read_bytes()
    want = (HERE / 'labels_sha256.txt').read_text(encoding='utf-8').split()[0]
    if hashlib.sha256(raw).hexdigest() != want:
        raise SystemExit('labels.json changed after its SHA was recorded')
    items, step1, control = [], [], []
    for r in json.loads(raw.decode('utf-8'))['rows']:
        snap = r['snapshot']
        P.REVS[snap] = snap
        base = swap(P.prompt({**r, 'src': snap}))
        text = base.rstrip()
        assert text.endswith(S1.OLD_TAIL), r['cand']
        text = text[:-len(S1.OLD_TAIL)] + S1.NEW_TAIL + '\n'
        for run in (1, 2, 3):
            d = CALLS / f'R{run}_{r["cand"]:02d}'
            d.mkdir(parents=True)
            (d / 'prompt.md').write_text(text, encoding='utf-8', newline='\n')
            items.append({'cand': r['cand'], 'run': run, 'dir': d.name, 'rule': r['rule'], 'name': r['name'],
                          'label': r['label'], 'rev': snap})
            step1.append({'dir': d.name})
        d = CALLS / f'C0_{r["cand"]:02d}'
        d.mkdir(parents=True)
        (d / 'prompt.md').write_text(base, encoding='utf-8', newline='\n')
        control.append({'dir': d.name, 'cand': r['cand'], 'label': r['label']})
    (HERE / 'items.json').write_text(json.dumps(items, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'step1_index.json').write_text(json.dumps(step1, indent=1) + '\n', encoding='utf-8')
    (HERE / 'control_index.json').write_text(json.dumps(control, indent=1) + '\n', encoding='utf-8')
    print(len(items), 'step-1 prompts,', len(control), 'control prompts')


if __name__ == '__main__':
    main()
