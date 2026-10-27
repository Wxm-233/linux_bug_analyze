from pathlib import Path
import re,json,hashlib,subprocess
H=Path(__file__).resolve().parent;O=H.parent/'virtio_dma_chain_20261026/source';manifest=[]
def fun(path,n):
 s=path.read_text();m=re.search(r'^(?:static inline )?(?:void|dma_addr_t) '+n+r'\([^;{]*\)\s*\{',s,re.M)
 if not m:raise RuntimeError(n)
 a=m.start();b=m.end();d=1
 while d:d+=(s[b]=='{')-(s[b]=='}');b+=1
 t=s[a:b];manifest.append(dict(file=path.name,name=n,line=s[:a].count('\n')+1,sha256=hashlib.sha256(t.encode()).hexdigest(),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest()));return t
base=(H/'boundary.c').read_text().split('int main(')[0]
head=r'''
#include <stdbool.h>
typedef uint64_t dma_addr_t;
struct device {bool force,coherent;uint64_t *dma_mask,bus_dma_limit;};struct io_tlb_pool {int unused;};
#define DMA_MAPPING_ERROR (~0ULL)
#define DMA_ATTR_MMIO 1
#define DMA_ATTR_SKIP_CPU_SYNC 2
#define unlikely(x) (x)
#define dev_WARN_ONCE(...) ((void)0)
static void mark(unsigned kind,uint64_t addr){trace[ntrace][0]=kind;trace[ntrace++][1]=addr;}
static bool is_swiotlb_force_bounce(struct device*d){return d->force;}
static bool is_swiotlb_active(struct device*d){(void)d;return true;}
static bool dev_is_dma_coherent(struct device*d){return d->coherent;}
static bool dma_capable(struct device*d,dma_addr_t a,size_t n,bool ram){(void)d;(void)a;(void)n;(void)ram;return true;}
static bool dma_kmalloc_needs_bounce(struct device*d,size_t n,enum dma_data_direction dir){(void)d;assert(n==8&&dir==DMA_FROM_DEVICE);return false;}
static dma_addr_t phys_to_dma(struct device*d,phys_addr_t a){(void)d;return a;}
static phys_addr_t dma_to_phys(struct device*d,dma_addr_t a){(void)d;return a;}
static dma_addr_t phys_to_dma_unencrypted(struct device*d,phys_addr_t a){(void)d;return a;}
static void arch_sync_dma_for_cpu_all(void){}
static void arch_dma_mark_clean(phys_addr_t a,size_t n){(void)a;(void)n;}
static void trace_swiotlb_bounced(struct device*d,dma_addr_t a,size_t n){(void)d;assert(a==0x10008&&n==8);}
static phys_addr_t swiotlb_tbl_map_single(struct device*d,phys_addr_t a,size_t n,unsigned align,enum dma_data_direction dir,unsigned long attrs){(void)d;assert(a==0x10008&&n==8&&align==0&&dir==DMA_FROM_DEVICE&&!attrs);mark(5,0x50008);return 0x50008;}
static struct io_tlb_pool *swiotlb_find_pool(struct device*d,phys_addr_t a){(void)d;(void)a;abort();}
static void __swiotlb_tbl_unmap_single(struct device*d,phys_addr_t a,size_t n,enum dma_data_direction dir,unsigned long attrs,struct io_tlb_pool*p){(void)d;(void)a;(void)n;(void)dir;(void)attrs;(void)p;abort();}
static void swiotlb_sync_single_for_cpu(struct device*d,phys_addr_t a,size_t n,enum dma_data_direction dir){(void)d;assert(n==8&&dir==DMA_FROM_DEVICE);if(a==0x50008)mark(6,0x10008);else assert(a==0x10008);}
static void swiotlb_tbl_unmap_single(struct device*d,phys_addr_t a,size_t n,enum dma_data_direction dir,unsigned long attrs){(void)d;assert(n==8&&dir==DMA_FROM_DEVICE&&attrs==DMA_ATTR_SKIP_CPU_SYNC);if(a==0x50008)mark(7,a);else assert(a==0x10008);}
'''
tail=r'''
int main(int argc,char**argv){assert(argc==4);int bounced=atoi(argv[1]),coherent=atoi(argv[2]),dmin=atoi(argv[3]);ctr_fixture=((uint64_t)dmin<<16)|(5ULL<<24);uint64_t mask=~0ULL;struct device d={.force=bounced,.coherent=coherent,.dma_mask=&mask,.bus_dma_limit=mask};dma_addr_t a=dma_direct_map_phys(&d,0x10008,8,DMA_FROM_DEVICE,0);assert(a==(bounced?0x50008:0x10008));dma_direct_unmap_phys(&d,a,8,DMA_FROM_DEVICE,0);for(uint64_t i=0;i<ntrace;i++)printf("%llu %llu\n",(unsigned long long)trace[i][0],(unsigned long long)trace[i][1]);}
'''
(H/'integrated.c').write_text(base+head+fun(O/'kernel__dma__swiotlb.c','swiotlb_map')+'\n'+'\n'.join(fun(O/'kernel__dma__direct.h',n) for n in ['dma_direct_sync_single_for_cpu','dma_direct_map_phys','dma_direct_unmap_phys'])+tail)
(H/'integrated_functions.json').write_text(json.dumps(dict(entries=manifest,scope='original DMA direct/map and swiotlb_map plus original ARM64 wrappers/boundary; pool allocation, lookup/copyback/release/address translation and capabilities are fixtures; maintenance operations are logs'),indent=2))
builds=[];rows=[]
for workaround in [0,1]:
 exe=H/f'integrated_{workaround}.bin';q=subprocess.run(['aarch64-linux-gnu-gcc','-static','-O0','-Wall','-Wextra','-Werror','-Wno-unused-parameter',f'-DWORKAROUND={workaround}',str(H/'integrated.c'),str(H/'boundary.S'),'-o',str(exe)],capture_output=True,text=True);builds.append(dict(workaround=workaround,code=q.returncode,stderr=q.stderr));(H/'integrated_builds.json').write_text(json.dumps(builds,indent=2))
 if q.returncode:raise RuntimeError(q.stderr)
 for bounced in [0,1]:
  for coherent in [0,1]:
   for dmin in [4,5]:
    q=subprocess.run(['qemu-aarch64',str(exe),str(bounced),str(coherent),str(dmin)],capture_output=True,text=True,timeout=15)
    row=dict(workaround=workaround,bounced=bounced,coherent=coherent,dmin=dmin,code=q.returncode,stdout=q.stdout,stderr=q.stderr);rows.append(row)
    if q.returncode:continue
    a=0x50000 if bounced else 0x10000;expected=[]
    if bounced:expected.append([5,0x50008])
    if not coherent:expected += [[3 if workaround else 1,a],[4,0],[3,a],[3,a],[4,0]]
    if bounced:expected += [[6,0x10008],[7,0x50008]]
    row['expected']=expected;row['local_relation']='matched' if [list(map(int,l.split())) for l in q.stdout.splitlines()]==expected else 'mismatch'
(H/'integrated_results.json').write_text(json.dumps(rows,indent=2))
if any(r.get('local_relation')!='matched' for r in rows):raise RuntimeError('integrated audit')
print('2 integrated instrumented builds /16 direct-bounce target sequences passed')
