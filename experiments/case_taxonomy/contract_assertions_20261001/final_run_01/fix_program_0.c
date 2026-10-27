/* Conditional source projection; see plan assumptions. */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <inttypes.h>
#include <string.h>
#define __packed __attribute__((packed))
typedef uint16_t u16, __u16, __le16, __be16;
static inline uint16_t cpu_to_le16(uint16_t x) {
#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
return x;
#else
return __builtin_bswap16(x);
#endif
}
static inline uint16_t cpu_to_be16(uint16_t x) {
#if __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
return x;
#else
return __builtin_bswap16(x);
#endif
}
typedef uint32_t u32, __u32, __le32, __be32;
static inline uint32_t cpu_to_le32(uint32_t x) {
#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
return x;
#else
return __builtin_bswap32(x);
#endif
}
static inline uint32_t cpu_to_be32(uint32_t x) {
#if __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
return x;
#else
return __builtin_bswap32(x);
#endif
}
typedef uint64_t u64, __u64, __le64, __be64;
static inline uint64_t cpu_to_le64(uint64_t x) {
#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
return x;
#else
return __builtin_bswap64(x);
#endif
}
static inline uint64_t cpu_to_be64(uint64_t x) {
#if __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
return x;
#else
return __builtin_bswap64(x);
#endif
}
#if __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__ && __BYTE_ORDER__ != __ORDER_BIG_ENDIAN__
#error "unsupported compiler target byte order"
#endif
struct hci_cp_le_write_def_data_len {
	__le16	tx_len;
	__le16	tx_time;
} __packed;
struct hci_dev { __u16 le_max_tx_len; __u16 le_max_tx_time; };
_Static_assert(sizeof(((struct hci_cp_le_write_def_data_len *)0)->tx_len) == 2, "payload field width");
_Static_assert(sizeof(((struct hci_dev *)0)->le_max_tx_len) == 2, "source field width");
_Static_assert(sizeof(((struct hci_cp_le_write_def_data_len *)0)->tx_time) == 2, "payload field width");
_Static_assert(sizeof(((struct hci_dev *)0)->le_max_tx_time) == 2, "source field width");
static struct hci_cp_le_write_def_data_len ca_produce_actual(struct hci_dev *hdev) {
struct hci_cp_le_write_def_data_len cp;
memset(&cp, 0, sizeof(cp));
cp.tx_len = cpu_to_le16(hdev->le_max_tx_len);
cp.tx_time = cpu_to_le16(hdev->le_max_tx_time);
return cp;
}
static struct hci_cp_le_write_def_data_len ca_produce(int ca_variant, struct hci_dev *hdev) {
struct hci_cp_le_write_def_data_len cp;
if (ca_variant == 0) return ca_produce_actual(hdev);
memset(&cp, 0, sizeof(cp));
switch (ca_variant) {
case 1:
cp.tx_len = cpu_to_le16(hdev->le_max_tx_len);
cp.tx_time = cpu_to_le16(hdev->le_max_tx_time);
break;
case 2:
cp.tx_len = hdev->le_max_tx_len;
cp.tx_time = cpu_to_le16(hdev->le_max_tx_time);
break;
case 3:
cp.tx_len = cpu_to_le16(hdev->le_max_tx_len);
cp.tx_time = hdev->le_max_tx_time;
break;
}
return cp;
}
static uint64_t ca_decode(const unsigned char *p, size_t n, int big) {
uint64_t x = 0; for (size_t j = 0; j < n; ++j) x |= ((uint64_t)p[j]) << (8 * (big ? n - 1 - j : j)); return x;
}
static void ca_hex(const unsigned char *p, size_t n) { for (size_t j = 0; j < n; ++j) printf("%02x", (unsigned)p[j]); }
int main(void) {
const char *ca_endian = __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__ ? "big" : "little";
printf("{\"kind\":\"layout\",\"program\":\"0d9d4c42cba663bc\",\"host_endian\":\"%s\",\"size\":%zu}\n", ca_endian, sizeof(struct hci_cp_le_write_def_data_len));
const char *ca_variants[] = { "actual", "reference", "partial_tx_len", "partial_tx_time" };
for (int ca_active = 0; ca_active < 2; ++ca_active) {
for (int ca_sample = 0; ca_sample < 3; ++ca_sample) {
uint64_t ca_value = 0;
if (ca_active == 0) { const uint64_t ca_samples[] = {UINT64_C(4660),UINT64_C(43831),UINT64_C(0)}; ca_value = ca_samples[ca_sample]; }
if (ca_active == 1) { const uint64_t ca_samples[] = {UINT64_C(4660),UINT64_C(43831),UINT64_C(0)}; ca_value = ca_samples[ca_sample]; }
struct hci_dev ca_source_0 = {0}; struct hci_dev *hdev = &ca_source_0;
if (ca_active == 0) hdev->le_max_tx_len = (__u16)ca_value;
if (ca_active == 1) hdev->le_max_tx_time = (__u16)ca_value;
for (int ca_variant = 0; ca_variant < 4; ++ca_variant) {
struct hci_cp_le_write_def_data_len ca_output = ca_produce(ca_variant, hdev);
unsigned char ca_bytes[sizeof(ca_output)]; memcpy(ca_bytes, &ca_output, sizeof(ca_output));
{
const size_t ca_offset = offsetof(struct hci_cp_le_write_def_data_len, tx_len), ca_width = 2;
const uint64_t ca_expected_value = (uint64_t)hdev->le_max_tx_len;
uint64_t ca_decoded = ca_decode(ca_bytes + ca_offset, ca_width, 0);
unsigned char ca_expected[8] = {0};
for (size_t ca_j = 0; ca_j < ca_width; ++ca_j) ca_expected[ca_j] = (unsigned char)(ca_expected_value >> (8 * (0 ? ca_width - 1 - ca_j : ca_j)));
int ca_ok = ca_decoded == ca_expected_value && !memcmp(ca_bytes + ca_offset, ca_expected, ca_width);
printf("{\"kind\":\"field_check\",\"program\":\"0d9d4c42cba663bc\",\"host_endian\":\"%s\",\"variant\":\"%s\",\"case_field\":\"%s\",\"case_index\":%d,\"value\":%" PRIu64 ",\"field\":\"tx_len\",\"offset\":%zu,\"width\":%zu,\"expected_value\":%" PRIu64 ",\"decoded\":%" PRIu64 ",\"actual_bytes\":\"", ca_endian, ca_variants[ca_variant],
(const char *[]) { "tx_len", "tx_time" }[ca_active], ca_sample, ca_value, ca_offset, ca_width, ca_expected_value, ca_decoded);
ca_hex(ca_bytes + ca_offset, ca_width); printf("\",\"expected_bytes\":\""); ca_hex(ca_expected, ca_width);
printf("\",\"pass\":%s}\n", ca_ok ? "true" : "false");
}
{
const size_t ca_offset = offsetof(struct hci_cp_le_write_def_data_len, tx_time), ca_width = 2;
const uint64_t ca_expected_value = (uint64_t)hdev->le_max_tx_time;
uint64_t ca_decoded = ca_decode(ca_bytes + ca_offset, ca_width, 0);
unsigned char ca_expected[8] = {0};
for (size_t ca_j = 0; ca_j < ca_width; ++ca_j) ca_expected[ca_j] = (unsigned char)(ca_expected_value >> (8 * (0 ? ca_width - 1 - ca_j : ca_j)));
int ca_ok = ca_decoded == ca_expected_value && !memcmp(ca_bytes + ca_offset, ca_expected, ca_width);
printf("{\"kind\":\"field_check\",\"program\":\"0d9d4c42cba663bc\",\"host_endian\":\"%s\",\"variant\":\"%s\",\"case_field\":\"%s\",\"case_index\":%d,\"value\":%" PRIu64 ",\"field\":\"tx_time\",\"offset\":%zu,\"width\":%zu,\"expected_value\":%" PRIu64 ",\"decoded\":%" PRIu64 ",\"actual_bytes\":\"", ca_endian, ca_variants[ca_variant],
(const char *[]) { "tx_len", "tx_time" }[ca_active], ca_sample, ca_value, ca_offset, ca_width, ca_expected_value, ca_decoded);
ca_hex(ca_bytes + ca_offset, ca_width); printf("\",\"expected_bytes\":\""); ca_hex(ca_expected, ca_width);
printf("\",\"pass\":%s}\n", ca_ok ? "true" : "false");
}
}
}
}
return 0;
}
