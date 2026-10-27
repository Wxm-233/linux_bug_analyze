from pathlib import Path
import json,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=read(HERE/'materials.json');folder=Path(m['output']);r=read(folder/'receipt.json')
assert r['status']!='started','still running'
assert sha(folder/'prompt.md')==m['prompt_sha256']==r['prompt_sha256']
for d in m['old_materials']+m['new_documents']:assert sha(Path(d['path']))==d['sha256'],d['id']
events=[json.loads(x) for x in (folder/'events.jsonl').read_text(encoding='utf-8').splitlines()]
result=dict(status=r['status'],new_model_calls=1,new_kernel_runs=0,
 independent_positive=0,independent_normal=0,
 **{k:r.get(k) for k in ('started_at','elapsed_seconds','actual_models','finish_reasons','done_marker','network_eof','usage','visible_reported_tokens','usage_known','final_characters','semantic_review_allowed','error','wall_clock_limit_reached')},
 material_hashes_verified=True,old_documents=len(m['old_materials']),new_documents=len(m['new_documents']),
 http=[e for e in events if e['kind']=='http'],response_ids=sorted(set(e['id'] for e in events if 'id' in e)),
 receipt_sha256=sha(folder/'receipt.json'),platform_billing_independently_verified=False)
if r['semantic_review_allowed']:
 assert r['status']=='complete_final_received' and r['done_marker'] and r['network_eof']
 assert r['actual_models']==['Kimi-K3'] and r['finish_reasons']==['stop']
 assert r['final_characters']>0
 result['final_sha256']=sha(folder/'final.md')
(HERE/'delivery.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=True))
