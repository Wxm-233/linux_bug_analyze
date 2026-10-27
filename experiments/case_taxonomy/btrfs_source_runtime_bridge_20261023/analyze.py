from pathlib import Path
import sys,json,hashlib,importlib.util,copy,traceback
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2];sys.path.insert(0,str(PROJECT))
from linux_bug_analyze.preprocessed_evidence import extract_definitions
from linux_bug_analyze.btrfs_runtime_facts import project,local_checks
from bridge import join,BindingError
OUT=PROJECT/'analysis_out/btrfs-source-runtime-bridge-20261023'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def loadmod(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
def main():
 assert not (HERE/'results.json').exists(),'preserve completed output'
 freeze=json.loads((HERE/'frozen_methods.json').read_text(encoding='utf-8-sig'))
 for p,h in freeze.items():assert sha(PROJECT.parent/p)==h,p
 ex=loadmod('frozen_extractor',HERE.parent/'btrfs_first_consumer_20261011/extractor.py')
 geom=loadmod('frozen_geometry',HERE.parent/'btrfs_geometry_authority_20261012/contract.py')
 manifest=json.loads((OUT/'manifest.json').read_text());summaries=[];rows=[];source_cache={};controls=[]
 old=PROJECT/'analysis_out/btrfs-mount-resume-20261023'
 seal=json.loads((HERE.parent/'btrfs_mount_resume_20261023/results.json').read_text())
 for p in manifest['profiles']:
  name=p['profile'];print('profile '+name,flush=True);root=p['source_root'];mode=p['mode']
  for s in p['sources'].values():assert sha(Path(s['path']))==s['sha256']
  if mode not in source_cache:
   texts={n:Path(s['path']).read_text() for n,s in p['sources'].items()}
   extracted=ex.extract_facts(texts['fs/btrfs/disk-io.c'],texts['fs/btrfs/super.c'],'open_ctree','btrfs_parse_options')
   assert extracted['status']=='limited_facts' and len(extracted['records'])==1
   candidate=extracted['records'][0]
   template=geom.derive_template(texts['fs/btrfs/ctree.h'],texts['include/asm-generic/unaligned.h'],texts['fs/btrfs/super.c'],candidate)
   source_cache[mode]={'extracted':extracted,'candidate':candidate,'template':template}
  src=source_cache[mode];defs={}
  for unit,selectors in [('disk-io',{'open_ctree':root+'/fs/btrfs/disk-io.c',src['candidate']['source_call']['name']:root+'/fs/btrfs/ctree.h','btrfs_sb':root+'/fs/btrfs/ctree.h'}),('super',{'btrfs_parse_options':root+'/fs/btrfs/super.c'})]:
   entry=p['preprocessed'][unit];i=Path(entry['path']);assert sha(i)==entry['sha256']
   extracted=extract_definitions(i.read_text(),selectors)
   defs.update(extracted)
  (OUT/(name+'-definitions.json')).write_text(json.dumps(defs,indent=2)+'\n')
  record={'revision':p['revision'],'profile':name,'page_size':p['page_size'],**{k:p['build_identity'][k] for k in ['image_sha256','config_sha256']},'candidate':src['candidate'],'template':src['template'],'compiled_definitions_verified':all(d['region_kind']=='definition' and d['source_selector_match']=='absolute_name_location' for d in defs.values())}
  summaries.append({'profile':name,'definitions':{k:{f:v[f] for f in ['name_location','sha256','mapped_token_sources','all_token_paths_match_name_location']} for k,v in defs.items()},'source':src})
  build=json.loads((old/name/'build.json').read_text());assert sha(Path(build['image']))==build['image_sha256'] and sha(old/name/'kernel.config')==build['config_sha256']
  runtime={'profile':name,'revision':build['revision'],**{k:build[k] for k in ['image_sha256','config_sha256']}}
  for sector in ([65536,4096] if p['page_size']==65536 else [4096]):
   d=old/name/f'sector{sector}'
   for file in ['boot.log','super.txt','tree.txt']:assert sha(d/file)==seal['artifact_sha256'][str((d/file).relative_to(old))]
   f=project(*[(d/file).read_text() for file in ['boot.log','super.txt','tree.txt']],requests=[2048,8192],sizes=[1024,6144,8192],context_id=name+'-'+str(sector))
   mapping={'source_field':src['candidate']['field'],'runtime_field':'sector_size','origin':'researcher_authored'}
   rows.append({'joined':join(record,runtime,f,mapping),'observation_checks':local_checks(f)})
   if not controls:
    trials=[]
    for key in ['revision','profile','image_sha256','config_sha256']:
     bad=copy.deepcopy(runtime);bad[key]='wrong';trials.append((key,record,bad,f,mapping))
    bad=copy.deepcopy(f);bad['page_size']=4096;trials.append(('page',record,runtime,bad,mapping))
    bad=copy.deepcopy(mapping);bad['source_field']='unregistered';trials.append(('field',record,runtime,f,bad))
    bad=copy.deepcopy(f);bad['cache_at_consumer']=4096;trials.append(('inverse_clamp_promotion',record,runtime,bad,mapping))
    bad=copy.deepcopy(record);bad['compiled_definitions_verified']=False;trials.append(('missing_compiled_definition',bad,runtime,f,mapping))
    for label,*args in trials:
     try:join(*args)
     except BindingError as e:controls.append({'name':label,'status':'rejected','reason':str(e)});continue
     raise AssertionError('control accepted '+label)
 result={'new_preprocess_commands':8,'new_kernel_builds':0,'new_boots':0,'replayed_mount_profiles':6,'replayed_files':36,'source_derivations':2,'configured_definitions':16,'profiles':summaries,'joined_records':rows,'negative_controls':controls,'independent_positive':0,'independent_normal':0,'full_core_connection':'insufficient_missing_runtime_cache_object_and_deadline'}
 for p,h in freeze.items():assert sha(PROJECT.parent/p)==h
 (HERE/'results.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'profiles':4,'joined':len(rows),'controls':len(controls),'cache_equality':'insufficient in all six','full_core_connection':result['full_core_connection']}))
if __name__=='__main__':
 try:main()
 except Exception:
  n=len(list(HERE.glob('failure*.txt')))+1;(HERE/f'failure{n}.txt').write_text(traceback.format_exc());raise
