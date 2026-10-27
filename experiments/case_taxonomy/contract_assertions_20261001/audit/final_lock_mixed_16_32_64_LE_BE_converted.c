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
struct command { __le16 small; __be32 medium; __le64 large; } __packed;
struct device { __u16 small; __u32 medium; __u64 large; };
_Static_assert(sizeof(((struct command *)0)->small) == 2, "payload field width");
_Static_assert(sizeof(((struct device *)0)->small) == 2, "source field width");
_Static_assert(sizeof(((struct command *)0)->medium) == 4, "payload field width");
_Static_assert(sizeof(((struct device *)0)->medium) == 4, "source field width");
_Static_assert(sizeof(((struct command *)0)->large) == 8, "payload field width");
_Static_assert(sizeof(((struct device *)0)->large) == 8, "source field width");
static struct command ca_produce_actual(struct device *dev) {
struct command cp;
memset(&cp, 0, sizeof(cp));
cp.small=cpu_to_le16(dev->small);
cp.medium=cpu_to_be32(dev->medium);
cp.large=cpu_to_le64(dev->large);
return cp;
}
static struct command ca_produce(int ca_variant, struct device *dev) {
struct command cp;
if (ca_variant == 0) return ca_produce_actual(dev);
memset(&cp, 0, sizeof(cp));
switch (ca_variant) {
case 1:
cp.small = cpu_to_le16(dev->small);
cp.medium = cpu_to_be32(dev->medium);
cp.large = cpu_to_le64(dev->large);
break;
case 2:
cp.small = dev->small;
cp.medium = cpu_to_be32(dev->medium);
cp.large = cpu_to_le64(dev->large);
break;
case 3:
cp.small = cpu_to_le16(dev->small);
cp.medium = dev->medium;
cp.large = cpu_to_le64(dev->large);
break;
case 4:
cp.small = cpu_to_le16(dev->small);
cp.medium = cpu_to_be32(dev->medium);
cp.large = dev->large;
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
printf("{\"kind\":\"layout\",\"program\":\"40e73da9e71684cb\",\"host_endian\":\"%s\",\"size\":%zu}\n", ca_endian, sizeof(struct command));
const char *ca_variants[] = { "actual", "reference", "partial_small", "partial_medium", "partial_large" };
for (int ca_active = 0; ca_active < 3; ++ca_active) {
for (int ca_sample = 0; ca_sample < 3; ++ca_sample) {
uint64_t ca_value = 0;
if (ca_active == 0) { const uint64_t ca_samples[] = {UINT64_C(4660),UINT64_C(43831),UINT64_C(0)}; ca_value = ca_samples[ca_sample]; }
if (ca_active == 1) { const uint64_t ca_samples[] = {UINT64_C(305419896),UINT64_C(3300104727),UINT64_C(0)}; ca_value = ca_samples[ca_sample]; }
if (ca_active == 2) { const uint64_t ca_samples[] = {UINT64_C(81985529216486895),UINT64_C(15466905105610617870),UINT64_C(0)}; ca_value = ca_samples[ca_sample]; }
struct device ca_source_0 = {0}; struct device *dev = &ca_source_0;
if (ca_active == 0) dev->small = (__u16)ca_value;
if (ca_active == 1) dev->medium = (__u32)ca_value;
if (ca_active == 2) dev->large = (__u64)ca_value;
for (int ca_variant = 0; ca_variant < 5; ++ca_variant) {
struct command ca_output = ca_produce(ca_variant, dev);
unsigned char ca_bytes[sizeof(ca_output)]; memcpy(ca_bytes, &ca_output, sizeof(ca_output));
{
const size_t ca_offset = offsetof(struct command, small), ca_width = 2;
const uint64_t ca_expected_value = (uint64_t)dev->small;
uint64_t ca_decoded = ca_decode(ca_bytes + ca_offset, ca_width, 0);
unsigned char ca_expected[8] = {0};
for (size_t ca_j = 0; ca_j < ca_width; ++ca_j) ca_expected[ca_j] = (unsigned char)(ca_expected_value >> (8 * (0 ? ca_width - 1 - ca_j : ca_j)));
int ca_ok = ca_decoded == ca_expected_value && !memcmp(ca_bytes + ca_offset, ca_expected, ca_width);
printf("{\"kind\":\"field_check\",\"program\":\"40e73da9e71684cb\",\"host_endian\":\"%s\",\"variant\":\"%s\",\"case_field\":\"%s\",\"case_index\":%d,\"value\":%" PRIu64 ",\"field\":\"small\",\"offset\":%zu,\"width\":%zu,\"expected_value\":%" PRIu64 ",\"decoded\":%" PRIu64 ",\"actual_bytes\":\"", ca_endian, ca_variants[ca_variant],
(const char *[]) { "small", "medium", "large" }[ca_active], ca_sample, ca_value, ca_offset, ca_width, ca_expected_value, ca_decoded);
ca_hex(ca_bytes + ca_offset, ca_width); printf("\",\"expected_bytes\":\""); ca_hex(ca_expected, ca_width);
printf("\",\"pass\":%s}\n", ca_ok ? "true" : "false");
}
{
const size_t ca_offset = offsetof(struct command, medium), ca_width = 4;
const uint64_t ca_expected_value = (uint64_t)dev->medium;
uint64_t ca_decoded = ca_decode(ca_bytes + ca_offset, ca_width, 1);
unsigned char ca_expected[8] = {0};
for (size_t ca_j = 0; ca_j < ca_width; ++ca_j) ca_expected[ca_j] = (unsigned char)(ca_expected_value >> (8 * (1 ? ca_width - 1 - ca_j : ca_j)));
int ca_ok = ca_decoded == ca_expected_value && !memcmp(ca_bytes + ca_offset, ca_expected, ca_width);
printf("{\"kind\":\"field_check\",\"program\":\"40e73da9e71684cb\",\"host_endian\":\"%s\",\"variant\":\"%s\",\"case_field\":\"%s\",\"case_index\":%d,\"value\":%" PRIu64 ",\"field\":\"medium\",\"offset\":%zu,\"width\":%zu,\"expected_value\":%" PRIu64 ",\"decoded\":%" PRIu64 ",\"actual_bytes\":\"", ca_endian, ca_variants[ca_variant],
(const char *[]) { "small", "medium", "large" }[ca_active], ca_sample, ca_value, ca_offset, ca_width, ca_expected_value, ca_decoded);
ca_hex(ca_bytes + ca_offset, ca_width); printf("\",\"expected_bytes\":\""); ca_hex(ca_expected, ca_width);
printf("\",\"pass\":%s}\n", ca_ok ? "true" : "false");
}
{
const size_t ca_offset = offsetof(struct command, large), ca_width = 8;
const uint64_t ca_expected_value = (uint64_t)dev->large;
uint64_t ca_decoded = ca_decode(ca_bytes + ca_offset, ca_width, 0);
unsigned char ca_expected[8] = {0};
for (size_t ca_j = 0; ca_j < ca_width; ++ca_j) ca_expected[ca_j] = (unsigned char)(ca_expected_value >> (8 * (0 ? ca_width - 1 - ca_j : ca_j)));
int ca_ok = ca_decoded == ca_expected_value && !memcmp(ca_bytes + ca_offset, ca_expected, ca_width);
printf("{\"kind\":\"field_check\",\"program\":\"40e73da9e71684cb\",\"host_endian\":\"%s\",\"variant\":\"%s\",\"case_field\":\"%s\",\"case_index\":%d,\"value\":%" PRIu64 ",\"field\":\"large\",\"offset\":%zu,\"width\":%zu,\"expected_value\":%" PRIu64 ",\"decoded\":%" PRIu64 ",\"actual_bytes\":\"", ca_endian, ca_variants[ca_variant],
(const char *[]) { "small", "medium", "large" }[ca_active], ca_sample, ca_value, ca_offset, ca_width, ca_expected_value, ca_decoded);
ca_hex(ca_bytes + ca_offset, ca_width); printf("\",\"expected_bytes\":\""); ca_hex(ca_expected, ca_width);
printf("\",\"pass\":%s}\n", ca_ok ? "true" : "false");
}
}
}
}
return 0;
}
