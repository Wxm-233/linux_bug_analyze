/*
 * /init for the machine_shutdown verification (plan.md).
 * First kernel: load /Image with /init2.cpio via kexec_file_load and reboot into it with LINUX_REBOOT_CMD_KEXEC.
 * Second kernel (cmdline contains kexec_second=1): print a marker and power off.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/reboot.h>
#include <stdio.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/syscall.h>
#include <unistd.h>

static const char second_cmdline[] = "console=ttyS0 panic=-1 kexec_second=1";

static void power_off(void)
{
	sync();
	reboot(RB_POWER_OFF);
}

int main(void)
{
	char cmdline[512] = "";
	int fd, kfd, ifd;
	ssize_t n;

	setvbuf(stdout, NULL, _IONBF, 0);
	mount("proc", "/proc", "proc", 0, NULL);
	fd = open("/proc/cmdline", O_RDONLY);
	if (fd >= 0) {
		n = read(fd, cmdline, sizeof(cmdline) - 1);
		cmdline[n > 0 ? n : 0] = 0;
		close(fd);
	}
	printf("KEXEC-TEST online_cpus=%ld cmdline=%s", sysconf(_SC_NPROCESSORS_ONLN), cmdline);
	if (strstr(cmdline, "kexec_second=1")) {
		printf("KEXEC-TEST SECOND KERNEL UP\n");
		power_off();
		return 0;
	}
	kfd = open("/Image", O_RDONLY);
	ifd = open("/init2.cpio", O_RDONLY);
	if (kfd < 0 || ifd < 0) {
		printf("KEXEC-TEST precondition-failed open (%s)\n", strerror(errno));
		power_off();
		return 1;
	}
	if (syscall(SYS_kexec_file_load, kfd, ifd, sizeof(second_cmdline), second_cmdline, 0UL)) {
		printf("KEXEC-TEST precondition-failed kexec_file_load (%s)\n", strerror(errno));
		power_off();
		return 1;
	}
	printf("KEXEC-TEST loaded; rebooting with LINUX_REBOOT_CMD_KEXEC\n");
	sync();
	syscall(SYS_reboot, LINUX_REBOOT_MAGIC1, LINUX_REBOOT_MAGIC2, LINUX_REBOOT_CMD_KEXEC, NULL);
	printf("KEXEC-TEST reboot returned (%s)\n", strerror(errno));
	power_off();
	return 1;
}
