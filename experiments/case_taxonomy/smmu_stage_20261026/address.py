"""New address contrasts under explicit conditional S1 function-test scope."""
from pathlib import Path
import subprocess,json,hashlib
H=Path(__file__).resolve().parent;OLD=H.parent/'smmu_chain_20261026'
rows=[];builds=[]
encoded=OLD/'cmd_build_projection.bin';manifest=json.loads((OLD/'encoding_results.json').read_text());assert hashlib.sha256(encoded.read_bytes()).hexdigest()==manifest['binary_sha256']
for version in ['old','fixed']:
 text=(OLD/f'{version}_12.c').read_text()
 assert 'if(argc!=7)' in text and 'unsigned long start=1UL<<30' in text
 text=text.replace('if(argc!=7)','if(argc!=8)').replace('unsigned long start=1UL<<30','unsigned long start=strtoul(argv[7],0,0)')
 p=H/f'{version}_address.c';p.write_text(text);exe=H/f'{version}_address.bin'
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-DPAGE_SHIFT=12',str(p),'-o',str(exe)],check=True)
 builds.append(dict(source=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
 for pages in [1,31,33,65]:
  start=0x7f1234567000;assert start%4096==0 and start%(1<<21)!=0
  out=subprocess.check_output([str(exe),'0',str(pages),'1','0','0','1',hex(start)],text=True)
  commands=[list(map(int,l.split()[1:])) for l in out.splitlines()[1:]]
  words=subprocess.run([str(encoded)],input=''.join(' '.join(map(str,c))+'\n' for c in commands),capture_output=True,text=True,check=True).stdout
  spans=[];bad=0
  for line in words.splitlines():
   w0,w1=(int(x,16) for x in line.split());num=(w0>>12)&31;scale=(w0>>20)&31;ttl=(w1>>8)&3;tg=(w1>>10)&3;addr=w1&(((1<<64)-1)^4095)
   assert tg==1;size=(num+1)*(1<<scale)*4096;spans.append([addr,addr+size]);bad+=ttl==num==scale==0
  cursor=start
  for a,b in spans:assert a==cursor;cursor=b
  assert cursor>=start+pages*4096
  assert bool(bad)==(version=='old' and pages!=31)
  rows.append(dict(version=version,pages=pages,start=hex(start),raw=out,words=words,intervals=spans,extra_bytes=cursor-(start+pages*4096),reserved_commands=bad,scope='synthetic callback S1 shape, not real mm/VMA mapping'))
with (H/'address_results.json').open('x') as f:json.dump(dict(builds=builds,projection_binary_sha256=manifest['binary_sha256'],cases=rows,condition='logical S1 label in earlier simplified harness, PAGE_SHIFT12, RIL1, BTM0, E2H0; not actual domain lifetime'),f,indent=2)
print('8 new non-block-aligned address cases; decoded-word coverage and reserved triples checked.')
