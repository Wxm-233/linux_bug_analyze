"""Stage-review re-verification: archive integrity of the three latest CPU identity rounds and
replay of every saved contract input through the unchanged common core (no new execution)."""
from pathlib import Path
from collections import Counter
import hashlib
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
CASES = HERE.parent
INNER = HERE.parents[2]
sys.path.insert(0, str(INNER))
from linux_bug_analyze.contract_protocol import evaluate_contract  # noqa: E402

CORE = INNER / 'linux_bug_analyze/contract_protocol.py'
CORE_SHA = '42d37cc48d1c87a4c4b938d67a5acaedcc685ceb207deae3f72d7dcc88da830e'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def manifest_check(root, entries):
    bad = [rel for rel, digest in entries.items() if not (root / rel.replace('\\', '/')).is_file()
           or sha(root / rel.replace('\\', '/')) != digest]
    return {'checked': len(entries), 'mismatched_or_missing': bad}


def integrity():
    out = {}
    runtime = CASES / 'cpu_identity_runtime_20261027'
    out['cpu_identity_runtime_20261027'] = manifest_check(
        runtime, {k: v['sha256'] for k, v in load(runtime / 'delivery_manifest.json')['artifacts'].items()})
    for name in ['sparc_identity_chain_20261027', 'sparc_identity_objects_20261027']:
        root = CASES / name
        entries = load(root / 'delivery_manifest.json')['files']
        # files written after the manifest by the same round's closing step are not listed; report only listed ones
        out[name] = manifest_check(root, entries)
    legacy = {}
    for name in ['cpu_identity_contract_20261021', 'cpu_mapping_transfer_20261021', 'cpu_domain_qualification_20261022',
                 'cpu_stage_propagation_20261022', 'cpu_write_effects_20261023', 'cpu_independent_admission_20261023']:
        root = CASES / name
        legacy[name] = {p.name: sha(p) for p in [root / 'README.md', root / 'results.json', root / 'program_results_v2.json',
                                                 root / 'analysis.json'] if p.is_file()}
    out['legacy_snapshot_no_prior_manifest'] = legacy
    return out


def replay(items, stored):
    rows, mismatched = Counter(), []
    doc_mismatch = []
    for item in items:
        for doc in item['ledger']['documents'].values():
            path = INNER / doc['path'].replace('\\', '/')
            if 'sha256' in doc and (not path.is_file() or sha(path) != doc['sha256']):
                doc_mismatch.append(doc['path'])
        got = evaluate_contract(item['contract'], item['ledger'], item['record'],
                                allow_synthetic=item['record'].get('basis') == 'synthetic')
        cid = item['contract']['id']
        rows[got['relation_at_observation']] += 1
        want = stored.get(cid)
        if want is None or want != got['relation_at_observation']:
            mismatched.append({'contract_id': cid, 'stored': want, 'replayed': got['relation_at_observation']})
    return {'replayed': len(items), 'decisions': dict(rows), 'mismatched': mismatched,
            'evidence_document_sha_mismatch': sorted(set(doc_mismatch))}


def object_recheck():
    root = CASES / 'sparc_identity_objects_20261027'
    spec = importlib.util.spec_from_file_location('check_objects', root / 'check_objects.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    facts = load(root / 'analysis/object_facts.json')
    stored = load(root / 'object_results.json')['decisions']
    diff = []
    for v in mod.VARIANTS:
        weight_fn = 'record_one_cpu' if v.startswith('fixed') else 'smp_fill_in_cpu_possible_map'
        got = mod.decide(v, facts[v], mod.lines(v, 'setup_arch'), mod.lines(v, weight_fn))
        for k, val in got.items():
            if stored[v][k][0] != val[0]:
                diff.append({'variant': v, 'check': k, 'stored': stored[v][k][0], 'replayed': val[0]})
    return {'variants': len(mod.VARIANTS), 'checks': 4 * len(mod.VARIANTS), 'mismatched': diff}


def main():
    if sha(CORE) != CORE_SHA:
        raise SystemExit('common core changed')
    target = HERE / 'replay_results.json'
    if target.exists():
        raise SystemExit('preserve replay_results.json')
    runtime = CASES / 'cpu_identity_runtime_20261027/analysis'
    arm_stored = {d['contract_id']: d['relation_at_observation']
                  for row in load(runtime / 'arm64_results.json')['rows'] for d in row['checks'].values()}
    sparc_old_stored = {row[k]['contract_id']: row[k]['relation_at_observation']
                        for row in load(runtime / 'sparc_replay_results.json')['rows'] for k in ['mapping', 'selection']}
    chain = CASES / 'sparc_identity_chain_20261027/analysis'
    chain_stored = {'sparc.identity_chain.' + row['context'] + '.' + k: v
                    for row in load(chain / 'results.json')['rows'] for k, v in row['decisions'].items()}
    result = {
        'core_sha256': CORE_SHA,
        'integrity': integrity(),
        'replay': {
            'arm64_runtime_normal': replay(load(runtime / 'arm64_contract_inputs.json'), arm_stored),
            'sparc_old_projection_adapter': replay(load(runtime / 'sparc_replay_inputs.json'), sparc_old_stored),
            'sparc_dual_width_projection': replay(load(chain / 'contract_inputs.json'), chain_stored),
        },
        'object_checks': object_recheck(),
        'new_executions': 0, 'new_builds': 0, 'model_calls': 0,
    }
    target.write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    summary = {k: {kk: (len(vv) if isinstance(vv, list) else vv) for kk, vv in v.items()} for k, v in result['replay'].items()}
    print(json.dumps({'integrity': {k: (len(v['mismatched_or_missing']) if 'mismatched_or_missing' in v else 'snapshot')
                                    for k, v in result['integrity'].items()},
                      'replay': summary, 'object_mismatch': len(result['object_checks']['mismatched'])}, ensure_ascii=False))


if __name__ == '__main__':
    main()
