import re, sys
sys.path.insert(0, ".")
import xvatom as X
D = X.Defs(X.files_of("df2908090cda"))

def wit(a, name, depth=0, seen=frozenset()):
    for p, body in D.effective(a, name)[0]:
        m = X.ATOMIC_ASM.search(body)
        if m:
            return [f"{name}@{p.split('/')[-1]}:asm:{m.group(0)}"]
        calls = X.V1.callees(body)
        for c in calls:
            if X.ATOMIC_CALL.match(c):
                return [f"{name}@{p.split('/')[-1]}", c]
        if depth < X.DEPTH:
            for c in calls:
                if c != name and c not in seen:
                    w = wit(a, c, depth + 1, seen | {name})
                    if w:
                        return [f"{name}@{p.split('/')[-1]}"] + w
    return None

for a, ref, M in [("powerpc", "ptep_get_and_clear", "pudp_huge_get_and_clear_full"), ("powerpc", "ptep_test_and_clear_young", "pudp_test_and_clear_young"),
                  ("powerpc", "ptep_get_and_clear", "pudp_huge_get_and_clear"), ("powerpc", "ptep_get_and_clear", "pmdp_huge_get_and_clear"),
                  ("mips", "ptep_get_and_clear", "pmdp_huge_get_and_clear"), ("mips", "ptep_test_and_clear_young", "pmdp_test_and_clear_young"),
                  ("mips", "ptep_set_wrprotect", "pmdp_set_wrprotect"), ("arm", "ptep_test_and_clear_young", "pmdp_test_and_clear_young"),
                  ("arm", "ptep_set_wrprotect", "pmdp_set_wrprotect")]:
    print(a, ref, "->", wit(a, ref))
    print("   ", M, "->", wit(a, M), "| defs:", [p for p, _ in D.effective(a, M)[0]][:3])
