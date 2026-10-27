"""Validate the authorized retry without reading response bodies on failure."""
from pathlib import Path
import json,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=read(HERE/'retry_authorization.json');old=ROOT/a['original_attempt'];new=ROOT/a['new_attempt']
assert sha(old/'receipt.json')==a['old_receipt_sha256']
assert sha(old/'prompt.md')==sha(new/'prompt.md')==a['prompt_sha256']
r=read(new/'receipt.json');p=read(new/'call_plan.json')
assert p['prompt_sha256']==a['prompt_sha256']
assert p['model']=='AWS-Claude-Opus-5.5' and p['client_version']=='2.1.301'
assert p['runner_retry_count']==p['cli_retries_requested']==0
assert r['status']!='started','call still running'
complete=r['status']=='complete_final_received' and not r['refusal_observed']
if complete:
 assert r['exit_code']==0 and r['final_text_transport_complete']
 assert set(r['stop_reasons'])<={'end_turn','stop_sequence'}
 assert (new/'final.md').is_file() and (new/'final.md').stat().st_size>0
result=dict(status=r['status'],prompt_unchanged=True,original_failure_preserved=True,
 allowed_semantic_review=complete,model_calls=1,new_kernel_runs=0,per_call_allowance=1000000,
 historical_usage_deducted=False,aggregate_remaining_budget=None,
 receipt_sha256=sha(new/'receipt.json'),receipt_path=str((new/'receipt.json').relative_to(ROOT)),
 **{k:r.get(k) for k in ('elapsed_seconds','exit_code','stop_reasons','visible_reported_tokens','conservative_accounted_tokens','usage_known','final_characters')})
(HERE/'delivery.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=True))
