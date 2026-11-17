"""Route each known defect's fix location to a triage exit (criteria 三, 四) and gather existing check results (五.3).

    python triage.py      -> triage.json, triage_summary.txt
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
SM = json.loads((CT / "boundary_closure_20261108/sample_match_v2.json").read_text(encoding="utf-8"))["samples"]
REACH = json.loads((CT / "static2_dev_20261109/sample_entities.json").read_text())["all"]
HREACH = json.loads((CT / "heldout_v2_20261111/confirm/reach.json").read_text())
DETECTED = ["A101", "A171", "A181", "A310", "B467"]

T_FILE = re.compile(r"^(arch/[^/]+/kernel/.*(traps|entry|ptrace|signal|hw_breakpoint|kprobes|uprobes|probes/|misaligned)"
                    r"|arch/[^/]+/mm/fault\.c$|kernel/entry/)")
B_FILE = re.compile(r"^(init/|arch/[^/]+/kernel/[^/]*(setup|head|smpboot)|arch/[^/]+/mm/init\.c$|arch/[^/]+/boot/)")
B_HDR = re.compile(r"__init(data|const)?\b")
E_FILE = re.compile(r"^(arch/[^/]+/kvm/|virt/kvm/|drivers/(perf|irqchip|iommu|pci|clocksource|cpuidle|acpi|firmware)/"
                    r"|arch/[^/]+/kernel/[^/]*(sbi|perf|pmu|kvm))")


def parse_patch(text):
    files, names, headers = [], set(), []
    for l in text.splitlines():
        if l.startswith("+++ b/"):
            files.append(l[6:].strip())
        elif l.startswith("--- a/"):
            f = l[6:].strip()
            if f not in files:
                files.append(f)
        m = re.match(r"^@@ [^@]* @@ ?(.*)", l)
        if m:
            h = m.group(1)
            headers.append(h)
            ids = re.findall(r"([A-Za-z_]\w*)\s*\(", h)
            if ids:
                names.add(ids[-1] if not h.lstrip().startswith("#define") else ids[0])
            else:
                v = re.findall(r"([A-Za-z_]\w*)\s*(?:\[[^\]]*\]\s*)*(?:__\w+\s*)*=", h) or re.findall(r"([A-Za-z_]\w*)\s*\[", h)
                if v:
                    names.add(v[-1])
        m2 = re.match(r"^[-+]\s*#\s*define\s+([A-Za-z_]\w*)", l)
        if m2:
            names.add(m2.group(1))
    return sorted(set(files)), sorted(names), headers


def route(files, headers, map_reach, reach):
    if files and all(not f.endswith((".c", ".h", ".S")) for f in files):
        return "构建", "改动全是非源码文件"
    if map_reach:
        return "D", "带参数可达"
    if reach:
        return "D'", "可达、无参数映射（ACTOR）"
    f = [x for x in files if T_FILE.search(x)]
    if f:
        return "T", f[0]
    h = [x for x in headers if B_HDR.search(x)]
    f = [x for x in files if B_FILE.search(x)]
    if h or f:
        return "B", (h[0][:60] if h else f[0])
    f = [x for x in files if E_FILE.search(x)]
    if f:
        return "E", f[0]
    return "M", ""


def existing_checks():
    out = {}
    for r in json.loads((CT / "checks2_xarch_20261109/sample_eval.json").read_text(encoding="utf-8")):
        out.setdefault(r["id"], {})["checks2"] = {"hit": r.get("hit"), "status": r.get("status"),
                                                 "flags": (r.get("summary") or {}).get("distinct_flags")}
    for r in json.loads((CT / "checks_v1_20261108/sample_eval.json").read_text(encoding="utf-8")):
        out.setdefault(r["id"], {})["ctx"] = {"hit": r.get("hit"), "flags": len(r.get("hit_flags", []))}
    for p in sorted((CT / "effdep_dev_20261113/out").glob("*.json")):
        if p.stem.startswith(("A", "B")) and "_" not in p.stem:
            d = json.loads(p.read_text(encoding="utf-8"))
            out.setdefault(p.stem, {})["effdep"] = {"hit": d["located"], "rank": d["first_hit_rank"],
                                                   "top50": bool(d["first_hit_rank"] and d["first_hit_rank"] <= 50),
                                                   "file_rank": d["first_file_hit_rank"], "qualified": d["qualified"]}
    return out


def main():
    rows = []
    for s in SM:
        p = CT / "boundary_closure_20261108" / s["patch"]
        files, names, headers = parse_patch(p.read_text(encoding="utf-8", errors="replace"))
        r = REACH.get(s["id"], {})
        ex, why = route(files, headers, r.get("map_reach", False), r.get("reach", False))
        rows.append({"id": s["id"], "set": "dev", "subject": s["subject"], "files": files, "functions": names,
                     "map_reach": r.get("map_reach", False), "reach": r.get("reach", False),
                     "has_reach_entry": bool(r), "exit": ex, "why": why})
    for p in sorted((HERE / "data").glob("L*.patch")):
        g = p.stem
        text = p.read_text(encoding="utf-8", errors="replace")
        files, names, headers = parse_patch(text)
        h = HREACH.get(g, {})
        mr = any(v["arg_mapped"] for v in h.values())
        rc = any(v["reach_depth"] is not None for v in h.values())
        ex, why = route(files, headers, mr, rc)
        subj = next((l.strip() for l in text.splitlines()[4:8] if l.strip()), "")
        rows.append({"id": g, "set": "holdout", "subject": subj, "files": files, "functions": names,
                     "map_reach": mr, "reach": rc, "has_reach_entry": bool(h), "exit": ex, "why": why})
    chk = existing_checks()
    for r in rows:
        r["checks"] = chk.get(r["id"], {})
    (HERE / "triage.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")

    L = []
    order = ["D", "D'", "T", "B", "E", "M", "构建"]
    for st in ("dev", "holdout"):
        rs = [r for r in rows if r["set"] == st]
        L.append(f"== {st} {len(rs)}")
        for e in order:
            ids = [r["id"] for r in rs if r["exit"] == e]
            L.append(f"  {e:4} {len(ids):3}  {' '.join(ids)}")
    L.append("== known dynamic outcomes")
    by = {r["id"]: r for r in rows}
    for i in DETECTED + ["A175"]:
        r = by[i]
        L.append(f"  {i} -> {r['exit']} ({r['why']}) files={r['files'][:3]}")
    L.append("== holdout routed to dynamic (tested, 0 detected -> fallback to manual)")
    L.append("  " + " ".join(r["id"] for r in rows if r["set"] == "holdout" and r["exit"] in ("D", "D'")))
    # 五.3 suggestion quality on manual-exit samples (E, M, and dynamic-tested-not-triggered holdout)
    manual = [r for r in rows if r["exit"] in ("E", "M") or (r["set"] == "holdout" and r["exit"] in ("D", "D'"))]
    ev = [r for r in manual if r["checks"]]
    loc = [r for r in ev if any(c.get("hit") for c in r["checks"].values())]
    t50 = [r for r in ev if r["checks"].get("effdep", {}).get("top50")]
    L.append(f"== manual exit: {len(manual)} samples; evaluated by >=1 check on pre-fix code: {len(ev)}; "
             f"located by >=1 check: {len(loc)}; effdep top-50: {len(t50)}")
    for r in ev:
        L.append(f"  {r['id']} {r['exit']} {json.dumps(r['checks'], ensure_ascii=False)}")
    allev = [r for r in rows if r["checks"]]
    L.append(f"== all evaluated samples (any exit): {len(allev)}")
    for r in allev:
        if r not in ev:
            L.append(f"  {r['id']} {r['exit']} {json.dumps(r['checks'], ensure_ascii=False)}")
    ins = {k for k, v in REACH.items() if v.get("in_site")}
    L.append(f"== type-consistency hint sites (current version, descriptive): in_site {sorted(ins)}; "
             f"of which manual exit: {sorted(i for i in ins if by.get(i, {}).get('exit') in ('E', 'M'))}")
    (HERE / "triage_summary.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
