/* Runtime boundary probe (rtprobe criteria 二). Runs as PID 1 in a QEMU initramfs; same 64-bit source for every
 * architecture. Output lines use the executor's probe format: {"probe":NAME,"value":...}. */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/auxv.h>
#include <sys/mman.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/syscall.h>
#include <unistd.h>

#ifndef MAP_FIXED_NOREPLACE
#define MAP_FIXED_NOREPLACE 0x100000
#endif

static int zfd = -1;
static unsigned long page;

/* 1 if the kernel's user-pointer check accepts P (read of length 0 never touches memory) */
static int uaccess_ok(uint64_t p)
{
	long r = syscall(SYS_read, zfd, (void *)p, 0UL);
	if (r == 0)
		return 1;
	return errno == EFAULT ? 0 : -1;
}

/* 1 if one page can be mapped at A (A page aligned) */
static int map_ok(uint64_t a)
{
	void *p = mmap((void *)a, page, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE, -1, 0);
	if (p == MAP_FAILED)
		return errno == EEXIST;
	if ((uint64_t)p != a) { /* kernel without MAP_FIXED_NOREPLACE treated it as a hint */
		munmap(p, page);
		return 0;
	}
	munmap(p, page);
	return 1;
}

static void emit_hex(const char *name, uint64_t v)
{
	printf("{\"probe\":\"%s\",\"value\":\"%" PRIx64 "\"}\n", name, v);
}

static void emit_int(const char *name, long v)
{
	printf("{\"probe\":\"%s\",\"value\":%ld}\n", name, v);
}

static void emit_err(const char *name, const char *why)
{
	printf("{\"harness_error\":\"probe_failed\",\"probe\":\"%s\",\"why\":\"%s\"}\n", name, why);
}

static void probe_uaccess(void)
{
	uint64_t p = 0;
	if (uaccess_ok(4096) != 1) {
		emit_err("uaccess_top", "low_address_rejected");
		return;
	}
	/* amendment 1: search 63 bits unless the top byte is ignored (then only 56 bits are meaningful) */
	int tbi = uaccess_ok(UINT64_C(4096) | (UINT64_C(1) << 63)) == 1;
	int bits = tbi ? 56 : 63;
	uint64_t lim = UINT64_C(1) << bits;
	for (int b = bits - 1; b >= 0; b--) {
		int r = uaccess_ok(p | (UINT64_C(1) << b));
		if (r < 0) {
			emit_err("uaccess_top", "unexpected_errno");
			return;
		}
		if (r)
			p |= UINT64_C(1) << b;
	}
	uint64_t top = p + 1; /* first rejected address (within the searched range) */
	/* spot checks of the "one contiguous range from 0" assumption */
	uint64_t below[3] = { top / 2, top - top / 8, top - 1 };
	uint64_t above[3] = { top, top + ((lim - top) / 2), lim - 1 };
	for (int i = 0; i < 3; i++)
		if (uaccess_ok(below[i]) != 1) {
			emit_err("uaccess_top", "not_contiguous_below");
			return;
		}
	for (int i = 0; i < 3; i++)
		if (top < lim && above[i] >= top && uaccess_ok(above[i]) != 0) {
			emit_err("uaccess_top", "not_contiguous_above");
			return;
		}
	emit_hex("uaccess_top", top);
	emit_int("uaccess_search_bits", bits);
	emit_int("top_byte_ignored", tbi);
}

/* amendment 1: do memory-management syscalls ignore the top address byte? */
static void probe_mm_tbi(void)
{
	unsigned char vec[4];
	void *m = mmap(NULL, page, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
	if (m == MAP_FAILED) {
		emit_err("mm_top_byte_ignored", "mmap");
		return;
	}
	*(volatile char *)m = 1;
	long r = syscall(SYS_mincore, (uint64_t)m | (UINT64_C(1) << 63), page, vec);
	emit_int("mm_top_byte_ignored", r == 0);
	munmap(m, page);
}

static void probe_mmap(void)
{
	uint64_t a = 0;
	for (int b = 63; b >= 12; b--) {
		uint64_t t = a | (UINT64_C(1) << b);
		if (t % page)
			continue;
		if (map_ok(t))
			a = t;
	}
	if (!a) {
		emit_err("mmap_top", "nothing_mappable");
		return;
	}
	uint64_t top = a + page;
	uint64_t below[3] = { (top / 2) & ~(page - 1), (top - top / 8) & ~(page - 1), top - page };
	for (int i = 0; i < 3; i++)
		if (!map_ok(below[i])) {
			emit_err("mmap_top", "not_contiguous_below");
			return;
		}
	if (map_ok(top) || map_ok(top + 16 * page)) {
		emit_err("mmap_top", "not_contiguous_above");
		return;
	}
	emit_hex("mmap_top", top);
	void *d = mmap(NULL, page, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
	if (d != MAP_FAILED) {
		emit_hex("mmap_default", (uint64_t)d);
		munmap(d, page);
	}
}

static void probe_hugepages(void)
{
	DIR *d = opendir("/sys/kernel/mm/hugepages");
	char names[16][64];
	int n = 0;
	struct dirent *e;
	if (!d) {
		printf("{\"probe\":\"hugepage_sizes\",\"value\":[]}\n");
		return;
	}
	while ((e = readdir(d)) && n < 16)
		if (e->d_name[0] != '.')
			snprintf(names[n++], sizeof(names[0]), "%s", e->d_name);
	closedir(d);
	for (int i = 0; i < n; i++) /* sort: readdir order is not stable across kernels */
		for (int j = i + 1; j < n; j++)
			if (strcmp(names[i], names[j]) > 0) {
				char t[64];
				memcpy(t, names[i], 64);
				memcpy(names[i], names[j], 64);
				memcpy(names[j], t, 64);
			}
	printf("{\"probe\":\"hugepage_sizes\",\"value\":[");
	for (int i = 0; i < n; i++)
		printf("%s\"%s\"", i ? "," : "", names[i]);
	printf("]}\n");
}

int main(void)
{
	int fd;
	if (getpid() != 1) {
		fprintf(stderr, "rt_probe must run as PID 1 in a QEMU initramfs\n");
		return 2;
	}
	mount("devtmpfs", "/dev", "devtmpfs", 0, NULL);
	fd = open("/dev/console", O_WRONLY);
	if (fd >= 0) {
		dup2(fd, 1);
		dup2(fd, 2);
		if (fd > 2)
			close(fd);
	}
	setvbuf(stdout, NULL, _IONBF, 0);
	mount("proc", "/proc", "proc", 0, NULL);
	mount("sysfs", "/sys", "sysfs", 0, NULL);
	printf("\n@@SH BEGIN\n");
	page = (unsigned long)sysconf(_SC_PAGESIZE);
	zfd = open("/dev/zero", O_RDONLY);
	emit_int("page_size", (long)page);
	if (zfd < 0)
		emit_err("uaccess_top", "open_zero");
	else
		probe_uaccess();
	probe_mmap();
	probe_mm_tbi();
	emit_hex("hwcap", getauxval(AT_HWCAP));
	emit_hex("hwcap2", getauxval(AT_HWCAP2));
	probe_hugepages();
	emit_int("nr_cpus_conf", sysconf(_SC_NPROCESSORS_CONF));
	printf("{\"taint_changed\":0}\n");
	printf("@@SH END\n");
	fflush(stdout);
	sync();
	reboot(RB_POWER_OFF);
	return 0;
}
