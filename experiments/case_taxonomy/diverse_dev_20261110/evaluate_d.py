"""(Copied from semhint_dev_20261109/evaluate.py for G2'/G3' with static2 hints, static2 criteria 4.4; the
G3-gain verdicts are not used.) Detection, first-detection cost, current-version oddities and link-by-link diagnosis (criteria 八、九,
diagnosis_conditions.md).   python evaluate.py  -> evaluation.json, review_detect.json, review_current.json

Manual confirmation (criteria 八 "确认") is read from confirm.json {sample: {case id: {"ok": bool, "why": str}}};
cases not listed there count as unconfirmed.
"""
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAMPLES = ["A101", "A310", "A171", "A181", "B467"]
GROUPS = ["G0d", "G2d", "G3d"]
SEEDS = ["1", "2", "3"]
B = 1000
ODD = ("odd_strong", "odd_weak")
M = (1 << 64) - 1
FIX_ITEMS = {"A101": {"arch_get_mmap_end"}, "A171": {"TASK_SIZE_MAX"}, "A181": {"__put_user", "put_user"},
             "A310": None, "B467": set()}


def load(g):
    meta = json.loads((HERE / "gen" / f"cases_{g}.json").read_text())
    lists = json.loads((HERE / "gen" / f"lists_{g}.json").read_text())
    cmp_ = json.loads((HERE / "runs" / g / "compare.json").read_text())
    hints = json.loads((HERE.parent / "rankprune_dev_20261110" / "gen" / f"hints_{g}.json").read_text())
    return meta, lists, cmp_, hints


def xorshift(s):
    s ^= (s << 13) & M
    s ^= s >> 7
    s ^= (s << 17) & M
    return s


def ival(tok):
    if tok.startswith("i:"):
        return int(tok[2:], 16)
    return None


def signed(v):
    return v - (1 << 64) if v is not None and v >> 63 else v


def cond(sample, c):
    """mutate_dev_20261110/diagnosis_conditions.md, evaluated on the logical case"""
    a, sc = c["args"], c["sc"]
    S = c.get("structs", [])

    def sbuf(tok):
        return S[int(tok[2:])] if tok.startswith("t:") and int(tok[2:]) < len(S) else None
    if sample == "A101":
        if sc != "mmap" or not c["tmpl"].startswith("occ"):
            return False
        addr, ln, fl = ival(a[0]), ival(a[1]), ival(a[3])
        if addr is None or ln is None or fl is None or addr == 0:
            return False
        return not (fl & 0x10) and not (fl & 0x100000) and (fl & 0xF) in (1, 2) and ln >= addr             and addr + ln <= 1 << 56
    if sample == "A310":
        return sc == "raw_nr" and a[0] == "i:ffffffffffffffff"
    if sample == "A171":
        def high(t):
            if t.startswith("o:"):
                return 56 <= int(t.split(":")[2]) <= 62
            v = ival(t)
            return v is not None and (1 << 56) <= v < (1 << 63)
        narrow = sc == "futex" and ival(a[1]) is not None and (ival(a[1]) & 0x7F) == 1 and high(a[0]) and             (a[0].startswith("o:") or ival(a[0]) % 4 == 0)
        return narrow or any(high(t) for t in a)
    if sample == "A181":
        if sc != "recvmsg" or a[0] != "f:udgram":
            return False
        m = sbuf(a[1])
        if not m or m.get("type") != "struct user_msghdr":
            return False
        st = m["set"]
        iov, ctl = st.get("msg_iov"), st.get("msg_control")
        if not iov or not ctl or iov[0] != "ptr" or ctl[0] != "ptr":
            return False
        ib, cb = S[iov[1]], S[ctl[1]]
        if ib.get("type") != "struct iovec" or "plain" not in cb:
            return False
        ok_iov = ib["set"].get("iov_base", [None])[0] == "ptr" and ib["set"].get("iov_len", [None])[0] == "len"
        fl = ival(a[2])
        return ok_iov and cb["plain"][2] == 1 and fl is not None and not (fl & 1) and             st.get("msg_controllen") == ["len", ctl[1]]  # mutate diagnosis_conditions.md: no fill rule, no MSG_OOB
    if sample == "B467":
        if sc != "perf_event_open" or a[3] != "f:neg" or ival(a[4]) != 0:
            return False
        m = sbuf(a[0])
        if not m or m.get("type") != "struct perf_event_attr" or m["set"].get("size") != ["sizeof"]:
            return False
        mutated = {k: v for k, v in m["set"].items() if v[0] == "int"}
        if list(mutated) != ["type"] or int(mutated["type"][1], 16) & 0xFFFFFFFF in range(6):
            return False
        pid, cpu = a[1], signed(ival(a[2]) if a[2].startswith("i:") else None)
        if pid in ("i:0", "s:self"):
            return True
        return (ival(pid) if pid.startswith("i:") else None) in (0xFFFFFFFF, M) and cpu == 0  # pid_t is 32-bit
    return False


def coverage(sample, hints):
    if sample == "A310":
        ok = bool(hints["raw_nr"]) and any(x["fn"] == "do_trap_ecall_u" for x in hints["raw_nr"]["ifs"])
        return {"candidate": ok, "mapped": ok, "sites": ["raw_nr"] if ok else []}
    items = FIX_ITEMS[sample]
    hit = []
    for sc, ss in hints["sites"].items():
        for s in ss:
            if items & (set(s.get("items", [])) | set(s.get("objects", []))):  # pruned hints keep no items (rankprune: see ranking_<group>.json)
                hit.append(f"{sc}:{s['fn']}:{s['line']}")
    # sites are only kept when mapped to a syscall parameter, so candidate == mapped here; unmapped guards that
    # mention the item are not stored by hints.py (reported as null)
    return {"candidate": bool(hit), "mapped": bool(hit), "sites": hit[:20], "n_sites": len(hit)}


def main():
    confirm = json.loads((HERE / "confirm.json").read_text()) if (HERE / "confirm.json").exists() else {}
    ev = {"samples": {}, "current": {}}
    review = {}
    for x in SAMPLES:
        meta, lists, cmp_, hints = load(x)
        C = {str(c["id"]): c for c in meta["cases"]}
        pre, fix = cmp_["verdicts"][f"{x.lower()}_pre"], cmp_["verdicts"][f"{x.lower()}_fix"]
        det = {cid for cid in C if pre.get(cid) in ODD and fix.get(cid) == "consistent"}
        det_strong = {cid for cid in det if pre[cid] == "odd_strong"}
        patch_diff = sorted(cid for cid in C if cid in cmp_["values"] and
                            cmp_["values"][cid][f"{x.lower()}_pre"] != cmp_["values"][cid][f"{x.lower()}_fix"])
        ok_ids = {cid for cid, v in confirm.get(x, {}).items() if v.get("ok")}
        per = {}
        for G in GROUPS:
            per[G] = {}
            for s in SEEDS:
                ids = [str(i) for i in lists[G][s]]
                first = next((i + 1 for i, cid in enumerate(ids) if cid in det), None)
                first_c = next((i + 1 for i, cid in enumerate(ids) if cid in det and cid in ok_ids), None)
                first_s = next((i + 1 for i, cid in enumerate(ids) if cid in det_strong), None)
                ncond = sum(1 for cid in ids if cond(x, C[cid]))
                ncond_diff = sum(1 for cid in ids if cond(x, C[cid]) and cid in det)
                per[G][s] = {"first_detect": first, "first_confirmed": first_c, "first_strong": first_s,
                             "detecting_cases": sum(1 for cid in ids if cid in det), "cond_cases": ncond,
                             "cond_and_detect": ncond_diff}
        ev["samples"][x] = {"detecting_ids": len(det), "detecting_strong": len(det_strong),
                            "patch_attributable_diff": len(patch_diff), "per_group": per,
                            "coverage": coverage(x, hints), "unstable": len(cmp_["unstable"]),
                            "complete": cmp_["complete"], "taint": cmp_["taint_changed"]}
        review[x] = [{"id": cid, "sc": C[cid]["sc"], "args": C[cid]["args"], "tmpl": C[cid]["tmpl"],
                      "verdict_pre": pre[cid], "values": cmp_["values"].get(cid), "cond": cond(x, C[cid]),
                      "in": sorted(f"{G}/{s}" for G in GROUPS for s in SEEDS if int(cid) in lists[G][s])}
                     for cid in sorted(det, key=int)]
    # main metric (criteria 九)
    tot = {}
    for G in GROUPS:
        tot[G] = {"confirmed_total": 0, "detect_total": 0, "per_seed_confirmed": {}}
        for s in SEEDS:
            n = sum(1 for x in SAMPLES if ev["samples"][x]["per_group"][G][s]["first_confirmed"])
            tot[G]["per_seed_confirmed"][s] = n
            tot[G]["confirmed_total"] += n
            tot[G]["detect_total"] += sum(1 for x in SAMPLES if ev["samples"][x]["per_group"][G][s]["first_detect"])
        tot[G]["median_cost"] = {}
        for x in SAMPLES:
            cs = sorted((ev["samples"][x]["per_group"][G][s]["first_confirmed"] or B + 1) for s in SEEDS)
            tot[G]["median_cost"][x] = cs[1]
        tot[G]["seeds_detecting"] = {x: sum(1 for s in SEEDS if ev["samples"][x]["per_group"][G][s]["first_confirmed"])
                                     for x in SAMPLES}
    ev["totals"] = tot

    def gain(a, others):
        """criteria 九: does group a show gain over the groups in others"""
        if any(0 < tot[a]["seeds_detecting"][x] < 2 for x in SAMPLES):
            return False, "unstable detection (a sample found in only 1 of 3 seeds)"
        best = max(others, key=lambda g: tot[g]["confirmed_total"])
        if tot[a]["confirmed_total"] > tot[best]["confirmed_total"]:
            return True, f"total {tot[a]['confirmed_total']} > {best} {tot[best]['confirmed_total']}"
        if tot[a]["confirmed_total"] == tot[best]["confirmed_total"]:
            both = [x for x in SAMPLES if tot[a]["median_cost"][x] <= B and tot[best]["median_cost"][x] <= B]
            faster = [x for x in both if tot[a]["median_cost"][x] * 2 <= tot[best]["median_cost"][x]]
            if both and len(faster) * 2 >= len(both):
                return True, f"equal totals; {len(faster)}/{len(both)} samples at most half the cost of {best}"
            return False, f"equal totals; {len(faster)}/{len(both)} samples at most half the cost of {best}"
        return False, f"total {tot[a]['confirmed_total']} < {best} {tot[best]['confirmed_total']}"
    ev["verdict_G3"] = None  # static2 criteria 4.4: descriptive only
    ev["verdict_G2_vs_G1"] = None

    # current version
    meta, lists, cmp_, hints = load("CUR")
    C = {str(c["id"]): c for c in meta["cases"]}
    v = cmp_["verdicts"]["cur_riscv"]
    clusters = {}
    for G in GROUPS:
        ids = {str(i) for s in SEEDS for i in lists[G][s]}
        odd_s = [cid for cid in ids if v.get(cid) == "odd_strong"]
        odd_w = [cid for cid in ids if v.get(cid) == "odd_weak"]
        ev["current"][G] = {"odd_strong": len(odd_s), "odd_weak": len(odd_w), "cases": len(ids)}
        for cid in odd_s + odd_w:
            vals = cmp_["values"][cid]
            r = json.loads(vals["cur_riscv"])[0]
            ref = sorted({json.loads(vals[k])[0] for k in vals if k != "cur_riscv"})
            key = f"{C[cid]['sc']}|{r}|{'/'.join(ref)}"
            clusters.setdefault(key, {"cases": set(), "groups": set()})
            clusters[key]["cases"].add(cid)
            clusters[key]["groups"].add(G)
    for G in GROUPS:
        ev["current"][G]["clusters"] = sum(1 for c in clusters.values() if G in c["groups"])
    keys = sorted(clusters)
    rng = random.Random(20261109)
    pick = keys if len(keys) <= 40 else sorted(rng.sample(keys, 40))
    ev["current"]["clusters_total"] = len(keys)
    rc = []
    for k in pick:
        cs = sorted(clusters[k]["cases"], key=int)
        ex = cs[0]
        rc.append({"cluster": k, "n_cases": len(cs), "groups": sorted(clusters[k]["groups"]), "example": ex,
                   "sc": C[ex]["sc"], "args": C[ex]["args"], "tmpl": C[ex]["tmpl"], "values": cmp_["values"][ex]})
    ev["current"]["unstable"] = len(cmp_["unstable"])
    ev["current"]["summary"] = cmp_["summary"]
    (HERE / "evaluation.json").write_text(json.dumps(ev, indent=1, default=sorted))
    (HERE / "review_detect.json").write_text(json.dumps(review, indent=1))
    (HERE / "review_current.json").write_text(json.dumps(rc, indent=1))
    print(json.dumps({"totals": {G: {k: tot[G][k] for k in ("confirmed_total", "detect_total", "median_cost")}
                                 for G in GROUPS},
                      "G3": ev["verdict_G3"], "G2vsG1": ev["verdict_G2_vs_G1"],
                      "current": {G: ev["current"][G] for G in GROUPS}}, indent=1))
    for x in SAMPLES:
        s = ev["samples"][x]
        print(x, "detecting", s["detecting_ids"], "strong", s["detecting_strong"], "patch_diff",
              s["patch_attributable_diff"], "coverage", s["coverage"]["candidate"],
              {G: [s["per_group"][G][sd]["first_detect"] for sd in SEEDS] for G in GROUPS},
              {G: sum(s["per_group"][G][sd]["cond_cases"] for sd in SEEDS) for G in GROUPS})


if __name__ == "__main__":
    main()
