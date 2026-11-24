"""ecpud criteria 二: ecbuild's EC (ecbuild_20261122/ec6.py = round-3 EC on any revision + the runtime-merge fix) with three
infrastructure changes. Judging rules are unchanged (round 3 + round-5 rules 4, 5 through ecprot_20261122/ec5.py). WSL.

  1. a new build riscv64_thp (riscv defconfig + TRANSPARENT_HUGEPAGE, variants by mkvariants3.sh);
  2. powerpc book3s64 boot-time index sizes (__pte/__pmd/__pud/__pgd_index_size) take the build's RADIX_* or H_* constant according
     to radix_enabled();
  3. a runtime predicate recognised by name is first evaluated through its own body on this build; a constant result is used as is.

    python3 ec7.py df                    -> all 21 builds at df2908090cda (names from round 3) + rules 4/5 -> /root/work/ec_cache/r7/df
    python3 ec7.py parent <hash>         -> parent of <hash>: re-mine riscv64_thp / ppc64le / ppc64le_hash, reuse the rest from v6;
                                            then the fixed run
    python3 ec7.py recall                -> results/recall.json (round-5 rules, hit definition as round 5)
    python3 ec7.py mine <tag> <rev> <b>  (internal)
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
for p in ("autoenc_20261122", "ecscan_20261122", "ecnoise_20261122", "ecrecall_20261122", "ecprot_20261122", "ecbuild_20261122"):
    sys.path.insert(0, str(CT / p))
import ec6  # noqa: E402
import ec4  # noqa: E402

V6 = Path("/root/work/ec_cache/v6")
V7 = Path("/root/work/ec_cache/v7")
R7 = Path("/root/work/ec_cache/r7")
R3DF = Path("/root/work/ec_cache/r3/df2908090cda")
DF = "df2908090cda"
ec4.VCACHE = V7
ec4.HERE = HERE
ec4.__file__ = str(Path(__file__))          # subprocesses "<this file> mine ..."
NEW = "riscv64_thp"
REMINE = ["riscv64_thp", "ppc64le", "ppc64le_hash"]
BOOT = {"__pte_index_size": "PTE_INDEX_SIZE", "__pmd_index_size": "PMD_INDEX_SIZE", "__pud_index_size": "PUD_INDEX_SIZE",
        "__pgd_index_size": "PGD_INDEX_SIZE"}
GWRAP = "".join(f"#ifdef {p}{s}\nstatic __attribute__((used)) unsigned long AE_G_{p}{s}(void) {{ return {p}{s}; }}\n#endif\n"
                for p in ("RADIX_", "H_") for s in BOOT.values())


def add_build():
    """change 1: riscv64_thp in every build list, architecture riscv"""
    import mine as M
    import ec as EC2
    import classify as C
    for L in (EC2.BUILDS, M.BUILDS, C.BUILDS):
        if NEW not in L:
            L.insert(L.index("riscv64") + 1, NEW)
    EC2.ARCH[NEW] = "riscv"


def patch_eval():
    import mine as M
    S, E = M.S, M.E
    if "AE_G_" not in M.CONSTS:
        M.CONSTS = M.CONSTS + GWRAP
    orig_load = M.load

    def load(b, p):
        """change 3: the bodies of runtime predicates (and what they call) are loaded too"""
        funcs = orig_load(b, p)
        for _ in range(12):
            miss = sorted(x for x in S.callees(funcs) if x not in funcs and not x.startswith("__builtin") and x != "__builtin_constant_p")
            if not miss:
                break
            got = E.dump_unit(b, p, miss)
            if not got:
                break
            funcs.update(got)
        info = S.BUILD_INFO.get(b, {})
        names = [nm for nm in S.enum_names(funcs) if nm not in info.get("enums", {})]
        if names:                                        # enum constants of the newly loaded bodies (e.g. true/false), as mine.load does
            src = p.read_text() + "".join(f"long long EN_{nm}(void) {{ return {nm}; }}\n" for nm in names)
            got = S.clang_consts(b, src, [f"EN_{nm}" for nm in names])
            info.setdefault("enums", {}).update({nm: got[f"EN_{nm}"] for nm in names if got.get(f"EN_{nm}") is not None})
        return funcs
    M.load = load
    base = S.SInterp.expr
    base_call = S.SInterp.call

    def call(self, name, args, depth=0):
        """amendment 1: inside a change-3 trial, compile-time assertion functions (never executed in a kernel that compiles) are no-ops"""
        if self.__dict__.get("_pred_guard"):
            if re.fullmatch(r"__compiletime_assert_\d+", name or ""):
                return S.SBV(32, 0)
            m = re.fullmatch(r"__builtin_(popcount|ctz|clz|ffs)(l|ll)?", name or "")
            if m:                                        # amendment 1: bit-count builtins on a constant argument
                x = S.unwrap(args[0])
                c = x.const() if isinstance(x, S.SBV) else None
                if c is None:
                    raise E.Unsupported(f"{name} of a non-constant")
                w = 32 if not m.group(2) else 64
                op = m.group(1)
                if op == "popcount":
                    r = bin(c & ((1 << w) - 1)).count("1")
                elif op == "ffs":
                    r = (c & -c).bit_length() if c else 0
                elif c == 0:
                    raise E.Unsupported(f"{name}(0) is undefined")
                elif op == "ctz":
                    r = (c & -c).bit_length() - 1
                else:
                    r = w - (c & ((1 << w) - 1)).bit_length()
                return S.SBV(32, r)
        return base_call(self, name, args, depth)
    S.SInterp.call = call
    base_stmt = M.AInterp.stmt

    def stmt(self, n, env, depth):
        """amendment 2: inside a change-3 trial, inline assembly and jumps make the trial fail (the predicate stays a runtime one)"""
        if self.__dict__.get("_pred_guard") and n.get("kind") in ("GCCAsmStmt", "MSAsmStmt", "GotoStmt", "LabelStmt", "IndirectGotoStmt"):
            raise E.Unsupported(f"{n.get('kind')} in a predicate trial")
        return base_stmt(self, n, env, depth)
    M.AInterp.stmt = stmt

    def try_body(self, name, args, depth):
        """change 3: evaluate a predicate's own body; side effects on runtime keys / notes are undone"""
        cache = self.__dict__.setdefault("_pred_cache", {})
        guard = self.__dict__.setdefault("_pred_guard", set())
        ck = (name, tuple(a.const() if isinstance(a, S.SBV) else None for a in args))
        if ck in cache:
            return cache[ck]
        if name in guard or name not in self.funcs:
            return None
        rt, nn = set(self.runtime), len(self.notes)
        guard.add(name)
        try:
            v = S.unwrap(self.call(name, args, depth + 1))
            v = v if isinstance(v, S.SBV) and v.const() is not None else None
        except Exception:                                # a failed trial only means "not a constant here"
            v = None
        finally:
            guard.discard(name)
            self.runtime.clear()
            self.runtime.update(rt)
            del self.notes[nn:]
        cache[ck] = v
        return v

    def expr(self, n, env, depth):
        k = n.get("kind")
        if k == "CallExpr":
            name = self.callee(n)
            if name and name != "__builtin_constant_p" and E.UNKNOWN_BOOL_CALLS.match(name):
                try:
                    args = [S.unwrap(self.expr(a, env, depth)) for a in n["inner"][1:]]
                except E.Unsupported:
                    args = None
                if args is not None:
                    v = try_body(self, name, args, depth)
                    if v is not None:
                        w, _ = self.width(n)
                        return v.resize(w or v.w)
        elif k == "DeclRefExpr":
            d = n.get("referencedDecl") or {}
            if d.get("kind") == "VarDecl" and d.get("name") in BOOT and d.get("id") not in env:
                radix = try_body(self, "radix_enabled", [], depth)
                if radix is not None:
                    radix = bool(radix.const())
                else:
                    key = "radix_enabled()"
                    self.runtime.add(key)
                    orc = getattr(self, "oracle", {})
                    radix = orc.get(key)
                if radix is not None:
                    w = f"AE_G_{'RADIX_' if radix else 'H_'}{BOOT[d['name']]}"
                    if w in self.funcs:
                        v = S.unwrap(self.call(w, [], depth + 1))
                        ww, _ = self.width(n)
                        return v.resize(ww or v.w)
        return base(self, n, env, depth)
    S.SInterp.expr = expr


def patch():
    ec6.patch()
    add_build()
    patch_eval()


def df_run():
    import ec5
    res = ec4.pipeline(DF, DF, None, reuse_from=R3DF)
    ec5.R5 = R7
    return ec5.revote(V7 / DF / DF, "df", DF, df=True), res


def df_part(builds):
    """amendment 2: re-mine only <builds> at df, the rest from the previous df run (backed up to v7/df_run2)"""
    import ec5
    bak = V7 / "df_run2"
    if not bak.exists():
        shutil.copytree(V7 / DF, bak)
    res = ec4.pipeline(DF, DF, builds, reuse_from=bak / DF)
    ec5.R5 = R7
    return ec5.revote(V7 / DF / DF, "df", DF, df=True), res


def parent(h):
    par = ec4.git("rev-parse", "--short=12", f"{h}^")
    import ec as EC2
    ok = [b for b in REMINE if (ec4.VER / par / f"cfg_{b}" / "mm" / ".memory.o.cmd").exists()]
    (V7 / par).mkdir(parents=True, exist_ok=True)
    ec4.pipeline(par, par, ok, reuse_from=V6 / par / par)
    ec4.fixed(h)


SAMPLES = ec6.SAMPLES


def recall7():
    import ec5
    import ec as EC2
    ec5.R5 = R7
    KS = "/root/repos/linux"
    out = {}
    for h in SAMPLES:
        par = subprocess.run(["git", "-C", KS, "rev-parse", "--short=12", f"{h}^"], capture_output=True, text=True).stdout.strip()
        fi = V7 / f"{h}-fixed" / "fixinfo.json"
        rec = {"hash": h, "parent": par}
        if not fi.exists() or not (V7 / par / par / "deviations.json").exists():
            rec["evaluable"] = False
            out[h] = rec
            print("RECALL7", h, "not evaluable", flush=True)
            continue
        info = json.loads(fi.read_text(encoding="utf-8"))
        archs = set(info["archs"])
        builds = json.loads((V7 / par / "meta.json").read_text())["builds"]
        names = set(ec5.changed_names2(h))
        rec["builds"] = builds
        rec["evaluable"] = any(EC2.ARCH.get(b) in archs for b in builds)

        def naming(c):
            return c["arch"] in archs and (c["func"] in names or set(re.split(r"[|>]", c["example"])) & names)
        P = ec5.revote(V7 / par / par, f"p_{par}", par)
        fdir = V7 / f"{h}-fixed" / par
        F = ec5.revote(fdir, f"f_{h}", par) if (fdir / "deviations.json").exists() else None
        fk = {ec5.key(c) for c in F["cands"]} if F else set()
        rec.update(rows_parent=len(P["cands"]), rows_fixed=len(F["cands"]) if F else None,
                   naming=[ec5.key(c) for c in P["cands"] if naming(c)],
                   gone=[ec5.key(c) for c in P["cands"] if c["arch"] in archs and ec5.key(c) not in fk],
                   hit=bool(F) and any(naming(c) and ec5.key(c) not in fk for c in P["cands"]),
                   laws_by_family=P["laws_by_family"], deviations_by_rule=P["deviations_by_rule"])
        out[h] = rec
        print("RECALL7", h, json.dumps({k: rec[k] for k in ("evaluable", "hit", "naming", "gone")}, ensure_ascii=False), len(builds),
              "builds", flush=True)
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "recall.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    cmd = sys.argv[1]
    patch()
    if cmd == "df":
        df_run()
    elif cmd == "dfpart":
        df_part(sys.argv[2:])
    elif cmd == "parent":
        parent(sys.argv[2])
    elif cmd == "mine":
        ec4.mine_one(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "recall":
        recall7()
