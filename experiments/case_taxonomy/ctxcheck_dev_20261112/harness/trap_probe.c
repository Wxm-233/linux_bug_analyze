/* Feasibility probe for user-mode trap entries (ctxcheck_dev_20261112). Runs as PID 1 in a QEMU initramfs.
 * For each trap kind, a child process executes it; the parent reports how the child ended and how many
 * alignment faults the kernel counted (PERF_COUNT_SW_ALIGNMENT_FAULTS, counted only when the kernel itself
 * handles a misaligned access).  Output: {"probe":NAME,"value":...} lines, then "@@SH END". */
#define _GNU_SOURCE
#include <linux/perf_event.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/prctl.h>
#include <sys/reboot.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <unistd.h>

static unsigned char buf[64] __attribute__((aligned(64)));

static void do_kind(int k)
{
	volatile unsigned char *p = buf + 1;
	switch (k) {
	case 0: { /* misaligned 8-byte load */
		uint64_t v;
#if defined(__riscv)
		__asm__ volatile("ld %0, 0(%1)" : "=r"(v) : "r"(p) : "memory");
#elif defined(__aarch64__)
		__asm__ volatile("ldr %0, [%1]" : "=r"(v) : "r"(p) : "memory");
#else
		__asm__ volatile("movq (%1), %0" : "=r"(v) : "r"(p) : "memory");
#endif
		(void)v;
		break;
	}
	case 1: { /* misaligned 8-byte store */
		uint64_t v = 0x1122334455667788ULL;
#if defined(__riscv)
		__asm__ volatile("sd %0, 0(%1)" : : "r"(v), "r"(p) : "memory");
#elif defined(__aarch64__)
		__asm__ volatile("str %0, [%1]" : : "r"(v), "r"(p) : "memory");
#else
		__asm__ volatile("movq %0, (%1)" : : "r"(v), "r"(p) : "memory");
#endif
		break;
	}
	case 2: /* breakpoint */
#if defined(__riscv)
		__asm__ volatile("ebreak");
#elif defined(__aarch64__)
		__asm__ volatile("brk #0");
#else
		__asm__ volatile("int3");
#endif
		break;
	case 3: /* illegal instruction */
#if defined(__riscv)
		__asm__ volatile("unimp");
#elif defined(__aarch64__)
		__asm__ volatile("udf #0");
#else
		__asm__ volatile("ud2");
#endif
		break;
	}
}

static const char *names[] = {"misaligned_load", "misaligned_store", "breakpoint", "illegal_insn"};

static void run(int k, int sigbus)
{
	struct perf_event_attr a;
	memset(&a, 0, sizeof(a));
	a.type = PERF_TYPE_SOFTWARE;
	a.size = sizeof(a);
	a.config = PERF_COUNT_SW_ALIGNMENT_FAULTS;
	a.inherit = 1;
	int fd = syscall(SYS_perf_event_open, &a, 0, -1, -1, 0);
	pid_t c = fork();
	if (c == 0) {
		if (sigbus)
			prctl(PR_SET_UNALIGN, PR_UNALIGN_SIGBUS, 0, 0, 0);
		do_kind(k);
		_exit(0);
	}
	int st = 0;
	waitpid(c, &st, 0);
	long long n = -1;
	if (fd >= 0 && read(fd, &n, sizeof(n)) != sizeof(n))
		n = -2;
	printf("{\"probe\":\"%s%s\",\"value\":{\"exit\":%d,\"signal\":%d,\"align_faults\":%lld,\"perf_fd\":%d}}\n",
	       names[k], sigbus ? "_sigbus" : "", WIFEXITED(st) ? WEXITSTATUS(st) : -1,
	       WIFSIGNALED(st) ? WTERMSIG(st) : 0, n, fd >= 0);
	fflush(stdout);
	if (fd >= 0)
		close(fd);
}

int main(void)
{
	mount("proc", "/proc", "proc", 0, NULL);
	printf("@@SH BEGIN\n");
	for (int k = 0; k < 4; k++)
		run(k, 0);
	run(0, 1);
	run(1, 1);
	for (int k = 0; k < 4; k++) /* second round: warnings are rate-limited, see whether they repeat */
		run(k, 0);
	printf("@@SH END\n");
	fflush(stdout);
	sync();
	reboot(RB_POWER_OFF);
	return 0;
}
