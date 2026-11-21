"""Kbuild evidence for blind expectations (criteria 四): reads only Makefiles/Kbuild of the source tree at df2908090cda and the
three builds' .config -- never compile_commands.json. Prints, per directory level, the lines that pull in the object or the
directory, and the config values they depend on. WSL.

    python3 kbuild_evidence.py <path.c> [...]
"""
import re
import subprocess
import sys

REPO = "/root/repos/linux"
REV = "df2908090cda"
BUILDS = {a: f"/root/work/boundary_build/{a}_defconfig/.config" for a in ("riscv", "arm64", "x86_64")}
CFG = {}
for a, p in BUILDS.items():
    vals = {}
    for ln in open(p):
        m = re.match(r"^(CONFIG_\w+)=(.*)$", ln.strip())
        if m:
            vals[m.group(1)] = m.group(2)
    CFG[a] = vals


def show(path):
    out = subprocess.run(["git", "-C", REPO, "show", f"{REV}:{path}"], capture_output=True, text=True, errors="replace")
    return out.stdout if out.returncode == 0 else None


def lines_mentioning(mk, name):
    txt = show(mk)
    if txt is None:
        return None
    txt = re.sub(r"\\\n", " ", txt)
    return [ln.strip() for ln in txt.split("\n") if re.search(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])", ln) and not ln.strip().startswith("#")]


def evidence(path):
    parts = path.split("/")
    obj = parts[-1][:-2] + ".o"
    print(f"### {path}")
    level_name = obj
    for i in range(len(parts) - 1, 0, -1):
        d = "/".join(parts[:i])
        hits = None
        for mk in (f"{d}/Makefile", f"{d}/Kbuild"):
            h = lines_mentioning(mk, level_name)
            if h:
                hits = (mk, h)
                break
        if hits is None:
            print(f"  [{d}] no line mentions {level_name}")
        else:
            print(f"  [{hits[0]}] {level_name}:")
            for ln in hits[1][:6]:
                cfgs = re.findall(r"CONFIG_\w+", ln)
                vals = " ".join(f"{c}={{{','.join(CFG[a].get(c, 'n') for a in BUILDS)}}}" for c in cfgs)
                print(f"      {ln[:150]}   {vals}")
            comp = [re.match(r"^([\w-]+)-(?:y|objs|\$\(CONFIG_\w+\))\s*[:+]?=", ln) for ln in hits[1]]
            comp = [m.group(1) for m in comp if m and m.group(1) not in ("obj", "lib", "subdir")]
            if comp and comp[0] + ".o" != level_name:
                level_name = comp[0] + ".o"
                h2 = lines_mentioning(hits[0], level_name)
                print(f"    composite -> {level_name}:")
                for ln in (h2 or [])[:4]:
                    cfgs = re.findall(r"CONFIG_\w+", ln)
                    vals = " ".join(f"{c}={{{','.join(CFG[a].get(c, 'n') for a in BUILDS)}}}" for c in cfgs)
                    print(f"      {ln[:150]}   {vals}")
        level_name = parts[i - 1] + "/"
    print("  (values listed as {riscv,arm64,x86_64})")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        evidence(p)
