
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
static bool vring_use_map_api(const struct virtio_device *vdev)
{
	if (!virtio_has_dma_quirk(vdev))
		return true;

	/* Otherwise, we are left to guess. */
	/*
	 * In theory, it's possible to have a buggy QEMU-supposed
	 * emulated Q35 IOMMU and Xen enabled at the same time.  On
	 * such a configuration, virtio has never worked and will
	 * not work without an even larger kludge.  Instead, enable
	 * the DMA API if we're a Xen guest, which at least allows
	 * all of the sensible Xen configurations to work correctly.
	 */
	if (xen_domain())
		return true;

	return false;
}
static bool vring_need_unmap_buffer(const struct vring_virtqueue *vring,
				    const struct vring_desc_extra *extra)
{
	return vring->use_map_api && (extra->addr != DMA_MAPPING_ERROR);
}
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
int main(int argc,char**argv){assert(argc==2);int bits=atoi(argv[1]);int quirk=bits&1;xen=(bits>>1)&1;int custom=(bits>>2)&1,premapped=(bits>>3)&1;fail=(bits>>4)&1;
struct device dev={7};struct page page={9};struct map_ops ops={custom_map,custom_unmap,custom_error};struct virtio_device vd={custom?&ops:NULL,quirk};struct vring_virtqueue vq={.vq={&vd},.map={&dev}};vq.use_map_api=vring_use_map_api(&vd);struct scatterlist sg={.length=8,.offset=128,.dma_len=8,.phys=0x10080,.dma=0x40080,.page=&page};dma_addr_t addr;u32 len;
int ret=vring_map_one_sg(&vq,&sg,DMA_FROM_DEVICE,&addr,&len,premapped,0);assert(len==8);
if(!ret){struct vring_desc_extra ex={.flags=VRING_DESC_F_WRITE,.addr=premapped?DMA_MAPPING_ERROR:addr,.len=len,.next=17};assert(vring_unmap_one_split(&vq,&ex)==17);}
bool mapped=!premapped&&vq.use_map_api;assert(vq.use_map_api==(!quirk||xen));assert(ret==(mapped&&fail?-ENOMEM:0));assert(dma_maps==(mapped&&!custom)&&custom_maps==(mapped&&custom));assert(dma_unmaps==(mapped&&!custom&&!fail)&&custom_unmaps==(mapped&&custom&&!fail));assert(kmsan==(!premapped&&!vq.use_map_api));
printf("RESULT %d %d %llu %u %d %d %d %d %d\n",ret,vq.use_map_api,(unsigned long long)addr,len,dma_maps,custom_maps,dma_unmaps,custom_unmaps,kmsan);return 0;}
