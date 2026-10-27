
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
typedef uint8_t __u8;
typedef uint16_t __le16;
typedef uint32_t __le32;
typedef struct { unsigned int value; } spinlock_t;
struct virtio_device;
struct input_dev;
#define __aligned(x) __attribute__((aligned(x)))
#ifdef ARCH_DMA_MINALIGN
#define ARCH_HAS_DMA_MINALIGN
#endif
#ifdef ARCH_HAS_DMA_MINALIGN
#define ____dma_from_device_aligned __aligned(ARCH_DMA_MINALIGN)
#else
#define ____dma_from_device_aligned
#endif

#define __cacheline_group_begin(GROUP) \
	__u8 __cacheline_group_begin__##GROUP[0]
#define __cacheline_group_end(GROUP) \
	__u8 __cacheline_group_end__##GROUP[0]
#define __dma_from_device_group_begin(GROUP)			\
	__cacheline_group_begin(GROUP) ____dma_from_device_aligned
#define __dma_from_device_group_end(GROUP)			\
	__cacheline_group_end(GROUP) ____dma_from_device_aligned
struct virtio_input_event {
	__le16 type;
	__le16 code;
	__le32 value;
};
struct virtio_input {
	struct virtio_device       *vdev;
	struct input_dev           *idev;
	char                       name[64];
	char                       serial[64];
	char                       phys[64];
	struct virtqueue           *evt, *sts;
	__dma_from_device_group_begin();
	struct virtio_input_event  evts[63];
	__dma_from_device_group_end();
	spinlock_t                 lock;
	bool                       ready;
};

int main(void)
{
    size_t event_start = offsetof(struct virtio_input, evts);
    size_t event_end = event_start + sizeof(((struct virtio_input *)0)->evts);
    size_t previous_end = offsetof(struct virtio_input, sts) +
                          sizeof(((struct virtio_input *)0)->sts);
    size_t next_start = offsetof(struct virtio_input, lock);
    size_t alignment = DMA_ALIGN;
    bool start_isolated = previous_end &&
        ((previous_end - 1) / alignment != event_start / alignment);
    bool end_isolated = event_end &&
        ((event_end - 1) / alignment != next_start / alignment);
    printf("%zu %zu %zu %zu %zu %d %d\n", previous_end, event_start,
           event_end, next_start, sizeof(struct virtio_input),
           start_isolated, end_isolated);
    return 0;
}
