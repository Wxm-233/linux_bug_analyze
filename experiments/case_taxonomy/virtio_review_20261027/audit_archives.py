from pathlib import Path
import json,hashlib,importlib.util
H=Path(__file__).resolve().parent;BASE=H.parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
ledger={}
def bind(p):
 if not p.is_file():raise RuntimeError('missing evidence '+str(p))
 n=str(p.relative_to(BASE)).replace('\\','/');ledger[n]=sha(p);return n
source_records=[]
for folder,manifest,key in [('virtio_dma_chain_20261026','source_manifest.json','file'),('virtio_shutdown_20261026','sources.json','local'),('virtio_cache_boundary_20261027','sources.json','local')]:
 mf=BASE/folder/manifest;data=read(mf);bind(mf)
 for row in data['files']:
  p=BASE/folder/'source'/row[key];b=p.read_bytes()
  if sha(p)!=row['sha256'] or hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()!=row['blob']:raise RuntimeError('source mismatch '+str(p))
  source_records.append(dict(path=row['path'],revision=data['revision'],evidence=bind(p)))
hash_checks=0
for folder in ['virtio_add_recycle_20261027','virtio_cache_boundary_20261027']:
 d=BASE/folder;bind(d/'method_update.json')
 for name,digest in read(d/'method_update.json')['evidence_sha256'].items():
  p=d/name
  if sha(p)!=digest:raise RuntimeError('archived artifact changed '+str(p))
  bind(p);hash_checks+=1
for folder,names in {
 'virtio_method_20261026':['raw_layouts.json','relation_audit.json','source_audit.json','audit_inputs.json'],
 'virtio_dma_chain_20261026':['function_manifest.json','mapping_results.json','mapping_audit.json','source_anchors.json'],
 'virtio_kimi_direct_20261026':['audit.json','results.json','bounce_gate_results.json','model_obligations.json','model_review.json','additional_source.json'],
 'virtio_recycle_20261026':['audit.json','results.json','controls.json','functions.json'],
 'virtio_shutdown_20261026':['functions.json','results.json','add_source_review.json']}.items():
 for name in names:bind(BASE/folder/name)
def module(folder,file):
 p=BASE/folder/file;bind(p);spec=importlib.util.spec_from_file_location('review_'+folder,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
chain=module('virtio_add_recycle_20261027','checker.py');cache=module('virtio_cache_boundary_20261027','audit.py');replay=[]
for i,row in enumerate(read(BASE/'virtio_add_recycle_20261027/results.json')):
 out=chain.assess(row)
 if out['status']!='observed_object_publication_recycle' or out['whole_path']!='insufficient':raise RuntimeError('chain replay')
 old=read(BASE/'virtio_add_recycle_20261027/audit.json')[i]
 if any(old.get(k)!=v for k,v in out.items()):raise RuntimeError('changed chain adjudication')
 replay.append(dict(kind='chain_archive',index=i,result=out))
for i,ctrl in enumerate(read(BASE/'virtio_add_recycle_20261027/controls.json')):
 out=chain.assess(ctrl['input'])
 if out['status']!='rejected':raise RuntimeError('chain negative')
 replay.append(dict(kind='chain_old_control',index=i,result=out))
for name in ['results.json','layout_trace_results.json']:
 for i,row in enumerate(read(BASE/'virtio_cache_boundary_20261027'/name)):
  out=cache.assess(row)
  if out['status']!='observed_instrumented_sequence' or out['hardware_effect']!='insufficient':raise RuntimeError('cache replay')
  replay.append(dict(kind='cache_'+name,index=i,result=out))
for i,ctrl in enumerate(read(BASE/'virtio_cache_boundary_20261027/controls.json')):
 out=cache.assess(ctrl['input'])
 if out['status']!='rejected':raise RuntimeError('cache negative')
 replay.append(dict(kind='cache_old_control',index=i,result=out))
for p in [H/'frozen_plan.json',BASE/'cpu_method_20261026/README.md',BASE/'btrfs_method_20261026/README.md',BASE/'smmu_review_20261026/review_matrix.json']:bind(p)
(H/'evidence_index.json').write_text(json.dumps(dict(sources=source_records,hash_ledger=ledger,recorded_hash_checks=hash_checks,scope='archive integrity and existing bounded evaluators, not semantic independence'),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(H/'archive_replay.json').write_text(json.dumps(dict(assess_calls=len(replay),new_kernel_runs=0,new_controls=0,records=replay),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(source_blob_records=len(source_records),artifacts=len(ledger),recorded_hash_checks=hash_checks,old_assess_replays=len(replay))))
