"""M2 validation (registration.md): program-enumerated F1/F2 instances on the die and shmem replays.

instances (WSL): parent -dD full traces (x86_64/arm64/s390 + guard configs) -> F1/F2 instances -> instances.json
collect   (WSL): both revisions x the case's build contexts -> instance facts -> facts.json
evaluate       : registered contracts judged per context -> results.json (+ summary printed)
No model calls.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
INNER = HERE.parents[2]
TRACE_CACHE = Path('/root/.cache/linux-bug-analyze/m2-traces')
sys.path.insert(0, str(INNER))
spec_ = importlib.util.spec_from_file_location('provider_run', HERE.parent / 'e1_provider_context_20261028' / 'provider_run.py')
m1 = importlib.util.module_from_spec(spec_)
spec_.loader.exec_module(m1)
from linux_bug_analyze import check_families as cf  # noqa: E402
from linux_bug_analyze import provider_context as pc  # noqa: E402
from linux_bug_analyze.candidate_bridge import evaluate_candidate  # noqa: E402
from linux_bug_analyze.contract_envelope import document  # noqa: E402


def instances(case):
    from linux_bug_analyze.kernel_facts import collect
    c, out_dir = m1.CASES[case], HERE / case
    target = out_dir / 'instances.json'
    if target.exists():
        raise SystemExit('preserve')
    out_dir.mkdir(exist_ok=True)
    found, receipts = [], {}
    for path, text in m1.touched(case).items():
        if not path.endswith('.c'):
            continue
        configs = pc.guard_configs(text)
        traces = {}
        for ctx, (arch, cross, defconfig) in m1.TRACE_CONTEXTS.items():
            spec = {'revision': c['parent'], 'arch': arch, 'cross_compile': cross, 'defconfig': defconfig,
                    'config_set': {s: True for s in configs}, 'make_vars': m1.HOST_COMPAT, 'files': [path], 'functions': [], 'macros': '*'}
            dest = TRACE_CACHE / case / ctx
            subprocess.run(['rm', '-rf', str(dest)])
            collect(spec, dest)
            traces[ctx] = json.loads((dest / 'bundle.json').read_text())['files'][path].get('macros') or {}
            receipts[ctx] = {'bundle_sha256': hashlib.sha256((dest / 'bundle.json').read_bytes()).hexdigest(), 'config_requested': configs}
        for inst in cf.f1_instances(text, traces) + cf.f2_instances(text, traces):
            found.append(dict(inst, file=path, id='%s.%d' % (inst['family'], len(found))))
    target.write_text(json.dumps({'case': case, 'instances': found, 'trace_receipts': receipts,
                                  'registration_sha256': hashlib.sha256((HERE / 'registration.md').read_bytes()).hexdigest()},
                                 ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'case': case, 'F1': sum(i['family'] == 'F1' for i in found), 'F2': sum(i['family'] == 'F2' for i in found),
                      'sample': [i.get('site') or (i['geometry'], i['limit']) for i in found][:30]}))


def collect(case):
    from linux_bug_analyze.kernel_facts import collect as kcollect, query
    c, out_dir = m1.CASES[case], HERE / case
    target = out_dir / 'facts.json'
    if target.exists():
        raise SystemExit('preserve')
    inst = json.loads((out_dir / 'instances.json').read_text(encoding='utf-8'))['instances']
    qs = {i['id']: cf.queries(i) for i in inst}
    macros = sorted({q['macro'] for v in qs.values() for q in v if q['kind'] == 'macro_from_arch'})
    values = sorted({q['macro'] for v in qs.values() for q in v if q['kind'] == 'macro_value'})
    functions = sorted({q['function'] for v in qs.values() for q in v if q['kind'] == 'returns_only_zero'})
    revisions = {'parent': c['parent'], 'fix': c['fix']}
    builds, answers = {}, {}
    for rv, rev in revisions.items():
        builds[rv], answers[rv] = {}, {}
        for ctx, (arch, cross, defconfig, cfg, extra) in c['contexts'].items():
            spec = {'revision': rev, 'arch': arch, 'cross_compile': cross, 'defconfig': defconfig, 'config_set': cfg,
                    'make_vars': m1.HOST_COMPAT + extra.get('make_vars', []), 'files': [c['built_file']], 'functions': [],
                    'macros': macros or ['__lba_none__'], 'macro_values': values, 'optimized_functions': functions}
            if extra.get('kcflags'):
                spec['kcflags'] = extra['kcflags']
            rel = f'{case}/builds/{rv}_{ctx}'
            try:
                kcollect(spec, HERE / rel)
                builds[rv][ctx] = rel + '/bundle.json'
                bundle = json.loads((HERE / rel / 'bundle.json').read_text())
            except Exception as exc:  # recorded, not retried
                builds[rv][ctx], bundle = {'error': repr(exc)[:300]}, None
            answers[rv][ctx] = {}
            for iid, iqs in qs.items():
                answers[rv][ctx][iid] = {}
                for q in iqs:
                    ok, value = query(bundle, q) if bundle is not None else (False, 'no_build_for_context')
                    answers[rv][ctx][iid][q['name']] = {'answered': ok, 'value': value if ok else None, 'reason': None if ok else value}
            print(rv, ctx, builds[rv][ctx] if isinstance(builds[rv][ctx], dict) else bundle['files'][c['built_file']].get('build_returncode'), flush=True)
    target.write_text(json.dumps({'case': case, 'contexts': list(c['contexts']), 'builds': builds, 'answers': answers},
                                 ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def m2a_contract(instance, answers):
    """Amendment M2a (amendment_m2a.md): F2 keeps only gate functions that have an optimized record here."""
    if instance['family'] != 'F2':
        return cf.contract(instance)
    kept = [fn for fn in instance['gates'] if answers[fn + '_returns_only_zero']['answered']]
    return cf.contract(dict(instance, gates=kept))


def evaluate(case, amendment=False):
    c, out_dir = m1.CASES[case], HERE / case
    target = out_dir / ('results_m2a.json' if amendment else 'results.json')
    if target.exists():
        raise SystemExit('preserve')
    inst = json.loads((out_dir / 'instances.json').read_text(encoding='utf-8'))['instances']
    step = json.loads((out_dir / 'facts.json').read_text(encoding='utf-8'))
    revisions = {'parent': c['parent'], 'fix': c['fix']}
    short = lambda x: x.get('relation_at_observation') or x.get('status')
    rows = []
    for i in inst:
        con = cf.contract(i)
        row = {'instance': i, 'contract': con, 'cells': {}}
        for rv, rev in revisions.items():
            row['cells'][rv] = {}
            for ctx in step['contexts']:
                bpath = step['builds'][rv][ctx]
                docs = {'evidence': document(HERE / (bpath if isinstance(bpath, str) else f'{case}/facts.json'), INNER, rev)}
                facts = {k: v['value'] for k, v in step['answers'][rv][ctx][i['id']].items() if v['answered']}
                if amendment:
                    con = m2a_contract(i, step['answers'][rv][ctx][i['id']])
                row['cells'][rv][ctx] = evaluate_candidate(con, facts, context=f'm2.{case}.{i["id"]}.{rv}.{ctx}', revision=rev,
                                                           basis='compiled_object', documents=docs, reviewed=True)
        rows.append(row)
    flags = {rv: sorted((r['instance']['id'], ctx) for r in rows for ctx, cell in r['cells'][rv].items() if short(cell) == 'violated')
             for rv in revisions}
    persistent = sorted(set(flags['parent']) & set(flags['fix']))
    summary = {'instances': len(rows), 'violated_parent': len(flags['parent']), 'violated_fix': len(flags['fix']),
               'parent_only': sorted(set(flags['parent']) - set(flags['fix'])), 'fix_only': sorted(set(flags['fix']) - set(flags['parent'])),
               'persistent': len(persistent),
               'status_counts': {rv: {s: sum(short(cell) == s for r in rows for cell in r['cells'][rv].values())
                                      for s in ('satisfied', 'violated', 'facts_unavailable', 'invalid_formalization')} for rv in revisions}}
    target.write_text(json.dumps({'case': case, 'summary': summary, 'rows': rows}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    label = {r['instance']['id']: r['instance'].get('site') or '%s<=%s' % (r['instance']['geometry'], r['instance']['limit']) for r in rows}
    print(json.dumps({k: v for k, v in summary.items() if k not in ('parent_only', 'fix_only')}))
    print('parent_only', [(label[i], cx) for i, cx in summary['parent_only']])
    print('fix_only', [(label[i], cx) for i, cx in summary['fix_only']])
    print('persistent', sorted({label[i] for i, _ in persistent}))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['instances', 'collect', 'evaluate', 'evaluate_m2a'])
    p.add_argument('--case', choices=sorted(m1.CASES), required=True)
    a = p.parse_args()
    {'instances': instances, 'collect': collect, 'evaluate': evaluate,
     'evaluate_m2a': lambda case: evaluate(case, amendment=True)}[a.command](a.case)
