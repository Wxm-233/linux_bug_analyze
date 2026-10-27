"""Recompile the historical bounded harness, preserving raw commands and sources."""
from pathlib import Path
import importlib.util,json,hashlib,subprocess,traceback,shutil
H=Path(__file__).resolve().parent;R=H.parents[3];P=H.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
names=['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']
save('notes_before.json',dict(before_sha256={n:sha(R/n) for n in names}))
shutil.copyfile(P/'interface_queue_20261026/sync_work_notes.py',H/'sync_work_notes.py')
driver=P/'smmu_range_probe.py'; old=P/'smmu_range_result.json'
save('inputs.json',{str(p.relative_to(R)):sha(p) for p in [driver,old,P/'cross_arch_smmu_source_20261013.json',H/'run.py']})
spec=importlib.util.spec_from_file_location('probe',driver);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
co=subprocess.check_output;run=subprocess.run;raw=[];sources={};builds=[]
save('environment.json',dict(compiler=co(['cc','--version'],text=True),uname=co(['uname','-a'],text=True),scope='host function harness, not ARM64 kernel or device execution'))
def capture(argv,*a,**kw):
 out=co(argv,*a,**kw)
 if argv[0]=='git':
  key=argv[-1];sources[key]=out
 elif Path(argv[0]).name in ['old','fixed','single_page_only_mutant','ttl_hint_only_mutant']:
  raw.append(dict(variant=Path(argv[0]).name,pages=int(argv[1]),page_shift=int(argv[2]),leaf=bool(int(argv[3])),range_feature=bool(int(argv[4])),stdout=out))
 return out
def compile_capture(argv,*a,**kw):
 if argv[0]=='cc':
  src=Path(argv[-3]);dest=H/src.name
  with dest.open('x',encoding='utf-8') as f:f.write(src.read_text())
  builds.append(dict(source=dest.name,sha256=sha(dest),flags=argv[1:-3]))
 return run(argv,*a,**kw)
subprocess.check_output=capture;subprocess.run=compile_capture
try:
 result=m.run(Path('/root/repos/linux'))
 save('results.json',result)
 assert result==json.loads(old.read_text(encoding='utf-8'))
 save('replay_check.json',dict(exact_old_results=True,function_compiles=len(builds),function_invocations=len(raw),new_kernel_boots=0,new_model_calls=0,new_cases=0))
except Exception:
 save('failure.json',dict(traceback=traceback.format_exc()));raise
finally:
 subprocess.check_output=co;subprocess.run=run
 save('raw_commands.json',raw);save('sources.json',sources);save('builds.json',builds)
print(json.dumps(dict(function_compiles=len(builds),function_invocations=len(raw),exact_old_results=True)))
