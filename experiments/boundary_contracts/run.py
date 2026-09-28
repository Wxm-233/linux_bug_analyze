"""Run three fixed historical source-slice contracts; no kernel or model calls."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from experiments.iommu_contracts.run import function

COMMITS = {'btrfs': '6f93e834fa7c5faa0372e46828b4b2a966ac61d7',
           'fbnic': '4bd451f4c2851eee7b6e17bb6fd6c9caaadbdc18',
           'parisc': 'd97180ad68bdb7ee10f327205a649bc2f558741d'}
HEADER = '#include <stdint.h>\n#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n'


def btrfs(read):
    disk = read('fs/btrfs/disk-io.c')
    parser = read('fs/btrfs/super.c')
    body = function(disk, 'int __cold open_ctree(')
    # Data-dependent projection only: real assignments and real call order.
    initial = 'fs_info->sectorsize = 4096;'
    assert function(disk, 'void btrfs_init_fs_info(').count(initial) == 1
    statements = ['sectorsize = btrfs_super_sectorsize(disk_super);',
                  'fs_info->sectorsize = sectorsize;',
                  'ret = btrfs_parse_options(fs_info, options, sb->s_flags);']
    for s in statements:
        assert body.count(s) == 1, s
    ordered = [initial] + sorted(statements, key=body.index)
    branch = parser[parser.index('\t\tcase Opt_max_inline:'):parser.index('\t\tcase Opt_acl:')]
    clamp = function(branch, 'if (info->max_inline)')
    return HEADER + r'''
typedef uint64_t u64;
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
struct info { u64 sectorsize, max_inline; };
static int btrfs_parse_options(struct info *info, u64 options, int flags) {
 (void)flags; info->max_inline=options;
''' + clamp + r'''
 return 0;
}
static u64 btrfs_super_sectorsize(u64 value) { return value; }
int main(int argc,char **argv) {
 if(argc!=3) return 2;
 struct info state={0}, *fs_info=&state;
 struct {int s_flags;} super={0}, *sb=&super;
 u64 disk_super=strtoull(argv[1],0,0), options=strtoull(argv[2],0,0), sectorsize=0;
 int ret;
''' + '\n'.join(ordered) + r'''
 printf("{\"value\":%llu,\"sectorsize\":%llu,\"rc\":%d}\n",
 (unsigned long long)state.max_inline,(unsigned long long)state.sectorsize,ret);
 return 0;
}
'''


def fbnic(read):
    src = read('drivers/net/ethernet/meta/fbnic/fbnic_txrx.c')
    hdr = read('drivers/net/ethernet/meta/fbnic/fbnic_csr.h')
    macros = hdr[hdr.index('#define FBNIC_BD_DESC_ADDR_MASK'):hdr.index('/* Rx Completion Queue Descriptors */')]
    fn = function(src, 'static void fbnic_bd_prep(')
    return HEADER + r'''
typedef uint64_t u64, __le64, dma_addr_t, netmem_ref;
typedef uint16_t u16;
static u64 page_size;
#define PAGE_SIZE page_size
#define DESC_GENMASK(h,l) ((~0ULL >> (63-(h))) & (~0ULL << (l)))
#define FIELD_PREP(mask,val) (((u64)(val)<<__builtin_ctzll(mask)) & (mask))
#define cpu_to_le64(x) (x)
static dma_addr_t page_pool_get_dma_addr_netmem(netmem_ref x) {return x;}
struct fbnic_ring { __le64 desc[128]; };
''' + macros + fn + r'''
int main(int argc,char **argv) {
 if(argc!=4) return 2;
 page_size=strtoull(argv[1],0,0);
 unsigned id=strtoul(argv[2],0,0); u64 address=strtoull(argv[3],0,0);
 if(page_size<4096 || page_size>65536 || id>3) return 3;
 struct fbnic_ring ring;
 for(int i=0;i<128;i++) ring.desc[i]=0xdeadbeefdeadbeefULL;
 fbnic_bd_prep(&ring,id,address);
 printf("{\"descriptors\":[");
 for(int i=0;i<128;i++) printf("%s%llu",i?",":"",(unsigned long long)ring.desc[i]);
 printf("]}\n"); return 0;
}
'''


def parisc(read):
    setup = function(read('arch/parisc/kernel/setup.c'), 'void __init setup_arch(')
    fn = function(read('arch/parisc/kernel/time.c'), 'static int __init init_cr16_clocksource(')
    # setup_arch itself is not executed: project its only scheduler stability effect.
    calls = re.findall(r'\bclear_sched_clock_stable\(\);', setup)
    assert len(calls) <= 1
    return HEADER + r'''
#define __init
#define CLOCK_SOURCE_IS_CONTINUOUS 1
#define CLOCK_SOURCE_UNSTABLE 2
static int cpu_count,running_on_qemu,cleared,registered;
static struct {unsigned long cpu_loc;} cpu_data[8];
#define per_cpu(v,c) (v[c])
#define for_each_online_cpu(c) for((c)=0;(c)<cpu_count;(c)++)
static int num_online_cpus(void) {return cpu_count;}
static void clear_sched_clock_stable(void) {cleared++;}
static struct {unsigned mem_10msec;} page0={100};
#define PAGE0 (&page0)
struct clocksource {const char *name; int flags,rating;};
static struct clocksource clocksource_cr16={"cr16",CLOCK_SOURCE_IS_CONTINUOUS,300};
static void clocksource_register_hz(struct clocksource *p,unsigned hz) {(void)p;(void)hz;registered++;}
''' + fn + r'''
int main(int argc,char **argv) {
 if(argc<3 || argc>10) return 2;
 running_on_qemu=atoi(argv[1]); cpu_count=argc-2;
 for(int i=0;i<cpu_count;i++) cpu_data[i].cpu_loc=strtoul(argv[i+2],0,0);
''' + '\n'.join(calls) + r'''
 int rc=init_cr16_clocksource();
 printf("{\"cleared\":%d,\"flags\":%d,\"rating\":%d,\"registered\":%d,\"rc\":%d}\n",
 cleared,clocksource_cr16.flags,clocksource_cr16.rating,registered,rc);
 return 0;
}
'''


def fixtures(case):
    if case == 'btrfs':
        # Explicit values independent of the extracted clamp expression.
        requests = [0,1,4095,4096,4097,16384,65535,65536,131072]
        expected = {4096:[0,1,4095,4096,4096,4096,4096,4096,4096],
                    65536:[0,1,4095,4096,4097,16384,65535,65536,65536]}
        return [(f'{size}-{value}', [size,value], {'value':want,'sectorsize':size,'rc':0})
                for size, values in expected.items() for value,want in zip(requests,values)]
    if case == 'fbnic':
        rows=[]
        for size in (4096,16384,65536):
            for ident in (0,1,3):
                for base in (0x100000,0x400000):
                    n=size//4096
                    arr=[0xdeadbeefdeadbeef]*128
                    for i in range(n):
                        # Contract: successive 4K physical chunks and unique fragment IDs.
                        arr[ident*n+i]=(base+i*4096)|((ident*n+i)<<48)
                    rows.append((f'{size}-{ident}-{base}',[size,ident,base],{'descriptors':arr}))
        return rows
    # Expected topology policy, not an assertion of physical clock synchronization.
    topology=[('single',[0],False),('same_socket',[7,7],False),
              ('four_same',[7,7,7,7],False),('different',[7,8],True),
              ('unknown',[0,0],True),('part_unknown',[7,0],True),
              ('late_different',[7,7,8],True)]
    return [(name+('-guest' if guest else '-native'),[guest,*loc],
             dict(cleared=int(unstable and not guest), flags=2 if unstable and not guest else 1,
                  rating=0 if unstable and not guest else 300,registered=1,rc=0))
            for guest in (0,1) for name,loc,unstable in topology]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--linux-dir',type=Path,required=True)
    ap.add_argument('--outdir',type=Path,required=True)
    args=ap.parse_args(); out=args.outdir.resolve(); out.mkdir(parents=True,exist_ok=False)
    manifest={'method':'historical C source slices with explicit test doubles, not kernel/hardware execution',
              'compiler':subprocess.check_output(['gcc','--version'],text=True).splitlines()[0], 'sources':[]}
    summary={}
    for case,builder in [('btrfs',btrfs),('fbnic',fbnic),('parisc',parisc)]:
        matrix=fixtures(case)
        (out/(case+'-fixtures.json')).write_text(json.dumps(matrix,indent=2)+'\n')
        summary[case]={}
        for mode in ('before','after'):
            folder=out/case/mode; folder.mkdir(parents=True)
            ref=COMMITS[case]+('^' if mode=='before' else '')
            revision=subprocess.check_output(['git','-C',str(args.linux_dir),'rev-parse',ref],text=True).strip()
            def read(path):
                data=subprocess.check_output(['git','-C',str(args.linux_dir),'show',revision+':'+path])
                dest=folder/path.replace('/','_'); dest.write_bytes(data)
                manifest['sources'].append(dict(case=case,mode=mode,revision=revision,path=path,
                    artifact=str(dest.relative_to(out)),sha256=hashlib.sha256(data).hexdigest()))
                return data.decode()
            source=builder(read); c=folder/'harness.c'; c.write_text(source)
            exe=folder/'harness'
            build=subprocess.run(['gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror',str(c),'-o',str(exe)],capture_output=True,text=True)
            (folder/'build.log').write_text(build.stdout+build.stderr)
            if build.returncode: raise RuntimeError(str(folder/'build.log'))
            rows=[]
            for name,inputs,want in matrix:
                proc=subprocess.run([str(exe),*map(str,inputs)],capture_output=True,text=True,timeout=5,check=True)
                actual=json.loads(proc.stdout)
                rows.append(dict(name=name,inputs=inputs,expected=want,actual=actual,passed=actual==want))
            (folder/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
            summary[case][mode]={'scenarios':len(rows),'passed':sum(r['passed'] for r in rows),
                'failed':[r['name'] for r in rows if not r['passed']]}
    manifest['artifacts']={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in out.rglob('*') if p.is_file()}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    # Exact expected counterexamples: old versions must fail, new versions must pass.
    expected_counts={'btrfs':5,'fbnic':12,'parisc':10}
    for case,n in expected_counts.items():
        assert len(summary[case]['before']['failed'])==n,summary[case]
        assert not summary[case]['after']['failed'],summary[case]
    (out/'VERIFIED').write_text('Exact expected old failures and all new passes checked.\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__': main()
