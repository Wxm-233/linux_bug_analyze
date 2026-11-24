"""toolfix criteria 三: calibration of the fixed tools. WSL.

    python3 calib_tools.py exh        -> calib_exh.json   (8-bit exhaustive: abstract vs clang concrete)
    python3 calib_tools.py rt         -> calib_rt.json    (two different runtime predicates, fixed vs old evaluator)
    python3 calib_tools.py wt         -> calib_wt.json    (WT micro cases, fixed vs old rng)
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(HERE))
import evalpg as E  # noqa: E402  (fixed copy)

WORK = Path("/root/work/toolfix")

EXPRS = ["x & 0x0f", "x | 0xa0", "x ^ 0x5a", "(unsigned char)~x", "(unsigned char)(x << 3)", "x >> 2", "(unsigned char)(x + 7)",
         "(unsigned char)(x - 3)", "(unsigned char)(0 - x)", "(unsigned char)(3 - x)", "(unsigned char)(x * 3)", "x == 0x40", "x != 3",
         "x < 100", "(x > 0x80) ? x : 0x11", "(unsigned char)((unsigned char)(x << 4) >> 4)", "(unsigned char)((signed char)x >> 1)",
         "(unsigned short)(int)(signed char)x", "!x", "(x & 1) && (x & 2)", "(x | 1) || 0", "(unsigned char)(x + 0)", "(unsigned char)(0 + x)",
         "(unsigned char)(x - 0)", "(unsigned char)((x & 0xf0) | (~x & 0x0f))"]


def load_old(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(Path(path).parent))
    spec.loader.exec_module(m)
    sys.path.pop(0)
    return m


def exh():
    WORK.mkdir(parents=True, exist_ok=True)
    body = "".join(f"unsigned int E{i}(unsigned char x) {{ return (unsigned int)({e}); }}\n" for i, e in enumerate(EXPRS))
    (WORK / "exh.c").write_text(body)
    main = '#include <stdio.h>\n#include "exh.c"\nint main(void){for(int x=0;x<256;x++){' + "".join(
        f'printf("%u ", E{i}((unsigned char)x));' for i in range(len(EXPRS))) + 'printf("\\n");}return 0;}\n'
    (WORK / "exh_main.c").write_text(main)
    subprocess.run(["clang", "-O0", "-w", "-o", str(WORK / "exh_main"), str(WORK / "exh_main.c")], check=True, cwd=WORK)
    conc = [list(map(int, ln.split())) for ln in subprocess.run([str(WORK / "exh_main")], capture_output=True, text=True).stdout.splitlines()]
    funcs = E.dump_unit("x86_64", WORK / "exh.c", ["E"])
    masks = [0xff, 0xf0, 0x0f, 0xaa, 0x00, 0xfe, 0x7f]
    rows, bad = [], 0
    for i, e in enumerate(EXPRS):
        fn = f"E{i}"
        nbad, nclaims = 0, 0
        for k in masks:
            for v in range(256):
                if v & ~k & 0xff:
                    continue                       # canonical: unknown bits zero in v
                it = E.Interp(funcs, 64, {})
                try:
                    out = it.call(fn, [E.BV(8, v, k)])
                except E.Unsupported:
                    continue
                cons = [x for x in range(256) if (x & k) == v]
                for x in cons:
                    c = conc[x][i]
                    known = out.k
                    if known:
                        nclaims += 1
                        if (c & known) != (out.v & known):
                            nbad += 1
        bad += nbad
        rows.append({"expr": e, "claims": nclaims, "contradictions": nbad})
        print(f"{e:55s} claims {nclaims:6d} contradictions {nbad}", flush=True)
    (HERE / "calib_exh.json").write_text(json.dumps({"total_contradictions": bad, "rows": rows}, indent=1, ensure_ascii=False))
    print("TOTAL contradictions", bad)


RT_SRC = r'''
#include <linux/mm.h>
#include <linux/pgtable.h>
int R_two(pte_t pte) { return !!(cpu_feature_enabled(X86_FEATURE_SHSTK) != cpu_feature_enabled(X86_FEATURE_PKU)); }
int R_same(pte_t pte) { return !!(cpu_feature_enabled(X86_FEATURE_SHSTK) != cpu_feature_enabled(X86_FEATURE_SHSTK)); }
'''


def rt():
    WORK.mkdir(parents=True, exist_ok=True)
    p = WORK / "rt.c"
    p.write_text(RT_SRC)
    old = load_old("evalpg_old", CT / "pgassert_20261121/evalpg.py")
    res = {}
    for tag, mod in (("fixed", E), ("old", old)):
        funcs = mod.dump_unit("x86_64", p, ["R_", "_static_cpu_has", "static_cpu_has"])
        res[tag] = {nm: mod.evaluate(funcs, nm, "x86_64") for nm in ("R_two", "R_same")}
        for nm, r in res[tag].items():
            print(tag, nm, r["status"], r.get("runtime"))
    ok = res["fixed"]["R_two"]["status"].startswith("违反") and res["fixed"]["R_same"]["status"].startswith("成立")
    (HERE / "calib_rt.json").write_text(json.dumps({"ok": ok, "results": res}, indent=1, ensure_ascii=False))
    print("RT ok", ok)


WT_SRC = r'''
int W_samewidth(unsigned int a) { int r; r = a; return r; }
unsigned int W_neg(int a) { unsigned int r; r = a; return r; }
unsigned int W_bypass(unsigned long long x, int flag) { if (flag) { if (x > 100) return 0; } return x; }
unsigned int W_reassign_then(unsigned long long x) { if (x <= 100) { x += 1ULL << 40; return x; } return 0; }
unsigned int W_reassign_after(unsigned long long x) { if (x > 100) return 0; x = x * 1000000000000ULL; return x; }
unsigned int W_fit_mask(unsigned long long x) { return x & 0xffff; }
unsigned int W_dom_ok(unsigned long long x) { if (x > 100) return 0; return x; }
'''
WT_CASES = {"W_samewidth": ("A|assign:r|a", 2, "可能超界"), "W_neg": ("A|assign:r|a", 3, "可能超界"),
            "W_bypass": ("A|return:return|x", 4, "可能超界"), "W_reassign_then": ("A|return:return|x", 5, "可能超界"),
            "W_reassign_after": ("A|return:return|x", 6, "可能超界"), "W_fit_mask": ("A|return:return|x", 7, "放得下"),
            "W_dom_ok": ("A|return:return|x", 8, "放得下")}


def wt():
    WORK.mkdir(parents=True, exist_ok=True)
    p = WORK / "wt_micro.c"
    p.write_text(WT_SRC)
    funcs = E.dump_unit("i386", p, ["W_"])
    import rng as R_new
    R_old = load_old("rng_old", CT / "wtrange2_20261121/rng.py")
    out, ok = [], 0
    for nm, (sig, line, want) in WT_CASES.items():
        fn = funcs[nm]
        got_new = R_new.status_for(fn, str(p), line, sig, WT_SRC)
        got_old = R_old.status_for(fn, str(p), line, sig, WT_SRC)
        sn = R_new.overall({"i386": got_new})
        so = R_old.overall({"i386": got_old})
        good = sn == want
        ok += good
        out.append({"func": nm, "expect": want, "fixed": sn, "old": so, "ok": good})
        print(f"{nm:18s} expect {want}  fixed {sn}  old {so}  {'OK' if good else 'MISMATCH'}", flush=True)
    miss = R_new.overall({"i386": [{"status": "放得下"}]}, [["i386_allmod", "解析失败或找不到函数"]])
    out.append({"func": "overall-with-missing-build", "expect": "缺项", "fixed": miss, "ok": miss == "缺项"})
    ok += miss == "缺项"
    print("overall with a missing build ->", miss)
    (HERE / "calib_wt.json").write_text(json.dumps({"ok": ok, "n": len(out), "rows": out}, indent=1, ensure_ascii=False))
    print("WT ok", ok, "/", len(out))


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    {"exh": exh, "rt": rt, "wt": wt}[sys.argv[1]]()
