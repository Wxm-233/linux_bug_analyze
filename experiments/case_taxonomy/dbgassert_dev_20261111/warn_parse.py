"""Kernel warning events in the console logs (dbgassert criteria 四). Pure Python.

    python warn_parse.py <runs dir>...  -> <runs dir>/warnings.json  (and a printed summary)
"""
import glob
import gzip
import json
import os
import re
import sys
from pathlib import Path

START = re.compile(r"(WARNING:|BUG:|kernel BUG|INFO: possible|INFO: suspicious|Unable to handle|Oops|"
                   r"-+\[ cut here \]-+)")
TS = re.compile(r"\[\s*\d+\.\d+\]\s?")
FN = re.compile(r"(\?\s+)?\b([A-Za-z_][\w.]*)\+0x[0-9a-f]+/0x[0-9a-f]+")
SKIP = {"dump_backtrace", "show_stack", "dump_stack_lvl", "dump_stack", "__warn", "report_bug", "warn_slowpath_fmt",
        "handle_bug", "exc_invalid_op", "asm_exc_invalid_op", "__warn_printk", "bug_handler", "call_break_hook",
        "brk_handler", "do_debug_exception", "el1_dbg", "el1h_64_sync_handler", "el1h_64_sync", "do_trap_break",
        "handle_exception", "walk_stackframe", "arch_stack_walk", "__dump_stack", "print_usage_bug", "valid_state",
        "lockdep_rcu_suspicious", "__might_resched", "__might_sleep", "___might_sleep"}
CASE = re.compile(r'"id":(\d+)')


def norm_first(line):
    s = TS.sub("", line).strip()
    s = re.sub(r"CPU: \d+", "CPU: N", s)
    s = re.sub(r"PID: \d+", "PID: N", s)
    s = re.sub(r"\b(pid|preempt_count|in_atomic\(\)|irqs_disabled\(\)|non_block): ?\w+", r"\1: N", s)
    s = re.sub(r"0x[0-9a-f]+|\b[0-9a-f]{8,16}\b", "ADDR", s)
    s = re.sub(r"\b\d+\b", "N", s)
    return s[:200]


def parse(path):
    text = gzip.open(path).read().replace(b"\x00", b"").decode("utf-8", "replace")
    lines = text.splitlines()
    events, pending, phase, last_case = [], [], "boot", None
    i = 0
    while i < len(lines):
        line = lines[i]
        if "@@SH BEGIN" in line:
            phase = "cases"
        m = CASE.search(line) if line.lstrip().startswith("{") or '{"id"' in line else None
        if m and phase == "cases":
            last_case = m.group(1)
            for e in pending:
                e["case"] = last_case
            pending = []
        if "@@SH END" in line or '"taint_changed"' in line:
            for e in pending:
                e["phase"] = "cases_tail"
            pending = []
            phase = "shutdown"
        km = TS.search(line)
        if km and START.search(line[km.start():]):
            first = line[km.start():]
            if "cut here" in first:  # the informative line follows
                j = i + 1
                while j < len(lines) and j < i + 4 and not START.search(lines[j].replace("cut here", "")):
                    j += 1
                if j < len(lines) and j < i + 4:
                    first = lines[j][TS.search(lines[j]).start():] if TS.search(lines[j]) else lines[j]
                    i = j
            fns, block, j = [], [first.strip()], i + 1
            while j < len(lines) and j < i + 80:
                l2 = lines[j]
                if not TS.search(l2) or "end trace" in l2:
                    break
                if j > i + 1 and START.search(l2) and "cut here" in l2:
                    break
                block.append(TS.sub("", l2).rstrip())
                for q, f in FN.findall(l2):
                    if not q and f not in SKIP and f not in fns:
                        fns.append(f)
                j += 1
            e = {"phase": phase, "first": norm_first(first), "stack": fns[:3], "text": block[:40]}
            e["signature"] = e["first"] + " @ " + " <- ".join(fns[:3])
            events.append(e)
            if phase == "cases":
                pending.append(e)
            i = j
            continue
        i += 1
    taint = re.search(r'"taint_changed":(\w+)', text)
    return {"events": events, "complete": "@@SH END" in text, "taint_changed": taint.group(1) if taint else None,
            "cases_seen": len(set(CASE.findall(text)))}


def main():
    for d in sys.argv[1:]:
        d = Path(d)
        out, sig = {}, {}
        for f in sorted(glob.glob(str(d / "*.log.gz"))):
            k, i = re.match(r"(.*)\.run(\d)\.log\.gz", os.path.basename(f)).groups()
            p = parse(f)
            out[f"{k}.run{i}"] = p
            for e in p["events"]:
                s = sig.setdefault((e["phase"] if e["phase"] != "cases_tail" else "cases", e["signature"]), {})
                s.setdefault(k, {"runs": set(), "cases": set()})
                s[k]["runs"].add(i)
                if e.get("case"):
                    s[k]["cases"].add(e["case"])
        summary = [{"phase": ph, "signature": s, "kernels": {k: {"runs": sorted(v["runs"]), "cases": sorted(v["cases"], key=int)[:20]}
                                                           for k, v in ks.items()}}
                   for (ph, s), ks in sorted(sig.items())]
        (d / "warnings.json").write_text(json.dumps({"runs": out, "signatures": summary}, indent=1, ensure_ascii=False),
                                         encoding="utf8")
        print("==", d.name)
        for r, p in out.items():
            print("  ", r, "complete", p["complete"], "taint_changed", p["taint_changed"], "cases", p["cases_seen"],
                  "events", len(p["events"]))
        for s in summary:
            print("  [%s] %s" % (s["phase"], s["signature"][:150]))
            for k, v in s["kernels"].items():
                print("        ", k, "runs", v["runs"], "cases", v["cases"][:8])


if __name__ == "__main__":
    main()
