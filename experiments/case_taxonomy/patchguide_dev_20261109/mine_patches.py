"""Mine counterpart fix patches and their elements (criteria sections 3.1, 3.2).

    python3 mine_patches.py mine <repo> <since> <out.json.gz> <pathspec ...>
        commits with a "Fixes:" line touching the pathspecs, one record per commit with its hunks' elements
    (library) hunk_elements(repo, commit, paths) -> the same per-hunk elements for one commit (used for riscv fixes)
"""
import gzip
import json
import re
import subprocess
import sys

KEYWORDS = {"if", "for", "while", "switch", "return", "sizeof", "typeof", "__typeof__", "defined", "__attribute__",
            "asm", "__asm__", "else", "do", "case", "goto"}
DIAG = re.compile(r"^(pr_|printk|dev_|WARN|BUG|panic|dump_stack|trace_|lockdep_|kasan_|kcsan_|kmsan_|netdev_|"
                  r"seq_printf|snprintf|sprintf|scnprintf)")
CALL = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
FIELD = re.compile(r"(?:\.|->)\s*([A-Za-z_]\w*)\s*(?:[|&^+\-]?=)(?!=)")
ERRNO = re.compile(r"-\s*(E[A-Z0-9]+)\b")
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@ ?(.*)$")
ARCH_OF = re.compile(r"^arch/([^/]+)/")


def strip_code(line):
    """drop string/char literals and comments from one source line"""
    line = re.sub(r'"(?:\\.|[^"\\])*"', '""', line)
    line = re.sub(r"'(?:\\.|[^'\\])*'", "''", line)
    line = re.sub(r"/\*.*?\*/", " ", line)
    line = re.sub(r"/\*.*$", " ", line)
    line = re.sub(r"^\s*\*.*$", " ", line)  # continuation line of a block comment
    return re.sub(r"//.*$", " ", line)


def func_of(header):
    names = re.findall(r"([A-Za-z_]\w*)\s*\(", header)
    return names[-1] if names else None


def elements(lines, func):
    calls, fields, errnos = set(), set(), set()
    for raw in lines:
        s = strip_code(raw)
        calls |= {n for n in CALL.findall(s) if n not in KEYWORDS and n != func and not DIAG.match(n)}
        fields |= set(FIELD.findall(s))
        errnos |= set(ERRNO.findall(s))
    return {"call": calls, "field": fields, "errno": errnos}


def parse_diff(text):
    """yield (file, func, plus_lines, minus_lines) per hunk of a unified -U0 diff"""
    file, func, plus, minus, in_hunk = None, None, [], [], False

    def flush():
        if in_hunk and file:
            return (file, func, plus, minus)
        return None

    for line in text.splitlines():
        if line.startswith("diff --git "):
            r = flush()
            if r:
                yield r
            file, in_hunk, plus, minus = None, False, [], []
        elif line.startswith("+++ "):
            file = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("--- ") and not in_hunk:
            continue
        elif line.startswith("@@"):
            r = flush()
            if r:
                yield r
            m = HUNK.match(line)
            func = func_of(m.group(1)) if m else None
            plus, minus, in_hunk = [], [], True
        elif in_hunk and line.startswith("+"):
            plus.append(line[1:])
        elif in_hunk and line.startswith("-"):
            minus.append(line[1:])
    r = flush()
    if r:
        yield r


def hunk_records(diff_text):
    out, skipped = [], 0
    for file, func, plus, minus in parse_diff(diff_text):
        if not (file.endswith(".c") or file.endswith(".h")):
            continue
        if not func:
            skipped += 1
            continue
        add, rem = elements(plus, func), elements(minus, func)
        net = {k: sorted(add[k] - rem[k]) for k in add}
        m = ARCH_OF.match(file)
        out.append({"file": file, "arch": m.group(1) if m else "", "func": func, "added": net})
    return out, skipped


def hunk_elements(repo, commit, paths=()):
    diff = subprocess.run(["git", "-C", repo, "show", "--no-color", "-U0", "--format=", commit, "--", *paths],
                          capture_output=True, text=True, errors="replace", check=True).stdout
    return hunk_records(diff)[0]


def mine(repo, since, out, paths):
    fmt = "@@@COMMIT %H %ct %at %s"
    p = subprocess.Popen(["git", "-C", repo, "log", "--no-merges", f"--since={since}", "--grep=^Fixes:",
                          f"--format={fmt}", "-p", "-U0", "--no-color", "--", *paths],
                         stdout=subprocess.PIPE, text=True, errors="replace")
    commits, cur, buf, skipped = [], None, [], 0

    def close():
        nonlocal skipped
        if cur:
            hunks, sk = hunk_records("\n".join(buf))
            skipped += sk
            cur["hunks"] = [h for h in hunks if any(h["added"].values())]
            commits.append(cur)

    for line in p.stdout:
        line = line.rstrip("\n")
        if line.startswith("@@@COMMIT "):
            close()
            h, ct, at, subj = (line[10:].split(" ", 3) + [""])[:4]
            cur, buf = {"commit": h, "cdate": int(ct), "adate": int(at), "subject": subj}, []
        else:
            buf.append(line)
    close()
    if p.wait() != 0:
        raise SystemExit("git log failed")
    with gzip.open(out, "wt", encoding="utf-8") as fh:
        json.dump({"since": since, "paths": paths, "commits": commits, "hunks_without_function": skipped}, fh)
    print(f"{len(commits)} commits, {sum(len(c['hunks']) for c in commits)} hunks with added elements, "
          f"{skipped} hunks without a function name -> {out}")


if __name__ == "__main__":
    if sys.argv[1] == "mine":
        mine(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:])
