from pathlib import Path,PurePosixPath
import argparse,json,hashlib,subprocess,datetime
HERE=Path(__file__).resolve().parent
h=lambda b:hashlib.sha256(b).hexdigest()
def git(*args):
 p=subprocess.run(['git','-C','/root/repos/linux',*args],capture_output=True,timeout=45)
 if p.returncode:raise RuntimeError(p.stderr.decode('utf-8','replace')[:1200])
 return p.stdout
p=argparse.ArgumentParser();p.add_argument('--phase',choices=['initial','supplement'],required=True);a=p.parse_args()
plan_path=HERE/(a.phase+'_material_plan.json');out=HERE/(a.phase+'_sources.json')
assert not out.exists(), 'Preserve first source collection'
plan=json.loads(plan_path.read_bytes());rows=[]
for case in plan['cases']:
 revision=case.get('parent',case.get('revision'));assert len(revision)==40
 for path in case['paths']:
  pure=PurePosixPath(path);assert not pure.is_absolute() and '..' not in pure.parts
  row={'case':case['case'],'revision':revision,'material_group':case['case']+'_parent','path':path,'status':'collection_error'}
  try:
   blob=git('rev-parse',revision+':'+path).decode().strip();raw=git('show',revision+':'+path)
   computed=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();assert computed==blob
   row.update(status='collected',git_blob=blob,sha256=h(raw),bytes=len(raw),text=raw.decode('utf-8'))
  except (RuntimeError,UnicodeError,AssertionError,subprocess.TimeoutExpired) as e:row['error']=str(e)
  rows.append(row)
result={'phase':a.phase,'collected_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'material_plan_sha256':h(plan_path.read_bytes()),'selection_sha256':h((HERE/'selection_pre.json').read_bytes()),'method_versions_sha256':h((HERE/'method_versions.json').read_bytes()),'semantic_layer':'unpreprocessed_original_parent_source','documents':rows,'child_messages_or_patches_read':0,'network_requests':0}
with out.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'phase':a.phase,'files':len(rows),'collected':sum(r['status']=='collected' for r in rows),'bytes':sum(r.get('bytes',0) for r in rows)}))
