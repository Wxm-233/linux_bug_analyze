from pathlib import Path
import hashlib,json,re,subprocess
H=Path(__file__).resolve().parent;S=H.parent/'virtio_dma_chain_20261026/source';manifest=[]
def fun(file,n):
 p=S/file;s=p.read_text();m=re.search(r'^(?:(?:static|inline)\s+)*(?:unsigned int|unsigned|int|bool|void|dma_addr_t|struct device\s*\*)\s*\*?\s*'+n+r'\([^;{]*\)\s*\{',s,re.M)
 if not m:raise RuntimeError('missing '+n)
 a=m.start();b=m.end();depth=1
 while depth:depth+=(s[b]=='{')-(s[b]=='}');b+=1
 t=s[a:b];manifest.append(dict(name=n,file=file,line=s[:a].count('\n')+1,sha256=hashlib.sha256(t.encode()).hexdigest(),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest()));return t
head=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
#include <errno.h>
typedef uint16_t u16;typedef uint16_t __virtio16;typedef uint32_t u32;typedef uint64_t dma_addr_t;typedef unsigned gfp_t;
enum dma_data_direction {DMA_TO_DEVICE=1,DMA_FROM_DEVICE=2};
#define DMA_MAPPING_ERROR (~0ULL)
#define VRING_DESC_F_NEXT 1
#define VRING_DESC_F_WRITE 2
#define VRING_DESC_F_INDIRECT 4
#define VRING_AVAIL_F_NO_INTERRUPT 1
#define GFP_ATOMIC 0
#define unlikely(x) (x)
#define cpu_to_virtio16(d,x) ((void)(d),(x))
#define cpu_to_virtio32(d,x) ((void)(d),(x))
#define cpu_to_virtio64(d,x) ((void)(d),(x))
#define virtio16_to_cpu(d,x) ((void)(d),(x))
#define virtio32_to_cpu(d,x) ((void)(d),(x))
#define le16_to_cpu(x) (x)
#define le32_to_cpu(x) (x)
#define START_USE(v) ((void)(v))
#define END_USE(v) ((void)(v))
#define LAST_ADD_TIME_UPDATE(v) ((void)(v))
#define LAST_ADD_TIME_INVALID(v) ((void)(v))
#define BUG_ON(x) assert(!(x))
#define WARN_ON_ONCE(x) ((void)(x))
#define pr_debug(...) ((void)0)
#define BAD_RING(v,...) do{(v)->broken=true;puts("BAD_RING");}while(0)
#define virtio_rmb(b) ((void)(b),puts("RMB"))
#define virtio_store_mb(b,p,x) do{(void)(b);*(p)=(x);puts("EVENT_STORE");}while(0)
#define vring_used_event(v) ((v)->event)
struct device {int tag;};struct page {int object;};
union virtio_map {struct device *dma_dev;};
struct map_ops {dma_addr_t(*map_page)(union virtio_map,struct page*,unsigned long,size_t,enum dma_data_direction,unsigned long);void(*unmap_page)(union virtio_map,dma_addr_t,size_t,enum dma_data_direction,unsigned long);int(*mapping_error)(union virtio_map,dma_addr_t);};
struct virtio_device {void *priv;struct map_ops *map;};
struct virtqueue {struct virtio_device *vdev;unsigned num_free;};
struct vring_desc_extra {dma_addr_t addr;u32 len;u16 flags,next;};
struct vring_desc {dma_addr_t addr;u32 len;u16 flags,next;};
struct state {void *data;struct vring_desc *indir_desc;unsigned total_in_len;};
struct used {u16 idx;struct {u32 id,len;}ring[4];};
struct avail {u16 idx;u16 ring[4];};
struct vring {unsigned num;struct used *used;struct avail *avail;struct vring_desc desc[4];u16 event;};
struct vring_virtqueue {struct virtqueue vq;union virtio_map map;bool use_map_api,indirect,broken,weak_barriers;u16 last_used_idx,free_head;unsigned num_added;bool(*notify)(struct virtqueue*);struct {struct vring vring;struct state desc_state[4];struct vring_desc_extra desc_extra[4];u16 avail_flags_shadow,avail_idx_shadow;}split;};
#define to_vvq(v) ((const struct vring_virtqueue*)(v))
struct virtio_input_event {u16 type,code;u32 value;};
struct virtio_input {struct virtqueue *evt;void *idev;int lock;bool ready;struct virtio_input_event evts[2];};
struct scatterlist {struct page *page;unsigned offset,length;dma_addr_t phys,dma;unsigned dma_len;struct scatterlist *next;};
#define sg_phys(s) ((s)->phys)
#define sg_page(s) ((s)->page)
#define sg_dma_address(s) ((s)->dma)
#define sg_dma_len(s) ((s)->dma_len)
static struct scatterlist *sg_next(struct scatterlist*s){return s->next;}
static struct virtio_input *current;static struct vring_virtqueue *active;static struct page pages[2]={{0},{1}};
static int mode,route,phase,locked,attempts,mapcalls,unmaps,reads,kicks,barriers;static int lastret[2],publications[2];static bool failed_once,mapped[2];
#define spin_lock_irqsave(p,f) do{(void)(p);(f)=0;assert(!locked);locked=1;puts("LOCK");}while(0)
#define spin_unlock_irqrestore(p,f) do{(void)(p);(void)(f);assert(locked);locked=0;puts("UNLOCK");}while(0)
static int object(void*p){int i=(struct virtio_input_event*)p-current->evts;assert(i>=0&&i<2);return i;}
static void virtqueue_kick(struct virtqueue*q){(void)q;kicks++;puts("KICK");}
static bool virtqueue_is_in_order(const struct vring_virtqueue*v){(void)v;return false;}

static struct vring_desc *alloc_indirect_split(struct vring_virtqueue*v,unsigned n,gfp_t g){(void)v;(void)n;(void)g;abort();}
static dma_addr_t vring_map_single(const struct vring_virtqueue*v,void*p,size_t n,enum dma_data_direction d){(void)v;(void)p;(void)n;(void)d;abort();}
static void kfree(void*p){(void)p;abort();}
static bool notify(struct virtqueue*q){(void)q;abort();}
static void kmsan_handle_dma(dma_addr_t a,size_t n,enum dma_data_direction d){assert((a==0x1000||a==0x1008)&&n==8&&d==DMA_FROM_DEVICE);printf("BYPASS %d\n",(int)((a-0x1000)/8));}
static dma_addr_t backend_map(struct page*p,unsigned long offset,size_t n,enum dma_data_direction d,unsigned long attrs){int i=p->object;assert(!offset&&n==8&&d==DMA_FROM_DEVICE&&!attrs&&!mapped[i]);mapcalls++;bool fail=(mode==1&&phase==0)||(mode==7&&phase==0&&i==0)||(mode==5&&phase==1)||((mode==4||mode==8)&&phase==1&&i==0&&!failed_once);if(fail){failed_once=true;printf("MAP_FAIL %d %d\n",phase,i);return DMA_MAPPING_ERROR;}mapped[i]=true;printf("MAP_OK %d %d\n",phase,i);return 0x2000+8*i;}
static void backend_unmap(dma_addr_t addr,size_t n,enum dma_data_direction d,unsigned long attrs){assert(addr>=0x2000&&addr<=0x2008&&n==8&&d==DMA_FROM_DEVICE&&!attrs);int i=(addr-0x2000)/8;assert(mapped[i]);mapped[i]=false;unmaps++;printf("UNMAP %d\n",i);}
static dma_addr_t dma_map_page_attrs(struct device*d,struct page*p,unsigned long o,size_t n,enum dma_data_direction dir,unsigned long a){assert(d->tag==7&&route==1);return backend_map(p,o,n,dir,a);}
static int dma_mapping_error(struct device*d,dma_addr_t a){(void)d;return a==DMA_MAPPING_ERROR;}
static void dma_unmap_page_attrs(struct device*d,dma_addr_t a,size_t n,enum dma_data_direction dir,unsigned long attrs){assert(d->tag==7&&route==1);backend_unmap(a,n,dir,attrs);}
static dma_addr_t custom_map(union virtio_map m,struct page*p,unsigned long o,size_t n,enum dma_data_direction d,unsigned long a){assert(m.dma_dev->tag==7&&route==2);return backend_map(p,o,n,d,a);}
static int custom_error(union virtio_map m,dma_addr_t a){(void)m;return a==DMA_MAPPING_ERROR;}
static void custom_unmap(union virtio_map m,dma_addr_t a,size_t n,enum dma_data_direction d,unsigned long attrs){assert(m.dma_dev->tag==7&&route==2);backend_unmap(a,n,d,attrs);}
static void wmb_probe(void){barriers++;unsigned slot=active->split.avail_idx_shadow&3;unsigned head=active->split.vring.avail->ring[slot];struct vring_desc *d=&active->split.vring.desc[head];int i=object(active->split.desc_state[head].data);assert(d->flags==VRING_DESC_F_WRITE&&d->len==8&&d->addr==(route?0x2000ULL:0x1000ULL)+8*i);assert(active->split.vring.avail->idx==active->split.avail_idx_shadow);printf("BEFORE_PUBLISH %d %d %u\n",phase,i,active->split.avail_idx_shadow);}
#define virtio_wmb(b) ((void)(b),wmb_probe())
'''
dispatch=r'''
/* This adapter intentionally fixes the dispatcher to the registered ordinary split layout. */
static int virtqueue_add(struct virtqueue*q,struct scatterlist**s,unsigned total,unsigned out,unsigned in,void*data,void*ctx,bool pre,gfp_t g,unsigned long a){assert(locked&&total==1&&out==0&&in==1&&!ctx&&!pre&&!a);struct vring_virtqueue*v=(void*)q;int i=object(data);unsigned before=v->split.avail_idx_shadow,free_before=q->num_free;attempts++;printf("ATTEMPT %d %d %u %u\n",phase,i,free_before,before);int ret=virtqueue_add_split(v,s,total,out,in,data,ctx,pre,g,a);lastret[i]=ret;if(!ret){assert(v->split.avail_idx_shadow==(u16)(before+1)&&v->split.vring.avail->idx==(u16)(before+1)&&q->num_free==free_before-1);publications[i]++;printf("PUBLISHED %d %d %u\n",phase,i,v->split.vring.avail->idx);}else{assert(v->split.avail_idx_shadow==before&&v->split.vring.avail->idx==before&&q->num_free==free_before);}printf("ADD_RETURN %d %d %d\n",phase,i,ret);return ret;}
'''
driverglue=r'''
static void sg_init_one(struct scatterlist*s,void*p,unsigned n){int i=object(p);*s=(struct scatterlist){.page=&pages[i],.length=n,.phys=0x1000+8*i};}
static void *virtqueue_get_buf(struct virtqueue*q,unsigned*len){void*p=virtqueue_get_buf_ctx_split((struct vring_virtqueue*)q,len,NULL);if(p)printf("TOKEN %d %u\n",object(p),*len);else puts("NO_TOKEN");return p;}
static void input_event(void*d,unsigned type,unsigned code,unsigned value){(void)d;assert(!locked&&type==1&&code<2&&value==1000+code&&!mapped[code]);reads++;printf("CPU_READ %u\n",code);if(mode==6){active->broken=true;puts("BROKEN_IN_CALLBACK");}}
'''
tail=r'''
static void complete_available(struct vring_virtqueue*v){struct used*u=v->split.vring.used;u16 end=v->split.vring.avail->idx;for(u16 j=u->idx;j!=end;j++){unsigned head=v->split.vring.avail->ring[j&3];assert(v->split.desc_state[head].data);int i=object(v->split.desc_state[head].data);u->ring[j&3].id=head;u->ring[j&3].len=8;printf("SIM_USED %d %u\n",i,head);}u->idx=end;}
int main(int argc,char**argv){assert(argc==4);mode=atoi(argv[1]);route=atoi(argv[2]);int ind=atoi(argv[3]);struct device dma={7};struct map_ops ops={custom_map,custom_unmap,custom_error};struct virtio_input vi={0};struct virtio_device dev={.priv=&vi,.map=route==2?&ops:NULL};struct used used={0};struct avail avail={0};struct vring_virtqueue v={.vq={&dev,4},.map={&dma},.use_map_api=route!=0,.indirect=ind,.notify=notify};v.split.vring=(struct vring){.num=4,.used=&used,.avail=&avail};for(int i=0;i<4;i++)v.split.desc_extra[i].next=(i+1)&3;vi.evt=&v.vq;vi.ready=true;current=&vi;active=&v;for(int i=0;i<2;i++)vi.evts[i]=(struct virtio_input_event){1,i,1000+i};if(mode==2)v.vq.num_free=0;if(mode==3)v.broken=true;locked=1;virtinput_queue_evtbuf(&vi,&vi.evts[0]);virtinput_queue_evtbuf(&vi,&vi.evts[1]);locked=0;printf("AFTER_FILL %d %d %u\n",lastret[0],lastret[1],v.vq.num_free);complete_available(&v);phase=1;virtinput_recv_events(&v.vq);printf("AFTER_RECV %d %d %u\n",lastret[0],lastret[1],v.vq.num_free);if(mode==8&&route){assert(lastret[0]==-ENOMEM);phase=2;locked=1;virtinput_queue_evtbuf(&vi,&vi.evts[0]);locked=0;assert(lastret[0]==0);puts("MANUAL_RECOVERY");}if(mode==0||(mode==8&&!route)){complete_available(&v);phase=2;virtinput_recv_events(&v.vq);}assert(!locked);if(mode==2){assert(lastret[0]==-ENOSPC&&lastret[1]==-ENOSPC&&reads==0&&mapcalls==0);}else if(mode==3){assert(lastret[0]==-EIO&&lastret[1]==-EIO&&reads==0&&mapcalls==0);}else if(mode==1&&route){assert(lastret[0]==-ENOMEM&&lastret[1]==-ENOMEM&&reads==0&&unmaps==0&&barriers==0);}else if(mode==6){assert(reads==1&&lastret[0]==-EIO&&publications[0]==1&&publications[1]==1);}else if(mode==7&&route){assert(reads==1&&publications[0]==0&&publications[1]==2);}else{assert(reads==((mode==0||(mode==8&&!route))?4:2));if(route&&(mode==4||mode==5||mode==8)){assert(publications[0]==(mode==8?2:1));assert(lastret[0]==(mode==8?0:-ENOMEM));}else assert(lastret[0]==0&&lastret[1]==0);}if(mode!=2) {unsigned tokens=0;for(int i=0;i<4;i++)tokens+=v.split.desc_state[i].data!=NULL;assert(tokens+v.vq.num_free==4);}printf("FINAL %d %d %d %d %d %d %d %d\n",attempts,mapcalls,unmaps,reads,kicks,barriers,publications[0],publications[1]);}
'''
ring='drivers__virtio__virtio_ring.c';driver='drivers__virtio__virtio_input.c'
before=['vring_dma_dev','vring_mapping_error','virtqueue_map_page_attrs','virtqueue_unmap_page_attrs','vring_map_one_sg','vring_need_unmap_buffer','vring_unmap_one_split','virtqueue_use_indirect','virtqueue_add_desc_split','virtqueue_add_split','detach_indirect_split','detach_buf_split_in_order','detach_buf_split','virtqueue_poll_split','more_used_split','virtqueue_get_buf_ctx_split']
code=head+'\n'.join(fun(ring,n) for n in before)+dispatch+fun(ring,'virtqueue_add_inbuf')+driverglue+'\n'.join(fun(driver,n) for n in ['virtinput_queue_evtbuf','virtinput_recv_events'])+tail
(H/'chain.c').write_text(code)
(H/'functions.json').write_text(json.dumps({'revision':'db191ba0c8564ff84877e5b1c9553e991feca239','functions':manifest,'scope':'original add/map/descriptor/get/recv chain; layout dispatcher, DMA backend, types, SG, locks/barriers and input endpoint are doubles; device completion simulated; indirect allocation unreachable for single SG'},indent=2))
p=subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(H/'chain.c'),'-o',str(H/'chain.bin')],capture_output=True,text=True)
(H/'build.json').write_text(json.dumps(dict(code=p.returncode,stderr=p.stderr),indent=2))
if p.returncode:raise RuntimeError(p.stderr)
rows=[]
for mode in range(9):
 for route in range(3):
  for indirect in [0,1]:
   p=subprocess.run([str(H/'chain.bin'),str(mode),str(route),str(indirect)],capture_output=True,text=True)
   rows.append(dict(mode=mode,route=route,indirect=indirect,code=p.returncode,stdout=p.stdout,stderr=p.stderr))
(H/'results.json').write_text(json.dumps(rows,indent=2))
if any(r['code'] for r in rows):raise RuntimeError('failed executions; see results.json')
print('1 build /54 add-publication-recycle executions passed')
