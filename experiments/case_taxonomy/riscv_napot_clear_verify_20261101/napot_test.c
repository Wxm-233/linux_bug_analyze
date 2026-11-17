/*
 * /init for the NAPOT clear verification (plan.md). Scenarios:
 *   P: poison a 64K hugetlb page with UFFDIO_POISON, munmap, map normal anon memory at the same address, read 16 pages.
 *   M: as P, but mremap the hugetlb page away instead of munmap.
 *   C: control, populate the hugetlb page (present), munmap, map normal anon memory, read 16 pages.
 * Each scenario uses its own 2MB region, which also holds a populated normal page so its page table stays alive.
 * Prints one RESULT line per scenario and powers off.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/userfaultfd.h>
#include <setjmp.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/syscall.h>
#include <unistd.h>

#ifndef MAP_HUGE_SHIFT
#define MAP_HUGE_SHIFT 26
#endif
#define MAP_HUGE_64KB (16U << MAP_HUGE_SHIFT)
#define SZ4K 0x1000UL
#define SZ64K 0x10000UL
#define SZ2M 0x200000UL

static sigjmp_buf jump;
static volatile sig_atomic_t last_sig;

static void on_signal(int sig)
{
	last_sig = sig;
	siglongjmp(jump, 1);
}

/* 0..255: byte read; -1: SIGBUS; -2: SIGSEGV */
static int probe(volatile char *p)
{
	last_sig = 0;
	if (sigsetjmp(jump, 1))
		return last_sig == SIGBUS ? -1 : -2;
	return (unsigned char)*p;
}

static void cat(const char *path)
{
	char buf[256];
	int fd = open(path, O_RDONLY);
	ssize_t n;

	if (fd < 0) {
		printf("  %s: open failed (%s)\n", path, strerror(errno));
		return;
	}
	n = read(fd, buf, sizeof(buf) - 1);
	close(fd);
	buf[n > 0 ? n : 0] = 0;
	printf("  %s: %s", path, buf);
}

static void put(const char *path, const char *val)
{
	int fd = open(path, O_WRONLY);

	if (fd >= 0) {
		if (write(fd, val, strlen(val)) < 0)
			printf("  write %s failed (%s)\n", path, strerror(errno));
		close(fd);
	}
}

static int poison(char *addr)
{
	struct uffdio_api api = { .api = UFFD_API, .features = 0 };
	struct uffdio_register reg = { .range = { (uintptr_t)addr, SZ64K }, .mode = UFFDIO_REGISTER_MODE_MISSING };
	struct uffdio_poison p = { .range = { (uintptr_t)addr, SZ64K }, .mode = 0 };
	int fd = syscall(SYS_userfaultfd, O_CLOEXEC | O_NONBLOCK);

	if (fd < 0 || ioctl(fd, UFFDIO_API, &api) || ioctl(fd, UFFDIO_REGISTER, &reg)) {
		printf("  userfaultfd setup failed (%s)\n", strerror(errno));
		return -1;
	}
	if (!(reg.ioctls & (1ULL << _UFFDIO_POISON))) {
		printf("  UFFDIO_POISON not offered for this range\n");
		return -1;
	}
	if (ioctl(fd, UFFDIO_POISON, &p) || p.updated != (int64_t)SZ64K) {
		printf("  UFFDIO_POISON failed (%s), updated=%lld\n", strerror(errno), (long long)p.updated);
		return -1;
	}
	return fd;
}

static void scenario(char kind, char *region, char *dest)
{
	char *huge = region + SZ64K;
	char line[160];
	int i, n, bus = 0, zero = 0, fd = -1, pre = 0;

	printf("SCENARIO %c region=%p\n", kind, (void *)region);
	if (mmap(region, SZ64K, PROT_READ | PROT_WRITE, MAP_FIXED | MAP_PRIVATE | MAP_ANONYMOUS, -1, 0) == MAP_FAILED) {
		printf("RESULT %c precondition-failed neighbour mmap (%s)\n", kind, strerror(errno));
		return;
	}
	region[0] = 1; /* populate the page table shared with the hugetlb page */
	if (mmap(huge, SZ64K, PROT_READ | PROT_WRITE, MAP_FIXED | MAP_PRIVATE | MAP_ANONYMOUS | MAP_HUGETLB | MAP_HUGE_64KB,
		 -1, 0) == MAP_FAILED) {
		printf("RESULT %c precondition-failed hugetlb mmap (%s)\n", kind, strerror(errno));
		return;
	}
	if (kind == 'C') {
		huge[0] = 1;
	} else {
		fd = poison(huge);
		if (fd < 0) {
			printf("RESULT %c precondition-failed poison\n", kind);
			return;
		}
		pre = probe(huge + SZ4K);
		printf("  read of poisoned hugetlb page before unmap: %d (expect -1, SIGBUS)\n", pre);
		if (pre != -1) {
			printf("RESULT %c precondition-failed marker not effective\n", kind);
			return;
		}
	}
	if (kind == 'M') {
		if (mremap(huge, SZ64K, SZ64K, MREMAP_MAYMOVE | MREMAP_FIXED, dest) == MAP_FAILED) {
			printf("RESULT %c precondition-failed mremap (%s)\n", kind, strerror(errno));
			return;
		}
		printf("  read at mremap destination: %d (expect -1)\n", probe(dest + SZ4K));
	} else if (munmap(huge, SZ64K)) {
		printf("RESULT %c precondition-failed munmap (%s)\n", kind, strerror(errno));
		return;
	}
	if (mmap(huge, SZ64K, PROT_READ | PROT_WRITE, MAP_FIXED | MAP_PRIVATE | MAP_ANONYMOUS, -1, 0) == MAP_FAILED) {
		printf("RESULT %c precondition-failed anon remap (%s)\n", kind, strerror(errno));
		return;
	}
	n = snprintf(line, sizeof(line), "  pages:");
	for (i = 0; i < 16; i++) {
		int v = probe(huge + i * SZ4K);

		bus += v == -1;
		zero += v == 0;
		n += snprintf(line + n, sizeof(line) - n, " %d", v);
	}
	printf("%s\n", line);
	printf("RESULT %c zero=%d sigbus=%d other=%d\n", kind, zero, bus, 16 - zero - bus);
	if (fd >= 0)
		close(fd);
}

int main(void)
{
	struct sigaction sa = { .sa_handler = on_signal, .sa_flags = SA_NODEFER };
	char *base, *a;

	setvbuf(stdout, NULL, _IONBF, 0);
	mount("proc", "/proc", "proc", 0, NULL);
	mount("sysfs", "/sys", "sysfs", 0, NULL);
	sigaction(SIGBUS, &sa, NULL);
	sigaction(SIGSEGV, &sa, NULL);

	printf("NAPOT-TEST start\n");
	cat("/proc/version");
	put("/sys/kernel/mm/hugepages/hugepages-64kB/nr_hugepages", "16");
	cat("/sys/kernel/mm/hugepages/hugepages-64kB/nr_hugepages");
	cat("/sys/kernel/mm/hugepages/hugepages-64kB/free_hugepages");

	base = mmap(NULL, 10 * SZ2M, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_NORESERVE, -1, 0);
	if (base == MAP_FAILED) {
		printf("RESULT * precondition-failed reservation\n");
	} else {
		a = (char *)(((uintptr_t)base + SZ2M - 1) & ~(SZ2M - 1));
		scenario('C', a, NULL);
		scenario('P', a + 2 * SZ2M, NULL);
		scenario('M', a + 4 * SZ2M, a + 6 * SZ2M + SZ2M / 2);
	}
	cat("/sys/kernel/mm/hugepages/hugepages-64kB/free_hugepages");
	printf("NAPOT-TEST end\n");
	sync();
	reboot(RB_POWER_OFF);
	return 0;
}
