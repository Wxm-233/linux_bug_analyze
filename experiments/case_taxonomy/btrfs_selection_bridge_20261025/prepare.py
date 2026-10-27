from pathlib import Path
import hashlib,json,shutil,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 p=HERE/n;assert not p.exists();p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
names=['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']
save('notes_before.json',dict(before_sha256={n:sha(ROOT/n) for n in names}))
shutil.copyfile(HERE.parent/'btrfs_event_scope_20261025/sync_work_notes.py',HERE/'sync_work_notes.py')
code="""from pathlib import Path
import hashlib,json
out={}
for mode in ['parent','fix']:
 p=Path('/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024')/mode/'build'
 out[mode]={n:{'text':(p/n).read_text(),'sha256':hashlib.sha256((p/n).read_bytes()).hexdigest()} for n in ['include/generated/autoconf.h','.config']}
print(json.dumps(out))
"""
r=subprocess.run(['wsl.exe','-d','Ubuntu','--','python3','-c',code],capture_output=True);assert r.returncode==0
headers=json.loads(r.stdout.decode('utf-8'))
for mode,items in headers.items():
 for name,item in items.items():
  p=HERE/(mode+('_autoconf.h' if name.endswith('.h') else '_config'));assert not p.exists();p.write_bytes(item['text'].encode('utf-8'));assert sha(p)==item['sha256']
files=[ROOT/'linux_bug_analyze/linux_bug_analyze'/n for n in ['contrast_selection.py','observation_planning.py']]
files += [HERE/'run.py',HERE.parent/'btrfs_typed_model_20261025/ingested.json',HERE.parent/'btrfs_event_scope_20261025/event_audit.json',HERE.parent/'contrast_selection_20261017/example_pool.json',HERE.parent/'contrast_selection_20261017/selection.json']
raw=ROOT/'linux_bug_analyze/analysis_out/btrfs-consumer-observation-20261024'
files+=[raw/'manifest.json']+[HERE/(m+s) for m in ['parent','fix'] for s in ['_config','_autoconf.h']]
save('frozen_inputs.json',{str(p.relative_to(ROOT)):sha(p) for p in files})
save('protocol.json',dict(scope='known-case development, all outcomes previously read',selector='unchanged same-revision cross-architecture policy',no_candidate_repair=True,new_runtime=False,source_hypotheses=[4096,65536],legal_requests=[2048,8192],no_independent_gain_claim=True))
print('Pinned actual WSL configuration and headers; run inputs fixed')
