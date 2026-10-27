/* Original historical init4/request functions and skb_put_data.
 * Allocator, skb storage/cb, skb_put, and queue are explicit user-mode fixtures.
 * No req_run, synchronization, response, controller, or hardware execution. */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <assert.h>
#include <errno.h>
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint8_t __u8;
typedef uint16_t __le16;
#define __packed __attribute__((packed))
#define BIT(n) (1UL << (n)) /* fixture bit operation, only HCI_REQ_START is used */
#define GFP_ATOMIC 0 /* allocator ignores flags; not the real kernel GFP value */
#define HCI_COMMAND_HDR_SIZE 3
#define HCI_COMMAND_PKT		0x01
#define HCI_LE_DATA_LEN_EXT		0x20
#define HCI_OP_DELETE_STORED_LINK_KEY	0x0c12
#define HCI_OP_GET_MWS_TRANSPORT_CONFIG	0x140c
#define HCI_OP_LE_SET_DEFAULT_PHY	0x2031
#define HCI_OP_LE_WRITE_DEF_DATA_LEN	0x2024
#define HCI_OP_READ_LOCAL_CODECS	0x100b
#define HCI_OP_READ_SYNC_TRAIN_PARAMS	0x0c77
#define HCI_OP_WRITE_SC_SUPPORT		0x0c7a
#define HCI_PRIMARY	0x00
#define HCI_REQ_START	BIT(0)
#define LMP_LE		0x40
#define LMP_SYNC_TRAIN	0x04
#define bt_cb(skb) ((struct bt_skb_cb *)((skb)->cb))
#define hci_skb_opcode(skb) bt_cb((skb))->hci.opcode
#define hci_skb_pkt_type(skb) bt_cb((skb))->pkt_type
#define lmp_sync_train_capable(dev) ((dev)->features[2][0] & LMP_SYNC_TRAIN)
/* Synthetic IDs go only to false-returning configuration helpers. */
#define HCI_QUIRK_BROKEN_STORED_LINK_KEY 1
#define HCI_SSP_ENABLED 2
typedef struct { u8 b[6]; } bdaddr_t;
static const bdaddr_t fixture_zero_address={{0}};
#define BDADDR_ANY (&fixture_zero_address)
static inline void bacpy(bdaddr_t *dst,const bdaddr_t *src) { memcpy(dst,src,sizeof(*dst)); }
struct hci_command_hdr {
	__le16	opcode;		/* OCF & OGF */
	__u8	plen;
} __packed;
struct hci_cp_delete_stored_link_key {
	bdaddr_t bdaddr;
	__u8     delete_all;
} __packed;
struct hci_cp_le_write_def_data_len {
	__le16	tx_len;
	__le16	tx_time;
} __packed;
struct hci_cp_le_set_default_phy {
	__u8    all_phys;
	__u8    tx_phys;
	__u8    rx_phys;
} __packed;
_Static_assert(sizeof(struct hci_command_hdr)==3,"HCI header size");
_Static_assert(offsetof(struct hci_command_hdr,opcode)==0,"header opcode offset");
_Static_assert(offsetof(struct hci_command_hdr,plen)==2,"header length offset");
_Static_assert(sizeof(struct hci_cp_le_write_def_data_len)==4,"target payload size");
_Static_assert(offsetof(struct hci_cp_le_write_def_data_len,tx_len)==0,"payload length offset");
_Static_assert(offsetof(struct hci_cp_le_write_def_data_len,tx_time)==2,"payload time offset");
struct hci_dev {
    u8 dev_type,features[3][8],le_features[8],commands[64];
    unsigned long quirks;
    u16 le_max_tx_len,le_max_tx_time;
    u8 le_tx_def_phys,le_rx_def_phys;
    char name[16];
};
/* Minimal fields for original macros; no real kernel cb/storage layout claim. */
struct bt_skb_cb { u8 pkt_type; struct {u16 opcode;u8 req_flags,req_event;} hci; };
struct sk_buff { unsigned char storage[64]; unsigned int len,capacity; unsigned char cb[64] __attribute__((aligned(8))); };
struct sk_buff_head { struct sk_buff *tail; unsigned int count; };
struct hci_request {
	struct hci_dev		*hdev;
	struct sk_buff_head	cmd_q;

	/* If something goes wrong when building the HCI request, the error
	 * value is stored in this field.
	 */
	int			err;
};
struct trace {
    int allocation_fail;
    unsigned int add_attempt_count,allocation_call_count,allocation_failure_count;
    unsigned int header_reservation_count,payload_reservation_count,payload_copy_completed_count;
    unsigned int queue_mock_enqueue_count,error_log_count,helper_stub_calls;
    unsigned int current_opcode,attempt_plen,all_add_opcodes[16],all_add_count;
    unsigned int queued_length,queued_pkt_type,queued_opcode,queued_req_flags,queued_req_event;
    unsigned char copy_header[3],copy_payload[4],queue_header[3],queue_payload[4],copy_command[7],queue_command[7];
    struct sk_buff fixture_skb;
};
static struct trace *active;
static inline __le16 cpu_to_le16(u16 value) {
#if __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
    return __builtin_bswap16(value);
#else
    return value;
#endif
}
/* Instrument the unchanged original add_ev debug call before req.err guard.
 * The exact format plus the target opcode distinguish it from prepare debug. */
static void trace_debug(const char *format,...) {
    va_list ap;va_start(ap,format);
    if(strcmp(format,"%s opcode 0x%4.4x plen %d")==0) {
        (void)va_arg(ap,const char *);
        unsigned int opcode=(unsigned int)va_arg(ap,int);
        unsigned int plen=va_arg(ap,unsigned int);
        assert(active->all_add_count<16);
        active->all_add_opcodes[active->all_add_count++]=opcode;
        active->current_opcode=opcode;
        if(opcode==HCI_OP_LE_WRITE_DEF_DATA_LEN) {++active->add_attempt_count;active->attempt_plen=plen;}
    } else if(strcmp(format,"skb len %d")==0) {
        (void)va_arg(ap,unsigned int);
        if(active->current_opcode==HCI_OP_LE_WRITE_DEF_DATA_LEN) {
            /* This original prepare debug follows the completed original
             * skb_put_data memcpy. Snapshot bytes without modifying them. */
            assert(active->fixture_skb.len==7);
            memcpy(active->copy_header,active->fixture_skb.storage,3);
            memcpy(active->copy_payload,active->fixture_skb.storage+3,4);
            memcpy(active->copy_command,active->fixture_skb.storage,7);
            ++active->payload_copy_completed_count;
        }
    } else assert(0 && "unexpected original debug format");
    va_end(ap);
}
#define BT_DBG(...) trace_debug(__VA_ARGS__)
static void bt_dev_err(struct hci_dev *hdev,const char *format,u16 opcode) {
    (void)hdev;(void)format;
    if(opcode==HCI_OP_LE_WRITE_DEF_DATA_LEN) ++active->error_log_count;
}
/* Deterministic allocator fault injection. It does not call alloc_skb. */
static struct sk_buff *bt_skb_alloc(unsigned int len,int flags) {
    (void)flags;assert(active->current_opcode==HCI_OP_LE_WRITE_DEF_DATA_LEN);assert(len==7);
    ++active->allocation_call_count;
    if(active->allocation_fail) {++active->allocation_failure_count;return NULL;}
    memset(&active->fixture_skb,0,sizeof(active->fixture_skb));
    active->fixture_skb.capacity=len;
    return &active->fixture_skb;
}
/* Contiguous bounded storage reservation. Original skb_put_data below performs
 * the payload memcpy. These counters record reservation separately from copy. */
static void *skb_put(struct sk_buff *skb,unsigned int len) {
    assert(skb==&active->fixture_skb);assert(skb->len+len<=skb->capacity);
    if(skb->len==0) {assert(len==3);++active->header_reservation_count;}
    else {assert(skb->len==3 && len==4);++active->payload_reservation_count;}
    void *result=skb->storage+skb->len;skb->len+=len;return result;
}
static inline void *skb_put_data(struct sk_buff *skb, const void *data,
				 unsigned int len)
{
	void *tmp = skb_put(skb, len);

	memcpy(tmp, data, len);

	return tmp;
}
static int skb_queue_empty(const struct sk_buff_head *queue) { return queue->count==0; }
/* Local queue mock records metadata and the exact header/payload bytes. */
static void skb_queue_tail(struct sk_buff_head *queue,struct sk_buff *skb) {
    assert(skb==&active->fixture_skb);assert(skb->len==7);
    assert(hci_skb_opcode(skb)==HCI_OP_LE_WRITE_DEF_DATA_LEN);
    queue->tail=skb;++queue->count;++active->queue_mock_enqueue_count;
    active->queued_length=skb->len;active->queued_pkt_type=hci_skb_pkt_type(skb);
    active->queued_opcode=hci_skb_opcode(skb);active->queued_req_flags=bt_cb(skb)->hci.req_flags;
    active->queued_req_event=bt_cb(skb)->hci.req_event;
    memcpy(active->queue_header,skb->storage,3);memcpy(active->queue_payload,skb->storage+3,4);
    memcpy(active->queue_command,skb->storage,7);
}
struct sk_buff *hci_prepare_cmd(struct hci_dev *hdev, u16 opcode, u32 plen,
				const void *param)
{
	int len = HCI_COMMAND_HDR_SIZE + plen;
	struct hci_command_hdr *hdr;
	struct sk_buff *skb;

	skb = bt_skb_alloc(len, GFP_ATOMIC);
	if (!skb)
		return NULL;

	hdr = skb_put(skb, HCI_COMMAND_HDR_SIZE);
	hdr->opcode = cpu_to_le16(opcode);
	hdr->plen   = plen;

	if (plen)
		skb_put_data(skb, param, plen);

	BT_DBG("skb len %d", skb->len);

	hci_skb_pkt_type(skb) = HCI_COMMAND_PKT;
	hci_skb_opcode(skb) = opcode;

	return skb;
}
void hci_req_add_ev(struct hci_request *req, u16 opcode, u32 plen,
		    const void *param, u8 event)
{
	struct hci_dev *hdev = req->hdev;
	struct sk_buff *skb;

	BT_DBG("%s opcode 0x%4.4x plen %d", hdev->name, opcode, plen);

	/* If an error occurred during request building, there is no point in
	 * queueing the HCI command. We can simply return.
	 */
	if (req->err)
		return;

	skb = hci_prepare_cmd(hdev, opcode, plen, param);
	if (!skb) {
		bt_dev_err(hdev, "no memory for command (opcode 0x%4.4x)",
			   opcode);
		req->err = -ENOMEM;
		return;
	}

	if (skb_queue_empty(&req->cmd_q))
		bt_cb(skb)->hci.req_flags |= HCI_REQ_START;

	bt_cb(skb)->hci.req_event = event;

	skb_queue_tail(&req->cmd_q, skb);
}
void hci_req_add(struct hci_request *req, u16 opcode, u32 plen,
		 const void *param)
{
	hci_req_add_ev(req, opcode, plen, param, 0);
}
/* Non-target capability/configuration helpers are false/no-op stubs. */
static int test_bit(unsigned int n,const unsigned long *p) { (void)n;(void)p;++active->helper_stub_calls;return 0; }
static int hci_dev_test_flag(struct hci_dev *hdev,unsigned int flag) { (void)hdev;(void)flag;++active->helper_stub_calls;return 0; }
static int bredr_sc_enabled(struct hci_dev *hdev) { (void)hdev;++active->helper_stub_calls;return 0; }
static void hci_set_event_mask_page_2(struct hci_request *req) { (void)req;++active->helper_stub_calls; }
static int hci_init4_req(struct hci_request *req, unsigned long opt)
{
	struct hci_dev *hdev = req->hdev;

	/* Some Broadcom based Bluetooth controllers do not support the
	 * Delete Stored Link Key command. They are clearly indicating its
	 * absence in the bit mask of supported commands.
	 *
	 * Check the supported commands and only if the the command is marked
	 * as supported send it. If not supported assume that the controller
	 * does not have actual support for stored link keys which makes this
	 * command redundant anyway.
	 *
	 * Some controllers indicate that they support handling deleting
	 * stored link keys, but they don't. The quirk lets a driver
	 * just disable this command.
	 */
	if (hdev->commands[6] & 0x80 &&
	    !test_bit(HCI_QUIRK_BROKEN_STORED_LINK_KEY, &hdev->quirks)) {
		struct hci_cp_delete_stored_link_key cp;

		bacpy(&cp.bdaddr, BDADDR_ANY);
		cp.delete_all = 0x01;
		hci_req_add(req, HCI_OP_DELETE_STORED_LINK_KEY,
			    sizeof(cp), &cp);
	}

	/* Set event mask page 2 if the HCI command for it is supported */
	if (hdev->commands[22] & 0x04)
		hci_set_event_mask_page_2(req);

	/* Read local codec list if the HCI command is supported */
	if (hdev->commands[29] & 0x20)
		hci_req_add(req, HCI_OP_READ_LOCAL_CODECS, 0, NULL);

	/* Get MWS transport configuration if the HCI command is supported */
	if (hdev->commands[30] & 0x08)
		hci_req_add(req, HCI_OP_GET_MWS_TRANSPORT_CONFIG, 0, NULL);

	/* Check for Synchronization Train support */
	if (lmp_sync_train_capable(hdev))
		hci_req_add(req, HCI_OP_READ_SYNC_TRAIN_PARAMS, 0, NULL);

	/* Enable Secure Connections if supported and configured */
	if (hci_dev_test_flag(hdev, HCI_SSP_ENABLED) &&
	    bredr_sc_enabled(hdev)) {
		u8 support = 0x01;

		hci_req_add(req, HCI_OP_WRITE_SC_SUPPORT,
			    sizeof(support), &support);
	}

	/* Set Suggested Default Data Length to maximum if supported */
	if (hdev->le_features[0] & HCI_LE_DATA_LEN_EXT) {
		struct hci_cp_le_write_def_data_len cp;

		cp.tx_len = cpu_to_le16(hdev->le_max_tx_len);
		cp.tx_time = cpu_to_le16(hdev->le_max_tx_time);
		hci_req_add(req, HCI_OP_LE_WRITE_DEF_DATA_LEN, sizeof(cp), &cp);
	}

	/* Set Default PHY parameters if command is supported */
	if (hdev->commands[35] & 0x20) {
		struct hci_cp_le_set_default_phy cp;

		cp.all_phys = 0x00;
		cp.tx_phys = hdev->le_tx_def_phys;
		cp.rx_phys = hdev->le_rx_def_phys;

		hci_req_add(req, HCI_OP_LE_SET_DEFAULT_PHY, sizeof(cp), &cp);
	}

	return 0;
}
static void hex_or_null(const unsigned char *bytes,size_t len,int present) {
    if(!present) {printf("null");return;}
    putchar('"');for(size_t i=0;i<len;++i) printf("%02x",(unsigned int)bytes[i]);putchar('"');
}
static void emit(int req_err_initial,int allocation_fail,int init4_result,const struct hci_request *req,const struct hci_dev *hdev) {
    printf("{\"kind\":\"row\",\"variant\":\"fix\",\"req_err_initial\":%d,\"allocation_configuration\":\"%s\",\"init4_return_value\":%d,\"req_err_after\":%d,\"primary\":true,\"lmp_le_capability\":true,\"data_length_extension\":true,\"host_values\":[%u,%u],\"target_opcode\":%u,\"attempt_plen\":%u,\"add_attempt_count\":%u,\"allocation_call_count\":%u,\"allocation_failure_count\":%u,\"header_reservation_count\":%u,\"payload_reservation_count\":%u,\"payload_copy_completed_count\":%u,\"queue_mock_enqueue_count\":%u,\"mock_queue_length\":%u,\"error_log_count\":%u,\"helper_stub_calls\":%u,\"all_add_attempt_opcodes\":[",
        req_err_initial,allocation_fail?"failure":"success",init4_result,req->err,hdev->le_max_tx_len,hdev->le_max_tx_time,HCI_OP_LE_WRITE_DEF_DATA_LEN,active->attempt_plen,active->add_attempt_count,active->allocation_call_count,active->allocation_failure_count,active->header_reservation_count,active->payload_reservation_count,active->payload_copy_completed_count,active->queue_mock_enqueue_count,req->cmd_q.count,active->error_log_count,active->helper_stub_calls);
    for(unsigned int i=0;i<active->all_add_count;++i) printf("%s%u",i?",":"",active->all_add_opcodes[i]);
    printf("],\"copy_header_hex\":");hex_or_null(active->copy_header,3,active->payload_copy_completed_count);
    printf(",\"copy_payload_hex\":");hex_or_null(active->copy_payload,4,active->payload_copy_completed_count);
    printf(",\"copy_command_hex\":");hex_or_null(active->copy_command,7,active->payload_copy_completed_count);
    printf(",\"queue_mock_header_hex\":");hex_or_null(active->queue_header,3,active->queue_mock_enqueue_count);
    printf(",\"queue_mock_payload_hex\":");hex_or_null(active->queue_payload,4,active->queue_mock_enqueue_count);
    printf(",\"queue_mock_command_hex\":");hex_or_null(active->queue_command,7,active->queue_mock_enqueue_count);
    printf(",\"queued_length\":%u,\"queued_packet_type\":%u,\"queued_opcode\":%u,\"queued_req_flags\":%u,\"queued_req_event\":%u,\"req_run_executed\":false}\n",active->queued_length,active->queued_pkt_type,active->queued_opcode,active->queued_req_flags,active->queued_req_event);
}
int main(void) {
    u16 marker=0x0102;unsigned char marker_bytes[2];memcpy(marker_bytes,&marker,2);
    const char *order=marker_bytes[0]==1 && marker_bytes[1]==2?"big":marker_bytes[0]==2 && marker_bytes[1]==1?"little":"unknown";
    assert(strcmp(order,"unknown")!=0);
#if __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
    assert(strcmp(order,"big")==0);
#else
    assert(strcmp(order,"little")==0);
#endif
    printf("{\"kind\":\"meta\",\"variant\":\"fix\",\"actual_host_order\":\"%s\",\"payload_size\":%zu,\"header_size\":%zu,\"target_opcode\":%u}\n",order,sizeof(struct hci_cp_le_write_def_data_len),sizeof(struct hci_command_hdr),HCI_OP_LE_WRITE_DEF_DATA_LEN);
    for(int error=0;error<=1;++error)
        for(int failure=0;failure<=1;++failure) {
            struct trace trace={.allocation_fail=failure};active=&trace;
            struct hci_dev device={0};struct hci_dev *hdev=&device;
            hdev->dev_type=HCI_PRIMARY;hdev->features[0][4]=LMP_LE;hdev->le_features[0]=HCI_LE_DATA_LEN_EXT;
hdev->le_max_tx_len = 0x001b;
hdev->le_max_tx_time = 0x0148;
            int initial_error=error?-EIO:0;
            struct hci_request request={.hdev=hdev,.err=initial_error};
            int result=hci_init4_req(&request,0);
            emit(initial_error,failure,result,&request,hdev);
        }
    return 0;
}
