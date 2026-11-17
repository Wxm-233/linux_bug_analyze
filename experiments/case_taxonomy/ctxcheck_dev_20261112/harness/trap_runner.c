/* Trap-case executor (ctxcheck criteria 五.1). Runs as PID 1 in a QEMU initramfs; same source for every
 * architecture.  Reads /cases.txt: one case per line "<id> <kind>", kind in breakpoint | illegal_insn |
 * misaligned_load | misaligned_store.  Each case runs in a child process; output per case:
 *   {"id":N,"trap":"kind","sig":S,"exit":E}
 * Cases are separated by 1.2 s (the "sleeping function called from invalid context" report is rate-limited to
 * one per second), so a kernel warning printed during a case appears before that case's line. */
#define _GNU_SOURCE
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static unsigned char buf[64] __attribute__((aligned(64)));

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
	} else {
		_exit(99);
	}
	(void)v;
}

int main(void)
{
	mount("proc", "/proc", "proc", 0, NULL);
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
