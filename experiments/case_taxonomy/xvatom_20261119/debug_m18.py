import sys
sys.path.insert(0, ".")
import xvatom as X
files = X.files_of("bbcbf045d6c7^")
D = X.Defs(files)
F = "pmdp_huge_get_and_clear_full"
live = [a for a in D.archs if D.live(a, F)]
print("live", live)
for a in live:
    defs, src = D.effective(a, F)
    asr = [x for p, b in defs for x in X.present_asserts(b)]
    print(a, src, len(defs), [p for p, _ in defs][:3], asr[:1])
