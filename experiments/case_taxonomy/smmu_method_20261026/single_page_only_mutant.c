
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
struct arm_smmu_device { unsigned int features; };
struct iommu_domain { unsigned long pgsize_bitmap; };
struct arm_smmu_domain {
    struct arm_smmu_device *smmu;
    struct iommu_domain domain;
};
struct arm_smmu_cmdq_ent {
    struct {
        bool leaf;
        unsigned long tg, ttl, scale, num, addr;
    } tlbi;
};
struct arm_smmu_cmdq_batch { unsigned int num; };
#define ARM_SMMU_FEAT_RANGE_INV 1U
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

		num_pages = size >> tg;

		/* Convert page size of 12,14,16 (log2) to 1,2,3 */
		cmd->tlbi.tg = (tg - 10) / 2;

		/*
		 * Determine what level the granule is at. For non-leaf, both
		 * io-pgtable and SVA pass a nominal last-level granule because
		 * they don't know what level(s) actually apply, so ignore that
		 * and leave TTL=0. However for various errata reasons we still
		 * want to use a range command, so avoid the SVA corner case
		 * where both scale and num could be 0 as well.
		 */
		if (cmd->tlbi.leaf)
			cmd->tlbi.ttl = 4 - ((ilog2(granule) - 3) / (tg - 3));
		else if (num_pages == 1)
			num_pages++;
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

int main(int argc, char **argv)
{
    if (argc != 5)
        return 2;
    unsigned long pages = strtoul(argv[1], NULL, 10);
    unsigned long shift = strtoul(argv[2], NULL, 10);
    bool leaf = strtoul(argv[3], NULL, 10) != 0;
    bool range = strtoul(argv[4], NULL, 10) != 0;
    struct arm_smmu_device smmu = { .features = range ? ARM_SMMU_FEAT_RANGE_INV : 0 };
    struct arm_smmu_domain domain = {
        .smmu = &smmu,
        .domain = { .pgsize_bitmap = 1UL << shift },
    };
    struct arm_smmu_cmdq_ent cmd = { .tlbi = { .leaf = leaf } };
    unsigned long granule = 1UL << shift;
    __arm_smmu_tlb_inv_range(&cmd, 0x100000UL, pages * granule,
                             granule, &domain);
    printf("%u\n", recorded_count);
    for (unsigned i = 0; i < recorded_count; i++) {
        struct arm_smmu_cmdq_ent *entry = &recorded[i];
        printf("%lu %lu %lu %lu %lu %u\n", entry->tlbi.addr,
               entry->tlbi.ttl, entry->tlbi.num, entry->tlbi.scale,
               entry->tlbi.tg, entry->tlbi.leaf);
    }
    return 0;
}
