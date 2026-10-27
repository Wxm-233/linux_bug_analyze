from pathlib import Path
import re,json,subprocess,hashlib
H=Path(__file__).resolve().parent;src=H/'source/drivers__virtio__virtio_ring.c';s=src.read_text();manifest=[]
def fun(n):
 m=re.search(r'^(?:static )?(?:bool|int|unsigned int|dma_addr_t|void|struct device \*)\s*'+n+r'\(',s,re.M);assert m,n
 a=m.start();b=s.index('{',a)+1;d=1
 while d:d+=(s[b]=='{')-(s[b]=='}');b+=1
 t=s[a:b];manifest.append(dict(name=n,line=s[:a].count('\n')+1,sha256=hashlib.sha256(t.encode()).hexdigest()));return t
head=r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <errno.h>
#include <assert.h>
typedef uint64_t dma_addr_t;typedef uint32_t u32;typedef uint16_t u16;
enum dma_data_direction {DMA_TO_DEVICE=1,DMA_FROM_DEVICE=2};
struct device {int id;};struct page {int id;};union virtio_map {struct device*dma_dev;};
struct map_ops {dma_addr_t(*map_page)(union virtio_map,struct page*,unsigned long,size_t,enum dma_data_direction,unsigned long);void(*unmap_page)(union virtio_map,dma_addr_t,size_t,enum dma_data_direction,unsigned long);int(*mapping_error)(union virtio_map,dma_addr_t);};
struct virtio_device {struct map_ops *map;int quirk;};struct virtqueue {struct virtio_device*vdev;};
struct vring_virtqueue {struct virtqueue vq;bool use_map_api;union virtio_map map;};
struct scatterlist {unsigned length,offset,dma_len;dma_addr_t phys,dma;struct page*page;};
struct vring_desc_extra {u16 flags;dma_addr_t addr;u32 len,next;};
#define DMA_MAPPING_ERROR (~0ULL)
#define VRING_DESC_F_WRITE 2
#define VRING_DESC_F_INDIRECT 4
#define sg_phys(s) ((s)->phys)
#define sg_page(s) ((s)->page)
#define sg_dma_address(s) ((s)->dma)
#define sg_dma_len(s) ((s)->dma_len)
#define to_vvq(v) ((struct vring_virtqueue*)(v))
static int xen,fail,custom_maps,dma_maps,custom_unmaps,dma_unmaps,kmsan;
static bool xen_domain(void){return xen;}
static bool virtio_has_dma_quirk(const struct virtio_device*v){return v->quirk;}
static void kmsan_handle_dma(dma_addr_t a,size_t n,enum dma_data_direction d){assert(a==0x10080&&n==8&&d==DMA_FROM_DEVICE);kmsan++;}
static dma_addr_t dma_map_page_attrs(struct device*d,struct page*p,unsigned long o,size_t n,enum dma_data_direction dir,unsigned long attrs){assert(d->id==7&&p->id==9&&o==128&&n==8&&dir==DMA_FROM_DEVICE&&!attrs);dma_maps++;return fail?DMA_MAPPING_ERROR:0x20080;}
static int dma_mapping_error(struct device*d,dma_addr_t a){(void)d;return a==DMA_MAPPING_ERROR;}
static void dma_unmap_page_attrs(struct device*d,dma_addr_t a,size_t n,enum dma_data_direction dir,unsigned long attrs){assert(d->id==7&&a==0x20080&&n==8&&dir==DMA_FROM_DEVICE&&!attrs);dma_unmaps++;}
static dma_addr_t custom_map(union virtio_map m,struct page*p,unsigned long o,size_t n,enum dma_data_direction d,unsigned long attrs){assert(m.dma_dev->id==7&&p->id==9&&o==128&&n==8&&d==DMA_FROM_DEVICE&&!attrs);custom_maps++;return fail?DMA_MAPPING_ERROR:0x30080;}
static int custom_error(union virtio_map m,dma_addr_t a){(void)m;return a==DMA_MAPPING_ERROR;}
static void custom_unmap(union virtio_map m,dma_addr_t a,size_t n,enum dma_data_direction d,unsigned long attrs){assert(m.dma_dev->id==7&&a==0x30080&&n==8&&d==DMA_FROM_DEVICE&&!attrs);custom_unmaps++;}
'''
names=['vring_use_map_api','vring_need_unmap_buffer','vring_dma_dev','vring_mapping_error','virtqueue_map_page_attrs','virtqueue_unmap_page_attrs','vring_map_one_sg','vring_unmap_one_split']
tail=r'''
int main(int argc,char**argv){assert(argc==2);int bits=atoi(argv[1]);int quirk=bits&1;xen=(bits>>1)&1;int custom=(bits>>2)&1,premapped=(bits>>3)&1;fail=(bits>>4)&1;
struct device dev={7};struct page page={9};struct map_ops ops={custom_map,custom_unmap,custom_error};struct virtio_device vd={custom?&ops:NULL,quirk};struct vring_virtqueue vq={.vq={&vd},.map={&dev}};vq.use_map_api=vring_use_map_api(&vd);struct scatterlist sg={.length=8,.offset=128,.dma_len=8,.phys=0x10080,.dma=0x40080,.page=&page};dma_addr_t addr;u32 len;
int ret=vring_map_one_sg(&vq,&sg,DMA_FROM_DEVICE,&addr,&len,premapped,0);assert(len==8);
if(!ret){struct vring_desc_extra ex={.flags=VRING_DESC_F_WRITE,.addr=premapped?DMA_MAPPING_ERROR:addr,.len=len,.next=17};assert(vring_unmap_one_split(&vq,&ex)==17);}
bool mapped=!premapped&&vq.use_map_api;assert(vq.use_map_api==(!quirk||xen));assert(ret==(mapped&&fail?-ENOMEM:0));assert(dma_maps==(mapped&&!custom)&&custom_maps==(mapped&&custom));assert(dma_unmaps==(mapped&&!custom&&!fail)&&custom_unmaps==(mapped&&custom&&!fail));assert(kmsan==(!premapped&&!vq.use_map_api));
printf("RESULT %d %d %llu %u %d %d %d %d %d\n",ret,vq.use_map_api,(unsigned long long)addr,len,dma_maps,custom_maps,dma_unmaps,custom_unmaps,kmsan);return 0;}
'''
(H/'mapping.c').write_text(head+'\n'.join(fun(n) for n in names)+tail)
(H/'function_manifest.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),functions=manifest,boundary='type/backend/feature doubles; no descriptor publication or actual DMA; premapped is control not virtinput path'),indent=2))
exe=H/'mapping.bin';q=subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(H/'mapping.c'),'-o',str(exe)],capture_output=True,text=True);(H/'build.json').write_text(json.dumps(dict(code=q.returncode,stderr=q.stderr),indent=2));assert q.returncode==0,q.stderr
rows=[]
for bits in range(32):
 q=subprocess.run([str(exe),str(bits)],capture_output=True,text=True);rows.append(dict(bits=bits,code=q.returncode,stdout=q.stdout,stderr=q.stderr));assert q.returncode==0,rows[-1]
(H/'mapping_results.json').write_text(json.dumps(rows,indent=2));print('1 build / 32 original routing+map/unmap cases passed')
