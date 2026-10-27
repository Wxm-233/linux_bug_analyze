from pathlib import Path
import re,subprocess,json,hashlib
H=Path(__file__).resolve().parent;s=(H/'dma-map-ops.h').read_text();parts=[]
for name in ['dma_kmalloc_safe','dma_kmalloc_size_aligned','dma_kmalloc_needs_bounce']:
 m=re.search(r'^static inline bool '+name+r'\(',s,re.M);a=m.start();b=s.index('{',a)+1;d=1
 while d:d+=(s[b]=='{')-(s[b]=='}');b+=1
 parts.append(s[a:b])
head=r'''
#include <stdbool.h>
#include <stdlib.h>
#include <stdio.h>
#include <assert.h>
struct device {int coherent;};enum dma_data_direction {DMA_TO_DEVICE=1,DMA_FROM_DEVICE=2};
#define IS_ENABLED(x) (x)
#define ARCH_DMA_MINALIGN 128
#define IS_ALIGNED(x,a) (((x)&((a)-1))==0)
static bool dev_is_dma_coherent(struct device*d){return d->coherent;}
/* Deliberately registered allocator/cache assumptions, not target ABI facts. */
static size_t kmalloc_size_roundup(size_t n){assert(n==8||n==64||n==512);return n;}
static size_t dma_get_cache_alignment(void){return 64;}
'''
tail=r'''
int main(int argc,char**argv){assert(argc==4);struct device d={atoi(argv[1])};int dir=atoi(argv[2]);size_t size=strtoul(argv[3],0,0);bool b=dma_kmalloc_needs_bounce(&d,size,dir);assert(b==(CONFIG_DMA_BOUNCE_UNALIGNED_KMALLOC&&!d.coherent&&dir==DMA_FROM_DEVICE&&size==8));printf("BOUNCE %d\n",b);return 0;}
'''
(H/'bounce_gate.c').write_text(head+'\n'.join(parts)+tail);builds=[];rows=[]
for config in [0,1]:
 exe=H/f'bounce_gate_{config}.bin';p=subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',f'-DCONFIG_DMA_BOUNCE_UNALIGNED_KMALLOC={config}',str(H/'bounce_gate.c'),'-o',str(exe)],capture_output=True,text=True);assert p.returncode==0,p.stderr;builds.append(dict(config=config,code=p.returncode,stderr=p.stderr))
 for coherent in [0,1]:
  for direction in [1,2]:
   for size in [8,64,512]:
    p=subprocess.run([str(exe),str(coherent),str(direction),str(size)],capture_output=True,text=True);assert p.returncode==0,p.stderr;rows.append(dict(config=config,coherent=coherent,direction=direction,size=size,stdout=p.stdout))
(H/'bounce_gate_results.json').write_text(json.dumps(dict(builds=builds,cases=rows,source_sha256=hashlib.sha256((H/'dma-map-ops.h').read_bytes()).hexdigest(),scope='configured predicate experiment; roundup and cache granule doubles; no real allocator/platform certification'),indent=2));print('2 predicate builds / 24 cases passed')
