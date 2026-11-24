/* lpaeinv criteria 三: /init for the Q2 stress test on arm LPAE. Freestanding (no libc): raw ARM EABI system calls.
 *   clang --target=armv7a-linux-gnueabihf -marm -O2 -ffreestanding -nostdlib -static -fno-pic -fuse-ld=lld -o init init.c
 * The parent mounts proc/sys/debugfs, sets THP=always, records /proc/vmstat, forks:
 *   A owner   : 8MB anonymous, 2MB aligned, MADV_HUGEPAGE, checkable word in every 4K page (read-only afterwards);
 *               loop { MADV_COLLAPSE; verify every page; mprotect across a 2MB boundary and back (split under the lock) }
 *   B splitter: loop { write "<pidA>,<start>,<end>" to /sys/kernel/debug/split_huge_pages }
 *   C remote  : loop { process_vm_readv the whole range and verify; read /proc/<pidA>/pagemap: count present / swap-type (migration
 *               entries during split_folio are normal, amendment 1) / neither (anomaly) }
 * then sleeps RUN_SECS, sets the stop flag, waits, prints counters and the vmstat deltas, powers off.
 */
typedef unsigned int u32;
typedef unsigned long long u64;

#define RUN_SECS 480

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
#define NR_fork 2
#define NR_read 3
#define NR_write 4
#define NR_open 5
#define NR_close 6
#define NR_getpid 20
#define NR_mount 21
#define NR_sync 36
#define NR_reboot 88
#define NR_wait4 114
#define NR_mprotect 125
#define NR_llseek 140
#define NR_nanosleep 162
#define NR_mmap2 192
#define NR_madvise 220
#define NR_exit_group 248
#define NR_process_vm_readv 376

#define LEN (8UL << 20)
#define NPG (LEN / 4096)
#define MAGIC 0x5a000000u

struct shared {
	volatile long stop, ready, pid_a;
	volatile long a_iter, a_collapse_ok, a_collapse_err, a_bad, a_mprot_err;
	volatile long b_iter, b_ok, b_err;
	volatile long c_iter, c_short, c_bad, c_pm_bad, c_pm_err, c_pm_swap;
	volatile long a_first_bad, c_first_bad, c_pm_first;
	volatile u64 c_pm_val;
};
static struct shared *S;
static unsigned long A;            /* region start (same address in every child: fork copies the parent's mappings) */

static unsigned long slen(const char *s) { unsigned long n = 0; while (s[n]) n++; return n; }
static void out(const char *s) { sc(NR_write, 1, (long)s, slen(s), 0, 0, 0); }
static void dec(long v)
{
	char b[24]; int i = 23; int neg = v < 0; unsigned long u = neg ? -v : v;
	b[i] = 0;
	do { b[--i] = '0' + u % 10; u /= 10; } while (u);
	if (neg) b[--i] = '-';
	out(b + i);
}
static void hex(u64 v)
{
	char b[19]; int i;
	b[0] = '0'; b[1] = 'x';
	for (i = 0; i < 16; i++) { int d = (v >> (60 - 4 * i)) & 15; b[2 + i] = d < 10 ? '0' + d : 'a' + d - 10; }
	b[18] = 0;
	out(b);
}
static void kv(const char *k, long v) { out("LPAEI "); out(k); out(" "); dec(v); out("\n"); }
static long wfile(const char *path, const char *s)
{
	long fd = sc(NR_open, (long)path, 1, 0, 0, 0, 0), r;
	if (fd < 0) return fd;
	r = sc(NR_write, fd, (long)s, slen(s), 0, 0, 0);
	sc(NR_close, fd, 0, 0, 0, 0, 0);
	return r;
}
static long vmstat(const char *key)
{
	static char buf[16384];
	long fd = sc(NR_open, (long)"/proc/vmstat", 0, 0, 0, 0, 0), n, tot = 0, kl = slen(key);
	if (fd < 0) return -1;
	while ((n = sc(NR_read, fd, (long)buf + tot, sizeof(buf) - 1 - tot, 0, 0, 0)) > 0 && tot < (long)sizeof(buf) - 1) tot += n;
	sc(NR_close, fd, 0, 0, 0, 0, 0);
	buf[tot] = 0;
	for (char *l = buf; *l;) {
		int m = 1;
		for (long i = 0; i < kl; i++) if (l[i] != key[i]) { m = 0; break; }
		if (m && l[kl] == ' ') { long v = 0; char *p = l + kl + 1; while (*p >= '0' && *p <= '9') v = v * 10 + (*p++ - '0'); return v; }
		while (*l && *l != '\n') l++;
		if (*l) l++;
	}
	return -2;
}
static void sleep_s(long s) { long ts[2] = { s, 0 }; sc(NR_nanosleep, (long)ts, 0, 0, 0, 0, 0); }
static void halt(void)
{
	sc(NR_sync, 0, 0, 0, 0, 0, 0);
	sc(NR_reboot, 0xfee1dead, 672274793, 0x4321fedc, 0, 0, 0);
	for (;;) sc(NR_exit, 0, 0, 0, 0, 0, 0);
}
static int check_page(const u32 *w, unsigned long i) { return w[0] == (MAGIC ^ (u32)i) && w[1023] == ~(MAGIC ^ (u32)i); }
static void put_num(char *c, int *k, unsigned long v, int hexa)
{
	char t[24]; int n = 0;
	if (hexa) { c[(*k)++] = '0'; c[(*k)++] = 'x'; do { int d = v & 15; t[n++] = d < 10 ? '0' + d : 'a' + d - 10; v >>= 4; } while (v); }
	else do { t[n++] = '0' + v % 10; v /= 10; } while (v);
	while (n) c[(*k)++] = t[--n];
}

static void owner(void)
{
	unsigned long i;
	for (i = 0; i < NPG; i++) {
		u32 *w = (u32 *)(A + i * 4096);
		w[0] = MAGIC ^ (u32)i;
		w[1023] = ~(MAGIC ^ (u32)i);
	}
	S->pid_a = sc(NR_getpid, 0, 0, 0, 0, 0, 0);
	S->ready = 1;
	while (!S->stop) {
		long r = sc(NR_madvise, A, LEN, 25 /* MADV_COLLAPSE */, 0, 0, 0);
		if (r == 0) S->a_collapse_ok++; else S->a_collapse_err++;
		for (i = 0; i < NPG; i++)
			if (!check_page((const u32 *)(A + i * 4096), i)) { if (S->a_first_bad < 0) S->a_first_bad = i; S->a_bad++; }
		if (sc(NR_mprotect, A + (1UL << 20), 2UL << 20, 1, 0, 0, 0) || sc(NR_mprotect, A + (1UL << 20), 2UL << 20, 3, 0, 0, 0))
			S->a_mprot_err++;
		S->a_iter++;
	}
	sc(NR_exit, 0, 0, 0, 0, 0, 0);
}

static void splitter(void)
{
	char cmd[96]; int k = 0;
	put_num(cmd, &k, S->pid_a, 0); cmd[k++] = ',';
	put_num(cmd, &k, A, 1); cmd[k++] = ',';
	put_num(cmd, &k, A + LEN, 1); cmd[k] = 0;
	while (!S->stop) {
		long r = wfile("/sys/kernel/debug/split_huge_pages", cmd);
		if (r > 0) S->b_ok++; else S->b_err++;
		S->b_iter++;
	}
	sc(NR_exit, 0, 0, 0, 0, 0, 0);
}

static void remote(unsigned long buf)
{
	char path[48]; int k = 0;
	static u64 pm[NPG];
	const char *pre = "/proc/";
	while (*pre) path[k++] = *pre++;
	put_num(path, &k, S->pid_a, 0);
	pre = "/pagemap"; while (*pre) path[k++] = *pre++;
	path[k] = 0;
	while (!S->stop) {
		unsigned long liov[2] = { buf, LEN }, riov[2] = { A, LEN }, i;
		long r = sc(NR_process_vm_readv, S->pid_a, (long)liov, 1, (long)riov, 1, 0);
		if (r != (long)LEN) S->c_short++;
		else
			for (i = 0; i < NPG; i++)
				if (!check_page((const u32 *)(buf + i * 4096), i)) { if (S->c_first_bad < 0) S->c_first_bad = i; S->c_bad++; }
		{
			long fd = sc(NR_open, (long)path, 0, 0, 0, 0, 0);
			u64 off = (u64)(A >> 12) * 8, res;
			if (fd < 0 || sc(NR_llseek, fd, (long)(off >> 32), (long)(off & 0xffffffffu), (long)&res, 0, 0) != 0 ||
			    sc(NR_read, fd, (long)pm, sizeof(pm), 0, 0, 0) != (long)sizeof(pm))
				S->c_pm_err++;
			else
				for (i = 0; i < NPG; i++)
					if ((pm[i] >> 63) & 1)
						;
					else if ((pm[i] >> 62) & 1)
						S->c_pm_swap++;              /* amendment 1: migration entries during split_folio are normal */
					else {
						if (S->c_pm_first < 0) { S->c_pm_first = i; S->c_pm_val = pm[i]; }
						S->c_pm_bad++;
					}
			if (fd >= 0) sc(NR_close, fd, 0, 0, 0, 0, 0);
		}
		S->c_iter++;
	}
	sc(NR_exit, 0, 0, 0, 0, 0, 0);
}

int main(void)
{
	unsigned long p, buf;
	long r, pa, pb, pc, s0, c0, s1, c1, st;

	out("LPAEI start\n");
	sc(NR_mount, (long)"proc", (long)"/proc", (long)"proc", 0, 0, 0);
	sc(NR_mount, (long)"sysfs", (long)"/sys", (long)"sysfs", 0, 0, 0);
	r = sc(NR_mount, (long)"debugfs", (long)"/sys/kernel/debug", (long)"debugfs", 0, 0, 0);
	kv("debugfs_mount", r);
	kv("thp_enable_write", wfile("/sys/kernel/mm/transparent_hugepage/enabled", "always"));
	S = (struct shared *)sc(NR_mmap2, 0, 4096, 3, 0x21 /* MAP_SHARED|MAP_ANONYMOUS */, -1, 0);
	S->a_first_bad = S->c_first_bad = S->c_pm_first = -1;
	p = sc(NR_mmap2, 0, LEN + (2UL << 20), 3, 0x22, -1, 0);
	A = (p + (2UL << 20) - 1) & ~((2UL << 20) - 1);
	kv("madvise_hugepage", sc(NR_madvise, A, LEN, 14, 0, 0, 0));
	buf = sc(NR_mmap2, 0, LEN, 3, 0x22, -1, 0);
	out("LPAEI region "); hex(A); out("\n");
	s0 = vmstat("thp_split_pmd"); c0 = vmstat("thp_collapse_alloc");
	out("LPAEI stress begin\n");
	pa = sc(NR_fork, 0, 0, 0, 0, 0, 0);
	if (pa == 0) owner();
	while (!S->ready) sleep_s(0);
	pb = sc(NR_fork, 0, 0, 0, 0, 0, 0);
	if (pb == 0) splitter();
	pc = sc(NR_fork, 0, 0, 0, 0, 0, 0);
	if (pc == 0) remote(buf);
	for (r = 0; r < RUN_SECS; r += 10) {
		sleep_s(10);
		out("LPAEI tick "); dec(r + 10); out(" a_iter "); dec(S->a_iter); out(" b_ok "); dec(S->b_ok); out(" c_iter "); dec(S->c_iter); out("\n");
	}
	S->stop = 1;
	sc(NR_wait4, pa, (long)&st, 0, 0, 0, 0);
	sc(NR_wait4, pb, (long)&st, 0, 0, 0, 0);
	sc(NR_wait4, pc, (long)&st, 0, 0, 0, 0);
	out("LPAEI stress end\n");
	s1 = vmstat("thp_split_pmd"); c1 = vmstat("thp_collapse_alloc");
	kv("thp_split_pmd_delta", s1 - s0);
	kv("thp_collapse_alloc_delta", c1 - c0);
	kv("a_iter", S->a_iter); kv("a_collapse_ok", S->a_collapse_ok); kv("a_collapse_err", S->a_collapse_err);
	kv("a_bad", S->a_bad); kv("a_first_bad", S->a_first_bad); kv("a_mprot_err", S->a_mprot_err);
	kv("b_iter", S->b_iter); kv("b_ok", S->b_ok); kv("b_err", S->b_err);
	kv("c_iter", S->c_iter); kv("c_short", S->c_short); kv("c_bad", S->c_bad); kv("c_first_bad", S->c_first_bad);
	kv("c_pm_bad", S->c_pm_bad); kv("c_pm_swap", S->c_pm_swap); kv("c_pm_err", S->c_pm_err); kv("c_pm_first", S->c_pm_first);
	out("LPAEI c_pm_val "); hex(S->c_pm_val); out("\n");
	out("LPAEI end\n");
	halt();
	return 0;
}

void *memset(void *d, int c, unsigned long n) { unsigned char *q = d; while (n--) *q++ = c; return d; }
void *memcpy(void *d, const void *s, unsigned long n) { unsigned char *q = d; const unsigned char *t = s; while (n--) *q++ = *t++; return d; }

__attribute__((naked, noreturn)) void _start(void)
{
	__asm__ volatile("bl main\n\tmov r7, #1\n\tsvc #0\n");
}
