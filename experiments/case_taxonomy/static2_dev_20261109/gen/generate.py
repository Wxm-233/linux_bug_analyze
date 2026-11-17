"""G2' and G3' with the static2 hints (static2 criteria 4.4); copied from semhint_dev_20261109/gen/generate.py,
only the group list changed. Rules, budget and seeds as round 1 (semhint criteria 五, amendments 2-3).

    python generate.py <group>      -> cases_<group>.json (logical cases), cases_<group>_<arch>.txt (executor input),
                                       lists_<group>.json {G0..G3: {seed: [case id, ...]}}

Executor tokens (harness/sh_init.c): i:<hex>  b:<fill>:<off>  o:<fill>:<bit>  f:<kind>  p:<kind>  s:self
"""
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
B = 1000
SEEDS = (1, 2, 3)
ARCHS = ("riscv", "arm64", "x86_64")
MASK = 2**64 - 1
KERNELS = {g: [f"{g.lower()}_pre", f"{g.lower()}_fix", f"{g.lower()}_ref_arm64", f"{g.lower()}_ref_x86_64"]
           for g in ("A101", "A310", "A171", "A181", "B467")}
KERNELS["CUR"] = ["cur_riscv", "cur_arm64", "cur_x86_64"]

BLACK_EXACT = {
    "reboot", "kill", "tkill", "tgkill", "rt_sigqueueinfo", "rt_tgsigqueueinfo", "pidfd_send_signal",
    "exit", "exit_group", "execve", "execveat", "clone", "clone3", "vfork", "fork",
    "mount", "umount2", "fsmount", "move_mount", "fsopen", "fsconfig", "fspick", "open_tree", "open_tree_attr",
    "mount_setattr", "pivot_root", "chroot", "fchroot", "swapon", "swapoff", "kexec_load", "kexec_file_load",
    "init_module", "finit_module", "delete_module", "settimeofday", "clock_settime", "clock_adjtime", "adjtimex",
    "acct", "quotactl", "quotactl_fd", "syslog", "sethostname", "setdomainname", "ptrace", "process_vm_writev",
    "prlimit64", "setrlimit", "rt_sigsuspend", "rt_sigreturn", "pause", "setsid", "setpgid",
    "setuid", "setgid", "setreuid", "setregid", "setresuid", "setresgid", "setfsuid", "setfsgid", "setgroups",
    "capset", "unshare", "setns", "seccomp", "bpf", "personality", "vhangup",
    "io_uring_setup", "io_uring_enter", "io_uring_register", "userfaultfd"}

GEN_INT = [0, 1, 2, -1, 7, 8, 16, 64, 255, 256, 4096, 65535, 65536, 2**31 - 1, 2**31, 2**32 - 1, 2**32,
           2**63 - 1, 2**63, "small", "rand64"]
GEN_SIZE = [0, 1, 8, 64, 4096, 8192, 2**31, 2**32, -1, "rand16"]
GEN_FLAGS = ["bit", "rand32", 0, -1]
FDS = ["file", "dir", "piperd", "pipewr", "ustream", "udgram", "eventfd", "memfd", "udp", "neg", "unopen"]
FILLS = ("z", "a", "g")

SIZE_RE = re.compile(r"(len|size|count|nbytes|^sz$|length|^nr|vlen|bufsiz|iovcnt|cnt|^n$|^num)", re.I)
FLAG_RE = re.compile(r"(flag|mode|cmd|^op$|how|advice|prot|which|option|type|whence|resource|policy|level|"
                     r"optname|domain|protocol|family|behavior|mask|events|^sig$|^code$|clock|^id$|idtype|attr)", re.I)
PID_RE = re.compile(r"^(pid|tgid|upid|ppid|pgid|sid|tid|pid1|pid2)$")
UID_RE = re.compile(r"^(uid|gid|euid|ruid|suid|egid|rgid|sgid|user|group|owner)$")
FD_RE = re.compile(r"^(fd|fd_in|fd_out|oldfd|newfd|epfd|dfd|olddfd|newdfd|ufd|fdin|fdout|mfd|pidfd|dirfd|"
                   r"fsfd|from_dfd|to_dfd|watchfd|fds?|group_fd|in_fd|out_fd|fildes|mountdirfd|mqdes)$")
ADDR_NAMES = {"addr", "start", "brk", "uaddr", "uaddr2", "new_addr", "old_addr", "start_addr", "addr_hint"}


def width_of(ptype):
    t = ptype.replace("const ", "").strip()
    if t.endswith("*"):
        return 64
    if t == "umode_t":
        return 16
    if "long" in t or t in ("size_t", "ssize_t", "loff_t", "off_t", "aio_context_t", "u64", "__u64", "s64",
                            "cap_user_header_t", "cap_user_data_t"):
        return 64
    return 32


def pclass(pname, ptype):
    t = ptype.replace("const ", "").strip()
    if t in ("cap_user_header_t", "cap_user_data_t"):  # pointer typedefs
        return "ptr"
    if t.endswith("*"):
        return "path" if re.search(r"\bchar \*$", t) else "ptr"
    if FD_RE.match(pname):
        return "fd"
    if pname in ADDR_NAMES and width_of(ptype) == 64:
        return "addr"
    if PID_RE.match(pname):
        return "pid"
    if UID_RE.match(pname):
        return "uid"
    if SIZE_RE.search(pname):
        return "size"
    if FLAG_RE.search(pname):
        return "flags"
    return "int"


def hexv(v, ptype=None):
    v &= MASK
    if ptype is not None:
        w = width_of(ptype)
        v &= (1 << w) - 1
    return "i:%x" % v


def generic(rng, pname, ptype):
    c = pclass(pname, ptype)
    if c == "int":
        v = rng.choice(GEN_INT)
        v = rng.randrange(256) if v == "small" else rng.getrandbits(64) if v == "rand64" else v
        return hexv(v, ptype)
    if c == "size":
        v = rng.choice(GEN_SIZE)
        return hexv(rng.randrange(65536) if v == "rand16" else v, ptype)
    if c == "flags":
        v = rng.choice(GEN_FLAGS)
        v = (1 << rng.randrange(32)) if v == "bit" else rng.getrandbits(32) if v == "rand32" else v
        return hexv(v, ptype)
    if c == "pid":
        return rng.choice(["i:0", "s:self", hexv(-1, ptype), "i:%x" % 99999])
    if c == "uid":
        return rng.choice(["i:0", hexv(-1, ptype), "i:%x" % 65534])
    if c == "ptr":
        k = rng.randrange(5)
        if k == 0:
            return "i:0"
        if k == 4:
            return "i:%x" % rng.getrandbits(64)
        return "b:%s:%d" % (rng.choice(FILLS), (0, 1, 8184)[k - 1])
    if c == "addr":
        k = rng.randrange(6)
        if k == 0:
            return "i:0"
        if k in (1, 2):
            return "b:%s:%d" % (rng.choice(FILLS), k - 1)
        return ["i:40000000", "i:100000000", "i:%x" % rng.getrandbits(64)][k - 3]
    if c == "path":
        return "p:" + rng.choice(["f", "d", "nx", "empty", "null"])
    if c == "fd":
        return "f:" + rng.choice(FDS + (["atcwd"] if "dfd" in pname or pname == "dirfd" else []))
    raise ValueError(c)


def hint_token(rng, tok):
    if tok.startswith("o:"):
        return "o:%s:%s" % (rng.choice(FILLS), tok[2:])
    return tok


def template(rng, params):
    ai = next((i for i, (n, t) in enumerate(params) if pclass(n, t) == "addr"), None)
    li = next((i for i, (n, t) in enumerate(params) if pclass(n, t) == "size"), None)
    if ai is None or li is None:
        return "none"
    return rng.choice(["none", f"occ:{ai}:{li}", f"adj:{ai}:{li}"])


RAW_PARAMS = [["nr", "long"]] + [[f"a{i}", "long"] for i in range(6)]


def make_case(rng, sc, params, hints, use_hints):
    args = [generic(rng, n, t) for n, t in params]
    if sc == "raw_nr":
        v = rng.choice(GEN_INT)
        v = rng.randrange(256) if v == "small" else rng.getrandbits(64) if v == "rand64" else v
        v = (v + 2**63) % 2**64 - 2**63  # signed 64-bit (amendment 2)
        args[0] = "r:%d" % v if v >= 0 else "i:%x" % (v & MASK)
    if use_hints and hints:
        sites = hints
        assigned = set()
        if rng.random() < 0.5:
            s = rng.choice(sites)
            for p, vs in s.items():
                args[int(p)] = hint_token(rng, rng.choice(vs))
                assigned.add(int(p))
        union = {}
        for s in sites:
            for p, vs in s.items():
                union.setdefault(int(p), set()).update(vs)
        for p, vs in sorted(union.items()):
            if p not in assigned and rng.random() < 0.5:
                args[p] = hint_token(rng, rng.choice(sorted(vs)))
    tmpl = "none" if sc == "raw_nr" else template(rng, params)
    return {"sc": sc, "args": args, "tmpl": tmpl}


def main():
    group = sys.argv[1]
    h = json.loads((HERE / f"hints_{group}.json").read_text())
    nrt = json.loads((HERE / "nr_tables.json").read_text())
    vt = json.loads((HERE.parents[1] / "twostage_dev_20261109/version_tables.json").read_text())
    tables = [set(vt[k]) for k in KERNELS[group]]
    common = set.intersection(*tables)
    excluded = {"blacklist": [], "no_entry": [], "no_number": []}
    U = []
    for sc in sorted(common):
        if sc in BLACK_EXACT:
            excluded["blacklist"].append(sc)
        elif sc not in h["entries"]:
            excluded["no_entry"].append(sc)
        elif any(sc not in nrt[a] for a in ARCHS):
            excluded["no_number"].append(sc)
        else:
            U.append(sc)
    U.append("raw_nr")
    T = [s for s in h["T"] if s in U]
    params = {sc: h["entries"][sc] for sc in U if sc != "raw_nr"}
    params["raw_nr"] = RAW_PARAMS
    hints = {sc: [s["values"] for s in h["sites"].get(sc, [])] for sc in T if sc != "raw_nr"}
    if "raw_nr" in T:
        hints["raw_nr"] = [{"0": h["raw_nr"]["values"]}]
    NR = {}
    for a in ARCHS:
        v = h["NR_syscalls"].get(a)
        NR[a] = v if isinstance(v, int) else max(nrt[a].values()) + 1

    cases, key2id, lists = [], {}, {}
    for G in ("G2", "G3"):
        lists[G] = {}
        for seed in SEEDS:
            rng = random.Random(f"{group}/{G}/{seed}")
            order_u = U[:]
            rng.shuffle(order_u)
            if G == "G0" or not T:
                target = []
            elif G == "G1":
                target = rng.sample(U, len(T))
            else:
                target = T[:]
                rng.shuffle(target)
            ids, iu, it = [], 0, 0
            for i in range(B):
                if target and i % 5 != 4:
                    sc = target[it % len(target)]
                    it += 1
                    use = G == "G3"
                else:
                    sc = order_u[iu % len(order_u)]
                    iu += 1
                    use = False
                c = make_case(rng, sc, params[sc], hints.get(sc), use)
                key = json.dumps(c, sort_keys=True)
                if key not in key2id:
                    key2id[key] = len(cases) + 1
                    cases.append(dict(c, id=len(cases) + 1))
                ids.append(key2id[key])
            lists[G][str(seed)] = ids

    for a in ARCHS:
        lines = []
        for c in cases:
            args = list(c["args"])
            if c["sc"] == "raw_nr":
                t = args[0]
                nr = NR[a] + int(t[2:]) if t.startswith("r:") else int(t[2:], 16) - 2**64
                nr = (nr + 2**63) % 2**64 - 2**63
                args = args[1:]
            else:
                nr = nrt[a][c["sc"]]
            args = (args + ["i:0"] * 6)[:6]
            lines.append(f"{c['id']} {nr} {c['tmpl']} " + " ".join(args))
        (HERE / f"cases_{group}_{a}.txt").write_text("\n".join(lines) + "\n")
    meta = {"group": group, "B": B, "seeds": SEEDS, "U": U, "T": T, "excluded": excluded, "NR_syscalls": NR,
            "params": params, "classes": {sc: [pclass(n, t) for n, t in ps] for sc, ps in params.items()},
            "cases": cases}
    (HERE / f"cases_{group}.json").write_text(json.dumps(meta, indent=0))
    (HERE / f"lists_{group}.json").write_text(json.dumps(lists))
    print(group, "U", len(U), "T", len(T), "cases", len(cases), "excluded", {k: len(v) for k, v in excluded.items()})


if __name__ == "__main__":
    main()
