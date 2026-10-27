from pathlib import Path
import copy,hashlib,json,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'linux_bug_analyze'))
from linux_bug_analyze.model_candidate import parse_model_candidate
from linux_bug_analyze.candidate_parts import inspect_parts
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 p=HERE/n;assert not p.exists()
 p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for p,h in read(HERE/'frozen_inputs.json').items():assert sha(ROOT/p)==h,p
out=ROOT/'模型调用测试/2026-10-25/btrfs_typed_model'
receipt=read(out/'receipt.json');assert receipt['status']=='complete_final_received'
try:
 parsed=parse_model_candidate((out/'final.md').read_text(encoding='utf-8'),read(HERE.parent/'btrfs_model_candidate_20261025/documents.json'))
except (ValueError,KeyError,TypeError) as e:
 save('results.json',dict(status='ingestion_rejected',reason=str(e),manual_repair=False));raise
save('ingested.json',parsed)
candidate=parsed['candidate'];before=copy.deepcopy(candidate)
rows=[]
for archived in read(HERE.parent/'btrfs_typed_parts_20261025/results.json')['rows']:
 facts=archived['facts'];assert 'disk_at_deadline' not in facts
 diagnostics=inspect_parts(candidate,read(HERE/'role_registry.json'),facts,context_id=archived['context_id'])
 rows.append(dict(context_id=archived['context_id'],facts=facts,diagnostics=diagnostics))
assert candidate==before
result=dict(status='new_unedited_candidate_inspected',candidate_sha256=sha(out/'final.md'),candidate_count=1,candidate_unchanged=True,rows=rows,model_calls=1,new_boots=0,independent_positive=0,independent_normal=0,formal_core_executions=0)
save('results.json',result)
print(json.dumps(dict(status=result['status'],rows=[dict(binding=r['diagnostics']['binding_status'],summary=r['diagnostics']['summary']) for r in rows])))
