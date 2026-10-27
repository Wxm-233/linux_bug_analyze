
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
static bool vring_need_unmap_buffer(const struct vring_virtqueue *vring,
				    const struct vring_desc_extra *extra)
{
	return vring->use_map_api && (extra->addr != DMA_MAPPING_ERROR);
}
static unsigned int vring_unmap_one_split(const struct vring_virtqueue *vq,
					  struct vring_desc_extra *extra)
{
	u16 flags;

	flags = extra->flags;

	if (flags & VRING_DESC_F_INDIRECT) {
		if (!vq->use_map_api)
			goto out;
	} else if (!vring_need_unmap_buffer(vq, extra))
		goto out;

	virtqueue_unmap_page_attrs(&vq->vq,
				   extra->addr,
				   extra->len,
				   (flags & VRING_DESC_F_WRITE) ?
				   DMA_FROM_DEVICE : DMA_TO_DEVICE,
				   0);

out:
	return extra->next;
}
static unsigned detach_buf_split_in_order(struct vring_virtqueue *vq,
					  unsigned int head,
					  void **ctx)
{
	struct vring_desc_extra *extra;
	unsigned int i;
	__virtio16 nextflag = cpu_to_virtio16(vq->vq.vdev, VRING_DESC_F_NEXT);

	/* Clear data ptr. */
	vq->split.desc_state[head].data = NULL;

	extra = vq->split.desc_extra;

	/* Put back on free list: unmap first-level descriptors and find end */
	i = head;

	while (vq->split.vring.desc[i].flags & nextflag) {
		i = vring_unmap_one_split(vq, &extra[i]);
		vq->vq.num_free++;
	}

	vring_unmap_one_split(vq, &extra[i]);

	/* Plus final descriptor */
	vq->vq.num_free++;

	if (vq->indirect)
		detach_indirect_split(vq, head);
	else if (ctx)
		*ctx = vq->split.desc_state[head].indir_desc;

	return i;
}
static void detach_buf_split(struct vring_virtqueue *vq, unsigned int head,
			     void **ctx)
{
	unsigned int i = detach_buf_split_in_order(vq, head, ctx);

	vq->split.desc_extra[i].next = vq->free_head;
	vq->free_head = head;
}
static bool virtqueue_poll_split(const struct vring_virtqueue *vq,
				 unsigned int last_used_idx)
{
	return (u16)last_used_idx != virtio16_to_cpu(vq->vq.vdev,
			vq->split.vring.used->idx);
}
static bool more_used_split(const struct vring_virtqueue *vq)
{
	return virtqueue_poll_split(vq, vq->last_used_idx);
}
static void *virtqueue_get_buf_ctx_split(struct vring_virtqueue *vq,
					 unsigned int *len,
					 void **ctx)
{
	void *ret;
	unsigned int i;
	u16 last_used;

	START_USE(vq);

	if (unlikely(vq->broken)) {
		END_USE(vq);
		return NULL;
	}

	if (!more_used_split(vq)) {
		pr_debug("No more buffers in queue\n");
		END_USE(vq);
		return NULL;
	}

	/* Only get used array entries after they have been exposed by host. */
	virtio_rmb(vq->weak_barriers);

	last_used = (vq->last_used_idx & (vq->split.vring.num - 1));
	i = virtio32_to_cpu(vq->vq.vdev,
			vq->split.vring.used->ring[last_used].id);
	*len = virtio32_to_cpu(vq->vq.vdev,
			vq->split.vring.used->ring[last_used].len);

	if (unlikely(i >= vq->split.vring.num)) {
		BAD_RING(vq, "id %u out of range\n", i);
		return NULL;
	}
	if (unlikely(!vq->split.desc_state[i].data)) {
		BAD_RING(vq, "id %u is not a head!\n", i);
		return NULL;
	}

	/* detach_buf_split clears data, so grab it now. */
	ret = vq->split.desc_state[i].data;
	detach_buf_split(vq, i, ctx);
	vq->last_used_idx++;
	/* If we expect an interrupt for the next entry, tell host
	 * by writing event index and flush out the write before
	 * the read in the next get_buf call. */
	if (!(vq->split.avail_flags_shadow & VRING_AVAIL_F_NO_INTERRUPT))
		virtio_store_mb(vq->weak_barriers,
				&vring_used_event(&vq->split.vring),
				cpu_to_virtio16(vq->vq.vdev, vq->last_used_idx));

	LAST_ADD_TIME_INVALID(vq);

	END_USE(vq);
	return ret;
}
static void *virtqueue_get_buf(struct virtqueue*q,unsigned *len){void*p=virtqueue_get_buf_ctx_split((struct vring_virtqueue*)q,len,NULL);if(p){int i=(struct virtio_input_event*)p-current->evts;reclaimed[i]=true;printf("TOKEN %d %u\n",i,*len);}else puts("NO_TOKEN");return p;}
static void input_event(void*d,unsigned type,unsigned code,unsigned value){(void)d;assert(!locked&&type==1&&code<2&&value==1000+code&&reclaimed[code]);printf("CPU_READ %u OTHER_RECLAIMED %d\n",code,reclaimed[1-code]);reads++;if(mode==8){current->ready=false;puts("READY_FALSE_IN_CALLBACK");}}
static void sg_init_one(struct scatterlist*s,void*p,unsigned n){s->p=p;s->len=n;}
static int virtqueue_add_inbuf(struct virtqueue*q,struct scatterlist*s,unsigned n,void*p,int gfp){(void)q;(void)gfp;assert(locked&&n==1&&s->p==p&&s->len==8);int i=(struct virtio_input_event*)p-current->evts;int ret=mode==1?-28:mode==2?-12:0;adds++;printf("ADD %d %d READY %d\n",i,ret,current->ready);if(!ret)reclaimed[i]=false;return ret;}
static void virtqueue_kick(struct virtqueue*q){(void)q;assert(locked);kicks++;puts("KICK");}
static void virtinput_queue_evtbuf(struct virtio_input *vi,
				   struct virtio_input_event *evtbuf)
{
	struct scatterlist sg[1];

	sg_init_one(sg, evtbuf, sizeof(*evtbuf));
	virtqueue_add_inbuf(vi->evt, sg, 1, evtbuf, GFP_ATOMIC);
}
static void virtinput_recv_events(struct virtqueue *vq)
{
	struct virtio_input *vi = vq->vdev->priv;
	struct virtio_input_event *event;
	unsigned long flags;
	unsigned int len;

	spin_lock_irqsave(&vi->lock, flags);
	if (vi->ready) {
		while ((event = virtqueue_get_buf(vi->evt, &len)) != NULL) {
			spin_unlock_irqrestore(&vi->lock, flags);
			input_event(vi->idev,
				    le16_to_cpu(event->type),
				    le16_to_cpu(event->code),
				    le32_to_cpu(event->value));
			spin_lock_irqsave(&vi->lock, flags);
			virtinput_queue_evtbuf(vi, event);
		}
		virtqueue_kick(vq);
	}
	spin_unlock_irqrestore(&vi->lock, flags);
}
int main(int argc,char**argv){assert(argc==4);mode=atoi(argv[1]);int map=atoi(argv[2]);unsigned len=atoi(argv[3]);struct vring_virtqueue v={0};struct virtio_input vi={0};struct virtio_device dev={.priv=&vi};struct used used={.idx=2,.ring={{0,len},{1,len}}};v.vq.vdev=&dev;v.use_map_api=map;v.split.vring.num=4;v.split.vring.used=&used;vi.evt=&v.vq;vi.ready=mode!=7;current=&vi;for(int i=0;i<2;i++){vi.evts[i]=(struct virtio_input_event){1,i,1000+i};v.split.desc_state[i].data=&vi.evts[i];v.split.desc_extra[i]=(struct vring_desc_extra){100+i,8,VRING_DESC_F_WRITE,0};}if(mode==3)v.broken=true;if(mode==4)used.idx=0;if(mode==5)used.ring[0].id=4;if(mode==6)v.split.desc_state[0].data=NULL;virtinput_recv_events(&v.vq);int consume=mode<=2||mode==8;assert(reads==2*consume&&adds==reads&&unmaps==reads*map&&kicks==(mode!=7)&&!locked&&v.last_used_idx==reads&&v.vq.num_free==(unsigned)reads);printf("FINAL reads=%d adds=%d unmaps=%d kicks=%d ready=%d\n",reads,adds,unmaps,kicks,vi.ready);}
