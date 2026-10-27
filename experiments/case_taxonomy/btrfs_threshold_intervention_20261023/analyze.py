from pathlib import Path
import sys,json,hashlib,copy
HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2];sys.path.insert(0,str(PROJECT))
from linux_bug_analyze.btrfs_runtime_facts import project,local_checks,EvidenceError
OUT=PROJECT/'analysis_out/btrfs-threshold-intervention-20261023'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 manifest=json.loads((OUT/'manifest.json').read_text())
 assert sha(Path(manifest['image']))==manifest['image_sha256']
 assert sha(OUT/'kernel.config')==manifest['config_sha256']
 assert sha(HERE/'init.c')==manifest['init_source_sha256']
 rows=[];sources={}
 for run in manifest['runs']:
  order=run['order'];d=OUT/order
  assert run['before_sha256']==manifest['baseline_sha256']
  assert sha(Path(run['disk']))==run['after_sha256']
  for n,h in run['artifacts'].items():assert sha(d/n)==h
  raw=[(d/n).read_text() for n in ['boot.log','super.txt','tree.txt']];sources[order]=raw
  f=project(*raw,requests=[4096,8192] if order=='AB' else [8192,4096],sizes=[1024,4095,4096,4097,6144,8192,8193],context_id=order)
  assert f['page_size']==f['sector_size']==f['node_size']==65536
  rows.append({'facts':f,'local_checks':local_checks(f)})
 def layouts(row):return {(f['request'],f['size']):f['extent'] for f in row['facts']['files']}
 a,b=map(layouts,rows);assert a==b
 contrasts=[{'size':s,'at4096':a[4096,s],'at8192':a[8192,s],'changed':a[4096,s]!=a[8192,s]} for s in [1024,4095,4096,4097,6144,8192,8193]]
 # Deliberate evidence-corruption controls, never counted as real cases.
 raw=sources['AB'];controls=[]
 def reject(label,inputs,requests=[4096,8192]):
  try:project(*inputs,requests=requests,sizes=[1024,4095,4096,4097,6144,8192,8193],context_id='control')
  except EvidenceError as e:controls.append({'control':label,'status':'rejected','reason':str(e)});return
  raise AssertionError('corruption accepted: '+label)
 boot,sup,tree=raw
 reject('wrong_filesystem_uuid',[boot,sup.replace(rows[0]['facts']['fsid'],'11111111-1111-1111-1111-111111111111'),tree])
 line=next(x for x in boot.splitlines() if x.startswith('FILE '))
 reject('duplicate_file_observation',[boot+'\n'+line+'\n',sup,tree])
 line=next(x for x in boot.splitlines() if x.startswith('PERSISTED '))
 reject('missing_persistent_readback',[boot.replace(line+'\n',''),sup,tree])
 reject('wrong_inode_filename',[boot,sup,tree.replace('name: option4096_size1024','name: different_file')])
 reject('missing_extent',[boot,sup,tree.replace('EXTENT_DATA','UNREGISTERED_DATA',1)])
 reject('wrong_mount_order',raw,[8192,4096])
 reject('missing_completion',[boot.replace('EXPERIMENT_DONE failures=0',''),sup,tree])
 reject('option_log_disagreement',[boot.replace('max_inline=4096,','max_inline=4097,',1),sup,tree])
 line=next(x for x in boot.splitlines() if x.startswith('FILE '))
 moved=boot.replace(line+'\n','').replace('MOUNT request=8192 rc=0 errno=0','MOUNT request=8192 rc=0 errno=0\n'+line)
 reject('record_in_wrong_mount_interval',[moved,sup,tree])
 reject('wrong_subvolume',[boot.replace('subvolid=5,','subvolid=256,',1),sup,tree])
 # Existing matrix is reprojected, not rerun or counted as new evidence.
 old=PROJECT/'analysis_out/btrfs-mount-resume-20261023';replay=[]
 prior=json.loads((HERE.parent/'btrfs_mount_resume_20261023/results.json').read_text())
 for mode in ['parent','fix']:
  for page,sector in [(64,65536),(64,4096),(4,4096)]:
   d=old/f'{mode}-{page}k'/f'sector{sector}'
   for n in ['boot.log','super.txt','tree.txt']:assert sha(d/n)==prior['artifact_sha256'][str((d/n).relative_to(old))]
   f=project(*[(d/n).read_text() for n in ['boot.log','super.txt','tree.txt']],requests=[2048,8192],sizes=[1024,6144,8192],context_id=f'{mode}-{page}k-{sector}')
   replay.append({'facts':f,'local_checks':local_checks(f)})
 result={'new_boots':2,'new_kernel_builds':0,'new_rw_mounts':4,'new_ro_remounts':4,'new_files':28,'old_boots_replayed':6,'old_files_reprojected':36,'independent_positive':0,'independent_normal':0,'crossed_order_layouts_equal':True,'contrasts':contrasts,'new_records':rows,'old_records':replay,'negative_controls':controls,'adapter_sha256':sha(PROJECT/'linux_bug_analyze/btrfs_runtime_facts.py')}
 (HERE/'results.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'contrasts':contrasts,'controls':controls,'old_cap_violations':[(r['facts']['context_id'],c['request']) for r in replay for c in r['local_checks']['effective_cap'] if not c['satisfied']]},indent=2))
if __name__=='__main__':main()
