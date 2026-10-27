
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
int main(int argc,char**argv){assert(argc==7);int action=atoi(argv[1]);unsigned dmin=atoi(argv[2]),cwg=atoi(argv[3]);unsigned long start=strtoul(argv[4],0,0),size=strtoul(argv[5],0,0);int dir=atoi(argv[6]);assert(dmin>=4&&dmin<=5&&size>0&&size<1024);ctr_fixture=((uint64_t)dmin<<16)|((uint64_t)cwg<<24);if(action==0)arch_sync_dma_for_device(start,size,dir);else arch_sync_dma_for_cpu(start,size,dir);for(uint64_t i=0;i<ntrace;i++)printf("%llu %llu\n",(unsigned long long)trace[i][0],(unsigned long long)trace[i][1]);return 0;}
