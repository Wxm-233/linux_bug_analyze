// SPDX-License-Identifier: GPL-2.0
/*
 * Non-present 64K NAPOT hugetlb entries are only partially cleared on riscv.
 * Needs Svnapot and free 64kB hugepages (e.g. hugepagesz=64K hugepages=16).
 * Expected: all 16 pages read 0. Affected kernels: pages 1..15 raise SIGBUS.
 */
#define _GNU_SOURCE
#include <fcntl.h>
#include <linux/userfaultfd.h>
#include <setjmp.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <unistd.h>

#define SZ4K	0x1000UL
#define SZ64K	0x10000UL
#define SZ2M	0x200000UL
#define MAP_HUGE_64KB	(16U << 26)

static sigjmp_buf env;

static void on_sigbus(int sig)
{
	siglongjmp(env, 1);
}

static int readable(volatile char *p)
{
	if (sigsetjmp(env, 1))
		return 0;
	(void)*p;
	return 1;
}

int main(void)
{
	struct uffdio_api api = { .api = UFFD_API };
	struct uffdio_register reg = { .mode = UFFDIO_REGISTER_MODE_MISSING };
	struct uffdio_poison poison = { 0 };
	char *res, *a, *huge;
	int uffd, i, bad = 0;

	signal(SIGBUS, on_sigbus);
	res = mmap(NULL, 2 * SZ2M, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_NORESERVE, -1, 0);
	a = (char *)(((uintptr_t)res + SZ2M - 1) & ~(SZ2M - 1));
	huge = a + SZ64K;

	/* A populated neighbour keeps the PTE table alive across munmap(). */
	mmap(a, SZ64K, PROT_READ | PROT_WRITE, MAP_FIXED | MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
	a[0] = 1;
	if (mmap(huge, SZ64K, PROT_READ | PROT_WRITE,
		 MAP_FIXED | MAP_PRIVATE | MAP_ANONYMOUS | MAP_HUGETLB | MAP_HUGE_64KB, -1, 0) == MAP_FAILED) {
		perror("mmap 64K hugetlb");
		return 2;
	}

	/* Install a PTE_MARKER_POISONED: set_huge_pte_at() writes all 16 PTEs. */
	uffd = syscall(SYS_userfaultfd, O_CLOEXEC);
	reg.range.start = poison.range.start = (uintptr_t)huge;
	reg.range.len = poison.range.len = SZ64K;
	if (uffd < 0 || ioctl(uffd, UFFDIO_API, &api) || ioctl(uffd, UFFDIO_REGISTER, &reg) ||
	    ioctl(uffd, UFFDIO_POISON, &poison)) {
		perror("userfaultfd poison");
		return 2;
	}

	/* huge_pte_clear() sees !pte_napot() and clears only the first PTE. */
	munmap(huge, SZ64K);
	mmap(huge, SZ64K, PROT_READ | PROT_WRITE, MAP_FIXED | MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
	for (i = 0; i < 16; i++) {
		int ok = readable(huge + i * SZ4K);

		printf("page %2d: %s\n", i, ok ? "ok" : "SIGBUS");
		bad += !ok;
	}
	printf("%s: %d of 16 pages fault on fresh anonymous memory\n", bad ? "FAIL" : "PASS", bad);
	return bad ? 1 : 0;
}
