from pathlib import Path
import hashlib,json,sys,copy,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'linux_bug_analyze'))
from linux_bug_analyze.contract_archive import load_verified_archive
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def save(n,v):(HERE/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert not (HERE/'frozen_inputs.json').exists(),'preserve registration'
prior=HERE.parent/'btrfs_archive_gate_20261024/frozen_inputs.json';pins=read(prior)
for p,h in pins.items():assert sha(ROOT/p)==h,p
relative='linux_bug_analyze/experiments/case_taxonomy/btrfs_layered_contract_20261024/registered_inputs.json'
bundles,snapshots=load_verified_archive(ROOT/relative,pins[relative]);items=[]
for b in bundles:
 if b['contract']['id']!='btrfs.layered.C':continue
 intent=dict(schema='interface_intent_v1',interface_id='btrfs.geometry_before_max_inline',
  deadline_event=b['record']['deadline_event'],contract=copy.deepcopy(b['contract']),
  origin='researcher_registered_question_not_proven_authority')
 proposal=dict(interface_id=intent['interface_id'],deadline_event=intent['deadline_event'],
  contract=copy.deepcopy(b['contract']),symbol_bindings={n:n for n in b['contract']['symbols']})
 items.append(dict(record_id=b['record']['id'],intent=intent,candidate=proposal))
assert len(items)==4
save('registered_intents.json',items)
files=[HERE/'registered_intents.json',HERE/'interface_card.md',HERE/'run.py',
 ROOT/'linux_bug_analyze/linux_bug_analyze/interface_intent.py',ROOT/'linux_bug_analyze/tests/test_interface_intent.py']
pins.update({str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in files})
save('frozen_inputs.json',pins)
names=['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']
save('notes_before.json',dict(before_sha256={n:sha(ROOT/n) for n in names}))
shutil.copyfile(HERE.parent/'new_input_contract_trial_20261017/sync_work_notes.py',HERE/'sync_work_notes.py')
print('Four independent intent records registered from existing C questions; original evidence preserved')
