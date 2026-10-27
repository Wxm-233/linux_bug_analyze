
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <errno.h>
#define ARM_SMMU_DOMAIN_S1 0
#define ARM_SMMU_DOMAIN_S2 1
#define ARM_SMMU_DOMAIN_NESTED 2
#define ARM_SMMU_DOMAIN_BYPASS 3
#define IOMMU_DOMAIN_IDENTITY 1
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
#define VA_BITS 48
#define mutex_lock(x) ((void)(x))
#define mutex_unlock(x) ((void)(x))
enum iommu_dev_features {IOMMU_DEV_FEAT_IOPF,IOMMU_DEV_FEAT_SVA};
enum io_pgtable_fmt {ARM_64_LPAE_S1,ARM_64_LPAE_S2};
struct arm_smmu_domain;
struct iommu_domain {unsigned type;unsigned long pgsize_bitmap;struct {unsigned long aperture_end;bool force_aperture;} geometry;struct arm_smmu_domain *owner;};
struct io_pgtable_ops {int x;};
struct arm_smmu_device {unsigned features;unsigned long ias,oas,pgsize_bitmap;void *dev;};
struct arm_smmu_domain {struct iommu_domain domain;struct arm_smmu_device *smmu;int stage;struct io_pgtable_ops *pgtbl_ops;};
struct arm_smmu_master {struct arm_smmu_device *smmu;bool sva_enabled,iopf_enabled;unsigned ssid_bits;};
struct device {struct arm_smmu_master *master;};
struct io_pgtable_cfg {unsigned long pgsize_bitmap,ias,oas;bool coherent_walk;void *tlb,*iommu_dev;};
static int failure,allocs,stage_calls,sva_lock,arm_smmu_flush_ops;static struct io_pgtable_ops ops;
static struct arm_smmu_domain *to_smmu_domain(struct iommu_domain *d){return d->owner;}
static struct arm_smmu_master *dev_iommu_priv_get(struct device *d){return d->master;}
static struct io_pgtable_ops *alloc_io_pgtable_ops(enum io_pgtable_fmt f,struct io_pgtable_cfg *c,void *cookie){(void)f;(void)cookie;allocs++;if(failure==1)return NULL;c->pgsize_bitmap=(1UL<<12)|(1UL<<21);return &ops;}
static void free_io_pgtable_ops(struct io_pgtable_ops *p){(void)p;}
static int arm_smmu_domain_finalise_s1(struct arm_smmu_domain*d,struct arm_smmu_master*m,struct io_pgtable_cfg*c){(void)d;(void)m;(void)c;stage_calls++;return failure==2?-ENOMEM:0;}
static int arm_smmu_domain_finalise_s2(struct arm_smmu_domain*d,struct arm_smmu_master*m,struct io_pgtable_cfg*c){return arm_smmu_domain_finalise_s1(d,m,c);}
static bool arm_smmu_master_iopf_supported(struct arm_smmu_master*m){(void)m;return true;}
static bool arm_smmu_master_sva_enabled(struct arm_smmu_master*m){return m->sva_enabled;}
static int arm_smmu_master_sva_enable_iopf(struct arm_smmu_master*m){(void)m;return failure==3?-EINVAL:0;}

#define ARM_SMMU_FEAT_TRANS_S1 (1 << 9)
#define ARM_SMMU_FEAT_TRANS_S2 (1 << 10)
#define ARM_SMMU_FEAT_SVA (1 << 17)
#define ARM_SMMU_FEAT_VAX (1 << 14)
#define ARM_SMMU_FEAT_COHERENCY (1 << 8)
static int arm_smmu_domain_finalise(struct iommu_domain *domain,
				    struct arm_smmu_master *master)
{
	int ret;
	unsigned long ias, oas;
	enum io_pgtable_fmt fmt;
	struct io_pgtable_cfg pgtbl_cfg;
	struct io_pgtable_ops *pgtbl_ops;
	int (*finalise_stage_fn)(struct arm_smmu_domain *,
				 struct arm_smmu_master *,
				 struct io_pgtable_cfg *);
	struct arm_smmu_domain *smmu_domain = to_smmu_domain(domain);
	struct arm_smmu_device *smmu = smmu_domain->smmu;

	if (domain->type == IOMMU_DOMAIN_IDENTITY) {
		smmu_domain->stage = ARM_SMMU_DOMAIN_BYPASS;
		return 0;
	}

	/* Restrict the stage to what we can actually support */
	if (!(smmu->features & ARM_SMMU_FEAT_TRANS_S1))
		smmu_domain->stage = ARM_SMMU_DOMAIN_S2;
	if (!(smmu->features & ARM_SMMU_FEAT_TRANS_S2))
		smmu_domain->stage = ARM_SMMU_DOMAIN_S1;

	switch (smmu_domain->stage) {
	case ARM_SMMU_DOMAIN_S1:
		ias = (smmu->features & ARM_SMMU_FEAT_VAX) ? 52 : 48;
		ias = min_t(unsigned long, ias, VA_BITS);
		oas = smmu->ias;
		fmt = ARM_64_LPAE_S1;
		finalise_stage_fn = arm_smmu_domain_finalise_s1;
		break;
	case ARM_SMMU_DOMAIN_NESTED:
	case ARM_SMMU_DOMAIN_S2:
		ias = smmu->ias;
		oas = smmu->oas;
		fmt = ARM_64_LPAE_S2;
		finalise_stage_fn = arm_smmu_domain_finalise_s2;
		break;
	default:
		return -EINVAL;
	}

	pgtbl_cfg = (struct io_pgtable_cfg) {
		.pgsize_bitmap	= smmu->pgsize_bitmap,
		.ias		= ias,
		.oas		= oas,
		.coherent_walk	= smmu->features & ARM_SMMU_FEAT_COHERENCY,
		.tlb		= &arm_smmu_flush_ops,
		.iommu_dev	= smmu->dev,
	};

	pgtbl_ops = alloc_io_pgtable_ops(fmt, &pgtbl_cfg, smmu_domain);
	if (!pgtbl_ops)
		return -ENOMEM;

	domain->pgsize_bitmap = pgtbl_cfg.pgsize_bitmap;
	domain->geometry.aperture_end = (1UL << pgtbl_cfg.ias) - 1;
	domain->geometry.force_aperture = true;

	ret = finalise_stage_fn(smmu_domain, master, &pgtbl_cfg);
	if (ret < 0) {
		free_io_pgtable_ops(pgtbl_ops);
		return ret;
	}

	smmu_domain->pgtbl_ops = pgtbl_ops;
	return 0;
}
bool arm_smmu_master_sva_supported(struct arm_smmu_master *master)
{
	if (!(master->smmu->features & ARM_SMMU_FEAT_SVA))
		return false;

	/* SSID support is mandatory for the moment */
	return master->ssid_bits;
}
int arm_smmu_master_enable_sva(struct arm_smmu_master *master)
{
	int ret;

	mutex_lock(&sva_lock);
	ret = arm_smmu_master_sva_enable_iopf(master);
	if (!ret)
		master->sva_enabled = true;
	mutex_unlock(&sva_lock);

	return ret;
}
static int arm_smmu_dev_enable_feature(struct device *dev,
				       enum iommu_dev_features feat)
{
	struct arm_smmu_master *master = dev_iommu_priv_get(dev);

	if (!master)
		return -ENODEV;

	switch (feat) {
	case IOMMU_DEV_FEAT_IOPF:
		if (!arm_smmu_master_iopf_supported(master))
			return -EINVAL;
		if (master->iopf_enabled)
			return -EBUSY;
		master->iopf_enabled = true;
		return 0;
	case IOMMU_DEV_FEAT_SVA:
		if (!arm_smmu_master_sva_supported(master))
			return -EINVAL;
		if (arm_smmu_master_sva_enabled(master))
			return -EBUSY;
		return arm_smmu_master_enable_sva(master);
	default:
		return -EINVAL;
	}
}
int main(int argc,char**argv){if(argc!=8)return 2;int identity=atoi(argv[1]),s1=atoi(argv[2]),s2=atoi(argv[3]),initial=atoi(argv[4]),cap=atoi(argv[5]),ssid=atoi(argv[6]);failure=atoi(argv[7]);
struct arm_smmu_device smmu={.features=(s1?ARM_SMMU_FEAT_TRANS_S1:0)|(s2?ARM_SMMU_FEAT_TRANS_S2:0)|(cap?ARM_SMMU_FEAT_SVA:0),.ias=48,.oas=48,.pgsize_bitmap=(1UL<<12)|(1UL<<21)};
struct arm_smmu_domain d={.smmu=&smmu,.stage=initial,.domain={.type=identity?IOMMU_DOMAIN_IDENTITY:0}};d.domain.owner=&d;
struct arm_smmu_master master={.smmu=&smmu,.ssid_bits=ssid};struct device dev={.master=&master};
int ret=arm_smmu_domain_finalise(&d.domain,&master);int enabled=ret?999:arm_smmu_dev_enable_feature(&dev,IOMMU_DEV_FEAT_SVA);
printf("%d %d %d %d %d %d %lu\n",ret,d.stage,enabled,master.sva_enabled,allocs,stage_calls,d.domain.pgsize_bitmap);return 0;}
