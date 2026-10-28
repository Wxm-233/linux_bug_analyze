"""Pilot-2 bridge step 1 (WSL): candidate -> queries -> fact bundle -> answers -> formalization prompt.
Pilot 2 is already contacted and is not evaluated."""
from pathlib import Path
import json
import re
import sys

HERE = Path(__file__).resolve().parent
INNER = HERE.parents[2]
sys.path.insert(0, str(INNER))
from linux_bug_analyze.candidate_bridge import build_queries, formalization_prompt  # noqa: E402
from linux_bug_analyze.contract_envelope import symbol_type  # noqa: E402
from linux_bug_analyze.kernel_facts import collect, query  # noqa: E402

CALL = INNER.parent / '模型调用测试/2026-10-28/e1_pilot_2'
OUTCALL = INNER.parent / '模型调用测试/2026-10-28/bridge_formalize_pilot2'


def sources_from_prompt(prompt):
    out, current, lines = {}, None, []
    for line in prompt.splitlines():
        m = re.match(r'^=== FILE: (.+) ===$', line)
        if m:
            if current:
                out[current] = '\n'.join(lines) + '\n'
            current, lines = m.group(1), []
        elif current is not None:
            n = re.match(r'^\s*\d+  (.*)$', line)
            if n:
                lines.append(n.group(1))
    if current:
        out[current] = '\n'.join(lines) + '\n'
    return out


def main():
    target = HERE / 'pilot_bridged.json'
    if target.exists():
        raise SystemExit('preserve')
    meta = json.loads((HERE.parent / 'eval_prep_20261028/e1_pilot_prompts.json').read_text())[1]
    sources = sources_from_prompt((CALL / 'prompt.md').read_text(encoding='utf-8'))
    final = (CALL / 'final.md').read_text(encoding='utf-8')
    cands = json.loads(final[final.find('{'):final.rfind('}') + 1])['candidates']
    bridged = build_queries(cands, sources)
    functions = sorted({f for b in bridged for f in b['functions']})
    spec = {'revision': meta['parent'], 'arch': 'x86_64', 'defconfig': 'x86_64_defconfig', 'config_set': {},
            'files': sorted(sources), 'functions': functions}
    (HERE / 'spec_pilot2.json').write_text(json.dumps(spec, indent=1) + '\n')
    collect(spec, HERE / 'bundle_pilot2')
    bundle = json.loads((HERE / 'bundle_pilot2/bundle.json').read_text(encoding='utf-8'))
    types, answers = {}, {}
    for b in bridged:
        types[b['candidate']], answers[b['candidate']] = {}, {}
        for q in b['queries']:
            ok, value = query(bundle, q)
            answers[b['candidate']][q['name']] = {'answered': ok, 'value': value if ok else None, 'reason': None if ok else value}
            if ok:
                types[b['candidate']][q['name']] = symbol_type(value)
    OUTCALL.mkdir(parents=True, exist_ok=False)
    (OUTCALL / 'prompt.md').write_text(formalization_prompt(cands, bridged, types), encoding='utf-8')
    out = {'functions': functions, 'bridged': bridged, 'answers': answers, 'types': types,
           'bundle': 'bundle_pilot2/bundle.json', 'callers': {p: e.get('callers') for p, e in bundle['files'].items()}}
    target.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    total = sum(len(b['queries']) for b in bridged)
    answered = sum(a['answered'] for c in answers.values() for a in c.values())
    by_kind = {}
    for b in bridged:
        for q in b['queries']:
            k = q['kind']
            by_kind.setdefault(k, [0, 0])
            by_kind[k][0] += 1
            by_kind[k][1] += answers[b['candidate']][q['name']]['answered']
    print(json.dumps({'candidates': len(bridged), 'functions': len(functions), 'queries': total, 'answered': answered,
                      'by_kind_total_answered': by_kind, 'prompt_bytes': len((OUTCALL / 'prompt.md').read_bytes())}))


if __name__ == '__main__':
    main()
