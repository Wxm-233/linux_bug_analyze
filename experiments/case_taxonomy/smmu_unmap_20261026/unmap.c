
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
#define ARM_LPAE_MAX_LEVELS		4
#define ARM_LPAE_LVL_SHIFT(l,d)						\
	(((ARM_LPAE_MAX_LEVELS - (l)) * (d)->bits_per_level) +		\
	ilog2(sizeof(arm_lpae_iopte)))
#define ARM_LPAE_GRANULE(d)						\
	(sizeof(arm_lpae_iopte) << (d)->bits_per_level)
#define ARM_LPAE_PGD_SIZE(d)						\
	(sizeof(arm_lpae_iopte) << (d)->pgd_bits)
#define ARM_LPAE_PTES_PER_TABLE(d)					\
	(ARM_LPAE_GRANULE(d) >> ilog2(sizeof(arm_lpae_iopte)))
#define ARM_LPAE_PGD_IDX(l,d)						\
	((l) == (d)->start_level ? (d)->pgd_bits - (d)->bits_per_level : 0)
#define ARM_LPAE_LVL_IDX(a,l,d)						\
	(((u64)(a) >> ARM_LPAE_LVL_SHIFT(l,d)) &			\
	 ((1 << ((d)->bits_per_level + ARM_LPAE_PGD_IDX(l,d))) - 1))
#define ARM_LPAE_BLOCK_SIZE(l,d)	(1ULL << ARM_LPAE_LVL_SHIFT(l,d))
#define ARM_LPAE_PTE_TYPE_SHIFT		0
#define ARM_LPAE_PTE_TYPE_MASK		0x3
#define ARM_LPAE_PTE_TYPE_BLOCK		1
#define ARM_LPAE_PTE_TYPE_TABLE		3
#define ARM_LPAE_PTE_TYPE_PAGE		3
#define ARM_LPAE_PTE_ADDR_MASK		GENMASK_ULL(47,12)
#define iopte_type(pte)					\
	(((pte) >> ARM_LPAE_PTE_TYPE_SHIFT) & ARM_LPAE_PTE_TYPE_MASK)
#define iopte_deref(pte,d) __va(iopte_to_paddr(pte, d))
static inline bool iopte_leaf(arm_lpae_iopte pte, int lvl,
			      enum io_pgtable_fmt fmt)
{
	if (lvl == (ARM_LPAE_MAX_LEVELS - 1) && fmt != ARM_MALI_LPAE)
		return iopte_type(pte) == ARM_LPAE_PTE_TYPE_PAGE;

	return iopte_type(pte) == ARM_LPAE_PTE_TYPE_BLOCK;
}
static arm_lpae_iopte paddr_to_iopte(phys_addr_t paddr,
				     struct arm_lpae_io_pgtable *data)
{
	arm_lpae_iopte pte = paddr;

	/* Of the bits which overlap, either 51:48 or 15:12 are always RES0 */
	return (pte | (pte >> (48 - 12))) & ARM_LPAE_PTE_ADDR_MASK;
}
static phys_addr_t iopte_to_paddr(arm_lpae_iopte pte,
				  struct arm_lpae_io_pgtable *data)
{
	u64 paddr = pte & ARM_LPAE_PTE_ADDR_MASK;

	if (ARM_LPAE_GRANULE(data) < SZ_64K)
		return paddr;

	/* Rotate the packed high-order bits back to the top */
	return (paddr | (paddr << (48 - 12))) & (ARM_LPAE_PTE_ADDR_MASK << 4);
}
static void __arm_lpae_clear_pte(arm_lpae_iopte *ptep, struct io_pgtable_cfg *cfg)
{

	*ptep = 0;

	if (!cfg->coherent_walk)
		__arm_lpae_sync_pte(ptep, 1, cfg);
}
static void __arm_lpae_free_pgtable(struct arm_lpae_io_pgtable *data, int lvl,
				    arm_lpae_iopte *ptep)
{
	arm_lpae_iopte *start, *end;
	unsigned long table_size;

	if (lvl == data->start_level)
		table_size = ARM_LPAE_PGD_SIZE(data);
	else
		table_size = ARM_LPAE_GRANULE(data);

	start = ptep;

	/* Only leaf entries at the last level */
	if (lvl == ARM_LPAE_MAX_LEVELS - 1)
		end = ptep;
	else
		end = (void *)ptep + table_size;

	while (ptep != end) {
		arm_lpae_iopte pte = *ptep++;

		if (!pte || iopte_leaf(pte, lvl, data->iop.fmt))
			continue;

		__arm_lpae_free_pgtable(data, lvl + 1, iopte_deref(pte, data));
	}

	__arm_lpae_free_pages(start, table_size, &data->iop.cfg);
}
static size_t __arm_lpae_unmap(struct arm_lpae_io_pgtable *data,
			       struct iommu_iotlb_gather *gather,
			       unsigned long iova, size_t size, size_t pgcount,
			       int lvl, arm_lpae_iopte *ptep)
{
	arm_lpae_iopte pte;
	struct io_pgtable *iop = &data->iop;
	int i = 0, num_entries, max_entries, unmap_idx_start;

	/* Something went horribly wrong and we ran out of page table */
	if (WARN_ON(lvl == ARM_LPAE_MAX_LEVELS))
		return 0;

	unmap_idx_start = ARM_LPAE_LVL_IDX(iova, lvl, data);
	ptep += unmap_idx_start;
	pte = READ_ONCE(*ptep);
	if (WARN_ON(!pte))
		return 0;

	/* If the size matches this level, we're in the right place */
	if (size == ARM_LPAE_BLOCK_SIZE(lvl, data)) {
		max_entries = ARM_LPAE_PTES_PER_TABLE(data) - unmap_idx_start;
		num_entries = min_t(int, pgcount, max_entries);

		while (i < num_entries) {
			pte = READ_ONCE(*ptep);
			if (WARN_ON(!pte))
				break;

			__arm_lpae_clear_pte(ptep, &iop->cfg);

			if (!iopte_leaf(pte, lvl, iop->fmt)) {
				/* Also flush any partial walks */
				io_pgtable_tlb_flush_walk(iop, iova + i * size, size,
							  ARM_LPAE_GRANULE(data));
				__arm_lpae_free_pgtable(data, lvl + 1, iopte_deref(pte, data));
			} else if (!iommu_iotlb_gather_queued(gather)) {
				io_pgtable_tlb_add_page(iop, gather, iova + i * size, size);
			}

			ptep++;
			i++;
		}

		return i * size;
	} else if (iopte_leaf(pte, lvl, iop->fmt)) {
		/*
		 * Insert a table at the next level to map the old region,
		 * minus the part we want to unmap
		 */
		return arm_lpae_split_blk_unmap(data, gather, iova, size, pte,
						lvl + 1, ptep, pgcount);
	}

	/* Keep on walkin' */
	ptep = iopte_deref(pte, data);
	return __arm_lpae_unmap(data, gather, iova, size, pgcount, lvl + 1, ptep);
}
static size_t arm_lpae_unmap_pages(struct io_pgtable_ops *ops, unsigned long iova,
				   size_t pgsize, size_t pgcount,
				   struct iommu_iotlb_gather *gather)
{
	struct arm_lpae_io_pgtable *data = io_pgtable_ops_to_data(ops);
	struct io_pgtable_cfg *cfg = &data->iop.cfg;
	arm_lpae_iopte *ptep = data->pgd;
	long iaext = (s64)iova >> cfg->ias;

	if (WARN_ON(!pgsize || (pgsize & cfg->pgsize_bitmap) != pgsize || !pgcount))
		return 0;

	if (cfg->quirks & IO_PGTABLE_QUIRK_ARM_TTBR1)
		iaext = ~iaext;
	if (WARN_ON(iaext))
		return 0;

	return __arm_lpae_unmap(data, gather, iova, pgsize, pgcount,
				data->start_level, ptep);
}
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
