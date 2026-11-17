/*
 * Diagnosis only, third round: is the multi-page "no stale entry" on riscv caused by the eager sfence.vma that
 * riscv issues after every page fault (update_mmu_cache_range), if QEMU turns each sfence.vma into a full flush?
 * After memset, re-read every page (refills TLB entries without faulting), then MADV_DONTNEED, then read the pages
 * again and record, per page position, whether it still returned the old 0xCC.
 *   order A: forward (page 0 first)   order B: backward (last page first)
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <unistd.h>

static void run(int pages, int backward, int refill)
{
	int stale_at[16] = {0};
	for (int it = 0; it < 20; it++) {
		size_t sz = pages * 4096UL;
		unsigned char *p = mmap(NULL, sz, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
		memset(p, 0xCC, sz);
		if (refill)
			for (int i = 0; i < pages; i++)
				(void)*(volatile unsigned char *)(p + i * 4096UL);
		madvise(p, sz, MADV_DONTNEED);
		for (int k = 0; k < pages; k++) {
			int i = backward ? pages - 1 - k : k;
			if (*(volatile unsigned char *)(p + i * 4096UL) == 0xCC)
				stale_at[i]++;
		}
		munmap(p, sz);
	}
	printf("pages=%d refill=%d order=%s stale_count_per_page(20 iterations)=", pages, refill, backward ? "backward" : "forward");
	for (int i = 0; i < pages; i++)
		printf("%d%s", stale_at[i], i + 1 < pages ? "," : "\n");
	fflush(stdout);
}

int main(void)
{
	mkdir("/proc", 0755);
	mount("proc", "/proc", "proc", 0, NULL);
	for (int refill = 0; refill <= 1; refill++) {
		run(2, 0, refill);
		run(2, 1, refill);
		run(8, 0, refill);
		run(8, 1, refill);
	}
	printf("@@END\n");
	fflush(stdout);
	sync();
	reboot(RB_POWER_OFF);
	return 0;
}
