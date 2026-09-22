/* Real x86-64 syscalls and x86 compat dispatch via int 0x80. No kernel edits. */
#define _GNU_SOURCE
#include <sys/mman.h>
#include <sys/syscall.h>
#include <sys/utsname.h>
#include <unistd.h>
#include <stdint.h>
#include <stdio.h>
#include <errno.h>
#include <string.h>
#include <stdlib.h>

static long compat_set(unsigned long ptr, unsigned long maxnode) {
    long result;
    __asm__ volatile("int $0x80" : "=a"(result) : "0"(276), "b"(2), "c"(ptr), "d"(maxnode) : "memory");
    return (int32_t)result;
}
int main(void) {
    struct utsname u;uname(&u);printf("kernel=%s machine=%s\n",u.release,u.machine);
    unsigned long allowed[1024]={0};
    long rc=syscall(SYS_get_mempolicy,NULL,allowed,32768UL,NULL,4UL);
    if(rc<0){printf("environment_blocked errno=%d %s\n",errno,strerror(errno));return 77;}
    int node=-1;for(int i=0;i<32768;i++)if(allowed[i/64]&(1UL<<(i%64))){node=i;break;}
    printf("first_allowed_node=%d\n",node);if(node<0||node>=64)return 78;
    size_t page=sysconf(_SC_PAGESIZE);
    unsigned char *mem=mmap(NULL,page*2,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_32BIT,-1,0);
    if(mem==MAP_FAILED||mprotect(mem+page,page,PROT_NONE))return 79;
    const unsigned sizes[]={32,64,65,96,127,128,1025,1056};
    for(int compat=0;compat<2;compat++)for(unsigned k=0;k<sizeof(sizes)/sizeof(*sizes);k++)for(int padded=0;padded<2;padded++)for(int tail=0;tail<2;tail++){
        unsigned bits=sizes[k];if((unsigned)node>=bits)continue;
        unsigned word=compat?32:64;size_t bytes=((bits+1+word-1)/word)*(word/8);
        if(padded)bytes=((bits+1+63)/64)*8;
        unsigned char *p=mem+page-bytes;memset(mem,0,page);p[node/8]|=1U<<(node%8);
        if(tail)p[(bits-1)/8]|=1U<<((bits-1)%8);
        errno=0;long set=compat?compat_set((uintptr_t)p,bits+1):syscall(SYS_set_mempolicy,2,p,bits+1);
        if(!compat&&set<0)set=-errno;
        int mode=-1;unsigned long actual[1024]={0};errno=0;
        long get=syscall(SYS_get_mempolicy,&mode,actual,32768UL,NULL,0);
        int page_node=-1;long page_rc=-1;
        if(set==0){
            void *allocation=mmap(NULL,page,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
            if(allocation==MAP_FAILED)return 82;
            *(volatile char*)allocation=1;
            page_rc=syscall(SYS_get_mempolicy,&page_node,NULL,0,allocation,3UL);
            munmap(allocation,page);
        }
        printf("{\"compat_dispatch\":%d,\"bits\":%u,\"maxnode\":%u,\"bytes\":%zu,\"padding64\":%d,\"tail\":%d,\"set_rc\":%ld,\"get_rc\":%ld,\"mode\":%d,\"mask0\":%lu,\"page_query_rc\":%ld,\"page_node\":%d}\n",compat,bits,bits+1,bytes,padded,tail,set,get,mode,actual[0],page_rc,page_node);
        if(syscall(SYS_set_mempolicy,0,NULL,0))return 80;
    }
    munmap(mem,page*2);return 0;
}
