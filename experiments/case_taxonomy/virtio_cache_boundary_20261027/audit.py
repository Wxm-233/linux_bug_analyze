from pathlib import Path
import json,hashlib,copy,subprocess
H=Path(__file__).resolve().parent
def assess(row):
 try:
  if row.get('code')!=0:return dict(status='rejected',reason='execution')
  st=row['start'];n=row['size'];dmin=row['dmin'];cwg=row['cwg'];wa=row['workaround'];action=row['action'];direction=row['direction']
  if not all(type(x) is int for x in [st,n,dmin,cwg,wa,action,direction]) or n<=0 or st<0 or st+n>2**64 or dmin not in (4,5) or cwg not in (4,5) or wa not in (0,1) or action not in (0,1) or direction not in (1,2):return dict(status='rejected',reason='unsupported_input')
  line=4<<dmin;end=st+n;lo=(st//line)*line;hi=(end//line)*line
  expected=[]
  if action==0:
   expected=[[3 if wa else 1,a] for a in range(lo,end,line)]+[[4,0]]
  elif direction!=1:
   if end%line:expected.append([3,hi])
   expected.append([3 if st%line else 2,lo]);expected.extend([2,a] for a in range(lo+line,hi,line));expected.append([4,0])
  actual=[list(map(int,s.split())) for s in row['stdout'].splitlines()]
  if actual!=expected:return dict(status='rejected',reason='operation_or_sequence')
  lines={a for op,a in actual if op!=4};wanted=set(range(lo,end,line)) if expected else set()
  if lines!=wanted:return dict(status='rejected',reason='range_coverage')
  partial={a for a in lines if a<st or a+line>end}
  if action==1 and direction!=1 and not partial<={a for op,a in actual if op==3}:return dict(status='rejected',reason='partial_line_not_cleaned')
  return dict(status='observed_instrumented_sequence',line=line,operated_lines=sorted(lines),partial_lines=sorted(partial),duplicate_addresses=len([a for op,a in actual if op!=4])-len(lines),hardware_effect='insufficient')
 except (KeyError,ValueError,TypeError):return dict(status='rejected',reason='invalid_record')

if __name__=='__main__':
 rows=json.loads((H/'results.json').read_text());audits=[dict(input_index=i,**assess(r)) for i,r in enumerate(rows)]
 if any(a['status']=='rejected' for a in audits):raise RuntimeError([a for a in audits if a['status']=='rejected'])
 # A metadata-only mutation of CWG must leave this primitive's observed ops unchanged.
 groups={}
 for r in rows:
  key=tuple(r[k] for k in ['workaround','dmin','action','direction','start','size']);groups.setdefault(key,[]).append(r)
 if not all(len(g)==2 and g[0]['stdout']==g[1]['stdout'] for g in groups.values()):raise RuntimeError('CWG dependence')
 base=next(r for r in rows if r['action']==1 and r['direction']==2 and r['size']==8 and r['start']==0x10008 and r['dmin']==4 and r['cwg']==5 and r['workaround']==0)
 controls=[]
 for name in ['missing_duplicate','wrong_cwg_stride','partial_ivac_only','missing_dsb','changed_object_address','empty_interval']:
  r=copy.deepcopy(base);ls=r['stdout'].splitlines()
  if name=='missing_duplicate':ls=ls[1:]
  elif name=='wrong_cwg_stride':r['dmin']=5;r['start']=0x10040;ls=['3 65600','3 65600','4 0']
  elif name=='partial_ivac_only':ls=['2 65536','4 0']
  elif name=='missing_dsb':ls=ls[:-1]
  elif name=='changed_object_address':r['start']+=128
  else:r['size']=0
  r['stdout']='\n'.join(ls)+'\n';out=assess(r)
  if out['status']!='rejected':raise RuntimeError(name)
  controls.append(dict(name=name,input=r,result=out))
 # This is an explicit conditional bridge from historical HOST layout to
 # instrumented address traces, never an actual ARM64 object-layout witness.
 lp=H.parent/'virtio_method_20261026/raw_layouts.json';layouts=json.loads(lp.read_text());bridges=[];trace_rows=[]
 for variant in ['old','fixed']:
  for dmin in [4,5]:
   line=4<<dmin;r=next(r for r in layouts if r['program']==f'{variant}-64-{line}');nums=list(map(int,r['stdout'].split()));start,end,lock=nums[1:4]
   for edge,off in [('first',start),('last',end-8)]:
    for wa in [0,1]:
     for action in [0,1]:
      a=0x10000+off;q=subprocess.run(['qemu-aarch64',str(H/f'boundary_{wa}.bin'),str(action),str(dmin),'5',str(a),'8','2'],capture_output=True,text=True,timeout=15)
      rec=dict(variant=variant,edge=edge,workaround=wa,dmin=dmin,cwg=5,line=line,action=action,direction=2,start=a,size=8,code=q.returncode,stdout=q.stdout,stderr=q.stderr)
      result=assess(rec)
      if result['status']=='rejected':raise RuntimeError(rec)
      trace_rows.append(rec)
      outside=[x for x in result['operated_lines'] if x<0x10000+start or x+line>0x10000+end]
      lock_hit=any(x<=0x10000+lock<x+line for x in result['operated_lines'])
      bridges.append(dict(trace_index=len(trace_rows)-1,variant=variant,edge=edge,line=line,action=action,workaround=wa,group_start=start,group_end=end,lock=lock,lines_crossing_group=outside,lock_line_hit=lock_hit,host_layout_base_assumed=0x10000,actual_ARM64_ABI='insufficient',actual_backend='insufficient',ownership_window='insufficient',whole_path='insufficient'))
 (H/'audit.json').write_text(json.dumps(dict(rows=audits,cwg_equal_pairs=len(groups)),indent=2));(H/'controls.json').write_text(json.dumps(controls,indent=2));(H/'layout_trace_results.json').write_text(json.dumps(trace_rows,indent=2));(H/'layout_bridge.json').write_text(json.dumps(dict(host_layout_source_sha256=hashlib.sha256(lp.read_bytes()).hexdigest(),rows=bridges),indent=2))
 print(f'{len(rows)} general audits;{len(groups)} CWG pairs;6 altered traces rejected;{len(trace_rows)} conditional host-layout traces')
