/* lpaeqemu criteria 二: /init for the arm LPAE QEMU test. Freestanding (no libc): raw ARM EABI system calls.
 *   clang --target=armv7a-linux-gnueabihf -marm -O2 -ffreestanding -nostdlib -static -fno-pic -fuse-ld=lld -o init init.c
 * Steps (each prints a marker first, so a crash or hang shows where it happened):
 *   mount proc/sys/debugfs; THP=always; show System RAM from /proc/iomem
 *   map 8MB anonymous, align 2MB, MADV_HUGEPAGE, write a checkable word into every 4K page
 *   pagemap + kpageflags before the split (PFN, present, THP)
 *   write "<pid>,<start>,<end>" to /sys/kernel/debug/split_huge_pages (THP split installs migration entries, then removes them)
 *   pagemap after the split; verify every page; power off
 */
typedef unsigned int u32;
typedef unsigned long long u64;

static long sc(long n, long a, long b, long c, long d, long e, long f)
{
	register long r0 __asm__("r0") = a;
	register long r1 __asm__("r1") = b;
	register long r2 __asm__("r2") = c;
	register long r3 __asm__("r3") = d;
	register long r4 __asm__("r4") = e;
	register long r5 __asm__("r5") = f;
	register long r7 __asm__("r7") = n;
	__asm__ volatile("svc #0" : "+r"(r0) : "r"(r1), "r"(r2), "r"(r3), "r"(r4), "r"(r5), "r"(r7) : "memory");
	return r0;
}

#define NR_exit 1
#define NR_read 3
#define NR_write 4
#define NR_open 5
#define NR_close 6
#define NR_getpid 20
#define NR_mount 21
#define NR_sync 36
#define NR_reboot 88
#define NR_llseek 140
#define NR_nanosleep 162
#define NR_mmap2 192
#define NR_madvise 220

static unsigned long slen(const char *s) { unsigned long n = 0; while (s[n]) n++; return n; }
static void out(const char *s) { sc(NR_write, 1, (long)s, slen(s), 0, 0, 0); }
static void hex(u64 v)
{
	char b[19]; int i;
	b[0] = '0'; b[1] = 'x';
	for (i = 0; i < 16; i++) { int d = (v >> (60 - 4 * i)) & 15; b[2 + i] = d < 10 ? '0' + d : 'a' + d - 10; }
	b[18] = 0;
	out(b);
}
static void dec(long v)
{
	char b[24]; int i = 23; int neg = v < 0; unsigned long u = neg ? -v : v;
	b[i] = 0;
	do { b[--i] = '0' + u % 10; u /= 10; } while (u);
	if (neg) b[--i] = '-';
	out(b + i);
}
static long wfile(const char *path, const char *s)
{
	long fd = sc(NR_open, (long)path, 1, 0, 0, 0, 0), r;
	if (fd < 0) return fd;
	r = sc(NR_write, fd, (long)s, slen(s), 0, 0, 0);
	sc(NR_close, fd, 0, 0, 0, 0, 0);
	return r;
}
static void catfile(const char *path, const char *only)
{
	static char buf[16384];
	long fd = sc(NR_open, (long)path, 0, 0, 0, 0, 0), n, tot = 0;
	if (fd < 0) { out("open failed "); out(path); out("\n"); return; }
	while ((n = sc(NR_read, fd, (long)buf + tot, sizeof(buf) - 1 - tot, 0, 0, 0)) > 0 && tot < (long)sizeof(buf) - 1) tot += n;
	sc(NR_close, fd, 0, 0, 0, 0, 0);
	buf[tot] = 0;
	/* print lines containing `only` */
	{
		char *l = buf;
		while (*l) {
			char *e = l; const char *o; int hit = 0;
			while (*e && *e != '\n') e++;
			for (char *p = l; p + slen(only) <= e && !hit; p++) {
				int k = 0;
				for (o = only; *o && p[k] == *o; o++, k++);
				if (!*o) hit = 1;
			}
			if (hit) { char c = *e; *e = 0; out("  "); out(l); out("\n"); *e = c; }
			l = *e ? e + 1 : e;
		}
	}
}
static u64 rd64(const char *path, u64 off)
{
	long fd = sc(NR_open, (long)path, 0, 0, 0, 0, 0);
	u64 v = ~0ULL, res;
	if (fd < 0) return ~0ULL - 1;
	if (sc(NR_llseek, fd, (long)(off >> 32), (long)(off & 0xffffffffu), (long)&res, 0, 0) == 0)
		if (sc(NR_read, fd, (long)&v, 8, 0, 0, 0) != 8) v = ~0ULL;
	sc(NR_close, fd, 0, 0, 0, 0, 0);
	return v;
}
static void show_pm(const char *tag, unsigned long base, int page)
{
	u64 e = rd64("/proc/self/pagemap", (u64)((base >> 12) + page) * 8);
	out(tag); out(" page "); dec(page); out(" pagemap "); hex(e);
	out(" present "); dec((e >> 63) & 1); out(" swap "); dec((e >> 62) & 1);
	if ((e >> 63) & 1) {
		u64 pfn = e & ((1ULL << 55) - 1), kf = rd64("/proc/kpageflags", pfn * 8);
		out(" pfn "); hex(pfn); out(pfn >= (1ULL << 24) ? " (>=2^24)" : " (<2^24)");
		out(" kpageflags "); hex(kf); out(" thp "); dec((kf >> 22) & 1);
	}
	out("\n");
}
static void halt(void)
{
	sc(NR_sync, 0, 0, 0, 0, 0, 0);
	sc(NR_reboot, 0xfee1dead, 672274793, 0x4321fedc, 0, 0, 0);
	for (;;) sc(NR_exit, 0, 0, 0, 0, 0, 0);
}

int main(void)
{
	unsigned long p, a, len = 4UL << 20, i;
	long r, pid, bad = 0, firstbad = -1;
	char cmd[96];
	int k = 0;

	out("LPAEQ start\n");
	sc(NR_mount, (long)"proc", (long)"/proc", (long)"proc", 0, 0, 0);
	sc(NR_mount, (long)"sysfs", (long)"/sys", (long)"sysfs", 0, 0, 0);
	r = sc(NR_mount, (long)"debugfs", (long)"/sys/kernel/debug", (long)"debugfs", 0, 0, 0);
	out("LPAEQ debugfs mount "); dec(r); out("\n");
	r = wfile("/sys/kernel/mm/transparent_hugepage/enabled", "always");
	out("LPAEQ thp enable write "); dec(r); out("\n");
	out("LPAEQ iomem System RAM:\n");
	catfile("/proc/iomem", "System RAM");

	p = sc(NR_mmap2, 0, 8UL << 20, 3, 0x22, -1, 0);
	if ((long)p < 0 && (long)p > -4096) { out("LPAEQ mmap failed\n"); halt(); }
	a = (p + (2UL << 20) - 1) & ~((2UL << 20) - 1);
	r = sc(NR_madvise, a, len, 14, 0, 0, 0);
	out("LPAEQ region "); hex(a); out(" madvise "); dec(r); out("\n");
	for (i = 0; i < len / 4096; i++) {
		u32 *w = (u32 *)(a + i * 4096);
		w[0] = 0x5a000000u ^ (u32)i;
		w[1023] = ~(0x5a000000u ^ (u32)i);
	}
	out("LPAEQ before split\n");
	show_pm("LPAEQ pre", a, 0); show_pm("LPAEQ pre", a, 1); show_pm("LPAEQ pre", a, 511); show_pm("LPAEQ pre", a, 512);

	pid = sc(NR_getpid, 0, 0, 0, 0, 0, 0);
	{
		/* "<pid>,0x<start>,0x<end>" */
		char t[24]; int n, j;
		long v = pid;
		n = 0; do { t[n++] = '0' + v % 10; v /= 10; } while (v);
		while (n) cmd[k++] = t[--n];
		cmd[k++] = ',';
		for (j = 0; j < 2; j++) {
			unsigned long x = j ? a + len : a;
			cmd[k++] = '0'; cmd[k++] = 'x';
			for (n = 7; n >= 0; n--) { int d = (x >> (4 * n)) & 15; cmd[k++] = d < 10 ? '0' + d : 'a' + d - 10; }
			if (!j) cmd[k++] = ',';
		}
		cmd[k] = 0;
	}
	out("LPAEQ split cmd "); out(cmd); out("\n");
	r = wfile("/sys/kernel/debug/split_huge_pages", cmd);
	out("LPAEQ split write returned "); dec(r); out("\n");

	out("LPAEQ after split: pagemap\n");
	show_pm("LPAEQ post", a, 0); show_pm("LPAEQ post", a, 1); show_pm("LPAEQ post", a, 511); show_pm("LPAEQ post", a, 512);
	show_pm("LPAEQ post", a, 1023);

	out("LPAEQ after split: verify\n");
	for (i = 0; i < len / 4096; i++) {
		u32 *w = (u32 *)(a + i * 4096);
		if (w[0] != (0x5a000000u ^ (u32)i) || w[1023] != ~(0x5a000000u ^ (u32)i)) {
			if (firstbad < 0) firstbad = i;
			bad++;
		}
	}
	out("LPAEQ verify bad "); dec(bad); out(" first "); dec(firstbad); out("\n");
	out("LPAEQ end\n");
	halt();
	return 0;
}

void *memset(void *d, int c, unsigned long n) { unsigned char *p = d; while (n--) *p++ = c; return d; }
void *memcpy(void *d, const void *s, unsigned long n) { unsigned char *p = d; const unsigned char *q = s; while (n--) *p++ = *q++; return d; }

__attribute__((naked, noreturn)) void _start(void)
{
	__asm__ volatile("bl main\n\tmov r7, #1\n\tsvc #0\n");
}
