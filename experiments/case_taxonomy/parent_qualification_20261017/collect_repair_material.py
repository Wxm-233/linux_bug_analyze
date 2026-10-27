"""Read the two child descriptions/diffs only after parent outputs are saved."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess

stage = Path(__file__).resolve().parent
outer = stage.parents[2].parent
protocol = json.loads((stage / 'protocol_pre.json').read_text(encoding='utf-8'))
if (stage / 'repair_material.json').exists():
    raise SystemExit('Repair material already collected; preserve initial sequence.')
components = stage / 'parent_component_results.json'
assert components.is_file()
parents = []
for case in protocol['candidates']:
    folder = outer / '模型调用测试/2026-10-17' / ('parent_qualification_' + case['id'])
    receipt = folder / 'receipt.json'
    record = json.loads(receipt.read_text(encoding='utf-8'))
    if record.get('status') == 'started':
        raise RuntimeError('Parent model not finished')
    parents.append({'candidate':case['id'],'model_delivery':record.get('status'),'receipt_sha256':hashlib.sha256(receipt.read_bytes()).hexdigest(),'final_sha256':hashlib.sha256((folder/'final.md').read_bytes()).hexdigest() if (folder/'final.md').is_file() else None})
timeline = {'parent_results_saved_before_oracle':True,'parent_models':parents,'component_result_sha256':hashlib.sha256(components.read_bytes()).hexdigest(),'oracle_collection_started_at':datetime.now(timezone.utc).isoformat()}
(stage/'parent_prediction_record.json').write_text(json.dumps(timeline,ensure_ascii=False,indent=2),encoding='utf-8')
materials=[]
for case in protocol['candidates']:
    base=['git','-C','/root/repos/linux']
    desc=subprocess.run(base+['show','-s','--format=fuller',case['commit']],capture_output=True,check=True).stdout.decode('utf-8')
    paths=[p for p in case['parent_paths'] if p.endswith(('.c','.h'))]
    diff=subprocess.run(base+['diff','--no-ext-diff','--no-textconv',case['parent'],case['commit'],'--',*paths],capture_output=True,check=True).stdout.decode('utf-8')
    materials.append({'candidate':case['id'],'parent':case['parent'],'commit':case['commit'],'description':desc,'diff':diff,'diff_paths':paths})
(stage/'repair_material.json').write_text(json.dumps({'materials':materials,'scope':'post-parent qualification oracle, not supplied to parent models/components'},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'candidates':[m['candidate'] for m in materials],'parent_predictions_preceded_oracle':True,'repair_diff_bytes':{m['candidate']:len(m['diff'].encode()) for m in materials}},ensure_ascii=False))
