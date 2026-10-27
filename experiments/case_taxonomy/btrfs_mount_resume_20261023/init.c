#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/reboot.h>
static int failures;
static void check(int ok,const char *step) { if(!ok){printf("ERROR step=%s errno=%d\n",step,errno);failures++;} }
static void mounts(void) { char b[4096]; int f=open("/proc/mounts",O_RDONLY); ssize_t n; while((n=read(f,b,sizeof b))>0) fwrite(b,1,n,stdout); close(f); }
int main(void) {
 setbuf(stdout,NULL); mkdir("/dev",0755);mkdir("/proc",0755);mkdir("/sys",0755);mkdir("/mnt",0755);
 check(!mount("devtmpfs","/dev","devtmpfs",0,NULL),"devtmpfs");
 check(!mount("proc","/proc","proc",0,NULL),"proc");
 check(!mount("sysfs","/sys","sysfs",0,NULL),"sysfs");
 printf("PAGE_SIZE=%ld\n",sysconf(_SC_PAGESIZE));
 int opts[]={2048,8192}; int sizes[]={1024,6144,8192};
 for(int o=0;o<2;o++) {
  char option[80];snprintf(option,sizeof option,"max_inline=%d",opts[o]);
  int m=mount("/dev/vda","/mnt","btrfs",0,option);printf("MOUNT request=%d rc=%d errno=%d\n",opts[o],m,m<0?errno:0);check(!m,"btrfs_mount");if(m)continue;
  mounts();
  for(int s=0;s<3;s++) {
   unsigned char data[8192], got[8192];for(int i=0;i<sizes[s];i++)data[i]=(unsigned char)(i*37+11);
   char p[128];snprintf(p,sizeof p,"/mnt/option%d_size%d",opts[o],sizes[s]);
   int f=open(p,O_CREAT|O_EXCL|O_RDWR,0644);check(f>=0,"create");if(f<0)continue;
   check(write(f,data,sizes[s])==sizes[s],"write");check(!fsync(f),"fsync");
   struct stat st;check(!fstat(f,&st),"stat");
   check(lseek(f,0,SEEK_SET)==0,"seek");int same=read(f,got,sizes[s])==sizes[s]&&!memcmp(got,data,sizes[s]);check(same,"readback");
   printf("FILE option=%d size=%d inode=%lu blocks=%lu readback=%d\n",opts[o],sizes[s],(unsigned long)st.st_ino,(unsigned long)st.st_blocks,same);close(f);
  }
  sync();check(!umount("/mnt"),"umount");
  check(!mount("/dev/vda","/mnt","btrfs",MS_RDONLY,NULL),"remount_ro");
  for(int s=0;s<3;s++) {char p[128];unsigned char b[8192];snprintf(p,sizeof p,"/mnt/option%d_size%d",opts[o],sizes[s]);int f=open(p,O_RDONLY);ssize_t n=read(f,b,sizes[s]);int ok=n==sizes[s];for(int i=0;ok&&i<n;i++)ok=b[i]==(unsigned char)(i*37+11);check(ok,"persisted_readback");printf("PERSISTED option=%d size=%d equal=%d\n",opts[o],sizes[s],ok);if(f>=0)close(f);}
  check(!umount("/mnt"),"umount_ro");
 }
 printf("EXPERIMENT_DONE failures=%d\n",failures);sync();reboot(RB_POWER_OFF);return failures;
}
