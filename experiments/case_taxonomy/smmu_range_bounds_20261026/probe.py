from pathlib import Path
import json,re,hashlib,subprocess
H=Path(__file__).resolve().parent; s=(H/'source/arch__arm64__include__asm__tlbflush.h').read_text(encoding='utf-8'); manifests=[]
def fun(name):
 m=re.search(r'^static inline void '+name+r'\(',s,re.M);a=m.start();b=s.index('{',a)+1;d=1
 while d:d+=(s[b]=='{')-(s[b]=='}');b+=1
 t=s[a:b];manifests.append(dict(name=name,line=s[:a].count('\n')+1,sha256=hashlib.sha256(t.encode()).hexdigest()));return t
names=['flush_tlb_mm','__flush_tlb_page_nosync','__flush_tlb_range']
fs=[fun(n) for n in names];a=s.index('#define __flush_tlb_range_op(');b=s.index('} while (0)',a)+len('} while (0)');macro=s[a:b]
defs=[]
for name in ['__TLBI_RANGE_PAGES','MAX_TLBI_RANGE_PAGES','TLBI_RANGE_MASK','__TLBI_RANGE_NUM','MAX_TLBI_OPS']:
 m=re.search(r'^#define '+name+r'(?:\(|\s)',s,re.M);a=m.start();b=s.index('\n',a)
 while s[b-1]=='\\':b=s.index('\n',b+1)
 defs.append(s[a:b])
head=r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <assert.h>
#define PAGE_SIZE (1UL<<PAGE_SHIFT)
#define PAGE_MASK (~(PAGE_SIZE-1))
#define PTRS_PER_PTE (PAGE_SIZE/8)
#define GENMASK_ULL(h,l) ((~0ULL<<(l))&(~0ULL>>(63-(h))))
#define round_down(x,y) ((x)&~((y)-1))
#define round_up(x,y) (((x)+(y)-1)&~((y)-1))
struct mm_struct {int unused;};struct vm_area_struct {struct mm_struct *vm_mm;};
static int cap,calls;static unsigned long got_start,got_end;
#define system_supports_tlb_range() (cap)
#define dsb(x) ((void)0)
#define ASID(mm) ((void)(mm),17UL)
#define __TLBI_VADDR(a,id) ((a)+(id))
#define __TLBI_VADDR_RANGE(a,id,s,n,t) ((a)+(id)+(s)+(n)+(t))
#define __tlbi(op,a) ((void)(a))
#define __tlbi_user(op,a) ((void)(a))
#define __tlbi_level(op,a,l) ((void)(a),(void)(l))
#define __tlbi_user_level(op,a,l) ((void)(a),(void)(l))
static void mmu_notifier_arch_invalidate_secondary_tlbs(struct mm_struct*m,unsigned long a,unsigned long b){(void)m;calls++;got_start=a;got_end=b;}
'''
tail=r'''
int main(int argc,char**argv){assert(argc==4);cap=atoi(argv[1]);unsigned long pages=strtoul(argv[2],0,0),kind=strtoul(argv[3],0,0);struct mm_struct m={0};struct vm_area_struct v={&m};unsigned long start=1UL<<30,end=start+pages*PAGE_SIZE;
if(kind)__flush_tlb_page_nosync(&m,start+7);else __flush_tlb_range(&v,start,end,PAGE_SIZE,false,0);
assert(calls==1);printf("%lu %lu %lu %lu\n",start,end,got_start,got_end);return 0;}
'''
(H/'origin.c').write_text(head+'\n'.join(defs)+'\n'+macro+'\n'+'\n'.join(fs)+tail,encoding='utf-8')
(H/'function_manifest.json').write_text(json.dumps(manifests,indent=2),encoding='utf-8')
builds=[];rows=[]
for shift in [12,14,16]:
 exe=H/f'origin_{shift}.bin';cmd=['cc','-std=gnu11','-Wall','-Wextra','-Werror',f'-DPAGE_SHIFT={shift}',str(H/'origin.c'),'-o',str(exe)]
 p=subprocess.run(cmd,capture_output=True,text=True);builds.append(dict(command=cmd,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr));(H/'builds.json').write_text(json.dumps(builds,indent=2));assert p.returncode==0,p.stderr
 for cap in [0,1]:
  for pages,kind in [(1,0),(31,0),(33,0),((1<<21)-1,0),(1<<21,0),(1<<32,0),(1,1)]:
   p=subprocess.run([str(exe),str(cap),str(pages),str(kind)],capture_output=True,text=True,timeout=15);assert p.returncode==0,p.stderr
   start,end,a,b=map(int,p.stdout.split());full=not kind and ((not cap and pages>=((1<<shift)//8)) or pages>=1<<21)
   assert (a,b)==((start,start+(1<<shift)) if kind else (0,(1<<64)-1) if full else (end,end))
   rows.append(dict(page_shift=shift,cpu_range_cap=cap,pages=pages,single_page_entry=bool(kind),stdout=p.stdout,callback_start=a,callback_end=b,route='single_page' if kind else 'full_sentinel' if full else 'empty_range_after_macro',limit='instruction/barrier/notifier doubles; original macro and functions'))
(H/'results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('3 builds; 42 original ARM64-entry scenarios passed; range branch emits end/end at pinned revision')
