"""Positive integration control: preserve real archived B diagnostics."""
from pathlib import Path
import hashlib,json,copy,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'linux_bug_analyze'))
from linux_bug_analyze.contract_archive import load_verified_archive
from linux_bug_analyze.contract_protocol import evaluate_contract
from linux_bug_analyze.interface_intent import evaluate_with_intent
pins=json.loads((HERE/'frozen_inputs.json').read_text(encoding='utf-8'))
for p,h in pins.items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
relative='linux_bug_analyze/experiments/case_taxonomy/btrfs_layered_contract_20261024/registered_inputs.json'
bundles,_=load_verified_archive(ROOT/relative,pins[relative]);rows=[]
for b in bundles:
 if b['contract']['id']!='btrfs.layered.B':continue
 intent=dict(schema='interface_intent_v1',interface_id='btrfs.cross_time_diagnostic',
   deadline_event=b['record']['deadline_event'],contract=copy.deepcopy(b['contract']))
 candidate=dict(interface_id=intent['interface_id'],deadline_event=intent['deadline_event'],
   contract=copy.deepcopy(b['contract']),symbol_bindings={s:s for s in b['contract']['symbols']})
 guarded=evaluate_with_intent(intent,candidate,b['ledger'],b['record'])
 original=evaluate_contract(b['contract'],b['ledger'],b['record'])
 assert guarded['core_executed'] and guarded['evaluation']==original
 rows.append(guarded)
assert [r['evaluation']['relation_at_observation'] for r in rows]==['violated','violated','satisfied','satisfied']
assert all(r['evaluation']['relation_at_deadline']=='insufficient' for r in rows)
(HERE/'diagnostic_control.json').write_text(json.dumps(dict(status='unchanged_real_diagnostics',rows=rows,
 clarification='B is a separately registered cross-time question, never admission of C'),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Four B diagnostics preserved exactly through guard: two violated, two satisfied; deadlines still insufficient')
