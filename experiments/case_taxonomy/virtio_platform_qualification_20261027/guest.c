#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <unistd.h>
#include <fcntl.h>
#include <dirent.h>
#include <errno.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/reboot.h>
#include <sys/utsname.h>
#include <linux/input.h>
#include <poll.h>
static void file(const char *p){char b[2048];int f=open(p,O_RDONLY);if(f<0){printf("LBA_FILE path=%s error=%d\n",p,errno);return;}ssize_t n=read(f,b,sizeof(b)-1);close(f);if(n>=0){b[n]=0;printf("LBA_FILE path=%s value=%s\n",p,b);}}
int main(void){setvbuf(stdout,NULL,_IONBF,0);mkdir("/dev",0755);mkdir("/proc",0755);mkdir("/sys",0755);mount("devtmpfs","/dev","devtmpfs",0,NULL);mount("proc","/proc","proc",0,NULL);mount("sysfs","/sys","sysfs",0,NULL);struct utsname u;if(!uname(&u))printf("LBA_GUEST release=%s machine=%s\n",u.release,u.machine);DIR*d=opendir("/sys/bus/virtio/devices");struct dirent*e;char p[256];if(d){while((e=readdir(d))){if(e->d_name[0]=='.')continue;const char*attrs[]={"device","features","status","uevent"};for(unsigned i=0;i<4;i++){snprintf(p,sizeof(p),"/sys/bus/virtio/devices/%.80s/%s",e->d_name,attrs[i]);file(p);}}closedir(d);}int fd=-1;for(int i=0;i<50&&fd<0;i++){fd=open("/dev/input/event0",O_RDONLY|O_NONBLOCK);if(fd<0)usleep(100000);}printf("LBA_USER_READY fd=%d error=%d\n",fd,fd<0?errno:0);int down=0,up=0,total=0;for(int i=0;i<100&&fd>=0&&(!down||!up);i++){struct pollfd f={fd,POLLIN,0};if(poll(&f,1,200)<=0)continue;struct input_event v[16];ssize_t n=read(fd,v,sizeof(v));if(n<=0)continue;for(unsigned j=0;j<(unsigned)n/sizeof(*v);j++){printf("LBA_USER_EVENT type=%u code=%u value=%d\n",v[j].type,v[j].code,v[j].value);total++;if(v[j].type==EV_KEY&&v[j].code==KEY_A){down|=v[j].value==1;up|=v[j].value==0;}}}printf("LBA_USER_DONE down=%d up=%d total=%d\n",down,up,total);sync();reboot(RB_POWER_OFF);for(;;)pause();}
