"""Prompts (criteria.md section 3): held-out items without facts (H0_nn) and with facts (H1_nn), using the prompt
format of llm_review_rule_flags_20261103/build.py; the 41 earlier items with facts (O1_nn), made by inserting
facts.md into their earlier prompt text. WSL; no model calls. Output: prompt_index.json and <CALLS>/<dir>/prompt.md.
"""
from pathlib import Path
import importlib.util
import json

HERE = Path(__file__).resolve().parent
PREV = HERE.parent / 'llm_review_rule_flags_20261103'
spec = importlib.util.spec_from_file_location('prev_build', PREV / 'build.py')
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)
CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-03' / 'llm_review_facts_20261103'
PREV_CALLS = P.CALLS
FACTS = (HERE / 'facts.md').read_text(encoding='utf-8').strip()
ANCHOR = '\n\n【规则】'


def with_facts(text):
    assert text.count(ANCHOR) == 1
    return text.replace(ANCHOR, '\n\n' + FACTS + ANCHOR, 1)


def main():
    if CALLS.exists():
        raise SystemExit('preserve')
    index = []
    rows = json.loads((HERE / 'heldout_labels.json').read_text(encoding='utf-8'))['rows']
    for k, r in enumerate(rows):
        item = {**r, 'src': 'mech' if r['snapshot'] == 'v6.6' else 'ctx'}
        base = P.prompt(item)
        for tag, text in (('H0', base), ('H1', with_facts(base))):
            d = CALLS / f'{tag}_{k:02d}'
            d.mkdir(parents=True)
            (d / 'prompt.md').write_text(text, encoding='utf-8', newline='\n')
            index.append({'dir': d.name, 'set': 'heldout', 'facts': tag == 'H1', 'k': k, 'rule': r['rule'],
                          'name': r['name'], 'label': r['label'], 'basis': r['basis']})
    for it in json.loads((PREV / 'items.json').read_text(encoding='utf-8')):
        text = (PREV_CALLS / it['dir'] / 'prompt.md').read_text(encoding='utf-8')
        d = CALLS / ('O1_' + it['dir'][2:])
        d.mkdir(parents=True)
        (d / 'prompt.md').write_text(with_facts(text), encoding='utf-8', newline='\n')
        index.append({'dir': d.name, 'set': 'original', 'facts': True, 'prev_dir': it['dir'], 'rule': it['rule'],
                      'name': it['name'], 'label': it['label'], 'basis': it['basis']})
    (HERE / 'prompt_index.json').write_text(json.dumps(index, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(len(index), 'prompts')


if __name__ == '__main__':
    main()
