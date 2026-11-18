/* s8dyn criteria 三: /init that generates page allocation / free load for ~20 s, then powers off.
 * The bug under test needs no special trigger: any allocation or free with interrupts disabled reaches
 * __kernel_map_pages() when debug_pagealloc=on. This program only keeps the allocator busy on all CPUs. */
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static double now(void)
{
	struct timespec ts;
	clock_gettime(CLOCK_MONOTONIC, &ts);
	return ts.tv_sec + ts.tv_nsec / 1e9;
}

static void work(int id, double secs)
{
	double t0 = now();
	char buf[4096];
	unsigned long n = 0;
	while (now() - t0 < secs) {
		size_t len = 16 << 20;
		char *p = mmap(NULL, len, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
		if (p != MAP_FAILED) {
			for (size_t i = 0; i < len; i += 4096)
				p[i] = (char)i;
			munmap(p, len);
		}
		int fd[2];
		if (pipe(fd) == 0) {
			memset(buf, id, sizeof(buf));
			for (int i = 0; i < 16; i++) {
				if (write(fd[1], buf, sizeof(buf)) < 0)
					break;
				if (read(fd[0], buf, sizeof(buf)) < 0)
					break;
			}
			close(fd[0]);
			close(fd[1]);
		}
		int f = open("/proc/meminfo", O_RDONLY);
		if (f >= 0) {
			while (read(f, buf, sizeof(buf)) > 0)
				;
			close(f);
		}
		pid_t c = fork();
		if (c == 0)
			_exit(0);
		if (c > 0)
			waitpid(c, NULL, 0);
		n++;
	}
	printf("@@WORKER %d loops %lu\n", id, n);
	fflush(stdout);
}

int main(void)
{
	mkdir("/proc", 0755);
	mount("proc", "/proc", "proc", 0, NULL);
	printf("@@START\n");
	fflush(stdout);
	long ncpu = sysconf(_SC_NPROCESSORS_ONLN);
	printf("@@CPUS %ld\n", ncpu);
	fflush(stdout);
	for (int i = 0; i < 4; i++) {
		if (fork() == 0) {
			work(i, 20.0);
			_exit(0);
		}
	}
	while (wait(NULL) > 0)
		;
	printf("@@END\n");
	fflush(stdout);
	sync();
	reboot(RB_POWER_OFF);
	return 0;
}
