
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <limits.h>
#include <assert.h>
struct list_head {struct list_head *next,*prev;};
#define LIST_HEAD_INIT(n) {&(n),&(n)}
struct iommu_iotlb_gather {unsigned long start,end;size_t pgsize;bool queued;struct list_head freelist;};
struct iommu_domain;struct ops {void(*iotlb_sync)(struct iommu_domain*,struct iommu_iotlb_gather*);};
struct iommu_domain {struct ops*ops;};struct arm_smmu_domain {struct iommu_domain domain;};
#define to_smmu_domain(p) ((struct arm_smmu_domain*)(p))
static int emitted;
static void arm_smmu_tlb_inv_range_domain(unsigned long a,size_t n,size_t g,bool leaf,struct arm_smmu_domain*d){(void)d;assert(leaf);emitted++;printf("RANGE %lu %zu %zu %d\n",a,n,g,leaf);}
static void arm_smmu_iotlb_sync(struct iommu_domain *domain,
				struct iommu_iotlb_gather *gather)
{
	struct arm_smmu_domain *smmu_domain = to_smmu_domain(domain);

	if (!gather->pgsize)
		return;

	arm_smmu_tlb_inv_range_domain(gather->start,
				      gather->end - gather->start + 1,
				      gather->pgsize, true, smmu_domain);
}
static inline void iommu_iotlb_gather_init(struct iommu_iotlb_gather *gather)
{
	*gather = (struct iommu_iotlb_gather) {
		.start	= ULONG_MAX,
		.freelist = LIST_HEAD_INIT(gather->freelist),
	};
}
static inline void iommu_iotlb_sync(struct iommu_domain *domain,
				  struct iommu_iotlb_gather *iotlb_gather)
{
	if (domain->ops->iotlb_sync)
		domain->ops->iotlb_sync(domain, iotlb_gather);

	iommu_iotlb_gather_init(iotlb_gather);
}
static inline
bool iommu_iotlb_gather_is_disjoint(struct iommu_iotlb_gather *gather,
				    unsigned long iova, size_t size)
{
	unsigned long start = iova, end = start + size - 1;

	return gather->end != 0 &&
		(end + 1 < gather->start || start > gather->end + 1);
}
static inline void iommu_iotlb_gather_add_range(struct iommu_iotlb_gather *gather,
						unsigned long iova, size_t size)
{
	unsigned long end = iova + size - 1;

	if (gather->start > iova)
		gather->start = iova;
	if (gather->end < end)
		gather->end = end;
}
static inline void iommu_iotlb_gather_add_page(struct iommu_domain *domain,
					       struct iommu_iotlb_gather *gather,
					       unsigned long iova, size_t size)
{
	/*
	 * If the new page is disjoint from the current range or is mapped at
	 * a different granularity, then sync the TLB so that the gather
	 * structure can be rewritten.
	 */
	if ((gather->pgsize && gather->pgsize != size) ||
	    iommu_iotlb_gather_is_disjoint(gather, iova, size))
		iommu_iotlb_sync(domain, gather);

	gather->pgsize = size;
	iommu_iotlb_gather_add_range(gather, iova, size);
}
static void arm_smmu_tlb_inv_page_nosync(struct iommu_iotlb_gather *gather,
					 unsigned long iova, size_t granule,
					 void *cookie)
{
	struct arm_smmu_domain *smmu_domain = cookie;
	struct iommu_domain *domain = &smmu_domain->domain;

	iommu_iotlb_gather_add_page(domain, gather, iova, granule);
}
int main(int argc,char**argv){assert(argc==2);struct ops ops={arm_smmu_iotlb_sync};struct arm_smmu_domain d={.domain={.ops=&ops}};struct iommu_iotlb_gather g;unsigned long a,n;iommu_iotlb_gather_init(&g);g.queued=atoi(argv[1]);while(scanf("%lu %lu",&a,&n)==2)arm_smmu_tlb_inv_page_nosync(&g,a,n,&d);printf("BEFORE_FINAL %d %lu %lu %zu\n",emitted,g.start,g.end,g.pgsize);iommu_iotlb_sync(&d.domain,&g);assert(g.start==ULONG_MAX&&!g.pgsize&&!g.end);printf("AFTER_FINAL %d\n",emitted);return 0;}
