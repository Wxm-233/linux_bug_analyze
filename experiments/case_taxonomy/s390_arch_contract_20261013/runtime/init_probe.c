#define _GNU_SOURCE
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/utsname.h>
#include <unistd.h>

static void read_field(const char *label, const char *path)
{
    char buf[256];
    int fd = open(path, O_RDONLY);
    ssize_t n = fd < 0 ? -1 : read(fd, buf, sizeof(buf)-1);
    if (fd >= 0) close(fd);
    if (n < 0) { printf("R4_USER field=%s error=1\n", label); return; }
    buf[n] = 0;
    for (ssize_t i=0; i<n; i++) if (buf[i]=='\n') buf[i]=' ';
    printf("R4_USER field=%s value=%s\n", label, buf);
}

int main(void)
{
    int fd = open("/dev/console", O_RDWR);
    if (fd >= 0) { dup2(fd,0); dup2(fd,1); dup2(fd,2); if (fd>2) close(fd); }
    setvbuf(stdout, NULL, _IONBF, 0);
    struct utsname u;
    if (uname(&u)==0) printf("R4_USER release=%s machine=%s pid=%d\n", u.release,u.machine,getpid());
    printf("R4_USER mount_proc=%d mount_sysfs=%d\n", mount("proc","/proc","proc",0,NULL),mount("sysfs","/sys","sysfs",0,NULL));
    read_field("cmdline","/proc/cmdline");
    read_field("online","/sys/devices/system/cpu/online");
    read_field("cpu1_threads","/sys/devices/system/cpu/cpu1/topology/thread_siblings_list");
    puts("R4_USER end=1");
    sync();
    reboot(RB_POWER_OFF);
    for (;;) pause();
}
