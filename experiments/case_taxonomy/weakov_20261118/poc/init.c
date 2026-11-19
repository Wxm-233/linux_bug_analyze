/* Guest /init (static, aarch64): ACPI hot-remove of CPU 1, check its sysfs device, then hot-add it back.
 * Every result line starts with "WK:" so the host script can grep it. */
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <unistd.h>

#define CPUDIR "/sys/devices/system/cpu/cpu1"

static int exists(const char *p) { struct stat st; return stat(p, &st) == 0; }

static int rd(const char *p, char *buf, int n)
{
	int fd = open(p, O_RDONLY), k;
	if (fd < 0) return -errno;
	k = read(fd, buf, n - 1);
	close(fd);
	if (k < 0) return -errno;
	buf[k] = 0;
	while (k > 0 && (buf[k - 1] == '\n' || buf[k - 1] == ' ')) buf[--k] = 0;
	return k;
}

static int wr(const char *p, const char *s, int n)
{
	int fd = open(p, O_WRONLY), k, e;
	if (fd < 0) return -errno;
	k = write(fd, s, n);
	e = errno;
	close(fd);
	return k < 0 ? -e : k;
}

static void msleep(int ms) { usleep(ms * 1000); }

/* find the ACPI device whose namespace path is \_SB_.C001 */
static int find_acpi(char *out, int n)
{
	DIR *d = opendir("/sys/bus/acpi/devices");
	struct dirent *e;
	char p[600], v[128];
	if (!d) return -1;
	while ((e = readdir(d))) {
		if (strncmp(e->d_name, "ACPI0007:", 9)) continue;
		snprintf(p, sizeof p, "/sys/bus/acpi/devices/%.200s/path", e->d_name);
		if (rd(p, v, sizeof v) > 0 && strstr(v, "C001")) {
			snprintf(out, n, "/sys/bus/acpi/devices/%.200s", e->d_name);
			closedir(d);
			return 0;
		}
	}
	closedir(d);
	return -1;
}

/* _STA of the ACPI device as Linux reports it; -1 when the device or attribute is gone */
static int acpi_sta(void)
{
	char acpi[600], p[700], v[32];
	if (find_acpi(acpi, sizeof acpi)) return -1;
	snprintf(p, sizeof p, "%s/status", acpi);
	return rd(p, v, sizeof v) > 0 ? atoi(v) : -1;
}

static void state(const char *tag)
{
	char v[64] = "?", acpi[600], pn[700] = "";
	int on = rd(CPUDIR "/online", v, sizeof v), have = find_acpi(acpi, sizeof acpi) == 0;
	/* physical_node: set by acpi_bind_one() in acpi_processor_add(), removed by acpi_unbind_one() on eject */
	if (have)
		snprintf(pn, sizeof pn, "%s/physical_node", acpi);
	printf("WK: %s cpu1_sysfs=%s online=%s acpi_dev=%s acpi_sta=%d phys=%s\n", tag, exists(CPUDIR) ? "present" : "absent",
	       on > 0 ? v : "n/a", have ? acpi : "none", acpi_sta(), have && exists(pn) ? "yes" : "no");
	fflush(stdout);
}

static int copy_file(const char *src, const char *dst)
{
	static char buf[65536];
	int fd = open(src, O_RDONLY), k;
	if (fd < 0) return -errno;
	k = read(fd, buf, sizeof buf);
	close(fd);
	if (k <= 0) return -EIO;
	return wr(dst, buf, k);
}

int main(void)
{
	char acpi[600], p[700], v[64];
	int r, i;

	mount("proc", "/proc", "proc", 0, 0);
	mount("sysfs", "/sys", "sysfs", 0, 0);
	mount("devtmpfs", "/dev", "devtmpfs", 0, 0);
	mount("configfs", "/sys/kernel/config", "configfs", 0, 0);
	setvbuf(stdout, NULL, _IOLBF, 0);
	printf("WK: start\n");

	if (find_acpi(acpi, sizeof acpi)) {
		printf("WK: ERROR no ACPI0007 device with path C001\n");
		goto out;
	}
	snprintf(p, sizeof p, "%s/eject", acpi);
	printf("WK: acpi device %s eject_attr=%s\n", acpi, exists(p) ? "yes" : "no");
	state("BEFORE");

	/* 1. hot-remove: write 1 to eject (offlines the CPU, runs _EJ0, then post_eject) */
	r = wr(p, "1", 1);
	printf("WK: eject write ret=%d\n", r);
	/* eject runs in a workqueue; it is complete once _STA reads 0 (the ACPI device object may stay) */
	for (i = 0; i < 100 && acpi_sta() > 0; i++)
		msleep(100);
	msleep(1000);
	if (acpi_sta() > 0) {
		printf("WK: ERROR eject did not complete (_STA still non-zero)\n");
		state("AFTER_EJECT");
		goto out;
	}
	state("AFTER_EJECT");

	/* 2. hot-add the same CPU back: load an SSDT whose module-level code restores _STA and notifies */
	mkdir("/sys/kernel/config/acpi/table/readd", 0755);
	r = copy_file("/ssdt_readd.aml", "/sys/kernel/config/acpi/table/readd/aml");
	printf("WK: readd table load ret=%d\n", r);
	for (i = 0; i < 50 && acpi_sta() <= 0; i++)
		msleep(100);
	msleep(2000);
	state("AFTER_ADD");
	r = wr(CPUDIR "/online", "1", 1);
	msleep(1000);
	printf("WK: online write ret=%d\n", r);
	state("AFTER_ONLINE");
	r = rd("/sys/devices/system/cpu/online", v, sizeof v);
	printf("WK: cpus_online=%s\n", r > 0 ? v : "?");
out:
	printf("WK: DONE\n");
	fflush(stdout);
	sync();
	reboot(RB_POWER_OFF);
	return 0;
}
