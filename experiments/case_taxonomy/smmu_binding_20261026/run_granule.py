from pathlib import Path
import importlib.util,subprocess,json,hashlib
H=Path(__file__).resolve().parent;S=H.parent/'smmu_chain_20261026/source'
sp=importlib.util.spec_from_file_location('probe',H.parent/'smmu_range_probe.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
source=(S/'06_drivers__iommu__io-pgtable-arm.c').read_text();body=m.function(source,'static void arm_lpae_restrict_pgsizes(')
pre='''#include <stdio.h>
#include <stdlib.h>
#define PAGE_SIZE (1UL<<PAGE_SHIFT)
#define PAGE_MASK (~(PAGE_SIZE-1))
#define SZ_4K (1UL<<12)
#define SZ_16K (1UL<<14)
#define SZ_64K (1UL<<16)
#define SZ_2M (1UL<<21)
#define SZ_1G (1UL<<30)
#define SZ_32M (1UL<<25)
#define SZ_512M (1UL<<29)
#define __ffs(v) __builtin_ctzl(v)
#define __fls(v) (63-__builtin_clzl(v))
#define min(a,b) ((a)<(b)?(a):(b))
struct io_pgtable_cfg {unsigned long pgsize_bitmap;unsigned int ias,oas;};
'''
main='''int main(int argc,char **argv){if(argc!=3)return 2;struct io_pgtable_cfg c={.pgsize_bitmap=strtoul(argv[1],0,0),.ias=52,.oas=strtoul(argv[2],0,0)};arm_lpae_restrict_pgsizes(&c);printf("%lu %u %u\\n",c.pgsize_bitmap,c.ias,c.oas);return 0;}'''
rows=[];builds=[]
for shift in [12,14,16]:
 p=H/f'granule_{shift}.c';p.write_text(pre+body+'\n'+main);exe=H/f'granule_{shift}.bin'
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',f'-DPAGE_SHIFT={shift}',str(p),'-o',str(exe)],check=True)
 builds.append(dict(file=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
 inputs=[(0,48,'empty')]
 blocks=sum(1<<x for x in [21,25,29,30,42])
 for subset in range(8):
  bitmap=blocks|sum(1<<g for bit,g in enumerate([12,14,16]) if subset&(1<<bit))
  for oas in [48,52]:inputs.append((bitmap,oas,'capability_combination'))
 for bitmap,oas,kind in inputs:
  out=subprocess.check_output([str(exe),str(bitmap),str(oas)],text=True);value,ias,afteroas=map(int,out.split());supported=bool(bitmap&(1<<shift))
  minimum=(value&-value).bit_length()-1 if value else None
  assert value&~bitmap==0
  if supported:assert minimum==shift and value&(1<<shift)
  if not bitmap:assert value==0
  rows.append(dict(cpu_shift=shift,input_bitmap=bitmap,input_oas=oas,kind=kind,output_bitmap=value,output_ias=ias,output_oas=afteroas,minimum_shift=minimum,sva_page_gate=supported,full_sva_eligibility='insufficient',stdout=out))
result=dict(scope='original restrict_pgsizes function, test types/macros; no allocator/CD/platform execution',function_sha256=hashlib.sha256(body.encode()).hexdigest(),builds=builds,rows=rows,summary=dict(combinations=len(rows),page_gate_pass=sum(r['sva_page_gate'] for r in rows),page_gate_fail=sum(not r['sva_page_gate'] for r in rows)))
with (H/'granule_results.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result['summary']))
