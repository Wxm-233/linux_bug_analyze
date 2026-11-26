import sys, time, json
sys.path.insert(0, "/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/bres_20261125")
import bres as B
B._init_worker("riscv")
js = [j for j in B.jobs("riscv") if j[1]["file"].endswith(("/mm/memory.c", "/fs/proc/task_mmu.c", "/mm/mprotect.c"))]
for j in js:
    t0 = time.time()
    b, u, recs, st = B.one(j)
    print(u, round(time.time() - t0, 1), "s", st, {k: sum(1 for r in recs if r["kind"] == k) for k in ("调用", "宏", "常量", "布局", "包装一层")})
    for r in recs:
        if r["F"]["name"] in ("smaps_pmd_entry", "change_pud_range", "zap_pud_range", "insert_page_into_pte_locked") and r["kind"] in ("调用", "宏"):
            print("   ", r["F"]["name"], r["line"], r["kind"], r["iface"], r["bind"]["def"], r["bind"]["basis"], [g["cond"][:40] for g in r["guards"]][:2], r["config"][:1])
print(len(B.jobs("riscv")), "units in riscv")
