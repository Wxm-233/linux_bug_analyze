"""Check raw offsets under explicit base/maintenance-unit assumptions."""
from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
archive=read(H.parent/'cross_arch_virtio_source_20261013.json');pins=[]
for query,text in read(H/'sources.json').items():
 path=query.split(':',1)[1];matches=[s for s in archive['sources'] if s['path']==path and s.get('text')==text]
 assert len(matches)==1,query
 blob=hashlib.sha1(b'blob '+str(len(text.encode())).encode()+b'\0'+text.encode()).hexdigest()
 assert blob==matches[0]['blob']
 pins.append(dict(query=query,blob=blob,revisions=matches[0]['revisions']))
anchors=[]
for path,needle in [('Documentation/core-api/dma-api-howto.rst','This protects both the head'),('drivers/virtio/virtio_input.c','sg_init_one(sg, evtbuf, sizeof(*evtbuf));')]:
 for s in archive['sources']:
  if s['path']!=path:continue
  text=s['text'];blob=hashlib.sha1(b'blob '+str(len(text.encode())).encode()+b'\0'+text.encode()).hexdigest();assert blob==s['blob']
  lines=text.splitlines();hits=[i+1 for i,l in enumerate(lines) if needle in l];assert hits
  anchors.append(dict(path=path,blob=blob,revisions=s['revisions'],lines=hits,needle=needle))
rows=[];controls=[];saved=read(H/'results.json')['cases']
for item in read(H/'raw_layouts.json'):
 variant,count,align=item['program'].rsplit('-',2);count=int(count);align=int(align)
 p,b,e,n,size,old_start,old_end=map(int,item['stdout'].split())
 assert 0<p<=b<e<=n<size and e-b==count*8
 # Compare maintenance units containing the nearest occupied boundary bytes.
 def isolated(base):return ((base+p-1)//align!=(base+b)//align,(base+e-1)//align!=(base+n)//align)
 start,end=isolated(0);assert (start,end)==(bool(old_start),bool(old_end))
 match=[x for x in saved if x['variant']==variant and x['events']==count and x['dma_cache_alignment']==align];assert len(match)==1
 assert (start,end)==(match[0]['start_isolated'],match[0]['end_isolated'])
 rows.append(dict(variant=variant,events=count,unit=align,base_residue_assumed=0,start='satisfied' if start else 'violated',end='satisfied' if end else 'violated',actual_base='insufficient',actual_dma_target='insufficient',ownership_interval='insufficient',whole_path='insufficient'))
 if variant=='fixed':
  bad=[r for r in range(align) if not all(isolated(r))]
  assert 0 not in bad
  controls.append(dict(events=count,unit=align,synthetic_base_residues=align,failing_residue_count=len(bad),first_failure=bad[0] if bad else None,meaning='counterfactual assumption sensitivity; misaligned instances are not valid C allocations or observed Linux faults'))
save('source_audit.json',dict(layout_sources=pins,semantic_anchors=anchors))
save('relation_audit.json',dict(rows=rows,base_assumption_controls=controls,not_hardware_execution=True))
save('audit_inputs.json',{p.name:sha(p) for p in [H/'audit.py',H/'raw_layouts.json',H/'sources.json',H/'results.json']})
print(json.dumps(dict(layouts=len(rows),synthetic_base_residues=sum(x['synthetic_base_residues'] for x in controls),base_controls=controls)))
