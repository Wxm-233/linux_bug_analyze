"""Emit the frozen historical mode slice; never read oracle/result files."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "config_contract_20261010/raw/01_drivers__i3c__master__mipi-i3c-hci__core.c"
OLD_SHA = "c3f534d1da90a4d13a75d841523b296d1bf54fb1183e135ff0511fd3693603bd"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    raw = OLD.read_bytes()
    assert sha(raw) == OLD_SHA
    lines = raw.decode().splitlines(keepends=True)
    original = "".join(lines[662:685])
    assert original.count("CONFIG_BIG_ENDIAN") == 1
    counterpart = original.replace("CONFIG_BIG_ENDIAN", "CONFIG_CPU_BIG_ENDIAN")
    constants = lines[36] + lines[44]
    assert "0x04" in lines[36] and "BIT(4)" in lines[44]
    folder = HERE / "projection"
    folder.mkdir(exist_ok=False)
    for cpu, fixture in [("BE", "#define CONFIG_CPU_BIG_ENDIAN 1\n"), ("LE", "")]:
        path = folder / "config" / cpu / "generated" / "autoconf.h"
        path.parent.mkdir(parents=True)
        path.write_text("/* Test fixture, NOT a generated historical kernel configuration. */\n" + fixture,
                        encoding="utf-8", newline="\n")
    prefix = r'''/* User-space register projection, not a full kernel initialization. */
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
'''
    wrapper = r'''
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
'''
    suffix = r'''/* END historical mode slice. */
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
                   "@@PREDICATE@@", TEST_CPU_BE ? "BE" : "LE", initial_bit,
                   accept ? "accept" : "reject", IS_ENABLED(@@CONFIG@@),
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
'''
    for predicate, config, body in [("original", "CONFIG_BIG_ENDIAN", original),
                                    ("cpu_attribute", "CONFIG_CPU_BIG_ENDIAN", counterpart)]:
        full = prefix + constants + wrapper + body + suffix.replace("@@PREDICATE@@", predicate).replace("@@CONFIG@@", config)
        (folder / f"mode_{predicate}.c").write_text(full, encoding="utf-8", newline="\n")
    evidence = {
        "parent": "7ff730ca458e841dbcdc87f264d7afe3eaed525e",
        "source": "../config_contract_20261010/raw/01_drivers__i3c__master__mipi-i3c-hci__core.c",
        "source_sha256": OLD_SHA,
        "slice_lines": [663, 685], "slice_text": original,
        "slice_sha256": sha(original.encode()),
        "constants_lines": [37, 45], "constants_text": constants,
        "counterpart_transformation": "one CONFIG_BIG_ENDIAN token replaced by CONFIG_CPU_BIG_ENDIAN within historical slice",
        "fixture_register_base": "0xa5000100",
        "fixture_errno_EOPNOTSUPP": 95,
        "actual_historical_config": "unknown",
        "complete_init_and_data_consumers": "not executed",
        "physical_endianness": "native x86_64; BE/LE are macro fixture labels",
        "generator_reads_oracle_or_results": False,
        "generated_files": {str(p.relative_to(HERE)).replace('\\', '/'): sha(p.read_bytes())
                            for p in sorted(folder.rglob('*')) if p.is_file()},
    }
    (HERE / "source_evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"generated_files": len(evidence['generated_files']), "slice_sha256": evidence['slice_sha256']}))


if __name__ == "__main__":
    main()
