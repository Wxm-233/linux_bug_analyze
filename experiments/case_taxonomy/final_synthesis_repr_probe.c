/* Small representation-only check for the opened idpf and fsl_raid edits.
 * This does not execute either driver, a DMA engine, or the kernel.
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static uint32_t to_le32(uint32_t value)
{
#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
	return value;
#else
	return __builtin_bswap32(value);
#endif
}

static uint32_t to_be32(uint32_t value)
{
#if __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
	return value;
#else
	return __builtin_bswap32(value);
#endif
}

static int check(const char *name, uint32_t value, int little_endian_wire)
{
	uint32_t old_word = value;
	uint32_t fixed_word = little_endian_wire ? to_le32(value) : to_be32(value);
	unsigned char old_bytes[4], fixed_bytes[4], expected[4];
	int old_ok, fixed_ok;

	memcpy(old_bytes, &old_word, sizeof(old_bytes));
	memcpy(fixed_bytes, &fixed_word, sizeof(fixed_bytes));
	if (little_endian_wire) {
		expected[0] = (unsigned char)value;
		expected[1] = (unsigned char)(value >> 8);
		expected[2] = (unsigned char)(value >> 16);
		expected[3] = (unsigned char)(value >> 24);
	} else {
		expected[0] = (unsigned char)(value >> 24);
		expected[1] = (unsigned char)(value >> 16);
		expected[2] = (unsigned char)(value >> 8);
		expected[3] = (unsigned char)value;
	}
	old_ok = !memcmp(old_bytes, expected, sizeof(expected));
	fixed_ok = !memcmp(fixed_bytes, expected, sizeof(expected));
	printf("{\"host\":\"%s\",\"case\":\"%s\",\"value\":%u,"
	       "\"old_matches_wire\":%d,\"fixed_matches_wire\":%d,"
	       "\"old_bytes\":\"%02x%02x%02x%02x\","
	       "\"fixed_bytes\":\"%02x%02x%02x%02x\"}\n",
#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
	       "little",
#else
	       "big",
#endif
	       name, value, old_ok, fixed_ok,
	       old_bytes[0], old_bytes[1], old_bytes[2], old_bytes[3],
	       fixed_bytes[0], fixed_bytes[1], fixed_bytes[2], fixed_bytes[3]);
	return !fixed_ok;
}

int main(void)
{
	int failures = 0;

	/* idpf's old native u32 store versus cpu_to_le32 on a one-byte command. */
	failures += check("idpf_nonzero", 0x5a, 1);
	failures += check("idpf_zero_control", 0, 1);
	/* fsl_raid's old native u32 store versus cpu_to_be32 descriptor fields. */
	failures += check("fsl_raid_nonzero", 0x01020304, 0);
	failures += check("fsl_raid_zero_control", 0, 0);
	return failures ? 1 : 0;
}
