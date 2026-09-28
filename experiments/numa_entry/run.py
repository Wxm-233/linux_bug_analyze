"""Historical set_mempolicy conversion chains with host protected-page input."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.iommu_contracts.run import function

REVS={'before':'e130242dc351f1cfa2bbeb6766a1486ce936ef88^',
      'unified':'e130242dc351f1cfa2bbeb6766a1486ce936ef88',
      'followup':'000eca5d044d1ee23b4ca311793cf3fc528da6c6'}

HEADER=r'''
#define _GNU_SOURCE
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <errno.h>
#include <signal.h>
#include <setjmp.h>
#include <sys/mman.h>
#include <unistd.h>
#define __user
typedef uint32_t compat_ulong_t;
#define BITS_PER_COMPAT_LONG 32
#define BITS_PER_LONG 64
#define BITS_PER_BYTE 8
#define PAGE_SIZE 4096
#define MAX_NUMNODES 64
#define ALIGN(x,a) (((x)+(a)-1)&~((a)-1))
#define BITS_TO_LONGS(n) (((n)+63)/64)
#define BITS_TO_COMPAT_LONGS(n) (((n)+31)/32)
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
#define DECLARE_BITMAP(n,b) unsigned long n[BITS_TO_LONGS(b)]
typedef struct {unsigned long bits[1];} nodemask_t;
#define nodes_addr(n) ((n).bits)
#define nodes_clear(n) memset(&(n),0,sizeof(n))
#define MPOL_F_STATIC_NODES (1<<15)
#define MPOL_F_RELATIVE_NODES (1<<14)
#define MPOL_MODE_FLAGS (MPOL_F_STATIC_NODES|MPOL_F_RELATIVE_NODES)
#define MPOL_MAX 5
#define SYSCALL_DEFINE3(name,t1,a1,t2,a2,t3,a3) long native_entry(t1 a1,t2 a2,t3 a3)
#define COMPAT_SYSCALL_DEFINE3(name,t1,a1,t2,a2,t3,a3) long compat_entry(t1 a1,t2 a2,t3 a3)
static int compat_mode,consumed;static unsigned long captured;
static sigjmp_buf recovery;static volatile sig_atomic_t armed,faults;
static void handler(int sig) {if(armed) {faults++;siglongjmp(recovery,1);} _exit(128+sig);}
static size_t checked_copy(void *dst,const void *src,size_t n) {
 if(sigsetjmp(recovery,1)) {armed=0;return n;}
 armed=1;
 for(size_t i=0;i<n;i++) ((volatile unsigned char*)dst)[i]=((const volatile unsigned char*)src)[i];
 armed=0;return 0;
}
#define copy_from_user(d,s,n) checked_copy(d,s,n)
#define copy_to_user(d,s,n) checked_copy(d,s,n)
#define get_user(v,p) (checked_copy(&(v),(p),sizeof(*(p)))?-EFAULT:0)
#define user_read_access_begin(p,n) ((void)(p),(void)(n),true)
#define user_read_access_end() do {} while(0)
#define unsafe_get_user(v,p,label) do {compat_ulong_t tmp;const compat_ulong_t *q=(p);if(checked_copy(&tmp,q,sizeof(tmp))) goto label;(v)=tmp;} while(0)
static inline int in_compat_syscall(void) {return compat_mode;}
static unsigned long temporary[4];
static inline void *compat_alloc_user_space(size_t n) {if(n>sizeof(temporary)) abort();memset(temporary,0,sizeof(temporary));return temporary;}
static int do_set_mempolicy(int mode,unsigned short flags,nodemask_t *nodes) {
 (void)mode;(void)flags;consumed++;captured=nodes->bits[0];return 0;
}
'''

MAIN=r'''
int main(int argc,char **argv) {
 if(argc!=5) return 2;
 unsigned bits=atoi(argv[1]);compat_mode=atoi(argv[2]);int pattern=atoi(argv[3]);int short_input=atoi(argv[4]);
 if(bits<1 || bits>256) return 3;
 long page=sysconf(_SC_PAGESIZE);if(page!=4096) return 4;
 unsigned char *mem=mmap(NULL,2*page,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
 if(mem==MAP_FAILED || mprotect(mem+page,page,PROT_NONE)) return 5;
 unsigned word=compat_mode?32:64;size_t bytes=((bits+word-1)/word)*(word/8);
 unsigned char *input=mem+page-bytes+(short_input?word/8:0);
 memset(mem,0,page);
 // Logical node zero is always requested. Pattern 1 additionally selects node 64.
 unsigned char data[64]={0};
 if(compat_mode) {((uint32_t*)data)[0]=1;if(pattern && bits>64)((uint32_t*)data)[2]=1;}
 else {((unsigned long*)data)[0]=1;if(pattern && bits>64)((unsigned long*)data)[1]=1;}
 memcpy(input,data,bytes-(short_input?word/8:0));
 struct sigaction sa={0};sa.sa_handler=handler;sigemptyset(&sa.sa_mask);
 sigaction(SIGSEGV,&sa,NULL);sigaction(SIGBUS,&sa,NULL);
 long rc=compat_mode?compat_entry(2,(compat_ulong_t*)input,bits+1):native_entry(2,(unsigned long*)input,bits+1);
 printf("{\"rc\":%ld,\"consumed\":%d,\"value\":%lu,\"page_faults\":%d}\n",rc,consumed,captured,(int)faults);
 munmap(mem,2*page);return 0;
}
'''

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--linux-dir',type=Path,required=True)
    ap.add_argument('--outdir',type=Path,required=True);a=ap.parse_args()
    out=a.outdir.resolve();out.mkdir(parents=True,exist_ok=False)
    # Frozen before executing any revision. Exact-width and partial-word tails.
    fixtures=[]
    for bits in (1,32,33,64,65,96,127,128,192):
        for compat in (0,1):
            for pattern in ((0,1) if bits>64 else (0,)):
                fixtures.append(dict(name=f'b{bits}-c{compat}-p{pattern}',args=[bits,compat,pattern,0],
                    expected={'rc':-22 if pattern else 0,'consumed':0 if pattern else 1,'value':0 if pattern else 1}))
    for bits in (32,64):
        for compat in (0,1):
            fixtures.append(dict(name=f'b{bits}-c{compat}-short',args=[bits,compat,0,1],
                expected={'rc':-14,'consumed':0,'value':0}))
    (out/'fixtures.json').write_text(json.dumps(fixtures,indent=2)+'\n')
    manifest={'scope':'real historical native/compat entry conversion chains; policy sink and uaccess recovery are doubles',
              'compiler':subprocess.check_output(['gcc','--version'],text=True).splitlines()[0], 'sources':[]}
    summary={}
    for mode,ref in REVS.items():
        folder=out/mode;folder.mkdir()
        revision=subprocess.check_output(['git','-C',str(a.linux_dir),'rev-parse',ref],text=True).strip()
        def read(path):
            data=subprocess.check_output(['git','-C',str(a.linux_dir),'show',revision+':'+path])
            file=folder/path.replace('/','_');file.write_bytes(data)
            manifest['sources'].append(dict(mode=mode,revision=revision,path=path,sha256=hashlib.sha256(data).hexdigest()))
            return data.decode()
        mem=read('mm/mempolicy.c');compat=read('kernel/compat.c')
        if mode=='followup':
            # Hold the 2021 entry chain fixed: later kernels remove compat wrappers.
            # Replay only the genuine 2022 get_nodes correction, not a full 2022 kernel.
            corrected=function(mem,'static int get_nodes(')
            base_ref=REVS['unified']
            base_data=subprocess.check_output(['git','-C',str(a.linux_dir),'show',base_ref+':mm/mempolicy.c'])
            (folder/'entry-base-mm_mempolicy.c').write_bytes(base_data)
            manifest['sources'].append(dict(mode=mode,revision=base_ref,path='mm/mempolicy.c',role='entry_chain_base',sha256=hashlib.sha256(base_data).hexdigest()))
            mem=base_data.decode(); old=function(mem,'static int get_nodes(')
            assert corrected==old.replace('nmask[maxnode / BITS_PER_LONG]','nmask[(maxnode - 1) / BITS_PER_LONG]')
            mem=mem.replace(old,corrected)
        src=HEADER+function(compat,'long compat_get_bitmap(')
        if mode!='before': src+=function(mem,'static int get_bitmap(')
        for sig in ('static int get_nodes(', 'static inline int sanitize_mpol_flags(',
                    'static long kernel_set_mempolicy(', 'SYSCALL_DEFINE3(set_mempolicy,',
                    'COMPAT_SYSCALL_DEFINE3(set_mempolicy,'):
            src+='\n'+function(mem,sig)
        src+=MAIN
        file=folder/'harness.c';file.write_text(src);exe=folder/'harness'
        cmd=['gcc','-O2','-Wall','-Wextra','-Werror',str(file),'-o',str(exe)]
        build=subprocess.run(cmd,capture_output=True,text=True)
        (folder/'build.log').write_text(build.stdout+build.stderr)
        if build.returncode:raise RuntimeError(str(folder/'build.log'))
        rows=[]
        for f in fixtures:
            p=subprocess.run([str(exe),*map(str,f['args'])],capture_output=True,text=True,timeout=5,check=True)
            actual=json.loads(p.stdout);observed={k:actual[k] for k in ('rc','consumed','value')}
            rows.append({**f,'actual':actual,'passed':observed==f['expected']})
        (folder/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
        summary[mode]={'count':len(rows),'passed':sum(r['passed'] for r in rows),
            'failed':[r['name'] for r in rows if not r['passed']],
            'faulted':[r['name'] for r in rows if r['actual']['page_faults']]}
    manifest['artifacts']={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
