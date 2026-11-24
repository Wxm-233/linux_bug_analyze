"""ecsrc criteria 二: ecpud's EC (ecpud_20261123/ec7.py) + one infrastructure change -- page-table functions that are only declared in
headers get their bodies from the architecture's .c file, compiled with the build's own memory.o flags. Judging rules unchanged. WSL.

    python3 ec8.py df                    -> all 21 builds at df2908090cda (names / reuse from v7) + rules 4/5 -> /root/work/ec_cache/r8/df
    python3 ec8.py changed               -> results/changed_df.json: builds whose behaviour files differ from v7 at df
    python3 ec8.py parent <hash>         -> parent of <hash>: re-mine the changed builds, reuse the rest from v7; then the fixed run
    python3 ec8.py recall                -> results/recall.json
    python3 ec8.py mine <tag> <rev> <b>  (internal)
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
for p in ("autoenc_20261122", "ecscan_20261122", "ecnoise_20261122", "ecrecall_20261122", "ecprot_20261122", "ecbuild_20261122",
          "ecpud_20261123"):
    sys.path.insert(0, str(CT / p))
import ec7  # noqa: E402
import ec4  # noqa: E402

V7, V8, R8 = Path("/root/work/ec_cache/v7"), Path("/root/work/ec_cache/v8"), Path("/root/work/ec_cache/r8")
DF = ec7.DF
ec4.VCACHE = V8
ec4.HERE = HERE
ec4.__file__ = str(Path(__file__))
PT_NAME = re.compile(r"^(pfn_p(te|md|ud)|_*p(te|md|ud)_\w+)$")


def find_c(src, arch, name):
    """criteria 二: the unique .c file under arch/<arch>/ that defines <name> (a line starting with a return type and '<name>(')"""
    pat = re.compile(rf"^[A-Za-z_][\w \t\*]*\b{re.escape(name)}\s*\([^;]*$", re.M)
    hits = []
    for f in (Path(src) / "arch" / arch).rglob("*.c"):
        try:
            t = f.read_text(errors="replace")
        except OSError:
            continue
        if name in t and pat.search(t):
            hits.append(f)
    return hits[0] if len(hits) == 1 else None


def patch_csrc():
    import mine as M
    import ec as EC2
    S, E, I = M.S, M.E, M.S.I
    load7 = M.load

    def load(b, p):
        funcs = load7(b, p)
        src = Path(I.BUILDS[b]).parent / "src"
        arch = {"i386": "x86"}.get(EC2.ARCH.get(b), EC2.ARCH.get(b))
        got_from = {}
        for _ in range(8):
            miss = sorted(x for x in S.callees(funcs) if x not in funcs and not x.startswith("__builtin"))
            files = {}
            for nm in miss:
                f = None
                if PT_NAME.match(nm) and src.exists():
                    f = find_c(src, arch, nm)
                if f is None:                            # helpers of an already completed body: look in the same files
                    f = next((g for g in set(got_from.values()) if re.search(rf"\b{re.escape(nm)}\s*\(", g.read_text(errors="replace"))
                              and re.search(rf"^[A-Za-z_][\w \t\*]*\b{re.escape(nm)}\s*\([^;]*$", g.read_text(errors="replace"), re.M)), None)
                if f is not None:
                    files.setdefault(f, []).append(nm)
            if not files:
                break
            added = 0
            for f, names in files.items():
                try:
                    got = E.dump_unit(b, f, names)
                except Exception:                        # compile failure: leave the names without bodies
                    got = {}
                for nm, fn in got.items():
                    if nm in names and nm not in funcs:
                        funcs[nm] = fn
                        got_from[nm] = f
                        added += 1
            if not added:
                break
        if got_from:
            info = S.BUILD_INFO.get(b, {})
            names = [nm for nm in S.enum_names(funcs) if nm not in info.get("enums", {})]
            if names:
                s2 = p.read_text() + "".join(f"long long EN_{nm}(void) {{ return {nm}; }}\n" for nm in names)
                got = S.clang_consts(b, s2, [f"EN_{nm}" for nm in names])
                info.setdefault("enums", {}).update({nm: got[f"EN_{nm}"] for nm in names if got.get(f"EN_{nm}") is not None})
        (Path(M.HERE) / f"csrc_{b}.json").write_text(json.dumps({nm: str(f).split("/src/", 1)[-1] for nm, f in got_from.items()},
                                                               indent=1), encoding="utf-8")
        print("CSRC", b, sorted(got_from), flush=True)
        return funcs
    M.load = load


def patch():
    ec7.patch()
    patch_csrc()


def df_run():
    import ec5
    res = ec4.pipeline(DF, DF, None, reuse_from=V7 / DF / DF)
    ec5.R5 = R8
    return ec5.revote(V8 / DF / DF, "df", DF, df=True), res


def changed():
    out = {}
    for f in sorted((V8 / DF / DF).glob("beh_*.json")):
        o = V7 / DF / DF / f.name
        A = json.loads(f.read_text())["laws"]
        B = json.loads(o.read_text())["laws"] if o.exists() else {}
        n = sum(1 for k in set(A) | set(B) if (A.get(k) or {}).get("beh") != (B.get(k) or {}).get("beh"))
        cs = V8 / DF / DF / f"csrc_{f.stem[4:]}.json"
        out[f.stem[4:]] = {"changed": n, "csrc": json.loads(cs.read_text()) if cs.exists() else None}
        print(f.stem[4:], n, out[f.stem[4:]]["csrc"])
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "changed_df.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")


def parent(h):
    par = ec4.git("rev-parse", "--short=12", f"{h}^")
    ch = json.loads((HERE / "results" / "changed_df.json").read_text(encoding="utf-8"))
    rem = [b for b, v in ch.items() if v["changed"]]
    ok = [b for b in rem if (ec4.VER / par / f"cfg_{b}" / "mm" / ".memory.o.cmd").exists()]
    (V8 / par).mkdir(parents=True, exist_ok=True)
    ec4.pipeline(par, par, ok, reuse_from=V7 / par / par)
    ec4.fixed(h)


def recall8():
    ec7.V7, ec7.R7 = V8, R8                      # same recall procedure as ec7, on this round's caches
    ec7.HERE = HERE
    ec7.recall7()


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    cmd = sys.argv[1]
    patch()
    if cmd == "df":
        df_run()
    elif cmd == "changed":
        changed()
    elif cmd == "parent":
        parent(sys.argv[2])
    elif cmd == "mine":
        ec4.mine_one(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "recall":
        recall8()
