from pathlib import Path
import json,hashlib,re,subprocess,shutil
H=Path(__file__).resolve().parent;R=H.parents[3];E=H.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
save('notes_before.json',{'before_sha256':{n:sha(R/n) for n in ['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']}})
shutil.copyfile(E/'smmu_stage_20261026/sync_work_notes.py',H/'sync_work_notes.py')
p=E/'smmu_chain_20261026/source/06_drivers__iommu__io-pgtable-arm.c';s=p.read_text();manifest=[]
def extract(name):
 matches=list(re.finditer(r'^static (?:inline )?(?:bool|void|size_t|phys_addr_t|arm_lpae_iopte) '+name+r'\(',s,re.M))
 for m in matches:
  a=m.start();b=s.index('{',a)
  if ';' in s[a:b]:continue
  z=b+1;depth=1
  while depth:depth+=(s[z]=='{')-(s[z]=='}');z+=1
  text=s[a:z];manifest.append(dict(name=name,line=s[:a].count('\n')+1,sha256=hashlib.sha256(text.encode()).hexdigest()));return text
 raise ValueError(name)
macros=[]
for n in ['ARM_LPAE_MAX_LEVELS','ARM_LPAE_LVL_SHIFT','ARM_LPAE_GRANULE','ARM_LPAE_PGD_SIZE','ARM_LPAE_PTES_PER_TABLE','ARM_LPAE_PGD_IDX','ARM_LPAE_LVL_IDX','ARM_LPAE_BLOCK_SIZE','ARM_LPAE_PTE_TYPE_SHIFT','ARM_LPAE_PTE_TYPE_MASK','ARM_LPAE_PTE_TYPE_BLOCK','ARM_LPAE_PTE_TYPE_TABLE','ARM_LPAE_PTE_TYPE_PAGE','ARM_LPAE_PTE_ADDR_MASK','iopte_type','iopte_deref']:
 m=re.search(r'^#define '+n+r'(?:\s|\()',s,re.M);a=m.start();b=s.index('\n',a)
 while s[b-1]=='\\':b=s.index('\n',b+1)
 macros.append(s[a:b])
head=r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <assert.h>
typedef uint64_t u64;typedef int64_t s64;typedef uint64_t arm_lpae_iopte;typedef uintptr_t phys_addr_t;
#define ilog2(x) (63-__builtin_clzl((unsigned long)(x)))
#define GENMASK_ULL(h,l) ((~0ULL<<(l))&(~0ULL>>(63-(h))))
#define SZ_64K 65536UL
#define __va(x) ((void *)(uintptr_t)(x))
#define READ_ONCE(x) (x)
static int warnings,walks,adds,frees,syncs;
#define WARN_ON(x) ((x)?(++warnings,1):0)
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
#define IO_PGTABLE_QUIRK_ARM_TTBR1 1
enum io_pgtable_fmt {ARM_64_LPAE_S1,ARM_MALI_LPAE};
struct io_pgtable_ops {int dummy;};struct io_pgtable_cfg {unsigned long pgsize_bitmap;int ias,quirks,coherent_walk;};
struct io_pgtable {struct io_pgtable_ops ops;struct io_pgtable_cfg cfg;enum io_pgtable_fmt fmt;};
struct arm_lpae_io_pgtable {struct io_pgtable iop;int pgd_bits,start_level,bits_per_level;void *pgd;};
struct iommu_iotlb_gather {int queued;};
#define io_pgtable_ops_to_data(x) ((struct arm_lpae_io_pgtable*)(x))
static bool iommu_iotlb_gather_queued(struct iommu_iotlb_gather*g){return g&&g->queued;}
static arm_lpae_iopte *root;static unsigned long last_addr,last_size;static int last_return;
static void __arm_lpae_sync_pte(arm_lpae_iopte*p,int n,struct io_pgtable_cfg*c){(void)n;(void)c;assert(!*p);syncs++;puts("SYNC_CLEAR");}
static void __arm_lpae_free_pages(void*p,size_t n,struct io_pgtable_cfg*c){(void)c;assert(last_return);frees++;printf("FREE %zu\n",n);free(p);}
static void io_pgtable_tlb_flush_walk(struct io_pgtable*i,unsigned long a,size_t n,size_t g){(void)i;walks++;last_addr=a;last_size=n;last_return=1;printf("WALK %lu %zu %zu\n",a,n,g);puts("WALK_RETURN");}
static void io_pgtable_tlb_add_page(struct io_pgtable*i,struct iommu_iotlb_gather*g,unsigned long a,size_t n){(void)i;(void)g;adds++;printf("ADD %lu %zu\n",a,n);}
static size_t arm_lpae_split_blk_unmap(struct arm_lpae_io_pgtable*d,struct iommu_iotlb_gather*g,unsigned long a,size_t n,arm_lpae_iopte p,int l,arm_lpae_iopte*t,size_t count){(void)d;(void)g;(void)a;(void)n;(void)p;(void)l;(void)t;(void)count;abort();}
'''
funcs='\n'.join(extract(n) for n in ['iopte_leaf','paddr_to_iopte','iopte_to_paddr','__arm_lpae_clear_pte','__arm_lpae_free_pgtable','__arm_lpae_unmap','arm_lpae_unmap_pages'])
tail=r'''
int main(int argc,char**argv){assert(argc==3);int mode=atoi(argv[1]),coherent=atoi(argv[2]);struct arm_lpae_io_pgtable d={.bits_per_level=PAGE_SHIFT-3,.pgd_bits=PAGE_SHIFT-3,.start_level=2,.iop={.cfg={.ias=48,.coherent_walk=coherent},.fmt=ARM_64_LPAE_S1}};unsigned long gran=ARM_LPAE_GRANULE(&d),block=ARM_LPAE_BLOCK_SIZE(2,&d),entries=ARM_LPAE_PTES_PER_TABLE(&d);d.iop.cfg.pgsize_bitmap=gran|block;
root=aligned_alloc(gran,gran);assert(root);memset(root,0,gran);d.pgd=root;struct iommu_iotlb_gather gather={.queued=mode==5};unsigned long idx=mode==2?entries-1:1,iova=idx*block,size=block,count=(mode==1||mode==2||mode==3)?2:1;
void*children[2]={0};int childcount=0;
if(mode<=3||mode==6){for(unsigned k=0;k<(mode==1?2U:1U);k++){children[k]=aligned_alloc(gran,gran);assert(children[k]);memset(children[k],0,gran);((arm_lpae_iopte*)children[k])[0]=3;root[idx+k]=paddr_to_iopte((uintptr_t)children[k],&d)|3;childcount++;}}
else if(mode==4||mode==5)root[idx]=1;
if(mode==6)size=gran;
if(mode==8)size=128;
if(mode==9)count=0;
if(mode==10)iova=1UL<<48;
size_t done=arm_lpae_unmap_pages(&d.iop.ops,iova,size,count,&gather);
if(mode<=3){assert(walks==(mode==1?2:1)&&frees==walks&&adds==0&&done==(unsigned long)walks*block);for(unsigned k=0;k<(unsigned)walks;k++)assert(!root[idx+k]);}
if(mode==4||mode==5){assert(done==block&&!walks&&!frees&&adds==(mode==4));assert(!root[idx]);}
if(mode==6){assert(done==gran&&!walks&&!frees&&adds==1&&root[idx]&&((arm_lpae_iopte*)children[0])[0]==0);}
if(mode>=7)assert(!done&&!walks&&!frees&&!adds);
assert(syncs==(coherent?0:walks+adds+(mode==5)));
printf("RESULT %zu %d %d %d %d %d\n",done,walks,adds,frees,syncs,warnings);
if(!frees)for(int k=0;k<childcount;k++)free(children[k]);free(root);return 0;}
'''
(H/'unmap.c').write_text(head+'\n'.join(macros)+'\n'+funcs+tail)
save('function_manifest.json',dict(source_sha256=sha(p),functions=manifest,macros=macros,substitutes=['allocation/direct-map address conversion','cfg/ops/container layout','flush callbacks and DMA sync','split helper aborts: unsupported branch']))
builds=[];rows=[]
for shift in [12,14,16]:
 exe=H/f'unmap_{shift}.bin';cmd=['cc','-std=gnu11','-Wall','-Wextra',f'-DPAGE_SHIFT={shift}',str(H/'unmap.c'),'-o',str(exe)];p=subprocess.run(cmd,capture_output=True,text=True);builds.append(dict(cmd=cmd,code=p.returncode,stderr=p.stderr));assert p.returncode==0,p.stderr
 for mode in range(11):
  for coherent in [0,1]:
   p=subprocess.run([str(exe),str(mode),str(coherent)],capture_output=True,text=True,timeout=10);rows.append(dict(shift=shift,mode=mode,coherent=coherent,code=p.returncode,stdout=p.stdout,stderr=p.stderr));assert p.returncode==0,rows[-1]
save('builds.json',builds);save('results.json',rows);print('3 builds / 66 original unmap/free function scenarios passed')
