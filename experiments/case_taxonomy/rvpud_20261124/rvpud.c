/* rvpud criteria 四: runs as /init on riscv.  Mode from the kernel command line: rvpud=A|C|D
 *   A: touch a 1GB vfio BAR mapping, mprotect(PROT_NONE), munmap            (T1 / T3)
 *   C: same, but mprotect(PROT_READ)                                         (T2)
 *   D: PROT_NONE, then back to PROT_READ|PROT_WRITE, touch in a child, munmap (T4, observe only)
 * The 1GB mapping: QEMU ivshmem-plain (vendor 1af4, device 1110) BAR2, bound to vfio-pci in no-IOMMU mode. */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/vfio.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/wait.h>
#include <unistd.h>

#define GB (1UL << 30)

static void put(const char *path, const char *val)
{
	int fd = open(path, O_WRONLY);
	if (fd < 0 || write(fd, val, strlen(val)) < 0)
		printf("@@WRITE-FAIL %s <- %s: %s\n", path, val, strerror(errno));
	if (fd >= 0)
		close(fd);
}

static int get(const char *path, char *buf, int n)
{
	int fd = open(path, O_RDONLY), k;
	if (fd < 0)
		return -1;
	k = read(fd, buf, n - 1);
	close(fd);
	buf[k < 0 ? 0 : k] = 0;
	return k;
}

static void done(int code)
{
	printf("@@END %d\n", code);
	fflush(stdout);
	sync();
	reboot(RB_POWER_OFF);
	exit(code);
}

int main(void)
{
	char buf[4096], dev[64] = "", p[256], mode = 'A';
	struct dirent *e;
	DIR *d;

	setvbuf(stdout, NULL, _IONBF, 0);
	mount("proc", "/proc", "proc", 0, NULL);
	mount("sysfs", "/sys", "sysfs", 0, NULL);
	mount("devtmpfs", "/dev", "devtmpfs", 0, NULL);
	mount("debugfs", "/sys/kernel/debug", "debugfs", 0, NULL);
	if (get("/proc/cmdline", buf, sizeof(buf)) > 0) {
		char *m = strstr(buf, "rvpud=");
		if (m)
			mode = m[6];
	}
	printf("@@MODE %c\n", mode);
	put("/sys/kernel/debug/dynamic_debug/control", "file vfio_pci_core.c +p");

	d = opendir("/sys/bus/pci/devices");
	while (d && (e = readdir(d))) {
		char v[32], i[32];
		snprintf(p, sizeof(p), "/sys/bus/pci/devices/%s/vendor", e->d_name);
		if (get(p, v, sizeof(v)) <= 0)
			continue;
		snprintf(p, sizeof(p), "/sys/bus/pci/devices/%s/device", e->d_name);
		get(p, i, sizeof(i));
		if (!strncmp(v, "0x1af4", 6) && !strncmp(i, "0x1110", 6))
			snprintf(dev, sizeof(dev), "%s", e->d_name);
	}
	if (!dev[0]) {
		printf("@@NO-IVSHMEM\n");
		done(2);
	}
	printf("@@DEV %s\n", dev);
	snprintf(p, sizeof(p), "/sys/bus/pci/devices/%s/driver_override", dev);
	put(p, "vfio-pci");
	put("/sys/bus/pci/drivers_probe", dev);

	snprintf(p, sizeof(p), "/sys/bus/pci/devices/%s/iommu_group", dev);
	int k = readlink(p, buf, sizeof(buf) - 1);
	if (k < 0) {
		printf("@@NO-GROUP %s\n", strerror(errno));
		done(2);
	}
	buf[k] = 0;
	snprintf(p, sizeof(p), "/dev/vfio/noiommu-%s", strrchr(buf, '/') + 1);
	int container = open("/dev/vfio/vfio", O_RDWR), group = open(p, O_RDWR);
	if (container < 0 || group < 0) {
		printf("@@OPEN-FAIL %s %d %d %s\n", p, container, group, strerror(errno));
		done(2);
	}
	if (ioctl(group, VFIO_GROUP_SET_CONTAINER, &container) || ioctl(container, VFIO_SET_IOMMU, VFIO_NOIOMMU_IOMMU)) {
		printf("@@SETUP-FAIL %s\n", strerror(errno));
		done(2);
	}
	int fd = ioctl(group, VFIO_GROUP_GET_DEVICE_FD, dev);
	struct vfio_region_info ri = { .argsz = sizeof(ri), .index = VFIO_PCI_BAR2_REGION_INDEX };
	if (fd < 0 || ioctl(fd, VFIO_DEVICE_GET_REGION_INFO, &ri)) {
		printf("@@REGION-FAIL %d %s\n", fd, strerror(errno));
		done(2);
	}
	printf("@@BAR2 size=0x%llx offset=0x%llx flags=0x%x\n", (unsigned long long)ri.size,
	       (unsigned long long)ri.offset, ri.flags);
	if (ri.size < GB || !(ri.flags & VFIO_REGION_INFO_FLAG_MMAP)) {
		printf("@@BAR2-UNUSABLE\n");
		done(2);
	}

	/* a 1GB-aligned address: reserve 2GB, map the BAR over the aligned 1GB inside it */
	char *res = mmap(NULL, 2 * GB, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_NORESERVE, -1, 0);
	char *a = (char *)(((uintptr_t)res + GB - 1) & ~(GB - 1));
	char *m = mmap(a, GB, PROT_READ | PROT_WRITE, MAP_SHARED | MAP_FIXED, fd, ri.offset);
	if (m == MAP_FAILED) {
		printf("@@MMAP-FAIL %s\n", strerror(errno));
		done(2);
	}
	printf("@@MAPPED %p\n", m);
	*(volatile int *)m = 0x5a5a;
	printf("@@TOUCHED read=0x%x\n", *(volatile int *)(m + GB - 4096));

	int r = mprotect(m, GB, mode == 'C' ? PROT_READ : PROT_NONE);
	printf("@@MPROTECT1 %s ret=%d %s\n", mode == 'C' ? "PROT_READ" : "PROT_NONE", r, r ? strerror(errno) : "");
	if (mode == 'D') {
		r = mprotect(m, GB, PROT_READ | PROT_WRITE);
		printf("@@MPROTECT2 PROT_READ|PROT_WRITE ret=%d %s\n", r, r ? strerror(errno) : "");
		pid_t c = fork();
		if (c == 0) {
			alarm(20);
			int v = *(volatile int *)m;
			*(volatile int *)(m + 8192) = 0x1234;
			printf("@@CHILD read=0x%x write ok\n", v);
			_exit(0);
		}
		int st = 0;
		waitpid(c, &st, 0);
		printf("@@CHILD-STATUS exited=%d code=%d signaled=%d sig=%d\n", WIFEXITED(st), WEXITSTATUS(st),
		       WIFSIGNALED(st), WIFSIGNALED(st) ? WTERMSIG(st) : 0);
	}
	r = munmap(m, GB);
	printf("@@MUNMAP ret=%d\n", r);
	done(0);
}
