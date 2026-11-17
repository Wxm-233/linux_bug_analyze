"""(Copied from rankprune_dev_20261110/compare.py; logs under /root/work/casemodel/runs.) Stability, capability exclusion and majority verdicts per riscv kernel (criteria 七). Runs in WSL.

    python3 compare.py <group>...  -> runs/<group>/compare.json

Verdicts per (riscv kernel, case id): consistent | odd_strong | odd_weak | ref_split | no_ref | excluded_cap |
excluded_env | unstable.  Observation compared = (r, t, b, pool) exactly as printed by the executor.
"""
import gzip
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "casemodel_dev_20261110" / "harness"))  # casemodel parse_log keeps "s"
from parse_log import parse_log  # noqa: E402

W = Path("/root/work/diverse")
KMSG = re.compile(r"(?<=[^\n])\[\s*\d+\.\d+\][^\n]*\n")  # amendment 2: kernel message inside an output line
D = "/root/work/difftest/build"
HW_CFG = {"riscv": ["RISCV_PMU_SBI", "RISCV_PMU_LEGACY"], "arm64": ["ARM_PMUV3", "HW_PERF_EVENTS"],
          "x86_64": ["CPU_SUP_INTEL", "CPU_SUP_AMD"]}
M = (1 << 64) - 1


def kernels(g):
    if g == "CUR":
        B = "/root/work/boundary_build"
        return {"cur_riscv": ("riscv", f"{B}/riscv_defconfig"), "cur_arm64": ("arm64", f"{B}/arm64_defconfig"),
                "cur_x86_64": ("x86_64", f"{B}/x86_64_defconfig")}
    l = g.lower()
    return {f"{l}_pre": ("riscv", f"{D}/{g}_pre"), f"{l}_fix": ("riscv", f"{D}/{g}_fix"),
            f"{l}_ref_arm64": ("arm64", f"{D}/{g}_ref_arm64"), f"{l}_ref_x86_64": ("x86_64", f"{D}/{g}_ref_x86_64")}


def is_hw_pmu(n):
    return n in ("cpu", "cpu_core", "cpu_atom") or n.startswith("armv8") or n.startswith("armv9")


def xorshift(s):
    s ^= (s << 13) & M
    s ^= s >> 7
    s ^= (s << 17) & M
    return s


def graph_word0_is_64(case):
    """first graph word of the first g buffer in argument order is the constant 64 (executor fills g buffers in
    argument order, 8 words each, from the case-id seeded xorshift64)"""
    s = (case["id"] * 0x9E3779B97F4A7C15 + 1) & M
    for tok in case["args"]:
        if tok.startswith(("b:g:", "o:g:")):
            s = xorshift(s)
            return not (s & 1)
    return None


def perf_needs_hw(case):
    """criteria 七.2: perf_event_open whose attr buffer starts with type 0, 3 or 4"""
    if case["sc"] != "perf_event_open":
        return False
    tok = case["args"][0]
    if tok.startswith("t:"):  # casemodel C1: structured attr, type field = mutated value or 0
        b = case.get("structs", [])[int(tok[2:])]
        v = b.get("set", {}).get("type")
        t = int(v[1], 16) if v and v[0] == "int" else 0
        return (t & 0xFFFFFFFF) in (0, 3, 4)
    if not tok.startswith(("b:", "o:")):
        return False
    _, fill, sub = tok.split(":")
    off = int(sub) if tok.startswith("b:") else 0
    if fill == "z":
        return True
    if fill == "a":
        return False
    # g: only the first g buffer of the case can be argument 0 here (argument order)
    if off == 0:
        return False  # 64 or a pool address: type is 64 or the address' low 32 bits (never 0/3/4 in practice)
    if off == 1:
        return bool(graph_word0_is_64(case))  # bytes 1..4 of the word 64 are zero
    return False  # offset 8184: 0xAA bytes


def main():
    for g in sys.argv[1:]:
        meta = json.loads((HERE / "gen" / f"cases_{g}.json").read_text())
        cases = {str(c["id"]): c for c in meta["cases"]}
        ks = kernels(g)
        obs, probe, cfg, complete, taint, herr = {}, {}, {}, {}, {}, {}
        repaired = {}
        for k, (arch, bdir) in ks.items():
            cfg[k] = Path(bdir, ".config").read_text()
            runs = []
            for i in (1, 2, 3):
                text = (W / "runs" / g / f"{k}.run{i}.log").read_bytes().replace(b"\x00", b"").decode("utf-8", "replace")
                text, nrep = KMSG.subn("", text)
                repaired[f"{k}.run{i}"] = nrep
                p = parse_log(text)
                runs.append(p)
            complete[k] = [r["complete"] for r in runs]
            taint[k] = [r["taint_changed"] for r in runs]
            herr[k] = sum(len(r.get("harness_errors", [])) for r in runs)
            probe[k] = runs[0]["probe"]
            obs[k] = [{cid: json.dumps(v) for cid, v in r["cases"].items()} for r in runs]
        hw = {k: any(is_hw_pmu(n) for n in probe[k].get("pmu_devices", [])) for k in ks}
        cap_cfg = {k: any(f"CONFIG_{o}=y" in cfg[k] for o in HW_CFG[ks[k][0]]) for k in ks}
        stable = {}
        unstable = []
        for cid in cases:
            vals = {}
            ok = True
            for k in ks:
                vs = {o.get(cid, "missing") for o in obs[k]}
                if len(vs) != 1:
                    ok = False
                    break
                vals[k] = vs.pop()
            if ok:
                stable[cid] = vals
            else:
                unstable.append(cid)
        refs = [k for k in ks if ks[k][0] != "riscv"]
        rvs = [k for k in ks if ks[k][0] == "riscv"]
        verdicts = {r: {} for r in rvs}
        for cid, c in cases.items():
            if cid not in stable:
                for r in rvs:
                    verdicts[r][cid] = "unstable"
                continue
            vals = stable[cid]
            need = perf_needs_hw(c)

            def excl(k):
                if need and not hw[k]:
                    return "excluded_cap" if not cap_cfg[k] else "excluded_env"
                return None

            comp = [k for k in refs if not excl(k)]
            for r in rvs:
                e = excl(r)
                if e:
                    verdicts[r][cid] = e
                elif not comp:
                    verdicts[r][cid] = "no_ref"
                elif len({vals[k] for k in comp}) > 1:
                    verdicts[r][cid] = "ref_split"
                elif vals[r] == vals[comp[0]]:
                    verdicts[r][cid] = "consistent"
                else:
                    verdicts[r][cid] = "odd_strong" if len(comp) == 2 else "odd_weak"
        summary = {r: {} for r in rvs}
        for r in rvs:
            for v in verdicts[r].values():
                summary[r][v] = summary[r].get(v, 0) + 1
        out = {"group": g, "kernels": {k: v[0] for k, v in ks.items()}, "complete": complete, "taint_changed": taint,
               "harness_errors": herr, "repaired_lines": {k: v for k, v in repaired.items() if v}, "hw_pmu": hw, "hw_pmu_config": cap_cfg, "unstable": unstable,
               "summary": summary, "verdicts": verdicts,
               "values": {cid: stable[cid] for cid in stable
                          if any(verdicts[r][cid] in ("odd_strong", "odd_weak") for r in rvs)}}
        (HERE / "runs" / g).mkdir(parents=True, exist_ok=True)
        (HERE / "runs" / g / "compare.json").write_text(json.dumps(out, indent=0))
        print(g, "complete", complete, "unstable", len(unstable), json.dumps(summary))


if __name__ == "__main__":
    main()
