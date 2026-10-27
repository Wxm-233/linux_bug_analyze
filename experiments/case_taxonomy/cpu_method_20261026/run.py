"""Replay the existing bounded method unchanged, redirecting its output only."""
from pathlib import Path
import ast,hashlib,json,sys,shutil
H=Path(__file__).resolve().parent;R=H.parents[3];OLD=H.parent/'cpu_topology_chain_20261023'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
names=['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']
save('notes_before.json',dict(before_sha256={n:sha(R/n) for n in names}))
shutil.copyfile(H.parent/'btrfs_method_20261026/sync_work_notes.py',H/'sync_work_notes.py')
driver=OLD/'run_chain_trial_v2.py';oldhash=sha(OLD/'results_v2.json')
tree=ast.parse(driver.read_text(encoding='utf-8'))
main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
assignment=main.body[0]
assert isinstance(assignment,ast.Assign) and assignment.targets[0].id=='output'
assert ast.unparse(assignment.value)=="HERE / 'results_v2.json'"
assignment.value=ast.Call(func=ast.Name(id='Path',ctx=ast.Load()),args=[ast.Constant(str(H/'replay.json'))],keywords=[])
sys.path.insert(0,str(R/'linux_bug_analyze'))
exec(compile(ast.fix_missing_locations(tree),str(driver),'exec'),dict(__file__=str(driver),__name__='__main__'))
result=read(H/'replay.json');assert result==read(OLD/'results_v2.json')
assert sha(OLD/'results_v2.json')==oldhash
summary=[]
for row in result['profiles']:
 c=row['checked'];e=c['evaluation'];s=c['sample']
 assert e['relation_at_deadline']==e['whole_path']=='insufficient'
 summary.append(dict(profile=row['profile'],sample_relation=e['relation_at_observation'],mask=s['mask'],online=s['online'],locks=s['locks'],final_contains_target=row['comparative_diagnostics']['final_state_only_contains_target'],deadline=e['relation_at_deadline']))
assert all(x['checked']['status']=='insufficient' for x in result['controls'])
packet=read(OLD/'trial_inputs.json')
cost={}
for row in packet['rows']:
 cost[row['profile']]=dict(contract_top_level_fields=list(row['contract']),required_claims=row['contract']['required_claims'],ledger_claim_count=len(row['ledger']['claims']),artifact_count=len(row['artifact_paths']))
save('summary.json',dict(exact_replay=True,profiles=summary,evidence_controls=len(result['controls']),old_archive_inputs=len(packet['archive_input_sha256']),manual_input_inventory=cost,inventory_is_not_time_cost=True,new_boots=0,new_model_calls=0,new_cases=0,independent_positive=0,independent_normal=0))
pins=[driver,OLD/'sample_adapter.py',OLD/'trial_inputs.json',OLD/'method_manifest_v2.json',OLD/'results_v2.json',OLD/'reviewed_chain.md',H/'run.py']
save('inputs.json',{str(p.relative_to(R)).replace('\\','/'):sha(p) for p in pins})
print(json.dumps(summary))
