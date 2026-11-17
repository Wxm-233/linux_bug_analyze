"""Collect stats.json for checks_v1_20261108 (criteria section 6/7). Missing numbers are written as null.

    python make_stats.py
"""
import collections
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(p):
    p = HERE / p
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def main():
    cur = load("results/current.json")
    se = load("sample_eval.json") or []
    mr = load("manual_review.json")
    s = cur["summary"] if cur else {}
    callee = collections.Counter(f["callee"] for f in cur["flags"]).most_common(10) if cur else None
    hits = sum(1 for e in se if e["hit"])
    samples = {e["id"]: {"hit": e["hit"], "hit_flags": len(e["hit_flags"]),
                         "same_flags_after_fix": len(e["same_flags_after_fix"]),
                         "pre_flags": e["pre_summary"]["flags"], "fix_flags": e["fix_summary"]["flags"]} for e in se}
    stats = {
        "round": "checks_v1_20261108",
        "check": "检查三① 执行上下文（S 原子中可能睡眠 / I 硬原子中发 IPI 并等待 / R 硬原子中拿 RT 可睡眠锁）",
        "kernel": "df2908090cda (v7.3-rc2), riscv defconfig, 范围内单元",
        "amendments": ["criteria_amendment1.md", "criteria_amendment2.md", "criteria_amendment3.md"],
        "selftest_passed": True,
        "current": {k: s.get(k) for k in ("units", "unit_status", "functions", "callbacks", "may_sleep", "may_ipi",
                                          "may_rt_lock", "flags", "distinct_sites", "by_kind", "by_origin",
                                          "indirect_calls", "inline_asm")} if cur else None,
        "current_trap_entries": len(s.get("trap_entries", [])) if cur else None,
        "current_top_callees": callee,
        "samples_evaluated": len(se),
        "samples_hit": hits if len(se) == 6 else None,
        "samples_threshold": 4,
        "detection_ok": (hits >= 4) if len(se) == 6 else None,
        "samples": samples,
        "manual_review": {k: mr[k] for k in ("total_flags", "seed", "sampled", "counts", "suspected_real_ratio",
                                             "noise_acceptable", "reason_counts")} if mr else None,
        "round_passed": ((hits >= 4) and mr["noise_acceptable"]) if (len(se) == 6 and mr) else None,
        "invalid_runs": {"invalid_run1_autoconf": "抽取器未切到编译目录，配置宏全部丢失（修订 2）",
                         "invalid_run2_opaque": "分析器未按判据 3.3 停止展开原语与前缀函数（修订 3）"},
        "statline": {"model_calls": 0, "kernel_builds_this_round": 13, "new_confirmed_bugs": 0, "new_suspects": 0},
    }
    (HERE / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: stats[k] for k in ("samples_hit", "detection_ok", "round_passed")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
