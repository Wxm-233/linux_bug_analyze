#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/reboot.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/utsname.h>
#include <unistd.h>

static void quote(const char *s, size_t n)
{
    putchar('"');
    for (size_t i=0; i<n; ++i) {
        unsigned char c=(unsigned char)s[i];
        if (c=='"' || c=='\\') printf("\\%c", c);
        else if (c=='\n') printf("\\n");
        else if (c=='\r') printf("\\r");
        else if (c=='\t') printf("\\t");
        else if (c<32) printf("\\u%04x", c);
        else putchar(c);
    }
    putchar('"');
}

static void read_file(const char *path)
{
    char buf[65537];
    int fd=open(path,O_RDONLY);
    int e=errno;
    printf("LBA_USER {\"event\":\"file\",\"path\":"); quote(path,strlen(path));
    if (fd<0) { printf(",\"errno\":%d,\"raw\":\"\",\"truncated\":false}\n",e); return; }
    ssize_t n=read(fd,buf,sizeof(buf)); e=errno; close(fd);
    if (n<0) { printf(",\"errno\":%d,\"raw\":\"\",\"truncated\":false}\n",e); return; }
    printf(",\"errno\":0,\"truncated\":%s,\"raw\":",n==(ssize_t)sizeof(buf)?"true":"false");
    quote(buf,(size_t)n); printf("}\n");
}

static void observe_dt(void)
{
    const char *base="/sys/firmware/devicetree/base/cpus";
    DIR *dir=opendir(base);
    if (!dir) { printf("LBA_USER {\"event\":\"DT_error\",\"errno\":%d}\n",errno); return; }
    struct dirent *entry;
    while ((entry=readdir(dir))!=NULL) {
        char path[1024],type[32];
        int len=snprintf(path,sizeof(path),"%s/%s/device_type",base,entry->d_name);
        if (len<0 || (size_t)len>=sizeof(path)) continue;
        int fd=open(path,O_RDONLY);
        if (fd<0) continue;
        ssize_t n=read(fd,type,sizeof(type)); close(fd);
        if (n!=4 || memcmp(type,"cpu\0",4)!=0) continue;
        len=snprintf(path,sizeof(path),"%s/%s/reg",base,entry->d_name);
        if (len<0 || (size_t)len>=sizeof(path)) continue;
        unsigned char reg[16]; fd=open(path,O_RDONLY);
        if (fd<0) continue;
        n=read(fd,reg,sizeof(reg)); close(fd);
        printf("LBA_USER {\"event\":\"dt_cpu\",\"path\":"); quote(path,strlen(path));
        printf(",\"reg_hex\":\"");
        for (ssize_t i=0; i<n; ++i) printf("%02x",(unsigned int)reg[i]);
        printf("\",\"bytes\":%zd}\n",n);
    }
    closedir(dir);
}

int main(void)
{
    setvbuf(stdout,NULL,_IONBF,0);
    printf("LBA_USER {\"event\":\"begin\",\"schema\":\"cpu_identity_runtime_v1\",\"pid\":%ld}\n",(long)getpid());
    mkdir("/proc",0755); mkdir("/sys",0755);
    int p=mount("proc","/proc","proc",0,NULL); int pe=errno;
    int s=mount("sysfs","/sys","sysfs",0,NULL); int se=errno;
    printf("LBA_USER {\"event\":\"mount\",\"proc_rc\":%d,\"proc_errno\":%d,\"sysfs_rc\":%d,\"sysfs_errno\":%d}\n",p,p?pe:0,s,s?se:0);
    struct utsname u;
    if (uname(&u)==0) {
        printf("LBA_USER {\"event\":\"uname\",\"release\":"); quote(u.release,strlen(u.release));
        printf(",\"machine\":"); quote(u.machine,strlen(u.machine)); printf("}\n");
    }
    read_file("/proc/cmdline");
    const char *files[]={"possible","present","online","offline","kernel_max"};
    for (size_t i=0; i<sizeof(files)/sizeof(files[0]); ++i) {
        char path[128]; snprintf(path,sizeof(path),"/sys/devices/system/cpu/%s",files[i]); read_file(path);
    }
    observe_dt();
    printf("LBA_USER {\"event\":\"end\",\"reached_end\":true}\n");
    sync(); reboot(LINUX_REBOOT_CMD_POWER_OFF);
    printf("LBA_USER {\"event\":\"poweroff_returned\",\"errno\":%d}\n",errno);
    for (;;) pause();
}
