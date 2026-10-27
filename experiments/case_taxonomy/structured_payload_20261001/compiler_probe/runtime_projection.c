/* Generated projection of exact reviewed declarations and HCI assignments.
 * Surrounding kernel/sk_buff paths are modeled, not compiled as a kernel TU. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint16_t __u16;
typedef uint16_t __le16;
#define __packed __attribute__((packed))
#define HCI_OP_LE_WRITE_DEF_DATA_LEN 0x2024
struct hci_cp_le_write_def_data_len {
	__le16	tx_len;
	__le16	tx_time;
} __packed;
struct hci_dev {
	__u16		le_max_tx_len;
	__u16		le_max_tx_time;
};
_Static_assert(sizeof(struct hci_cp_le_write_def_data_len) == 4, "HCI payload width");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct hci_dev *)0)->le_max_tx_len), __u16), "host field width");
/* GCC collapses plain typedefs; this assertion documents that endian meaning
 * is NOT a GCC type distinction without Sparse annotations. */
_Static_assert(__builtin_types_compatible_p(__u16, __le16), "plain endian typedefs collapse");
static __le16 cpu_to_le16(__u16 n) {
#if __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
    return __builtin_bswap16(n);
#else
    return n;
#endif
}
struct hci_request { unsigned char data[4]; };
static void hci_req_add(struct hci_request *req, unsigned op, size_t plen, const void *param) {
    assert(op == HCI_OP_LE_WRITE_DEF_DATA_LEN && plen == sizeof(req->data));
    memcpy(req->data, param, plen);
}
static void hci_old(struct hci_request *req, const struct hci_dev *hdev) {
    struct hci_cp_le_write_def_data_len cp;
cp.tx_len = hdev->le_max_tx_len;
cp.tx_time = hdev->le_max_tx_time;
    hci_req_add(req, HCI_OP_LE_WRITE_DEF_DATA_LEN, sizeof(cp), &cp);
}
static void hci_fixed(struct hci_request *req, const struct hci_dev *hdev) {
    struct hci_cp_le_write_def_data_len cp;
cp.tx_len = cpu_to_le16(hdev->le_max_tx_len);
cp.tx_time = cpu_to_le16(hdev->le_max_tx_time);
    hci_req_add(req, HCI_OP_LE_WRITE_DEF_DATA_LEN, sizeof(cp), &cp);
}
static void hci_partial(struct hci_request *req, const struct hci_dev *hdev) {
    struct hci_cp_le_write_def_data_len cp;
cp.tx_len = cpu_to_le16(hdev->le_max_tx_len);
cp.tx_time = hdev->le_max_tx_time;
    hci_req_add(req, HCI_OP_LE_WRITE_DEF_DATA_LEN, sizeof(cp), &cp);
}
static void hex(const unsigned char *p, size_t n) {
    for (size_t i = 0; i < n; ++i) printf("%02x", (unsigned)p[i]);
}
static void put_le32(uint32_t n, unsigned char *p) {
    for (unsigned i=0; i<4; ++i) p[i]=(unsigned char)(n >> (8*i));
}
static uint32_t get_le32(const unsigned char *p) {
    uint32_t n=0;
    for (unsigned i=0; i<4; ++i) n |= (uint32_t)p[i] << (8*i);
    return n;
}
static uint32_t get_host32(const unsigned char *p) {
    /* memcpy deliberately avoids alignment/aliasing assumptions. This only
     * projects numeric representation of the old u32* consumer. */
    uint32_t n; memcpy(&n,p,sizeof(n)); return n;
}
int main(void) {
#if __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
    const char *endian="big";
#else
    const char *endian="little";
#endif
    printf("META,%s,%zu,%zu\n",endian,sizeof(uint16_t),sizeof(uint32_t));
    const struct hci_dev pairs[]={{0x001b,0x0148},{0x1234,0xabcd},{0,0}};
    for (size_t i=0;i<sizeof(pairs)/sizeof(pairs[0]);++i) {
        struct hci_request a,b,c;
        hci_old(&a,&pairs[i]); hci_fixed(&b,&pairs[i]); hci_partial(&c,&pairs[i]);
        printf("HCI,%u,%u,",(unsigned)pairs[i].le_max_tx_len,(unsigned)pairs[i].le_max_tx_time);
        hex(a.data,4); putchar(','); hex(b.data,4); putchar(','); hex(c.data,4); putchar('\n');
    }
    const uint32_t sizes[]={0x12345678,0x00100020,0};
    for(size_t i=0;i<sizeof(sizes)/sizeof(sizes[0]);++i) {
        uint32_t n=sizes[i]; unsigned char host[4],le[4];
        memcpy(host,&n,sizeof(n)); put_le32(n,le);
        printf("CD,%u,%u,%u,%u,%u,",n,get_host32(host),get_le32(le),get_le32(host),get_host32(le));
        hex(host,4); putchar(','); hex(le,4); putchar('\n');
    }
    return 0;
}
