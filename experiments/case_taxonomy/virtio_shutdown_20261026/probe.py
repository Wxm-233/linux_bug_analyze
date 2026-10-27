from pathlib import Path
import re,json,hashlib,subprocess
H=Path(__file__).resolve().parent;manifest=[]
def fun(p,n):
 s=p.read_text();m=re.search(r'^(?:static (?:inline\s*)?)?void '+n+r'\([^;{]*\)\s*\{',s,re.M)
 if not m:raise ValueError(n)
 a=m.start();b=m.end();d=1
 while d:d+=(s[b]=='{')-(s[b]=='}');b+=1
 t=s[a:b];manifest.append(dict(name=n,path=str(p.relative_to(H.parent)),line=s[:a].count('\n')+1,sha256=hashlib.sha256(t.encode()).hexdigest()));return t
head=r'''
#include <stdio.h>
#include <stdbool.h>
#include <stdlib.h>
#include <assert.h>
struct virtio_device;
struct config {void (*reset)(struct virtio_device*);void (*synchronize_cbs)(struct virtio_device*);};
struct virtio_device {struct config *config;};
struct pci_dev {int irq;};
struct virtio_pci_modern_device {int unused;};
struct virtio_pci_device {struct virtio_device vdev;struct virtio_pci_modern_device mdev;bool intx_enabled;int msix_vectors;struct pci_dev *pci_dev;};
static int delay,reads,irq_count,rcus,breaks,cleanups;
static struct virtio_pci_device *to_vp_device(struct virtio_device*d){return (struct virtio_pci_device*)d;}
static void synchronize_irq(int i){irq_count++;printf("SYNC_IRQ %d\n",i);}
static int pci_irq_vector(struct pci_dev*p,int i){(void)p;return 100+i;}
static void synchronize_rcu(void){rcus++;puts("SYNC_RCU");}
static void __attribute__((unused)) virtio_break_device(struct virtio_device*d){(void)d;breaks++;puts("BREAK");}
static void vp_modern_set_status(struct virtio_pci_modern_device*d,int s){(void)d;assert(s==0);puts("STATUS_WRITE_ZERO");}
static int vp_modern_get_status(struct virtio_pci_modern_device*d){(void)d;int s=reads++<delay;printf("STATUS_READ %d\n",s);return s;}
static void msleep(int n){assert(n==1);puts("SLEEP");}
static void vp_modern_avq_cleanup(struct virtio_device*d){(void)d;cleanups++;puts("AVQ_CLEANUP");}
'''
tail=r'''
int main(int argc,char**argv){assert(argc==5);int cb=atoi(argv[1]),intx=atoi(argv[2]),vectors=atoi(argv[3]);delay=atoi(argv[4]);struct config c={.reset=vp_reset,.synchronize_cbs=cb?vp_synchronize_vectors:NULL};struct pci_dev p={.irq=17};struct virtio_pci_device d={.vdev={&c},.intx_enabled=intx,.msix_vectors=vectors,.pci_dev=&p};virtio_reset_device(&d.vdev);int hard=0;
#ifdef CONFIG_VIRTIO_HARDEN_NOTIFICATION
hard=1;
#endif
assert(breaks==hard&&rcus==hard*!cb&&irq_count==(intx+vectors)*(1+hard*cb)&&reads==delay+1&&cleanups==1);puts("RESET_RETURN");}
'''
spec=[(H/'source/drivers__virtio__virtio_pci_common.c','vp_synchronize_vectors'),(H.parent/'virtio_dma_chain_20261026/source/include__linux__virtio_config.h','virtio_synchronize_cbs'),(H/'source/drivers__virtio__virtio_pci_modern.c','vp_reset'),(H/'source/drivers__virtio__virtio.c','virtio_reset_device')]
(H/'reset.c').write_text(head+'\n'.join(fun(p,n) for p,n in spec)+tail)
(H/'functions.json').write_text(json.dumps(manifest,indent=2))
builds=[];rows=[]
for hard in [0,1]:
 exe=H/f'reset_{hard}.bin';cmd=['cc','-std=gnu11','-Wall','-Wextra','-Werror']+(['-DCONFIG_VIRTIO_HARDEN_NOTIFICATION'] if hard else [])+[str(H/'reset.c'),'-o',str(exe)]
 p=subprocess.run(cmd,capture_output=True,text=True);builds.append(dict(hard=hard,code=p.returncode,stderr=p.stderr));(H/'builds.json').write_text(json.dumps(builds,indent=2))
 if p.returncode:raise RuntimeError(p.stderr)
 for cb in [0,1]:
  for intx in [0,1]:
   for vectors in [0,2]:
    for delay in [0,2]:
     p=subprocess.run([str(exe),str(cb),str(intx),str(vectors),str(delay)],capture_output=True,text=True);rows.append(dict(hard=hard,callback=cb,intx=intx,vectors=vectors,delay=delay,code=p.returncode,stdout=p.stdout,stderr=p.stderr))
(H/'results.json').write_text(json.dumps(rows,indent=2))
if any(r['code'] for r in rows):raise RuntimeError('execution failure')
print('2 builds,32 reset branch executions passed; IRQ/status/RCU are doubles')
