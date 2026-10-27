
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <limits.h>
struct arm_smmu_device { unsigned int features; };
struct iommu_domain { unsigned long pgsize_bitmap; };
struct arm_smmu_domain {
 int stage; struct {struct {int asid;} cd;} s1_cfg; struct {int vmid;} s2_cfg;
    struct arm_smmu_device *smmu;
    struct iommu_domain domain;
};
struct arm_smmu_cmdq_ent {
 unsigned int opcode;
    struct {
        bool leaf; int asid,vmid;
        unsigned long tg, ttl, scale, num, addr;
    } tlbi;
};
struct arm_smmu_cmdq_batch { unsigned int num; };

#define CMDQ_TLBI_RANGE_NUM_MAX 31UL
#define __ffs(x) __builtin_ctzl(x)
#define ilog2(x) (63 - __builtin_clzl((unsigned long)(x)))
static struct arm_smmu_cmdq_ent recorded[128];
static unsigned int recorded_count;
static void arm_smmu_cmdq_batch_add(struct arm_smmu_device *smmu,
    struct arm_smmu_cmdq_batch *batch, struct arm_smmu_cmdq_ent *cmd)
{
    (void)smmu;
    if (recorded_count >= 128)
        abort();
    recorded[recorded_count++] = *cmd;
    batch->num++;
}
static void arm_smmu_cmdq_batch_submit(struct arm_smmu_device *smmu,
    struct arm_smmu_cmdq_batch *batch)
{
    (void)smmu; (void)batch;
}

#define ARM_SMMU_FEAT_RANGE_INV (1 << 15)
#define ARM_SMMU_FEAT_BTM (1 << 16)
#define ARM_SMMU_FEAT_E2H (1 << 18)
#define CMDQ_OP_TLBI_EL2_VA 0x22
#define CMDQ_OP_TLBI_NH_VA 0x12
#define CMDQ_OP_TLBI_S2_IPA 0x2a
#define ARM_SMMU_DOMAIN_S1 1
#define ARM_SMMU_DOMAIN_S2 2
#define IOMMU_NO_PASID 0
#define PAGE_SIZE (1UL << PAGE_SHIFT)
struct mmu_notifier {int unused;};
struct mm_struct {int pasid;};
struct cd {int asid;};
struct arm_smmu_mmu_notifier {struct mmu_notifier mn; struct arm_smmu_domain *domain; struct cd *cd;};
static struct arm_smmu_mmu_notifier *mn_to_smmu(struct mmu_notifier *mn) {return (void *)mn;}
static int asid_calls,asid_value,atc_calls,atc_pasid; static unsigned long atc_start,atc_size;
static void arm_smmu_tlb_inv_asid(struct arm_smmu_device *s,int a){(void)s;asid_calls++;asid_value=a;}
static int arm_smmu_atc_inv_domain(struct arm_smmu_domain *d,int p,unsigned long a,size_t n){(void)d;atc_calls++;atc_pasid=p;atc_start=a;atc_size=n;return 0;}

static void __arm_smmu_tlb_inv_range(struct arm_smmu_cmdq_ent *cmd,
				     unsigned long iova, size_t size,
				     size_t granule,
				     struct arm_smmu_domain *smmu_domain)
{
	struct arm_smmu_device *smmu = smmu_domain->smmu;
	unsigned long end = iova + size, num_pages = 0, tg = 0;
	size_t inv_range = granule;
	struct arm_smmu_cmdq_batch cmds;

	if (!size)
		return;

	if (smmu->features & ARM_SMMU_FEAT_RANGE_INV) {
		/* Get the leaf page size */
		tg = __ffs(smmu_domain->domain.pgsize_bitmap);

		/* Convert page size of 12,14,16 (log2) to 1,2,3 */
		cmd->tlbi.tg = (tg - 10) / 2;

		/*
		 * Determine what level the granule is at. For non-leaf, io-pgtable
		 * assumes .tlb_flush_walk can invalidate multiple levels at once,
		 * so ignore the nominal last-level granule and leave TTL=0.
		 */
		if (cmd->tlbi.leaf)
			cmd->tlbi.ttl = 4 - ((ilog2(granule) - 3) / (tg - 3));

		num_pages = size >> tg;
	}

	cmds.num = 0;

	while (iova < end) {
		if (smmu->features & ARM_SMMU_FEAT_RANGE_INV) {
			/*
			 * On each iteration of the loop, the range is 5 bits
			 * worth of the aligned size remaining.
			 * The range in pages is:
			 *
			 * range = (num_pages & (0x1f << __ffs(num_pages)))
			 */
			unsigned long scale, num;

			/* Determine the power of 2 multiple number of pages */
			scale = __ffs(num_pages);
			cmd->tlbi.scale = scale;

			/* Determine how many chunks of 2^scale size we have */
			num = (num_pages >> scale) & CMDQ_TLBI_RANGE_NUM_MAX;
			cmd->tlbi.num = num - 1;

			/* range is num * 2^scale * pgsize */
			inv_range = num << (scale + tg);

			/* Clear out the lower order bits for the next iteration */
			num_pages -= num << scale;
		}

		cmd->tlbi.addr = iova;
		arm_smmu_cmdq_batch_add(smmu, &cmds, cmd);
		iova += inv_range;
	}
	arm_smmu_cmdq_batch_submit(smmu, &cmds);
}
static void arm_smmu_tlb_inv_range_domain(unsigned long iova, size_t size,
					  size_t granule, bool leaf,
					  struct arm_smmu_domain *smmu_domain)
{
	struct arm_smmu_cmdq_ent cmd = {
		.tlbi = {
			.leaf	= leaf,
		},
	};

	if (smmu_domain->stage == ARM_SMMU_DOMAIN_S1) {
		cmd.opcode	= smmu_domain->smmu->features & ARM_SMMU_FEAT_E2H ?
				  CMDQ_OP_TLBI_EL2_VA : CMDQ_OP_TLBI_NH_VA;
		cmd.tlbi.asid	= smmu_domain->s1_cfg.cd.asid;
	} else {
		cmd.opcode	= CMDQ_OP_TLBI_S2_IPA;
		cmd.tlbi.vmid	= smmu_domain->s2_cfg.vmid;
	}
	__arm_smmu_tlb_inv_range(&cmd, iova, size, granule, smmu_domain);

	/*
	 * Unfortunately, this can't be leaf-only since we may have
	 * zapped an entire table.
	 */
	arm_smmu_atc_inv_domain(smmu_domain, IOMMU_NO_PASID, iova, size);
}
void arm_smmu_tlb_inv_range_asid(unsigned long iova, size_t size, int asid,
				 size_t granule, bool leaf,
				 struct arm_smmu_domain *smmu_domain)
{
	struct arm_smmu_cmdq_ent cmd = {
		.opcode	= smmu_domain->smmu->features & ARM_SMMU_FEAT_E2H ?
			  CMDQ_OP_TLBI_EL2_VA : CMDQ_OP_TLBI_NH_VA,
		.tlbi = {
			.asid	= asid,
			.leaf	= leaf,
		},
	};

	__arm_smmu_tlb_inv_range(&cmd, iova, size, granule, smmu_domain);
}
static void arm_smmu_tlb_inv_walk(unsigned long iova, size_t size,
				  size_t granule, void *cookie)
{
	arm_smmu_tlb_inv_range_domain(iova, size, granule, false, cookie);
}
static void arm_smmu_mm_arch_invalidate_secondary_tlbs(struct mmu_notifier *mn,
						struct mm_struct *mm,
						unsigned long start,
						unsigned long end)
{
	struct arm_smmu_mmu_notifier *smmu_mn = mn_to_smmu(mn);
	struct arm_smmu_domain *smmu_domain = smmu_mn->domain;
	size_t size;

	/*
	 * The mm_types defines vm_end as the first byte after the end address,
	 * different from IOMMU subsystem using the last address of an address
	 * range. So do a simple translation here by calculating size correctly.
	 */
	size = end - start;
	if (size == ULONG_MAX)
		size = 0;

	if (!(smmu_domain->smmu->features & ARM_SMMU_FEAT_BTM)) {
		if (!size)
			arm_smmu_tlb_inv_asid(smmu_domain->smmu,
					      smmu_mn->cd->asid);
		else
			arm_smmu_tlb_inv_range_asid(start, size,
						    smmu_mn->cd->asid,
						    PAGE_SIZE, false,
						    smmu_domain);
	}

	arm_smmu_atc_inv_domain(smmu_domain, mm->pasid, start, size);
}

int main(int argc,char **argv){
 if(argc!=9)return 2;
 unsigned long mode=strtoul(argv[1],0,0),pages=strtoul(argv[2],0,0),range=strtoul(argv[3],0,0),btm=strtoul(argv[4],0,0),e2h=strtoul(argv[5],0,0),stage=strtoul(argv[6],0,0);
 struct arm_smmu_device smmu={.features=(range?ARM_SMMU_FEAT_RANGE_INV:0)|(btm?ARM_SMMU_FEAT_BTM:0)|(e2h?ARM_SMMU_FEAT_E2H:0)};
 struct arm_smmu_domain d={.smmu=&smmu,.domain={.pgsize_bitmap=PAGE_SIZE|(PAGE_SIZE<<(PAGE_SHIFT-3))},.stage=stage,.s1_cfg={.cd={.asid=23}},.s2_cfg={.vmid=31}};
 struct cd cd={.asid=17};struct mm_struct mm={.pasid=19};struct arm_smmu_mmu_notifier mn={.domain=&d,.cd=&cd};
 unsigned long start=strtoul(argv[7],0,0),size=strtoul(argv[8],0,0)-start; (void)pages;
 if(mode==2){start=0;size=ULONG_MAX;}
 if(mode==1)arm_smmu_tlb_inv_walk(start,size,PAGE_SIZE,&d);
 else arm_smmu_mm_arch_invalidate_secondary_tlbs(&mn.mn,&mm,start,start+size);
 printf("META %u %d %d %d %d %lu %lu\n",recorded_count,asid_calls,asid_value,atc_calls,atc_pasid,atc_start,atc_size);
 for(unsigned int i=0;i<recorded_count;i++){struct arm_smmu_cmdq_ent *c=&recorded[i];printf("CMD %u %d %d %lu %lu %lu %lu %lu %u\n",c->opcode,c->tlbi.asid,c->tlbi.vmid,c->tlbi.addr,c->tlbi.ttl,c->tlbi.num,c->tlbi.scale,c->tlbi.tg,c->tlbi.leaf);}
 return 0;
}
