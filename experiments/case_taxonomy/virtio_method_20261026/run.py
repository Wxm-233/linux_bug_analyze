"""Preserve raw output and compiled layout sources without changing old probe."""
from pathlib import Path
import importlib.util,json,hashlib,subprocess,shutil,traceback
H=Path(__file__).resolve().parent;R=H.parents[3];P=H.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
names=['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']
save('notes_before.json',dict(before_sha256={n:sha(R/n) for n in names}))
shutil.copyfile(P/'smmu_method_20261026/sync_work_notes.py',H/'sync_work_notes.py')
driver=P/'virtio_dma_layout_probe.py';old=P/'virtio_dma_layout_result.json'
save('inputs.json',{str(p.relative_to(R)):sha(p) for p in [driver,old,P/'cross_arch_virtio_source_20261013.json',H/'run.py']})
spec=importlib.util.spec_from_file_location('probe',driver);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
co=subprocess.check_output;run=subprocess.run;raw=[];sources={};builds=[]
save('environment.json',dict(compiler=co(['cc','--version'],text=True),uname=co(['uname','-a'],text=True),scope='host layout with type doubles; no DMA'))
def capture(argv,*a,**kw):
 out=co(argv,*a,**kw)
 if argv[0]=='git':sources[argv[-1]]=out
 else:raw.append(dict(program=Path(argv[0]).name,stdout=out))
 return out
def build(argv,*a,**kw):
 if argv[0]=='cc':
  src=Path(argv[-3]);dest=H/src.name
  with dest.open('x',encoding='utf-8') as f:f.write(src.read_text())
  builds.append(dict(source=dest.name,sha256=sha(dest),flags=argv[1:-3]))
 return run(argv,*a,**kw)
subprocess.check_output=capture;subprocess.run=build
try:
 result=m.run(Path('/root/repos/linux'));save('results.json',result)
 assert result==json.loads(old.read_text(encoding='utf-8'))
 save('replay_check.json',dict(exact_old_results=True,layout_compiles=len(builds),executions=len(raw),new_kernel_boots=0,new_dma_operations=0,new_model_calls=0))
except Exception:
 save('failure.json',dict(traceback=traceback.format_exc()));raise
finally:
 subprocess.check_output=co;subprocess.run=run
 save('raw_layouts.json',raw);save('sources.json',sources);save('builds.json',builds)
print(json.dumps(dict(layout_compiles=len(builds),executions=len(raw),exact_old_results=True)))
