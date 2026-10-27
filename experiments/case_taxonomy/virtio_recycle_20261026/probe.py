from pathlib import Path
import re,json,hashlib,subprocess
H=Path(__file__).resolve().parent
S=H.parent/'virtio_dma_chain_20261026/source'
manifest=[]
def fun(file,name):
 s=(S/file).read_text();m=re.search(r'^static [^;{]*?\b'+name+r'\([^;{]*?\)\s*\{',s,re.M)
 if not m: raise ValueError(name)
 a=m.start();b=m.end();d=1
 while d:d+=(s[b]=='{')-(s[b]=='}');b+=1
 t=s[a:b];manifest.append(dict(file=file,name=name,line=s[:a].count('\n')+1,sha256=hashlib.sha256(t.encode()).hexdigest(),source_sha256=hashlib.sha256((S/file).read_bytes()).hexdigest()));return t
head=r'''
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <assert.h>
typedef uint16_t u16;typedef uint16_t __virtio16;typedef uint32_t u32;
#define VRING_DESC_F_NEXT 1
#define VRING_DESC_F_WRITE 2
#define VRING_DESC_F_INDIRECT 4
#define VRING_AVAIL_F_NO_INTERRUPT 1
#define DMA_MAPPING_ERROR (~0ULL)
#define DMA_FROM_DEVICE 2
#define DMA_TO_DEVICE 1
#define GFP_ATOMIC 0
#define unlikely(x) (x)
#define cpu_to_virtio16(d,x) (x)
#define virtio16_to_cpu(d,x) (x)
#define virtio32_to_cpu(d,x) (x)
#define le16_to_cpu(x) (x)
#define le32_to_cpu(x) (x)
#define START_USE(x) ((void)0)
#define END_USE(x) ((void)0)
#define LAST_ADD_TIME_INVALID(x) ((void)0)
#define pr_debug(...) ((void)0)
#define BAD_RING(v,...) do{(v)->broken=true;puts("BAD_RING");}while(0)
#define virtio_rmb(x) puts("RMB")
#define virtio_store_mb(b,p,x) do{*(p)=(x);puts("EVENT_STORE");}while(0)
#define vring_used_event(v) ((v)->event)
static int locked;
#define spin_lock_irqsave(p,f) do{(void)(p);(f)=0;assert(!locked);locked=1;puts("LOCK");}while(0)
#define spin_unlock_irqrestore(p,f) do{(void)(p);(void)(f);assert(locked);locked=0;puts("UNLOCK");}while(0)
struct virtio_device {void *priv;};
struct virtqueue {struct virtio_device *vdev;unsigned num_free;};
struct vring_desc_extra {uint64_t addr;u32 len;u16 flags,next;};
struct vring_desc {u16 flags;};
struct state {void *data;struct vring_desc *indir_desc;};
struct used {u16 idx;struct {u32 id,len;}ring[4];};
struct vring {unsigned num;struct used *used;struct vring_desc desc[4];u16 event;};
struct vring_virtqueue {struct virtqueue vq;bool use_map_api,indirect,broken,weak_barriers;u16 last_used_idx,free_head;struct {struct vring vring;struct state desc_state[4];struct vring_desc_extra desc_extra[4];u16 avail_flags_shadow;}split;};
struct virtio_input_event {u16 type,code;u32 value;};
struct virtio_input {struct virtqueue *evt;void *idev;int lock;bool ready;struct virtio_input_event evts[2];};
struct scatterlist {void *p;unsigned len;};
static int mode,unmaps,reads,adds,kicks;static bool reclaimed[2];static struct virtio_input *current;
static void detach_indirect_split(struct vring_virtqueue*v,unsigned h){(void)v;(void)h;abort();}
static void virtqueue_unmap_page_attrs(const struct virtqueue*q,uint64_t addr,unsigned len,int dir,unsigned attrs){(void)q;assert(addr>=100&&addr<=101&&len==8&&dir==DMA_FROM_DEVICE&&attrs==0);int i=addr-100;reclaimed[i]=true;unmaps++;printf("UNMAP %d\n",i);}
'''
ring='drivers__virtio__virtio_ring.c';driver='drivers__virtio__virtio_input.c'
middle=r'''
static void *virtqueue_get_buf(struct virtqueue*q,unsigned *len){void*p=virtqueue_get_buf_ctx_split((struct vring_virtqueue*)q,len,NULL);if(p){int i=(struct virtio_input_event*)p-current->evts;reclaimed[i]=true;printf("TOKEN %d %u\n",i,*len);}else puts("NO_TOKEN");return p;}
static void input_event(void*d,unsigned type,unsigned code,unsigned value){(void)d;assert(!locked&&type==1&&code<2&&value==1000+code&&reclaimed[code]);printf("CPU_READ %u OTHER_RECLAIMED %d\n",code,reclaimed[1-code]);reads++;if(mode==8){current->ready=false;puts("READY_FALSE_IN_CALLBACK");}}
static void sg_init_one(struct scatterlist*s,void*p,unsigned n){s->p=p;s->len=n;}
static int virtqueue_add_inbuf(struct virtqueue*q,struct scatterlist*s,unsigned n,void*p,int gfp){(void)q;(void)gfp;assert(locked&&n==1&&s->p==p&&s->len==8);int i=(struct virtio_input_event*)p-current->evts;int ret=mode==1?-28:mode==2?-12:0;adds++;printf("ADD %d %d READY %d\n",i,ret,current->ready);if(!ret)reclaimed[i]=false;return ret;}
static void virtqueue_kick(struct virtqueue*q){(void)q;assert(locked);kicks++;puts("KICK");}
'''
tail=r'''
int main(int argc,char**argv){assert(argc==4);mode=atoi(argv[1]);int map=atoi(argv[2]);unsigned len=atoi(argv[3]);struct vring_virtqueue v={0};struct virtio_input vi={0};struct virtio_device dev={.priv=&vi};struct used used={.idx=2,.ring={{0,len},{1,len}}};v.vq.vdev=&dev;v.use_map_api=map;v.split.vring.num=4;v.split.vring.used=&used;vi.evt=&v.vq;vi.ready=mode!=7;current=&vi;for(int i=0;i<2;i++){vi.evts[i]=(struct virtio_input_event){1,i,1000+i};v.split.desc_state[i].data=&vi.evts[i];v.split.desc_extra[i]=(struct vring_desc_extra){100+i,8,VRING_DESC_F_WRITE,0};}if(mode==3)v.broken=true;if(mode==4)used.idx=0;if(mode==5)used.ring[0].id=4;if(mode==6)v.split.desc_state[0].data=NULL;virtinput_recv_events(&v.vq);int consume=mode<=2||mode==8;assert(reads==2*consume&&adds==reads&&unmaps==reads*map&&kicks==(mode!=7)&&!locked&&v.last_used_idx==reads&&v.vq.num_free==(unsigned)reads);printf("FINAL reads=%d adds=%d unmaps=%d kicks=%d ready=%d\n",reads,adds,unmaps,kicks,vi.ready);}
'''
names=['vring_need_unmap_buffer','vring_unmap_one_split','detach_buf_split_in_order','detach_buf_split','virtqueue_poll_split','more_used_split','virtqueue_get_buf_ctx_split']
code=head+'\n'.join(fun(ring,n) for n in names)+middle+'\n'.join(fun(driver,n) for n in ['virtinput_queue_evtbuf','virtinput_recv_events'])+tail
(H/'recycle.c').write_text(code)
(H/'functions.json').write_text(json.dumps({'functions':manifest,'scope':'split non-in-order single direct descriptor; get wrapper, add, DMA callbacks, barriers, locks, input delivery and types are doubles; used completions preloaded; no real publication/device/cache'},indent=2))
p=subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(H/'recycle.c'),'-o',str(H/'recycle.bin')],capture_output=True,text=True)
(H/'build.json').write_text(json.dumps({'code':p.returncode,'stderr':p.stderr},indent=2))
if p.returncode:raise RuntimeError(p.stderr)
rows=[]
for mode in range(9):
 for map_api in [0,1]:
  for length in [0,4,8]:
   p=subprocess.run([str(H/'recycle.bin'),str(mode),str(map_api),str(length)],capture_output=True,text=True)
   rows.append(dict(mode=mode,map_api=map_api,length=length,code=p.returncode,stdout=p.stdout,stderr=p.stderr))
(H/'results.json').write_text(json.dumps(rows,indent=2))
if any(r['code'] for r in rows):raise RuntimeError('failed execution; see results')
print('1 compile,54 executions passed')
