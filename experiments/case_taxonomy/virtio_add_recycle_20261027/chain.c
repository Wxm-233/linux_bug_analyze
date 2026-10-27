
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
static struct device *vring_dma_dev(const struct vring_virtqueue *vq)
{
	return vq->map.dma_dev;
}
static int vring_mapping_error(const struct vring_virtqueue *vq,
			       dma_addr_t addr)
{
	struct virtio_device *vdev = vq->vq.vdev;

	if (!vq->use_map_api)
		return 0;

	if (vdev->map)
		return vdev->map->mapping_error(vq->map, addr);
	else
		return dma_mapping_error(vring_dma_dev(vq), addr);
}
dma_addr_t virtqueue_map_page_attrs(const struct virtqueue *_vq,
				    struct page *page,
				    unsigned long offset,
				    size_t size,
				    enum dma_data_direction dir,
				    unsigned long attrs)
{
	const struct vring_virtqueue *vq = to_vvq(_vq);
	struct virtio_device *vdev = _vq->vdev;

	if (vdev->map)
		return vdev->map->map_page(vq->map,
					   page, offset, size,
					   dir, attrs);

	return dma_map_page_attrs(vring_dma_dev(vq),
				  page, offset, size,
				  dir, attrs);
}
void virtqueue_unmap_page_attrs(const struct virtqueue *_vq,
				dma_addr_t map_handle,
				size_t size, enum dma_data_direction dir,
				unsigned long attrs)
{
	const struct vring_virtqueue *vq = to_vvq(_vq);
	struct virtio_device *vdev = _vq->vdev;

	if (vdev->map)
		vdev->map->unmap_page(vq->map,
				      map_handle, size, dir, attrs);
	else
		dma_unmap_page_attrs(vring_dma_dev(vq), map_handle,
				     size, dir, attrs);
}
static int vring_map_one_sg(const struct vring_virtqueue *vq, struct scatterlist *sg,
			    enum dma_data_direction direction, dma_addr_t *addr,
			    u32 *len, bool premapped, unsigned long attr)
{
	if (premapped) {
		*addr = sg_dma_address(sg);
		*len = sg_dma_len(sg);
		return 0;
	}

	*len = sg->length;

	if (!vq->use_map_api) {
		/*
		 * If DMA is not used, KMSAN doesn't know that the scatterlist
		 * is initialized by the hardware. Explicitly check/unpoison it
		 * depending on the direction.
		 */
		kmsan_handle_dma(sg_phys(sg), sg->length, direction);
		*addr = (dma_addr_t)sg_phys(sg);
		return 0;
	}

	/*
	 * We can't use dma_map_sg, because we don't use scatterlists in
	 * the way it expects (we don't guarantee that the scatterlist
	 * will exist for the lifetime of the mapping).
	 */
	*addr = virtqueue_map_page_attrs(&vq->vq, sg_page(sg),
					 sg->offset, sg->length,
					 direction, attr);

	if (vring_mapping_error(vq, *addr))
		return -ENOMEM;

	return 0;
}
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
static bool virtqueue_use_indirect(const struct vring_virtqueue *vq,
				   unsigned int total_sg)
{
	/*
	 * If the host supports indirect descriptor tables, and we have multiple
	 * buffers, then go indirect. FIXME: tune this threshold
	 */
	return (vq->indirect && total_sg > 1 && vq->vq.num_free);
}
static inline unsigned int virtqueue_add_desc_split(struct vring_virtqueue *vq,
						    struct vring_desc *desc,
						    struct vring_desc_extra *extra,
						    unsigned int i,
						    dma_addr_t addr,
						    unsigned int len,
						    u16 flags, bool premapped)
{
	struct virtio_device *vdev = vq->vq.vdev;
	u16 next;

	desc[i].flags = cpu_to_virtio16(vdev, flags);
	desc[i].addr = cpu_to_virtio64(vdev, addr);
	desc[i].len = cpu_to_virtio32(vdev, len);

	extra[i].addr = premapped ? DMA_MAPPING_ERROR : addr;
	extra[i].len = len;
	extra[i].flags = flags;

	next = extra[i].next;

	desc[i].next = cpu_to_virtio16(vdev, next);

	return next;
}
static inline int virtqueue_add_split(struct vring_virtqueue *vq,
				      struct scatterlist *sgs[],
				      unsigned int total_sg,
				      unsigned int out_sgs,
				      unsigned int in_sgs,
				      void *data,
				      void *ctx,
				      bool premapped,
				      gfp_t gfp,
				      unsigned long attr)
{
	struct vring_desc_extra *extra;
	struct scatterlist *sg;
	struct vring_desc *desc;
	unsigned int i, n, avail, descs_used, err_idx, sg_count = 0;
	/* Total length for in-order */
	unsigned int total_in_len = 0;
	int head;
	bool indirect;

	START_USE(vq);

	BUG_ON(data == NULL);
	BUG_ON(ctx && vq->indirect);

	if (unlikely(vq->broken)) {
		END_USE(vq);
		return -EIO;
	}

	LAST_ADD_TIME_UPDATE(vq);

	BUG_ON(total_sg == 0);

	head = vq->free_head;

	if (virtqueue_use_indirect(vq, total_sg))
		desc = alloc_indirect_split(vq, total_sg, gfp);
	else {
		desc = NULL;
		WARN_ON_ONCE(total_sg > vq->split.vring.num && !vq->indirect);
	}

	if (desc) {
		/* Use a single buffer which doesn't continue */
		indirect = true;
		/* Set up rest to use this indirect table. */
		i = 0;
		descs_used = 1;
		extra = (struct vring_desc_extra *)&desc[total_sg];
	} else {
		indirect = false;
		desc = vq->split.vring.desc;
		extra = vq->split.desc_extra;
		i = head;
		descs_used = total_sg;
	}

	if (unlikely(vq->vq.num_free < descs_used)) {
		pr_debug("Can't add buf len %i - avail = %i\n",
			 descs_used, vq->vq.num_free);
		/* FIXME: for historical reasons, we force a notify here if
		 * there are outgoing parts to the buffer.  Presumably the
		 * host should service the ring ASAP. */
		if (out_sgs)
			vq->notify(&vq->vq);
		if (indirect)
			kfree(desc);
		END_USE(vq);
		return -ENOSPC;
	}

	for (n = 0; n < out_sgs; n++) {
		for (sg = sgs[n]; sg; sg = sg_next(sg)) {
			dma_addr_t addr;
			u32 len;
			u16 flags = 0;

			if (++sg_count != total_sg)
				flags |= VRING_DESC_F_NEXT;

			if (vring_map_one_sg(vq, sg, DMA_TO_DEVICE, &addr, &len,
					     premapped, attr))
				goto unmap_release;

			/* Note that we trust indirect descriptor
			 * table since it use stream DMA mapping.
			 */
			i = virtqueue_add_desc_split(vq, desc, extra, i, addr,
						     len, flags, premapped);
		}
	}
	for (; n < (out_sgs + in_sgs); n++) {
		for (sg = sgs[n]; sg; sg = sg_next(sg)) {
			dma_addr_t addr;
			u32 len;
			u16 flags = VRING_DESC_F_WRITE;

			if (++sg_count != total_sg)
				flags |= VRING_DESC_F_NEXT;

			if (vring_map_one_sg(vq, sg, DMA_FROM_DEVICE, &addr, &len,
					     premapped, attr))
				goto unmap_release;

			/* Note that we trust indirect descriptor
			 * table since it use stream DMA mapping.
			 */
			i = virtqueue_add_desc_split(vq, desc, extra, i, addr,
						     len, flags, premapped);
			total_in_len += len;
		}
	}

	if (indirect) {
		/* Now that the indirect table is filled in, map it. */
		dma_addr_t addr = vring_map_single(
			vq, desc, total_sg * sizeof(struct vring_desc),
			DMA_TO_DEVICE);
		if (vring_mapping_error(vq, addr))
			goto unmap_release;

		virtqueue_add_desc_split(vq, vq->split.vring.desc,
					 vq->split.desc_extra,
					 head, addr,
					 total_sg * sizeof(struct vring_desc),
					 VRING_DESC_F_INDIRECT, false);
	}

	/* We're using some buffers from the free list. */
	vq->vq.num_free -= descs_used;

	/* Update free pointer */
	if (virtqueue_is_in_order(vq)) {
		vq->free_head += descs_used;
		if (vq->free_head >= vq->split.vring.num)
			vq->free_head -= vq->split.vring.num;
		vq->split.desc_state[head].total_in_len = total_in_len;
	} else if (indirect)
		vq->free_head = vq->split.desc_extra[head].next;
	else
		vq->free_head = i;

	/* Store token and indirect buffer state. */
	vq->split.desc_state[head].data = data;
	if (indirect)
		vq->split.desc_state[head].indir_desc = desc;
	else
		vq->split.desc_state[head].indir_desc = ctx;

	/* Put entry in available array (but don't update avail->idx until they
	 * do sync). */
	avail = vq->split.avail_idx_shadow & (vq->split.vring.num - 1);
	vq->split.vring.avail->ring[avail] = cpu_to_virtio16(vq->vq.vdev, head);

	/* Descriptors and available array need to be set before we expose the
	 * new available array entries. */
	virtio_wmb(vq->weak_barriers);
	vq->split.avail_idx_shadow++;
	vq->split.vring.avail->idx = cpu_to_virtio16(vq->vq.vdev,
						vq->split.avail_idx_shadow);
	vq->num_added++;

	pr_debug("Added buffer head %i to %p\n", head, vq);
	END_USE(vq);

	/* This is very unlikely, but theoretically possible.  Kick
	 * just in case. */
	if (unlikely(vq->num_added == (1 << 16) - 1))
		virtqueue_kick(&vq->vq);

	return 0;

unmap_release:
	err_idx = i;

	if (indirect)
		i = 0;
	else
		i = head;

	for (n = 0; n < total_sg; n++) {
		if (i == err_idx)
			break;

		i = vring_unmap_one_split(vq, &extra[i]);
	}

	if (indirect)
		kfree(desc);

	END_USE(vq);
	return -ENOMEM;
}
static void detach_indirect_split(struct vring_virtqueue *vq,
				  unsigned int head)
{
	struct vring_desc_extra *extra = vq->split.desc_extra;
	struct vring_desc *indir_desc = vq->split.desc_state[head].indir_desc;
	unsigned int j;
	u32 len, num;

	/* Free the indirect table, if any, now that it's unmapped. */
	if (!indir_desc)
		return;
	len = vq->split.desc_extra[head].len;

	BUG_ON(!(vq->split.desc_extra[head].flags &
			VRING_DESC_F_INDIRECT));
	BUG_ON(len == 0 || len % sizeof(struct vring_desc));

	num = len / sizeof(struct vring_desc);

	extra = (struct vring_desc_extra *)&indir_desc[num];

	if (vq->use_map_api) {
		for (j = 0; j < num; j++)
			vring_unmap_one_split(vq, &extra[j]);
	}

	kfree(indir_desc);
	vq->split.desc_state[head].indir_desc = NULL;
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
/* This adapter intentionally fixes the dispatcher to the registered ordinary split layout. */
static int virtqueue_add(struct virtqueue*q,struct scatterlist**s,unsigned total,unsigned out,unsigned in,void*data,void*ctx,bool pre,gfp_t g,unsigned long a){assert(locked&&total==1&&out==0&&in==1&&!ctx&&!pre&&!a);struct vring_virtqueue*v=(void*)q;int i=object(data);unsigned before=v->split.avail_idx_shadow,free_before=q->num_free;attempts++;printf("ATTEMPT %d %d %u %u\n",phase,i,free_before,before);int ret=virtqueue_add_split(v,s,total,out,in,data,ctx,pre,g,a);lastret[i]=ret;if(!ret){assert(v->split.avail_idx_shadow==(u16)(before+1)&&v->split.vring.avail->idx==(u16)(before+1)&&q->num_free==free_before-1);publications[i]++;printf("PUBLISHED %d %d %u\n",phase,i,v->split.vring.avail->idx);}else{assert(v->split.avail_idx_shadow==before&&v->split.vring.avail->idx==before&&q->num_free==free_before);}printf("ADD_RETURN %d %d %d\n",phase,i,ret);return ret;}
int virtqueue_add_inbuf(struct virtqueue *vq,
			struct scatterlist *sg, unsigned int num,
			void *data,
			gfp_t gfp)
{
	return virtqueue_add(vq, &sg, num, 0, 1, data, NULL, false, gfp, 0);
}
static void sg_init_one(struct scatterlist*s,void*p,unsigned n){int i=object(p);*s=(struct scatterlist){.page=&pages[i],.length=n,.phys=0x1000+8*i};}
static void *virtqueue_get_buf(struct virtqueue*q,unsigned*len){void*p=virtqueue_get_buf_ctx_split((struct vring_virtqueue*)q,len,NULL);if(p)printf("TOKEN %d %u\n",object(p),*len);else puts("NO_TOKEN");return p;}
static void input_event(void*d,unsigned type,unsigned code,unsigned value){(void)d;assert(!locked&&type==1&&code<2&&value==1000+code&&!mapped[code]);reads++;printf("CPU_READ %u\n",code);if(mode==6){active->broken=true;puts("BROKEN_IN_CALLBACK");}}
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
static void complete_available(struct vring_virtqueue*v){struct used*u=v->split.vring.used;u16 end=v->split.vring.avail->idx;for(u16 j=u->idx;j!=end;j++){unsigned head=v->split.vring.avail->ring[j&3];assert(v->split.desc_state[head].data);int i=object(v->split.desc_state[head].data);u->ring[j&3].id=head;u->ring[j&3].len=8;printf("SIM_USED %d %u\n",i,head);}u->idx=end;}
int main(int argc,char**argv){assert(argc==4);mode=atoi(argv[1]);route=atoi(argv[2]);int ind=atoi(argv[3]);struct device dma={7};struct map_ops ops={custom_map,custom_unmap,custom_error};struct virtio_input vi={0};struct virtio_device dev={.priv=&vi,.map=route==2?&ops:NULL};struct used used={0};struct avail avail={0};struct vring_virtqueue v={.vq={&dev,4},.map={&dma},.use_map_api=route!=0,.indirect=ind,.notify=notify};v.split.vring=(struct vring){.num=4,.used=&used,.avail=&avail};for(int i=0;i<4;i++)v.split.desc_extra[i].next=(i+1)&3;vi.evt=&v.vq;vi.ready=true;current=&vi;active=&v;for(int i=0;i<2;i++)vi.evts[i]=(struct virtio_input_event){1,i,1000+i};if(mode==2)v.vq.num_free=0;if(mode==3)v.broken=true;locked=1;virtinput_queue_evtbuf(&vi,&vi.evts[0]);virtinput_queue_evtbuf(&vi,&vi.evts[1]);locked=0;printf("AFTER_FILL %d %d %u\n",lastret[0],lastret[1],v.vq.num_free);complete_available(&v);phase=1;virtinput_recv_events(&v.vq);printf("AFTER_RECV %d %d %u\n",lastret[0],lastret[1],v.vq.num_free);if(mode==8&&route){assert(lastret[0]==-ENOMEM);phase=2;locked=1;virtinput_queue_evtbuf(&vi,&vi.evts[0]);locked=0;assert(lastret[0]==0);puts("MANUAL_RECOVERY");}if(mode==0||(mode==8&&!route)){complete_available(&v);phase=2;virtinput_recv_events(&v.vq);}assert(!locked);if(mode==2){assert(lastret[0]==-ENOSPC&&lastret[1]==-ENOSPC&&reads==0&&mapcalls==0);}else if(mode==3){assert(lastret[0]==-EIO&&lastret[1]==-EIO&&reads==0&&mapcalls==0);}else if(mode==1&&route){assert(lastret[0]==-ENOMEM&&lastret[1]==-ENOMEM&&reads==0&&unmaps==0&&barriers==0);}else if(mode==6){assert(reads==1&&lastret[0]==-EIO&&publications[0]==1&&publications[1]==1);}else if(mode==7&&route){assert(reads==1&&publications[0]==0&&publications[1]==2);}else{assert(reads==((mode==0||(mode==8&&!route))?4:2));if(route&&(mode==4||mode==5||mode==8)){assert(publications[0]==(mode==8?2:1));assert(lastret[0]==(mode==8?0:-ENOMEM));}else assert(lastret[0]==0&&lastret[1]==0);}if(mode!=2) {unsigned tokens=0;for(int i=0;i<4;i++)tokens+=v.split.desc_state[i].data!=NULL;assert(tokens+v.vq.num_free==4);}printf("FINAL %d %d %d %d %d %d %d %d\n",attempts,mapcalls,unmaps,reads,kicks,barriers,publications[0],publications[1]);}
