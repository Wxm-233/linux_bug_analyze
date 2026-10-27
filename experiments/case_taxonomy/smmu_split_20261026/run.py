from pathlib import Path
import re,json,hashlib,subprocess,shutil
H=Path(__file__).resolve().parent;E=H.parent;R=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 with (H/n).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
save('notes_before.json',{'before_sha256':{n:sha(R/n) for n in ['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']}})
shutil.copyfile(E/'smmu_stage_20261026/sync_work_notes.py',H/'sync_work_notes.py')
p=E/'smmu_chain_20261026/source/06_drivers__iommu__io-pgtable-arm.c';s=p.read_text();manifest=[]
def extract(name):
 for m in re.finditer(r'^static (?:void|size_t|arm_lpae_iopte) '+name+r'\(',s,re.M):
  a=m.start();b=s.index('{',a)
  if ';' in s[a:b]:continue
  z=b+1;d=1
  while d:d+=(s[z]=='{')-(s[z]=='}');z+=1
  result=s[a:z];manifest.append(dict(name=name,line=s[:a].count('\n')+1,sha256=hashlib.sha256(result.encode()).hexdigest()));return result
 raise ValueError(name)
base=E/'smmu_unmap_20261026/unmap_observed.c';c=base.read_text();c=c[:c.index('int main(')]
c=re.sub(r'^static size_t arm_lpae_split_blk_unmap[^\n]+\n','',c,flags=re.M)
c=re.sub(r'^static void __arm_lpae_sync_pte[^\n]+\n','',c,flags=re.M)
c=re.sub(r'^static void __arm_lpae_free_pages[^\n]+\n','',c,flags=re.M)
extra=r'''
static int mode,allocs,installs,barriers,init_sync,clear_sync,install_sync;
static arm_lpae_iopte *competitor;static void *allocation;
#define GFP_ATOMIC 0
#define IO_PGTABLE_QUIRK_ARM_NS 2
#define ARM_LPAE_PTE_NSTABLE (1ULL<<63)
#define ARM_LPAE_PTE_SW_SYNC (1ULL<<55)
#define ARM_LPAE_PTE_ATTR_MASK ((0x3ffULL<<2)|(6ULL<<52))
#define iopte_prot(p) ((p)&ARM_LPAE_PTE_ATTR_MASK)
#define __pa(p) ((uintptr_t)(p))
#define WRITE_ONCE(x,v) ((x)=(v))
static void dma_wmb(void){barriers++;puts("BARRIER_CALL");}
static arm_lpae_iopte cmpxchg64_relaxed(arm_lpae_iopte*p,arm_lpae_iopte curr,arm_lpae_iopte new){assert(barriers==1);installs++;if(mode==2)*p=(uintptr_t)competitor|3;if(mode==3)*p=0;arm_lpae_iopte old=*p;if(old==curr)*p=new;printf("INSTALL %d\n",old==curr);return old;}
static void *__arm_lpae_alloc_pages(size_t n,int flags,struct io_pgtable_cfg*c){(void)flags;(void)c;allocs++;if(mode==1){puts("ALLOC_FAIL");return NULL;}allocation=aligned_alloc(n,n);assert(allocation);memset(allocation,0,n);puts("ALLOC_OK");return allocation;}
static void __arm_lpae_sync_pte(arm_lpae_iopte*p,int n,struct io_pgtable_cfg*c){(void)n;(void)c;syncs++;if(!*p){clear_sync++;puts("SYNC_CLEAR");}else if(p>=root&&p<root+((1UL<<PAGE_SHIFT)/8)){install_sync++;puts("SYNC_INSTALL");}else init_sync++;}
static void __arm_lpae_free_pages(void*p,size_t n,struct io_pgtable_cfg*c){(void)n;(void)c;assert(p==allocation);frees++;puts("FREE_PRIVATE");free(p);allocation=NULL;}
static size_t __arm_lpae_unmap(struct arm_lpae_io_pgtable*,struct iommu_iotlb_gather*,unsigned long,size_t,size_t,int,arm_lpae_iopte*);
'''
pos=c.index('static inline bool iopte_leaf');c=c[:pos]+extra+c[pos:]
pos=c.index('static size_t __arm_lpae_unmap(struct arm_lpae_io_pgtable *data,')
c=c[:pos]+'\n'.join(extract(n) for n in ['__arm_lpae_init_pte','arm_lpae_install_table','arm_lpae_split_blk_unmap'])+'\n'+c[pos:]
main=r'''
int main(int argc,char**argv){assert(argc==4);mode=atoi(argv[1]);int coherent=atoi(argv[2]),queued=atoi(argv[3]);struct arm_lpae_io_pgtable d={.bits_per_level=PAGE_SHIFT-3,.pgd_bits=PAGE_SHIFT-3,.start_level=2,.iop={.cfg={.ias=48,.coherent_walk=coherent},.fmt=ARM_64_LPAE_S1}};
size_t gran=ARM_LPAE_GRANULE(&d),block=ARM_LPAE_BLOCK_SIZE(2,&d),entries=ARM_LPAE_PTES_PER_TABLE(&d);d.iop.cfg.pgsize_bitmap=gran|block;root=aligned_alloc(gran,gran);assert(root);memset(root,0,gran);root[1]=1;d.pgd=root;
if(mode==2){competitor=aligned_alloc(gran,gran);assert(competitor);for(size_t i=0;i<entries;i++)competitor[i]=paddr_to_iopte(i*gran,&d)|3;}
size_t index=mode==4?entries-1:3,count=2,expected=mode==4?1:2;unsigned long address=block+index*gran;struct iommu_iotlb_gather gather={.queued=queued};
size_t done=arm_lpae_unmap_pages(&d.iop.ops,address,gran,count,&gather);assert(!walks&&allocs==1);
if(mode==1){assert(!done&&!installs&&!frees&&root[1]==1&&!adds);}
else if(mode==3){assert(!done&&installs==1&&frees==1&&!root[1]&&!adds);}
else{assert(done==expected*gran&&installs==1);assert(adds==(int)((mode==2&&queued)?0:expected));assert(frees==(mode==2));arm_lpae_iopte*t=iopte_deref(root[1],&d);for(size_t i=0;i<entries;i++){if(i>=index&&i<index+expected)assert(t[i]==0);else assert(iopte_leaf(t[i],3,d.iop.fmt)&&iopte_to_paddr(t[i],&d)==i*gran);}free(t);}
printf("RESULT %zu %d %d %d %d %d %d %d %d %d\n",done,allocs,installs,adds,frees,barriers,init_sync,install_sync,clear_sync,warnings);free(root);return 0;}
'''
(H/'split.c').write_text(c+main)
save('manifest.json',dict(base_sha256=sha(base),source_sha256=sha(p),functions=manifest,boundary='original init/install/split/unmap; injected cmpxchg outcomes, no concurrent execution; allocator/DMA/callback doubles'))
builds=[];rows=[]
for shift in [12,14,16]:
 exe=H/f'split_{shift}.bin';cmd=['cc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter',f'-DPAGE_SHIFT={shift}',str(H/'split.c'),'-o',str(exe)];q=subprocess.run(cmd,capture_output=True,text=True);builds.append(dict(cmd=cmd,code=q.returncode,stderr=q.stderr));assert q.returncode==0,q.stderr
 for mode in range(5):
  for coherent in [0,1]:
   for queued in [0,1]:
    q=subprocess.run([str(exe),str(mode),str(coherent),str(queued)],capture_output=True,text=True,timeout=10);rows.append(dict(shift=shift,mode=mode,coherent=coherent,queued=queued,stdout=q.stdout,stderr=q.stderr,code=q.returncode));assert q.returncode==0,rows[-1]
save('builds.json',builds);save('results.json',rows);print('3 builds / 60 split+install+unmap scenarios passed; surviving translations checked')
