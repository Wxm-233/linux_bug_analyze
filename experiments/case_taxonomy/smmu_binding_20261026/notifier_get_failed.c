
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
arm_smmu_mmu_notifier_get(struct arm_smmu_domain *smmu_domain,
			  struct mm_struct *mm)
{
	int ret;
	struct arm_smmu_ctx_desc *cd;
	struct arm_smmu_mmu_notifier *smmu_mn;

	list_for_each_entry(smmu_mn, &smmu_domain->mmu_notifiers, list) {
		if (smmu_mn->mn.mm == mm) {
			refcount_inc(&smmu_mn->refs);
			return smmu_mn;
		}
	}

	cd = arm_smmu_alloc_shared_cd(mm);
	if (IS_ERR(cd))
		return ERR_CAST(cd);

	smmu_mn = kzalloc(sizeof(*smmu_mn), GFP_KERNEL);
	if (!smmu_mn) {
		ret = -ENOMEM;
		goto err_free_cd;
	}

	refcount_set(&smmu_mn->refs, 1);
	smmu_mn->cd = cd;
	smmu_mn->domain = smmu_domain;
	smmu_mn->mn.ops = &arm_smmu_mmu_notifier_ops;

	ret = mmu_notifier_register(&smmu_mn->mn, mm);
	if (ret) {
		kfree(smmu_mn);
		goto err_free_cd;
	}

	ret = arm_smmu_write_ctx_desc(smmu_domain, mm->pasid, cd);
	if (ret)
		goto err_put_notifier;

	list_add(&smmu_mn->list, &smmu_domain->mmu_notifiers);
	return smmu_mn;

err_put_notifier:
	/* Frees smmu_mn */
	mmu_notifier_put(&smmu_mn->mn);
err_free_cd:
	arm_smmu_free_shared_cd(cd);
	return ERR_PTR(ret);
}

int main(int argc,char **argv){if(argc!=2)return 2;mode=atoi(argv[1]);struct mm_struct mm={19},other={21};struct arm_smmu_domain d={0};expected=&d;
struct arm_smmu_mmu_notifier existing={.mn={.mm=mode==5?&mm:&other},.refs=1,.cd=&cd,.domain=&d};if(mode==5||mode==6)d.mmu_notifiers.entry=&existing;
struct arm_smmu_mmu_notifier *n=arm_smmu_mmu_notifier_get(&d,&mm);int err=IS_ERR(n)?PTR_ERR(n):0;int bound=!err&&n->domain==&d&&n->cd==&cd&&n->mn.mm==&mm;
printf("%d %d %d %d %d %d %d %d %d\n",err,regs,writes,puts,frees,ready_at_register,adds,bound,existing.refs);
if(!err&&n!=&existing)free(n);return 0;}
