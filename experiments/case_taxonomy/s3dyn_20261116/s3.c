/* s3dyn criteria 三/四: /init for the suspect-3 test (ext4 DAX + userfaultfd async WP).
 * Records are one JSON object per line, prefixed by "@@R ".  Static x86_64 binary. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/userfaultfd.h>
#include <signal.h>
#include <stdarg.h>
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
#include <time.h>
#include <unistd.h>

#ifndef STATX_ATTR_DAX
#define STATX_ATTR_DAX 0x00200000
#endif
#define PG 4096UL
#define NPG 16
#define ALLOC_PG 2   /* written with pwrite + fsync before mapping */
#define HOLE_PG 10   /* created by ftruncate, never written */
#define TIMEOUT_MS 20000

static void rec(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
static void rec(const char *fmt, ...)
{
	char b[1024];
	va_list ap;
	va_start(ap, fmt);
	vsnprintf(b, sizeof(b), fmt, ap);
	va_end(ap);
	printf("@@R %s\n", b);
	fflush(stdout);
}

static int make_file(const char *path)   /* 8 written pages + 8 hole pages */
{
	int fd = open(path, O_RDWR | O_CREAT | O_TRUNC, 0644);
	if (fd < 0)
		return -1;
	char buf[PG];
	memset(buf, 'A', sizeof(buf));
	for (int i = 0; i < NPG / 2; i++)
		if (pwrite(fd, buf, PG, i * PG) != (ssize_t)PG)
			return -1;
	if (fsync(fd) || ftruncate(fd, NPG * PG) || fsync(fd))
		return -1;
	return fd;
}

static uint64_t pagemap(void *addr)
{
	int fd = open("/proc/self/pagemap", O_RDONLY);
	uint64_t v = 0;
	if (fd >= 0) {
		if (pread(fd, &v, 8, ((uintptr_t)addr / PG) * 8) != 8)
			v = 0;
		close(fd);
	}
	return v;
}

static int uffd_wp(void *addr, size_t len, uint64_t *feat)
{
	int u = syscall(__NR_userfaultfd, O_CLOEXEC | O_NONBLOCK);
	if (u < 0)
		return -1;
	struct uffdio_api api = { .api = UFFD_API, .features = UFFD_FEATURE_WP_ASYNC };
	if (ioctl(u, UFFDIO_API, &api))
		return -2;
	*feat = api.features;
	struct uffdio_register reg = { .range = { (uintptr_t)addr, len }, .mode = UFFDIO_REGISTER_MODE_WP };
	if (ioctl(u, UFFDIO_REGISTER, &reg))
		return -3;
	struct uffdio_writeprotect wp = { .range = { (uintptr_t)addr, len }, .mode = UFFDIO_WRITEPROTECT_MODE_WP };
	if (ioctl(u, UFFDIO_WRITEPROTECT, &wp))
		return -4;
	return u;
}

/* child: exit 0 ok, 3 bad data, 10+ setup step; status line to fd 'out' before the access */
enum { DAX, SHM };
static void child(int out, int kind, int use_uffd, int pg, int write)
{
	int fd;
	if (kind == DAX) {
		fd = make_file("/mnt/f");
	} else {
		fd = memfd_create("c2", 0);
		char buf[PG];
		memset(buf, 'A', sizeof(buf));
		if (fd >= 0 && ftruncate(fd, NPG * PG) == 0)
			for (int i = 0; i < NPG / 2; i++)
				if (pwrite(fd, buf, PG, i * PG) != (ssize_t)PG)
					_exit(10);
	}
	if (fd < 0)
		_exit(10);
	char *m = mmap(NULL, NPG * PG, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
	if (m == MAP_FAILED)
		_exit(11);
	uint64_t feat = 0;
	int u = 0;
	if (use_uffd) {
		u = uffd_wp(m, NPG * PG, &feat);
		if (u < 0)
			_exit(12 - u);   /* 13..16 = userfaultfd/API/REGISTER/WRITEPROTECT */
	}
	uint64_t pm = pagemap(m + pg * PG);
	dprintf(out, "\"pm_present\":%d,\"pm_swap\":%d,\"pm_uffd_wp\":%d,\"feat\":\"0x%llx\"",
		(int)(pm >> 63 & 1), (int)(pm >> 62 & 1), (int)(pm >> 57 & 1), (unsigned long long)feat);
	close(out);
	volatile char *p = m + pg * PG;
	char want = pg < NPG / 2 ? 'A' : 0;
	if (write) {
		p[0] = 'W';
		char c = 0;
		if (pread(fd, &c, 1, pg * PG) != 1 || c != 'W')
			_exit(3);
	} else {
		char c = p[0];
		if (c != want)
			_exit(3);
	}
	_exit(0);
}

static long minflt_of(pid_t pid)
{
	char path[64], b[1024];
	snprintf(path, sizeof(path), "/proc/%d/stat", pid);
	int fd = open(path, O_RDONLY);
	if (fd < 0)
		return -1;
	ssize_t n = read(fd, b, sizeof(b) - 1);
	close(fd);
	if (n <= 0)
		return -1;
	b[n] = 0;
	char *s = strrchr(b, ')');
	long v = -1;
	/* after ") ": state ppid pgrp session tty tpgid flags minflt */
	if (s)
		sscanf(s + 2, "%*c %*d %*d %*d %*d %*d %*u %ld", &v);
	return v;
}

static void run_case(const char *name, int kind, int use_uffd, int pg, int write)
{
	int pp[2];
	if (pipe(pp))
		return;
	unlink("/mnt/f");
	pid_t pid = fork();
	if (pid == 0) {
		close(pp[0]);
		child(pp[1], kind, use_uffd, pg, write);
	}
	close(pp[1]);
	char st[512] = "";
	ssize_t n = read(pp[0], st, sizeof(st) - 1);
	st[n > 0 ? n : 0] = 0;
	close(pp[0]);
	int status = 0, waited = 0;
	long minflt = -1;
	for (; waited < TIMEOUT_MS; waited += 100) {
		if (waitpid(pid, &status, WNOHANG) == pid)
			break;
		usleep(100000);
	}
	const char *res;
	char sig[32] = "";
	if (waited >= TIMEOUT_MS) {
		minflt = minflt_of(pid);
		kill(pid, SIGKILL);
		waitpid(pid, &status, 0);
		res = "HANG";
	} else if (WIFSIGNALED(status)) {
		int s = WTERMSIG(status);
		res = s == SIGBUS ? "SIGBUS" : s == SIGSEGV ? "SIGSEGV" : "SIGNAL";
		snprintf(sig, sizeof(sig), "%d", s);
	} else {
		int e = WEXITSTATUS(status);
		res = e == 0 ? "OK" : e == 3 ? "BADDATA" : "ERR";
		snprintf(sig, sizeof(sig), "exit%d", e);
	}
	rec("{\"t\":\"%s\",\"res\":\"%s\",\"how\":\"%s\",\"ms\":%d,\"minflt_at_kill\":%ld%s%s}", name, res, sig, waited, minflt,
	    st[0] ? "," : "", st);
}

static int copy_img(void)
{
	int in = open("/fs.img", O_RDONLY), out = open("/dev/pmem0", O_WRONLY);
	if (in < 0 || out < 0)
		return -1;
	static char buf[1 << 20];
	ssize_t n;
	long tot = 0;
	while ((n = read(in, buf, sizeof(buf))) > 0) {
		if (write(out, buf, n) != n)
			return -2;
		tot += n;
	}
	fsync(out);
	close(in);
	close(out);
	return (int)(tot >> 20);
}

int main(void)
{
	mount("proc", "/proc", "proc", 0, NULL);
	mount("sysfs", "/sys", "sysfs", 0, NULL);
	mount("devtmpfs", "/dev", "devtmpfs", 0, NULL);
	struct stat sb;
	int have = stat("/dev/pmem0", &sb) == 0;
	int mb = have ? copy_img() : -9;
	int mnt = have && mb > 0 ? (mount("/dev/pmem0", "/mnt", "ext4", 0, "dax=always") ? -errno : 0) : -999;
	int dax = 0;
	if (mnt == 0) {
		int fd = make_file("/mnt/f");
		struct statx sx;
		if (fd >= 0 && statx(AT_FDCWD, "/mnt/f", 0, STATX_BASIC_STATS, &sx) == 0)
			dax = !!(sx.stx_attributes & STATX_ATTR_DAX);
		if (fd >= 0)
			close(fd);
	}
	rec("{\"t\":\"C0\",\"pmem0\":%d,\"img_mb\":%d,\"mount\":%d,\"dax\":%d,\"res\":\"%s\"}", have, mb, mnt, dax,
	    have && mnt == 0 && dax ? "OK" : "ERR");
	if (have && mnt == 0 && dax) {
		run_case("C1w_alloc", DAX, 0, ALLOC_PG, 1);
		run_case("C1w_hole", DAX, 0, HOLE_PG, 1);
		run_case("C1r_alloc", DAX, 0, ALLOC_PG, 0);
		run_case("C1r_hole", DAX, 0, HOLE_PG, 0);
		run_case("C2w", SHM, 1, HOLE_PG, 1);
		run_case("C2r", SHM, 1, ALLOC_PG, 0);
		run_case("T1", DAX, 1, ALLOC_PG, 1);
		run_case("T2", DAX, 1, HOLE_PG, 1);
		run_case("T3", DAX, 1, ALLOC_PG, 0);
		run_case("T4", DAX, 1, HOLE_PG, 0);
	}
	printf("@@END\n");
	fflush(stdout);
	sync();
	reboot(RB_POWER_OFF);
	return 0;
}
