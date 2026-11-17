/*
 * (second round: page counts 1..16 and a sched_yield variant)
 * Diagnosis only (not a rule check): on the riscv N2r kernel, which variant of "unmap then read" still sees the
 * old data through a stale TLB entry?  Runs as /init, prints lines, powers off.
 *   size 4 KiB / 64 KiB  x  MADV_DONTNEED / munmap (read under SIGSEGV guard)
 * Also prints the CPU ISA string and the 64 KiB mTHP setting and counters.
 */
#define _GNU_SOURCE
#include <fcntl.h>
#include <setjmp.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <unistd.h>
#include <sched.h>

static sigjmp_buf jb;
static void segv(int s) { (void)s; siglongjmp(jb, 1); }

static void cat(const char *tag, const char *path)
{
	char buf[4096];
	int fd = open(path, O_RDONLY);
	int n = fd >= 0 ? read(fd, buf, sizeof(buf) - 1) : -1;
	if (fd >= 0)
		close(fd);
	buf[n > 0 ? n : 0] = 0;
	for (char *p = buf; *p; p++)
		if (*p == '\n')
			*p = ' ';
	printf("%s: %s\n", tag, n > 0 ? buf : "<none>");
}

static void isa(void)
{
	char buf[8192];
	int fd = open("/proc/cpuinfo", O_RDONLY);
	int n = fd >= 0 ? read(fd, buf, sizeof(buf) - 1) : -1;
	if (fd >= 0)
		close(fd);
	buf[n > 0 ? n : 0] = 0;
	char *p = strstr(buf, "isa");
	if (p) {
		char *e = strchr(p, '\n');
		if (e)
			*e = 0;
		printf("cpu %s\n", p);
	}
}

static int do_yield;
static void one(size_t sz, int use_munmap)
{
	int stale_pages = 0, faulted = 0, total = 0;
	for (int it = 0; it < 50; it++) {
		unsigned char *p = mmap(NULL, sz, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
		if (p == MAP_FAILED)
			return;
		memset(p, 0xCC, sz);
		if (do_yield)
			sched_yield();
		if (use_munmap)
			munmap(p, sz);
		else
			madvise(p, sz, MADV_DONTNEED);
		for (size_t off = 0; off < sz; off += 4096) {
			total++;
			if (sigsetjmp(jb, 1)) {
				faulted++;
				continue;
			}
			if (*(volatile unsigned char *)(p + off) == 0xCC)
				stale_pages++;
		}
		if (!use_munmap)
			munmap(p, sz);
	}
	printf("yield=%d size=%zuK op=%s pages_read=%d stale_0xCC=%d faulted=%d\n", do_yield, sz / 1024, use_munmap ? "munmap" : "dontneed",
	       total, stale_pages, faulted);
	fflush(stdout);
}

int main(void)
{
	mkdir("/proc", 0755);
	mkdir("/sys", 0755);
	mount("proc", "/proc", "proc", 0, NULL);
	mount("sysfs", "/sys", "sysfs", 0, NULL);
	signal(SIGSEGV, segv);
	isa();
	cat("thp_enabled", "/sys/kernel/mm/transparent_hugepage/enabled");
	cat("mthp64k_enabled", "/sys/kernel/mm/transparent_hugepage/hugepages-64kB/enabled");
	cat("mthp64k_fault_alloc_before", "/sys/kernel/mm/transparent_hugepage/hugepages-64kB/stats/anon_fault_alloc");
	for (int y = 0; y <= 1; y++) {
		do_yield = y;
		for (int pages = 1; pages <= 16; pages *= 2)
			one(pages * 4096, 0);
		one(3 * 4096, 0);
	}
	cat("mthp64k_fault_alloc_after", "/sys/kernel/mm/transparent_hugepage/hugepages-64kB/stats/anon_fault_alloc");
	printf("@@END\n");
	fflush(stdout);
	sync();
	reboot(RB_POWER_OFF);
	return 0;
}
