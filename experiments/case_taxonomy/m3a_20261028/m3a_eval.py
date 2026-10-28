"""M3a runner (registration_m3a.md): M3 plus the Kbuild applicability fact as every contract's scope. No model calls.

run --commit --label (WSL) -> runs/<label>/{instances,results}.json
A context where the consumer file is not selected by Kbuild is not_applicable (even if its forced build failed); an unknown
selection is facts_unavailable. Everything else is M3 (m3_20261028/m3_eval.py) unchanged.
"""
from pathlib import Path
import argparse
import importlib.util
import json

HERE = Path(__file__).resolve().parent
spec_ = importlib.util.spec_from_file_location('m3_eval', HERE.parent / 'm3_20261028' / 'm3_eval.py')
m3 = importlib.util.module_from_spec(spec_)
spec_.loader.exec_module(m3)
v2, cf, pc, INNER = m3.v2, m3.cf, m3.pc, m3.INNER
from linux_bug_analyze.candidate_bridge import evaluate_candidate  # noqa: E402
from linux_bug_analyze.contract_envelope import document  # noqa: E402

TRACE_CACHE = Path('/root/.cache/linux-bug-analyze/m3a-traces')
short = v2.short


def scoped(contract):
    return dict(contract, config_symbols=['kbuild_selected'], scope={'symbol': 'kbuild_selected'})


def judge(inst, bundle, bpath, rev, tag):
    from linux_bug_analyze.kernel_facts import query
    sel_ok, selected = query(bundle, {'kind': 'kbuild_selected', 'file': inst['file']})
    if sel_ok and selected is False:
        return {'status': 'evaluated', 'applicability': 'not_applicable', 'relation_at_observation': 'not_applicable', 'reasons': ['kbuild_not_selected']}
    if not sel_ok:
        return {'status': 'facts_unavailable', 'missing': ['kbuild_selected'], 'reason': selected}
    if bundle['files'][inst['file']].get('build_returncode'):
        return {'status': 'facts_unavailable', 'missing': ['build']}
    answers = {q['name']: dict(zip(('answered', 'value'), query(bundle, q))) for q in cf.queries(inst)}
    base = cf.contract(dict(inst, gates=[g for g in inst['gates'] if answers[g + '_returns_only_zero']['answered']])) if inst['family'] == 'F2' else cf.contract(inst)
    facts = dict({k: v['value'] for k, v in answers.items() if v['answered']}, kbuild_selected=True)
    return evaluate_candidate(scoped(base), facts, context=f'm3a.{tag}.{inst["id"]}', revision=rev, basis='compiled_object',
                              documents={'evidence': document(HERE / bpath, INNER, rev)}, reviewed=True)


def run(commit, label):
    out = HERE / 'runs' / label
    if (out / 'results.json').exists():
        raise SystemExit('preserve')
    out.mkdir(parents=True, exist_ok=True)
    fix, parent = v2.full(commit), v2.full(commit + '^')
    files = m3.consumer_files(fix)
    if not files:
        (out / 'results.json').write_text(json.dumps({'commit': fix, 'status': 'e4_not_applicable'}) + '\n')
        return
    instances, trace_status = [], {}
    for path in files:
        text = v2.git('show', parent + ':' + path).stdout.decode('utf-8', 'replace')
        configs = pc.guard_configs(text)
        traces = {}
        for ctx, (arch, cross, defconfig, cfg) in v2.TRACE_CONTEXTS.items():
            bundle, err = v2._collect(v2._spec(parent, arch, cross, defconfig, cfg, configs, [path], macros='*'),
                                      TRACE_CACHE / label / path.replace('/', '_') / ctx)
            entry = bundle['files'][path] if bundle else {}
            if bundle and entry.get('macro_trace_returncode') == 0:
                traces[ctx] = entry.get('macros') or {}
        trace_status[path] = 'trace_failed' if not traces else 'single_trace' if len(traces) == 1 else 'ok'
        found = cf.f3_instances(text, path)
        if traces:
            found = (cf.f1_instances(text, traces, direct=False, provided='fallback') + cf.f1d_instances(text, traces)
                     + cf.f2_instances(text, traces, limit_contains_g=True) + found)
        for inst in found:
            instances.append(dict(inst, file=path, configs=configs, id='%s.%d' % (inst['family'], len(instances))))
    (out / 'instances.json').write_text(json.dumps({'commit': fix, 'parent': parent, 'files': files, 'trace_status': trace_status,
                                                    'instances': instances}, indent=1) + '\n')
    if not instances:
        status = 'trace_failed' if all(s == 'trace_failed' for s in trace_status.values()) else 'no_instances'
        (out / 'results.json').write_text(json.dumps({'commit': fix, 'status': status, 'trace_status': trace_status}) + '\n')
        return
    by_file = {}
    for i in instances:
        by_file.setdefault(i['file'], []).append(i)

    def needs(insts):
        qs = [q for i in insts for q in cf.queries(i)]
        return (sorted({q['macro'] for q in qs if q['kind'] in ('macro_provided', 'macro_defined')}) or ['__lba_none__'],
                sorted({q['macro'] for q in qs if q['kind'] == 'macro_value'}), sorted({q['function'] for q in qs if q['kind'] == 'returns_only_zero'}))

    def facts_at(rev, ctx, tag, path):
        arch, cross, defconfig, cfg = v2.JUDGE_CONTEXTS[ctx]
        macros, values, functions = needs(by_file[path])
        rel = f'runs/{label}/builds/{tag}_{ctx}_{path.replace("/", "_")}'
        configs = sorted({c for i in by_file[path] for c in i['configs']})
        bundle, err = v2._collect(v2._spec(rev, arch, cross, defconfig, cfg, configs, [path], macros=macros, macro_values=values,
                                           optimized_functions=functions), HERE / rel)
        return rel + '/bundle.json', bundle, err

    revisions = {'parent': parent, 'fix': fix}
    cells, builds = {}, {}
    for rv, rev in revisions.items():
        cells[rv], builds[rv] = {}, {}
        for ctx in v2.JUDGE_CONTEXTS:
            cells[rv][ctx] = {}
            for path, insts in by_file.items():
                bpath, bundle, err = facts_at(rev, ctx, rv, path)
                builds[rv][f'{ctx}:{path}'] = bpath if bundle else {'error': err}
                for i in insts:
                    cells[rv][ctx][i['id']] = judge(i, bundle, bpath, rev, f'{label}.{rv}.{ctx}') if bundle else {'status': 'facts_unavailable', 'missing': ['build']}
    flags = {rv: {(iid, ctx) for ctx, per in cells[rv].items() for iid, c in per.items() if short(c) == 'violated'} for rv in revisions}
    both = sorted(flags['parent'] & flags['fix'])
    labels, ml_cache = [], {}
    by_id = {i['id']: i for i in instances}
    mainline = v2.full(v2.MAINLINE)
    for iid, ctx in both:
        key = (ctx, by_id[iid]['file'])
        if key not in ml_cache:
            ml_cache[key] = facts_at(mainline, ctx, 'mainline', by_id[iid]['file'])
        bpath, bundle, err = ml_cache[key]
        c = judge(by_id[iid], bundle, bpath, mainline, f'{label}.mainline.{ctx}') if bundle else {'status': 'facts_unavailable'}
        labels.append({'id': iid, 'context': ctx, 'mainline': short(c),
                       'label': {'violated': 'persists_in_mainline', 'satisfied': 'resolved_in_mainline', 'not_applicable': 'resolved_in_mainline'}.get(short(c), 'mainline_undecidable')})
    fam = lambda pairs: {k: sum(1 for iid, _ in pairs if (by_id[iid]['family'] + ('d' if by_id[iid].get('kind') == 'direct_placeholder' else '')) == k)
                         for k in ('F1', 'F1d', 'F2', 'F3')}
    status_counts = {rv: {} for rv in revisions}
    for rv in revisions:
        for per in cells[rv].values():
            for c in per.values():
                status_counts[rv][short(c)] = status_counts[rv].get(short(c), 0) + 1
    summary = {'commit': fix, 'files': files, 'trace_status': trace_status, 'instances': len(instances),
               'parent_only': sorted(flags['parent'] - flags['fix']), 'fix_only': sorted(flags['fix'] - flags['parent']), 'both': both,
               'by_family': {'parent_only': fam(flags['parent'] - flags['fix']), 'fix_only': fam(flags['fix'] - flags['parent']), 'both': fam(both)},
               'labels': {k: sum(l['label'] == k for l in labels) for k in ('resolved_in_mainline', 'persists_in_mainline', 'mainline_undecidable')},
               'status_counts': status_counts}
    (out / 'results.json').write_text(json.dumps({'summary': summary, 'builds': builds, 'cells': cells, 'labels': labels}, indent=1) + '\n')
    print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in summary.items() if k not in ('files', 'commit')}))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['run'])
    p.add_argument('--commit', required=True)
    p.add_argument('--label', required=True)
    a = p.parse_args()
    run(a.commit, a.label)
