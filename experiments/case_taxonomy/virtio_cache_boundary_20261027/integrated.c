
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
typedef uint64_t phys_addr_t;
enum dma_data_direction {DMA_TO_DEVICE=1,DMA_FROM_DEVICE=2};
uint64_t ctr_fixture,ntrace;uint64_t trace[256][2];
extern void dcache_clean_poc(unsigned long,unsigned long);
extern void dcache_inval_poc(unsigned long,unsigned long);
static void *phys_to_virt(phys_addr_t a){return (void*)(uintptr_t)a;}
void arch_sync_dma_for_device(phys_addr_t paddr, size_t size,
			      enum dma_data_direction dir)
{
	unsigned long start = (unsigned long)phys_to_virt(paddr);

	dcache_clean_poc(start, start + size);
}
void arch_sync_dma_for_cpu(phys_addr_t paddr, size_t size,
			   enum dma_data_direction dir)
{
	unsigned long start = (unsigned long)phys_to_virt(paddr);

	if (dir == DMA_TO_DEVICE)
		return;

	dcache_inval_poc(start, start + size);
}

#include <stdbool.h>
typedef uint64_t dma_addr_t;
struct device {bool force,coherent;uint64_t *dma_mask,bus_dma_limit;};struct io_tlb_pool {int unused;};
#define DMA_MAPPING_ERROR (~0ULL)
#define DMA_ATTR_MMIO 1
#define DMA_ATTR_SKIP_CPU_SYNC 2
#define unlikely(x) (x)
#define dev_WARN_ONCE(...) ((void)0)
static void mark(unsigned kind,uint64_t addr){trace[ntrace][0]=kind;trace[ntrace++][1]=addr;}
static bool is_swiotlb_force_bounce(struct device*d){return d->force;}
static bool is_swiotlb_active(struct device*d){(void)d;return true;}
static bool dev_is_dma_coherent(struct device*d){return d->coherent;}
static bool dma_capable(struct device*d,dma_addr_t a,size_t n,bool ram){(void)d;(void)a;(void)n;(void)ram;return true;}
static bool dma_kmalloc_needs_bounce(struct device*d,size_t n,enum dma_data_direction dir){(void)d;assert(n==8&&dir==DMA_FROM_DEVICE);return false;}
static dma_addr_t phys_to_dma(struct device*d,phys_addr_t a){(void)d;return a;}
static phys_addr_t dma_to_phys(struct device*d,dma_addr_t a){(void)d;return a;}
static dma_addr_t phys_to_dma_unencrypted(struct device*d,phys_addr_t a){(void)d;return a;}
static void arch_sync_dma_for_cpu_all(void){}
static void arch_dma_mark_clean(phys_addr_t a,size_t n){(void)a;(void)n;}
static void trace_swiotlb_bounced(struct device*d,dma_addr_t a,size_t n){(void)d;assert(a==0x10008&&n==8);}
static phys_addr_t swiotlb_tbl_map_single(struct device*d,phys_addr_t a,size_t n,unsigned align,enum dma_data_direction dir,unsigned long attrs){(void)d;assert(a==0x10008&&n==8&&align==0&&dir==DMA_FROM_DEVICE&&!attrs);mark(5,0x50008);return 0x50008;}
static struct io_tlb_pool *swiotlb_find_pool(struct device*d,phys_addr_t a){(void)d;(void)a;abort();}
static void __swiotlb_tbl_unmap_single(struct device*d,phys_addr_t a,size_t n,enum dma_data_direction dir,unsigned long attrs,struct io_tlb_pool*p){(void)d;(void)a;(void)n;(void)dir;(void)attrs;(void)p;abort();}
static void swiotlb_sync_single_for_cpu(struct device*d,phys_addr_t a,size_t n,enum dma_data_direction dir){(void)d;assert(n==8&&dir==DMA_FROM_DEVICE);if(a==0x50008)mark(6,0x10008);else assert(a==0x10008);}
static void swiotlb_tbl_unmap_single(struct device*d,phys_addr_t a,size_t n,enum dma_data_direction dir,unsigned long attrs){(void)d;assert(n==8&&dir==DMA_FROM_DEVICE&&attrs==DMA_ATTR_SKIP_CPU_SYNC);if(a==0x50008)mark(7,a);else assert(a==0x10008);}
dma_addr_t swiotlb_map(struct device *dev, phys_addr_t paddr, size_t size,
		enum dma_data_direction dir, unsigned long attrs)
{
	phys_addr_t swiotlb_addr;
	dma_addr_t dma_addr;

	trace_swiotlb_bounced(dev, phys_to_dma(dev, paddr), size);

	swiotlb_addr = swiotlb_tbl_map_single(dev, paddr, size, 0, dir, attrs);
	if (swiotlb_addr == (phys_addr_t)DMA_MAPPING_ERROR)
		return DMA_MAPPING_ERROR;

	/* Ensure that the address returned is DMA'ble */
	dma_addr = phys_to_dma_unencrypted(dev, swiotlb_addr);
	if (unlikely(!dma_capable(dev, dma_addr, size, true))) {
		__swiotlb_tbl_unmap_single(dev, swiotlb_addr, size, dir,
			attrs | DMA_ATTR_SKIP_CPU_SYNC,
			swiotlb_find_pool(dev, swiotlb_addr));
		dev_WARN_ONCE(dev, 1,
			"swiotlb addr %pad+%zu overflow (mask %llx, bus limit %llx).\n",
			&dma_addr, size, *dev->dma_mask, dev->bus_dma_limit);
		return DMA_MAPPING_ERROR;
	}

	if (!dev_is_dma_coherent(dev) && !(attrs & DMA_ATTR_SKIP_CPU_SYNC))
		arch_sync_dma_for_device(swiotlb_addr, size, dir);
	return dma_addr;
}
static inline void dma_direct_sync_single_for_cpu(struct device *dev,
		dma_addr_t addr, size_t size, enum dma_data_direction dir)
{
	phys_addr_t paddr = dma_to_phys(dev, addr);

	if (!dev_is_dma_coherent(dev)) {
		arch_sync_dma_for_cpu(paddr, size, dir);
		arch_sync_dma_for_cpu_all();
	}

	swiotlb_sync_single_for_cpu(dev, paddr, size, dir);

	if (dir == DMA_FROM_DEVICE)
		arch_dma_mark_clean(paddr, size);
}
static inline dma_addr_t dma_direct_map_phys(struct device *dev,
		phys_addr_t phys, size_t size, enum dma_data_direction dir,
		unsigned long attrs)
{
	dma_addr_t dma_addr;

	if (is_swiotlb_force_bounce(dev)) {
		if (attrs & DMA_ATTR_MMIO)
			goto err_overflow;

		return swiotlb_map(dev, phys, size, dir, attrs);
	}

	if (attrs & DMA_ATTR_MMIO) {
		dma_addr = phys;
		if (unlikely(!dma_capable(dev, dma_addr, size, false)))
			goto err_overflow;
	} else {
		dma_addr = phys_to_dma(dev, phys);
		if (unlikely(!dma_capable(dev, dma_addr, size, true)) ||
		    dma_kmalloc_needs_bounce(dev, size, dir)) {
			if (is_swiotlb_active(dev))
				return swiotlb_map(dev, phys, size, dir, attrs);

			goto err_overflow;
		}
	}

	if (!dev_is_dma_coherent(dev) &&
	    !(attrs & (DMA_ATTR_SKIP_CPU_SYNC | DMA_ATTR_MMIO)))
		arch_sync_dma_for_device(phys, size, dir);
	return dma_addr;

err_overflow:
	dev_WARN_ONCE(
		dev, 1,
		"DMA addr %pad+%zu overflow (mask %llx, bus limit %llx).\n",
		&dma_addr, size, *dev->dma_mask, dev->bus_dma_limit);
	return DMA_MAPPING_ERROR;
}
static inline void dma_direct_unmap_phys(struct device *dev, dma_addr_t addr,
		size_t size, enum dma_data_direction dir, unsigned long attrs)
{
	phys_addr_t phys;

	if (attrs & DMA_ATTR_MMIO)
		/* nothing to do: uncached and no swiotlb */
		return;

	phys = dma_to_phys(dev, addr);
	if (!(attrs & DMA_ATTR_SKIP_CPU_SYNC))
		dma_direct_sync_single_for_cpu(dev, addr, size, dir);

	swiotlb_tbl_unmap_single(dev, phys, size, dir,
					 attrs | DMA_ATTR_SKIP_CPU_SYNC);
}
int main(int argc,char**argv){assert(argc==4);int bounced=atoi(argv[1]),coherent=atoi(argv[2]),dmin=atoi(argv[3]);ctr_fixture=((uint64_t)dmin<<16)|(5ULL<<24);uint64_t mask=~0ULL;struct device d={.force=bounced,.coherent=coherent,.dma_mask=&mask,.bus_dma_limit=mask};dma_addr_t a=dma_direct_map_phys(&d,0x10008,8,DMA_FROM_DEVICE,0);assert(a==(bounced?0x50008:0x10008));dma_direct_unmap_phys(&d,a,8,DMA_FROM_DEVICE,0);for(uint64_t i=0;i<ntrace;i++)printf("%llu %llu\n",(unsigned long long)trace[i][0],(unsigned long long)trace[i][1]);}
