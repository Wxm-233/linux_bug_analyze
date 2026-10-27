from pathlib import Path
import importlib.util,subprocess,json,hashlib
H=Path(__file__).resolve().parent;S=H.parent/'smmu_chain_20261026/source'
sp=importlib.util.spec_from_file_location('probe',H.parent/'smmu_range_probe.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
text=(S/'03_drivers__iommu__arm__arm-smmu-v3__arm-smmu-v3-sva.c').read_text();body=m.function(text,'arm_smmu_mmu_notifier_get(')
pre=r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stddef.h>
#include <errno.h>
#define GFP_KERNEL 0
#define ERR_PTR(v) ((void *)(intptr_t)(v))
#define PTR_ERR(v) ((int)(intptr_t)(v))
#define IS_ERR(v) ((uintptr_t)(v)>=(uintptr_t)-4095)
#define ERR_CAST(v) ((void *)(v))
struct mm_struct {int pasid;};struct mmu_notifier {struct mm_struct *mm;const void *ops;};
struct list_head {void *entry;};struct arm_smmu_domain {struct list_head mmu_notifiers;};
struct arm_smmu_ctx_desc {int asid;};
struct arm_smmu_mmu_notifier {struct mmu_notifier mn;int refs;struct arm_smmu_ctx_desc *cd;struct arm_smmu_domain *domain;struct list_head list;};
#define list_for_each_entry(p,h,m) for((p)=(h)->entry;(p);(p)=NULL)
#define refcount_inc(p) (++*(p))
#define refcount_set(p,v) (*(p)=(v))
static int arm_smmu_mmu_notifier_ops,mode,regs,writes,puts,frees,ready_at_register,adds;
static struct arm_smmu_ctx_desc cd={.asid=17};static struct arm_smmu_domain *expected;
static struct arm_smmu_ctx_desc *arm_smmu_alloc_shared_cd(struct mm_struct *mm){(void)mm;return mode==1?ERR_PTR(-ENOMEM):&cd;}
static void *kzalloc(size_t n,int flags){(void)flags;return mode==2?NULL:calloc(1,n);}
static void kfree(void *p){free(p);}
static void arm_smmu_free_shared_cd(struct arm_smmu_ctx_desc *c){(void)c;frees++;}
static int mmu_notifier_register(struct mmu_notifier *mn,struct mm_struct *mm){struct arm_smmu_mmu_notifier *n=(void *)mn;regs++;ready_at_register=n->domain==expected&&n->cd==&cd&&mn->ops==&arm_smmu_mmu_notifier_ops;if(mode==3)return -ENOMEM;mn->mm=mm;return 0;}
static int arm_smmu_write_ctx_desc(struct arm_smmu_domain *d,int pasid,struct arm_smmu_ctx_desc *c){if(d!=expected||pasid!=19||c!=&cd)abort();writes++;return mode==4?-E2BIG:0;}
static void mmu_notifier_put(struct mmu_notifier *mn){puts++;free(mn);}
static void list_add(struct list_head *node,struct list_head *head){adds++;head->entry=(char *)node - offsetof(struct arm_smmu_mmu_notifier,list);}
static struct arm_smmu_mmu_notifier *
'''
main=r'''
int main(int argc,char **argv){if(argc!=2)return 2;mode=atoi(argv[1]);struct mm_struct mm={19},other={21};struct arm_smmu_domain d={0};expected=&d;
struct arm_smmu_mmu_notifier existing={.mn={.mm=mode==5?&mm:&other},.refs=1,.cd=&cd,.domain=&d};if(mode==5||mode==6)d.mmu_notifiers.entry=&existing;
struct arm_smmu_mmu_notifier *n=arm_smmu_mmu_notifier_get(&d,&mm);int err=IS_ERR(n)?PTR_ERR(n):0;int bound=!err&&n->domain==&d&&n->cd==&cd&&n->mn.mm==&mm;
printf("%d %d %d %d %d %d %d %d %d\n",err,regs,writes,puts,frees,ready_at_register,adds,bound,existing.refs);
if(!err&&n!=&existing)free(n);return 0;}
'''
p=H/'notifier_get.c';p.write_text(pre+body+'\n'+main);exe=H/'notifier_get.bin'
done=subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(p),'-o',str(exe)],capture_output=True,text=True);assert done.returncode==0,done.stderr
names=['success','cd_alloc_failure','notifier_alloc_failure','registration_failure','ctx_write_failure','same_mm_reuse','different_mm_new']
expected_rows=[[0,1,1,0,0,1,1,1,1],[-12,0,0,0,0,0,0,0,1],[-12,0,0,0,1,0,0,0,1],[-12,1,0,0,1,1,0,0,1],[-7,1,1,1,1,1,0,0,1],[0,0,0,0,0,0,0,1,2],[0,1,1,0,0,1,1,1,1]]
rows=[]
for mode,name in enumerate(names):
 out=subprocess.check_output([str(exe),str(mode)],text=True);values=list(map(int,out.split()));assert values==expected_rows[mode],(mode,values)
 rows.append(dict(mode=name,values=values,stdout=out))
with (H/'notifier_results.json').open('x') as f:json.dump(dict(function_sha256=hashlib.sha256(body.encode()).hexdigest(),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),scope='original notifier_get only; registration, allocation, CD write, list and release are doubles; no concurrent kernel registration',columns=['errno','register_calls','write_calls','put_calls','free_cd_calls','fields_ready_at_register','list_add_calls','returned_binding','existing_refs'],rows=rows),f,indent=2)
print('Seven notifier creation/reuse/failure branches verified; no concurrency claim.')
