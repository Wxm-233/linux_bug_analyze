"""Final artifact/reference audit; does not repeat experiments or core tests."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
INNER = HERE.parents[2]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path):
    return json.loads(path.read_bytes())

def need(value, reason):
    if not value:
        raise ValueError(reason)

def main():
    out = HERE / 'delivery_manifest.json'
    need(not out.exists(), 'preserve_delivery_audit')
    active = HERE / 'analysis_attempt2'
    index = load(active / 'input_index.json')
    for name,digest in index.items():
        need(sha(HERE / name)==digest,'input_digest_changed:'+name)
    contracts = load(active / 'contract_inputs.json')['rows'] + load(HERE / 'normal_policy.json')['inputs']
    references = set()
    for item in contracts:
        for document in item['ledger']['documents'].values():
            path = INNER / document['path']
            need(path.resolve().is_relative_to(INNER.resolve()),'reference_outside_project')
            need(sha(path)==document['sha256'],'reviewed_reference_changed:'+document['path'])
            references.add(document['path'])
    manifest = load(HERE / 'policy_sources/manifest.json')
    for row in manifest:
        path = HERE / row['archived_path']; raw=path.read_bytes()
        need(sha(path)==row['sha256'],'policy_source_digest_changed')
        need(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==row['git_blob'],'policy_source_blob_mismatch')
    result, normal = load(active/'results.json'), load(HERE/'normal_policy.json')
    need(result['relation_counts']=={'satisfied':3,'violated':1},'unexpected_source_result')
    need(all(row['effective_TU_reconstruction']['whole_path']=='insufficient' and row['historical_runtime_origin']=='unknown' for row in result['rows']),'scope_promoted')
    controls = load(active/'controls.json')['controls'] + normal['controls']
    need(len(controls)==16 and all(row.get('actual',row.get('result'))['relation_at_observation']=='insufficient' for row in controls),'control_rejection_missing')
    artifacts = {}
    for path in sorted(HERE.rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts or path.name.startswith('before_') or path.name in ['plan_before.md']:
            continue
        artifacts[str(path.relative_to(HERE))] = {'sha256':sha(path),'bytes':path.stat().st_size}
    delivery = {'date':'2026-10-27','status':'bounded_source_policy_stage_complete_interface_still_in_progress',
        'authoritative_analysis':'analysis_attempt2/results.json','normal_policy_results':'normal_policy.json',
        'initial_analysis_preserved':'analysis_attempt1/', 'new_preprocessing':4,'new_compilations':0,'new_builds':0,'new_boots':0,'new_model_calls':0,
        'final_source_context_evaluations':8,'final_constructed_control_evaluations':16,'final_core_calls':24,
        'final_old_archive_core_replays':10,'all_local_core_calls_including_initial_pass':59,
        'historical_runtime_origin_upgrades':0,'new_defects':0,'formal_independent_positive_normal':[0,0],
        'core_sha256':result['core_sha256'],'reviewed_reference_documents':len(references),
        'manual_inputs':['versioned normative/default policy','finite macro body semantics','attribute groups and object roles','configuration and evidence support domain'],
        'open':['historical compilation/link-to-image source bridge','actual publication and first content-consumption identity','physical values and lifecycle','independent evaluation','automatic requirement inference'],
        'next':'continue this CPU export mechanism: audit source/object/image/publication binding before deciding minimal new runtime',
        'artifacts':artifacts}
    out.write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:value for key,value in delivery.items() if key!='artifacts'},ensure_ascii=False))

if __name__=='__main__':
    main()
