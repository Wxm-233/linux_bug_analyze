
#include <stdbool.h>
#include <stdlib.h>
#include <stdio.h>
#include <assert.h>
struct device {int coherent;};enum dma_data_direction {DMA_TO_DEVICE=1,DMA_FROM_DEVICE=2};
#define IS_ENABLED(x) (x)
#define ARCH_DMA_MINALIGN 128
#define IS_ALIGNED(x,a) (((x)&((a)-1))==0)
static bool dev_is_dma_coherent(struct device*d){return d->coherent;}
/* Deliberately registered allocator/cache assumptions, not target ABI facts. */
static size_t kmalloc_size_roundup(size_t n){assert(n==8||n==64||n==512);return n;}
static size_t dma_get_cache_alignment(void){return 64;}
static inline bool dma_kmalloc_safe(struct device *dev,
				    enum dma_data_direction dir)
{
	/*
	 * If DMA bouncing of kmalloc() buffers is disabled, the kmalloc()
	 * caches have already been aligned to a DMA-safe size.
	 */
	if (!IS_ENABLED(CONFIG_DMA_BOUNCE_UNALIGNED_KMALLOC))
		return true;

	/*
	 * kmalloc() buffers are DMA-safe irrespective of size if the device
	 * is coherent or the direction is DMA_TO_DEVICE (non-desctructive
	 * cache maintenance and benign cache line evictions).
	 */
	if (dev_is_dma_coherent(dev) || dir == DMA_TO_DEVICE)
		return true;

	return false;
}
static inline bool dma_kmalloc_size_aligned(size_t size)
{
	/*
	 * Larger kmalloc() sizes are guaranteed to be aligned to
	 * ARCH_DMA_MINALIGN.
	 */
	if (size >= 2 * ARCH_DMA_MINALIGN ||
	    IS_ALIGNED(kmalloc_size_roundup(size), dma_get_cache_alignment()))
		return true;

	return false;
}
static inline bool dma_kmalloc_needs_bounce(struct device *dev, size_t size,
					    enum dma_data_direction dir)
{
	return !dma_kmalloc_safe(dev, dir) && !dma_kmalloc_size_aligned(size);
}
int main(int argc,char**argv){assert(argc==4);struct device d={atoi(argv[1])};int dir=atoi(argv[2]);size_t size=strtoul(argv[3],0,0);bool b=dma_kmalloc_needs_bounce(&d,size,dir);assert(b==(CONFIG_DMA_BOUNCE_UNALIGNED_KMALLOC&&!d.coherent&&dir==DMA_FROM_DEVICE&&size==8));printf("BOUNCE %d\n",b);return 0;}
