/* Audit-only reduced C; typedefs deliberately do not enforce endianness. */
typedef unsigned short __u16;
typedef unsigned short __le16;
#define cpu_to_le16(x) __builtin_bswap16(x)
struct device { __u16 value; };
struct encoded_device { __le16 value; };
typedef struct encoded_device encoded_dev;
struct command { __le16 value; } __attribute__((packed));
extern void hci_req_add(void *req, unsigned opcode, unsigned size, const void *data);
void send(struct device *dev)
{
    {
        encoded_dev dev[1] = {{ .value = cpu_to_le16(7) }};
        struct command cp;
        cp.value = dev->value;
        hci_req_add((void *)0, 1, sizeof(cp), &cp);
    }
}
