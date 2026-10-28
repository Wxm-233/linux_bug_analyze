"""riscv supplement to the die replay: rebuild riscv for parent and fix with the binutils>=2.38 ISA flags
(same effect as upstream 6df2a016c0c8, no source change), answer the existing vocabulary, and judge it with
the existing formalization and researcher review. Existing replay results are not touched.

prepare  (WSL): two builds -> answers for the riscv context -> riscv_facts.json
evaluate      : riscv_results.json (same layers as replay_results.json)
"""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
ROUND = HERE.parent
INNER = HERE.parents[3]
sys.path.insert(0, str(INNER))
spec_ = importlib.util.spec_from_file_location('replay_run', ROUND / 'replay_run.py')
replay = importlib.util.module_from_spec(spec_)
spec_.loader.exec_module(replay)
from linux_bug_analyze.candidate_bridge import evaluate_candidate, parse_formalizations  # noqa: E402
from linux_bug_analyze.contract_envelope import document  # noqa: E402

MARCH = '-march=rv64imafdc_zicsr_zifencei'  # defconfig ISA plus the extensions binutils>=2.38 requires spelled out
CONTEXT = 'riscv'


def prepare():
    from linux_bug_analyze.kernel_facts import collect, query
    target = HERE / 'riscv_facts.json'
    if target.exists():
        raise SystemExit('preserve')
    step = json.loads((ROUND / 'replay_facts.json').read_text(encoding='utf-8'))
    arch, cross, defconfig, cfg = replay.CONTEXTS[CONTEXT]
    builds, answers = {}, {}
    for rv, rev in replay.REVISIONS.items():
        spec = {'revision': rev, 'arch': arch, 'cross_compile': cross, 'defconfig': defconfig, 'config_set': cfg,
                'make_vars': replay.HOST_COMPAT + ['KAFLAGS=' + MARCH], 'kcflags': MARCH,
                'files': [step['built_file']], 'functions': [], 'macros': step['needs']['macros']}
        rel = f'builds/{rv}_{CONTEXT}'
        try:
            collect(spec, HERE / rel)
            builds[rv] = rel + '/bundle.json'
        except Exception as exc:  # recorded, not retried
            builds[rv] = {'error': repr(exc)[:300]}
        bundle = json.loads((HERE / builds[rv]).read_text()) if isinstance(builds[rv], str) else None
        answers[rv] = {}
        for b in step['bridged']:
            i = str(b['candidate'])
            answers[rv][i] = {}
            for q in b['queries']:
                ok, value = query(bundle, q) if bundle is not None else (False, 'no_build_for_context')
                answers[rv][i][q['name']] = {'answered': ok, 'value': value if ok else None, 'reason': None if ok else value}
    target.write_text(json.dumps({'context': CONTEXT, 'march': MARCH, 'builds': builds, 'answers': answers},
                                 ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    status = {rv: (json.loads((HERE / v).read_text())['files'][step['built_file']].get('build_returncode') if isinstance(v, str) else v)
              for rv, v in builds.items()}
    print(json.dumps({'builds': status}))


def evaluate():
    target = HERE / 'riscv_results.json'
    if target.exists():
        raise SystemExit('preserve')
    step = json.loads((HERE / 'riscv_facts.json').read_text(encoding='utf-8'))
    formal = parse_formalizations((replay.CALLS / 'die_replay_formalize' / 'final.md').read_text(encoding='utf-8'))
    review = json.loads((ROUND / 'researcher_review.json').read_text(encoding='utf-8'))
    out = {'context': CONTEXT, 'candidates': []}
    for i in sorted(step['answers']['parent'], key=int):
        f = formal.get(int(i), {'expressible': False, 'reason': 'missing from model output'})
        verdict = review.get(i) or {}
        row = {'candidate': int(i), 'per_revision': {}}
        for rv, rev in replay.REVISIONS.items():
            bpath = step['builds'][rv]
            docs = {'evidence': document(HERE / (bpath if isinstance(bpath, str) else 'riscv_facts.json'), INNER, rev)}
            facts = {k: v['value'] for k, v in step['answers'][rv][i].items() if v['answered']}
            kw = dict(context=f'die_replay.c{i}.{rv}.{CONTEXT}', revision=rev, basis='compiled_object', documents=docs)
            cell = {'unreviewed': evaluate_candidate(f, facts, reviewed=False, **kw)}
            if verdict.get('faithful'):
                cell['reviewed'] = evaluate_candidate(f, facts, reviewed=True, **kw)
            for layer in ('hindsight', 'naive_hindsight'):
                if layer + '_formalization' in verdict:
                    cell[layer] = evaluate_candidate(verdict[layer + '_formalization'], facts, reviewed=True, **kw)
            row['per_revision'][rv] = cell
        out['candidates'].append(row)
    target.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    short = lambda c: c.get('relation_at_observation') or c.get('status')
    for r in out['candidates']:
        print(r['candidate'], {rv: {layer: short(c) for layer, c in cells.items()} for rv, cells in r['per_revision'].items()})


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['prepare', 'evaluate'])
    {'prepare': prepare, 'evaluate': evaluate}[p.parse_args().command]()
