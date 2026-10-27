
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
typedef uint64_t phys_addr_t;
enum dma_data_direction {DMA_TO_DEVICE=1,DMA_FROM_DEVICE=2,DMA_BIDIRECTIONAL=0};
struct device {int unused;};struct page {int unused;};
struct slot {phys_addr_t orig_addr;size_t alloc_size;};
struct io_tlb_pool {phys_addr_t start;unsigned char *vaddr;struct slot slots[4];};
#define IO_TLB_SHIFT 11
#define IO_TLB_SIZE (1UL<<IO_TLB_SHIFT)
#define PAGE_SIZE 4096UL
#define PAGE_MASK (~(PAGE_SIZE-1))
#define PFN_DOWN(a) ((a)/PAGE_SIZE)
#define INVALID_PHYS_ADDR (~0ULL)
#define DMA_ATTR_SKIP_CPU_SYNC 1
#define BUG_ON(x) assert(!(x))
#define dev_WARN_ONCE(...) ((void)0)
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
#define local_irq_save(f) do{(f)=0;}while(0)
#define local_irq_restore(f) ((void)(f))
static unsigned char original[4096],bounce[8192];static int copies,releases;static struct page pg;
static struct page *pfn_to_page(unsigned long n){(void)n;return &pg;}
static bool PageHighMem(struct page*p){(void)p;return false;}
static unsigned long swiotlb_align_offset(struct device*d,unsigned long x,phys_addr_t a){(void)d;(void)x;return a&(IO_TLB_SIZE-1);}
static void *phys_to_virt(phys_addr_t a){assert(a>=0x10000&&a<0x11000);return original+(a-0x10000);}
static void memcpy_from_page(void*v,struct page*p,unsigned o,unsigned n){(void)v;(void)p;(void)o;(void)n;abort();}
static void memcpy_to_page(struct page*p,unsigned o,void*v,unsigned n){(void)v;(void)p;(void)o;(void)n;abort();}
static void *copy_probe(void*d,const void*s,size_t n){copies++;printf("COPY %zu\n",n);return memmove(d,s,n);}
#define memcpy copy_probe
static bool swiotlb_del_transient(struct device*d,phys_addr_t a,struct io_tlb_pool*p){(void)d;(void)a;(void)p;return false;}
static void swiotlb_release_slots(struct device*d,phys_addr_t a,struct io_tlb_pool*p){(void)d;(void)a;(void)p;releases++;puts("RELEASE");}
static void swiotlb_bounce(struct device *dev, phys_addr_t tlb_addr, size_t size,
			   enum dma_data_direction dir, struct io_tlb_pool *mem)
{
	int index = (tlb_addr - mem->start) >> IO_TLB_SHIFT;
	phys_addr_t orig_addr = mem->slots[index].orig_addr;
	size_t alloc_size = mem->slots[index].alloc_size;
	unsigned long pfn = PFN_DOWN(orig_addr);
	unsigned char *vaddr = mem->vaddr + tlb_addr - mem->start;
	int tlb_offset;

	if (orig_addr == INVALID_PHYS_ADDR)
		return;

	/*
	 * It's valid for tlb_offset to be negative. This can happen when the
	 * "offset" returned by swiotlb_align_offset() is non-zero, and the
	 * tlb_addr is pointing within the first "offset" bytes of the second
	 * or subsequent slots of the allocated swiotlb area. While it's not
	 * valid for tlb_addr to be pointing within the first "offset" bytes
	 * of the first slot, there's no way to check for such an error since
	 * this function can't distinguish the first slot from the second and
	 * subsequent slots.
	 */
	tlb_offset = (tlb_addr & (IO_TLB_SIZE - 1)) -
		     swiotlb_align_offset(dev, 0, orig_addr);

	orig_addr += tlb_offset;
	alloc_size -= tlb_offset;

	if (size > alloc_size) {
		dev_WARN_ONCE(dev, 1,
			"Buffer overflow detected. Allocation size: %zu. Mapping size: %zu.\n",
			alloc_size, size);
		size = alloc_size;
	}

	if (PageHighMem(pfn_to_page(pfn))) {
		unsigned int offset = orig_addr & ~PAGE_MASK;
		struct page *page;
		unsigned int sz = 0;
		unsigned long flags;

		while (size) {
			sz = min_t(size_t, PAGE_SIZE - offset, size);

			local_irq_save(flags);
			page = pfn_to_page(pfn);
			if (dir == DMA_TO_DEVICE)
				memcpy_from_page(vaddr, page, offset, sz);
			else
				memcpy_to_page(page, offset, vaddr, sz);
			local_irq_restore(flags);

			size -= sz;
			pfn++;
			vaddr += sz;
			offset = 0;
		}
	} else if (dir == DMA_TO_DEVICE) {
		memcpy(vaddr, phys_to_virt(orig_addr), size);
	} else {
		memcpy(phys_to_virt(orig_addr), vaddr, size);
	}
}
void __swiotlb_tbl_unmap_single(struct device *dev, phys_addr_t tlb_addr,
		size_t mapping_size, enum dma_data_direction dir,
		unsigned long attrs, struct io_tlb_pool *pool)
{
	/*
	 * First, sync the memory before unmapping the entry
	 */
	if (!(attrs & DMA_ATTR_SKIP_CPU_SYNC) &&
	    (dir == DMA_FROM_DEVICE || dir == DMA_BIDIRECTIONAL))
		swiotlb_bounce(dev, tlb_addr, mapping_size,
						DMA_FROM_DEVICE, pool);

	if (swiotlb_del_transient(dev, tlb_addr, pool))
		return;
	swiotlb_release_slots(dev, tlb_addr, pool);
}
void __swiotlb_sync_single_for_cpu(struct device *dev, phys_addr_t tlb_addr,
		size_t size, enum dma_data_direction dir,
		struct io_tlb_pool *pool)
{
	if (dir == DMA_FROM_DEVICE || dir == DMA_BIDIRECTIONAL)
		swiotlb_bounce(dev, tlb_addr, size, DMA_FROM_DEVICE, pool);
	else
		BUG_ON(dir != DMA_TO_DEVICE);
}
int main(int argc,char**argv){assert(argc==4);int mode=atoi(argv[1]);unsigned off=atoi(argv[2]),written=atoi(argv[3]);struct device dev={0};struct io_tlb_pool pool={.start=0x20000,.vaddr=bounce,.slots={{.orig_addr=0x10000+off,.alloc_size=8}}};for(unsigned i=0;i<sizeof(original);i++)original[i]=(unsigned char)(i%251);memset(bounce,0xee,sizeof(bounce));unsigned char before[4096];memmove(before,original,sizeof(before));phys_addr_t tlb=pool.start+off;
/* The map allocator is not executed: supply the mapping record it would own,
 * then execute its original initial-copy primitive before simulated writes. */
swiotlb_bounce(&dev,tlb,8,DMA_TO_DEVICE,&pool);assert(!memcmp(bounce+off,original+off,8));for(unsigned i=0;i<written;i++)bounce[off+i]=0xa0+i;
if(mode==1)__swiotlb_sync_single_for_cpu(&dev,tlb,8,DMA_FROM_DEVICE,&pool);
__swiotlb_tbl_unmap_single(&dev,tlb,8,DMA_FROM_DEVICE,mode?DMA_ATTR_SKIP_CPU_SYNC:0,&pool);
for(unsigned i=0;i<sizeof(original);i++){unsigned char expected=before[i];if(mode!=2&&i>=off&&i<off+written)expected=0xa0+i-off;assert(original[i]==expected);}assert(releases==1&&copies==(mode==2?1:2));printf("RESULT mode=%d offset=%u written=%u copies=%d neighbors=preserved\n",mode,off,written,copies);}
