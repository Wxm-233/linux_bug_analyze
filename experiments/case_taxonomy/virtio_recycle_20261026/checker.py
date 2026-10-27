"""Bounded trace verifier for this split/non-in-order, two-token harness only."""
def assess(row):
 if row.get('code') != 0 or row.get('map_api') not in (0,1):
  return {'status':'invalid_trace'}
 lines=row['stdout'].splitlines(); objects={}; reads=[]; failures=[]
 for line in lines:
  p=line.split()
  if not p: continue
  if p[0]=='UNMAP':
   i=int(p[1])
   if not row['map_api'] or i in objects:return {'status':'invalid_order'}
   objects[i]='unmapped'
  elif p[0]=='TOKEN':
   i=int(p[1])
   if row['map_api'] and objects.get(i)!='unmapped':return {'status':'invalid_order'}
   if not row['map_api'] and i in objects:return {'status':'invalid_order'}
   objects[i]='token'
  elif p[0]=='CPU_READ':
   i=int(p[1])
   if objects.get(i)!='token':return {'status':'invalid_order'}
   objects[i]='read';reads.append(i)
  elif p[0]=='ADD':
   i=int(p[1]);ret=int(p[2])
   if objects.get(i)!='read':return {'status':'invalid_order'}
   objects[i]='add_returned'
   if ret: failures.append({'object':i,'return':ret})
 if any(v!='add_returned' for v in objects.values()):return {'status':'incomplete_trace'}
 if not lines or not lines[-1].startswith('FINAL '):return {'status':'incomplete_trace'}
 return {'status':'observed_local_order' if reads else 'no_consumption',
         'objects_read':reads,'requeue_failures':failures,
         'cpu_visibility':'insufficient','device_ownership':'insufficient',
         'whole_path':'insufficient','scope':'registered_harness_only'}

if __name__=='__main__':
 from pathlib import Path
 import json,copy
 h=Path(__file__).resolve().parent
 rows=json.loads((h/'results.json').read_text())
 audits=[dict(mode=r['mode'],map_api=r['map_api'],length=r['length'],**assess(r)) for r in rows]
 if any(a['status'] not in ('observed_local_order','no_consumption') for a in audits):raise RuntimeError('audit failed')
 base=next(r for r in rows if r['mode']==0 and r['map_api']==1 and r['length']==8)
 controls=[]
 for name in ['early_read','missing_add','wrong_object','bypass_with_unmap']:
  r=copy.deepcopy(base)
  if name=='early_read':
   ls=r['stdout'].splitlines();a=ls.index('UNMAP 0');b=next(i for i,l in enumerate(ls) if l.startswith('CPU_READ 0'));ls[a],ls[b]=ls[b],ls[a];r['stdout']='\n'.join(ls)+'\n'
  elif name=='missing_add':r['stdout']='\n'.join(l for l in r['stdout'].splitlines() if not l.startswith('ADD 0'))+'\n'
  elif name=='wrong_object':r['stdout']=r['stdout'].replace('TOKEN 0 8','TOKEN 3 8')
  else:r['map_api']=0
  out=assess(r)
  if out['status'] in ('observed_local_order','no_consumption'):raise RuntimeError(name)
  controls.append(dict(name=name,input=r,result=out))
 (h/'audit.json').write_text(json.dumps(audits,indent=2))
 (h/'controls.json').write_text(json.dumps(controls,indent=2))
 print('54 local trace audits; 4 altered trace controls rejected')
