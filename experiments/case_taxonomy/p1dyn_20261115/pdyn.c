/* p1dyn criteria 四: dynamic checks for the two P1 suspects. Runs as /init (static), prints JSON lines, powers off.
 *   S1: smaps_pmd_entry reads pmd_young/pmd_dirty on a THP migration entry
 *   S2: folio_referenced_one clears young on a device-exclusive pte
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <sched.h>
#include <setjmp.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <unistd.h>

#define MB (1UL << 20)
#define PG 4096UL

static int wfile(const char *p, const char *v)
{
	int fd = open(p, O_WRONLY), r = -1;
	if (fd >= 0) {
		r = write(fd, v, strlen(v)) == (ssize_t)strlen(v) ? 0 : -errno;
		close(fd);
	} else
		r = -errno;
	return r;
}

/* ------------------------------------------------------------ S1 */
struct sm { long ahp, ref, lazy, pdirty, sdirty; int found; };

static char smbuf[1 << 20];

static void smaps_read(unsigned long start, struct sm *s)
{
	memset(s, 0, sizeof(*s));
	int fd = open("/proc/self/smaps", O_RDONLY);
	if (fd < 0)
		return;
	size_t n = 0;
	ssize_t r;
	while ((r = read(fd, smbuf + n, sizeof(smbuf) - 1 - n)) > 0)
		n += r;
	close(fd);
	smbuf[n] = 0;
	char key[32];
	snprintf(key, sizeof(key), "%lx-", start);
	char *p = smbuf;
	while (p && *p) {
		if (!strncmp(p, key, strlen(key)) && (p == smbuf || p[-1] == '\n'))
			break;
		p = strchr(p, '\n');
		if (p)
			p++;
	}
	if (!p || !*p)
		return;
	s->found = 1;
	p = strchr(p, '\n');
	while (p && *++p) {
		unsigned long a, b;
		if (sscanf(p, "%lx-%lx ", &a, &b) == 2)
			break;
		long v;
		if (sscanf(p, "AnonHugePages: %ld", &v) == 1) s->ahp = v;
		else if (sscanf(p, "Referenced: %ld", &v) == 1) s->ref = v;
		else if (sscanf(p, "LazyFree: %ld", &v) == 1) s->lazy = v;
		else if (sscanf(p, "Private_Dirty: %ld", &v) == 1) s->pdirty = v;
		else if (sscanf(p, "Shared_Dirty: %ld", &v) == 1) s->sdirty = v;
		p = strchr(p, '\n');
	}
}

static unsigned char *thp;
static volatile int mig_done;
static int mig_ok, mig_fail, mig_err;

static long move_one(void *addr, int node)
{
	void *pages[1] = { addr };
	int nodes[1] = { node }, status[1] = { -99 };
	long r = syscall(SYS_move_pages, 0, 1, pages, node < 0 ? NULL : nodes, status, 2 /* MPOL_MF_MOVE */);
	return r < 0 ? -errno - 1000 : status[0];
}

static void *migrator(void *arg)
{
	(void)arg;
	int cur = (int)move_one(thp, -1);
	for (int i = 0; i < 300; i++) {
		int tgt = cur == 0 ? 1 : 0;
		long st = move_one(thp, tgt);
		if (st == tgt) {
			mig_ok++;
			cur = tgt;
		} else if (st <= -1000)
			mig_err = (int)(-st - 1000);
		else
			mig_fail++;
	}
	mig_done = 1;
	return NULL;
}

static void S1(void)
{
	wfile("/sys/kernel/mm/transparent_hugepage/enabled", "always");
	wfile("/sys/kernel/mm/transparent_hugepage/defrag", "always");
	unsigned char *raw = mmap(NULL, 4 * MB, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
	thp = (unsigned char *)(((unsigned long)raw + 2 * MB - 1) & ~(2 * MB - 1));
	madvise(thp, 2 * MB, MADV_HUGEPAGE);
	memset(thp, 0x5a, 2 * MB);
	struct sm s0, s1;
	smaps_read((unsigned long)thp, &s0);
	int fr = madvise(thp, 2 * MB, MADV_FREE);
	smaps_read((unsigned long)thp, &s1);
	long node0 = move_one(thp, -1);
	/* baseline */
	long bmin[3] = { 1L << 40, 1L << 40, 1L << 40 }, bmax[3] = { -1, -1, -1 };
	int bstable = 1;
	struct sm b;
	for (int i = 0; i < 200; i++) {
		smaps_read((unsigned long)thp, &b);
		long v[3] = { b.ref, b.lazy, b.pdirty };
		for (int k = 0; k < 3; k++) {
			if (v[k] < bmin[k]) bmin[k] = v[k];
			if (v[k] > bmax[k]) bmax[k] = v[k];
		}
		if (b.ahp != s1.ahp)
			bstable = 0;
	}
	if (bmin[0] != bmax[0] || bmin[1] != bmax[1] || bmin[2] != bmax[2])
		bstable = 0;
	/* migration phase */
	pthread_t th;
	pthread_create(&th, NULL, migrator, NULL);
	long samples = 0, a_ref = 0, a_lazy = 0, a_pd = 0, thp_samples = 0, max_ref = 0, min_lazy = 1L << 40, max_pd = 0, a_sd = 0, max_sd = 0;
	struct sm x;
	while (!mig_done) {
		smaps_read((unsigned long)thp, &x);
		samples++;
		if (x.ahp == 2048) thp_samples++;
		if (x.ref > bmax[0]) a_ref++;
		if (x.lazy < bmin[1]) a_lazy++;
		if (x.pdirty > bmax[2]) a_pd++;
		if (x.ref > max_ref) max_ref = x.ref;
		if (x.lazy < min_lazy) min_lazy = x.lazy;
		if (x.pdirty > max_pd) max_pd = x.pdirty;
		if (x.sdirty > b.sdirty) a_sd++;
		if (x.sdirty > max_sd) max_sd = x.sdirty;
	}
	pthread_join(th, NULL);
	struct sm e;
	smaps_read((unsigned long)thp, &e);
	int valid = bstable && mig_ok > 0 && e.ahp == 2048 && s1.ahp == 2048;
	printf("{\"t\":\"S1\",\"valid\":%d,\"thp_before\":%ld,\"lazy_after_free\":%ld,\"madv_free\":%d,\"node0\":%ld,"
	       "\"base\":{\"ref\":[%ld,%ld],\"lazy\":[%ld,%ld],\"pdirty\":[%ld,%ld],\"stable\":%d},"
	       "\"mig_ok\":%d,\"mig_fail\":%d,\"mig_errno\":%d,\"samples\":%ld,\"thp_samples\":%ld,"
	       "\"anom\":{\"ref\":%ld,\"lazy\":%ld,\"pdirty\":%ld},\"extreme\":{\"max_ref\":%ld,\"min_lazy\":%ld,\"max_pdirty\":%ld},"
	       "\"end\":{\"ahp\":%ld,\"ref\":%ld,\"lazy\":%ld,\"pdirty\":%ld},\"sdirty\":{\"base\":%ld,\"anom\":%ld,\"max\":%ld}}\n",
	       valid, s0.ahp, s1.lazy, fr, node0, bmin[0], bmax[0], bmin[1], bmax[1], bmin[2], bmax[2], bstable, mig_ok, mig_fail,
	       mig_err, samples, thp_samples, a_ref, a_lazy, a_pd, max_ref, min_lazy, max_pd, e.ahp, e.ref, e.lazy, e.pdirty, b.sdirty, a_sd, max_sd);
	fflush(stdout);
}

/* ------------------------------------------------------------ S2 */
struct hmm_dmirror_cmd { uint64_t addr, ptr, npages, cpages, faults; };
#define HMM_DMIRROR_EXCLUSIVE _IOWR('H', 0x05, struct hmm_dmirror_cmd)
#define HMM_DMIRROR_CHECK_EXCLUSIVE _IOWR('H', 0x06, struct hmm_dmirror_cmd)
#define NP 64

static sigjmp_buf jb;
static void on_bus(int s) { (void)s; siglongjmp(jb, 1); }
static void on_alarm(int s)
{
	(void)s;
	const char m[] = "{\"t\":\"S2hang\",\"hang\":1}\n";
	if (write(1, m, sizeof(m) - 1)) {}
	_exit(0);
}

struct pm { int present, swap, types[32]; };

static void pagemap(unsigned char *buf, struct pm *o, uint64_t *raw0)
{
	memset(o, 0, sizeof(*o));
	int fd = open("/proc/self/pagemap", O_RDONLY);
	for (int i = 0; i < NP; i++) {
		uint64_t e = 0;
		if (pread(fd, &e, 8, ((unsigned long)(buf + i * PG) / PG) * 8) != 8)
			e = 0;
		if (i == 0 && raw0) *raw0 = e;
		if (e >> 63 & 1) o->present++;
		else if (e >> 62 & 1) { o->swap++; o->types[e & 31]++; }
	}
	close(fd);
}

static void types_json(char *s, size_t n, struct pm *p)
{
	size_t k = snprintf(s, n, "{");
	for (int t = 0; t < 32; t++)
		if (p->types[t]) k += snprintf(s + k, n - k, "%s\"%d\":%d", k > 1 ? "," : "", t, p->types[t]);
	snprintf(s + k, n - k, "}");
}

static void S2(void)
{
	mkdir("/sys/fs/cgroup/t", 0755);
	char pid[32];
	snprintf(pid, sizeof(pid), "%d", getpid());
	int cg = wfile("/sys/fs/cgroup/t/cgroup.procs", pid);
	int fd = open("/dev/hmm_dmirror0", O_RDWR);
	if (fd < 0) {
		printf("{\"t\":\"S2\",\"valid\":0,\"why\":\"open /dev/hmm_dmirror0 errno %d\",\"cg\":%d}\n", errno, cg);
		fflush(stdout);
		return;
	}
	unsigned char *buf = mmap(NULL, NP * PG, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
	madvise(buf, NP * PG, MADV_NOHUGEPAGE);
	for (int i = 0; i < NP; i++)
		for (unsigned long j = 0; j < PG; j += 8)
			*(uint64_t *)(buf + i * PG + j) = 0xC0DE000000000000ULL | ((uint64_t)i << 32) | j;
	unsigned char *mirror = malloc(NP * PG);
	struct hmm_dmirror_cmd c = { (uint64_t)(unsigned long)buf, (uint64_t)(unsigned long)mirror, NP, 0, 0 };
	int ex = ioctl(fd, HMM_DMIRROR_EXCLUSIVE, &c) ? -errno : 0;
	struct pm p1, p2;
	uint64_t r1 = 0, r2 = 0;
	pagemap(buf, &p1, &r1);
	struct hmm_dmirror_cmd ck = { (uint64_t)(unsigned long)buf, 0, NP, 0, 0 };
	int chk1 = ioctl(fd, HMM_DMIRROR_CHECK_EXCLUSIVE, &ck) ? -errno : 0;
	int rec[3];
	for (int k = 0; k < 3; k++)
		rec[k] = wfile("/sys/fs/cgroup/t/memory.reclaim", "64M");
	pagemap(buf, &p2, &r2);
	int chk2 = ioctl(fd, HMM_DMIRROR_CHECK_EXCLUSIVE, &ck) ? -errno : 0;
	{
		char a1[256], a2[256];
		types_json(a1, sizeof(a1), &p1);
		types_json(a2, sizeof(a2), &p2);
		printf("{\"t\":\"S2a\",\"exclusive\":%d,\"check_before\":%d,\"check_after\":%d,\"reclaim\":[%d,%d,%d],\"before\":{\"present\":%d,\"swap\":%d,\"types\":%s},\"after\":{\"present\":%d,\"swap\":%d,\"types\":%s}}\n",
		       ex, chk1, chk2, rec[0], rec[1], rec[2], p1.present, p1.swap, a1, p2.present, p2.swap, a2);
		fflush(stdout);
	}
	signal(SIGALRM, on_alarm);
	alarm(30);
	signal(SIGBUS, on_bus);
	signal(SIGSEGV, on_bus);
	int bad = 0, bus = 0;
	for (int i = 0; i < NP; i++) {
		if (sigsetjmp(jb, 1)) {
			bus++;
			continue;
		}
		volatile uint64_t *q = (volatile uint64_t *)(buf + i * PG);
		for (unsigned long j = 0; j < PG; j += 8)
			if (q[j / 8] != (0xC0DE000000000000ULL | ((uint64_t)i << 32) | j)) {
				bad++;
				break;
			}
	}
	alarm(0);
	char t1[256], t2[256];
	types_json(t1, sizeof(t1), &p1);
	types_json(t2, sizeof(t2), &p2);
	int valid = ex == 0 && (p1.swap > 0 || chk1 == -EPERM);
	printf("{\"t\":\"S2\",\"valid\":%d,\"cg\":%d,\"exclusive\":%d,\"cpages\":%llu,\"check_before\":%d,\"check_after\":%d,"
	       "\"reclaim\":[%d,%d,%d],\"before\":{\"present\":%d,\"swap\":%d,\"types\":%s,\"raw0\":\"%llx\"},"
	       "\"after\":{\"present\":%d,\"swap\":%d,\"types\":%s,\"raw0\":\"%llx\"},\"bad_pages\":%d,\"sigbus\":%d}\n",
	       valid, cg, ex, (unsigned long long)c.cpages, chk1, chk2, rec[0], rec[1], rec[2], p1.present, p1.swap, t1,
	       (unsigned long long)r1, p2.present, p2.swap, t2, (unsigned long long)r2, bad, bus);
	fflush(stdout);
}

/* ------------------------------------------------------------ setup */
static int zram_swap(void)
{
	if (wfile("/sys/block/zram0/disksize", "64M"))
		return -1;
	int fd = open("/dev/zram0", O_RDWR);
	if (fd < 0)
		return -2;
	static unsigned char hdr[PG];
	memset(hdr, 0, sizeof(hdr));
	uint32_t *info = (uint32_t *)(hdr + 1024);
	info[0] = 1;                     /* version */
	info[1] = (64 * MB) / PG - 1;    /* last_page */
	info[2] = 0;                     /* nr_badpages */
	memcpy(hdr + PG - 10, "SWAPSPACE2", 10);
	if (write(fd, hdr, PG) != (ssize_t)PG)
		return -3;
	fsync(fd);
	close(fd);
	return syscall(SYS_swapon, "/dev/zram0", 0) ? -errno : 0;
}

static void child(void (*f)(void))
{
	pid_t p = fork();
	if (p == 0) {
		f();
		_exit(0);
	}
	int st;
	waitpid(p, &st, 0);
	if (!WIFEXITED(st))
		printf("{\"t\":\"CHILD\",\"signal\":%d}\n", WIFSIGNALED(st) ? WTERMSIG(st) : -1);
}

int main(void)
{
	mount("proc", "/proc", "proc", 0, NULL);
	mount("sysfs", "/sys", "sysfs", 0, NULL);
	mount("devtmpfs", "/dev", "devtmpfs", 0, NULL);
	int cgm = mount("cgroup2", "/sys/fs/cgroup", "cgroup2", 0, NULL) ? -errno : 0;
	int ctl = wfile("/sys/fs/cgroup/cgroup.subtree_control", "+memory");
	int zs = zram_swap();
	long nodes = 0;
	for (int n = 0; n < 4; n++) {
		char p[64];
		snprintf(p, sizeof(p), "/sys/devices/system/node/node%d", n);
		struct stat st;
		if (!stat(p, &st)) nodes++;
	}
	struct stat hs;
	printf("{\"t\":\"ENV\",\"cgroup2\":%d,\"memctl\":%d,\"zram_swap\":%d,\"numa_nodes\":%ld,\"hmm_dev\":%d}\n", cgm, ctl, zs, nodes,
	       stat("/dev/hmm_dmirror0", &hs) == 0);
	fflush(stdout);
	child(S1);
	child(S2);
	printf("@@END\n");
	fflush(stdout);
	sync();
	reboot(RB_POWER_OFF);
	return 0;
}
