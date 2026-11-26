#!/usr/bin/env python3
"""Reusable kernel builds (kbuild_reuse_20261115 criteria 二). Run in WSL as root.

    python3 kbuild.py get <rev> <arch> <profile> [--mut FILE:NAME] [--force] [--tag T]
        print the image path; build only if (rev, arch, profile, mutation[, tag]) is not registered
    python3 kbuild.py import <rev> <arch> <profile> <mut|-> <img> [--config P] [--vmlinux P] [--note TEXT]
        copy an existing image into images/ and register it (the original file is not touched)
    python3 kbuild.py list

Layout under /root/work/kbuild/:
    pristine/<rev12>/                      git archive of the revision, never modified
    trees/<rev12>_<arch>_<profile>/src     cp -al of pristine; files are changed only by unlink + write
    trees/<rev12>_<arch>_<profile>/out     persistent O= build directory
    images/                                registered images; registry.json
"""
import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path("/root/work/kbuild")
KSRC = Path("/root/repos/linux")
ENV = dict(os.environ, PATH="/usr/lib/llvm-18/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin")
KARCH = {"riscv": "riscv", "arm64": "arm64", "x86_64": "x86", "arm": "arm", "powerpc": "powerpc"}
DEFC = {"riscv": "defconfig", "arm64": "defconfig", "x86_64": "x86_64_defconfig", "arm": "multi_v7_defconfig",
        "powerpc": "ppc64le_defconfig"}
# widebuild_20261125: arm and powerpc added; powerpc builds vmlinux only (its zImage boot wrapper is not needed here)
IMG = {"riscv": "arch/riscv/boot/Image", "arm64": "arch/arm64/boot/Image", "x86_64": "arch/x86/boot/bzImage",
       "arm": "arch/arm/boot/zImage", "powerpc": "vmlinux"}


def log(*a):
    print("[kbuild]", *a, file=sys.stderr, flush=True)


def sh(cmd, cwd=None, out=None):
    with open(out, "a") if out else open(os.devnull, "w") as f:
        return subprocess.run(cmd, cwd=cwd, env=ENV, stdout=f, stderr=subprocess.STDOUT).returncode


def rev12(rev):
    return subprocess.run(["git", "-C", str(KSRC), "rev-parse", "--short=12", rev], capture_output=True, text=True,
                          check=True).stdout.strip()


def load_reg():
    p = ROOT / "registry.json"
    return json.loads(p.read_text()) if p.exists() else {}


def save_reg(reg):
    p = ROOT / "registry.json"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(reg, indent=1, sort_keys=True))
    tmp.replace(p)


def regkey(r, arch, profile, mut, tag=None):
    return "|".join([r, arch, profile, mut or "-"] + ([tag] if tag else []))


def replace_file(path, text):
    """Never write through a hard link: unlink, then create a new file (fresh mtime)."""
    path.unlink()
    path.write_text(text)


def pristine(r):
    d = ROOT / "pristine" / r
    if not (d / ".complete").exists():
        log("extracting", r)
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True)
        p1 = subprocess.Popen(["git", "-C", str(KSRC), "archive", "--format=tar", r], stdout=subprocess.PIPE)
        subprocess.run(["tar", "-x", "-C", str(d)], stdin=p1.stdout, check=True)
        p1.wait()
        (d / ".complete").write_text(r)
    return d


def apply_edit(src, e, backup):
    """e: {file, anchor, insert_before | new, region_start?}. Returns False if the anchor is not unique."""
    f = src / e["file"]
    s = f.read_text()
    a, b = 0, len(s)
    if e.get("region_start"):
        a = s.index(e["region_start"])
        b = s.index("\n}\n", a) + 3
    seg = s[a:b]
    if seg.count(e["anchor"]) != 1:
        log("anchor count", seg.count(e["anchor"]), "in", e["file"])
        return False
    new = e["insert_before"] + e["anchor"] if "insert_before" in e else e["new"]
    backup.setdefault(e["file"], s)
    replace_file(f, s[:a] + seg.replace(e["anchor"], new) + s[b:])
    return True


def revert(src, backup):
    for rel, text in backup.items():
        replace_file(src / rel, text)


def tree(r, arch, profile, prof):
    t = ROOT / "trees" / f"{r}_{arch}_{profile}"
    src, out = t / "src", t / "out"
    if not (t / ".src_ready").exists():
        shutil.rmtree(t, ignore_errors=True)
        t.mkdir(parents=True)
        subprocess.run(["cp", "-al", str(pristine(r)), str(src)], check=True)
        for e in prof.get("source_edits", []):
            if not apply_edit(src, e, {}):
                sys.exit(f"profile {profile}: source edit failed")
        (t / ".src_ready").write_text(json.dumps(prof.get("source_edits", [])))
    if not (out / ".config").exists():
        out.mkdir(exist_ok=True)
        lg = t / "config.log"
        ka = KARCH[arch]
        if sh(["make", "-C", str(src), f"O={out}", f"ARCH={ka}", "LLVM=1", DEFC[arch]], out=lg):
            sys.exit("defconfig failed, see " + str(lg))
        cfg = ["-e" if v == "y" else "-d" for v in prof["config"].values()]
        args = []
        for (k, v), flag in zip(prof["config"].items(), cfg):
            args += [flag, k]
        sh([str(src / "scripts/config"), "--file", str(out / ".config")] + args, out=lg)
        sh(["make", "-C", str(src), f"O={out}", f"ARCH={ka}", "LLVM=1", "olddefconfig"], out=lg)
        for k, v in prof["config"].items():
            have = f"CONFIG_{k}=y" in (out / ".config").read_text()
            if have != (v == "y"):
                log("WARNING config", k, "wanted", v, "got", "y" if have else "n")
    return t, src, out


def build(t, src, out, arch, logname):
    lg = t / logname
    t0 = time.time()
    rc = sh(["make", "-C", str(src), f"O={out}", f"ARCH={KARCH[arch]}", "LLVM=1", "-j20",
             os.path.basename(IMG[arch]), "vmlinux"], out=lg)
    txt = lg.read_text(errors="replace")
    return rc, round(time.time() - t0), txt.count(" CC "), txt.count("macro redefined")


def cmd_get(a):
    profiles = json.loads((HERE / "profiles.json").read_text())
    prof = profiles[a.profile]
    r = rev12(a.rev)
    mut, spec = None, None
    if a.mut:
        mfile, mname = a.mut.split(":")
        mp = Path(mfile) if os.path.isabs(mfile) else HERE / "mutations" / mfile
        spec = json.loads(mp.read_text())[mname][a.arch]
        mut = f"{mp.stem}:{mname}"
    key = regkey(r, a.arch, a.profile, mut, a.tag)
    reg = load_reg()
    if key in reg and not a.force and Path(reg[key]["img"]).exists():
        log("registered", key)
        print(reg[key]["img"])
        return 0
    (ROOT / "locks").mkdir(parents=True, exist_ok=True)
    with open(ROOT / "locks" / f"{r}_{a.arch}_{a.profile}.lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        t, src, out = tree(r, a.arch, a.profile, prof)
        backup = {}
        stamp = time.strftime("%Y%m%d_%H%M%S")
        try:
            if spec:
                for e in spec["edits"]:
                    if not apply_edit(src, e, backup):
                        log("MUTATION NOT APPLIED", mut)
                        return 2
                pc = spec["precheck"]
                lg = t / f"precheck_{stamp}.log"
                obj = pc["obj"][:-2] + ".i"
                sh(["make", "-C", str(src), f"O={out}", f"ARCH={KARCH[a.arch]}", "LLVM=1", obj], out=lg)
                ifile = out / obj
                ok = False
                if ifile.exists():
                    txt = ifile.read_text(errors="replace")
                    if pc.get("region_start"):  # search only inside one function of the preprocessed file
                        i = txt.find(pc["region_start"])
                        txt = txt[i:txt.index("\n}\n", i) + 3] if i >= 0 else ""
                    found = bool(re.search(pc["regex"], txt))
                    ok = bool(txt) and (not found if pc.get("absent") else found)
                if not ok:
                    log("PRECHECK FAILED", mut, "regex", pc["regex"], "not in", obj, "(see", lg, ")")
                    return 3
                log("precheck ok", mut, obj)
            rc, secs, ncc, redef = build(t, src, out, a.arch, f"build_{stamp}.log")
            if rc:
                log("BUILD FAILED", key, f"{secs}s", "see", t / f"build_{stamp}.log")
                return 4
            name = key.replace("|", "_").replace(":", "-")
            img = ROOT / "images" / f"{name}.img"
            img.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(out / IMG[a.arch], img)
            shutil.copy(out / ".config", img.with_suffix(".config"))
            ent = {"img": str(img), "config": str(img.with_suffix(".config")), "built": stamp, "seconds": secs,
                   "recompiled": ncc, "macro_redefined": redef, "source": "kbuild",
                   "mutation_sha": hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:16] if spec else None}
            if prof.get("keep_vmlinux"):
                shutil.copy(out / "vmlinux", img.with_suffix(".vmlinux"))
                ent["vmlinux"] = str(img.with_suffix(".vmlinux"))
            reg = load_reg()
            reg[key] = ent
            save_reg(reg)
            log("BUILD OK", key, f"{secs}s", f"recompiled={ncc}", f"macro_redefined={redef}")
            print(img)
            return 0
        finally:
            if backup:
                revert(src, backup)
                log("reverted", list(backup))


def cmd_import(a):
    r = rev12(a.rev)
    key = regkey(r, a.arch, a.profile, None if a.mut == "-" else a.mut)
    name = key.replace("|", "_").replace(":", "-")
    img = ROOT / "images" / f"{name}.img"
    img.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(a.img, img)
    ent = {"img": str(img), "source": "import", "from": a.img, "note": a.note,
           "imported": time.strftime("%Y%m%d_%H%M%S")}
    for k in ("config", "vmlinux"):
        p = getattr(a, k)
        if p:
            dst = img.with_suffix("." + k)
            shutil.copy(p, dst)
            ent[k] = str(dst)
    reg = load_reg()
    reg[key] = ent
    save_reg(reg)
    log("imported", key)
    print(img)


def cmd_list(a):
    for k, v in sorted(load_reg().items()):
        print(k, v.get("source"), v.get("built") or v.get("imported"), v["img"])


def main():
    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest="cmd", required=True)
    g = sp.add_parser("get")
    g.add_argument("rev"), g.add_argument("arch"), g.add_argument("profile")
    g.add_argument("--mut"), g.add_argument("--force", action="store_true"), g.add_argument("--tag")
    i = sp.add_parser("import")
    for x in ("rev", "arch", "profile", "mut", "img"):
        i.add_argument(x)
    i.add_argument("--config"), i.add_argument("--vmlinux"), i.add_argument("--note", default="")
    sp.add_parser("list")
    a = p.parse_args()
    sys.exit({"get": cmd_get, "import": cmd_import, "list": cmd_list}[a.cmd](a) or 0)


if __name__ == "__main__":
    main()
