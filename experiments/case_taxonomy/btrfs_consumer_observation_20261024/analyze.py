from pathlib import Path
import sys,json,hashlib,re
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2];sys.path.insert(0,str(PROJECT))
from linux_bug_analyze.btrfs_runtime_facts import project
from observations import project_operands,ObservationError
OUT=PROJECT/'analysis_out/btrfs-consumer-observation-20261024';OLD=PROJECT/'analysis_out/btrfs-mount-resume-20261023'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 assert not (HERE/'results.json').exists()
 manifest=json.loads((OUT/'manifest.json').read_text());rows=[];controls=[]
 seal=json.loads((HERE.parent/'btrfs_mount_resume_20261023/results.json').read_text())
 for row in manifest:
  mode=row['mode'];d=OUT/mode
  for file,h in row['artifacts'].items():assert sha(d/file)==h
  assert sha(Path(row['image']))==row['image_sha256']
  assert sha(Path(row['disk']))==row['disk_after_sha256']
  assert sha(d/'kernel.config')==row['baseline_build']['config_sha256']
  assert sha(Path(row['baseline_build']['image']))==row['baseline_build']['image_sha256']
  assert sha(d/'super.observed.c')==row['source_after_sha256']
  assert sha(d/'observation.patch')==row['patch_sha256']
  boot=(d/'boot.log').read_text();facts=project(boot,(d/'super.txt').read_text(),(d/'tree.txt').read_text(),requests=[2048,8192],sizes=[1024,6144,8192],context_id='observed-'+mode)
  events=project_operands(boot,facts['fsid'],'observed-'+mode)
  assert all(e['adjacent_disk_sample']==facts['sector_size']==65536 for e in events)
  baseline=OLD/f'{mode}-64k/sector65536'
  for n in ['boot.log','super.txt','tree.txt']:assert sha(baseline/n)==seal['artifact_sha256'][str((baseline/n).relative_to(OLD))]
  original=project(*[(baseline/n).read_text() for n in ['boot.log','super.txt','tree.txt']],requests=[2048,8192],sizes=[1024,6144,8192],context_id='baseline-'+mode)
  def layouts(f):return {(v['request'],v['size']):v['extent'] for v in f['files']}
  assert facts['effective_limits']==original['effective_limits'] and layouts(facts)==layouts(original)
  # Preprocessed code keeps the captured operand in the actual clamp expression.
  pp=(d/'super.i').read_text();assert pp.count('u32 lba_cache = info->sectorsize;')==1
  assert 'lba_result' in pp and pp.count('LBA_CLAMP info=')==1
  expression=re.findall(r'^\s*u64 lba_result = (.+);$',pp,re.M)
  assert len(expression)==1 and 'lba_cache' in expression[0] and 'lba_request' in expression[0] and 'info->' not in expression[0]
  assert pp.count('info->max_inline = lba_result;')==1
  rows.append({'mode':mode,'events':events,'facts':facts,'unobserved_behavior_match':True,'config_matches_unobserved':True})
  if not controls:
   line=next(s for s in boot.splitlines() if 'LBA_CLAMP' in s)
   cases={'missing':boot.replace(line+'\n',''),'duplicate':boot+'\n'+line+'\n',
          'wrong_uuid':boot.replace('fsid='+facts['fsid'],'fsid=11111111-1111-1111-1111-111111111111',1),
          'bad_result':boot.replace('result=2048','result=2049',1),
          'wrong_request':boot.replace('request=2048 cache=','request=2049 cache=',1)}
   ptr=events[0]['info_pointer'];cases['zero_pointer']=boot.replace('info='+ptr,'info=0000000000000000',1)
   cases['late_event']=boot.replace(line+'\n','').replace('MOUNT request=2048 rc=0 errno=0','MOUNT request=2048 rc=0 errno=0\n'+line)
   for label,b in cases.items():
    try:project_operands(b,facts['fsid'],'control')
    except ObservationError as e:controls.append({'name':label,'rejected':True,'reason':str(e)});continue
    raise AssertionError('control accepted '+label)
 assert manifest[0]['disk_before_sha256']==manifest[1]['disk_before_sha256']
 result={'new_kernel_builds':2,'new_boots':2,'new_rw_mounts':4,'new_ro_remounts':4,'new_files':12,'operand_events':4,'observations':rows,'negative_controls':controls,'independent_positive':0,'independent_normal':0,'scope':'reviewed local observation transformation; no universal equivalence or atomic disk/cache snapshot'}
 (HERE/'results.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'events':[{k:v for k,v in e.items() if k not in ['info_pointer','super_pointer','object_id']} for r in rows for e in r['events']],'controls':len(controls)},indent=2))
if __name__=='__main__':main()
