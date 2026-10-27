
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
static void io_pgtable_tlb_flush_walk(struct io_pgtable*i,unsigned long a,size_t n,size_t g){(void)i;assert(root[a/n]==0);puts("PARENT_CLEAR_OBSERVED");walks++;last_addr=a;last_size=n;last_return=1;printf("WALK %lu %zu %zu\n",a,n,g);puts("WALK_RETURN");}
static void io_pgtable_tlb_add_page(struct io_pgtable*i,struct iommu_iotlb_gather*g,unsigned long a,size_t n){(void)i;(void)g;adds++;printf("ADD %lu %zu\n",a,n);}
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
static void __arm_lpae_init_pte(struct arm_lpae_io_pgtable *data,
				phys_addr_t paddr, arm_lpae_iopte prot,
				int lvl, int num_entries, arm_lpae_iopte *ptep)
{
	arm_lpae_iopte pte = prot;
	struct io_pgtable_cfg *cfg = &data->iop.cfg;
	size_t sz = ARM_LPAE_BLOCK_SIZE(lvl, data);
	int i;

	if (data->iop.fmt != ARM_MALI_LPAE && lvl == ARM_LPAE_MAX_LEVELS - 1)
		pte |= ARM_LPAE_PTE_TYPE_PAGE;
	else
		pte |= ARM_LPAE_PTE_TYPE_BLOCK;

	for (i = 0; i < num_entries; i++)
		ptep[i] = pte | paddr_to_iopte(paddr + i * sz, data);

	if (!cfg->coherent_walk)
		__arm_lpae_sync_pte(ptep, num_entries, cfg);
}
static arm_lpae_iopte arm_lpae_install_table(arm_lpae_iopte *table,
					     arm_lpae_iopte *ptep,
					     arm_lpae_iopte curr,
					     struct arm_lpae_io_pgtable *data)
{
	arm_lpae_iopte old, new;
	struct io_pgtable_cfg *cfg = &data->iop.cfg;

	new = paddr_to_iopte(__pa(table), data) | ARM_LPAE_PTE_TYPE_TABLE;
	if (cfg->quirks & IO_PGTABLE_QUIRK_ARM_NS)
		new |= ARM_LPAE_PTE_NSTABLE;

	/*
	 * Ensure the table itself is visible before its PTE can be.
	 * Whilst we could get away with cmpxchg64_release below, this
	 * doesn't have any ordering semantics when !CONFIG_SMP.
	 */
	dma_wmb();

	old = cmpxchg64_relaxed(ptep, curr, new);

	if (cfg->coherent_walk || (old & ARM_LPAE_PTE_SW_SYNC))
		return old;

	/* Even if it's not ours, there's no point waiting; just kick it */
	__arm_lpae_sync_pte(ptep, 1, cfg);
	if (old == curr)
		WRITE_ONCE(*ptep, new | ARM_LPAE_PTE_SW_SYNC);

	return old;
}
static size_t arm_lpae_split_blk_unmap(struct arm_lpae_io_pgtable *data,
				       struct iommu_iotlb_gather *gather,
				       unsigned long iova, size_t size,
				       arm_lpae_iopte blk_pte, int lvl,
				       arm_lpae_iopte *ptep, size_t pgcount)
{
	struct io_pgtable_cfg *cfg = &data->iop.cfg;
	arm_lpae_iopte pte, *tablep;
	phys_addr_t blk_paddr;
	size_t tablesz = ARM_LPAE_GRANULE(data);
	size_t split_sz = ARM_LPAE_BLOCK_SIZE(lvl, data);
	int ptes_per_table = ARM_LPAE_PTES_PER_TABLE(data);
	int i, unmap_idx_start = -1, num_entries = 0, max_entries;

	if (WARN_ON(lvl == ARM_LPAE_MAX_LEVELS))
		return 0;

	tablep = __arm_lpae_alloc_pages(tablesz, GFP_ATOMIC, cfg);
	if (!tablep)
		return 0; /* Bytes unmapped */

	if (size == split_sz) {
		unmap_idx_start = ARM_LPAE_LVL_IDX(iova, lvl, data);
		max_entries = ptes_per_table - unmap_idx_start;
		num_entries = min_t(int, pgcount, max_entries);
	}

	blk_paddr = iopte_to_paddr(blk_pte, data);
	pte = iopte_prot(blk_pte);

	for (i = 0; i < ptes_per_table; i++, blk_paddr += split_sz) {
		/* Unmap! */
		if (i >= unmap_idx_start && i < (unmap_idx_start + num_entries))
			continue;

		__arm_lpae_init_pte(data, blk_paddr, pte, lvl, 1, &tablep[i]);
	}

	pte = arm_lpae_install_table(tablep, ptep, blk_pte, data);
	if (pte != blk_pte) {
		__arm_lpae_free_pages(tablep, tablesz, cfg);
		/*
		 * We may race against someone unmapping another part of this
		 * block, but anything else is invalid. We can't misinterpret
		 * a page entry here since we're never at the last level.
		 */
		if (iopte_type(pte) != ARM_LPAE_PTE_TYPE_TABLE)
			return 0;

		tablep = iopte_deref(pte, data);
	} else if (unmap_idx_start >= 0) {
		for (i = 0; i < num_entries; i++)
			io_pgtable_tlb_add_page(&data->iop, gather, iova + i * size, size);

		return num_entries * size;
	}

	return __arm_lpae_unmap(data, gather, iova, size, pgcount, lvl, tablep);
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

int main(int argc,char**argv){assert(argc==4);mode=atoi(argv[1]);int coherent=atoi(argv[2]),queued=atoi(argv[3]);struct arm_lpae_io_pgtable d={.bits_per_level=PAGE_SHIFT-3,.pgd_bits=PAGE_SHIFT-3,.start_level=2,.iop={.cfg={.ias=48,.coherent_walk=coherent},.fmt=ARM_64_LPAE_S1}};
size_t gran=ARM_LPAE_GRANULE(&d),block=ARM_LPAE_BLOCK_SIZE(2,&d),entries=ARM_LPAE_PTES_PER_TABLE(&d);d.iop.cfg.pgsize_bitmap=gran|block;root=aligned_alloc(gran,gran);assert(root);memset(root,0,gran);root[1]=1;d.pgd=root;
if(mode==2){competitor=aligned_alloc(gran,gran);assert(competitor);for(size_t i=0;i<entries;i++)competitor[i]=paddr_to_iopte(i*gran,&d)|3;}
size_t index=mode==4?entries-1:3,count=2,expected=mode==4?1:2;unsigned long address=block+index*gran;struct iommu_iotlb_gather gather={.queued=queued};
size_t done=arm_lpae_unmap_pages(&d.iop.ops,address,gran,count,&gather);assert(!walks&&allocs==1);
if(mode==1){assert(!done&&!installs&&!frees&&root[1]==1&&!adds);}
else if(mode==3){assert(!done&&installs==1&&frees==1&&!root[1]&&!adds);}
else{assert(done==expected*gran&&installs==1);assert(adds==(int)((mode==2&&queued)?0:expected));assert(frees==(mode==2));arm_lpae_iopte*t=iopte_deref(root[1],&d);for(size_t i=0;i<entries;i++){if(i>=index&&i<index+expected)assert(t[i]==0);else assert(iopte_leaf(t[i],3,d.iop.fmt)&&iopte_to_paddr(t[i],&d)==i*gran);}free(t);}
printf("RESULT %zu %d %d %d %d %d %d %d %d %d\n",done,allocs,installs,adds,frees,barriers,init_sync,install_sync,clear_sync,warnings);free(root);return 0;}
