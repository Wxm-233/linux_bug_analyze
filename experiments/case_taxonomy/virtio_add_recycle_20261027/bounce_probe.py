from pathlib import Path
import re,json,hashlib,subprocess
H=Path(__file__).resolve().parent;p=H.parent/'virtio_dma_chain_20261026/source/kernel__dma__swiotlb.c';s=p.read_text();manifest=[]
def fun(n):
 m=re.search(r'^(?:static )?void '+n+r'\([^;{]*\)\s*\{',s,re.M)
 if not m:raise RuntimeError(n)
 a=m.start();b=m.end();d=1
 while d:d+=(s[b]=='{')-(s[b]=='}');b+=1
 t=s[a:b];manifest.append(dict(name=n,line=s[:a].count('\n')+1,sha256=hashlib.sha256(t.encode()).hexdigest()));return t
head=r'''
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
typedef uint64_t phys_addr_t;
enum dma_data_direction {DMA_TO_DEVICE=1,DMA_FROM_DEVICE=2,DMA_BIDIRECTIONAL=0};
struct device {int unused;};struct page {int unused;};
struct slot {phys_addr_t orig_addr;size_t alloc_size;};
struct io_tlb_pool {phys_addr_t start;unsigned char *vaddr;struct slot slots[4];};
#define IO_TLB_SHIFT 11
#define IO_TLB_SIZE (1UL<<IO_TLB_SHIFT)
#define PAGE_SIZE 4096UL
#define PAGE_MASK (~(PAGE_SIZE-1))
#define PFN_DOWN(a) ((a)/PAGE_SIZE)
#define INVALID_PHYS_ADDR (~0ULL)
#define DMA_ATTR_SKIP_CPU_SYNC 1
#define BUG_ON(x) assert(!(x))
#define dev_WARN_ONCE(...) ((void)0)
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
#define local_irq_save(f) do{(f)=0;}while(0)
#define local_irq_restore(f) ((void)(f))
static unsigned char original[4096],bounce[8192];static int copies,releases;static struct page pg;
static struct page *pfn_to_page(unsigned long n){(void)n;return &pg;}
static bool PageHighMem(struct page*p){(void)p;return false;}
static unsigned long swiotlb_align_offset(struct device*d,unsigned long x,phys_addr_t a){(void)d;(void)x;return a&(IO_TLB_SIZE-1);}
static void *phys_to_virt(phys_addr_t a){assert(a>=0x10000&&a<0x11000);return original+(a-0x10000);}
static void memcpy_from_page(void*v,struct page*p,unsigned o,unsigned n){(void)v;(void)p;(void)o;(void)n;abort();}
static void memcpy_to_page(struct page*p,unsigned o,void*v,unsigned n){(void)v;(void)p;(void)o;(void)n;abort();}
static void *copy_probe(void*d,const void*s,size_t n){copies++;printf("COPY %zu\n",n);return memmove(d,s,n);}
#define memcpy copy_probe
static bool swiotlb_del_transient(struct device*d,phys_addr_t a,struct io_tlb_pool*p){(void)d;(void)a;(void)p;return false;}
static void swiotlb_release_slots(struct device*d,phys_addr_t a,struct io_tlb_pool*p){(void)d;(void)a;(void)p;releases++;puts("RELEASE");}
'''
tail=r'''
int main(int argc,char**argv){assert(argc==4);int mode=atoi(argv[1]);unsigned off=atoi(argv[2]),written=atoi(argv[3]);struct device dev={0};struct io_tlb_pool pool={.start=0x20000,.vaddr=bounce,.slots={{.orig_addr=0x10000+off,.alloc_size=8}}};for(unsigned i=0;i<sizeof(original);i++)original[i]=(unsigned char)(i%251);memset(bounce,0xee,sizeof(bounce));unsigned char before[4096];memmove(before,original,sizeof(before));phys_addr_t tlb=pool.start+off;
/* The map allocator is not executed: supply the mapping record it would own,
 * then execute its original initial-copy primitive before simulated writes. */
swiotlb_bounce(&dev,tlb,8,DMA_TO_DEVICE,&pool);assert(!memcmp(bounce+off,original+off,8));for(unsigned i=0;i<written;i++)bounce[off+i]=0xa0+i;
if(mode==1)__swiotlb_sync_single_for_cpu(&dev,tlb,8,DMA_FROM_DEVICE,&pool);
__swiotlb_tbl_unmap_single(&dev,tlb,8,DMA_FROM_DEVICE,mode?DMA_ATTR_SKIP_CPU_SYNC:0,&pool);
for(unsigned i=0;i<sizeof(original);i++){unsigned char expected=before[i];if(mode!=2&&i>=off&&i<off+written)expected=0xa0+i-off;assert(original[i]==expected);}assert(releases==1&&copies==(mode==2?1:2));printf("RESULT mode=%d offset=%u written=%u copies=%d neighbors=preserved\n",mode,off,written,copies);}
'''
(H/'bounce.c').write_text(head+'\n'.join(fun(n) for n in ['swiotlb_bounce','__swiotlb_tbl_unmap_single','__swiotlb_sync_single_for_cpu'])+tail)
(H/'bounce_functions.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),functions=manifest,scope='lowmem original copy primitive and CPU sync/unmap; synthetic physical translation/alignment/pool/slot release; allocator/highmem/device/cache not executed; writes simulated'),indent=2))
q=subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(H/'bounce.c'),'-o',str(H/'bounce.bin')],capture_output=True,text=True)
(H/'bounce_build.json').write_text(json.dumps(dict(code=q.returncode,stderr=q.stderr),indent=2))
if q.returncode:raise RuntimeError(q.stderr)
rows=[]
for mode in [0,1,2]:
 for offset in [24,60,120]:
  for written in [0,4,8]:
   q=subprocess.run([str(H/'bounce.bin'),str(mode),str(offset),str(written)],capture_output=True,text=True);rows.append(dict(mode=mode,offset=offset,written=written,code=q.returncode,stdout=q.stdout,stderr=q.stderr))
(H/'bounce_results.json').write_text(json.dumps(rows,indent=2))
if any(r['code'] for r in rows):raise RuntimeError('bounce execution failure')
print('1 build /27 lowmem copyback executions passed')
