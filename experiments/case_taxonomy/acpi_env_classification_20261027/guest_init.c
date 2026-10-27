/* Static PID1: report CPU sets, wait for one hot-added CPU, try to online it, power off. */
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

static void show(const char *label, const char *path)
{
	char buf[256] = {0};
	int fd = open(path, O_RDONLY), n;

	if (fd < 0) {
		printf("LBA %s=ERR%d\n", label, errno);
		return;
	}
	n = read(fd, buf, sizeof(buf) - 1);
	close(fd);
	while (n > 0 && (buf[n - 1] == '\n' || buf[n - 1] == ' '))
		buf[--n] = 0;
	printf("LBA %s=%s\n", label, buf);
}

static unsigned cpu_dirs(void)
{
	unsigned mask = 0;
	DIR *d = opendir("/sys/devices/system/cpu");
	struct dirent *e;

	if (!d)
		return 0;
	while ((e = readdir(d))) {
		unsigned n;
		char tail;
		if (sscanf(e->d_name, "cpu%u%c", &n, &tail) == 1 && n < 32)
			mask |= 1u << n;
	}
	closedir(d);
	return mask;
}

static void sets(const char *stage)
{
	char l[64];
	snprintf(l, sizeof(l), "%s_possible", stage); show(l, "/sys/devices/system/cpu/possible");
	snprintf(l, sizeof(l), "%s_present", stage); show(l, "/sys/devices/system/cpu/present");
	snprintf(l, sizeof(l), "%s_online", stage); show(l, "/sys/devices/system/cpu/online");
	printf("LBA %s_cpu_dirs=0x%x\n", stage, cpu_dirs());
}

int main(void)
{
	unsigned boot_dirs, now = 0;
	struct timespec pause = {0, 200000000};
	int i, added = -1;

	setvbuf(stdout, NULL, _IONBF, 0);
	mount("proc", "/proc", "proc", 0, NULL);
	mount("sysfs", "/sys", "sysfs", 0, NULL);
	mount("devtmpfs", "/dev", "devtmpfs", 0, NULL);
	show("cmdline", "/proc/cmdline");
	sets("boot");
	boot_dirs = cpu_dirs();
	printf("LBA_READY\n");
	for (i = 0; i < 225 && added < 0; i++) {        /* 45 s */
		nanosleep(&pause, NULL);
		now = cpu_dirs();
		if (now & ~boot_dirs)
			added = __builtin_ctz(now & ~boot_dirs);
	}
	if (added < 0) {
		printf("LBA hotplug_new_cpu_dir=none\n");
	} else {
		char path[96];
		int fd, rc;
		printf("LBA hotplug_new_cpu_dir=cpu%d\n", added);
		snprintf(path, sizeof(path), "/sys/devices/system/cpu/cpu%d/online", added);
		show("hotplug_online_before", path);
		fd = open(path, O_WRONLY);
		if (fd < 0) {
			printf("LBA hotplug_online_write=open_errno%d\n", errno);
		} else {
			rc = write(fd, "1", 1);
			printf("LBA hotplug_online_write=%s%d\n", rc == 1 ? "ok" : "errno", rc == 1 ? 0 : errno);
			close(fd);
		}
		for (i = 0; i < 25; i++)
			nanosleep(&pause, NULL);
		show("hotplug_online_after", path);
	}
	sets("final");
	printf("LBA_DONE\n");
	sync();
	reboot(RB_POWER_OFF);
	return 0;
}
