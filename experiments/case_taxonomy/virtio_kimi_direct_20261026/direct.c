
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <assert.h>
typedef uint64_t dma_addr_t;typedef uint64_t phys_addr_t;
enum dma_data_direction {DMA_FROM_DEVICE=2};
struct device {int force,capable,needs,active,coherent,bounce_fail;};
#define DMA_ATTR_MMIO 1
#define DMA_ATTR_SKIP_CPU_SYNC 2
#define DMA_MAPPING_ERROR (~0ULL)
#define unlikely(x) (x)
#define dev_WARN_ONCE(...) ((void)0)
static int bounce,for_device,for_cpu,cpu_all,bounce_cpu,clean,unmap;
static bool is_swiotlb_force_bounce(struct device*d){return d->force;}
static bool is_swiotlb_active(struct device*d){return d->active;}
static bool dev_is_dma_coherent(struct device*d){return d->coherent;}
static bool dma_capable(struct device*d,dma_addr_t a,size_t n,bool ram){(void)a;(void)n;(void)ram;return d->capable;}
static bool dma_kmalloc_needs_bounce(struct device*d,size_t n,enum dma_data_direction dir){assert(n==8&&dir==DMA_FROM_DEVICE);return d->needs;}
static dma_addr_t phys_to_dma(struct device*d,phys_addr_t a){(void)d;return a+0x100000;}
static phys_addr_t dma_to_phys(struct device*d,dma_addr_t a){(void)d;return a-0x100000;}
static dma_addr_t swiotlb_map(struct device*d,phys_addr_t a,size_t n,enum dma_data_direction dir,unsigned long attrs){(void)attrs;assert(a==0x10080&&n==8&&dir==DMA_FROM_DEVICE);bounce++;puts("BOUNCE_MAP");return d->bounce_fail?DMA_MAPPING_ERROR:0x190080;}
static void arch_sync_dma_for_device(phys_addr_t a,size_t n,enum dma_data_direction d){assert(a==0x10080&&n==8&&d==DMA_FROM_DEVICE);for_device++;puts("ARCH_DEVICE");}
static void arch_sync_dma_for_cpu(phys_addr_t a,size_t n,enum dma_data_direction d){assert((a==0x10080||a==0x90080)&&n==8&&d==DMA_FROM_DEVICE);for_cpu++;printf("ARCH_CPU %llu\n",(unsigned long long)a);}
static void arch_sync_dma_for_cpu_all(void){cpu_all++;puts("CPU_ALL");}
static void swiotlb_sync_single_for_cpu(struct device*d,phys_addr_t a,size_t n,enum dma_data_direction dir){(void)d;(void)a;(void)n;(void)dir;bounce_cpu++;puts("SWIOTLB_CPU_HELPER");}
static void arch_dma_mark_clean(phys_addr_t a,size_t n){(void)a;(void)n;clean++;puts("MARK_CLEAN");}
static void swiotlb_tbl_unmap_single(struct device*d,phys_addr_t a,size_t n,enum dma_data_direction dir,unsigned long attrs){(void)d;(void)a;assert(n==8&&dir==DMA_FROM_DEVICE&&(attrs&DMA_ATTR_SKIP_CPU_SYNC));unmap++;puts("SWIOTLB_UNMAP_HELPER");}
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
int main(int argc,char**argv){assert(argc==4);int mode=atoi(argv[1]),coherent=atoi(argv[2]),skip=atoi(argv[3]);struct device d={.force=mode==1||mode==6||mode==9,.capable=mode!=2&&mode!=4&&mode!=8,.needs=mode==3||mode==5,.active=mode!=4&&mode!=5,.coherent=coherent,.bounce_fail=mode==6};unsigned long attrs=(skip?DMA_ATTR_SKIP_CPU_SYNC:0)|(mode>=7?DMA_ATTR_MMIO:0);dma_addr_t a=dma_direct_map_phys(&d,0x10080,8,DMA_FROM_DEVICE,attrs);bool fail=mode==4||mode==5||mode==6||mode==8||mode==9;assert((a==DMA_MAPPING_ERROR)==fail);assert(bounce==(mode==1||mode==2||mode==3||mode==6));assert(for_device==(mode==0&&!coherent&&!skip));if(!fail)dma_direct_unmap_phys(&d,a,8,DMA_FROM_DEVICE,attrs);bool cpu=!fail&&mode<7&&!skip;assert(for_cpu==(cpu&&!coherent)&&cpu_all==for_cpu&&bounce_cpu==cpu&&clean==cpu&&unmap==(!fail&&mode<7));printf("RESULT %llu %d %d %d %d %d %d %d\n",(unsigned long long)a,bounce,for_device,for_cpu,cpu_all,bounce_cpu,clean,unmap);return 0;}
