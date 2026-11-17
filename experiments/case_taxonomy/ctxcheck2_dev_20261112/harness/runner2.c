/* Case executor of ctxcheck2 (criteria 三.1 + amendment 1, 一). Runs as PID 1 in a QEMU initramfs; same source
 * for riscv64, arm64 and x86_64.  /cases.txt: one case per line "<id> <kind>".  Each case runs in a child
 * process; the parent prints  {"id":N,"trap":"kind","sig":S,"exit":E}.  A child may print one line
 * {"cnote":"..."} before it ends (no "id" key, so it does not move warning attribution).  Cases are 1.2 s apart
 * (the sleeping-in-atomic report is rate-limited to one per second).
 * Kinds: breakpoint illegal_insn misaligned_load misaligned_store segv_read write_ro exec_nx
 *        uprobe_load uprobe_plain ptrace_singlestep hw_watchpoint signal_syscall */
#define _GNU_SOURCE
#include <errno.h>
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
#include <sys/syscall.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

/* two probe targets: the first instruction of probe_load reads memory, that of probe_plain does not */
#if defined(__riscv)
__asm__(".text\n.balign 16\n.globl probe_load\nprobe_load:\n ld a0, 0(a0)\n ret\n"
        ".balign 16\n.globl probe_plain\nprobe_plain:\n addi a0, a0, 1\n ret\n");
#elif defined(__aarch64__)
__asm__(".text\n.balign 16\n.globl probe_load\nprobe_load:\n ldr x0, [x0]\n ret\n"
        ".balign 16\n.globl probe_plain\nprobe_plain:\n add x0, x0, #1\n ret\n");
#else
__asm__(".text\n.balign 16\n.globl probe_load\nprobe_load:\n movq (%rdi), %rax\n ret\n"
        ".balign 16\n.globl probe_plain\nprobe_plain:\n leaq 1(%rdi), %rax\n ret\n");
#endif
long probe_load(volatile long *p);
long probe_plain(long v);

static unsigned char buf[64] __attribute__((aligned(64)));
static volatile long watched;

static void note(const char *fmt, long a, long b)
{
	printf("{\"cnote\":\"");
	printf(fmt, a, b);
	printf("\"}\n");
	fflush(stdout);
}

static long perf_open(struct perf_event_attr *a)
{
	return syscall(SYS_perf_event_open, a, 0, -1, -1, 0);
}

static unsigned long file_offset(void *fn)
{
	FILE *m = fopen("/proc/self/maps", "r");
	char line[512];
	unsigned long s, e, off, a = (unsigned long)fn;
	while (m && fgets(line, sizeof(line), m)) {
		char perm[8];
		if (sscanf(line, "%lx-%lx %7s %lx", &s, &e, perm, &off) == 4 && a >= s && a < e && strstr(line, "/init")) {
			fclose(m);
			return a - s + off;
		}
	}
	if (m)
		fclose(m);
	return 0;
}

static void do_uprobe(int load)
{
	FILE *t = fopen("/sys/bus/event_source/devices/uprobe/type", "r");
	int type = -1;
	if (!t || fscanf(t, "%d", &type) != 1) {
		note("uprobe_pmu_missing errno=%ld %ld", errno, 0);
		_exit(20);
	}
	fclose(t);
	void *fn = load ? (void *)probe_load : (void *)probe_plain;
	struct perf_event_attr a;
	memset(&a, 0, sizeof(a));
	a.type = type;
	a.size = sizeof(a);
	a.config1 = (uint64_t)(uintptr_t) "/init";
	a.config2 = file_offset(fn);
	long fd = perf_open(&a);
	if (fd < 0) {
		note("uprobe_open errno=%ld off=%ld", errno, (long)a.config2);
		_exit(21);
	}
	long r;
	if (load) {
		volatile long *p = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
		r = probe_load(p); /* page never touched before: the probed load faults */
	} else {
		r = probe_plain(41);
	}
	long long n = -1;
	if (read(fd, &n, sizeof(n)) != sizeof(n))
		n = -2;
	note("uprobe hits=%ld r=%ld", (long)n, r);
	close(fd);
}

static void do_singlestep(void)
{
	pid_t c = fork();
	if (c == 0) {
		ptrace(PTRACE_TRACEME, 0, 0, 0);
		raise(SIGSTOP);
		volatile int x = 0;
		for (int i = 0; i < 100; i++)
			x += i;
		_exit(0);
	}
	int st, ok = 0, err = 0;
	waitpid(c, &st, 0);
	for (int i = 0; i < 5; i++) {
		if (ptrace(PTRACE_SINGLESTEP, c, 0, 0) < 0) {
			err = errno;
			break;
		}
		waitpid(c, &st, 0);
		ok++;
	}
	ptrace(PTRACE_CONT, c, 0, 0);
	waitpid(c, &st, 0);
	note("singlestep ok=%ld errno=%ld", ok, err);
}

static void do_watchpoint(void)
{
	struct perf_event_attr a;
	memset(&a, 0, sizeof(a));
	a.type = PERF_TYPE_BREAKPOINT;
	a.size = sizeof(a);
	a.bp_type = HW_BREAKPOINT_W;
	a.bp_addr = (uint64_t)(uintptr_t)&watched;
	a.bp_len = HW_BREAKPOINT_LEN_8;
	long fd = perf_open(&a);
	if (fd < 0) {
		note("watchpoint_open errno=%ld %ld", errno, 0);
		_exit(22);
	}
	watched = 42;
	long long n = -1;
	if (read(fd, &n, sizeof(n)) != sizeof(n))
		n = -2;
	note("watchpoint hits=%ld %ld", (long)n, 0);
	close(fd);
}

static int sig_pipe[2];
static void on_usr1(int s)
{
	(void)s;
	syscall(SYS_getpid);
	syscall(SYS_write, sig_pipe[1], "x", 1);
}

static void do_signal(void)
{
	pipe(sig_pipe);
	struct sigaction sa;
	memset(&sa, 0, sizeof(sa));
	sa.sa_handler = on_usr1;
	sigaction(SIGUSR1, &sa, NULL);
	kill(getpid(), SIGUSR1);
	char c = 0;
	note("signal read=%ld c=%ld", (long)read(sig_pipe[0], &c, 1), c);
}

static void do_kind(const char *k)
{
	volatile unsigned char *p = buf + 1;
	uint64_t v = 0x1122334455667788ULL;
	if (!strcmp(k, "misaligned_load")) {
#if defined(__riscv)
		__asm__ volatile("ld %0, 0(%1)" : "=r"(v) : "r"(p) : "memory");
#elif defined(__aarch64__)
		__asm__ volatile("ldr %0, [%1]" : "=r"(v) : "r"(p) : "memory");
#else
		__asm__ volatile("movq (%1), %0" : "=r"(v) : "r"(p) : "memory");
#endif
	} else if (!strcmp(k, "misaligned_store")) {
#if defined(__riscv)
		__asm__ volatile("sd %0, 0(%1)" : : "r"(v), "r"(p) : "memory");
#elif defined(__aarch64__)
		__asm__ volatile("str %0, [%1]" : : "r"(v), "r"(p) : "memory");
#else
		__asm__ volatile("movq %0, (%1)" : : "r"(v), "r"(p) : "memory");
#endif
	} else if (!strcmp(k, "breakpoint")) {
#if defined(__riscv)
		__asm__ volatile("ebreak");
#elif defined(__aarch64__)
		__asm__ volatile("brk #0");
#else
		__asm__ volatile("int3");
#endif
	} else if (!strcmp(k, "illegal_insn")) {
#if defined(__riscv)
		__asm__ volatile("unimp");
#elif defined(__aarch64__)
		__asm__ volatile("udf #0");
#else
		__asm__ volatile("ud2");
#endif
	} else if (!strcmp(k, "segv_read")) {
		v = *(volatile uint64_t *)(uintptr_t)0x10;
	} else if (!strcmp(k, "write_ro")) {
		volatile uint64_t *q = mmap(NULL, 4096, PROT_READ, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
		*q = v;
	} else if (!strcmp(k, "exec_nx")) {
		void *q = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
		memset(q, 0, 4096);
		((void (*)(void))q)();
	} else if (!strcmp(k, "uprobe_load")) {
		do_uprobe(1);
	} else if (!strcmp(k, "uprobe_plain")) {
		do_uprobe(0);
	} else if (!strcmp(k, "ptrace_singlestep")) {
		do_singlestep();
	} else if (!strcmp(k, "hw_watchpoint")) {
		do_watchpoint();
	} else if (!strcmp(k, "signal_syscall")) {
		do_signal();
	} else {
		_exit(99);
	}
	(void)v;
}

int main(void)
{
	mount("proc", "/proc", "proc", 0, NULL);
	mount("sysfs", "/sys", "sysfs", 0, NULL);
	FILE *in = fopen("/cases.txt", "r");
	printf("@@SH BEGIN\n");
	fflush(stdout);
	char kind[64];
	unsigned long id;
	while (in && fscanf(in, "%lu %63s", &id, kind) == 2) {
		struct timespec gap = {1, 200000000};
		nanosleep(&gap, NULL);
		pid_t c = fork();
		if (c == 0) {
			do_kind(kind);
			_exit(0);
		}
		int st = 0;
		waitpid(c, &st, 0);
		printf("{\"id\":%lu,\"trap\":\"%s\",\"sig\":%d,\"exit\":%d}\n", id, kind,
		       WIFSIGNALED(st) ? WTERMSIG(st) : 0, WIFEXITED(st) ? WEXITSTATUS(st) : -1);
		fflush(stdout);
	}
	struct timespec gap = {1, 200000000};
	nanosleep(&gap, NULL);
	printf("@@SH END\n");
	fflush(stdout);
	sync();
	reboot(RB_POWER_OFF);
	return 0;
}
