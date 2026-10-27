from pathlib import Path
import subprocess,json,hashlib
H=Path(__file__).resolve().parent;old=H.parent/'smmu_range_bounds_20261026/origin.c';s=old.read_text()
assert 'assert(argc==4)' in s and '__flush_tlb_range(&v,start,end,PAGE_SIZE,false,0)' in s
s=s.replace('assert(argc==4)','assert(argc==5)').replace('__flush_tlb_range(&v,start,end,PAGE_SIZE,false,0)','__flush_tlb_range(&v,start,end,strtoul(argv[4],0,0),false,0)')
(H/'stride.c').write_text(s);rows=[];builds=[]
for shift in [12,14,16]:
 exe=H/f'stride_{shift}.bin';p=subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',f'-DPAGE_SHIFT={shift}',str(H/'stride.c'),'-o',str(exe)],capture_output=True,text=True);builds.append(dict(shift=shift,code=p.returncode,stderr=p.stderr));assert p.returncode==0,p.stderr
 for cap in [0,1]:
  for blocks in [1,31]:
   stride=1<<(2*shift-3);pages=blocks*(1<<(shift-3));p=subprocess.run([str(exe),str(cap),str(pages),'0',str(stride)],capture_output=True,text=True,timeout=15);assert p.returncode==0
   start,end,a,b=map(int,p.stdout.split());aligned_start=start&~(stride-1);aligned_end=(end+stride-1)&~(stride-1);rounded_pages=(aligned_end-aligned_start)>>shift
   full=rounded_pages>=1<<21 or (not cap and aligned_end-aligned_start>=((1<<shift)//8)*stride)
   assert (a,b)==((0,(1<<64)-1) if full else (aligned_end,aligned_end))
   rows.append(dict(shift=shift,cpu_range=cap,blocks=blocks,stride=stride,raw=p.stdout,full=full,scope='block-stride shape; no actual hugepage mapping'))
(H/'stride_results.json').write_text(json.dumps(dict(parent_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),builds=builds,cases=rows),indent=2));print('3 builds and 12 block-stride executions passed')
