/*
 * /init of the differential-test initramfs, version 2 (criteria sections 4-5).
 * Same source for every architecture, built static. First a probe section that only reads system information
 * (sysfs PMU list, PMU event lists, cpuinfo), then the tests. Calls only documented system calls with ordinary or
 * explicitly unsupported arguments. Tests that may get the process killed run in a child process.
 * Output: one JSON line per probe/test between @@DT BEGIN / @@DT END, then power off.
 */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/futex.h>
#include <linux/hw_breakpoint.h>
#include <linux/perf_event.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/mount.h>
#include <sys/ptrace.h>
#include <sys/reboot.h>
#include <sys/socket.h>
#include <sys/syscall.h>
#include <sys/uio.h>
#include <sys/utsname.h>
#include <sys/wait.h>
#include <unistd.h>

#ifndef MAP_FIXED_NOREPLACE
#define MAP_FIXED_NOREPLACE 0x100000
#endif

static char rbuf[128];

static const char *errname(int e)
{
	const char *n = strerrorname_np(e);
	snprintf(rbuf, sizeof(rbuf), "%s", n ? n : "E?");
	return rbuf;
}

static const char *result(long ret)
{
	if (ret >= 0)
		return "ok";
	return errname(errno);
}

static void emit(const char *test, const char *res)
{
	printf("{\"test\": \"%s\", \"result\": \"%s\"}\n", test, res);
}

/* ---------------------------------------------------------------- probes (criteria section 5) */

static void json_str(const char *s)
{
	putchar('"');
	for (; *s; s++) {
		if (*s == '"' || *s == '\\')
			putchar('\\');
		if ((unsigned char)*s >= 0x20)
			putchar(*s);
	}
	putchar('"');
}

static int is_hw_pmu(const char *n)
{
	return !strcmp(n, "cpu") || !strcmp(n, "cpu_core") || !strcmp(n, "cpu_atom") ||
	       !strncmp(n, "armv8", 5) || !strncmp(n, "armv9", 5);
}

static void probe_pmus(void)
{
	DIR *d = opendir("/sys/bus/event_source/devices");
	struct dirent *e;
	char path[512];
	int first = 1;

	printf("{\"probe\": \"pmu_devices\", \"value\": [");
	if (d) {
		while ((e = readdir(d))) {
			if (e->d_name[0] == '.')
				continue;
			if (!first)
				printf(", ");
			json_str(e->d_name);
			first = 0;
		}
		closedir(d);
	}
	printf("]}\n");

	d = opendir("/sys/bus/event_source/devices");
	if (!d)
		return;
	while ((e = readdir(d))) {
		DIR *ev;
		struct dirent *x;
		if (e->d_name[0] == '.' || !is_hw_pmu(e->d_name))
			continue;
		snprintf(path, sizeof(path), "/sys/bus/event_source/devices/%s/events", e->d_name);
		ev = opendir(path);
		printf("{\"probe\": \"pmu_events\", \"pmu\": ");
		json_str(e->d_name);
		if (!ev) {
			printf(", \"value\": null}\n");
			continue;
		}
		printf(", \"value\": [");
		first = 1;
		while ((x = readdir(ev))) {
			if (x->d_name[0] == '.')
				continue;
			if (!first)
				printf(", ");
			json_str(x->d_name);
			first = 0;
		}
		closedir(ev);
		printf("]}\n");
	}
	closedir(d);
}

static void probe_cpuinfo(void)
{
	FILE *f = fopen("/proc/cpuinfo", "r");
	char line[4096];
	int seen_isa = 0, seen_mmu = 0, seen_feat = 0, seen_flags = 0;

	if (!f)
		return;
	while (fgets(line, sizeof(line), f)) {
		char *colon = strchr(line, ':');
		int *seen = NULL;
		const char *key = NULL;
		if (!colon)
			continue;
		if (!strncmp(line, "isa", 3) && !strncmp(line, "isa\t", 4)) { seen = &seen_isa; key = "isa"; }
		else if (!strncmp(line, "mmu", 3)) { seen = &seen_mmu; key = "mmu"; }
		else if (!strncmp(line, "Features", 8)) { seen = &seen_feat; key = "Features"; }
		else if (!strncmp(line, "flags", 5)) { seen = &seen_flags; key = "flags"; }
		if (!seen || *seen)
			continue;
		*seen = 1;
		line[strcspn(line, "\n")] = 0;
		colon++;
		while (*colon == ' ' || *colon == '\t')
			colon++;
		printf("{\"probe\": \"cpuinfo\", \"key\": \"%s\", \"value\": ", key);
		json_str(colon);
		printf("}\n");
	}
	fclose(f);
}

static long read_long(const char *path)
{
	FILE *f = fopen(path, "r");
	long v = -1;
	if (f) {
		if (fscanf(f, "%ld", &v) != 1)
			v = -1;
		fclose(f);
	}
	return v;
}

/* ---------------------------------------------------------------- helpers */

/* run fn in a child; the child prints its own result line; if it dies by a signal, print that instead */
static void in_child(const char *test, const char *(*fn)(void))
{
	pid_t p = fork();
	int st;

	if (p == 0) {
		emit(test, fn());
		_exit(0);
	}
	if (p < 0) {
		emit(test, "fork_failed");
		return;
	}
	waitpid(p, &st, 0);
	if (WIFSIGNALED(st)) {
		char b[64];
		snprintf(b, sizeof(b), "killed_%s", sigabbrev_np(WTERMSIG(st)) ? sigabbrev_np(WTERMSIG(st)) : "?");
		emit(test, b);
	}
}

/* ---------------------------------------------------------------- perf (unchanged from round 1) */

static void perf_probe(const char *name, unsigned int type, unsigned long long config, int breakpoint)
{
	struct perf_event_attr attr;
	long fd;

	memset(&attr, 0, sizeof(attr));
	attr.size = sizeof(attr);
	attr.type = type;
	attr.config = config;
	attr.disabled = 1;
	attr.exclude_kernel = 1;
	attr.exclude_hv = 1;
	if (breakpoint) {
		attr.bp_type = HW_BREAKPOINT_X;
		attr.bp_addr = (unsigned long)&perf_probe;
		attr.bp_len = sizeof(long);
	}
	errno = 0;
	fd = syscall(__NR_perf_event_open, &attr, 0, -1, -1, 0);
	emit(name, result(fd));
	if (fd >= 0)
		close(fd);
}

/* ---------------------------------------------------------------- A101: mmap hint */

#define GiB (1UL << 30)

static const char *t_mmap_hint_free(void)
{
	void *hint = (void *)(4 * GiB);
	void *p = mmap(hint, 4096, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
	if (p == MAP_FAILED)
		return errname(errno);
	munmap(p, 4096);
	return p == hint ? "at_hint" : "elsewhere";
}

static const char *t_mmap_hint_occupied(void)
{
	void *hint = (void *)(1 * GiB);
	void *a = mmap(hint, 2 * GiB, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_NORESERVE | MAP_FIXED_NOREPLACE, -1, 0);
	void *b;
	if (a != hint)
		return "setup_failed";
	b = mmap(hint, 2 * GiB, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_NORESERVE, -1, 0);
	if (b == MAP_FAILED)
		return errname(errno);
	munmap(b, 2 * GiB);
	munmap(a, 2 * GiB);
	return "ok";
}

/* ---------------------------------------------------------------- A310: syscall number -1 */

static const char *classify_minus1(long r, int e)
{
	if (r == 12345)
		return "ret_arg0";
	if (r == -1)
		return errname(e);
	return "ret_other";
}

static const char *t_syscall_minus1(void)
{
	long r;
	errno = 0;
	r = syscall(-1, 12345L);
	return classify_minus1(r, errno);
}

static const char *t_syscall_bignr(void)
{
	long r;
	errno = 0;
	r = syscall(100000, 12345L);
	return classify_minus1(r, errno);
}

static const char *t_syscall_minus1_traced(void)
{
	pid_t p = fork();
	int st, sig = 0;

	if (p == 0) {
		long r;
		ptrace(PTRACE_TRACEME, 0, 0, 0);
		raise(SIGSTOP);
		errno = 0;
		r = syscall(-1, 12345L);
		if (r == 12345)
			_exit(1);
		if (r == -1 && errno == ENOSYS)
			_exit(0);
		if (r == -1)
			_exit(2);
		_exit(3);
	}
	if (p < 0)
		return "fork_failed";
	if (waitpid(p, &st, 0) < 0 || !WIFSTOPPED(st))
		return "trace_setup_failed";
	ptrace(PTRACE_SETOPTIONS, p, 0, PTRACE_O_TRACESYSGOOD | PTRACE_O_EXITKILL);
	for (;;) {
		if (ptrace(PTRACE_SYSCALL, p, 0, sig) < 0)
			return "ptrace_failed";
		if (waitpid(p, &st, 0) < 0)
			return "wait_failed";
		if (WIFEXITED(st))
			break;
		if (WIFSIGNALED(st))
			return "tracee_killed";
		sig = (WIFSTOPPED(st) && WSTOPSIG(st) != (SIGTRAP | 0x80)) ? WSTOPSIG(st) : 0;
	}
	switch (WEXITSTATUS(st)) {
	case 0: return "ENOSYS";
	case 1: return "ret_arg0";
	case 2: return "err_other";
	default: return "ret_other";
	}
}

/* ---------------------------------------------------------------- A171: futex on high alias address */

static uint32_t *futex_page(void)
{
	uint32_t *w = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
	if (w == MAP_FAILED)
		return NULL;
	*w = 0; /* fault it in */
	return w;
}

static const char *t_futex_wake_normal(void)
{
	uint32_t *w = futex_page();
	long r;
	if (!w)
		return "setup_failed";
	errno = 0;
	r = syscall(SYS_futex, w, FUTEX_WAKE, 1, NULL, NULL, 0);
	return result(r);
}

static const char *t_futex_wake_highalias(void)
{
	uint32_t *w = futex_page();
	long r;
	if (!w)
		return "setup_failed";
	errno = 0;
	r = syscall(SYS_futex, (void *)((uintptr_t)w | (1UL << 62)), FUTEX_WAKE, 1, NULL, NULL, 0);
	return result(r);
}

/* ---------------------------------------------------------------- A181: cmsg_len at an unaligned address */

static const char *cmsg_test(size_t off)
{
	int sv[2], one = 1;
	char data = 'x', in;
	unsigned char cbuf[128];
	struct iovec iov = { &in, 1 };
	struct msghdr m;
	uint64_t len;
	long r;

	if (socketpair(AF_UNIX, SOCK_DGRAM, 0, sv) < 0)
		return "setup_failed";
	if (setsockopt(sv[1], SOL_SOCKET, SO_PASSCRED, &one, sizeof(one)) < 0)
		return "setup_failed";
	if (write(sv[0], &data, 1) != 1)
		return "setup_failed";
	memset(cbuf, 0xAA, sizeof(cbuf));
	memset(&m, 0, sizeof(m));
	m.msg_iov = &iov;
	m.msg_iovlen = 1;
	m.msg_control = cbuf + off;
	m.msg_controllen = CMSG_SPACE(sizeof(struct ucred));
	errno = 0;
	r = recvmsg(sv[1], &m, 0);
	close(sv[0]);
	close(sv[1]);
	if (r < 0)
		return errname(errno);
	if (m.msg_flags & MSG_CTRUNC)
		return "ctrunc";
	memcpy(&len, cbuf + off, sizeof(len));
	return len == CMSG_LEN(sizeof(struct ucred)) ? "len_ok" : "len_bad";
}

static const char *t_cmsg_len_aligned(void) { return cmsg_test(0); }
static const char *t_cmsg_len_unaligned(void) { return cmsg_test(1); }

static const char *t_getpid(void) { return getpid() > 0 ? "ok" : "fail"; }

/* ---------------------------------------------------------------- main */

int main(void)
{
	struct utsname u;
	long taint0, taint1;
	int fd;

	mount("devtmpfs", "/dev", "devtmpfs", 0, NULL);
	fd = open("/dev/console", O_WRONLY);
	if (fd >= 0) {
		dup2(fd, 1);
		dup2(fd, 2);
	}
	setvbuf(stdout, NULL, _IONBF, 0);
	mount("proc", "/proc", "proc", 0, NULL);
	mount("sysfs", "/sys", "sysfs", 0, NULL);
	printf("\n@@DT BEGIN\n");

	probe_pmus();
	probe_cpuinfo();
	taint0 = read_long("/proc/sys/kernel/tainted");

	/* controls */
	emit("getpid", t_getpid());
	uname(&u);
	emit("uname_sysname", u.sysname);
	in_child("syscall_bignr", t_syscall_bignr);

	/* perf matrix (round 1) */
	perf_probe("hw_cycles", PERF_TYPE_HARDWARE, PERF_COUNT_HW_CPU_CYCLES, 0);
	perf_probe("hw_instructions", PERF_TYPE_HARDWARE, PERF_COUNT_HW_INSTRUCTIONS, 0);
	perf_probe("hw_config_max", PERF_TYPE_HARDWARE, PERF_COUNT_HW_MAX, 0);
	perf_probe("hw_config_bogus", PERF_TYPE_HARDWARE, 0x7f, 0);
	perf_probe("sw_cpu_clock", PERF_TYPE_SOFTWARE, PERF_COUNT_SW_CPU_CLOCK, 0);
	perf_probe("sw_config_bogus", PERF_TYPE_SOFTWARE, 0x7f, 0);
	perf_probe("cache_l1d_read_access", PERF_TYPE_HW_CACHE,
		   PERF_COUNT_HW_CACHE_L1D | (PERF_COUNT_HW_CACHE_OP_READ << 8) |
		   (PERF_COUNT_HW_CACHE_RESULT_ACCESS << 16), 0);
	perf_probe("cache_config_bogus", PERF_TYPE_HW_CACHE, 0xffffff, 0);
	perf_probe("raw_zero", PERF_TYPE_RAW, 0, 0);
	perf_probe("raw_bogus", PERF_TYPE_RAW, 0xffffffffULL, 0);
	perf_probe("breakpoint_exec", PERF_TYPE_BREAKPOINT, 0, 1);
	perf_probe("type_unknown", 0x7fff, 0, 0);

	/* new samples */
	in_child("mmap_hint_free", t_mmap_hint_free);
	in_child("mmap_hint_occupied", t_mmap_hint_occupied);
	in_child("syscall_minus1", t_syscall_minus1);
	in_child("syscall_minus1_traced", t_syscall_minus1_traced);
	in_child("futex_wake_normal", t_futex_wake_normal);
	in_child("futex_wake_highalias", t_futex_wake_highalias);
	in_child("cmsg_len_aligned", t_cmsg_len_aligned);
	in_child("cmsg_len_unaligned", t_cmsg_len_unaligned);

	taint1 = read_long("/proc/sys/kernel/tainted");
	printf("{\"probe\": \"taint_changed\", \"value\": %s}\n", taint0 == taint1 ? "false" : "true");
	printf("@@DT END\n");
	sync();
	reboot(RB_POWER_OFF);
	return 0;
}
