"""Release only the two registered repairs after parent prediction is terminal."""
from pathlib import Path
import hashlib
import json
import subprocess

stage=Path(__file__).resolve().parent
inner=stage.parents[2]
outer=inner.parent
protocol=json.loads((stage/'protocol_pre.json').read_text(encoding='utf-8'))
receipt=json.loads((outer/'模型调用测试/2026-10-17/core_parent_D/receipt.json').read_text(encoding='utf-8'))
assert receipt.get('status') in ['complete_final_received','response_refused','no_complete_final'], 'Parent model still running'
assert json.loads((stage/'model_adequacy.json').read_text(encoding='utf-8'))['C']['decision']=='skip_project_model_in_this_round'
out=stage/'repair_material.json'
if out.exists():
    raise SystemExit('Repairs already released; preserve first record.')
records=[]
for case in protocol['cases']:
    proc=subprocess.run(['git','-C',protocol['collection']['git'],'show','--format=fuller','--no-ext-diff','--no-renames',case['hash']],capture_output=True,timeout=30)
    record={'case':case['id'],'hash':case['hash'],'parent':case['parent'],'exit_code':proc.returncode}
    if proc.returncode:
        record['error']=proc.stderr.decode('utf-8',errors='replace')[:1000]
    else:
        target=stage/('repair_'+case['id']+'.txt')
        target.write_bytes(proc.stdout)
        record.update(saved_path=target.name,bytes=len(proc.stdout),sha256=hashlib.sha256(proc.stdout).hexdigest())
    records.append(record)
out.write_text(json.dumps({'parent_receipt_status_before_release':receipt['status'],'parent_visible_tokens':receipt.get('visible_reported_tokens'),'repairs':records,'no_retry':True},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'parent_status':receipt['status'],'repair_count':len(records),'bytes':[r.get('bytes') for r in records]},ensure_ascii=False))
