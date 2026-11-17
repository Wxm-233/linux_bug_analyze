"""Write one prompt.md per (method, item) for methods L and RL (criteria.md), plus RL repeats for 20 items
(random.Random(20261101)). L and RL share the task text and answer rules; RL adds catalog.md and the checker result.
Output directories: 模型调用测试/2026-11-01/mixed_20261101/<method>_<id>/ ; index: prompt_index.json.
"""
from pathlib import Path
import json
import random

HERE = Path(__file__).resolve().parent
OUTER = HERE.parents[3]
CALLS = OUTER / '模型调用测试' / '2026-11-01' / 'mixed_20261101'

TASK = """You are reviewing one function from the RISC-V architecture code of the Linux kernel.

Decide whether this function, as shown, contains a real bug: incorrect behaviour on some reachable path or
configuration. Style issues, missing optimisations and hypothetical misuse by future callers do not count.
"""
ANSWER = """Answer with one JSON object and nothing else:
{"verdict": "bug" or "no_bug", "confidence": a number from 0 to 1, "lines": [line numbers of the faulty code, empty if no_bug], "mechanism": %s, "requirement": "the violated requirement, or empty", "reason": "at most three sentences"}
Claim "bug" only if you can name the concrete requirement that is violated and the lines that violate it.
"""
MECH_L = '"a short label for the kind of defect, or none"'
MECH_RL = '"one of M1 to M9 from the catalog, or none"'


def rule_text(rule):
    if rule.get('note') == 'outside checker scope':
        return ('Automatic checker (mechanism M2 only, architecture hugetlb files only): this function is outside its '
                'scope, so there is no automatic evidence either way.')
    if not rule['sites']:
        return 'Automatic checker (mechanism M2 only): no site where size or grouping is decoded from an entry.'
    out = ['Automatic checker (mechanism M2 only) found these sites where size or grouping is decoded from an entry:']
    for s in rule['sites']:
        cls = sorted({c['class'] for c in s.get('callers') or []})
        out.append('- line %d, %s(): verdict %s; common callers classified %s (NP = may pass a non-present entry, '
                   'P = present, U = unconstrained)' % (s['line'], s['decoder'], s['verdict'], ', '.join(cls) or 'n/a'))
    return '\n'.join(out)


def prompt(it, method):
    parts = [TASK]
    if method == 'RL':
        parts += [(HERE / 'catalog.md').read_text(encoding='utf-8').strip(), '', rule_text(it['rule']), '']
    parts += ['File: %s' % it['path'], '', 'Function (left column: file line numbers):', '```c', it['code'], '```', '']
    if it['callees']:
        parts += ['Functions from the same file that it calls:', '```c', it['callees'], '```', '']
    parts.append(ANSWER % (MECH_RL if method == 'RL' else MECH_L))
    return '\n'.join(parts)


def main():
    if CALLS.exists():
        raise SystemExit('preserve')
    items = json.loads((HERE / 'samples.json').read_text(encoding='utf-8'))['items']
    repeat = set(random.Random(20261101).sample([i['id'] for i in items], 20))
    index = []
    for it in items:
        for method in ['L', 'RL'] + (['RLrep'] if it['id'] in repeat else []):
            d = CALLS / ('%s_%s' % (method, it['id']))
            d.mkdir(parents=True)
            (d / 'prompt.md').write_text(prompt(it, 'RL' if method == 'RLrep' else method), encoding='utf-8', newline='\n')
            index.append({'dir': d.name, 'method': method, 'id': it['id']})
    (HERE / 'prompt_index.json').write_text(json.dumps(index, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(len(index), 'prompts;', sum(x['method'] == 'RLrep' for x in index), 'repeats')


if __name__ == '__main__':
    main()
