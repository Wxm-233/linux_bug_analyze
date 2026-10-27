"""Compare full candidate and every preserved relation to registered C, without approval."""
from pathlib import Path
import copy,hashlib,json,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'linux_bug_analyze'))
from linux_bug_analyze.interface_intent import check_intent,_canonical
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=HERE.parent/'btrfs_mainline_20261025'
for p,h in read(old/'frozen_inputs.json').items():assert sha(ROOT/p)==h,p
entries=read(old/'registered_intents.json')
intent=entries[0]['intent'];candidate=read(HERE/'ingested.json')['candidate']
concrete=copy.deepcopy(candidate)
if concrete['deadline_event']=='min_consumption':concrete['deadline_event']=intent['deadline_event']
baseline=intent['contract'];expected=_canonical(baseline['relation'],{s:s for s in baseline['symbols']})
results=read(HERE/'results.json');rows=[]
for part in results['rows'][0]['diagnostics']['parts']:
 if part['field']!='relation':continue
 rows.append(dict(path=part['path'],semantic_roles=part['semantic_roles'],same_registered_relation=_canonical(part['expression'],candidate['symbol_bindings'])==expected))
result=dict(full_candidate_guard=check_intent(intent,concrete),relation_coverage=rows,
 deadline_matches=candidate['deadline_event']=='min_consumption',
 meaning='Subexpression equality is structural coverage only, not approval of scope, other clauses, source authority or facts.',
 original_candidate_unmodified=True,formal_core_executions=0)
p=HERE/'intent_audit.json';assert not p.exists();p.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
