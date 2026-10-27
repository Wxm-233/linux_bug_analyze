from pathlib import Path
import json,hashlib,shutil,copy
from checker import assess
H=Path(__file__).resolve().parent;R=H.parents[3];E=H.parent;Q=E/'smmu_queue_20261026'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 if n in ['notes_before.json','input_manifest.json'] and (H/n).exists():
  assert json.loads((H/n).read_text(encoding='utf-8'))==v;return
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
save('notes_before.json',{'before_sha256':{n:sha(R/n) for n in ['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']}})
shutil.copyfile(E/'smmu_stage_20261026/sync_work_notes.py',H/'sync_work_notes.py')
authority=E/'smmu_chain_20261026/authority.json';identity=json.loads((Q/'source_and_binary.json').read_text(encoding='utf-8'));assert sha(authority)==identity['authority_sha256']
prior=json.loads((Q/'results.json').read_text(encoding='utf-8'));rows=[];inputs=[]
for r in prior['cases']:
 p=Q/(r['name']+'.json');raw=json.loads(p.read_text(encoding='utf-8'));out=assess(raw,True)
 assert out['queue']==('error_observed' if r['name']=='unknown_opcode' else 'consumed_in_model')
 rows.append(dict(case=r['name'],verdict=out));inputs.append(dict(path=str(p.relative_to(R)),sha256=sha(p)))
assert sum(r['verdict']['encoding']=='violation' for r in rows)==3
save('results_v2.json',rows)
base=json.loads((Q/'old_1.json').read_text(encoding='utf-8'));controls=[]
mut=copy.deepcopy(base);mut.pop('words');controls.append(('missing_words',mut,True,'insufficient','insufficient'))
mut=copy.deepcopy(base);mut['stdout']='\n'.join(mut['stdout'].splitlines()[:-1])+'\n';controls.append(('missing_response',mut,True,'violation','insufficient'))
mut=copy.deepcopy(base);mut['words'][0][1]^=1<<10;controls.append(('words_disagree_with_readback',mut,True,'pass_this_rule_only','insufficient'))
controls.append(('missing_authority',base,False,'insufficient','consumed_in_model'))
checks=[]
for name,raw,auth,encoding,queue in controls:
 out=assess(raw,auth);assert out['encoding']==encoding and out['queue']==queue and out['whole_path']=='insufficient'
 assert out['observed_encoding']=='insufficient'
 checks.append(dict(name=name,synthetic=True,verdict=out))
save('controls_v2.json',checks)
save('input_manifest.json',dict(inputs=inputs,authority=dict(path=str(authority.relative_to(R)),sha256=sha(authority)),manual_rule='TG nonzero and NUM=SCALE=TTL=0 reserved, scoped NH_VA',scope='same-family known development replay; not independent evaluation'))
print('10 raw transcripts evaluated; 4 evidence controls passed; whole_path never promoted.')
