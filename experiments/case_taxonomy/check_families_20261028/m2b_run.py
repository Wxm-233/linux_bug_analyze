"""M2b (registration_m2b.md): tightened instances on the M2 facts, then mainline outcome labels.

instances (WSL): re-enumerate with F1b/F2b from the M2 parent traces -> <case>/instances_m2b.json (ids = M2 ids)
evaluate       : M2a gate rule on the M2 facts for the M2b subset -> <case>/results_m2b.json
mainline  (WSL): facts for every M2b instance at mainline in the case's contexts (die riscv without the old flags)
                 -> <case>/facts_mainline_m2b.json
label          : outcome label for each observation reported in both parent and fix -> <case>/labels_m2b.json
"""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
spec_ = importlib.util.spec_from_file_location('check_run', HERE / 'check_run.py')
m2 = importlib.util.module_from_spec(spec_)
spec_.loader.exec_module(m2)
cf, m1, INNER = m2.cf, m2.m1, m2.INNER
from linux_bug_analyze.candidate_bridge import evaluate_candidate  # noqa: E402
from linux_bug_analyze.contract_envelope import document  # noqa: E402

MAINLINE = 'df2908090cda'  # v7.3-rc2, as checked for the upstream drafts
short = lambda x: x.get('relation_at_observation') or x.get('status')


def key(i):
    return (i['family'], i.get('site'), i.get('geometry'), i.get('limit'))


def instances(case):
    out_dir = HERE / case
    target = out_dir / 'instances_m2b.json'
    if target.exists():
        raise SystemExit('preserve')
    m2_inst = json.loads((out_dir / 'instances.json').read_text(encoding='utf-8'))['instances']
    ids = {key(i): i['id'] for i in m2_inst}
    found = []
    for path, text in m1.touched(case).items():
        if not path.endswith('.c'):
            continue
        traces = {ctx: json.loads((m2.TRACE_CACHE / case / ctx / 'bundle.json').read_text())['files'][path].get('macros') or {}
                  for ctx in m1.TRACE_CONTEXTS}
        for inst in cf.f1_instances(text, traces, direct=False) + cf.f2_instances(text, traces, limit_contains_g=True):
            if key(inst) not in ids:
                raise SystemExit('M2b instance not in M2: %r' % (key(inst),))  # M2b must be a subset of M2
            found.append(dict(inst, file=path, id=ids[key(inst)]))
    dropped = sorted(set(ids.values()) - {i['id'] for i in found})
    target.write_text(json.dumps({'case': case, 'instances': found, 'dropped_m2_ids': dropped}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'case': case, 'kept': len(found), 'dropped': len(dropped)}))


def _judge(case, inst, answers_by_ctx, builds, revision, tag):
    cells = {}
    for ctx, per in answers_by_ctx.items():
        a = per[inst['id']]
        bpath = builds[ctx]
        docs = {'evidence': document(HERE / (bpath if isinstance(bpath, str) else f'{case}/facts.json'), INNER, revision)}
        facts = {k: v['value'] for k, v in a.items() if v['answered']}
        cells[ctx] = evaluate_candidate(m2.m2a_contract(inst, a), facts, context=f'm2b.{case}.{inst["id"]}.{tag}.{ctx}',
                                        revision=revision, basis='compiled_object', documents=docs, reviewed=True)
    return cells


def evaluate(case):
    c, out_dir = m1.CASES[case], HERE / case
    target = out_dir / 'results_m2b.json'
    if target.exists():
        raise SystemExit('preserve')
    inst = json.loads((out_dir / 'instances_m2b.json').read_text(encoding='utf-8'))['instances']
    step = json.loads((out_dir / 'facts.json').read_text(encoding='utf-8'))
    revisions = {'parent': c['parent'], 'fix': c['fix']}
    rows = [{'instance': i, 'cells': {rv: _judge(case, i, step['answers'][rv], step['builds'][rv], rev, rv) for rv, rev in revisions.items()}}
            for i in inst]
    flags = {rv: sorted((r['instance']['id'], cx) for r in rows for cx, cell in r['cells'][rv].items() if short(cell) == 'violated') for rv in revisions}
    summary = {'instances': len(rows), 'parent_only': sorted(set(flags['parent']) - set(flags['fix'])),
               'fix_only': sorted(set(flags['fix']) - set(flags['parent'])), 'both': sorted(set(flags['parent']) & set(flags['fix']))}
    target.write_text(json.dumps({'case': case, 'summary': summary, 'rows': rows}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in summary.items()}))
    print('parent_only', summary['parent_only'])


def mainline(case):
    from linux_bug_analyze.kernel_facts import collect as kcollect, query
    c, out_dir = m1.CASES[case], HERE / case
    target = out_dir / 'facts_mainline_m2b.json'
    if target.exists():
        raise SystemExit('preserve')
    inst = json.loads((out_dir / 'instances_m2b.json').read_text(encoding='utf-8'))['instances']
    qs = {i['id']: cf.queries(i) for i in inst}
    macros = sorted({q['macro'] for v in qs.values() for q in v if q['kind'] == 'macro_from_arch'})
    values = sorted({q['macro'] for v in qs.values() for q in v if q['kind'] == 'macro_value'})
    functions = sorted({q['function'] for v in qs.values() for q in v if q['kind'] == 'returns_only_zero'})
    builds, answers = {}, {}
    for ctx, (arch, cross, defconfig, cfg, _extra) in c['contexts'].items():  # mainline: no old riscv flags
        spec = {'revision': MAINLINE, 'arch': arch, 'cross_compile': cross, 'defconfig': defconfig, 'config_set': cfg,
                'make_vars': m1.HOST_COMPAT, 'files': [c['built_file']], 'functions': [],
                'macros': macros or ['__lba_none__'], 'macro_values': values, 'optimized_functions': functions}
        rel = f'{case}/builds_mainline/{ctx}'
        try:
            kcollect(spec, HERE / rel)
            builds[ctx] = rel + '/bundle.json'
            bundle = json.loads((HERE / rel / 'bundle.json').read_text())
        except Exception as exc:  # recorded, not retried
            builds[ctx], bundle = {'error': repr(exc)[:300]}, None
        if bundle is not None and bundle['files'][c['built_file']].get('build_returncode'):
            bundle = None  # a failed build answers nothing
        answers[ctx] = {iid: {q['name']: dict(zip(('answered', 'value'), query(bundle, q))) if bundle is not None
                              else {'answered': False, 'value': 'no_build_for_context'} for q in iqs} for iid, iqs in qs.items()}
        for per in answers[ctx].values():
            for v in per.values():
                if not v['answered']:
                    v['reason'], v['value'] = v['value'], None
        print(ctx, builds[ctx] if isinstance(builds[ctx], dict) else 'ok', flush=True)
    target.write_text(json.dumps({'case': case, 'revision': MAINLINE, 'builds': builds, 'answers': answers}, ensure_ascii=False, indent=1) + '\n',
                      encoding='utf-8')


def label(case):
    out_dir = HERE / case
    target = out_dir / 'labels_m2b.json'
    if target.exists():
        raise SystemExit('preserve')
    res = json.loads((out_dir / 'results_m2b.json').read_text(encoding='utf-8'))
    ml = json.loads((out_dir / 'facts_mainline_m2b.json').read_text(encoding='utf-8'))
    inst = {r['instance']['id']: r['instance'] for r in res['rows']}
    labels = []
    for iid, ctx in res['summary']['both']:
        cell = _judge(case, inst[iid], {ctx: ml['answers'][ctx]}, ml['builds'], ml['revision'], 'mainline')[ctx]
        outcome = {'violated': 'persists_in_mainline', 'satisfied': 'resolved_in_mainline'}.get(short(cell), 'mainline_undecidable')
        labels.append({'id': iid, 'site': inst[iid].get('site') or '%s<=%s' % (inst[iid]['geometry'], inst[iid]['limit']),
                       'context': ctx, 'mainline': short(cell), 'label': outcome})
    counts = {k: sum(l['label'] == k for l in labels) for k in ('resolved_in_mainline', 'persists_in_mainline', 'mainline_undecidable')}
    target.write_text(json.dumps({'case': case, 'counts': counts, 'labels': labels}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(counts))
    by_site = {}
    for l in labels:
        by_site.setdefault((l['site'], l['label']), []).append(l['context'])
    for (site, lab), ctxs in sorted(by_site.items()):
        print(' ', lab, site, ctxs)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['instances', 'evaluate', 'mainline', 'label'])
    p.add_argument('--case', choices=sorted(m1.CASES), required=True)
    a = p.parse_args()
    {'instances': instances, 'evaluate': evaluate, 'mainline': mainline, 'label': label}[a.command](a.case)
