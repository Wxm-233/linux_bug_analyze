"""Read-only reconstruction using the archived verifier's observation block."""
from pathlib import Path
import ast,hashlib,json,re,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
OLD=HERE.parent/'btrfs_mount_resume_20261023'
OUT=ROOT/'linux_bug_analyze/analysis_out/btrfs-mount-resume-20261023'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
def save(n,v):
 p=HERE/n;assert not p.exists(),n
 p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
names=['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']
before=dict(before_sha256={n:sha(ROOT/n) for n in names})
if (HERE/'notes_before.json').exists():
 assert read(HERE/'notes_before.json')==before
else:save('notes_before.json',before)
shutil.copyfile(HERE.parent/'research_direction_20261025/sync_work_notes.py',HERE/'sync_work_notes.py')
saved=read(OLD/'results.json')
for rel,h in saved['artifact_sha256'].items():assert sha(OUT/rel)==h,rel
module=ast.parse((OLD/'verify.py').read_text(encoding='utf-8'))
main=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='main')
# Keep precisely initialization and the first outer loop; no historical output writes,
# no runtime Image/disk access, no imports of the kernel execution runner.
assert [type(x).__name__ for x in main.body[:3]]==['Assign','Assign','For']
body=main.body[:3]+[ast.Return(value=ast.Tuple(elts=[ast.Name(id='rows',ctx=ast.Load()),ast.Name(id='artifacts',ctx=ast.Load())],ctx=ast.Load()))]
fn=ast.FunctionDef(name='reconstruct',args=main.args,body=body,decorator_list=[])
code=ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[]))
ns=dict(OUT=OUT,re=re,sha=sha)
exec(compile(code,str(OLD/'verify.py'),'exec'),ns)
rows,artifacts=ns['reconstruct']()
print(json.dumps(dict(rows_equal=rows==saved['observations'],artifact_keys=list(artifacts)[:1],saved_keys=list(saved['artifact_sha256'])[:1])))
artifacts={k.replace('\\','/'):v for k,v in artifacts.items()}
assert rows==saved['observations'] and artifacts==saved['artifact_sha256']
builds={}
for mode in ['parent','fix']:
 for page in [4,64]:
  folder=OUT/f'{mode}-{page}k';b=read(folder/'build.json')
  assert sha(folder/'kernel.config')==b['config_sha256']
  assert sha(OLD/'init.c')==b['init_source_sha256']
  cfg=(folder/'kernel.config').read_text(encoding='utf-8')
  assert f'CONFIG_ARM64_{page}K_PAGES=y' in cfg
  builds[f'{mode}-{page}k']=dict(revision=b['revision'],config_sha256=b['config_sha256'],image_sha256=b['image_sha256'])
for mode in ['parent','fix']:
 assert builds[f'{mode}-4k']['revision']==builds[f'{mode}-64k']['revision']
diagnostics=[]
for row in rows:
 for request,value in row['effective_max_inline'].items():
  r=int(request);disk=row['sector_size']
  diagnostics.append(dict(mode=row['mode'],page_size=row['page_size'],disk_sector_size=disk,request=r,
   effective=value,reference_arithmetic=min(r,disk),matches_archived_geometry_arithmetic=value==min(r,disk),
   reference_scope='offline disk geometry; not independently sampled at deadline',
   inline_geometry_gate='eligible_geometry_only' if row['page_size']==disk else 'not_applicable_to_inline_path',
   readiness_contract='insufficient'))
# Boundary checks of the analytically derived equivalence, not new cases.
checks=0
for r in range(33):
 for c in range(33):
  for d in range(33):
   assert (min(r,c)==min(r,d)) == (c==d or r<=min(c,d));checks+=1
save('results.json',dict(archive_reconstructed=True,builds=builds,archived_runs=len(rows),archived_files=sum(len(x['files']) for x in rows),
 diagnostics=diagnostics,arithmetic_boundary_checks=checks,arithmetic_formula='min(r,c)==min(r,d) iff c==d or r<=min(c,d), for nonnegative integers',
 formula_status='manual algebra plus finite sanity checks; not automated theorem discovery',
 previous_candidate_unchanged=True,new_model_calls=0,new_boots=0,independent_positive=0,independent_normal=0))
save('reconstructed_observations.json',rows)
pins=[OLD/'verify.py',OLD/'results.json',OLD/'init.c',HERE/'run.py']
save('inputs.json',{str(p.relative_to(ROOT)):sha(p) for p in pins}|{str((OUT/p).relative_to(ROOT)):h for p,h in artifacts.items()})
print(json.dumps(dict(archived_runs=len(rows),archived_files=36,diagnostic_rows=len(diagnostics),offline_arithmetic_mismatches=sum(not x['matches_archived_geometry_arithmetic'] for x in diagnostics),boundary_checks=checks)))
