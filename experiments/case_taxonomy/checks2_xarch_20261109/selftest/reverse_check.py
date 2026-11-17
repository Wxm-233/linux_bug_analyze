# reverse checks for checks2 selftest: break the analyzer in memory, the fixture must then disagree with EXPECTED
import sys, json
R = "/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/checks2_xarch_20261109"
sys.path.insert(0, R); sys.path.insert(0, R + "/selftest")
import xcmp, verify
W = "/root/work/checks2/selftest"
red = {a: xcmp.load(f"{W}/{a}/facts.json.gz") for a in ("riscv", "x86", "arm64")}
pool = [f"{W}/pool.json"]
def run(tag):
    flags, _ = xcmp.compare(red["riscv"], [("x86", red["x86"]), ("arm64", red["arm64"])], pool)
    got = {(f["type"], f["family"], f["detail"], t) for f in flags for t in f["counterparts"]}
    print(tag, "matches EXPECTED:", got == verify.EXPECTED, "| unexpected:", sorted(got - verify.EXPECTED), "| missing:", sorted(verify.EXPECTED - got))
run("unchanged")
orig = xcmp.Build.impls
xcmp.Build.impls = lambda self, n: orig(self, n)[-1:]          # archbound-like: only one definition per arch
run("one-definition")
xcmp.Build.impls = orig
xcmp.DEPTH = 0                                                 # no transitive writes/calls
run("depth-0")
