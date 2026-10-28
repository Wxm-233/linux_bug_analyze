"""Cross-architecture bridge run for one E1 call.

prepare (WSL): needs -> tree collection (deps pass, then final pass) -> builds on architectures with a
               cross compiler -> per-architecture answers -> value-blind per-arch formalization prompt.
evaluate     : parse formalization; evaluate each candidate once per architecture (unreviewed, and reviewed
               where researcher_review_<tag>.json marks it faithful).
"""
from pathlib import Path
import argparse
import json
import sys

HERE = Path(__file__).resolve().parent
INNER = HERE.parents[2]
CALLS = INNER.parent / '模型调用测试/2026-10-28'
sys.path.insert(0, str(INNER))
from linux_bug_analyze.candidate_bridge import arch_needs, build_arch_queries, evaluate_candidate, formalization_prompt, parse_formalizations  # noqa: E402
from linux_bug_analyze.contract_envelope import document, symbol_type  # noqa: E402

BUILD_ARCHES = {'x86': ('x86_64', '', 'x86_64_defconfig'), 'arm64': ('arm64', 'aarch64-linux-gnu-', 'defconfig'),
                's390': ('s390', 's390x-linux-gnu-', 'defconfig'), 'sparc': ('sparc64', 'sparc64-linux-gnu-', 'sparc64_defconfig'),
                'riscv': ('riscv', 'riscv64-linux-gnu-', 'defconfig')}


def load_e1(e1_dir):
    import re
    e1 = CALLS / e1_dir
    out, current, lines = {}, None, []
    for line in (e1 / 'prompt.md').read_text(encoding='utf-8').splitlines():
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
    final = (e1 / 'final.md').read_text(encoding='utf-8')
    return out, json.loads(final[final.find('{'):final.rfind('}') + 1]).get('candidates', [])


def prepare(e1_dir, parent, tag):
    from linux_bug_analyze.kernel_facts import collect, collect_tree, query, tree_query
    target = HERE / f'{tag}_arch.json'
    if target.exists():
        raise SystemExit('preserve')
    sources, cands = load_e1(e1_dir)
    needs = arch_needs(cands, sources)
    base = {'revision': parent, 'arches': 'all', 'config_symbols': needs['config_symbols'],
            'uapi': [{'header': h, 'macros': needs['macros']} for h in needs['headers']]}
    collect_tree(dict(base, kconfig_symbols=[]), HERE / f'tree/{tag}_deps')
    deps = json.loads((HERE / f'tree/{tag}_deps/tree_bundle.json').read_text())['kconfig_deps']
    import re
    arch_syms = sorted({s for lines in deps.values() for l in lines for s in re.findall(r'\b(ARCH_\w+|HAVE_\w+)\b', l)})
    collect_tree(dict(base, kconfig_symbols=arch_syms), HERE / f'tree/{tag}')
    tree = json.loads((HERE / f'tree/{tag}/tree_bundle.json').read_text())
    cfiles = sorted(p for p in sources if p.endswith('.c') and not p.startswith('arch/'))
    built_file = cfiles[0] if cfiles else None
    builds = {}
    if built_file:
        for a, (arch, cross, defconfig) in BUILD_ARCHES.items():
            spec = {'revision': parent, 'arch': arch, 'cross_compile': cross, 'defconfig': defconfig,
                    'config_set': {s: True for s in needs['config_symbols']}, 'files': [built_file], 'functions': []}
            try:
                collect(spec, HERE / f'builds/{tag}_{a}')
                builds[a] = f'builds/{tag}_{a}/bundle.json'
            except Exception as exc:  # recorded, not retried
                builds[a] = {'error': repr(exc)[:200]}
    bridged = build_arch_queries(cands, sources, needs, deps, built_file)
    answers, types = {}, {}
    for b in bridged:
        i = b['candidate']
        answers[i], types[i] = {}, {}
        for a in tree['arches']:
            bundle = json.loads((HERE / builds[a]).read_text()) if isinstance(builds.get(a), str) else None
            answers[i][a] = {}
            for q in b['queries']:
                if q['kind'] in ('uapi_defined', 'uapi_value', 'kconfig_selects'):
                    ok, value = tree_query(tree, a, q)
                elif q['kind'] == 'constant':
                    ok, value = True, q['value']
                elif bundle is not None:
                    ok, value = query(bundle, q)
                else:
                    ok, value = False, 'no_build_for_arch'
                answers[i][a][q['name']] = {'answered': ok, 'value': value if ok else None, 'reason': None if ok else value}
                if ok and q['name'] not in types[i]:
                    types[i][q['name']] = symbol_type(value)
    out_call = CALLS / f'{tag}_formalize'
    out_call.mkdir(parents=True, exist_ok=False)
    (out_call / 'prompt.md').write_text(formalization_prompt(cands, bridged, types, mode='necessary', per_arch=True), encoding='utf-8')
    target.write_text(json.dumps({'e1_dir': e1_dir, 'parent': parent, 'needs': needs, 'kconfig_deps': deps, 'arch_symbols': arch_syms,
                                  'builds': builds, 'bridged': bridged, 'answers': answers, 'types': types, 'arches': tree['arches']},
                                 ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    built = {a: (json.loads((HERE / v).read_text())['files'][built_file]['build_returncode'] if isinstance(v, str) else v) for a, v in builds.items()}
    print(json.dumps({'needs': needs, 'arch_symbols': arch_syms, 'arches': len(tree['arches']), 'builds': built,
                      'queries_per_candidate': [len(b['queries']) for b in bridged], 'prompt_bytes': len((out_call / 'prompt.md').read_bytes())}))


def evaluate(tag):
    target = HERE / f'{tag}_results.json'
    if target.exists():
        raise SystemExit('preserve')
    call = CALLS / f'{tag}_formalize'
    receipt = json.loads((call / 'receipt.json').read_text(encoding='utf-8'))
    step = json.loads((HERE / f'{tag}_arch.json').read_text(encoding='utf-8'))
    out = {'delivery': receipt.get('status'), 'usage': receipt.get('usage'), 'candidates': []}
    if receipt.get('status') == 'complete_final_received':
        formal = parse_formalizations((call / 'final.md').read_text(encoding='utf-8'))
        review_path = HERE / f'researcher_review_{tag}.json'
        review = json.loads(review_path.read_text(encoding='utf-8')) if review_path.exists() else {}
        docs = {'evidence': document(HERE / f'tree/{tag}/tree_bundle.json', INNER, step['parent'])}
        for b in step['bridged']:
            i = b['candidate']
            f = formal.get(i, {'expressible': False, 'reason': 'missing from model output'})
            verdict = review.get(str(i)) or {}
            rf = verdict.get('normalized_formalization') or f
            row = {'candidate': i, 'formalization': f, 'researcher_review': verdict or None, 'per_arch': {}}
            for a in step['arches']:
                facts = {k: v['value'] for k, v in step['answers'][str(i)][a].items() if v['answered']}
                kw = dict(context=f'{tag}.c{i}.{a}', revision=step['parent'], basis='compiled_object', documents=docs)
                cell = {'unreviewed': evaluate_candidate(f, facts, reviewed=False, **kw)}
                if verdict.get('faithful'):
                    cell['reviewed'] = evaluate_candidate(f, facts, reviewed=True, **kw)
                    if 'normalized_formalization' in verdict:
                        cell['reviewed_normalized'] = evaluate_candidate(rf, facts, reviewed=True, **kw)
                row['per_arch'][a] = cell
            out['candidates'].append(row)
    target.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    for r in out['candidates']:
        un = {a: c['unreviewed'].get('relation_at_observation') or c['unreviewed'].get('status') for a, c in r['per_arch'].items()}
        rv = {a: c['reviewed'].get('relation_at_observation') or c['reviewed'].get('status') for a, c in r['per_arch'].items() if 'reviewed' in c}
        rn = {a: c['reviewed_normalized'].get('relation_at_observation') or c['reviewed_normalized'].get('status') for a, c in r['per_arch'].items() if 'reviewed_normalized' in c}
        print(r['candidate'], 'expressible', r['formalization'].get('expressible'), r['formalization'].get('strength'))
        print('  unreviewed', sorted(set(un.values())))
        if rv:
            print('  reviewed', rv)
        if rn:
            print('  reviewed_normalized', rn)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['prepare', 'evaluate'])
    p.add_argument('--e1')
    p.add_argument('--parent')
    p.add_argument('--tag', required=True)
    a = p.parse_args()
    prepare(a.e1, a.parent, a.tag) if a.command == 'prepare' else evaluate(a.tag)
