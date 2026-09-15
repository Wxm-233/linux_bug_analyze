"""Historical NUMA/perf/topology slices on x86_64 and emulated s390x."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.iommu_contracts.run import function

REVS={'numa':'e130242dc351f1cfa2bbeb6766a1486ce936ef88',
      'perf':'aa6a6a2d16c1e2e27e986936369959d70316199f',
      'topology':'a052096bdd6809eeab809202726634d1ac975aa1'}
H='#include <stdio.h>\n#include <stdint.h>\n#include <stdbool.h>\n#include <stdlib.h>\n#include <string.h>\n#include <errno.h>\n'

def numa(read,mode):
    src=read('mm/mempolicy.c'); compat=read('kernel/compat.c')
    get=function(src,'static int get_nodes(')
    bitmap=function(src,'static int get_bitmap(') if mode=='after' else ''
    return H+r'''
#define __user
typedef uint32_t compat_ulong_t;
#define BITS_PER_COMPAT_LONG 32
#define BITS_PER_LONG 64
#define BITS_PER_BYTE 8
#define PAGE_SIZE 4096
#define MAX_NUMNODES 128
#define ALIGN(x,a) (((x)+(a)-1)&~((a)-1))
#define BITS_TO_LONGS(n) (((n)+63)/64)
#define BITS_TO_COMPAT_LONGS(n) (((n)+31)/32)
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
typedef struct {unsigned long bits[2];} nodemask_t;
#define nodes_addr(n) ((n).bits)
#define nodes_clear(n) memset(&(n),0,sizeof(n))
static int compat_mode;
static unsigned char *user_begin; static size_t user_size;
static inline int in_compat_syscall(void) {return compat_mode;}
static bool access_ok(const void *p,size_t n) {
 uintptr_t a=(uintptr_t)p,b=(uintptr_t)user_begin;
 return a>=b && a-b<=user_size && n<=user_size-(a-b);
}
#define user_read_access_begin(p,n) access_ok(p,n)
#define user_read_access_end() do {} while(0)
#define unsafe_get_user(v,p,label) do {const compat_ulong_t *q=(p); if(!access_ok(q,sizeof(*q))) goto label; (v)=*q;} while(0)
#define get_user(v,p) (access_ok(p,sizeof(*(p)))?((v)=*(p),0):-EFAULT)
static size_t copy_from_user(void *d,const void *s,size_t n) {if(!access_ok(s,n)) return n; memcpy(d,s,n);return 0;}
''' + (function(compat,'long compat_get_bitmap(') if mode=='after' else '')+bitmap+get+r'''
int main(int argc,char **argv) {
 if(argc!=4) return 2;
 unsigned bits=atoi(argv[1]);compat_mode=atoi(argv[2]);int bound=atoi(argv[3]);
 if(bits<1 || bits>64) return 3;
 union {unsigned long w[4];uint32_t c[8];} input={0};
 unsigned long value=1UL|(1UL<<(bits-1));
 if(compat_mode) {input.c[0]=(uint32_t)value;input.c[1]=(uint32_t)(value>>32);}
 else input.w[0]=value;
 size_t required=compat_mode?((bits+31)/32)*4:8;
 user_begin=(unsigned char*)&input;user_size=bound==0?required:bound==1?16:required-1;
 nodemask_t result; int rc=get_nodes(&result,input.w,bits+1);
 printf("{\"rc\":%d,\"value\":%lu}\n",rc,rc?0:result.bits[0]);return 0;
}
'''

def perf(read,mode):
    src=read('tools/perf/util/parse-events.c')
    hdr=read('tools/perf/util/evsel_config.h')
    consumer=read('tools/perf/util/evsel.c')
    enum=hdr[hdr.index('enum evsel_term_type {'):hdr.index('};',hdr.index('enum evsel_term_type {'))+2]
    struct=function(hdr,'struct evsel_config_term {')+';'
    constructor=function(src,'static struct evsel_config_term *add_config_term(')
    write='new_term->val.val = val;'
    definition=src[src.rindex('static int get_config_terms('):]
    assert mode=='after' or write in function(definition,'static int get_config_terms(')
    consume='attr->write_backward = term->val.overwrite ? 1 : 0;'
    assert consume in consumer
    return H+r'''
typedef uint64_t u64; typedef uint32_t u32;
struct list_head {struct list_head *next,*prev;};
#define INIT_LIST_HEAD(p) do {(p)->next=(p);(p)->prev=(p);} while(0)
static void list_add_tail(struct list_head *n,struct list_head *h) {n->prev=h->prev;n->next=h;h->prev->next=n;h->prev=n;}
#define zalloc(n) calloc(1,n)
#define zfree(p) do {free(*(p));*(p)=NULL;} while(0)
'''+enum+struct+constructor+r'''
int main(int argc,char **argv) {
 if(argc!=3) return 2;
 int kind=atoi(argv[1]); u64 val=strtoull(argv[2],0,0);
 enum evsel_term_type types[]={EVSEL__CONFIG_TERM_OVERWRITE,EVSEL__CONFIG_TERM_INHERIT,
 EVSEL__CONFIG_TERM_TIME,EVSEL__CONFIG_TERM_MAX_STACK,EVSEL__CONFIG_TERM_AUX_SAMPLE_SIZE,
 EVSEL__CONFIG_TERM_PERIOD};
 struct list_head head;INIT_LIST_HEAD(&head);
''' + ('struct evsel_config_term *new_term=add_config_term(types[kind],&head,false,NULL,val);'
        if mode=='after' else 'struct evsel_config_term *new_term=add_config_term(types[kind],&head,false);\n'+write)+r'''
 if(!new_term) return 3;
 struct evsel_config_term *term=new_term;
 struct {unsigned write_backward;} storage={0},*attr=&storage;
''' + 'if(kind==0) { '+consume+' }'+ r'''
 unsigned long long got=0;
 switch(kind) {
 case 0:got=attr->write_backward;break;
 case 1:got=term->val.inherit;break;
 case 2:got=term->val.time;break;
 case 3:got=term->val.max_stack;break;
 case 4:got=term->val.aux_sample_size;break;
 case 5:got=term->val.period;break;
 }
 printf("{\"value\":%llu,\"linked\":%d,\"big_endian\":%d}\n",got,head.next==&term->list,
 __BYTE_ORDER__==__ORDER_BIG_ENDIAN__);free(term);return 0;
}
'''

def topology(read,mode):
    src=read('arch/s390/kernel/topology.c'); smp=read('arch/s390/kernel/smp.c')
    group=function(src,'static void cpu_group_map('); thread=function(src,'static void cpu_thread_map(')
    start=function(smp,'static void smp_start_secondary(')
    stop=function(smp,'int __cpu_disable(')
    candidates=['cpumask_set_cpu(cpu, &cpu_setup_mask);','update_cpu_masks();',
                'notify_cpu_starting(cpu);','set_cpu_online(cpu, true);']
    def projection(body,strings):
        for s in strings: assert body.count(s)<=1,s
        return sorted([s for s in strings if s in body],key=body.index)
    begin=projection(start,candidates)
    end=projection(stop,['set_cpu_online(smp_processor_id(), false);','set_cpu_online(cpu, false);',
                          'cpumask_clear_cpu(cpu, &cpu_setup_mask);','update_cpu_masks();'])
    # Controlled partial-repair counterexamples on the fixed source.
    if mode=='order_only':
        group=group.replace('!cpumask_test_cpu(cpu, &cpu_setup_mask)','!cpu_online(cpu)').replace('&cpu_setup_mask','cpu_online_mask')
        thread=thread.replace('&cpu_setup_mask','cpu_online_mask')
    if mode=='mask_only':
        begin.remove('update_cpu_masks();'); begin.append('update_cpu_masks();')
    return H+r'''
typedef unsigned cpumask_t;
static cpumask_t online=1,present=15,cpu_setup_mask=1;
#define cpu_online_mask (&online)
#define cpu_present_mask (&present)
#define cpumask_clear(p) (*(p)=0)
#define cpumask_set_cpu(c,p) (*(p)|=1U<<(c))
#define cpumask_clear_cpu(c,p) (*(p)&=~(1U<<(c)))
#define cpumask_test_cpu(c,p) (!!(*(p)&(1U<<(c))))
#define cpumask_copy(d,s) (*(d)=*(s))
#define cpumask_and(d,a,b) (*(d)=*(a)&*(b))
#define cpu_online(c) cpumask_test_cpu(c,&online)
#define cpu_present(c) cpumask_test_cpu(c,&present)
#define fallthrough __attribute__((fallthrough))
#define TOPOLOGY_MODE_HW 0
#define TOPOLOGY_MODE_PACKAGE 1
#define TOPOLOGY_MODE_SINGLE 2
static int topology_mode;static unsigned smp_cpu_mtid;
struct mask_info {cpumask_t mask;struct mask_info *next;};
static struct mask_info info={15,NULL};
static cpumask_t groups[4],threads[4];static unsigned target;
#define smp_processor_id() target
static void set_cpu_online(unsigned c,bool on) {if(on)online|=1U<<c;else online&=~(1U<<c);}
''' + group+thread+r'''
static void update_cpu_masks(void) {for(unsigned c=0;c<4;c++){cpu_group_map(&groups[c],&info,c);cpu_thread_map(&threads[c],c);}}
static void notify_cpu_starting(unsigned cpu) {
 printf("{\"event\":\"notify\",\"group\":%u,\"thread\":%u,\"online\":%u}\n",groups[cpu],threads[cpu],online);
}
static void start_cpu(unsigned cpu) {
'''+'\n'.join(begin)+r'''
}
static void stop_cpu(unsigned cpu) {(void)cpu;
'''+'\n'.join(end)+r'''
}
int main(int argc,char **argv) {
 if(argc!=4) return 2;
 topology_mode=atoi(argv[1]);smp_cpu_mtid=atoi(argv[2]);target=atoi(argv[3]);(void)cpu_setup_mask;
 update_cpu_masks();
 start_cpu(target);
 printf("{\"event\":\"online\",\"group\":%u,\"thread\":%u,\"online\":%u}\n",groups[target],threads[target],online);
 stop_cpu(target);
 printf("{\"event\":\"offline\",\"group\":%u,\"thread\":%u,\"online\":%u}\n",groups[target],threads[target],online);
 start_cpu(target);return 0;
}
'''

def fixtures(case,arch):
    if case=='numa':
        return [(f'bits{bits}-compat{compat}-bound{bound}',[bits,compat,bound],
                 {'rc':-14 if bound==2 else 0,'value':0 if bound==2 else 1|(1<<(bits-1))})
                for bits in (1,31,32,33,63,64) for compat in (0,1) for bound in (0,1,2)]
    if case=='perf':
        values=[(0,1),(0,1),(0,1),(0,127),(0,4294967295),(0,4294967297)]
        return [(f'field{kind}-{v}',[kind,v],{'value':v,'linked':1,'big_endian':int(arch=='s390x')})
                for kind,seq in enumerate(values) for v in seq]
    rows=[]
    for mode in range(3):
        for mtid in (1,3):
            for cpu in (1,2):
                ready=1|(1<<cpu)
                group=(1<<cpu) if mode==2 else ready
                thread=(ready & (((1<<(mtid+1))-1) << ((cpu//(mtid+1))*(mtid+1)))) if mode==0 else 1<<cpu
                notify=dict(event='notify',group=group,thread=thread,online=1)
                rows.append((f'mode{mode}-mtid{mtid}-cpu{cpu}',[mode,mtid,cpu],
                    [notify,dict(event='online',group=group,thread=thread,online=ready),
                     dict(event='offline',group=0,thread=0,online=1),notify]))
    return rows

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--linux-dir',type=Path,required=True)
    ap.add_argument('--outdir',type=Path,required=True);args=ap.parse_args()
    out=args.outdir.resolve();out.mkdir(parents=True,exist_ok=False)
    manifest={'sources':[],'tools':{},'scope':'historical source slices; s390x user emulation, no kernel boot'}
    summary={}
    for tool in ('gcc','s390x-linux-gnu-gcc','qemu-s390x'):
        manifest['tools'][tool]=subprocess.check_output([tool,'--version'],text=True).splitlines()[0]
    for case,builder in [('numa',numa),('perf',perf),('topology',topology)]:
        summary[case]={}
        modes=['before','after']+(['order_only','mask_only'] if case=='topology' else [])
        for mode in modes:
            folder=out/case/mode;folder.mkdir(parents=True)
            ref=REVS[case]+('^' if mode=='before' else '')
            revision=subprocess.check_output(['git','-C',str(args.linux_dir),'rev-parse',ref],text=True).strip()
            def read(path):
                data=subprocess.check_output(['git','-C',str(args.linux_dir),'show',revision+':'+path])
                p=folder/path.replace('/','_');p.write_bytes(data)
                manifest['sources'].append(dict(case=case,mode=mode,revision=revision,path=path,
                    artifact=str(p.relative_to(out)),sha256=hashlib.sha256(data).hexdigest()))
                return data.decode()
            c=folder/'harness.c';c.write_text(builder(read,mode)); summary[case][mode]={}
            for arch,compiler,prefix in [('x86_64','gcc',[]),('s390x','s390x-linux-gnu-gcc',['qemu-s390x'])]:
                exe=folder/arch
                command=[compiler,'-std=gnu11','-O2','-Wall','-Wextra','-Werror','-static',str(c),'-o',str(exe)]
                if case=='topology': command.insert(1,'-Wno-sign-compare')
                proc=subprocess.run(command,capture_output=True,text=True)
                (folder/(arch+'-build.log')).write_text(proc.stdout+proc.stderr)
                if proc.returncode: raise RuntimeError(str(folder/(arch+'-build.log')))
                rows=[]
                for name,inputs,want in fixtures(case,arch):
                    cmd=prefix+[str(exe),*map(str,inputs)]
                    proc=subprocess.run(cmd,capture_output=True,text=True,timeout=10,check=True)
                    actual=[json.loads(s) for s in proc.stdout.splitlines()]
                    if case!='topology': actual=actual[0]
                    rows.append(dict(name=name,command=cmd,expected=want,actual=actual,passed=actual==want))
                (folder/(arch+'-results.json')).write_text(json.dumps(rows,indent=2)+'\n')
                summary[case][mode][arch]={'count':len(rows),'passed':sum(r['passed'] for r in rows),
                    'failed':[r['name'] for r in rows if not r['passed']]}
    manifest['artifacts']={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
