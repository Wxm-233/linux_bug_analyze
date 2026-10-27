from pathlib import Path
import json,re,hashlib,subprocess
H=Path(__file__).resolve().parent;A=(H/'source/arch__arm64__include__asm__assembler.h').read_text();S=(H/'source/arch__arm64__mm__cache.S').read_text();manifest=[]
def macro(n):
 m=re.search(r'^\s*\.macro\s+'+n+r'(?:\s|,)',A,re.M);a=m.start();end=A.index('.endm',m.end())+len('.endm');t=A[a:end];manifest.append(dict(kind='macro',name=n,line=A[:a].count('\n')+1,sha256=hashlib.sha256(t.encode()).hexdigest()));return t
def body(n):
 marker='SYM_FUNC_START('+n+')';a=S.index(marker)+len(marker);b=S.index('SYM_FUNC_END('+n+')',a);t=S[a:b];manifest.append(dict(kind='assembly_body',name=n,line=S[:a].count('\n')+1,sha256=hashlib.sha256(t.encode()).hexdigest()));return f'\n.global {n}\n.type {n}, %function\n{n}:\n'+t+'\n'
shim=r'''
.text
.macro read_ctr reg
 adrp \reg, ctr_fixture
 ldr \reg, [\reg, :lo12:ctr_fixture]
.endm
.macro trace_op op, addr
 adrp x9, trace
 add x9, x9, :lo12:trace
 adrp x10, ntrace
 ldr x11, [x10, :lo12:ntrace]
 add x9, x9, x11, lsl #4
 mov x12, #\op
 str x12, [x9]
 str \addr, [x9, #8]
 add x11, x11, #1
 str x11, [x10, :lo12:ntrace]
.endm
/* Maintenance itself is replaced with a log. Branch/arithmetic stay AArch64. */
.macro dc op, addr
 .ifc \op, cvac
 trace_op 1, \addr
 .else
 .ifc \op, ivac
 trace_op 2, \addr
 .else
 .ifc \op, civac
 trace_op 3, \addr
 .else
 .error "unregistered cache op"
 .endif
 .endif
 .endif
.endm
.macro dsb domain
 trace_op 4, xzr
.endm
.macro _cond_uaccess_extable label, fixup
.endm
'''
macros='\n'.join(macro(n) for n in ['dcache_line_size','__dcache_op_workaround_clean_cache','dcache_by_myline_op','dcache_by_line_op'])
# Project the registered clean-cache alternative at build time; do not emulate
# Linux runtime alternative patching. Opening a GAS conditional in one macro
# and closing it in another is invalid (initial failed build preserved).
macros=macros.replace('alternative_if_not ARM64_WORKAROUND_CLEAN_CACHE','.if WORKAROUND == 0').replace('alternative_else','.else').replace('alternative_endif','.endif')
asm=shim+macros+body('__pi_dcache_inval_poc')+body('__pi_dcache_clean_poc')+'\n.global dcache_inval_poc\n.set dcache_inval_poc, __pi_dcache_inval_poc\n.global dcache_clean_poc\n.set dcache_clean_poc, __pi_dcache_clean_poc\n.section .note.GNU-stack,"",%progbits\n'
(H/'boundary.S').write_text(asm)
p=H.parent/'virtio_dma_chain_20261026/source/arch__arm64__mm__dma-mapping.c';c=p.read_text();functions=[]
for name in ['arch_sync_dma_for_device','arch_sync_dma_for_cpu']:
 m=re.search(r'^void '+name+r'\([^;{]*\)\s*\{',c,re.M);a=m.start();b=m.end();d=1
 while d:d+=(c[b]=='{')-(c[b]=='}');b+=1
 t=c[a:b];functions.append(t);manifest.append(dict(kind='C_body',name=name,line=c[:a].count('\n')+1,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),sha256=hashlib.sha256(t.encode()).hexdigest()))
head=r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
typedef uint64_t phys_addr_t;
enum dma_data_direction {DMA_TO_DEVICE=1,DMA_FROM_DEVICE=2};
uint64_t ctr_fixture,ntrace;uint64_t trace[256][2];
extern void dcache_clean_poc(unsigned long,unsigned long);
extern void dcache_inval_poc(unsigned long,unsigned long);
static void *phys_to_virt(phys_addr_t a){return (void*)(uintptr_t)a;}
'''
tail=r'''
int main(int argc,char**argv){assert(argc==7);int action=atoi(argv[1]);unsigned dmin=atoi(argv[2]),cwg=atoi(argv[3]);unsigned long start=strtoul(argv[4],0,0),size=strtoul(argv[5],0,0);int dir=atoi(argv[6]);assert(dmin>=4&&dmin<=5&&size>0&&size<1024);ctr_fixture=((uint64_t)dmin<<16)|((uint64_t)cwg<<24);if(action==0)arch_sync_dma_for_device(start,size,dir);else arch_sync_dma_for_cpu(start,size,dir);for(uint64_t i=0;i<ntrace;i++)printf("%llu %llu\n",(unsigned long long)trace[i][0],(unsigned long long)trace[i][1]);return 0;}
'''
(H/'boundary.c').write_text(head+'\n'.join(functions)+tail)
(H/'functions.json').write_text(json.dumps(dict(entries=manifest,scope='original C wrappers, assembly boundary bodies and line-loop macros; read_ctr/DC/DSB/alternative patching are fixtures; QEMU user-mode executes arithmetic/branches, no hardware cache operation'),indent=2))
builds=[];rows=[]
for workaround in [0,1]:
 exe=H/f'boundary_{workaround}.bin';q=subprocess.run(['aarch64-linux-gnu-gcc','-static','-O0','-Wall','-Wextra','-Werror','-Wno-unused-parameter',f'-DWORKAROUND={workaround}',str(H/'boundary.c'),str(H/'boundary.S'),'-o',str(exe)],capture_output=True,text=True);builds.append(dict(workaround=workaround,code=q.returncode,stderr=q.stderr));(H/'builds.json').write_text(json.dumps(builds,indent=2))
 if q.returncode:raise RuntimeError(q.stderr)
 dis=subprocess.check_output(['aarch64-linux-gnu-objdump','-d',str(exe)],text=True)
 # Full static libc disassembly is not a cache instruction witness; save only our bodies.
 parts=[]
 for n in ['__pi_dcache_inval_poc','__pi_dcache_clean_poc']:
  m=re.search(r'^\w+ <'+n+r'>:\n(.*?)(?=\n\n)',dis,re.M|re.S)
  if m:parts.append(m.group(0))
 (H/f'disassembly_{workaround}.txt').write_text('\n\n'.join(parts))
 for dmin in [4,5]:
  line=4<<dmin
  for cwg in [4,5]:
   for action,dir in [(0,2),(1,2),(1,1)]:
    for offset,size in [(0,8),(8,8),(line-8,8),(line-4,8),(0,line),(8,line*2),(line-8,line+16)]:
     start=0x10000+offset;args=[str(action),str(dmin),str(cwg),str(start),str(size),str(dir)]
     q=subprocess.run(['qemu-aarch64',str(exe),*args],capture_output=True,text=True,timeout=15)
     rows.append(dict(workaround=workaround,dmin=dmin,cwg=cwg,line=line,action=action,direction=dir,start=start,size=size,code=q.returncode,stdout=q.stdout,stderr=q.stderr))
(H/'results.json').write_text(json.dumps(rows,indent=2))
if any(r['code'] for r in rows):raise RuntimeError('execution failure')
print(f'2 instrumented AArch64 builds /{len(rows)} QEMU user executions complete')
