"""Object/state verifier for the registered ordinary split two-buffer harness.

Trace statements are observations inserted at harness boundaries. They are not
hardware barriers, device DMA effects, or a generic kernel trace format.
"""
import json
from pathlib import Path

class Reject(Exception):pass
def need(ok,why):
 if not ok:raise Reject(why)

def assess(row):
 try:
  need(isinstance(row,dict) and row.get('code')==0,'execution')
  route=row.get('route');need(type(route) is int and route in (0,1,2),'route')
  mode=row.get('mode');need(type(mode) is int and mode in range(9),'mode')
  need(type(row.get('indirect')) is int and row['indirect'] in (0,1),'feature')
  need(isinstance(row.get('stdout'),str),'text')
  states=['absent','absent'];generations=[0,0];attempt=None;free=0 if mode==2 else 4
  publications=reads=maps=unmaps=barriers=attempts=0;errors=[];final=False;broken=mode==3
  for line in row['stdout'].splitlines():
   p=line.split();need(bool(p) and not final,'empty/after_final');tag=p[0]
   if tag=='ATTEMPT':
    need(len(p)==5,'attempt_arity');phase,i,f,idx=map(int,p[1:]);need(i in (0,1),'object')
    need(attempt is None and states[i] in ('absent','cpu','failed'),'attempt_state')
    need(f==free and idx==publications,'attempt_counts')
    attempt=dict(phase=phase,i=i,prior=states[i],map=None,barrier=False,publish=False);attempts+=1
   elif tag in ('MAP_OK','MAP_FAIL','BYPASS'):
    need(attempt is not None and attempt['map'] is None,'map_without_attempt')
    need(not broken and free>0,'map_after_early_failure')
    if tag=='BYPASS':
     need(len(p)==2 and route==0 and int(p[1])==attempt['i'],'bypass_binding')
    else:
     need(len(p)==3 and route!=0 and list(map(int,p[1:]))==[attempt['phase'],attempt['i']],'map_binding');maps+=1
    attempt['map']=tag
   elif tag=='BEFORE_PUBLISH':
    need(attempt is not None and len(p)==4,'barrier')
    need(list(map(int,p[1:]))==[attempt['phase'],attempt['i'],publications],'barrier_binding')
    need(attempt['map'] in ('MAP_OK','BYPASS') and not attempt['barrier'],'barrier_without_map')
    attempt['barrier']=True;barriers+=1
   elif tag=='PUBLISHED':
    need(attempt is not None and len(p)==4,'publish')
    need(list(map(int,p[1:]))==[attempt['phase'],attempt['i'],publications+1],'publish_binding')
    need(attempt['barrier'] and not attempt['publish'],'publish_before_barrier')
    attempt['publish']=True;states[attempt['i']]='published';generations[attempt['i']]+=1;publications+=1;free-=1
   elif tag=='ADD_RETURN':
    need(attempt is not None and len(p)==4,'return')
    phase,i,ret=map(int,p[1:]);need([phase,i]==[attempt['phase'],attempt['i']],'return_binding')
    if ret==0:need(attempt['publish'],'success_without_publication')
    else:
     need(not attempt['barrier'] and not attempt['publish'],'failed_publication')
     need((ret==-5 and broken and attempt['map'] is None) or (ret==-28 and free==0 and not broken and attempt['map'] is None) or (ret==-12 and attempt['map']=='MAP_FAIL'),'error_cause')
     states[i]='failed';errors.append(dict(phase=phase,object=i,result=ret))
    attempt=None
   elif tag=='SIM_USED':
    need(len(p)==3,'used');i,head=map(int,p[1:]);need(i in (0,1) and head in range(4) and states[i]=='published' and attempt is None,'used_state');states[i]='used'
   elif tag=='UNMAP':
    need(len(p)==2 and route!=0 and attempt is None,'unmap');i=int(p[1]);need(i in (0,1) and states[i]=='used','unmap_state');states[i]='unmapped';unmaps+=1
   elif tag=='TOKEN':
    need(len(p)==3,'token');i,length=map(int,p[1:]);need(i in (0,1) and length==8 and states[i]==('unmapped' if route else 'used'),'token_binding');states[i]='token';free+=1
   elif tag=='CPU_READ':
    need(len(p)==2,'read');i=int(p[1]);need(i in (0,1) and states[i]=='token','read_before_token');states[i]='cpu';reads+=1
   elif tag=='BROKEN_IN_CALLBACK':broken=True
   elif tag=='AFTER_FILL' or tag=='AFTER_RECV':
    need(len(p)==4 and int(p[3])==free and attempt is None,'snapshot')
   elif tag=='FINAL':
    need(len(p)==9 and attempt is None,'final');a,m,u,r,k,b,g0,g1=map(int,p[1:]);need([a,m,u,r,b,g0,g1]==[attempts,maps,unmaps,reads,barriers,*generations],'final_counts');need(k>=0,'kick_count');final=True
   elif tag in ('LOCK','UNLOCK','RMB','EVENT_STORE','NO_TOKEN','KICK','MANUAL_RECOVERY'):pass
   else:raise Reject('unregistered_tag')
  need(final,'missing_final')
  return dict(status='observed_object_publication_recycle',reads=reads,publications=publications,errors=errors,final_states=states,cpu_visibility='insufficient',device_effect='insufficient',whole_path='insufficient')
 except (Reject,ValueError,TypeError,KeyError,IndexError) as e:return dict(status='rejected',reason=str(e))

if __name__=='__main__':
 import copy
 h=Path(__file__).resolve().parent;rows=json.loads((h/'results.json').read_text())
 audit=[dict(mode=r['mode'],route=r['route'],indirect=r['indirect'],**assess(r)) for r in rows]
 if any(a['status']=='rejected' for a in audit):raise RuntimeError([a for a in audit if a['status']=='rejected'])
 base=next(r for r in rows if r['mode']==0 and r['route']==1 and r['indirect']==1)
 controls=[]
 for name in ['publish_before_barrier','wrong_token_object','missing_unmap','reuse_before_completion','failure_after_publish','missing_final']:
  r=copy.deepcopy(base);ls=r['stdout'].splitlines()
  if name=='publish_before_barrier':
   a=ls.index('BEFORE_PUBLISH 0 0 0');b=ls.index('PUBLISHED 0 0 1');ls[a],ls[b]=ls[b],ls[a]
  elif name=='wrong_token_object':ls[ls.index('TOKEN 0 8')]='TOKEN 1 8'
  elif name=='missing_unmap':ls.remove('UNMAP 0')
  elif name=='reuse_before_completion':ls.insert(ls.index('SIM_USED 0 0'),'ATTEMPT 1 0 2 2')
  elif name=='failure_after_publish':ls[ls.index('ADD_RETURN 0 0 0')]='ADD_RETURN 0 0 -12'
  else:ls=ls[:-1]
  r['stdout']='\n'.join(ls)+'\n';result=assess(r)
  if result['status']!='rejected':raise RuntimeError(name)
  controls.append(dict(name=name,input=r,result=result))
 (h/'audit.json').write_text(json.dumps(audit,indent=2));(h/'controls.json').write_text(json.dumps(controls,indent=2))
 print('54 object/publication audits pass;6 altered traces rejected')
