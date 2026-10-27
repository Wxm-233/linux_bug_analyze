"""Parser boundary tests for the post-read LoongArch PMU phase prototype."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] /
                       "experiments" / "case_taxonomy"))
import state_pmu_probe_v2 as probe  # noqa: E402


MAIN = """
static void do_pre_smp_initcalls(void) {
    for (fn = __initcall_start; fn < __initcall0_start; fn++) { }
}
static void do_basic_setup(void) { do_initcalls(); }
static void kernel_init_freeable(void) {
    do_pre_smp_initcalls();
    smp_init();
    do_basic_setup();
}
"""
MAKE = "obj-$(CONFIG_PERF_EVENTS) += perf_event.o perf_regs.o\n"
INIT = ("#define early_initcall(fn) __define_initcall(fn, early)\n"
        "#define pure_initcall(fn) __define_initcall(fn, 0)\n")
SMP = """
static inline void on_each_cpu(smp_call_func_t func, void *info, int wait) {
    on_each_cpu_cond_mask(NULL, func, info, wait, cpu_online_mask);
}
"""


def pmu(kind: str, call: bool = True) -> str:
    body = "on_each_cpu(reset_counters, NULL, 1);" if call else "register_pmu();"
    return ("static void reset_counters(void *arg) { write_counter(0); }\n"
            f"static int init_hw_perf_events(void) {{ {body} return 0; }}\n"
            f"{kind}(init_hw_perf_events);\n")


def evaluate(kind: str, *, call: bool = True, perf: bool = True,
             make: str = MAKE) -> dict:
    sources = {
        "init/main.c": MAIN,
        "arch/loongarch/kernel/perf_event.c": pmu(kind, call),
        "arch/loongarch/kernel/Makefile": make,
        "include/linux/init.h": INIT,
        "include/linux/smp.h": SMP,
    }
    with patch.object(probe, "source", side_effect=lambda _r, _v, p: sources[p]):
        return probe.evaluate(Path("unused"), "0000000", perf_events=perf)


class StatePmuProbeV2Tests(unittest.TestCase):
    def test_multi_object_kbuild_and_early_consumer(self):
        row = evaluate("early_initcall")
        self.assertEqual(row["status"], "hit")
        self.assertEqual(row["phase"], "pre_smp")
        self.assertEqual(len(row["online_consumer_sites"]), 1)

    def test_pure_initcall_is_after_smp(self):
        self.assertEqual(evaluate("pure_initcall")["status"], "normal")

    def test_unknown_initcall_phase_refuses(self):
        row = evaluate("module_init")
        self.assertEqual(row["status"], "insufficient")

    def test_no_online_consumer_refuses(self):
        row = evaluate("early_initcall", call=False)
        self.assertEqual(row["status"], "insufficient")

    def test_perf_events_off_is_not_applicable(self):
        self.assertEqual(evaluate("early_initcall", perf=False)["status"],
                         "not_applicable")

    def test_unrecognized_kbuild_refuses(self):
        row = evaluate("early_initcall", make="obj-y += perf_event.o\n")
        self.assertEqual(row["status"], "insufficient")


if __name__ == "__main__":
    unittest.main()
