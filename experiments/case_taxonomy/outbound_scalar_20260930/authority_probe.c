/* Reduced, host-only projection of two reviewed historical Linux expressions.
 * No kernel objects, Bluetooth controller, or SAS/NVMe device are involved.
 *
 * hci_ll:    old &speed vs fixed &cpu_to_le32(speed) passed as four raw bytes.
 * mpt3sas:  old cpu_to_le32(scsi_bufflen) vs fixed scsi_bufflen compared
 *           with NVME_PRP_PAGE_SIZE * 4, with PAGE_SIZE=4096 and sge<=2.
 */
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
#define HOST_ENDIAN "little"
static uint32_t cpu_to_le32(uint32_t value) { return value; }
#elif __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
#define HOST_ENDIAN "big"
static uint32_t cpu_to_le32(uint32_t value) { return __builtin_bswap32(value); }
#else
#error unsupported host byte order
#endif

#define NVME_PRP_PAGE_SIZE 4096U

static void to_hex(const unsigned char data[4], char out[9])
{
	static const char digits[] = "0123456789abcdef";
	for (unsigned int i = 0; i < 4; ++i) {
		out[2 * i] = digits[data[i] >> 4];
		out[2 * i + 1] = digits[data[i] & 15];
	}
	out[8] = '\0';
}

static void hci_case(uint32_t speed)
{
	unsigned char old_bytes[4], fixed_bytes[4], expected_bytes[4];
	uint32_t speed_le = cpu_to_le32(speed);
	char old_hex[9], fixed_hex[9], expected_hex[9];

	/* __hci_cmd_sync -> hci_prepare_cmd -> skb_put_data is raw copying. */
	memcpy(old_bytes, &speed, sizeof(speed));
	memcpy(fixed_bytes, &speed_le, sizeof(speed_le));
	for (unsigned int i = 0; i < 4; ++i)
		expected_bytes[i] = (unsigned char)(speed >> (8 * i));
	to_hex(old_bytes, old_hex);
	to_hex(fixed_bytes, fixed_hex);
	to_hex(expected_bytes, expected_hex);
	printf("HCI,%u,%s,%s,%s,%u\n", speed, old_hex, fixed_hex,
	       expected_hex, speed);
}

static bool old_build_prp(uint32_t host_length, int sge_count,
			  uint32_t *compared_length)
{
	uint32_t data_length = cpu_to_le32(host_length);
	*compared_length = data_length;
	return !((data_length <= NVME_PRP_PAGE_SIZE * 4U) && (sge_count <= 2));
}

static bool fixed_build_prp(uint32_t host_length, int sge_count)
{
	uint32_t data_length = host_length;
	return !((data_length <= NVME_PRP_PAGE_SIZE * 4U) && (sge_count <= 2));
}

static void mpt_case(uint32_t length, int sge_count)
{
	uint32_t compared_length;
	bool old_result = old_build_prp(length, sge_count, &compared_length);
	bool fixed_result = fixed_build_prp(length, sge_count);
	printf("MPT,%u,%d,%u,%d,%d\n", length, sge_count,
	       compared_length, old_result, fixed_result);
}

int main(void)
{
	static const uint32_t speeds[] = {0U, 115200U, 3000000U};
	static const uint32_t lengths[] = {0U, 4096U, 16384U, 16385U, 65536U};
	printf("META,%s,%zu\n", HOST_ENDIAN, sizeof(uint32_t));
	for (unsigned int i = 0; i < sizeof(speeds) / sizeof(speeds[0]); ++i)
		hci_case(speeds[i]);
	for (unsigned int i = 0; i < sizeof(lengths) / sizeof(lengths[0]); ++i) {
		mpt_case(lengths[i], 2);
		mpt_case(lengths[i], 3);
	}
	return 0;
}
