#include <stdio.h>
#include <stdlib.h>
#define PAGE_SIZE (1UL<<PAGE_SHIFT)
#define PAGE_MASK (~(PAGE_SIZE-1))
#define SZ_4K (1UL<<12)
#define SZ_16K (1UL<<14)
#define SZ_64K (1UL<<16)
#define SZ_2M (1UL<<21)
#define SZ_1G (1UL<<30)
#define SZ_32M (1UL<<25)
#define SZ_512M (1UL<<29)
#define __ffs(v) __builtin_ctzl(v)
#define __fls(v) (63-__builtin_clzl(v))
#define min(a,b) ((a)<(b)?(a):(b))
struct io_pgtable_cfg {unsigned long pgsize_bitmap;unsigned int ias,oas;};
static void arm_lpae_restrict_pgsizes(struct io_pgtable_cfg *cfg)
{
	unsigned long granule, page_sizes;
	unsigned int max_addr_bits = 48;

	/*
	 * We need to restrict the supported page sizes to match the
	 * translation regime for a particular granule. Aim to match
	 * the CPU page size if possible, otherwise prefer smaller sizes.
	 * While we're at it, restrict the block sizes to match the
	 * chosen granule.
	 */
	if (cfg->pgsize_bitmap & PAGE_SIZE)
		granule = PAGE_SIZE;
	else if (cfg->pgsize_bitmap & ~PAGE_MASK)
		granule = 1UL << __fls(cfg->pgsize_bitmap & ~PAGE_MASK);
	else if (cfg->pgsize_bitmap & PAGE_MASK)
		granule = 1UL << __ffs(cfg->pgsize_bitmap & PAGE_MASK);
	else
		granule = 0;

	switch (granule) {
	case SZ_4K:
		page_sizes = (SZ_4K | SZ_2M | SZ_1G);
		break;
	case SZ_16K:
		page_sizes = (SZ_16K | SZ_32M);
		break;
	case SZ_64K:
		max_addr_bits = 52;
		page_sizes = (SZ_64K | SZ_512M);
		if (cfg->oas > 48)
			page_sizes |= 1ULL << 42; /* 4TB */
		break;
	default:
		page_sizes = 0;
	}

	cfg->pgsize_bitmap &= page_sizes;
	cfg->ias = min(cfg->ias, max_addr_bits);
	cfg->oas = min(cfg->oas, max_addr_bits);
}
int main(int argc,char **argv){if(argc!=3)return 2;struct io_pgtable_cfg c={.pgsize_bitmap=strtoul(argv[1],0,0),.ias=52,.oas=strtoul(argv[2],0,0)};arm_lpae_restrict_pgsizes(&c);printf("%lu %u %u\n",c.pgsize_bitmap,c.ias,c.oas);return 0;}