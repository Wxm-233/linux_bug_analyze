"""Freeze saved results and expectations without importing or rerunning a detector."""
from pathlib import Path
import hashlib,json

HERE=Path(__file__).resolve().parent
PREV=HERE.parent/'encoded_length_check_development_20261008'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(name,data):
    p=HERE/name
    assert not p.exists(),p
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

results=PREV/'runs/initial/results.json'
assert sha(results)=='19cff1d41dd6a606485f76e0f0b1389b669ddcde17eb3cc1f1b257d9d8cb22dc'
closed=PREV/'completion_manifest.json'
assert sha(closed)=='caffbd0ab193d357b17c1699bbd8994514943a7491a3415fb91e297b48d75a93'
saved=json.loads(closed.read_text(encoding='utf-8'))
for f in saved['files']:assert sha(Path(f['path']))==f['sha256'],f['path']
old=json.loads(results.read_text(encoding='utf-8'))
rows=[]
for group,key in [('probes','id'),('development','revision_label_outside_rule')]:
    for n,r in enumerate(old[group]):
        value=r['result']
        counts={s:sum(a['status']==s for a in value['assignments']) for s in ['candidate','normal','insufficient']}
        rows.append(dict(query_label_outside_generator=group+':'+r[key],group=group,index=n,
            json_pointer=f'/{group}/{n}/result',
            expected_generated=counts['candidate']+counts['normal'],
            expected_refused_assignments=counts['insufficient'],
            expected_query_disposition='insufficient' if value['execution_status']!='ok' else ('no_eligible_assignment' if not value['assignments'] else 'records'),
            expected_component_values=[ [c['value'] for c in a['length_components']] for a in value['assignments'] if a['status'] in ['candidate','normal']],
            expected_upstream_statuses=[a['status'] for a in value['assignments']]))
assert len(rows)==14
put('inputs_pre.json',dict(saved_result_path=str(results),saved_result_sha256=sha(results),
    previous_completion_path=str(closed),previous_completion_sha256=sha(closed),
    query_count=14,queries=rows,labels_enter_generator=False,old_detector_reexecution=False))
paths=[HERE/'protocol_pre.md',HERE/'prepare_inputs.py',HERE/'inputs_pre.json',results,closed,PREV/'verify_stage.py']
put('freeze_inputs_pre.json',dict(files=[dict(path=str(p),sha256=sha(p)) for p in paths],
    purpose='saved-output-only input lock; no detector/model/Git',previous_stage_files_checked=len(saved['files'])))
print(json.dumps(dict(saved_queries=14,previous_files_checked=len(saved['files']),
    freeze_inputs_sha256=sha(HERE/'freeze_inputs_pre.json'),old_detector_reexecution=False),ensure_ascii=False))
