"""Per-architecture compile-time values of object-like boundary macros and enum constants (criteria 4.5,
amendment 2 for NR_syscalls). Runs in WSL.

    python3 macro_values.py <group> <facts.json.gz> -> /root/work/semhint/values/<group>.json
        {"<arch>": {"<name>": int | "nonconst" | "undefined"}, "builds": {...}}

For each name, a probe file includes a fixed set of headers and statically initialises an unsigned 64-bit object
from the name; it is compiled with the flags of mm/mmap.o from that build (-S) and the value is read back from the
assembly. Names are probed in batches; a batch with errors is split by the reported line numbers and the remainder
recompiled, so every name gets its own verdict.
"""
import gzip
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAMES = json.loads((HERE / "boundary_names.json").read_text())
B = "/root/work/difftest/build"
BUILDS = {g: {"riscv": f"{B}/{g}_pre", "arm64": f"{B}/{g}_ref_arm64", "x86_64": f"{B}/{g}_ref_x86_64"}
          for g in ("A101", "A310", "A171", "A181", "B467")}
BUILDS["CUR"] = {a: f"/root/work/boundary_build/{a}_defconfig" for a in ("riscv", "arm64", "x86_64")}
HEADERS = ["linux/kernel.h", "linux/mm.h", "linux/mman.h", "linux/sched.h", "linux/uaccess.h", "linux/syscalls.h",
           "linux/futex.h", "linux/perf_event.h", "linux/socket.h", "net/sock.h", "linux/fs.h", "linux/elf.h",
           "linux/compat.h", "asm/unistd.h", "asm/processor.h", "asm/pgtable.h", "asm/page.h", "asm/elf.h"]
VALRE = re.compile(r"^__shv_(\d+):\s*$")
DATARE = re.compile(r"^\s*\.(quad|xword|dword|8byte)\s+(\S+)")


def base_cmd(build):
    line = Path(build, "mm/.mmap.o.cmd").read_text().splitlines()[0]
    cmd = shlex.split(line.split(":=", 1)[1])
    out, skip = [], False
    for x in cmd:
        if skip:
            skip = False
            continue
        if x == "-o":
            skip = True
            continue
        if x == "-c" or x.endswith("mm/mmap.c") or x.startswith("-Wp,-M") or x.startswith("-Werror"):
            continue
        out.append(x)
    return out + ["-ferror-limit=0", "-Wno-error"]


def compile_batch(build, cmd, names, kinds, extra=None):
    lines = [f"#include <{h}>" for h in HEADERS]
    if extra:
        lines += [f"#if __has_include(<{extra}>)", f"#include <{extra}>", "#endif"]
    first = len(lines) + 1
    for i, n in enumerate(names):
        e = f"__attribute__((used)) const unsigned long long __shv_{i} = (unsigned long long)({n});"
        if kinds.get(n) == "macro":
            lines.append(f"#ifdef {n}\n{e}\n#else\n#error SH_UNDEF_{i}\n#endif")
        else:
            lines.append(f"{e} /* {n} */")
    src = "\n".join(lines) + "\n"
    with tempfile.NamedTemporaryFile("w", suffix=".c", delete=False, dir="/tmp") as fh:
        fh.write(src)
        path = fh.name
    try:
        r = subprocess.run(cmd + ["-S", "-o", "-", path], cwd=build, capture_output=True, text=True)
    finally:
        os.unlink(path)
    if r.returncode == 0:
        vals, cur = {}, None
        for l in r.stdout.splitlines():
            m = VALRE.match(l)
            if m:
                cur = int(m.group(1))
                continue
            m = DATARE.match(l)
            if m and cur is not None:
                try:
                    vals[names[cur]] = int(m.group(2), 0) & (2**64 - 1)
                except ValueError:
                    vals[names[cur]] = "nonconst"
                cur = None
        return {n: vals.get(n, "nonconst") for n in names}, None
    # map error lines back to names: probe line k (1-based) of name i
    bad, undef = set(), set()
    starts = []
    ln = first
    for n in names:
        starts.append(ln)
        ln += 5 if kinds.get(n) == "macro" else 1
    for m in re.finditer(r"\.c:(\d+):\d+: (?:fatal )?error: (.*)", r.stderr):
        L = int(m.group(1))
        for i, s in enumerate(starts):
            if s <= L < s + (5 if kinds.get(names[i]) == "macro" else 1):
                (undef if "SH_UNDEF" in m.group(2) or "undeclared" in m.group(2) else bad).add(i)
                break
        else:
            return None, r.stderr[-2000:]  # error in the fixed headers: whole build unusable
    return {"bad": bad, "undef": undef}, None


def probe(build, names, kinds, extra=None):
    cmd = base_cmd(build)
    res = {}
    todo = list(names)
    for _ in range(4):
        if not todo:
            break
        out, err = compile_batch(build, cmd, todo, kinds, extra)
        if err:
            return None, err
        if "bad" not in out:
            res.update(out)
            todo = []
            break
        for i in out["undef"]:
            res[todo[i]] = "undefined"
        for i in out["bad"]:
            res[todo[i]] = "nonconst"
        todo = [n for i, n in enumerate(todo) if i not in out["bad"] and i not in out["undef"]]
    for n in todo:
        res.setdefault(n, "nonconst")
    return res, None


def main():
    group, facts = sys.argv[1], sys.argv[2]
    d = json.load(gzip.open(facts, "rt"))
    kinds = NAMES["kind"]
    names = set()
    for n in NAMES["macro"]:
        md = d["macros"].get(n)
        if md is None or not md["fl"]:
            names.add(n)
    names |= {n for n, k in kinds.items() if k == "enum_constant"}
    names.add("NR_syscalls")
    kinds = dict(kinds, NR_syscalls="macro")
    names = sorted(names)
    chunks = [names[i:i + 60] for i in range(0, len(names), 60)]
    out = {"group": group, "builds": BUILDS[group], "names": len(names), "headers": HEADERS}
    defhdr = {}
    for n, md in d["macros"].items():
        f = md.get("file") or ""
        m = re.match(r"(?:include/|arch/riscv/include/)(.*\.h)$", f)
        if m and not m.group(1).startswith(("generated/", "uapi/")):
            defhdr[n] = m.group(1)
    retried = {}
    out["pass2_resolved"] = retried
    for arch, build in BUILDS[group].items():
        with ThreadPoolExecutor(12) as ex:
            parts = list(ex.map(lambda c: probe(build, c, kinds), chunks))
        vals = {}
        for p, err in parts:
            if err:
                print(arch, "HEADER ERROR", err[-600:])
                sys.exit(3)
            vals.update(p)
        # pass 2 (criteria 4.5 "固定的一组头文件" plus the name's own riscv header): undefined names again
        byhdr = {}
        for n, v in vals.items():
            if v == "undefined" and defhdr.get(n):
                byhdr.setdefault(defhdr[n], []).append(n)
        def p2(item):
            h, ns = item
            r, err = probe(build, ns, kinds, h)
            return ns, r if not err else {}
        with ThreadPoolExecutor(12) as ex:
            for ns, r in ex.map(p2, byhdr.items()):
                for n in ns:
                    if r.get(n) not in (None, "undefined"):
                        vals[n] = r[n]
                        retried[arch] = retried.get(arch, 0) + 1
        out[arch] = vals
        st = {}
        for v in vals.values():
            k = v if isinstance(v, str) else "const"
            st[k] = st.get(k, 0) + 1
        print(group, arch, st, "NR_syscalls", vals.get("NR_syscalls"), "TASK_SIZE_MAX", vals.get("TASK_SIZE_MAX"))
    os.makedirs("/root/work/semhint/values", exist_ok=True)
    Path(f"/root/work/semhint/values/{group}.json").write_text(json.dumps(out, indent=0))


if __name__ == "__main__":
    main()
