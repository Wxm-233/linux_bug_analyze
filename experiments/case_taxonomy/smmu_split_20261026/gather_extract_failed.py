from pathlib import Path
import re,json,subprocess,hashlib
H=Path(__file__).resolve().parent;E=H.parent
header=E/'smmu_binding_20261026/source/include__linux__iommu.h';driver=E/'smmu_chain_20261026/source/00_drivers__iommu__arm__arm-smmu-v3__arm-smmu-v3.c';manifest=[]
def fun(p,n):
 s=p.read_text();m=re.search(r'^(?:static inline(?: void)?\s*\n|static (?:inline )?(?:bool|void) )'+n+r'\(',s,re.M);assert m,n
 a=m.start();b=s.index('{',a)+1;d=1
 while d:d+=(s[b]=='{')-(s[b]=='}');b+=1
 text=s[a:b];manifest.append(dict(source=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),name=n,line=s[:a].count('\n')+1));return text
head=r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <limits.h>
#include <assert.h>
struct list_head {struct list_head *next,*prev;};
#define LIST_HEAD_INIT(n) {&(n),&(n)}
struct iommu_iotlb_gather {unsigned long start,end;size_t pgsize;bool queued;struct list_head freelist;};
struct iommu_domain;struct ops {void(*iotlb_sync)(struct iommu_domain*,struct iommu_iotlb_gather*);};
struct iommu_domain {struct ops*ops;};struct arm_smmu_domain {struct iommu_domain domain;};
#define to_smmu_domain(p) ((struct arm_smmu_domain*)(p))
static int emitted;
static void arm_smmu_tlb_inv_range_domain(unsigned long a,size_t n,size_t g,bool leaf,struct arm_smmu_domain*d){(void)d;assert(leaf);emitted++;printf("RANGE %lu %zu %zu %d\n",a,n,g,leaf);}
'''
code=head+fun(driver,'arm_smmu_iotlb_sync')+'\n'
for n in ['iommu_iotlb_gather_init','iommu_iotlb_sync','iommu_iotlb_gather_is_disjoint','iommu_iotlb_gather_add_range','iommu_iotlb_gather_add_page']:code+=fun(header,n)+'\n'
code+=fun(driver,'arm_smmu_tlb_inv_page_nosync')+r'''
int main(int argc,char**argv){assert(argc==2);struct ops ops={arm_smmu_iotlb_sync};struct arm_smmu_domain d={.domain={.ops=&ops}};struct iommu_iotlb_gather g;unsigned long a,n;iommu_iotlb_gather_init(&g);g.queued=atoi(argv[1]);while(scanf("%lu %lu",&a,&n)==2)arm_smmu_tlb_inv_page_nosync(&g,a,n,&d);printf("BEFORE_FINAL %d %lu %lu %zu\n",emitted,g.start,g.end,g.pgsize);iommu_iotlb_sync(&d.domain,&g);assert(g.start==ULONG_MAX&&!g.pgsize&&!g.end);printf("AFTER_FINAL %d\n",emitted);return 0;}
'''
(H/'gather.c').write_text(code);exe=H/'gather.bin';p=subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(H/'gather.c'),'-o',str(exe)],capture_output=True,text=True)
(H/'gather_build.json').write_text(json.dumps(dict(code=p.returncode,stderr=p.stderr,functions=manifest),indent=2));assert p.returncode==0,p.stderr
rows=[]
for r in json.loads((H/'results.json').read_text()):
 if r['coherent']:continue
 adds=[list(map(int,l.split()[1:])) for l in r['stdout'].splitlines() if l.startswith('ADD ')]
 p=subprocess.run([str(exe),str(r['queued'])],input=''.join(f'{a} {n}\n' for a,n in adds),capture_output=True,text=True,check=True)
 before=next(l.split() for l in p.stdout.splitlines() if l.startswith('BEFORE_FINAL'));assert before[1]=='0'
 ranges=[list(map(int,l.split()[1:])) for l in p.stdout.splitlines() if l.startswith('RANGE ')]
 assert len(ranges)==bool(adds)
 if adds:assert ranges==[[adds[0][0],sum(n for a,n in adds),adds[0][1],1]]
 rows.append(dict(shift=r['shift'],mode=r['mode'],queued=r['queued'],input=adds,stdout=p.stdout))
controls=[]
for name,seq in [('gap',[(4096,4096),(16384,4096)]),('granule_change',[(4096,4096),(8192,8192)])]:
 p=subprocess.run([str(exe),'0'],input=''.join(f'{a} {n}\n' for a,n in seq),capture_output=True,text=True,check=True)
 assert 'BEFORE_FINAL 1 ' in p.stdout and 'AFTER_FINAL 2' in p.stdout
 controls.append(dict(name=name,synthetic=True,stdout=p.stdout))
(H/'gather_results.json').write_text(json.dumps(dict(cases=rows,controls=controls),indent=2));print('1 gather build / 30 derived cases + 2 boundary controls passed')
