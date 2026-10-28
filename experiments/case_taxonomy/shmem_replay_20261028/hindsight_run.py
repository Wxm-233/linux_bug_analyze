"""Researcher-specified hindsight facts and contracts for the shmem replay (borrow the fix's semantics; they test
whether value/optimized-body facts and the core can separate parent and fix, not the E1 pipeline).

collect  (WSL): per revision x context, value probes of HPAGE_PMD_ORDER/MAX_PAGECACHE_ORDER and the optimized body
                of shmem_is_huge -> hindsight_facts.json
evaluate      : hindsight / naive-hindsight contracts and synthetic controls -> hindsight_results.json, controls.json
"""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
INNER = HERE.parents[2]
sys.path.insert(0, str(INNER))
spec_ = importlib.util.spec_from_file_location('replay_run', HERE / 'replay_run.py')
replay = importlib.util.module_from_spec(spec_)
spec_.loader.exec_module(replay)
from linux_bug_analyze.candidate_bridge import evaluate_candidate  # noqa: E402
from linux_bug_analyze.contract_envelope import document  # noqa: E402

MACROS = ['HPAGE_PMD_ORDER', 'MAX_PAGECACHE_ORDER']
QUERIES = [{'name': 'value_HPAGE_PMD_ORDER', 'kind': 'macro_value', 'macro': 'HPAGE_PMD_ORDER'},
           {'name': 'value_MAX_PAGECACHE_ORDER', 'kind': 'macro_value', 'macro': 'MAX_PAGECACHE_ORDER'},
           {'name': 'shmem_is_huge_returns_only_zero', 'kind': 'returns_only_zero', 'function': 'shmem_is_huge'},
           {'name': 'config_transparent_hugepage', 'kind': 'config', 'option': 'CONFIG_TRANSPARENT_HUGEPAGE', 'absent_is_false': True}]
BASE = {'expressible': True, 'strength': 'necessary_only', 'config_symbols': ['config_transparent_hugepage'],
        'scope': {'symbol': 'config_transparent_hugepage'}}
LE = {'op': 'le', 'args': [{'symbol': 'value_HPAGE_PMD_ORDER'}, {'symbol': 'value_MAX_PAGECACHE_ORDER'}]}
CONTRACTS = {
    'hindsight': dict(BASE, reason='hindsight: with THP, shmem may hand out PMD-order page cache only if that order fits the page-cache limit '
                                   '(shmem_is_huge folded to false, or HPAGE_PMD_ORDER <= MAX_PAGECACHE_ORDER)',
                      relation={'op': 'or', 'args': [{'symbol': 'shmem_is_huge_returns_only_zero'}, LE]}),
    'naive_hindsight': dict(BASE, reason='hindsight contrast: the macro relation alone, ignoring what the consumer does', relation=LE)}


def collect():
    from linux_bug_analyze.kernel_facts import collect as kcollect, query
    target = HERE / 'hindsight_facts.json'
    if target.exists():
        raise SystemExit('preserve')
    builds, answers = {}, {}
    for rv, rev in replay.REVISIONS.items():
        builds[rv], answers[rv] = {}, {}
        for ctx, (arch, cross, defconfig, cfg) in replay.CONTEXTS.items():
            spec = {'revision': rev, 'arch': arch, 'cross_compile': cross, 'defconfig': defconfig, 'config_set': cfg,
                    'make_vars': replay.HOST_COMPAT, 'files': [replay.BUILT_FILE], 'functions': [], 'macros': MACROS,
                    'macro_values': MACROS, 'optimized_functions': ['shmem_is_huge']}
            rel = f'hindsight/builds/{rv}_{ctx}'
            try:
                kcollect(spec, HERE / rel)
                builds[rv][ctx] = rel + '/bundle.json'
                bundle = json.loads((HERE / rel / 'bundle.json').read_text())
            except Exception as exc:  # recorded, not retried
                builds[rv][ctx], bundle = {'error': repr(exc)[:300]}, None
            answers[rv][ctx] = {}
            for q in QUERIES:
                ok, value = query(bundle, q) if bundle is not None else (False, 'no_build_for_context')
                answers[rv][ctx][q['name']] = {'answered': ok, 'value': value if ok else None, 'reason': None if ok else value}
    target.write_text(json.dumps({'queries': QUERIES, 'builds': builds, 'answers': answers}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    for rv in answers:
        for ctx, a in answers[rv].items():
            print(rv, ctx, {k: (v['value'] if v['answered'] else v['reason']) for k, v in a.items()})


def evaluate():
    target = HERE / 'hindsight_results.json'
    if target.exists():
        raise SystemExit('preserve')
    step = json.loads((HERE / 'hindsight_facts.json').read_text(encoding='utf-8'))
    short = lambda c: c.get('relation_at_observation') or c.get('status')
    docs = lambda rv, ctx: {'evidence': document(HERE / (step['builds'][rv][ctx] if isinstance(step['builds'][rv][ctx], str) else 'hindsight_facts.json'),
                                                 INNER, replay.REVISIONS[rv])}
    facts = lambda rv, ctx: {k: v['value'] for k, v in step['answers'][rv][ctx].items() if v['answered']}
    out = {'contracts': CONTRACTS, 'cells': {}}
    for layer, contract in CONTRACTS.items():
        out['cells'][layer] = {rv: {ctx: evaluate_candidate(contract, facts(rv, ctx), context=f'shmem_hindsight.{layer}.{rv}.{ctx}',
                                                            revision=replay.REVISIONS[rv], basis='compiled_object', documents=docs(rv, ctx), reviewed=True)
                                    for ctx in replay.CONTEXTS} for rv in replay.REVISIONS}
        print(layer, json.dumps({rv: {c: short(v) for c, v in per.items()} for rv, per in out['cells'][layer].items()}))
    target.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    rows = []
    for name, rv, ctx, patch, expect in [
            ('fix_arm64_64k_guard_removed', 'fix', 'arm64_64k', {'shmem_is_huge_returns_only_zero': False}, 'violated'),
            ('parent_x86_order_above_limit', 'parent', 'x86_64', {'value_HPAGE_PMD_ORDER': 10}, 'violated'),
            ('parent_arm64_64k_limit_raised', 'parent', 'arm64_64k', {'value_MAX_PAGECACHE_ORDER': 13}, 'satisfied'),
            ('parent_arm64_64k_unchanged', 'parent', 'arm64_64k', {}, 'violated'),
            ('fix_arm64_64k_unchanged', 'fix', 'arm64_64k', {}, 'satisfied'),
            # evaluate_candidate reports missing relation facts before applying the scope, so a THP-less context with
            # unanswerable values is facts_unavailable rather than not_applicable (recorded limitation).
            ('parent_alpha_unchanged', 'parent', 'alpha', {}, 'facts_unavailable')]:
        r = evaluate_candidate(CONTRACTS['hindsight'], dict(facts(rv, ctx), **patch), context=f'control.{name}', revision=replay.REVISIONS[rv],
                               basis='compiled_object', documents=docs(rv, ctx), reviewed=True, synthetic=True)
        rows.append({'control': name, 'revision': rv, 'context': ctx, 'patch': patch, 'expected': expect, 'got': short(r), 'as_expected': short(r) == expect})
    (HERE / 'controls.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    for x in rows:
        print(x['control'], x['got'], x['as_expected'])


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['collect', 'evaluate'])
    {'collect': collect, 'evaluate': evaluate}[p.parse_args().command]()
