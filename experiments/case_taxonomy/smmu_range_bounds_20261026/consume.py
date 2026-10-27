from pathlib import Path
import subprocess,json,hashlib
H=Path(__file__).resolve().parent;O=H.parent/'smmu_chain_20261026';inputs=json.loads((H/'results.json').read_text());rows=[];builds=[]
for version in ['old','fixed']:
 for shift in [12,14,16]:
  source=O/f'{version}_{shift}.c';s=source.read_text();assert 'if(argc!=7)' in s
  s=s.replace('if(argc!=7)','if(argc!=9)').replace('unsigned long start=1UL<<30,size=pages*PAGE_SIZE;','unsigned long start=strtoul(argv[7],0,0),size=strtoul(argv[8],0,0)-start; (void)pages;')
  p=H/f'{version}_{shift}_consume.c';p.write_text(s);exe=p.with_suffix('.bin')
  q=subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',f'-DPAGE_SHIFT={shift}',str(p),'-o',str(exe)],capture_output=True,text=True);builds.append(dict(source=p.name,parent_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),returncode=q.returncode,stderr=q.stderr));assert q.returncode==0,q.stderr
  for i,r in enumerate(inputs):
   if r['page_shift']!=shift:continue
   q=subprocess.run([str(exe),'0','0','1','0','0','1',str(r['callback_start']),str(r['callback_end'])],capture_output=True,text=True);assert q.returncode==0,q.stderr
   meta=list(map(int,q.stdout.splitlines()[0].split()[1:]));single=r['single_page_entry']
   assert meta[0]==(1 if single else 0) and meta[1]==(0 if single else 1)
   rows.append(dict(version=version,input=i,raw=q.stdout,smmu_route='range_command' if single else 'asid_all',scope='joined callback arguments, not live object identity; SMMU RIL1 BTM0 E2H0'))
(H/'consume_builds.json').write_text(json.dumps(builds,indent=2));(H/'consume_results.json').write_text(json.dumps(rows,indent=2));print('6 builds; 84 downstream executions; only 12 single-page cases use range commands')
