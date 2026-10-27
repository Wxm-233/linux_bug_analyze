/* Post-read reduced UAPI layout from c3838262^ and c3838262.
 * It checks the documented cast precondition; it is not a driver build or
 * a packet-throughput measurement. Compile with -DFIXED for the repaired form.
 */
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

struct virtio_net_hdr_v1 {
    uint8_t flags;
    uint8_t gso_type;
    uint16_t hdr_len;
    uint16_t gso_size;
    union {
        struct { uint16_t csum_start, csum_offset; };
        struct { uint16_t start, offset; } csum;
        struct { uint16_t segments, dup_acks; } rsc;
    };
    uint16_t num_buffers;
};

struct virtio_net_hdr_v1_hash {
    struct virtio_net_hdr_v1 hdr;
#ifdef FIXED
    uint16_t hash_value_lo;
    uint16_t hash_value_hi;
#else
    uint32_t hash_value;
#endif
    uint16_t hash_report;
    uint16_t padding;
};

struct virtio_net_hdr_v1_hash_tunnel {
    struct virtio_net_hdr_v1_hash hash_hdr;
    uint16_t outer_th_offset;
    uint16_t inner_nh_offset;
};

int main(void)
{
    size_t base_align = _Alignof(struct virtio_net_hdr_v1);
    size_t hash_align = _Alignof(struct virtio_net_hdr_v1_hash);
    size_t tunnel_align = _Alignof(struct virtio_net_hdr_v1_hash_tunnel);
    uintptr_t two_byte_aligned_address = 2;
    int base_accepts = (two_byte_aligned_address & (base_align - 1)) == 0;
    int tunnel_accepts = (two_byte_aligned_address & (tunnel_align - 1)) == 0;
    printf("base_align=%zu hash_align=%zu tunnel_align=%zu "
           "hash_size=%zu tunnel_size=%zu hash_offset=%zu "
           "two_byte_address_base=%d two_byte_address_tunnel=%d\n",
           base_align, hash_align, tunnel_align,
           sizeof(struct virtio_net_hdr_v1_hash),
           sizeof(struct virtio_net_hdr_v1_hash_tunnel),
           offsetof(struct virtio_net_hdr_v1_hash_tunnel, hash_hdr),
           base_accepts, tunnel_accepts);
#ifdef FIXED
    return base_align != 2 || hash_align != 2 || tunnel_align != 2 ||
           !base_accepts || !tunnel_accepts;
#else
    return base_align != 2 || hash_align != 4 || tunnel_align != 4 ||
           !base_accepts || tunnel_accepts;
#endif
}
