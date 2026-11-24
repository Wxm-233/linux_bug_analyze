"""pgassert criteria 四 (day 9): isolated micro functions checking the evaluator's classification on a real build. WSL.

    python3 calib9.py [build]  -> calib9_<build>.json
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import evalpg as E  # noqa: E402

MICRO = r'''
#include <linux/mm.h>
#include <linux/pgtable.h>
#ifdef CONFIG_ARM64
#define M_AF PTE_AF
#else
#define M_AF _PAGE_ACCESSED
#endif
static inline pte_t m_bad_mkold(pte_t pte) { return __pte(pte_val(pte) | M_AF); }   /* wrong on purpose: sets instead of clearing */
static inline pte_t m_bad_mkclean(pte_t pte) { return pte; }                                   /* wrong on purpose: no-op */
int M_bad_mkold(pte_t pte)     { return !!(pte_young(m_bad_mkold(pte_mkyoung(pte)))); }
int M_bad_mkclean(pte_t pte)   { return !!(pte_dirty(m_bad_mkclean(pte_mkdirty(pte)))); }
int M_order_ok(pte_t pte)      { return !!(pte_young(pte_mkold(pte_mkyoung(pte)))); }
int M_order_ok2(pte_t pte)     { return !!(!pte_young(pte_mkyoung(pte_mkold(pte)))); }
int M_input_bit(pte_t pte)     { return !!(pte_val(pte) & M_AF); }
int M_arith(pte_t pte)         { return !!(pte_val(pte) * 3 == 7); }
'''
EXPECT = {"M_bad_mkold": "违反（任意输入）", "M_bad_mkclean": "违反（任意输入）", "M_order_ok": "成立", "M_order_ok2": "成立",
          "M_input_bit": "违反（某组输入位）", "M_arith": "未知"}


def main(b):
    p = E.WORK / f"micro_{b}.c"
    E.WORK.mkdir(parents=True, exist_ok=True)
    p.write_text(MICRO)
    funcs = E.dump_unit(b, p, ["M_", "m_"])
    need = set()

    def callees(n):
        if isinstance(n, dict):
            if n.get("kind") == "CallExpr":
                c = n["inner"][0]
                while c.get("kind") in ("ImplicitCastExpr", "ParenExpr") and c.get("inner"):
                    c = c["inner"][0]
                x = (c.get("referencedDecl") or {}).get("name")
                if x:
                    need.add(x)
            for v in n.values():
                callees(v)
        elif isinstance(n, list):
            for v in n:
                callees(v)
    for _ in range(8):
        need.clear()
        callees(list(funcs.values()))
        miss = sorted(x for x in need if x not in funcs and not E.UNKNOWN_BOOL_CALLS.match(x) and not x.startswith("__builtin"))
        if not miss:
            break
        funcs.update(E.dump_unit(b, p, miss))
    out, ok = [], 0
    for nm, want in EXPECT.items():
        r = E.evaluate(funcs, nm, b)
        good = r["status"].startswith(want.rstrip("）"))   # category prefix up to 任意输入 / 某组输入位
        ok += good
        out.append({"func": nm, "expect": want, "got": r["status"], "ok": good})
        print(nm, "expect", want, "got", r["status"], "OK" if good else "MISMATCH", flush=True)
    (HERE / f"calib9_{b}.json").write_text(json.dumps({"build": b, "ok": ok, "n": len(EXPECT), "rows": out}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    if any(b.startswith("arm64") for b in sys.argv[1:]):
        import evalarm  # noqa: F401  (registers arm64 builds)
    for b in (sys.argv[1:] or ["rv32_abi", "x86_64"]):
        main(b)
