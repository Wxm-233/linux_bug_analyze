"""Bounded raw-command audit; rules are explicitly researcher supplied."""
from pathlib import Path
import json,hashlib,collections
H=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
archive=read(H.parent/'cross_arch_smmu_source_20261013.json')
source_audit=[]
for key,text in read(H/'sources.json').items():
 path=key.split(':',1)[1]
 matches=[s for s in archive['sources'] if s['path']==path and s.get('text')==text]
 assert len(matches)==1,(key,len(matches))
 blob=hashlib.sha1(b'blob '+str(len(text.encode())).encode()+b'\0'+text.encode()).hexdigest()
 assert blob==matches[0]['blob']
 source_audit.append(dict(query=key,git_blob=blob,archived_revisions=matches[0]['revisions']))
rows=[]
for item in read(H/'raw_commands.json'):
 lines=item['stdout'].splitlines();assert int(lines[0])==len(lines)-1
 intervals=[];bad=[];ttl_bad=[];fields=[];g=1<<item['page_shift']
 for number,line in enumerate(lines[1:]):
  addr,ttl,num,scale,tg,leaf=map(int,line.split());assert leaf==int(item['leaf'])
  assert min(addr,ttl,num,scale,tg)>=0
  fields.append(dict(addr=addr,ttl=ttl,num=num,scale=scale,tg=tg,leaf=leaf))
  if item['range_feature']:
   assert tg==(item['page_shift']-10)//2
   if ttl==num==scale==0:bad.append(number)
   if not item['leaf'] and ttl!=0:ttl_bad.append(number)
   length=(num+1)*(1<<scale)*g
  else:length=g
  intervals.append((addr,addr+length))
 # Independent interval-union coverage; does not call the original assess().
 start=0x100000;end=start+item['pages']*g;cursor=start
 for a,b in sorted(intervals):
  if a>cursor:break
  cursor=max(cursor,b)
 covered=cursor>=end
 assert covered
 rows.append({k:v for k,v in item.items() if k!='stdout'}|dict(
  commands=fields,coverage='satisfied' if covered else 'violated',
  encoding='not_applicable' if not item['range_feature'] else ('violated' if bad else 'satisfied'),
  unknown_level='not_applicable' if not item['range_feature'] or item['leaf'] else ('violated' if ttl_bad else 'satisfied'),
  invalid_command_indices=bad,ttl_command_indices=ttl_bad,extra_pages=(cursor-end)//g,
  hardware_execution='insufficient',over_invalidation_safety='insufficient',authority='known fix explanation and source; hardware specification not independently closed'))
counts={}
for variant in sorted({x['variant'] for x in rows}):
 part=[x for x in rows if x['variant']==variant]
 counts[variant]=dict(combinations=len(part),coverage_satisfied=sum(x['coverage']=='satisfied' for x in part),encoding_violated=sum(x['encoding']=='violated' for x in part),unknown_level_violated=sum(x['unknown_level']=='violated' for x in part),overcoverage_combinations=sum(x['extra_pages']>0 for x in part))
save('source_audit.json',source_audit)
save('relation_audit.json',dict(scope='registered finite command model; not hardware certification',rows=rows,counts=counts))
save('audit_inputs.json',{p.name:sha(p) for p in [H/'audit.py',H/'sources.json',H/'raw_commands.json',H/'results.json']})
print(json.dumps(counts))
