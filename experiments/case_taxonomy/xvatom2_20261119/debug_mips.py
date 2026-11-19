import re, sys
sys.path.insert(0, ".")
import xvatom2 as V
X = V.X
D = X.Defs(X.files_of("df2908090cda"))

def wit(a, name, pos, stack=frozenset()):
    for kind, pn, pt, body in V.effective2(D, a, name):
        names = {pn[i] for i in pos if i < len(pn)}
        if kind == "func":
            names |= {n for n, ts in zip(pn, pt) if ts & V.ENTRY_T}
        if not names:
            continue
        text = V.V1.blank(body)
        names = V.aliases(text, names)
        m = X.ATOMIC_ASM.search(body)
        if m:
            return [f"{name}{sorted(names)}:asm:{m.group(0)}"]
        for c, args in V.calls_with_args(text):
            hit = [i for i, x in enumerate(args) if V.mentions(x, names)]
            if not hit:
                continue
            if X.ATOMIC_CALL.match(c):
                return [f"{name}{sorted(names)}", f"{c}({', '.join(args)})"]
            if c != name and c not in stack:
                w = wit(a, c, hit, stack | {name})
                if w:
                    return [f"{name}{sorted(names)}"] + w
    return None

for ref in ("ptep_test_and_clear_young", "ptep_set_wrprotect", "ptep_get_and_clear"):
    print("mips", ref, "->", wit("mips", ref, {2}))
