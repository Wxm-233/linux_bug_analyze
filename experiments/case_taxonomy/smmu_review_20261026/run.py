from pathlib import Path
import json,hashlib,shutil,copy,importlib.util,subprocess,sys
from checker import assess
H=Path(__file__).resolve().parent;R=H.parents[3];E=H.parent;Q=E/'smmu_queue_20261026'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
save('notes_before.json',{'before_sha256':{n:sha(R/n) for n in ['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']}})
shutil.copyfile(E/'smmu_stage_20261026/sync_work_notes.py',H/'sync_work_notes.py')
oldpath=E/'smmu_decision_20261026/checker.py';spec=importlib.util.spec_from_file_location('old_checker',oldpath);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
base=json.loads((Q/'old_1.json').read_text(encoding='utf-8'));mut=copy.deepcopy(base);pairs=list(zip(mut['requests'],mut['stdout'].splitlines()));idx=next(i for i,(r,v) in enumerate(pairs) if r.startswith('writel 0x9050098 '));pairs.insert(0,pairs.pop(idx));mut['requests']=[p[0] for p in pairs];mut['stdout']='\n'.join(p[1] for p in pairs)+'\n'
before=old.assess(mut,True);after=assess(mut,True);assert before['observed_encoding']=='violation' and after['observed_encoding']=='insufficient'
controls=[dict(name='producer_before_payload',raw=mut)]
mut=copy.deepcopy(base);mut['requests'].append(mut['requests'][0]);mut['stdout']+='OK\n';controls.append(dict(name='extra_write_after_observation',raw=mut))
mut=copy.deepcopy(base);mut['stdout']=mut['stdout'].replace('OK 0x0011000000000012','OK 0x0011000000000013');controls.append(dict(name='RAM_mismatch',raw=mut))
mut=copy.deepcopy(base);mut['stdout']='\n'.join(mut['stdout'].splitlines()[:-1])+'\n';controls.append(dict(name='missing_reply',raw=mut))
save('control_inputs.json',controls);results=[]
for c in controls:
 v=assess(c['raw'],True);assert v['observed_encoding']==v['queue']=='insufficient';results.append(dict(name=c['name'],verdict=v))
rows=[]
for r in json.loads((Q/'results.json').read_text(encoding='utf-8'))['cases']:
 p=Q/(r['name']+'.json');raw=json.loads(p.read_text(encoding='utf-8'));v=assess(raw,True)
 assert v['queue']==('error_observed' if r['name']=='unknown_opcode' else 'consumed_in_model')
 rows.append(dict(case=r['name'],sha256=sha(p),verdict=v))
save('regression.json',dict(old_checker_sha256=sha(oldpath),reproduction=dict(before=before,after=after),cases=rows,controls=results))
# A separate optimized interpreter must preserve all rejection results; no input validation uses assert.
code="import json;from pathlib import Path;from checker import assess;cs=json.loads(Path('control_inputs.json').read_text(encoding='utf-8'));print(json.dumps([assess(c['raw'],True)['observed_encoding'] for c in cs]))"
p=subprocess.run([sys.executable,'-O','-c',code],cwd=H,capture_output=True,text=True);assert p.returncode==0 and json.loads(p.stdout)==['insufficient']*4
save('optimized_controls.json',dict(command=[sys.executable,'-O','-c',code],stdout=p.stdout,stderr=p.stderr,code=p.returncode))
print('Prior temporal-evidence defect reproduced; 10 replays and 4 controls pass, plus 4 optimized controls.')
