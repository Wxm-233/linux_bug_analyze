/*
 * X1 closed loop (x1loop criteria 二): property check, run as /init.
 * Property P: every byte read from never-written anonymous memory is 0.
 * Per round: dirty 512 MiB (amendment 1) with 0xA5 and free it; drop caches (lets the huge zero folio be freed and
 * reallocated); map 8 MiB anonymous, align to 2 MiB, MADV_HUGEPAGE, read 3 blocks of 2 MiB without writing.
 * One JSON line per round; "@@END" at the end; then power off.
 */
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

#define MB (1024UL * 1024UL)
#define HPAGE (2 * MB)

static int write_file(const char *path, const char *val)
{
	int fd = open(path, O_WRONLY);
	if (fd < 0)
		return -1;
	int n = write(fd, val, strlen(val));
	close(fd);
	return n < 0 ? -1 : 0;
}

static void read_file(const char *path, char *buf, size_t len)
{
	int fd = open(path, O_RDONLY);
	buf[0] = 0;
	if (fd < 0) {
		snprintf(buf, len, "<none>");
		return;
	}
	int n = read(fd, buf, len - 1);
	close(fd);
	buf[n > 0 ? n : 0] = 0;
	for (char *p = buf; *p; p++)
		if (*p == '\n' || *p == '"')
			*p = ' ';
}

static long vmstat(const char *key)
{
	static char buf[65536];
	int fd = open("/proc/vmstat", O_RDONLY);
	if (fd < 0)
		return -1;
	int n = read(fd, buf, sizeof(buf) - 1);
	close(fd);
	if (n <= 0)
		return -1;
	buf[n] = 0;
	size_t kl = strlen(key);
	for (char *p = buf; p && *p; p = strchr(p, '\n') ? strchr(p, '\n') + 1 : NULL)
		if (!strncmp(p, key, kl) && p[kl] == ' ')
			return atol(p + kl + 1);
	return -1;
}

int main(void)
{
	char thp[256], zp[64];

	mkdir("/proc", 0755);
	mkdir("/sys", 0755);
	mount("proc", "/proc", "proc", 0, NULL);
	mount("sysfs", "/sys", "sysfs", 0, NULL);
	int set = write_file("/sys/kernel/mm/transparent_hugepage/enabled", "always");
	read_file("/sys/kernel/mm/transparent_hugepage/enabled", thp, sizeof(thp));
	read_file("/sys/kernel/mm/transparent_hugepage/use_zero_page", zp, sizeof(zp));
	printf("{\"setup\":1,\"thp_set_ret\":%d,\"thp_enabled\":\"%s\",\"use_zero_page\":\"%s\"}\n", set, thp, zp);
	fflush(stdout);

	for (int r = 1; r <= 8; r++) {  /* amendment 2: 8 rounds */
		size_t dsz = 512 * MB;
		unsigned char *d = mmap(NULL, dsz, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
		int dirty_ok = d != MAP_FAILED;
		int dirty_unmap = -2;
		if (dirty_ok) {
			memset(d, 0xA5, dsz);
			dirty_unmap = munmap(d, dsz);
		}
		int drop = write_file("/proc/sys/vm/drop_caches", "3");
		/* amendment 2: read in a child process; the per-mm huge zero folio reference goes away when it exits,
		 * so the next round's drop_caches can free the folio and it is allocated afresh every round */
		pid_t pid = fork();
		if (pid > 0) {
			waitpid(pid, NULL, 0);
			continue;
		}
		long z0 = vmstat("thp_zero_page_alloc");

		size_t msz = 8 * MB;
		unsigned char *q = mmap(NULL, msz, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
		int mmap_ok = q != MAP_FAILED;
		int madv = -2, unmap = -2;
		unsigned long nonzero = 0, first_off = 0;
		int first_val = -1;
		if (mmap_ok) {
			unsigned char *a = (unsigned char *)(((uintptr_t)q + HPAGE - 1) & ~(uintptr_t)(HPAGE - 1));
			madv = madvise(a, 3 * HPAGE, MADV_HUGEPAGE);
			for (size_t i = 0; i < 3 * HPAGE; i++) {
				unsigned char v = *(volatile unsigned char *)(a + i);
				if (v) {
					if (!nonzero) {
						first_off = i;
						first_val = v;
					}
					nonzero++;
				}
			}
			unmap = munmap(q, msz);
		}
		long z1 = vmstat("thp_zero_page_alloc");
		printf("{\"round\":%d,\"dirty_ok\":%d,\"dirty_munmap\":%d,\"drop_caches\":%d,\"mmap_ok\":%d,\"madvise\":%d,"
		       "\"munmap\":%d,\"bytes_read\":%lu,\"nonzero\":%lu,\"first_off\":%lu,\"first_val\":%d,"
		       "\"zero_alloc_before\":%ld,\"zero_alloc_delta\":%ld}\n",
		       r, dirty_ok, dirty_unmap, drop, mmap_ok, madv, unmap, (unsigned long)(3 * HPAGE), nonzero,
		       first_off, first_val, z0, z1 - z0);
		fflush(stdout);
		if (pid == 0)
			_exit(0);
	}
	printf("@@END\n");
	fflush(stdout);
	sync();
	reboot(RB_POWER_OFF);
	return 0;
}
