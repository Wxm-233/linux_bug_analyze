"""Per-architecture definitions at one revision (effdep2 I3, amendment 2; effdep3 J2, 二.1, 二.2). WSL, read-only on /root/repos/linux.

    python3 archscan.py <rev> <out.json.gz>
        out: {"rev", "archs": [...],
              "defs": {name: {arch|"generic": "nontrivial"|"trivial"}},
              "guards": {name: [CONFIG symbols around trivial generic definitions]},
              "selects": {arch: [Kconfig symbols selected / def_bool y]}}
"""
import gzip
import json
import re
import subprocess
import sys

REPO = "/root/repos/linux"
CMT = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)
FUNC = re.compile(r"(?m)^(?:[A-Za-z_][^;{}()#=\n]*?\b)?([A-Za-z_]\w*)\s*\(([^;{}]*?)\)\s*(?:(?:__\w+|notrace|asmlinkage)(?:\([^)]*\))?\s*)*\{")
DEFINE = re.compile(r"(?m)^[ \t]*#[ \t]*define[ \t]+([A-Za-z_]\w*)(\([^)]*\))?((?:[^\n\\]|\\.)*(?:\\\n(?:[^\n\\]|\\.)*)*)")
DIRECTIVE = re.compile(r"(?m)^[ \t]*#[ \t]*(if|ifdef|ifndef|elif|else|endif)\b([^\n]*)")
PPLINE = re.compile(r"(?m)^[ \t]*#[^\n]*$")
KEYW = {"if", "while", "for", "switch", "return", "sizeof", "else", "do", "case"}
CONST = r"[-~!(\s]*(?:\(\s*\w[\w\s\*]*\)\s*)?(?:0x[0-9a-fA-F]+|\d+\w*|[A-Z_][A-Z0-9_]*|true|false|NULL)[)\s]*"
RET_CONST = re.compile(rf"^\s*return\s*(?:{CONST})?\s*$")


def triv_body(b):
    """J2: empty, or only `return <const>;` statements once preprocessor lines are removed"""
    b = PPLINE.sub(" ", b)
    if len(b) > 600:
        return False
    stmts = [s for s in b.split(";") if s.strip()]
    return all(RET_CONST.match(s) for s in stmts)
TRIV_MACRO = re.compile(rf"^\s*(?:do\s*\{{\s*\}}\s*while\s*\(\s*0\s*\)|\(\s*\(\s*void\s*\)\s*[^;]*\)|\({{\s*\}}\)|{CONST})?\s*$")
SYM = re.compile(r"\bCONFIG_([A-Za-z0-9_]+)")


def body_end(text, i):
    depth = 0
    for m in re.finditer(r"[{}]", text[i:]):
        depth += 1 if m.group() == "{" else -1
        if depth == 0:
            return i + m.start()
    return len(text)


def guard_fn(text):
    """CONFIG symbols of the preprocessor conditions enclosing an offset"""
    import bisect
    pos, states, st = [], [], []
    for m in DIRECTIVE.finditer(text):
        kind, arg = m.group(1), m.group(2)
        if kind in ("if", "ifdef", "ifndef"):
            st = st + [frozenset(SYM.findall(arg))]
        elif kind == "elif" and st:
            st = st[:-1] + [st[-1] | frozenset(SYM.findall(arg))]
        elif kind == "endif" and st:
            st = st[:-1]
        pos.append(m.start())
        states.append(st)

    def at(off):
        i = bisect.bisect_left(pos, off) - 1
        return sorted(set().union(*states[i])) if i >= 0 and states[i] else []
    return at


def scan(text, arch, defs, guards, only=None):
    text = CMT.sub(" ", text)
    gat = guard_fn(text) if arch == "generic" else None
    for m in FUNC.finditer(text):
        name = m.group(1)
        if name in KEYW or (only is not None and name not in only):
            continue
        b0 = m.end() - 1
        b1 = body_end(text, b0)
        triv = triv_body(text[b0 + 1:b1])
        put(defs, name, arch, triv)
        if gat and triv:
            guards.setdefault(name, set()).update(gat(m.start()))
    for m in DEFINE.finditer(text):
        name, params, body = m.group(1), m.group(2), m.group(3).replace("\\\n", " ")
        if params is None and not body.strip():
            continue  # feature flag like #define __HAVE_ARCH_X
        if only is None or name in only:
            triv = bool(TRIV_MACRO.match(body))
            put(defs, name, arch, triv)
            if gat and triv:
                guards.setdefault(name, set()).update(gat(m.start()))


def read_all(p, rev, files, fn):
    for f in files:
        p.stdin.write(f"{rev}:{f}\n".encode())
        p.stdin.flush()
        hdr = p.stdout.readline().split()
        if len(hdr) < 3 or hdr[1] != b"blob":
            continue
        data = p.stdout.read(int(hdr[2]))
        p.stdout.read(1)
        fn(f, data.decode("utf-8", "replace"))


def put(defs, name, arch, triv):
    d = defs.setdefault(name, {})
    v = "trivial" if triv else "nontrivial"
    if d.get(arch) != "nontrivial":
        d[arch] = v


SELECT = re.compile(r"(?m)^\s*select\s+([A-Z0-9_]+)")
def defbool_y(text):
    """symbols defined in this Kconfig file with `def_bool y` (line scan)"""
    out, cur = set(), None
    for line in text.splitlines():
        m = re.match(r"(?:menu)?config\s+([A-Z0-9_]+)\s*$", line)
        if m:
            cur = m.group(1)
        elif line and not line[0].isspace():
            cur = None
        elif cur and re.match(r"\s+def_bool\s+y\b", line):
            out.add(cur)
    return out


def main():
    rev, out = sys.argv[1], sys.argv[2]
    allf = subprocess.run(["git", "-C", REPO, "ls-tree", "-r", "--name-only", rev], capture_output=True, text=True).stdout.split()
    files = [f for f in allf if f.startswith(("arch/", "include/linux/", "include/asm-generic/")) and f.endswith((".c", ".h"))]
    archs = sorted({f.split("/")[1] for f in files if f.startswith("arch/") and f.count("/") >= 2})
    p = subprocess.Popen(["git", "-C", REPO, "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    defs, guards = {}, {}
    read_all(p, rev, files, lambda f, t: scan(t, f.split("/")[1] if f.startswith("arch/") else "generic", defs, guards))
    only = {n for n, d in defs.items() if any(a != "generic" for a in d)}
    rest = [f for f in allf if f.endswith((".c", ".h")) and not f.startswith(
        ("arch/", "include/linux/", "include/asm-generic/", "Documentation/", "tools/", "scripts/", "samples/"))]
    read_all(p, rev, rest, lambda f, t: scan(t, "generic", defs, guards, only))
    selects = {a: set() for a in archs}
    kfiles = [f for f in allf if f.startswith("arch/") and f.split("/")[-1].startswith("Kconfig")]

    def kc(f, t):
        a = f.split("/")[1]
        if a in selects:
            selects[a].update(SELECT.findall(t))
            selects[a].update(defbool_y(t))
    read_all(p, rev, kfiles, kc)
    p.stdin.close()
    json.dump({"rev": rev, "archs": archs, "defs": defs,
               "guards": {n: sorted(g) for n, g in guards.items() if g and n in only},
               "selects": {a: sorted(s) for a, s in selects.items()}}, gzip.open(out, "wt"))
    print(rev, len(files), "+", len(rest), "files", len(kfiles), "Kconfig", len(archs), "archs", len(defs), "names")


if __name__ == "__main__":
    main()
