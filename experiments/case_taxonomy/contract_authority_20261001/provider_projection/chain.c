#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stddef.h>
typedef uint8_t __u8;
typedef uint16_t __u16;
typedef uint16_t __le16;
#define __packed __attribute__((packed))
#define BT_DBG(...) do {} while (0)
#define HCI_OP_LE_WRITE_DEF_DATA_LEN 0x2024
static __u16 le16_to_cpu(__le16 v) {
#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
 return v;
#else
 return __builtin_bswap16(v);
#endif
}
static __le16 cpu_to_le16(__u16 v) { return le16_to_cpu(v); }
struct hci_dev { char name[16]; __u16 le_max_tx_len,le_max_tx_time,le_max_rx_len,le_max_rx_time;
 __u16 le_def_tx_len,le_def_tx_time; };
struct sk_buff { unsigned char *data; };
static void *sent_data;
static void *hci_sent_cmd_data(struct hci_dev *hdev, unsigned opcode) {
 (void)hdev; return opcode == HCI_OP_LE_WRITE_DEF_DATA_LEN ? sent_data : NULL;
}
struct hci_rp_le_read_max_data_len {
	__u8	status;
	__le16	tx_len;
	__le16	tx_time;
	__le16	rx_len;
	__le16	rx_time;
} __packed;
struct hci_cp_le_write_def_data_len {
	__le16	tx_len;
	__le16	tx_time;
} __packed;
static void hci_cc_le_read_max_data_len(struct hci_dev *hdev,
					struct sk_buff *skb)
{
	struct hci_rp_le_read_max_data_len *rp = (void *) skb->data;

	BT_DBG("%s status 0x%2.2x", hdev->name, rp->status);

	if (rp->status)
		return;

	hdev->le_max_tx_len = le16_to_cpu(rp->tx_len);
	hdev->le_max_tx_time = le16_to_cpu(rp->tx_time);
	hdev->le_max_rx_len = le16_to_cpu(rp->rx_len);
	hdev->le_max_rx_time = le16_to_cpu(rp->rx_time);
}
static void hci_cc_le_write_def_data_len(struct hci_dev *hdev,
					 struct sk_buff *skb)
{
	struct hci_cp_le_write_def_data_len *sent;
	__u8 status = *((__u8 *) skb->data);

	BT_DBG("%s status 0x%2.2x", hdev->name, status);

	if (status)
		return;

	sent = hci_sent_cmd_data(hdev, HCI_OP_LE_WRITE_DEF_DATA_LEN);
	if (!sent)
		return;

	hdev->le_def_tx_len = le16_to_cpu(sent->tx_len);
	hdev->le_def_tx_time = le16_to_cpu(sent->tx_time);
}
static void produce_parent(struct hci_dev *hdev, unsigned char *out) {
 struct hci_cp_le_write_def_data_len cp = {0};
 cp.tx_len = hdev->le_max_tx_len;
 cp.tx_time = hdev->le_max_tx_time;
 memcpy(out, &cp, sizeof(cp));
}
static void produce_fix(struct hci_dev *hdev, unsigned char *out) {
 struct hci_cp_le_write_def_data_len cp = {0};
 cp.tx_len = cpu_to_le16(hdev->le_max_tx_len);
 cp.tx_time = cpu_to_le16(hdev->le_max_tx_time);
 memcpy(out, &cp, sizeof(cp));
}

static void state(const char *kind, const char *variant, unsigned i, struct hci_dev *hdev, unsigned char *payload) {
 printf("{\"kind\":\"%s\",\"variant\":\"%s\",\"index\":%u,\"host_values\":[%u,%u,%u,%u],\"reader_values\":[%u,%u],\"payload\":\"",
 kind,variant,i,hdev->le_max_tx_len,hdev->le_max_tx_time,hdev->le_max_rx_len,hdev->le_max_rx_time,hdev->le_def_tx_len,hdev->le_def_tx_time);
 if(payload) for(size_t n=0;n<sizeof(struct hci_cp_le_write_def_data_len);n++) printf("%02x",payload[n]);
 puts("\"}");
}
int main(void) {
 const __u16 values[][4] = {{27,328,27,328},{251,2120,251,2120},{37,901,41,1003}};
 printf("{\"kind\":\"layout\",\"host_endian\":\"%s\",\"rp_size\":%zu,\"cp_size\":%zu,\"cp_offsets\":[%zu,%zu]}\n",
#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
 "little",
#else
 "big",
#endif
 sizeof(struct hci_rp_le_read_max_data_len),sizeof(struct hci_cp_le_write_def_data_len),
 offsetof(struct hci_cp_le_write_def_data_len,tx_len),offsetof(struct hci_cp_le_write_def_data_len,tx_time));
 for(unsigned i=0;i<3;i++) {
  unsigned char response[sizeof(struct hci_rp_le_read_max_data_len)]={0};
  for(unsigned j=0;j<4;j++) { response[1+2*j]=(unsigned char)values[i][j]; response[2+2*j]=(unsigned char)(values[i][j]>>8); }
  for(unsigned v=0;v<2;v++) {
   struct hci_dev hdev={.le_max_tx_len=27,.le_max_tx_time=328,.le_max_rx_len=27,.le_max_rx_time=328,.le_def_tx_len=51,.le_def_tx_time=801};
   struct sk_buff skb={response};
   hci_cc_le_read_max_data_len(&hdev,&skb);
   struct hci_cp_le_write_def_data_len sent;
   if(v==0) produce_parent(&hdev,(unsigned char *)&sent); else produce_fix(&hdev,(unsigned char *)&sent);
   sent_data=&sent; unsigned char status=0; struct sk_buff complete={&status};
   hci_cc_le_write_def_data_len(&hdev,&complete);
   state("chain",v==0?"parent":"fix",i,&hdev,(unsigned char *)&sent);
  }
 }
 struct hci_dev hdev={.le_max_tx_len=27,.le_max_tx_time=328,.le_max_rx_len=27,.le_max_rx_time=328,.le_def_tx_len=51,.le_def_tx_time=801};
 unsigned char response[sizeof(struct hci_rp_le_read_max_data_len)]={1,0x11,0x22,0x33,0x44,0x55,0x66,0x77,0x88};
 struct sk_buff skb={response}; hci_cc_le_read_max_data_len(&hdev,&skb);
 state("provider_error","none",0,&hdev,NULL);
 struct hci_cp_le_write_def_data_len sent={cpu_to_le16(251),cpu_to_le16(2120)};
 sent_data=&sent; unsigned char status=1; struct sk_buff complete={&status};
 hci_cc_le_write_def_data_len(&hdev,&complete); state("reader_error","none",0,&hdev,NULL);
 status=0; sent_data=NULL; hci_cc_le_write_def_data_len(&hdev,&complete);
 state("reader_missing_sent","none",0,&hdev,NULL);
 return 0;
}
