"""Record material integrity and refusal; never load model response bodies."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
materials=json.loads((HERE/'materials.json').read_text(encoding='utf-8'))
for doc in materials['documents']:
    p=Path(doc['path']);assert sha(p)==doc['sha256']
    lines=p.read_text(encoding='utf-8').splitlines()
    for lo,hi in doc['spans']:assert 1<=lo<=hi<=len(lines)
folder=Path(materials['output'])
assert sha(folder/'prompt.md')==materials['prompt_sha256']
plan=json.loads((folder/'call_plan.json').read_text(encoding='utf-8'))
assert plan['prompt_sha256']==materials['prompt_sha256']
receipt=json.loads((folder/'receipt.json').read_text(encoding='utf-8'))
assert receipt['status']=='response_refused' and receipt['refusal_observed']
raw=ROOT/'linux_bug_analyze/analysis_out/btrfs-consumer-observation-20261024'
old=json.loads((raw/'manifest.json').read_text(encoding='utf-8'))[0]
assert old['mode']=='parent'
assert sha(raw/'parent/super.i')==old['artifacts']['super.i']
assert sha(raw/'parent/super.observed.c')==old['source_after_sha256']
result=dict(status='response_refused_no_semantic_adoption',model_body_read=False,automatic_retry=False,
    material_integrity='verified',documents=len(materials['documents']),
    prior_conservative_accounting=materials['prior_accounting'],
    cumulative_conservative_accounting=materials['prior_accounting']+receipt['conservative_accounted_tokens'],
    receipt_path=str((folder/'receipt.json').relative_to(ROOT)),receipt_sha256=sha(folder/'receipt.json'),
    **{k:receipt.get(k) for k in ('elapsed_seconds','exit_code','actual_models','stop_reasons','visible_reported_tokens','conservative_accounted_tokens','usage_known','final_characters')},
    new_kernel_runs=0,adopted_requirements=0,deadline='insufficient',whole_path='insufficient')
save(HERE/'results.json',result)
print(json.dumps(result,ensure_ascii=True))
