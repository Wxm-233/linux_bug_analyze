/*
 * (z5fix_20261115: copy of proprules_20261114/propsuite.c; only Z5 changed, see criteria)
 * Property rules R1 (zeroing), R2 (invalidation), R3 (instruction consistency) as user-space checks
 * (proprules criteria 二, amendment 1). Runs as /init. Each template: dirty memory + drop_caches in the
 * parent, then the template in a fresh child. One JSON line per template; "@@END"; power off.
 */
#define _GNU_SOURCE
#include <fcntl.h>
#include <pthread.h>
#include <setjmp.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

#define KB 1024UL
#define MB (1024UL * KB)
#define HPAGE (2 * MB)
#define PG 4096UL

static void wfile(const char *p, const char *v)
{
	int fd = open(p, O_WRONLY);
	if (fd >= 0) {
		if (write(fd, v, strlen(v)) < 0) {}
		close(fd);
	}
}

static long vmstat(const char *key)
{
	static char buf[65536];
	int fd = open("/proc/vmstat", O_RDONLY);
	if (fd < 0)
		return -1;
	int n = read(fd, buf, sizeof(buf) - 1);
	close(fd);
	if (n <= 0)
		return -1;
	buf[n] = 0;
	size_t kl = strlen(key);
	for (char *p = buf; p && *p; p = strchr(p, '\n') ? strchr(p, '\n') + 1 : NULL)
		if (!strncmp(p, key, kl) && p[kl] == ' ')
			return atol(p + kl + 1);
	return -1;
}

static void dirty(void)
{
	size_t sz = 512 * MB;
	unsigned char *d = mmap(NULL, sz, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
	if (d != MAP_FAILED) {
		memset(d, 0xA5, sz);
		munmap(d, sz);
	}
	wfile("/proc/sys/vm/drop_caches", "3");
}

static unsigned long count_nonzero(const unsigned char *p, size_t n, long *first)
{
	unsigned long c = 0;
	*first = -1;
	for (size_t i = 0; i < n; i++)
		if (((volatile const unsigned char *)p)[i]) {
			if (*first < 0)
				*first = (long)i;
			c++;
		}
	return c;
}

static void report(const char *t, int valid, int violated, const char *detail)
{
	printf("{\"t\":\"%s\",\"valid\":%d,\"violated\":%d,\"detail\":\"%s\"}\n", t, valid, violated, detail);
	fflush(stdout);
}

/* ---- R1 zeroing ---- */
static void z_simple(const char *t, unsigned char *p, size_t n, int ok, const char *extra)
{
	char d[200];
	long f;
	if (!ok) {
		report(t, 0, 0, extra);
		return;
	}
	unsigned long c = count_nonzero(p, n, &f);
	snprintf(d, sizeof(d), "bytes=%lu nonzero=%lu first=%ld val=%d %s", (unsigned long)n, c, f,
		 f >= 0 ? p[f] : -1, extra);
	report(t, 1, c > 0, d);
}

static void Z1(void)
{
	unsigned char *p = mmap(NULL, 64 * KB, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
	z_simple("Z1", p, 64 * KB, p != MAP_FAILED, "");
}

static void Z2(void)
{
	unsigned char *p = mmap(NULL, 64 * KB, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
	if (p == MAP_FAILED) {
		report("Z2", 0, 0, "mmap failed");
		return;
	}
	unsigned long c = 0;
	for (size_t pg = 0; pg < 64 * KB; pg += PG) {
		p[pg] = 1;
		long f;
		c += count_nonzero(p + pg + 1, PG - 1, &f);
	}
	char d[100];
	snprintf(d, sizeof(d), "nonzero=%lu", c);
	report("Z2", 1, c > 0, d);
}

static unsigned char *thp_area(int *madv)
{
	unsigned char *q = mmap(NULL, 8 * MB, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
	if (q == MAP_FAILED)
		return NULL;
	unsigned char *a = (unsigned char *)(((uintptr_t)q + HPAGE - 1) & ~(uintptr_t)(HPAGE - 1));
	*madv = madvise(a, 3 * HPAGE, MADV_HUGEPAGE);
	return a;
}

static void Z3(void)
{
	int madv = -2;
	long z0 = vmstat("thp_zero_page_alloc");
	unsigned char *a = thp_area(&madv);
	char e[80];
	if (a) {
		long f;
		unsigned long c = count_nonzero(a, 3 * HPAGE, &f);
		long z1 = vmstat("thp_zero_page_alloc");
		char d[200];
		snprintf(d, sizeof(d), "nonzero=%lu first=%ld val=%d zero_page_alloc_delta=%ld", c, f, f >= 0 ? a[f] : -1, z1 - z0);
		report("Z3", madv == 0 && z1 - z0 > 0, c > 0, d);
		return;
	}
	snprintf(e, sizeof(e), "mmap failed");
	report("Z3", 0, 0, e);
}

static void Z4(void)
{
	int madv = -2;
	long t0 = vmstat("thp_fault_alloc");
	unsigned char *a = thp_area(&madv);
	if (!a) {
		report("Z4", 0, 0, "mmap failed");
		return;
	}
	unsigned long c = 0;
	for (int i = 0; i < 3; i++) {
		long f;
		a[i * HPAGE] = 1;
		c += count_nonzero(a + i * HPAGE + 1, HPAGE - 1, &f);
	}
	long t1 = vmstat("thp_fault_alloc");
	char d[120];
	snprintf(d, sizeof(d), "nonzero=%lu thp_fault_alloc_delta=%ld", c, t1 - t0);
	report("Z4", madv == 0 && t1 - t0 > 0, c > 0, d);
}

static void Z5(void)
{
	unsigned char *p = mmap(NULL, 64 * KB, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
	if (p == MAP_FAILED) {
		report("Z5", 0, 0, "mmap failed");
		return;
	}
	memset(p, 0xCC, 64 * KB);
	/* z5fix: read every page once so its translation is cached again (reads do not fault, so riscv issues no
	 * sfence.vma that QEMU would turn into a full flush) before MADV_DONTNEED */
	for (size_t off = 0; off < 64 * KB; off += PG)
		(void)*(volatile unsigned char *)(p + off);
	int r = madvise(p, 64 * KB, MADV_DONTNEED);
	z_simple("Z5", p, 64 * KB, r == 0, "");
}

static void Z6(void)
{
	int fd = open("/z6file", O_CREAT | O_RDWR | O_TRUNC, 0644);
	unsigned char buf[100];
	memset(buf, 0xEE, sizeof(buf));
	int ok = fd >= 0 && write(fd, buf, sizeof(buf)) == (ssize_t)sizeof(buf);
	unsigned char *p = ok ? mmap(NULL, PG, PROT_READ, MAP_SHARED, fd, 0) : MAP_FAILED;
	if (p == MAP_FAILED) {
		report("Z6", 0, 0, "open/write/mmap failed");
		return;
	}
	z_simple("Z6", p + 100, PG - 100, 1, "");
}

static void Z7(void)
{
	int fd = memfd_create("z7", 0);
	int ok = fd >= 0 && ftruncate(fd, 64 * KB) == 0;
	unsigned char *p = ok ? mmap(NULL, 64 * KB, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0) : MAP_FAILED;
	z_simple("Z7", p, 64 * KB, p != MAP_FAILED, "");
}

static void Z8(void)
{
	unsigned char *old = sbrk(0);
	void *r = sbrk(64 * KB);
	z_simple("Z8", old, 64 * KB, r != (void *)-1 && old != (void *)-1, "");
}

static void Z9(void)
{
	unsigned char *p = mmap(NULL, 64 * KB, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
	if (p == MAP_FAILED) {
		report("Z9", 0, 0, "mmap failed");
		return;
	}
	memset(p, 0xCC, 64 * KB);
	unsigned char *q = mremap(p, 64 * KB, 128 * KB, MREMAP_MAYMOVE);
	z_simple("Z9", q + 64 * KB, 64 * KB, q != MAP_FAILED, "");
}

/* ---- R2 invalidation ---- */
static __thread sigjmp_buf jb;
static __thread volatile int in_probe;
static void segv(int s)
{
	(void)s;
	if (in_probe)
		siglongjmp(jb, 1);
	_exit(99);
}

static int faults_on_read(volatile unsigned char *p)
{
	in_probe = 1;
	if (sigsetjmp(jb, 1)) {
		in_probe = 0;
		return 1;
	}
	(void)*p;
	in_probe = 0;
	return 0;
}

static int faults_on_write(volatile unsigned char *p)
{
	in_probe = 1;
	if (sigsetjmp(jb, 1)) {
		in_probe = 0;
		return 1;
	}
	*p = 2;
	in_probe = 0;
	return 0;
}

static void T1(void)
{
	int bad = 0, ok = 1;
	for (int i = 0; i < 200; i++) {
		unsigned char *p = mmap(NULL, PG, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
		if (p == MAP_FAILED) {
			ok = 0;
			break;
		}
		p[0] = 1;
		if (munmap(p, PG)) {
			ok = 0;
			break;
		}
		if (!faults_on_read(p))
			bad++;
	}
	char d[80];
	snprintf(d, sizeof(d), "iterations=200 read_after_munmap_succeeded=%d", bad);
	report("T1", ok, bad > 0, d);
}

static void T2(void)
{
	int bad = 0, ok = 1;
	for (int i = 0; i < 200; i++) {
		unsigned char *p = mmap(NULL, PG, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
		if (p == MAP_FAILED) {
			ok = 0;
			break;
		}
		p[0] = 1;
		if (mprotect(p, PG, PROT_READ)) {
			ok = 0;
			break;
		}
		if (!faults_on_write(p))
			bad++;
		munmap(p, PG);
	}
	char d[80];
	snprintf(d, sizeof(d), "iterations=200 write_after_mprotect_ro_succeeded=%d", bad);
	report("T2", ok, bad > 0, d);
}

static volatile unsigned char *t3_page;
static volatile int t3_state;   /* 0 idle, 1 reading, 2 unmapped, 3 done */
static volatile int t3_bad, t3_reading_seen;

static void *t3_reader(void *arg)
{
	(void)arg;
	signal(SIGSEGV, segv);
	for (;;) {
		while (t3_state == 0)
			;
		if (t3_state == 3)
			return NULL;
		/* keep the translation hot on this CPU; a fault here (page already gone) is fine (amendment 2.2) */
		while (t3_state == 1)
			if (faults_on_read(t3_page)) {
				while (t3_state == 1)
					;
				break;
			}
		if (!faults_on_read(t3_page))
			t3_bad++;
		t3_state = 0;
	}
}

static void T3(void)
{
	pthread_t th;
	if (pthread_create(&th, NULL, t3_reader, NULL)) {
		report("T3", 0, 0, "pthread_create failed");
		return;
	}
	int ok = 1;
	for (int i = 0; i < 200; i++) {
		unsigned char *p = mmap(NULL, PG, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
		if (p == MAP_FAILED) {
			ok = 0;
			break;
		}
		p[0] = 1;
		t3_page = p;
		t3_state = 1;
		for (volatile int k = 0; k < 20000; k++)
			;
		if (munmap(p, PG)) {
			ok = 0;
			break;
		}
		t3_state = 2;
		while (t3_state == 2)
			;
	}
	t3_state = 3;
	pthread_join(th, NULL);
	char d[80];
	snprintf(d, sizeof(d), "iterations=200 cross_cpu_read_after_munmap_succeeded=%d", t3_bad);
	report("T3", ok, t3_bad > 0, d);
}

/* ---- R3 instruction consistency (amendment 1: write to a file, map it afresh, execute) ---- */
static size_t fn_code(unsigned char *b, unsigned n)
{
#if defined(__riscv)
	uint32_t w[2] = {(n << 20) | 0x513u, 0x00008067u};   /* li a0,n ; ret */
	memcpy(b, w, 8);
	return 8;
#elif defined(__aarch64__)
	uint32_t w[2] = {0x52800000u | (n << 5), 0xd65f03c0u};   /* mov w0,#n ; ret */
	memcpy(b, w, 8);
	return 8;
#elif defined(__x86_64__)
	b[0] = 0xB8;
	memcpy(b + 1, &n, 4);
	b[5] = 0xC3;   /* mov eax,n ; ret */
	return 6;
#endif
}

static void I1(void)
{
	int fd = open("/i1code", O_CREAT | O_RDWR | O_TRUNC, 0755);
	if (fd < 0 || ftruncate(fd, PG)) {
		report("I1", 0, 0, "open/ftruncate failed");
		return;
	}
	int bad = 0, ok = 1;
	for (unsigned n = 1; n <= 100; n++) {
		unsigned char b[16];
		size_t len = fn_code(b, n);
		if (pwrite(fd, b, len, 0) != (ssize_t)len) {
			ok = 0;
			break;
		}
		void *p = mmap(NULL, PG, PROT_READ | PROT_EXEC, MAP_PRIVATE, fd, 0);
		if (p == MAP_FAILED) {
			ok = 0;
			break;
		}
		int (*f)(void) = (int (*)(void))p;
		if ((unsigned)f() != n)
			bad++;
		munmap(p, PG);
	}
	char d[80];
	snprintf(d, sizeof(d), "iterations=100 stale_code_executed=%d", bad);
	report("I1", ok, bad > 0, d);
}

int main(void)
{
	mkdir("/proc", 0755);
	mkdir("/sys", 0755);
	mount("proc", "/proc", "proc", 0, NULL);
	mount("sysfs", "/sys", "sysfs", 0, NULL);
	wfile("/sys/kernel/mm/transparent_hugepage/enabled", "always");
	signal(SIGSEGV, segv);
	struct { const char *name; void (*fn)(void); } tests[] = {
		{"Z1", Z1}, {"Z2", Z2}, {"Z3", Z3}, {"Z4", Z4}, {"Z5", Z5}, {"Z6", Z6}, {"Z7", Z7}, {"Z8", Z8},
		{"Z9", Z9}, {"T1", T1}, {"T2", T2}, {"T3", T3}, {"I1", I1}};
	for (unsigned i = 0; i < sizeof(tests) / sizeof(tests[0]); i++) {
		/* amendment 2.1: each zeroing template is attempted 8 times, each in a fresh child after dirtying */
		int attempts = tests[i].name[0] == 'Z' ? 8 : 1;
		for (int at = 1; at <= attempts; at++) {
			dirty();
			pid_t pid = fork();
			if (pid == 0) {
				signal(SIGSEGV, segv);
				tests[i].fn();
				_exit(0);
			}
			int st = 0;
			waitpid(pid, &st, 0);
			if (!WIFEXITED(st) || WEXITSTATUS(st) != 0) {
				printf("{\"t\":\"%s\",\"valid\":0,\"violated\":0,\"detail\":\"child status %d\"}\n", tests[i].name, st);
				fflush(stdout);
			}
		}
	}
	printf("@@END\n");
	fflush(stdout);
	sync();
	reboot(RB_POWER_OFF);
	return 0;
}
