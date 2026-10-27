"""Check two historical CPU-hotplug producer/consumer ordering contracts.

The topology check compiles the original kernel function bodies with small
cacheinfo/topology doubles. The Hyper-V check projects callback order from
the historical enum and registration source. Neither boots a kernel.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path


TOPO_FIX = "3fcbf1c77d089fcf0331fd8f3cbbe6c436a3edbd"
HV_FIX = "52ae076c3a9b366b6fa9f7c7e67aed8b28716ed9"


def git_file(root: Path, revision: str, path: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), "show", f"{revision}:{path}"], text=True
    )


def extract(source: str, signature: str) -> str:
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 0
    for pos in range(opening, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[start : pos + 1]
    raise ValueError(f"unbalanced function: {signature}")


C_PREFIX = r"""
#include <stdbool.h>
#include <stdio.h>
#define CACHE_ID 1
#define CONFIG_OF 1
#define CONFIG_ACPI 0
#define IS_ENABLED(x) (x)
#define pr_info(...) ((void)0)
struct cpumask { unsigned int bits; };
struct cpu_topology {
    int package_id, cluster_id, core_id;
    struct cpumask llc_sibling, core_sibling, cluster_sibling, thread_sibling;
};
struct cacheinfo { int level, attributes, id; void *fw_token; };
static struct cpu_topology cpu_topology[2];
static struct cacheinfo leaves[2][1];
static int nleaves[2], planned_id[2], fail_detection, detection_calls;
static unsigned int online_mask;
#define cache_leaves(cpu) (nleaves[(cpu)])
#define per_cpu_cacheinfo_idx(cpu, index) (&leaves[(cpu)][(index)])
#define for_each_online_cpu(cpu) for ((cpu) = 0; (cpu) < 2; ++(cpu)) if (online_mask & (1U << (cpu)))
#define cpumask_set_cpu(cpu, mask) ((mask)->bits |= (1U << (cpu)))
static int detect_cache_attributes(unsigned int cpu)
{
    ++detection_calls;
    if (fail_detection) return -1;
    nleaves[cpu] = 1;
    leaves[cpu][0] = (struct cacheinfo){.level = 3, .attributes = CACHE_ID, .id = planned_id[cpu]};
    return 0;
}
"""


C_MAIN = r"""
int main(void)
{
    const char *names[] = {"rehotplug_shared", "already_ready", "different_llc", "detection_failure"};
    for (int k = 0; k < 4; ++k) {
        cpu_topology[0] = (struct cpu_topology){.package_id=0, .cluster_id=0, .core_id=0, .llc_sibling={1}};
        cpu_topology[1] = (struct cpu_topology){.package_id=0, .cluster_id=0, .core_id=1, .llc_sibling={2}};
        planned_id[0] = 7;
        planned_id[1] = k == 2 ? 9 : 7;
        leaves[0][0] = (struct cacheinfo){.level=3, .attributes=CACHE_ID, .id=7};
        nleaves[0] = 1;
        nleaves[1] = (k == 1 || k == 2) ? 1 : 0;
        if (nleaves[1]) leaves[1][0] = (struct cacheinfo){.level=3, .attributes=CACHE_ID, .id=planned_id[1]};
        fail_detection = k == 3;
        detection_calls = 0;
        online_mask = 1; /* CPU 1 is starting; CPU 0 is already online. */
        update_siblings_masks(1);
        printf("%s,%u,%u,%d,%d\n", names[k], cpu_topology[0].llc_sibling.bits,
               cpu_topology[1].llc_sibling.bits, nleaves[1], detection_calls);
    }
    return 0;
}
"""


def run_topology(root: Path) -> dict:
    old_topology = git_file(root, TOPO_FIX + "^", "drivers/base/arch_topology.c")
    fixed_topology = git_file(root, TOPO_FIX, "drivers/base/arch_topology.c")
    cache_source = git_file(root, TOPO_FIX, "drivers/base/cacheinfo.c")
    assert cache_source == git_file(root, TOPO_FIX + "^", "drivers/base/cacheinfo.c")
    shared = "\n\n".join(
        extract(cache_source, signature)
        for signature in (
            "static inline bool cache_leaves_are_shared(",
            "bool last_level_cache_is_valid(",
            "bool last_level_cache_is_shared(",
        )
    )
    old = extract(old_topology, "void update_siblings_masks(")
    fixed = extract(fixed_topology, "void update_siblings_masks(")
    assert "detect_cache_attributes(cpuid)" not in old
    assert fixed.index("detect_cache_attributes(cpuid)") < fixed.index("for_each_online_cpu(cpu)")
    late = old[:-1] + "\tdetect_cache_attributes(cpuid);\n}"
    results = {}
    with tempfile.TemporaryDirectory(prefix="hotplug-order-") as folder:
        directory = Path(folder)
        for name, body in (("old", old), ("fixed", fixed), ("late_prepare_mutant", late)):
            source = directory / f"{name}.c"
            binary = directory / name
            source.write_text(C_PREFIX + shared + "\n" + body + "\n" + C_MAIN)
            compiled = subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter", "-Wno-unused-function", str(source), "-o", str(binary)], capture_output=True, text=True)
            if compiled.returncode:
                raise RuntimeError(compiled.stderr)
            lines = subprocess.check_output([str(binary)], text=True).splitlines()
            results[name] = {}
            for line in lines:
                scenario, mask0, mask1, ready, detects = line.split(",")
                results[name][scenario] = {
                    "cpu0_llc_mask": int(mask0), "cpu1_llc_mask": int(mask1),
                    "cpu1_cache_ready": bool(int(ready)), "detect_calls": int(detects),
                }
    assert results["old"]["rehotplug_shared"]["cpu1_llc_mask"] == 2
    assert results["fixed"]["rehotplug_shared"]["cpu1_llc_mask"] == 3
    assert results["late_prepare_mutant"]["rehotplug_shared"]["cpu1_llc_mask"] == 2
    for version in results:
        assert results[version]["already_ready"]["cpu1_llc_mask"] == 3
        assert results[version]["different_llc"]["cpu1_llc_mask"] == 2
        assert results[version]["detection_failure"]["cpu1_llc_mask"] == 2
    return {"source_commit": TOPO_FIX, "source_functions": ["update_siblings_masks", "cache_leaves_are_shared", "last_level_cache_is_valid", "last_level_cache_is_shared"], "late_prepare_mutant_is_synthetic": True, "results": results}


def run_hyperv(root: Path) -> dict:
    path = "arch/arm64/hyperv/mshyperv.c"
    old = git_file(root, HV_FIX + "^", path)
    fixed = git_file(root, HV_FIX, path)
    enum = git_file(root, HV_FIX, "include/linux/cpuhotplug.h")
    provider = git_file(root, HV_FIX, "drivers/hv/hv_common.c")
    consumer = git_file(root, HV_FIX, "drivers/pci/controller/pci-hyperv.c")
    states = ["CPUHP_AP_HYPERV_ONLINE", "CPUHP_AP_IRQ_AFFINITY_ONLINE", "CPUHP_AP_ONLINE_DYN"]
    positions = {state: enum.index("\t" + state + ",") for state in states}
    assert positions[states[0]] < positions[states[1]] < positions[states[2]]
    registration = re.compile(r"cpuhp_setup_state\((CPUHP_AP_[A-Z_]+),\s*\"arm64/hyperv_init:online\",\s*hv_common_cpu_init,\s*hv_common_cpu_die\)")
    old_state = registration.search(old).group(1)
    fixed_state = registration.search(fixed).group(1)
    assert (old_state, fixed_state) == ("CPUHP_AP_ONLINE_DYN", "CPUHP_AP_HYPERV_ONLINE")
    assert "*inputarg = kmalloc(" in extract(provider, "int hv_common_cpu_init(")
    assert "return 0;" in extract(provider, "int hv_common_cpu_die(")
    assert "kfree" not in extract(provider, "int hv_common_cpu_die(")
    assert "params = *this_cpu_ptr(hyperv_pcpu_input_arg);" in consumer
    assert "memset(params, 0, sizeof(*params));" in consumer
    def projection(state: str) -> dict:
        order = sorted((state, "CPUHP_AP_IRQ_AFFINITY_ONLINE"), key=positions.get)
        ready = False
        observed = None
        for callback in order:
            if callback == state:
                ready = True  # Successful hv_common_cpu_init allocation.
            else:
                observed = ready  # IRQ affinity may reach vPCI's per-CPU input page.
        return {"registration_state": state, "online_order": order,
                "page_ready_at_irq_consumer": observed,
                "offline_page_retained": True}
    old_result, fixed_result = projection(old_state), projection(fixed_state)
    assert not old_result["page_ready_at_irq_consumer"]
    assert fixed_result["page_ready_at_irq_consumer"]
    return {"source_commit": HV_FIX, "state_order": states,
            "producer": "hv_common_cpu_init -> hyperv_pcpu_input_arg",
            "consumer": "pci-hyperv vPCI IRQ retarget -> hyperv_pcpu_input_arg",
            "assumption": "IRQ affinity callback reaches vPCI and allocation succeeds",
            "old": old_result, "fixed": fixed_result}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--linux-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("hotplug_order_result.json"))
    args = parser.parse_args()
    result = {"topology_function_execution": run_topology(args.linux_dir),
              "hyperv_source_order_projection": run_hyperv(args.linux_dir)}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
