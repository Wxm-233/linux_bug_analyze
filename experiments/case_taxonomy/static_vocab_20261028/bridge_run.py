"""Generic bridge run over one E1 call directory.

prepare (WSL): sources+candidates -> queries -> fact bundle -> answers -> value-blind formalization prompt.
evaluate     : parse the formalization call, validate, evaluate unreviewed (and reviewed where a
               researcher_review_<tag>.json marks a candidate faithful).
"""
from pathlib import Path
import argparse
import json
import re
import sys

HERE = Path(__file__).resolve().parent
INNER = HERE.parents[2]
CALLS = INNER.parent / '模型调用测试/2026-10-28'
sys.path.insert(0, str(INNER))
from linux_bug_analyze.candidate_bridge import build_queries, evaluate_candidate, formalization_prompt, parse_formalizations  # noqa: E402
from linux_bug_analyze.contract_envelope import document, symbol_type  # noqa: E402

ARCH = {'x86': ('x86_64', '', 'x86_64_defconfig'), 'arm64': ('arm64', 'aarch64-linux-gnu-', 'defconfig'),
        'sparc': ('sparc64', 'sparc64-linux-gnu-', 'sparc64_defconfig'), 's390': ('s390', 's390x-linux-gnu-', 'defconfig')}


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


def prepare(e1_dir, parent, tag):
    from linux_bug_analyze.kernel_facts import collect, query
    target = HERE / f'{tag}_bridged.json'
    if target.exists():
        raise SystemExit('preserve')
    e1 = CALLS / e1_dir
    sources = sources_from_prompt((e1 / 'prompt.md').read_text(encoding='utf-8'))
    final = (e1 / 'final.md').read_text(encoding='utf-8')
    cands = json.loads(final[final.find('{'):final.rfind('}') + 1]).get('candidates', [])
    bridged = build_queries(cands, sources)
    first = sorted(sources)[0]
    key = first.split('/')[1] if first.startswith('arch/') else 'x86'
    arch, cross, defconfig = ARCH.get(key, ARCH['x86'])
    functions = sorted({f for b in bridged for f in b['functions']})
    spec = {'revision': parent, 'arch': arch, 'cross_compile': cross, 'defconfig': defconfig, 'config_set': {},
            'files': sorted(p for p in sources if p.endswith('.c')), 'functions': functions}
    (HERE / 'specs').mkdir(exist_ok=True)
    (HERE / f'specs/{tag}.json').write_text(json.dumps(spec, indent=1) + '\n')
    collect(spec, HERE / f'bundles/{tag}')
    bundle = json.loads((HERE / f'bundles/{tag}/bundle.json').read_text(encoding='utf-8'))
    types, answers, by_kind = {}, {}, {}
    for b in bridged:
        types[b['candidate']], answers[b['candidate']] = {}, {}
        for q in b['queries']:
            ok, value = query(bundle, q)
            answers[b['candidate']][q['name']] = {'answered': ok, 'value': value if ok else None, 'reason': None if ok else value}
            by_kind.setdefault(q['kind'], [0, 0])
            by_kind[q['kind']][0] += 1
            by_kind[q['kind']][1] += ok
            if ok:
                types[b['candidate']][q['name']] = symbol_type(value)
    out_call = CALLS / f'{tag}_formalize'
    out_call.mkdir(parents=True, exist_ok=False)
    (out_call / 'prompt.md').write_text(formalization_prompt(cands, bridged, types), encoding='utf-8')
    builds = {p: e.get('build_returncode') for p, e in bundle['files'].items()}
    target.write_text(json.dumps({'e1_dir': e1_dir, 'parent': parent, 'spec': spec, 'builds': builds, 'bridged': bridged,
                                  'answers': answers, 'types': types, 'by_kind': by_kind}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'tag': tag, 'arch': arch, 'builds': builds, 'candidates': len(bridged), 'functions': len(functions),
                      'queries': sum(v[0] for v in by_kind.values()), 'answered': sum(v[1] for v in by_kind.values()),
                      'by_kind': by_kind, 'prompt_bytes': len((out_call / 'prompt.md').read_bytes())}))


def evaluate(tag, facts_tag=None):
    facts_tag = facts_tag or tag
    target = HERE / f'{tag}_results.json'
    if target.exists():
        raise SystemExit('preserve')
    call = CALLS / f'{tag}_formalize'
    receipt = json.loads((call / 'receipt.json').read_text(encoding='utf-8'))
    step1 = json.loads((HERE / f'{facts_tag}_bridged.json').read_text(encoding='utf-8'))
    out = {'delivery': receipt.get('status'), 'usage': receipt.get('usage'), 'elapsed_seconds': receipt.get('elapsed_seconds'), 'candidates': []}
    if receipt.get('status') == 'complete_final_received':
        formal = parse_formalizations((call / 'final.md').read_text(encoding='utf-8'))
        review_path = HERE / f'researcher_review_{tag}.json'
        review = json.loads(review_path.read_text(encoding='utf-8')) if review_path.exists() else {}
        docs = {'evidence': document(HERE / f'bundles/{facts_tag}/bundle.json', INNER, step1['parent'])}
        for b in step1['bridged']:
            i = b['candidate']
            facts = {k: v['value'] for k, v in step1['answers'][str(i)].items() if v['answered']}
            f = formal.get(i, {'expressible': False, 'reason': 'missing from model output'})
            kw = dict(context=f'{tag}.c{i}', revision=step1['parent'], basis='compiled_object', documents=docs)
            row = {'candidate': i, 'formalization': f, 'unreviewed': evaluate_candidate(f, facts, reviewed=False, **kw),
                   'researcher_review': review.get(str(i))}
            verdict = review.get(str(i)) or {}
            if verdict.get('faithful'):
                rf = verdict.get('normalized_formalization') or f
                rfacts = dict(facts, build_context=True) if 'build_context' in json.dumps(rf) else facts
                row['reviewed'] = evaluate_candidate(rf, rfacts, reviewed=True, **kw)
                row['reviewed_used_normalization'] = 'normalized_formalization' in verdict
            out['candidates'].append(row)
    target.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'delivery': out['delivery'], 'expressible': sum(1 for r in out['candidates'] if r['formalization'].get('expressible')),
                      'candidates': len(out['candidates']),
                      'unreviewed': [r['unreviewed'].get('status') + ':' + str(r['unreviewed'].get('relation_at_observation')) for r in out['candidates']],
                      'reviewed': [(r['candidate'], r.get('reviewed', {}).get('relation_at_observation')) for r in out['candidates'] if 'reviewed' in r]}, ensure_ascii=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['prepare', 'evaluate'])
    p.add_argument('--e1')
    p.add_argument('--parent')
    p.add_argument('--tag', required=True)
    p.add_argument('--facts-tag')
    a = p.parse_args()
    prepare(a.e1, a.parent, a.tag) if a.command == 'prepare' else evaluate(a.tag, a.facts_tag)
