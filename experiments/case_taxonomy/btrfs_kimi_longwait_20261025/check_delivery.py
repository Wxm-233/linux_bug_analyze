from pathlib import Path
import json,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
prep=read(HERE/'prepared.json');folder=ROOT/prep['current_attempt'];r=read(folder/'receipt.json')
assert r['status']!='started','still running'
old=ROOT/'模型调用测试/2026-10-25/btrfs_kimi_k3_newkey'
assert sha(old/'receipt.json')==prep['old_receipt_sha256']
assert r['payload_sha256']==read(old/'receipt.json')['payload_sha256']
assert sha(folder/'prompt.md')==prep['prompt_sha256']
events=[json.loads(x) for x in (folder/'events.jsonl').read_text(encoding='utf-8').splitlines()]
result=dict(status=r['status'],new_model_calls=1,new_kernel_runs=0,
 independent_positive=0,independent_normal=0,
 **{k:r.get(k) for k in ('started_at','elapsed_seconds','actual_models','finish_reasons','done_marker','network_eof','usage','visible_reported_tokens','usage_known','final_characters','semantic_review_allowed','error','wall_clock_limit_reached')},
 request_payload_identical=True,old_partial_attempt_preserved=True,
 event_count=len(events),http=[e for e in events if e['kind']=='http'],
 response_ids=sorted(set(e['id'] for e in events if 'id' in e)),
 first_content_seconds=next((e['elapsed_seconds'] for e in events if any(c.get('content') for c in e.get('choices',[]))),None),
 partial_characters=len((folder/'partial_text.md').read_text(encoding='utf-8')),
 receipt_sha256=sha(folder/'receipt.json'),platform_billing_independently_verified=False)
if r['semantic_review_allowed']:
 assert r['status']=='complete_final_received' and r['done_marker'] and r['network_eof']
 assert r['actual_models']==['Kimi-K3'] and r['finish_reasons']==['stop']
 assert r['final_characters']>0
 result['final_sha256']=sha(folder/'final.md')
(HERE/'delivery.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=True))
