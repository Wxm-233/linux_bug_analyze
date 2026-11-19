"""weakov criteria 一-五: implementation consistency, __weak common implementation vs arch override, path effects.
Lexical (git objects of /root/repos/linux), any revision, no build. Runs in WSL.

    python3 weakov.py selftest
    python3 weakov.py run <rev> [out.json]     candidates at rev
    python3 weakov.py dev                      criteria 六.2 and 六.4
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "p1check_20261115"))
import p1check as C  # noqa: E402

IDENT = re.compile(r"^[A-Za-z_]\w*$")
KEYW = C.KEYW | {"defined", "__attribute__", "asm", "__asm__", "volatile", "__volatile__"}
# criteria 二: not effects
NONEFF_EXACT = {"printk", "per_cpu", "per_cpu_ptr", "READ_ONCE", "WRITE_ONCE", "IS_ENABLED", "likely", "unlikely", "container_of",
                "sizeof", "ARRAY_SIZE", "min", "max", "might_sleep", "BUG", "dump_stack"}
NONEFF_PREFIX = ("pr_", "WARN", "BUG_ON", "lockdep_assert", "this_cpu_", "dev_err", "dev_warn", "dev_info", "dev_dbg", "dev_notice",
                 "dev_crit", "dev_alert", "dev_emerg", "dev_printk")


def noneffect(n):
    return n in NONEFF_EXACT or n.startswith(NONEFF_PREFIX) or n.endswith("_once")


# ---------------------------------------------------------------- statement structure
def cond_map(t, b0, b1):
    """ctx[i] = tuple of enclosing condition texts for every token in body (b0 '{' .. b1 '}'); () = top level"""
    ctx = {}

    def text(lo, hi):
        return " ".join(t[k][0] for k in range(lo, hi + 1))

    def mark(lo, hi, conds):
        for k in range(lo, hi + 1):
            ctx.setdefault(k, conds)

    def stmt(j, conds):
        if j >= b1:
            return b1
        x = t[j][0]
        if x == "{":
            ctx[j] = conds
            k = j + 1
            while k < b1 and t[k][0] != "}":
                k = stmt(k, conds) + 1
            ctx[min(k, b1)] = conds
            return min(k, b1)
        if x == ";":
            ctx[j] = conds
            return j
        if x == "if" and j + 1 < b1 and t[j + 1][0] == "(":
            e = C.match_fwd(t, j + 1)
            mark(j, e, conds)
            c = text(j + 2, e - 1)
            end = stmt(e + 1, conds + (c,))
            if end + 1 < b1 and t[end + 1][0] == "else":
                ctx[end + 1] = conds
                end = stmt(end + 2, conds + ("!(" + c + ")",))
            return end
        if x in ("for", "while", "switch") and j + 1 < b1 and t[j + 1][0] == "(":
            e = C.match_fwd(t, j + 1)
            mark(j, e, conds)
            return stmt(e + 1, conds + (x + " " + text(j + 2, e - 1),))
        if x == "do":
            ctx[j] = conds
            end = stmt(j + 1, conds + ("do",))
            k = end + 1
            if k < b1 and t[k][0] == "while":
                e = C.match_fwd(t, k + 1)
                mark(k, e + 1, conds)
                return e + 1
            return end
        if (x in ("case", "default") or (IDENT.match(x) and t[j + 1][0] == ":" and x not in KEYW)):
            k = j
            while k < b1 and t[k][0] != ":":
                k += 1
            mark(j, k, conds)
            return k
        # simple statement or macro loop
        k, d = j, 0
        while k < b1:
            y = t[k][0]
            if y in ("(", "["):
                d += 1
            elif y in (")", "]"):
                d -= 1
            elif y == "{" and d == 0:
                if t[k - 1][0] == ")" and IDENT.match(t[j][0]) and t[j + 1][0] == "(" and C.match_fwd(t, j + 1) == k - 1:
                    mark(j, k - 1, conds)                      # for_each_xxx(...) { ... }
                    return stmt(k, conds + ("loop " + t[j][0],))
                k = C.match_fwd(t, k, "{", "}")                # initializer
            elif y == "{":
                k = C.match_fwd(t, k, "{", "}")                # statement expression
            elif y == ";" and d <= 0:
                break
            k += 1
        mark(j, min(k, b1), conds)
        return min(k, b1)

    k = b0 + 1
    while k < b1:
        k = stmt(k, ()) + 1
    return ctx


def header(t, name_idx):
    h = name_idx - 1
    while h >= 0 and t[h][0] not in (";", "}", "{"):
        h -= 1
    return [t[k][0] for k in range(h + 1, name_idx)]


def defs_in(src):
    """[(name, ret_tokens, weak, static, t, b0, b1)]"""
    try:
        t = C.tokenize(C.strip(src))
        out = []
        for name, params, b0, b1 in C.functions(t):
            j = b0 - 1
            while j > 0 and t[j][0] != ")":
                j -= 1
            k = C.match_back(t, j)
            ni = k - 1
            while ni >= 0 and t[ni][0] != name:   # attributes between ) and name are rare; walk back to the name
                ni -= 1
            hd = header(t, ni)
            out.append((name, hd, "__weak" in hd, "static" in hd, t, b0, b1))
        return out
    except (IndexError, RecursionError):
        return []


def is_void(hd):
    toks = [x for x in hd if x not in ("__weak", "static", "inline", "__init", "notrace", "noinline", "__cpuinit", "extern")]
    return "void" in toks and "*" not in toks


def calls_of(t, b0, b1):
    return [i for i in range(b0, b1) if IDENT.match(t[i][0]) and t[i + 1][0] == "(" and t[i][0] not in KEYW]


def weak_effects(t, b0, b1, name):
    ctx = cond_map(t, b0, b1)
    cut = b1
    for i in range(b0, b1):
        if t[i][0] in ("return", "goto"):
            cut = i
            if t[i][0] == "return" and ctx.get(i) == ():
                while cut < b1 and t[cut][0] != ";":
                    cut += 1
            break
    eff = []
    for i in calls_of(t, b0, cut):
        n = t[i][0]
        if ctx.get(i) == () and n != name and not noneffect(n) and n not in eff:
            eff.append(n)
    return eff


ERRV = re.compile(r"^(-\s*E[A-Z0-9]+|ERR_PTR\b.*|false|NULL|ret|err|error|rc)$")


def missing_paths(t, b0, b1, e, void):
    ctx = cond_map(t, b0, b1)
    occ = [i for i in calls_of(t, b0, b1) if t[i][0] == e]
    top = [i for i in occ if ctx.get(i) == ()]
    if not top:
        return [{"line": t[occ[0]][1], "kind": "conditional-effect", "cond": " && ".join(ctx.get(occ[0], ())), "ret": None}]
    p = top[0]
    labels = {t[k][0]: k for k in range(b0 + 1, b1 - 1) if IDENT.match(t[k][0]) and t[k + 1][0] == ":" and t[k - 1][0] in (";", "{", "}")}
    out = []
    for j in range(b0 + 1, p):
        x = t[j][0]
        if x == "return" and ctx.get(j) != ():
            k = j + 1
            while k < b1 and t[k][0] != ";":
                k += 1
            rv = " ".join(t[m][0] for m in range(j + 1, k))
            out.append({"line": t[j][1], "kind": "early-return", "cond": " && ".join(ctx.get(j, ())), "ret": rv, "void": void})
        elif x == "goto" and IDENT.match(t[j + 1][0]) and labels.get(t[j + 1][0], -1) > p:
            out.append({"line": t[j][1], "kind": "goto-past", "cond": " && ".join(ctx.get(j, ())), "ret": "goto " + t[j + 1][0], "void": void})
    return out


def callers(files, N):
    """common (non-arch) call sites: [(path:line, func, ignored?)]"""
    out = []
    for p, src in files.items():
        if p.startswith("arch/") or not re.search(r"\b" + re.escape(N) + r"\s*\(", src):
            continue
        for name, hd, weak, static, t, b0, b1 in defs_in(src):
            for i in calls_of(t, b0, b1):
                if t[i][0] != N:
                    continue
                e = C.match_fwd(t, i + 1)
                ign = t[i - 1][0] in (";", "{", "}", ":", ")", "else") and e + 1 < len(t) and t[e + 1][0] == ";"
                out.append((f"{p}:{t[i][1]}", name, ign))
    return out


def analyze(files):
    weak = {}
    for p, src in files.items():
        if p.startswith("arch/") or not p.endswith(".c"):
            continue
        for name, hd, w, st, t, b0, b1 in defs_in(src):
            if w and not st:
                eff = weak_effects(t, b0, b1, name)
                if eff:
                    weak.setdefault(name, (p, eff, is_void(hd)))
    over = {}
    for p, src in files.items():
        m = re.match(r"arch/([^/]+)/.*\.c$", p)
        if not m:
            continue
        for name, hd, w, st, t, b0, b1 in defs_in(src):
            if name in weak and not w and not st:
                over.setdefault(name, []).append((m.group(1), p, hd, t, b0, b1))
    archs = sorted({p.split("/")[1] for p in files if p.startswith("arch/") and p.count("/") >= 2})
    cands, pre = [], 0
    for N, ovs in sorted(over.items()):
        wp, eff, wvoid = weak[N]
        for a, p, hd, t, b0, b1 in ovs:
            got = {t[i][0] for i in calls_of(t, b0, b1)}
            void = is_void(hd)
            for e in [x for x in eff if x in got]:
                miss = missing_paths(t, b0, b1, e, void)
                if not miss:
                    continue
                pre += 1
                cs = callers(files, N)
                if not cs:
                    continue
                ign = void or any(c[2] for c in cs)
                keep = [m for m in miss if void or m["kind"] != "early-return" or m["ret"] in ("", "0")
                        or (any(c[2] for c in cs))]
                if not keep:
                    continue
                cands.append({"hook": N, "arch": a, "effect": e, "weak": wp, "override": f"{p}:{t[b0][1]}", "void": void,
                              "ignored": ign, "missing": keep, "callers": [f"{c[0]} {c[1]}{' (ignored)' if c[2] else ''}" for c in cs[:3]],
                              "n_callers": len(cs), "n_generic_archs": len(archs) - len({o[0] for o in ovs})})
    cands.sort(key=lambda c: (not c["ignored"], -c["n_generic_archs"], c["hook"], c["arch"]))
    return cands, {"weak_with_effect": len(weak), "overridden": len(over), "pre_caller_filter": pre}


# ---------------------------------------------------------------- git
def run(rev):
    weakf = [ln.split(":", 1)[1] for ln in C.git("grep", "-l", "-w", "__weak", rev, "--", "*.c", ":(exclude)arch").split("\n") if ln]
    files = C.cat_files(rev, weakf)
    names = set()
    for p, s in files.items():
        for name, hd, w, st, t, b0, b1 in defs_in(s):
            if w and not st:
                names.add(name)
    pat = HERE / ".names.tmp"
    pat.write_text("\n".join(sorted(names)) + "\n")
    archf = [ln.split(":", 1)[1] for ln in C.git("grep", "-l", "-w", "-F", "-f", str(pat), rev, "--", "arch/*.c").split("\n") if ln]
    files.update(C.cat_files(rev, archf))
    cands0, _ = analyze(files)
    hooks = sorted({c for c in names if any(c in s for p, s in files.items() if p.startswith("arch/"))})
    pat.write_text("\n".join(hooks) + "\n")
    comf = [ln.split(":", 1)[1] for ln in C.git("grep", "-l", "-w", "-F", "-f", str(pat), rev, "--", "*.c", "*.h", ":(exclude)arch").split("\n") if ln]
    pat.unlink()
    files.update(C.cat_files(rev, [p for p in comf if p not in files]))
    return analyze(files)


def cmd_run(rev, out=None):
    cands, info = run(rev)
    print("info", info, "cands", len(cands))
    for c in cands:
        print(f"  {c['hook']} [{c['arch']}] effect={c['effect']} ign={c['ignored']} generic_archs={c['n_generic_archs']} {c['override']}")
        for m in c["missing"]:
            print(f"      L{m['line']} {m['kind']} if ({m['cond'][:90]}) {m['ret'] or ''}")
        print("      callers:", "; ".join(c["callers"]))
    if out:
        Path(out).write_text(json.dumps({"rev": rev, "info": info, "cands": cands}, indent=1))
    return cands


def cmd_dev():
    res = {}
    for name, rev, want in (("fix_parent", "18a4e5cf633f^", True), ("fix", "18a4e5cf633f", False),
                            ("intro_parent", "eba4675008a6^", False), ("intro", "eba4675008a6", True)):
        cands, info = run(rev)
        hit = [c for c in cands if c["hook"] == "arch_unregister_cpu" and c["arch"] == "arm64" and c["effect"] == "unregister_cpu"]
        res[name] = {"rev": rev, "want": want, "hit": bool(hit), "ok": bool(hit) == want, "n_cands": len(cands), "info": info,
                     "match": hit}
        print(name, rev, "hit" if hit else "no-hit", "OK" if bool(hit) == want else "FAIL", "cands", len(cands), info)
        for c in hit:
            for m in c["missing"]:
                print(f"    L{m['line']} {m['kind']} if ({m['cond']}) {m['ret'] or ''}")
    (HERE / "dev.json").write_text(json.dumps(res, indent=1))


# ---------------------------------------------------------------- selftest
W = """
void __weak arch_unregister_cpu(int num)
{
	unregister_cpu(&per_cpu(cpu_devices, num));
}
int __weak hook_b(int x)
{
	pr_info("x");
	return do_b(x);
}
void __weak hook_c(int x)
{
	do_c(x);
}
void __weak hook_d(int x)
{
}
"""
COM = """
static void post(struct acpi_processor *pr)
{
	arch_unregister_cpu(pr->id);
	per_cpu(processors, pr->id) = NULL;
	hook_c(1);
	hook_d(1);
}
int user(int x)
{
	int r = hook_b(x);
	if (r)
		return r;
	return 0;
}
"""
OLD = """
void arch_unregister_cpu(int cpu)
{
	acpi_handle acpi_handle = acpi_get_processor_handle(cpu);
	struct cpu *c = &per_cpu(cpu_devices, cpu);
	if (!acpi_handle) {
		pr_err_once("Removing a CPU without associated ACPI handle\\n");
		return;
	}
	status = acpi_evaluate_integer(acpi_handle, "_STA", NULL, &sta);
	if (ACPI_FAILURE(status))
		return;
	if (cpu_present(cpu) && !(sta & ACPI_STA_DEVICE_PRESENT)) {
		pr_err_once("x\\n");
		return;
	}
	unregister_cpu(c);
}
int hook_b(int x)
{
	if (x < 0)
		return -EINVAL;
	return do_b(x);
}
void hook_c(int x)
{
	if (x > 3)
		goto out;
	prep();
	do_c(x);
out:
	done();
}
void hook_d(int x)
{
	if (x)
		return;
	other(x);
}
"""
NEW = """
void arch_unregister_cpu(int cpu)
{
	acpi_handle acpi_handle = acpi_get_processor_handle(cpu);
	struct cpu *c = &per_cpu(cpu_devices, cpu);
	status = acpi_evaluate_integer(acpi_handle, "_STA", NULL, &sta);
	if (!ACPI_FAILURE(status) &&
	    cpu_present(cpu) && !(sta & ACPI_STA_DEVICE_PRESENT))
		pr_err_once("x\\n");
	unregister_cpu(c);
}
void hook_c(int x)
{
	for_each_cpu(x, m) {
		if (x)
			continue;
	}
	do_c(x);
	if (x)
		return;
}
"""
COND = """
void hook_c(int x)
{
	if (x)
		do_c(x);
}
"""


def selftest():
    ok = True

    def chk(label, files, want):
        nonlocal ok
        cands, _ = analyze(files)
        got = sorted((c["hook"], c["arch"], c["effect"], len(c["missing"])) for c in cands)
        good = got == sorted(want)
        ok &= good
        print("PASS" if good else "FAIL", label, got)

    base = {"drivers/base/cpu.c": W, "drivers/acpi/p.c": COM}
    chk("old arm64 + goto-past (report); -EINVAL checked (no); no shared effect (no)", {**base, "arch/arm64/kernel/smp.c": OLD},
        [("arch_unregister_cpu", "arm64", "unregister_cpu", 3), ("hook_c", "arm64", "do_c", 1)])
    chk("fixed arm64; loop continue and return after effect (no)", {**base, "arch/arm64/kernel/smp.c": NEW}, [])
    chk("effect only in a branch (report)", {**base, "arch/x86/kernel/a.c": COND}, [("hook_c", "x86", "do_c", 1)])
    chk("no common caller (no)", {"drivers/base/cpu.c": W, "arch/arm64/kernel/smp.c": OLD}, [])
    ign = COM.replace("int r = hook_b(x);\n\tif (r)\n\t\treturn r;", "hook_b(x);")
    chk("-EINVAL with an ignoring caller (report)", {"drivers/base/cpu.c": W, "drivers/acpi/p.c": ign, "arch/arm64/kernel/smp.c": OLD},
        [("arch_unregister_cpu", "arm64", "unregister_cpu", 3), ("hook_b", "arm64", "do_b", 1), ("hook_c", "arm64", "do_c", 1)])
    t = C.tokenize(C.strip(OLD))
    _, _, b0, b1 = next(C.functions(t))
    conds = sorted({m["cond"] for m in missing_paths(t, b0, b1, "unregister_cpu", True)})
    good = conds == sorted(["! acpi_handle", "ACPI_FAILURE ( status )", "cpu_present ( cpu ) && ! ( sta & ACPI_STA_DEVICE_PRESENT )"])
    ok &= good
    print("PASS" if good else "FAIL", "condition texts", conds)
    print("ALL PASS" if ok else "SOME FAIL")
    return ok


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "selftest"
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    elif cmd == "run":
        cmd_run(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif cmd == "dev":
        cmd_dev()
