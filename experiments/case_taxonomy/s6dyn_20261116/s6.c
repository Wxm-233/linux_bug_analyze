/* s6dyn criteria 三: S6 = shmem force branch hands an order beyond MAX_PAGECACHE_ORDER to anon shmem (arm64 64K).
 * Runs as /init (static), prints JSON lines, powers off. Page size and PMD size are read at run time.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>

#ifndef MADV_PAGEOUT
#define MADV_PAGEOUT 21
#endif

static int wfile(const char *p, const char *v)
{
	int fd = open(p, O_WRONLY), r;
	if (fd < 0)
		return -errno;
	r = write(fd, v, strlen(v)) == (ssize_t)strlen(v) ? 0 : -errno;
	close(fd);
	return r;
}

static int rfile(const char *p, char *b, size_t n)
{
	int fd = open(p, O_RDONLY);
	if (fd < 0)
		return -errno;
	ssize_t k = read(fd, b, n - 1);
	close(fd);
	if (k < 0)
		return -errno;
	b[k] = 0;
	for (char *q = b; *q; q++)
		if (*q == '\n')
			*q = 0;
	return 0;
}

static int zram_swap(long pg)
{
	if (wfile("/sys/block/zram0/disksize", "64M"))
		return -1;
	int fd = open("/dev/zram0", O_RDWR);
	if (fd < 0)
		return -2;
	unsigned char *hdr = calloc(1, pg);
	uint32_t *info = (uint32_t *)(hdr + 1024);
	info[0] = 1;
	info[1] = (64L << 20) / pg - 1;
	memcpy(hdr + pg - 10, "SWAPSPACE2", 10);
	if (write(fd, hdr, pg) != (ssize_t)pg)
		return -3;
	fsync(fd);
	close(fd);
	return syscall(SYS_swapon, "/dev/zram0", 0) ? -errno : 0;
}

static uint64_t pm(int fd, unsigned char *a, long pg)
{
	uint64_t e = 0;
	if (pread(fd, &e, 8, ((unsigned long)a / pg) * 8) != 8)
		e = 0;
	return e;
}

static uint64_t kpf(uint64_t e)
{
	if (!(e >> 63 & 1))
		return ~0ULL;
	uint64_t pfn = e & ((1ULL << 55) - 1), f = ~0ULL;
	int fd = open("/proc/kpageflags", O_RDONLY);
	if (fd >= 0) {
		if (pread(fd, &f, 8, pfn * 8) != 8)
			f = ~0ULL;
		close(fd);
	}
	return f;
}

static long shmem_pmd_kb(void)
{
	FILE *f = fopen("/proc/self/smaps", "r");
	char l[256];
	long s = 0, v;
	if (!f)
		return -1;
	while (fgets(l, sizeof(l), f))
		if (sscanf(l, "ShmemPmdMapped: %ld kB", &v) == 1)
			s += v;
	fclose(f);
	return s;
}

static int count_present(unsigned char *buf, long n, long pg)
{
	int fd = open("/proc/self/pagemap", O_RDONLY), c = 0;
	for (long i = 0; i < n; i++)
		c += pm(fd, buf + i * pg, pg) >> 63 & 1;
	close(fd);
	return c;
}

int main(void)
{
	mount("proc", "/proc", "proc", 0, NULL);
	mount("sysfs", "/sys", "sysfs", 0, NULL);
	mount("devtmpfs", "/dev", "devtmpfs", 0, NULL);
	printf("{\"t\":\"BOOT\"}\n");
	fflush(stdout);
	long pg = sysconf(_SC_PAGESIZE);
	char b[256] = {0};
	rfile("/sys/kernel/mm/transparent_hugepage/hpage_pmd_size", b, sizeof(b));
	long pmd = strtol(b, NULL, 10);
	printf("{\"t\":\"PRE_ZRAM\",\"pmd\":%ld}\n", pmd);
	fflush(stdout);
	int zs = zram_swap(pg);
	char cmd[512] = {0}, want[16] = "";
	rfile("/proc/cmdline", cmd, sizeof(cmd));
	char *m = strstr(cmd, "s6mode=");
	if (m)
		sscanf(m + 7, "%15[a-z_]", want);
	int wr = want[0] ? wfile("/sys/kernel/mm/transparent_hugepage/shmem_enabled", want) : -1;
	char cur[128] = {0};
	rfile("/sys/kernel/mm/transparent_hugepage/shmem_enabled", cur, sizeof(cur));
	char sel[32] = "";
	char *lb = strchr(cur, '['), *rb = lb ? strchr(lb, ']') : NULL;
	if (lb && rb && rb - lb - 1 < (long)sizeof(sel))
		memcpy(sel, lb + 1, rb - lb - 1);
	printf("{\"t\":\"ENV\",\"page\":%ld,\"pmd\":%ld,\"zram_swap\":%d,\"want\":\"%s\",\"write\":%d,\"selected\":\"%s\",\"mode_ok\":%d}\n",
	       pg, pmd, zs, want, wr, sel, strcmp(sel, want) == 0);
	fflush(stdout);
	if (pmd <= 0) {
		printf("{\"t\":\"S6\",\"valid\":0,\"why\":\"no pmd size\"}\n@@END\n");
		fflush(stdout);
		reboot(RB_POWER_OFF);
	}
	unsigned char *raw = mmap(NULL, 2 * pmd, PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANONYMOUS, -1, 0);
	if (raw == MAP_FAILED) {
		printf("{\"t\":\"S6\",\"valid\":0,\"why\":\"mmap errno %d\"}\n@@END\n", errno);
		fflush(stdout);
		reboot(RB_POWER_OFF);
	}
	unsigned char *buf = (unsigned char *)(((unsigned long)raw + pmd - 1) & ~(pmd - 1));
	long n = pmd / pg;
	printf("{\"t\":\"S6start\"}\n");
	fflush(stdout);
	for (long i = 0; i < n; i++)
		*(uint64_t *)(buf + i * pg) = 0xC0DE000000000000ULL | (uint64_t)i;
	int fd = open("/proc/self/pagemap", O_RDONLY);
	uint64_t f0 = kpf(pm(fd, buf, pg)), fn = kpf(pm(fd, buf + (n - 1) * pg, pg));
	close(fd);
	int head = f0 != ~0ULL && (f0 >> 15 & 1), tail = fn != ~0ULL && (fn >> 16 & 1);
	long spk = shmem_pmd_kb();
	int pres1 = count_present(buf, n, pg);
	printf("{\"t\":\"S6a\",\"pages\":%ld,\"head0\":%d,\"tailN\":%d,\"whole_pmd_folio\":%d,\"kpf0\":\"%llx\",\"kpfN\":\"%llx\","
	       "\"shmem_pmd_kb\":%ld,\"present_before\":%d}\n",
	       n, head, tail, head && tail, (unsigned long long)f0, (unsigned long long)fn, spk, pres1);
	fflush(stdout);
	int po = madvise(buf, pmd, MADV_PAGEOUT) ? -errno : 0;
	int pres2 = count_present(buf, n, pg);
	int rm = madvise(buf + (n / 2) * pg, pg, MADV_REMOVE) ? -errno : 0;
	printf("{\"t\":\"S6b\",\"pageout\":%d,\"present_after_pageout\":%d,\"remove\":%d}\n", po, pres2, rm);
	fflush(stdout);
	long bad = 0;
	for (long i = 0; i < n; i++) {
		uint64_t v = *(volatile uint64_t *)(buf + i * pg);
		uint64_t exp = i == n / 2 ? 0 : (0xC0DE000000000000ULL | (uint64_t)i);
		bad += v != exp;
	}
	printf("{\"t\":\"S6\",\"valid\":1,\"bad\":%ld}\n@@END\n", bad);
	fflush(stdout);
	sync();
	reboot(RB_POWER_OFF);
	return 0;
}
