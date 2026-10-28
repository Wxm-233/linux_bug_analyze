"""M2c (registration_m2c.md): F1 'natively provided' = final definition is not a guarded fallback.

instances (WSL): fallback-annotate the M2 parent traces, enumerate F1b(M2c)+F2b -> <case>/instances_m2c.json
evaluate  (WSL): fallback-annotate the M2 fact bundles (and the M2b mainline bundles) in memory, judge parent/fix,
                 label observations reported in both on mainline -> <case>/results_m2c.json, <case>/labels_m2c.json
Existing bundles are read, never rewritten. No new builds, no model calls.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
spec_ = importlib.util.spec_from_file_location('m2b_run', HERE / 'm2b_run.py')
m2b = importlib.util.module_from_spec(spec_)
spec_.loader.exec_module(m2b)
m2, cf, m1, INNER = m2b.m2, m2b.cf, m2b.m1, m2b.INNER
from linux_bug_analyze.candidate_bridge import evaluate_candidate  # noqa: E402
from linux_bug_analyze.contract_envelope import document  # noqa: E402
from linux_bug_analyze.kernel_facts import CACHE, annotate_fallbacks, query  # noqa: E402

short = m2b.short


def _annotated(bundle):
    rev = bundle['revision']
    arch = bundle['spec']['arch']
    roots = [CACHE / rev / 'linux', CACHE / rev / ('build-%s-%s' % (arch, bundle['build_profile']))]
    for entry in bundle['files'].values():
        annotate_fallbacks(entry.get('macros') or {}, roots)
    return bundle


def instances(case):
    out_dir = HERE / case
    target = out_dir / 'instances_m2c.json'
    if target.exists():
        raise SystemExit('preserve')
    m2_inst = json.loads((out_dir / 'instances.json').read_text(encoding='utf-8'))['instances']
    ids = {m2b.key(i): i['id'] for i in m2_inst}
    found, notes = [], {}
    for path, text in m1.touched(case).items():
        if not path.endswith('.c'):
            continue
        traces = {}
        for ctx in m1.TRACE_CONTEXTS:
            bundle = _annotated(json.loads((m2.TRACE_CACHE / case / ctx / 'bundle.json').read_text()))
            traces[ctx] = bundle['files'][path].get('macros') or {}
        for inst in cf.f1_instances(text, traces, direct=False, provided='fallback') + cf.f2_instances(text, traces, limit_contains_g=True):
            k = m2b.key(inst)
            found.append(dict(inst, file=path, id=ids.get(k, 'M2c.new.%d' % len(found)), in_m2=k in ids))
        notes[path] = {m: {ctx: {f: traces[ctx].get(m, {}).get(f) for f in ('origin', 'line', 'fallback')} for ctx in traces}
                       for i in found if i['family'] == 'F1' for m in i['macros']}
    target.write_text(json.dumps({'case': case, 'instances': found, 'fallback_notes': notes}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'case': case, 'kept': len(found), 'new_vs_m2': sum(not i['in_m2'] for i in found),
                      'sites': [i.get('site') or '%s<=%s' % (i['geometry'], i['limit']) for i in found]}))


def _judge(inst, bundle, bpath, rev, tag, case):
    answers = {q['name']: dict(zip(('answered', 'value'), query(bundle, q))) for q in cf.queries(inst)}
    facts = {k: v['value'] for k, v in answers.items() if v['answered']}
    docs = {'evidence': document(HERE / bpath, INNER, rev)}
    return evaluate_candidate(m2.m2a_contract(inst, answers), facts, context=f'm2c.{case}.{inst["id"]}.{tag}', revision=rev,
                              basis='compiled_object', documents=docs, reviewed=True), answers


def evaluate(case):
    c, out_dir = m1.CASES[case], HERE / case
    target = out_dir / 'results_m2c.json'
    if target.exists():
        raise SystemExit('preserve')
    inst = json.loads((out_dir / 'instances_m2c.json').read_text(encoding='utf-8'))['instances']
    step = json.loads((out_dir / 'facts.json').read_text(encoding='utf-8'))
    revisions = {'parent': c['parent'], 'fix': c['fix']}
    bundles = {rv: {ctx: _annotated(json.loads((HERE / step['builds'][rv][ctx]).read_text())) for ctx in step['contexts']} for rv in revisions}
    rows = []
    for i in inst:
        row = {'instance': i, 'cells': {}, 'answers': {}}
        for rv, rev in revisions.items():
            row['cells'][rv], row['answers'][rv] = {}, {}
            for ctx in step['contexts']:
                cell, ans = _judge(i, bundles[rv][ctx], step['builds'][rv][ctx], rev, f'{rv}.{ctx}', case)
                row['cells'][rv][ctx], row['answers'][rv][ctx] = cell, ans
        rows.append(row)
    flags = {rv: sorted((r['instance']['id'], cx) for r in rows for cx, cell in r['cells'][rv].items() if short(cell) == 'violated') for rv in revisions}
    both = sorted(set(flags['parent']) & set(flags['fix']))
    labels = []
    ml_path = out_dir / 'facts_mainline_m2b.json'
    ml = json.loads(ml_path.read_text(encoding='utf-8')) if ml_path.exists() else None
    by_id = {r['instance']['id']: r['instance'] for r in rows}
    for iid, ctx in both:
        if ml is None or not isinstance(ml['builds'].get(ctx), str):
            labels.append({'id': iid, 'context': ctx, 'label': 'mainline_undecidable', 'reason': 'no mainline bundle'})
            continue
        bundle = _annotated(json.loads((HERE / ml['builds'][ctx]).read_text()))
        cell, _ = _judge(by_id[iid], bundle, ml['builds'][ctx], ml['revision'], f'mainline.{ctx}', case)
        labels.append({'id': iid, 'site': by_id[iid].get('site'), 'context': ctx, 'mainline': short(cell),
                       'label': {'violated': 'persists_in_mainline', 'satisfied': 'resolved_in_mainline'}.get(short(cell), 'mainline_undecidable')})
    summary = {'instances': len(rows), 'parent_only': sorted(set(flags['parent']) - set(flags['fix'])),
               'fix_only': sorted(set(flags['fix']) - set(flags['parent'])), 'both': both,
               'labels': {k: sum(l['label'] == k for l in labels) for k in ('resolved_in_mainline', 'persists_in_mainline', 'mainline_undecidable')},
               'status_counts': {rv: {s: sum(short(cell) == s for r in rows for cell in r['cells'][rv].values())
                                      for s in ('satisfied', 'violated', 'facts_unavailable', 'invalid_formalization')} for rv in revisions}}
    target.write_text(json.dumps({'case': case, 'summary': summary, 'rows': rows}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    (out_dir / 'labels_m2c.json').write_text(json.dumps({'case': case, 'labels': labels}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    label_of = {i['id']: i.get('site') or '%s<=%s' % (i['geometry'], i['limit']) for i in inst}
    print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in summary.items()}))
    print('parent_only', [(label_of[i], cx) for i, cx in summary['parent_only']])
    print('both', [(label_of[l['id']], l['context'], l['label']) for l in labels])


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['instances', 'evaluate'])
    p.add_argument('--case', choices=sorted(m1.CASES), required=True)
    a = p.parse_args()
    {'instances': instances, 'evaluate': evaluate}[a.command](a.case)
