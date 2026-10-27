from pathlib import Path
import argparse,copy,hashlib,importlib.util,json,re,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'linux_bug_analyze'))
from linux_bug_analyze.model_candidate import parse_model_candidate
from linux_bug_analyze.candidate_parts import inspect_parts

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
 if args.output.exists():raise ValueError('preserve prior result')
 read=lambda p:json.loads(p.read_text(encoding='utf-8'))
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 for p,h in read(HERE/'frozen_inputs.json').items():assert sha(ROOT/p)==h,p
 candidate_file=ROOT/'模型调用测试/2026-10-25/btrfs_model_candidate/final.md'
 ingested=parse_model_candidate(candidate_file.read_text(encoding='utf-8'),read(HERE.parent/'btrfs_model_candidate_20261025/documents.json'))
 candidate=ingested['candidate'];before=copy.deepcopy(candidate);roles=read(HERE/'role_registry.json')
 folder=ROOT/'linux_bug_analyze/analysis_out/btrfs-consumer-observation-20261024/parent'
 boot=(folder/'boot.log').read_text(encoding='utf-8');disk=(folder/'super.txt').read_text(encoding='utf-8')
 config=(folder/'kernel.config').read_text(encoding='utf-8')
 def scalar(text,pattern):
  rows=list(re.finditer(pattern,text,re.M));assert len(rows)==1
  return int(rows[0][1]),text.count('\n',0,rows[0].start())+1
 page,page_line=scalar(boot,r'^PAGE_SIZE=(\d+)$')
 sector,sector_line=scalar(disk,r'^sectorsize\s+(\d+)$')
 devices,device_line=scalar(disk,r'^num_devices\s+(\d+)$')
 fsids=re.findall(r'^fsid\s+([0-9a-f-]+)$',disk,re.M);assert len(fsids)==1
 assert 'CONFIG_ARM64_64K_PAGES=y' in config and page==65536
 spec=importlib.util.spec_from_file_location('original_operands',HERE.parent/'btrfs_consumer_observation_20261024/observations.py')
 obs=importlib.util.module_from_spec(spec);spec.loader.exec_module(obs)
 events=obs.project_operands(boot,fsids[0],'typed-parts-parent');rows=[]
 def ref(filename,line):
  p=folder/filename
  return dict(path=str(p.relative_to(ROOT)),sha256=sha(p),start_line=line,end_line=line)
 for event in events:
  context=event['event_id'];facts={}
  def fact(role,value,evidence,event_kind):
   facts[role]=dict(value=value,origin='program_projection',context_id=context,evidence=evidence,event_kind=event_kind)
  fact('page_size',page,[ref('boot.log',page_line)],'run_geometry')
  fact('disk_sector_size',sector,[ref('super.txt',sector_line)],'archived_disk_geometry')
  fact('device_count',devices,[ref('super.txt',device_line)],'archived_disk_geometry')
  fact('request_values',sorted({e['request'] for e in events}),[ref('boot.log',e['boot_line']) for e in events],'registered_run_requests')
  for role,key,kind in [('cache','consumed_cache','saved_consumption_operand'),('request','request','saved_request'),
                        ('result','result','saved_result'),('adjacent_disk','adjacent_disk_sample','after_consumption_sample')]:
   fact(role,event[key],[ref('boot.log',event['boot_line'])],kind)
  out=inspect_parts(candidate,roles,facts,context_id=context)
  assert out['binding_status']=='insufficient'
  assert out['summary']['scope']==dict(satisfied=0,violated=0,insufficient=7)
  assert out['summary']['relation']==dict(satisfied=3,violated=0,insufficient=2)
  assert len(out['parts'])==12 and candidate==before
  assert 'disk_at_deadline' not in facts and 'mount_flags' not in facts and 'selected_profile' not in facts
  rows.append(dict(context_id=context,object_id=event['object_id'],facts=facts,diagnostics=out))
 result=dict(status='typed_dependencies_and_lossless_parts_replayed',candidate_sha256=sha(candidate_file),
  candidate_unchanged=True,candidate_count=1,archived_contexts=2,rows=rows,
  distinct_scope_parts=7,distinct_relation_parts=5,local_arithmetic_results=6,unresolved_reference_parts=4,
  model_calls=0,new_boots=0,independent_positive=0,independent_normal=0,
  caveats=['schema/role vocabulary manually registered','old candidate is read development input, no new extraction result',
  'arithmetic already checked by operand parser; no new defect detection gain',
  'scope bindings remain invalid; local value diagnostics do not admit whole candidate',
  'no original-core evaluation or deadline promotion'])
 args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in result.items() if k!='rows'}))

if __name__=='__main__':main()
