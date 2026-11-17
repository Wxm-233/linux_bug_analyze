/*
 * /init of the differential-test initramfs (criteria sections 2-3).
 * Same source for every architecture, built static. Calls only documented system calls with ordinary or
 * explicitly unsupported arguments, prints one JSON line per test between @@DT BEGIN / @@DT END, then powers off.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/hw_breakpoint.h>
#include <linux/perf_event.h>
#include <stdio.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/syscall.h>
#include <sys/utsname.h>
#include <unistd.h>

static const char *result(long ret)
{
	static char buf[64];
	if (ret >= 0)
		return "ok";
	snprintf(buf, sizeof(buf), "%s", strerrorname_np(errno) ? strerrorname_np(errno) : "E?");
	return buf;
}

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
	printf("{\"test\": \"perf_event_open\", \"case\": \"%s\", \"type\": %u, \"config\": %llu, \"result\": \"%s\"}\n",
	       name, type, config, result(fd));
	if (fd >= 0)
		close(fd);
}

int main(void)
{
	struct utsname u;
	long r;
	int fd;

	mount("devtmpfs", "/dev", "devtmpfs", 0, NULL);
	fd = open("/dev/console", O_WRONLY);
	if (fd >= 0) {
		dup2(fd, 1);
		dup2(fd, 2);
	}
	setvbuf(stdout, NULL, _IONBF, 0);
	printf("\n@@DT BEGIN\n");

	/* controls: the harness itself */
	errno = 0;
	r = getpid();
	printf("{\"test\": \"getpid\", \"result\": \"%s\"}\n", r > 0 ? "ok" : "fail");
	uname(&u);
	printf("{\"test\": \"uname_sysname\", \"result\": \"%s\"}\n", u.sysname);
	errno = 0;
	r = syscall(-1);
	printf("{\"test\": \"syscall_invalid_nr\", \"result\": \"%s\"}\n", result(r));

	/* perf_event_open matrix */
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

	printf("@@DT END\n");
	sync();
	reboot(RB_POWER_OFF);
	return 0;
}
