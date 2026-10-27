/* User-space register projection, not a full kernel initialization. */
#include <stdint.h>
#include <stdio.h>
#include "../raw/01_include__linux__kconfig.h"
#if !defined(__x86_64__)
#error This experiment is frozen for native WSL x86_64 user space.
#endif
#if defined(CONFIG_BIG_ENDIAN) || defined(CONFIG_BIG_ENDIAN_MODULE) || defined(CONFIG_CPU_BIG_ENDIAN_MODULE)
#error The experiment requires these config fixtures to remain undefined.
#endif
#if TEST_CPU_BE
#if !defined(CONFIG_CPU_BIG_ENDIAN) || CONFIG_CPU_BIG_ENDIAN != 1
#error BE fixture requires CONFIG_CPU_BIG_ENDIAN equal to 1.
#endif
#else
#ifdef CONFIG_CPU_BIG_ENDIAN
#error LE fixture requires CONFIG_CPU_BIG_ENDIAN undefined.
#endif
#endif
#define BIT(n) (1u << (n)) /* Harness implementation; only BIT(4) is used. */
#define EOPNOTSUPP 95 /* Harness errno number; original symbolic return retained. */
#define HC_CONTROL			0x04
#define HC_CONTROL_DATA_BIG_ENDIAN	BIT(4)

struct fake_hci { struct { int dev; } master; };
static uint32_t model_register, write_request;
static unsigned reads, writes, diagnostics, invalid_access, entered;
static int accepts_write;
static uint32_t reg_read(unsigned offset)
{
    ++reads;
    if (offset != HC_CONTROL) ++invalid_access;
    return model_register;
}
static void reg_write(unsigned offset, uint32_t value)
{
    ++writes;
    if (offset != HC_CONTROL) ++invalid_access;
    write_request = value;
    if (accepts_write) model_register = value;
}
static void dev_err(const void *device, const char *message)
{
    (void)device;
    (void)message;
    ++diagnostics;
}
static int project_mode(struct fake_hci *hci)
{
    uint32_t regval;
    entered = 1;
/* BEGIN unchanged historical lines 663-685 (counterpart replaces one config). */
	/* Make sure our data ordering fits the host's */
	regval = reg_read(HC_CONTROL);
	if (IS_ENABLED(CONFIG_BIG_ENDIAN)) {
		if (!(regval & HC_CONTROL_DATA_BIG_ENDIAN)) {
			regval |= HC_CONTROL_DATA_BIG_ENDIAN;
			reg_write(HC_CONTROL, regval);
			regval = reg_read(HC_CONTROL);
			if (!(regval & HC_CONTROL_DATA_BIG_ENDIAN)) {
				dev_err(&hci->master.dev, "cannot set BE mode\n");
				return -EOPNOTSUPP;
			}
		}
	} else {
		if (regval & HC_CONTROL_DATA_BIG_ENDIAN) {
			regval &= ~HC_CONTROL_DATA_BIG_ENDIAN;
			reg_write(HC_CONTROL, regval);
			regval = reg_read(HC_CONTROL);
			if (regval & HC_CONTROL_DATA_BIG_ENDIAN) {
				dev_err(&hci->master.dev, "cannot clear BE mode\n");
				return -EOPNOTSUPP;
			}
		}
	}
/* END historical mode slice. */
    return 0; /* Local end-of-slice sentinel, NOT hci_init success. */
}
int main(void)
{
    struct fake_hci hci = {0};
    for (unsigned initial_bit = 0; initial_bit < 2; ++initial_bit) {
        for (unsigned accept = 0; accept < 2; ++accept) {
            const uint32_t initial = 0xa5000100u | (initial_bit << 4);
            model_register = initial;
            write_request = reads = writes = diagnostics = invalid_access = entered = 0;
            accepts_write = (int)accept;
            const int rc = project_mode(&hci);
            printf("{\"predicate\":\"%s\",\"cpu_mode\":\"%s\","
                   "\"initial_data_big_endian_bit\":%u,\"write_policy\":\"%s\","
                   "\"host_target\":\"x86_64\",\"selector\":%d,"
                   "\"initial_control_register\":\"0x%08x\","
                   "\"final_control_register\":\"0x%08x\","
                   "\"final_data_big_endian_bit\":%u,\"reg_read_calls\":%u,"
                   "\"reg_write_calls\":%u,\"write_request_values\":[",
                   "original", TEST_CPU_BE ? "BE" : "LE", initial_bit,
                   accept ? "accept" : "reject", IS_ENABLED(CONFIG_BIG_ENDIAN),
                   initial, model_register,
                   (model_register & HC_CONTROL_DATA_BIG_ENDIAN) != 0, reads, writes);
            if (writes) printf("\"0x%08x\"", write_request);
            printf("],\"local_return_value\":%d,\"diagnostics\":%u,"
                   "\"invalid_register_access\":%u,\"mode_region_entered\":%s}\n",
                   rc, diagnostics, invalid_access, entered ? "true" : "false");
        }
    }
    return 0;
}
