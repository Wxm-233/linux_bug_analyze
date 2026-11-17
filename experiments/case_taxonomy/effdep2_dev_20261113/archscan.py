"""Per-architecture definitions at one revision (effdep2 criteria I3). WSL, read-only on /root/repos/linux.

    python3 archscan.py <rev> <out.json.gz>
        out: {"rev", "archs": [...], "defs": {name: {arch|"generic": "nontrivial"|"trivial"}}}
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
KEYW = {"if", "while", "for", "switch", "return", "sizeof", "else", "do", "case"}
CONST = r"[-~!(\s]*(?:\(\s*\w[\w\s\*]*\)\s*)?(?:0x[0-9a-fA-F]+|\d+\w*|[A-Z_][A-Z0-9_]*|true|false|NULL)[)\s]*"
TRIV_BODY = re.compile(rf"^\s*(?:return\s*(?:{CONST})?;)?\s*$")
TRIV_MACRO = re.compile(rf"^\s*(?:do\s*\{{\s*\}}\s*while\s*\(\s*0\s*\)|\(\s*\(\s*void\s*\)\s*[^;]*\)|\({{\s*\}}\)|{CONST})?\s*$")


def body_end(text, i):
    depth = 0
    for m in re.finditer(r"[{}]", text[i:]):
        depth += 1 if m.group() == "{" else -1
        if depth == 0:
            return i + m.start()
    return len(text)


def scan(text, arch, defs, only=None):
    text = CMT.sub(" ", text)
    for m in FUNC.finditer(text):
        name = m.group(1)
        if name in KEYW or (only is not None and name not in only):
            continue
        b0 = m.end() - 1
        b1 = body_end(text, b0)
        triv = bool(TRIV_BODY.match(text[b0 + 1:b1]))
        put(defs, name, arch, triv)
    for m in DEFINE.finditer(text):
        name, params, body = m.group(1), m.group(2), m.group(3).replace("\\\n", " ")
        if params is None and not body.strip():
            continue  # feature flag like #define __HAVE_ARCH_X
        if only is None or name in only:
            put(defs, name, arch, bool(TRIV_MACRO.match(body)))


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


def main():
    rev, out = sys.argv[1], sys.argv[2]
    files = subprocess.run(["git", "-C", REPO, "ls-tree", "-r", "--name-only", rev, "arch", "include/linux", "include/asm-generic"],
                           capture_output=True, text=True).stdout.split()
    files = [f for f in files if f.endswith((".c", ".h"))]
    archs = sorted({f.split("/")[1] for f in files if f.startswith("arch/") and f.count("/") >= 2})
    p = subprocess.Popen(["git", "-C", REPO, "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    defs = {}
    read_all(p, rev, files, lambda f, t: scan(t, f.split("/")[1] if f.startswith("arch/") else "generic", defs))
    # amendment 2: generic definitions anywhere outside arch/ (lib/, kernel/, __weak, ...), only names some arch defines
    only = {n for n, d in defs.items() if any(a != "generic" for a in d)}
    rest = subprocess.run(["git", "-C", REPO, "ls-tree", "-r", "--name-only", rev], capture_output=True, text=True).stdout.split()
    rest = [f for f in rest if f.endswith((".c", ".h")) and not f.startswith(
        ("arch/", "include/linux/", "include/asm-generic/", "Documentation/", "tools/", "scripts/", "samples/"))]
    read_all(p, rev, rest, lambda f, t: scan(t, "generic", defs, only))
    p.stdin.close()
    json.dump({"rev": rev, "archs": archs, "defs": defs}, gzip.open(out, "wt"))
    print(rev, len(files), "+", len(rest), "files", len(archs), "archs", len(defs), "names")


if __name__ == "__main__":
    main()
