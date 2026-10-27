/* Full reviewed entry/init3/init4/reader texts surrounded by explicit stubs.
 * This is request construction in a user-mode fixture, not kernel/controller execution. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <stddef.h>
#include <errno.h>
typedef uint8_t u8;
typedef uint8_t __u8;
typedef uint16_t __u16;
typedef uint16_t __le16;
#define __packed __attribute__((packed))
#define BT_DBG(...) do {} while(0)
#define msecs_to_jiffies(n) (n) /* no real clock/timer */
#define HCI_AMP		0x01
#define HCI_INIT_TIMEOUT	msecs_to_jiffies(10000)	/* 10 seconds */
#define HCI_LE_CHAN_SEL_ALG2		0x40
#define HCI_LE_CONN_PARAM_REQ_PROC	0x02
#define HCI_LE_DATA_LEN_EXT		0x20
#define HCI_LE_ENCRYPTION		0x01
#define HCI_LE_EXT_SCAN_POLICY		0x80
#define HCI_MAX_PAGES	3
#define HCI_OP_DELETE_STORED_LINK_KEY	0x0c12
#define HCI_OP_GET_MWS_TRANSPORT_CONFIG	0x140c
#define HCI_OP_LE_CLEAR_RESOLV_LIST	0x2029
#define HCI_OP_LE_CLEAR_WHITE_LIST	0x2010
#define HCI_OP_LE_READ_ADV_TX_POWER	0x2007
#define HCI_OP_LE_READ_DEF_DATA_LEN	0x2023
#define HCI_OP_LE_READ_MAX_DATA_LEN	0x202f
#define HCI_OP_LE_READ_NUM_SUPPORTED_ADV_SETS	0x203b
#define HCI_OP_LE_READ_RESOLV_LIST_SIZE	0x202a
#define HCI_OP_LE_READ_WHITE_LIST_SIZE	0x200f
#define HCI_OP_LE_SET_DEFAULT_PHY	0x2031
#define HCI_OP_LE_SET_EVENT_MASK	0x2001
#define HCI_OP_LE_WRITE_DEF_DATA_LEN	0x2024
#define HCI_OP_READ_LOCAL_CODECS	0x100b
#define HCI_OP_READ_LOCAL_EXT_FEATURES	0x1004
#define HCI_OP_READ_PAGE_SCAN_ACTIVITY	0x0c1b
#define HCI_OP_READ_PAGE_SCAN_TYPE	0x0c46
#define HCI_OP_READ_STORED_LINK_KEY	0x0c0d
#define HCI_OP_READ_SYNC_TRAIN_PARAMS	0x0c77
#define HCI_OP_WRITE_SC_SUPPORT		0x0c7a
#define HCI_PRIMARY	0x00
#define LMP_LE		0x40
#define LMP_NO_BREDR	0x20
#define LMP_SYNC_TRAIN	0x04
#define lmp_le_capable(dev)        ((dev)->features[0][4] & LMP_LE)
#define lmp_sync_train_capable(dev) ((dev)->features[2][0] & LMP_SYNC_TRAIN)
#define lmp_bredr_capable(dev)     (!((dev)->features[0][4] & LMP_NO_BREDR))
/* Synthetic IDs used only by helpers that always return false. */
#define HCI_SETUP 1
#define HCI_CONFIG 2
#define HCI_SSP_ENABLED 3
#define HCI_QUIRK_BROKEN_STORED_LINK_KEY 4
typedef struct { __u8 b[6]; } bdaddr_t;
static const bdaddr_t zero_address={{0}};
#define BDADDR_ANY (&zero_address)
static void bacpy(bdaddr_t *dst, const bdaddr_t *src) { memcpy(dst,src,sizeof(*dst)); }
struct hci_cp_read_stored_link_key {
	bdaddr_t bdaddr;
	__u8     read_all;
} __packed;
struct hci_cp_read_local_ext_features {
	__u8     page;
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
_Static_assert(sizeof(struct hci_cp_le_write_def_data_len)==4,"payload width");
struct hci_dev {
    __u8 dev_type;
    __u8 features[HCI_MAX_PAGES][8],le_features[8],commands[64],max_page;
    unsigned long quirks;
    __u8 le_tx_def_phys,le_rx_def_phys;
    __u16 le_max_tx_len,le_max_tx_time,le_def_tx_len,le_def_tx_time;
    char name[16];
};
struct hci_request { struct hci_dev *hdev; };
struct sk_buff { unsigned char *data; };
struct trace {
    int early_error;
    unsigned stages[4],stage_count,opcodes[64],opcode_count,target_count;
    struct hci_cp_le_write_def_data_len sent;
    unsigned helper_stub_calls;
};
static struct trace *active;
static __u16 le16_to_cpu(__le16 value) {
#if __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
    return __builtin_bswap16(value);
#else
    return value;
#endif
}
static inline __le16 cpu_to_le16(__u16 value) { return le16_to_cpu(value); }
static void hci_req_add(struct hci_request *req, unsigned opcode, size_t length, const void *parameter) {
    (void)req;
    assert(active->opcode_count<64);
    active->opcodes[active->opcode_count++]=opcode;
    if(opcode==HCI_OP_LE_WRITE_DEF_DATA_LEN) {
        assert(length==sizeof(active->sent) && parameter!=NULL);
        memcpy(&active->sent,parameter,length);
        ++active->target_count;
    }
}
/* False/no-op setup helpers; immutable fixture capabilities and defaults. */
static int test_bit(unsigned n,const unsigned long *p) { (void)n;(void)p;++active->helper_stub_calls;return 0; }
static int hci_dev_test_flag(struct hci_dev *hdev,unsigned f) { (void)hdev;(void)f;++active->helper_stub_calls;return 0; }
static int bredr_sc_enabled(struct hci_dev *hdev) { (void)hdev;++active->helper_stub_calls;return 0; }
static int use_ext_scan(struct hci_dev *hdev) { (void)hdev;++active->helper_stub_calls;return 0; }
static int use_ext_conn(struct hci_dev *hdev) { (void)hdev;++active->helper_stub_calls;return 0; }
static int ext_adv_capable(struct hci_dev *hdev) { (void)hdev;++active->helper_stub_calls;return 0; }
static void hci_setup_event_mask(struct hci_request *req) { (void)req;++active->helper_stub_calls; }
static void hci_setup_link_policy(struct hci_request *req) { (void)req;++active->helper_stub_calls; }
static void hci_set_le_support(struct hci_request *req) { (void)req;++active->helper_stub_calls; }
static void hci_set_event_mask_page_2(struct hci_request *req) { (void)req;++active->helper_stub_calls; }
static void hci_debugfs_create_basic(struct hci_dev *hdev) { (void)hdev;++active->helper_stub_calls; }
static void hci_debugfs_create_common(struct hci_dev *hdev) { (void)hdev;++active->helper_stub_calls; }
static void hci_debugfs_create_bredr(struct hci_dev *hdev) { (void)hdev;++active->helper_stub_calls; }
static void hci_debugfs_create_le(struct hci_dev *hdev) { (void)hdev;++active->helper_stub_calls; }
static int hci_init1_req(struct hci_request *req,unsigned long opt) { (void)req;(void)opt;return 0; }
static int hci_init2_req(struct hci_request *req,unsigned long opt) { (void)req;(void)opt;return 0; }
static int hci_init3_req(struct hci_request *req, unsigned long opt)
{
	struct hci_dev *hdev = req->hdev;
	u8 p;

	hci_setup_event_mask(req);

	if (hdev->commands[6] & 0x20 &&
	    !test_bit(HCI_QUIRK_BROKEN_STORED_LINK_KEY, &hdev->quirks)) {
		struct hci_cp_read_stored_link_key cp;

		bacpy(&cp.bdaddr, BDADDR_ANY);
		cp.read_all = 0x01;
		hci_req_add(req, HCI_OP_READ_STORED_LINK_KEY, sizeof(cp), &cp);
	}

	if (hdev->commands[5] & 0x10)
		hci_setup_link_policy(req);

	if (hdev->commands[8] & 0x01)
		hci_req_add(req, HCI_OP_READ_PAGE_SCAN_ACTIVITY, 0, NULL);

	/* Some older Broadcom based Bluetooth 1.2 controllers do not
	 * support the Read Page Scan Type command. Check support for
	 * this command in the bit mask of supported commands.
	 */
	if (hdev->commands[13] & 0x01)
		hci_req_add(req, HCI_OP_READ_PAGE_SCAN_TYPE, 0, NULL);

	if (lmp_le_capable(hdev)) {
		u8 events[8];

		memset(events, 0, sizeof(events));

		if (hdev->le_features[0] & HCI_LE_ENCRYPTION)
			events[0] |= 0x10;	/* LE Long Term Key Request */

		/* If controller supports the Connection Parameters Request
		 * Link Layer Procedure, enable the corresponding event.
		 */
		if (hdev->le_features[0] & HCI_LE_CONN_PARAM_REQ_PROC)
			events[0] |= 0x20;	/* LE Remote Connection
						 * Parameter Request
						 */

		/* If the controller supports the Data Length Extension
		 * feature, enable the corresponding event.
		 */
		if (hdev->le_features[0] & HCI_LE_DATA_LEN_EXT)
			events[0] |= 0x40;	/* LE Data Length Change */

		/* If the controller supports Extended Scanner Filter
		 * Policies, enable the correspondig event.
		 */
		if (hdev->le_features[0] & HCI_LE_EXT_SCAN_POLICY)
			events[1] |= 0x04;	/* LE Direct Advertising
						 * Report
						 */

		/* If the controller supports Channel Selection Algorithm #2
		 * feature, enable the corresponding event.
		 */
		if (hdev->le_features[1] & HCI_LE_CHAN_SEL_ALG2)
			events[2] |= 0x08;	/* LE Channel Selection
						 * Algorithm
						 */

		/* If the controller supports the LE Set Scan Enable command,
		 * enable the corresponding advertising report event.
		 */
		if (hdev->commands[26] & 0x08)
			events[0] |= 0x02;	/* LE Advertising Report */

		/* If the controller supports the LE Create Connection
		 * command, enable the corresponding event.
		 */
		if (hdev->commands[26] & 0x10)
			events[0] |= 0x01;	/* LE Connection Complete */

		/* If the controller supports the LE Connection Update
		 * command, enable the corresponding event.
		 */
		if (hdev->commands[27] & 0x04)
			events[0] |= 0x04;	/* LE Connection Update
						 * Complete
						 */

		/* If the controller supports the LE Read Remote Used Features
		 * command, enable the corresponding event.
		 */
		if (hdev->commands[27] & 0x20)
			events[0] |= 0x08;	/* LE Read Remote Used
						 * Features Complete
						 */

		/* If the controller supports the LE Read Local P-256
		 * Public Key command, enable the corresponding event.
		 */
		if (hdev->commands[34] & 0x02)
			events[0] |= 0x80;	/* LE Read Local P-256
						 * Public Key Complete
						 */

		/* If the controller supports the LE Generate DHKey
		 * command, enable the corresponding event.
		 */
		if (hdev->commands[34] & 0x04)
			events[1] |= 0x01;	/* LE Generate DHKey Complete */

		/* If the controller supports the LE Set Default PHY or
		 * LE Set PHY commands, enable the corresponding event.
		 */
		if (hdev->commands[35] & (0x20 | 0x40))
			events[1] |= 0x08;        /* LE PHY Update Complete */

		/* If the controller supports LE Set Extended Scan Parameters
		 * and LE Set Extended Scan Enable commands, enable the
		 * corresponding event.
		 */
		if (use_ext_scan(hdev))
			events[1] |= 0x10;	/* LE Extended Advertising
						 * Report
						 */

		/* If the controller supports the LE Extended Create Connection
		 * command, enable the corresponding event.
		 */
		if (use_ext_conn(hdev))
			events[1] |= 0x02;      /* LE Enhanced Connection
						 * Complete
						 */

		/* If the controller supports the LE Extended Advertising
		 * command, enable the corresponding event.
		 */
		if (ext_adv_capable(hdev))
			events[2] |= 0x02;	/* LE Advertising Set
						 * Terminated
						 */

		hci_req_add(req, HCI_OP_LE_SET_EVENT_MASK, sizeof(events),
			    events);

		/* Read LE Advertising Channel TX Power */
		if ((hdev->commands[25] & 0x40) && !ext_adv_capable(hdev)) {
			/* HCI TS spec forbids mixing of legacy and extended
			 * advertising commands wherein READ_ADV_TX_POWER is
			 * also included. So do not call it if extended adv
			 * is supported otherwise controller will return
			 * COMMAND_DISALLOWED for extended commands.
			 */
			hci_req_add(req, HCI_OP_LE_READ_ADV_TX_POWER, 0, NULL);
		}

		if (hdev->commands[26] & 0x40) {
			/* Read LE White List Size */
			hci_req_add(req, HCI_OP_LE_READ_WHITE_LIST_SIZE,
				    0, NULL);
		}

		if (hdev->commands[26] & 0x80) {
			/* Clear LE White List */
			hci_req_add(req, HCI_OP_LE_CLEAR_WHITE_LIST, 0, NULL);
		}

		if (hdev->commands[34] & 0x40) {
			/* Read LE Resolving List Size */
			hci_req_add(req, HCI_OP_LE_READ_RESOLV_LIST_SIZE,
				    0, NULL);
		}

		if (hdev->commands[34] & 0x20) {
			/* Clear LE Resolving List */
			hci_req_add(req, HCI_OP_LE_CLEAR_RESOLV_LIST, 0, NULL);
		}

		if (hdev->le_features[0] & HCI_LE_DATA_LEN_EXT) {
			/* Read LE Maximum Data Length */
			hci_req_add(req, HCI_OP_LE_READ_MAX_DATA_LEN, 0, NULL);

			/* Read LE Suggested Default Data Length */
			hci_req_add(req, HCI_OP_LE_READ_DEF_DATA_LEN, 0, NULL);
		}

		if (ext_adv_capable(hdev)) {
			/* Read LE Number of Supported Advertising Sets */
			hci_req_add(req, HCI_OP_LE_READ_NUM_SUPPORTED_ADV_SETS,
				    0, NULL);
		}

		hci_set_le_support(req);
	}

	/* Read features beyond page 1 if available */
	for (p = 2; p < HCI_MAX_PAGES && p <= hdev->max_page; p++) {
		struct hci_cp_read_local_ext_features cp;

		cp.page = p;
		hci_req_add(req, HCI_OP_READ_LOCAL_EXT_FEATURES,
			    sizeof(cp), &cp);
	}

	return 0;
}
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
static int __hci_req_sync(struct hci_dev *hdev,int (*callback)(struct hci_request *,unsigned long),
                          unsigned long opt,unsigned timeout,void *status) {
    (void)timeout;(void)status;
    unsigned stage=callback==hci_init1_req?1:callback==hci_init2_req?2:callback==hci_init3_req?3:4;
    assert(active->stage_count<4);
    active->stages[active->stage_count++]=stage;
    /* Error injection is before the stage-1 stub callback, not a real timeout. */
    if(stage==1 && active->early_error) return -EIO;
    struct hci_request req={hdev};
    return callback(&req,opt);
}
static int __hci_init(struct hci_dev *hdev)
{
	int err;

	err = __hci_req_sync(hdev, hci_init1_req, 0, HCI_INIT_TIMEOUT, NULL);
	if (err < 0)
		return err;

	if (hci_dev_test_flag(hdev, HCI_SETUP))
		hci_debugfs_create_basic(hdev);

	err = __hci_req_sync(hdev, hci_init2_req, 0, HCI_INIT_TIMEOUT, NULL);
	if (err < 0)
		return err;

	/* HCI_PRIMARY covers both single-mode LE, BR/EDR and dual-mode
	 * BR/EDR/LE type controllers. AMP controllers only need the
	 * first two stages of init.
	 */
	if (hdev->dev_type != HCI_PRIMARY)
		return 0;

	err = __hci_req_sync(hdev, hci_init3_req, 0, HCI_INIT_TIMEOUT, NULL);
	if (err < 0)
		return err;

	err = __hci_req_sync(hdev, hci_init4_req, 0, HCI_INIT_TIMEOUT, NULL);
	if (err < 0)
		return err;

	/* This function is only called when the controller is actually in
	 * configured state. When the controller is marked as unconfigured,
	 * this initialization procedure is not run.
	 *
	 * It means that it is possible that a controller runs through its
	 * setup phase and then discovers missing settings. If that is the
	 * case, then this function will not be called. It then will only
	 * be called during the config phase.
	 *
	 * So only when in setup phase or config phase, create the debugfs
	 * entries and register the SMP channels.
	 */
	if (!hci_dev_test_flag(hdev, HCI_SETUP) &&
	    !hci_dev_test_flag(hdev, HCI_CONFIG))
		return 0;

	hci_debugfs_create_common(hdev);

	if (lmp_bredr_capable(hdev))
		hci_debugfs_create_bredr(hdev);

	if (lmp_le_capable(hdev))
		hci_debugfs_create_le(hdev);

	return 0;
}
static void *hci_sent_cmd_data(struct hci_dev *hdev,unsigned opcode) {
    (void)hdev;
    return opcode==HCI_OP_LE_WRITE_DEF_DATA_LEN && active->target_count?&active->sent:NULL;
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
static void emit(int primary,int le,int extension,int error,int result,struct hci_dev *hdev) {
    printf("{\"kind\":\"row\",\"variant\":\"fix\",\"primary\":%d,\"lmp_le_capability\":%d,\"extension\":%d,\"early_error\":%d,\"result\":%d,\"stages\":[",primary,le,extension,error,result);
    for(unsigned i=0;i<active->stage_count;++i) printf("%s%u",i?",":"",active->stages[i]);
    printf("],\"add_attempt_opcodes\":[");
    for(unsigned i=0;i<active->opcode_count;++i) printf("%s%u",i?",":"",active->opcodes[i]);
    printf("],\"target_add_attempt_count\":%u,\"simulated_target_copy_count\":%u,\"helper_stub_calls\":%u,\"host_values\":[%u,%u],\"reader_values\":[%u,%u],\"payload_hex\":",active->target_count,active->target_count,active->helper_stub_calls,hdev->le_max_tx_len,hdev->le_max_tx_time,hdev->le_def_tx_len,hdev->le_def_tx_time);
    if(active->target_count) {
        putchar('"');
        unsigned char *p=(void *)&active->sent;
        for(size_t i=0;i<sizeof(active->sent);++i) printf("%02x",(unsigned)p[i]);
        putchar('"');
    } else printf("null");
    puts("}");
}
int main(void) {
    __u16 marker=0x0102;unsigned char bytes[2];memcpy(bytes,&marker,2);
    const char *host_order=bytes[0]==1 && bytes[1]==2?"big":bytes[0]==2 && bytes[1]==1?"little":"unknown";
    assert(strcmp(host_order,"unknown")!=0);
#if __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
    assert(strcmp(host_order,"big")==0);
#else
    assert(strcmp(host_order,"little")==0);
#endif
    printf("{\"kind\":\"meta\",\"variant\":\"fix\",\"actual_host_order\":\"%s\",\"payload_bytes\":%zu,\"primary_constant\":%u,\"other_constant\":%u,\"le_mask\":%u,\"extension_mask\":%u}\n",host_order,sizeof(struct hci_cp_le_write_def_data_len),HCI_PRIMARY,HCI_AMP,LMP_LE,HCI_LE_DATA_LEN_EXT);
    for(int primary=0;primary<=1;++primary)
        for(int le=0;le<=1;++le)
            for(int extension=0;extension<=1;++extension)
                for(int error=0;error<=1;++error) {
                    struct trace t={.early_error=error};active=&t;
                    struct hci_dev dev={0};struct hci_dev *hdev=&dev;
                    hdev->dev_type=primary?HCI_PRIMARY:HCI_AMP;
                    hdev->features[0][4]=le?LMP_LE:0;
                    hdev->le_features[0]=extension?HCI_LE_DATA_LEN_EXT:0;
                    hdev->le_def_tx_len=51;hdev->le_def_tx_time=801;
hdev->le_max_tx_len = 0x001b;
hdev->le_max_tx_time = 0x0148;
                    int result=__hci_init(hdev);
                    if(active->target_count) {
                        unsigned char success=0;struct sk_buff skb={&success};
                        hci_cc_le_write_def_data_len(hdev,&skb);
                    }
                    emit(primary,le,extension,error,result,hdev);
                }
    return 0;
}
