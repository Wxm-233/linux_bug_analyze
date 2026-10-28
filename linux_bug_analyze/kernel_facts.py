"""Generic kernel fact collection (WSL) and fact-bundle queries (any OS).

``collect`` builds selected files of one pinned revision under one architecture/configuration and
writes a fact bundle: configuration values, per-function disassembly with relocations, and for the
requested functions their preprocessed body and early-CFG dump record. ``query`` answers registered
query kinds from a bundle only; anything it cannot answer is omitted, never defaulted.

    python3 -m linux_bug_analyze.kernel_facts collect --spec spec.json --out DIR    (in WSL)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Mapping

REPO = "/root/repos/linux"
CACHE = Path("/root/.cache/linux-bug-analyze/kernel-facts")
BUNDLE_SCHEMA = "kernel_fact_bundle_v1"
QUERY_KINDS = {"defined", "references", "may_reference", "config", "expansion_contains", "direct_write",
               "writes", "reads", "escapes", "in_init", "initcall_level", "calls", "reachable",
               "writers_count", "all_writers_in_init", "any_reader_outside_init", "constant", "build_ok",
               "macro_defined", "macro_from_arch", "object_defines_token", "macro_value", "returns_only_zero"}
INIT_SECTIONS = (".init.text", ".head.text", ".ref.text.init", ".meminit.text", ".cpuinit.text")


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _run(argv: list[str], log: list[dict[str, Any]], cwd: str | None = None, timeout: int = 3600) -> subprocess.CompletedProcess:
    started = time.monotonic()
    done = subprocess.run(argv, capture_output=True, cwd=cwd, timeout=timeout, env=dict(os.environ, LC_ALL="C"))
    log.append({"argv": argv, "returncode": done.returncode, "seconds": round(time.monotonic() - started, 3),
                "stderr_tail": done.stderr.decode("utf-8", "replace")[-600:]})
    return done


def _split_objdump(text: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        m = re.match(r"^[0-9a-f]+ <([^>]+)>:$", line)
        if m:
            current = m.group(1)
            out[current] = []
        elif current is not None and line.strip():
            out[current].append(line.rstrip())
    return out


def _function_body(text: str, name: str) -> str | None:
    """Unique top-level definition of ``name`` in preprocessed C, by brace matching; None if not unique."""
    hits = []
    for m in re.finditer(r"(?m)^[^\n;{}#]*\b" + re.escape(name) + r"\s*\(", text):
        depth_before = text.count("{", 0, m.start()) - text.count("}", 0, m.start())
        if depth_before != 0:
            continue
        open_brace = text.find("{", m.end())
        semicolon = text.find(";", m.end())
        if open_brace < 0 or (0 <= semicolon < open_brace):
            continue
        depth, i = 0, open_brace
        while i < len(text):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    hits.append(text[m.start():i + 1])
                    break
            i += 1
    return hits[0] if len(hits) == 1 else None


def _top_level_functions(text: str) -> dict[str, str]:
    """All top-level function definitions in preprocessed C (name -> body text); duplicates dropped."""
    out: dict[str, str] = {}
    seen: set[str] = set()
    depth, boundary, i, n = 0, 0, 0, len(text)
    while i < n:
        ch = text[i]
        if ch == '"' or ch == "'":
            j = i + 1
            while j < n and text[j] != ch:
                j += 2 if text[j] == "\\" else 1
            i = j + 1
            continue
        if ch == "{":
            if depth == 0:
                header = text[boundary:i]
                m = re.search(r"\b([A-Za-z_]\w*)\s*\((?:[^()]|\([^()]*\))*\)\s*(?:__attribute__\s*\(\(.*?\)\)\s*)*$", header, re.S)
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                if m and "=" not in header.split(m.group(1))[-1].split(")")[-1]:
                    name = m.group(1)
                    if name in seen:
                        out.pop(name, None)
                    else:
                        out[name] = header.strip().splitlines()[-1] + text[start:i + 1]
                    seen.add(name)
                boundary = i + 1
        elif ch == ";" and depth == 0:
            boundary = i + 1
        i += 1
    return out


MARKER = re.compile(r'(?m)^# \d+ "([^"]+)"')
WRITE_OPS = r"(?:[+\-*/%&|^]|<<|>>)?=(?!=)"


def _tu_functions(text: str) -> dict[str, dict[str, str]]:
    """Top-level function definitions with the source file named by the preceding line marker."""
    markers = [(m.start(), m.group(1)) for m in MARKER.finditer(text)]
    offsets = [o for o, _ in markers]
    import bisect
    out: dict[str, dict[str, str]] = {}
    dup: set[str] = set()
    depth, boundary, i, n, m, header, start = 0, 0, 0, len(text), None, "", 0
    while i < n:
        ch = text[i]
        if ch in "\"'":
            j = i + 1
            while j < n and text[j] != ch:
                j += 2 if text[j] == "\\" else 1
            i = j + 1
            continue
        if ch == "{":
            if depth == 0:
                header = text[boundary:i]
                m = re.search(r"\b([A-Za-z_]\w*)\s*\((?:[^()]|\([^()]*\))*\)\s*(?:__attribute__\s*\(\(.*?\)\)\s*)*$", header, re.S)
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                if m and "=" not in header.split(m.group(1))[-1].split(")")[-1]:
                    name = m.group(1)
                    k = bisect.bisect_right(offsets, start) - 1
                    entry = {"file": markers[k][1] if k >= 0 else "", "header": MARKER.sub("", header).strip(), "body": text[start:i + 1]}
                    if name in out or name in dup:
                        out.pop(name, None)
                        dup.add(name)
                    else:
                        out[name] = entry
                boundary = i + 1
                m = None
        elif ch == ";" and depth == 0:
            boundary = i + 1
        i += 1
    return out


def _accesses(body: str) -> dict[str, list[str]]:
    """Syntactic accesses in one preprocessed body: variables as 'x', fields as '.f' ('->f' and '.f' alike)."""
    code = re.sub(r'"(?:\\.|[^"\\])*"', '""', body)
    writes, reads, escapes, calls = set(), set(), set(), set()
    for m in re.finditer(r"(->|\.)?\s*\b([A-Za-z_]\w*)\b", code):
        sep, name = m.group(1), m.group(2)
        key = "." + name if sep else name
        after = code[m.end():m.end() + 64]
        before = code[max(0, m.start() - 3):m.start()]
        if re.match(r"\s*\(", after) and not sep:
            calls.add(name)
            continue
        if re.match(r"\s*(?:\[[^\]]*\]\s*)*" + WRITE_OPS, after) or re.match(r"\s*(?:\+\+|--)", after) or before.endswith(("++", "--")):
            writes.add(key)
            if re.match(r"\s*(?:\[[^\]]*\]\s*)*(?:[+\-*/%&|^]|<<|>>)=", after) or re.match(r"\s*(?:\+\+|--)", after) or before.endswith(("++", "--")):
                reads.add(key)
            continue
        if before.rstrip().endswith("&") and not before.rstrip().endswith("&&") and not sep:
            escapes.add(key)
        reads.add(key)
    return {"writes": sorted(writes), "reads": sorted(reads), "escapes": sorted(escapes), "calls": sorted(calls)}


def _macro_trace(text: str, names: list[str] | None, roots: list[str]) -> dict[str, dict[str, Any]]:
    """#define/#undef events of ``names`` (every macro when None) in -dD preprocessed output, attributed via
    line markers; ``line`` is the source line of the final definition, ``define`` its full directive."""
    def rel(path: str) -> str:
        for root in roots:
            if path.startswith(root.rstrip("/") + "/"):
                return path[len(root.rstrip("/")) + 1:]
        return path
    wanted = set(names) if names is not None else None
    out = {n: {"defined": False, "origin": None, "text": None, "events": []} for n in (names or [])}
    current, lineno = None, 0
    for line in text.splitlines():
        m = re.match(r'^# (\d+) "([^"]*)"', line)
        if m:
            current, lineno = rel(m.group(2)), int(m.group(1))
            continue
        m = re.match(r"^#\s*(define|undef)\s+([A-Za-z_]\w*)(.*)$", line)
        if m and (wanted is None or m.group(2) in wanted):
            op, name = m.group(1), m.group(2)
            rec = out.setdefault(name, {"defined": False, "origin": None, "text": None, "events": []})
            rec["events"].append([op, current])
            rec.update({"defined": True, "origin": current, "text": m.group(3).strip(), "line": lineno, "define": line.strip()}
                       if op == "define" else {"defined": False, "origin": None, "text": None, "line": None, "define": None})
        lineno += 1
    return out


def _compile_command(build: Path, stem: str) -> list[str] | None:
    """The compiler invocation Kbuild saved for ``stem``.o (first command of the .cmd line)."""
    import shlex
    cmd_file = build / Path(stem).parent / (".%s.o.cmd" % Path(stem).name)
    if not cmd_file.exists():
        return None
    m = re.match(r"^(?:saved)?cmd_\S+\s*:=\s*(.*)$", cmd_file.read_text(errors="replace").splitlines()[0])
    return shlex.split(m.group(1).split(";")[0]) if m else None


def _probe_value(build: Path, stem: str, source: Path, macro: str, cross: str) -> dict[str, Any]:
    """Integer value of ``macro`` in the compilation unit: compile the saved command on a probe that includes the
    source and returns (macro) from a function, then read the constant from that function's optimized GIMPLE
    (architecture independent; works for statement-expression macros such as min())."""
    argv = _compile_command(build, stem)
    if not argv or "-o" not in argv:
        return {"answered": False, "reason": "compile_command_unavailable"}
    probe = build / (stem + ".lba_probe.c")
    obj = build / (stem + ".lba_probe.o")
    dump = build / (stem + ".lba_probe.optimized")
    fn = "__lba_probe_" + macro
    # Reserved-spelling attributes: the kernel defines plain `noinline`/`used` as macros.
    # The prototype keeps -Werror=missing-prototypes builds (CONFIG_WERROR) compiling.
    probe.write_text('#include "%s"\nlong long %s(void);\n__attribute__((__used__, __noinline__)) long long %s(void) { return (long long)(%s); }\n'
                     % (source, fn, fn, macro))
    dump.unlink(missing_ok=True)
    out = []
    for i, tok in enumerate(argv):
        if tok.startswith(("-Wp,-MMD", "-Wp,-MD", "-fdump-tree")) or tok == "-dD":
            continue
        if i > 0 and argv[i - 1] == "-o":
            out.append(str(obj))
        elif i == len(argv) - 1:
            out.append(str(probe))
        else:
            out.append(tok)
    out.insert(-1, "-fdump-tree-optimized=" + str(dump))
    done = subprocess.run(out, cwd=str(build), capture_output=True, env=dict(os.environ, LC_ALL="C"), timeout=600)
    obj.unlink(missing_ok=True)
    if done.returncode != 0 or not dump.exists():
        return {"answered": False, "reason": "probe_compile_failed", "stderr_tail": done.stderr.decode("utf-8", "replace")[-300:]}
    record = _cfg_record(dump.read_text(errors="replace"), fn)
    stmts = _body_statements(record or "")
    m = re.fullmatch(r"return (-?\d+);", stmts[0]) if len(stmts) == 1 else None
    return {"answered": True, "value": int(m.group(1))} if m else {"answered": False, "reason": "not_an_integer_constant"}


def _body_statements(record: str) -> list[str]:
    """Statements of an optimized GIMPLE function record (no declarations, block labels or debug markers)."""
    body = record[record.find("{") + 1:record.rfind("}")] if "{" in record else ""
    lines = [l.strip() for l in body.splitlines() if l.strip()]
    # Declarations precede the first block label.
    first = next((i for i, l in enumerate(lines) if re.match(r"^<bb \d+>", l)), len(lines))
    return [l for l in lines[first:] if not re.match(r"^<bb \d+>", l) and not l.startswith(("#", ";;"))]


def _returns_only_zero(record: str) -> bool:
    """Optimized GIMPLE body reduced to a single constant-zero return."""
    return _body_statements(record) in (["return 0;"], ["return false;"])


def _cfg_record(text: str, name: str) -> str | None:
    headers = list(re.finditer(r"(?m)^;; Function ([A-Za-z_]\w*) \(", text))
    idx = [i for i, h in enumerate(headers) if h.group(1) == name]
    if len(idx) != 1:
        return None
    i = idx[0]
    end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
    return text[headers[i].start():end].rstrip() + "\n"


def collect(spec: Mapping[str, Any], out: Path) -> dict[str, Any]:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    log: list[dict[str, Any]] = []
    rev = subprocess.run(["git", "-C", REPO, "rev-parse", spec["revision"]], capture_output=True, text=True).stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", rev):
        raise RuntimeError("unresolvable revision")
    src = CACHE / rev / "linux"
    if not src.exists():
        src.mkdir(parents=True)
        archive = subprocess.run(["git", "-C", REPO, "archive", rev], capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(src)], input=archive, check=True)
    overrides = spec.get("config_set", {})
    make_vars = list(spec.get("make_vars", []))
    kcflags = str(spec.get("kcflags", "")).strip()  # appended to the KCFLAGS this function sets itself
    # make_vars/kcflags join the profile key only when given, so earlier cache keys stay valid.
    extra = ([make_vars] if make_vars else []) + ([kcflags] if kcflags else [])
    profile = _sha_bytes(json.dumps([spec["arch"], spec["defconfig"], overrides] + extra, sort_keys=True).encode())[:12]
    kc = lambda flags: "KCFLAGS=" + " ".join(f for f in (flags, kcflags) if f)
    build = CACHE / rev / ("build-%s-%s" % (spec["arch"], profile))
    cross = spec.get("cross_compile", "")
    make = ["make", "-C", str(src), "O=" + str(build), "ARCH=" + spec["arch"], "-j20"] + (["CROSS_COMPILE=" + cross] if cross else []) + make_vars
    if not (build / ".config").exists():
        build.mkdir(parents=True, exist_ok=True)
        if _run(make + [spec["defconfig"]], log).returncode:
            raise RuntimeError("defconfig failed")
        if overrides:
            cfg = [str(src / "scripts/config"), "--file", str(build / ".config")]
            for k, v in overrides.items():
                cfg += (["--enable", k] if v is True else ["--disable", k] if v is False else ["--set-val", k, str(v)])
            _run(cfg, log)
            if _run(make + ["olddefconfig"], log).returncode:
                raise RuntimeError("olddefconfig failed")
    config_text = (build / ".config").read_text()
    config = {}
    for line in config_text.splitlines():
        m = re.match(r"^(CONFIG_\w+)=(.*)$", line)
        if m:
            v = m.group(2)
            config[m.group(1)] = True if v == "y" else (int(v) if re.fullmatch(r"-?\d+", v) else v.strip('"'))
        m = re.match(r"^# (CONFIG_\w+) is not set$", line)
        if m:
            config[m.group(1)] = False
    objdump = (cross + "objdump") if cross else "objdump"
    files = {}
    for path in spec["files"]:
        stem = path[:-2]
        entry: dict[str, Any] = {}
        if spec.get("macros"):
            # -dD pass first; the normal pass below regenerates the .i without it.
            traced = _run(make + [kc("-dD"), stem + ".i"], log)
            dd = build / (stem + ".i")
            entry["macro_trace_returncode"] = traced.returncode
            if traced.returncode == 0 and dd.exists():
                dtext = dd.read_text(errors="replace")
                entry["macro_trace_sha256"] = _sha_bytes(dd.read_bytes())
                entry["macros"] = _macro_trace(dtext, None if spec["macros"] == "*" else list(spec["macros"]), [str(src), str(build)])
        started = time.time()
        dumps_flags = "-fdump-tree-cfg-lineno" + (" -fdump-tree-optimized" if spec.get("optimized_functions") else "")
        done = _run(make + [kc(dumps_flags), stem + ".o", stem + ".i"], log)
        entry["build_returncode"] = done.returncode
        obj, pre = build / (stem + ".o"), build / (stem + ".i")
        if done.returncode == 0 and obj.exists():
            dis = subprocess.run([objdump, "-dr", "--no-show-raw-insn", str(obj)], capture_output=True, text=True).stdout
            nm = subprocess.run([cross + "nm" if cross else "nm", str(obj)], capture_output=True, text=True).stdout
            entry["object_sha256"] = _sha_bytes(obj.read_bytes())
            entry["functions"] = _split_objdump(dis)
            entry["defined_text_symbols"] = sorted({l.split()[-1] for l in nm.splitlines() if re.match(r"^[0-9a-f]+ [tT] ", l)})
            entry["defined_symbols"] = sorted({l.split()[-1] for l in nm.splitlines() if re.match(r"^[0-9a-f]+ [A-TV-Za-tv-z] ", l)})
        if pre.exists():
            ptext = pre.read_text(errors="replace")
            entry["preprocessed_sha256"] = _sha_bytes(pre.read_bytes())
            entry["bodies"] = {f: _function_body(ptext, f) for f in spec.get("functions", [])}
            tu = _tu_functions(ptext)
            index = {}
            for name, info in tu.items():
                if info["file"].endswith(path) or name in spec.get("functions", []):
                    sec = re.search(r'__section__\s*\(\s*"([^"]+)"', info["header"])
                    index[name] = {"file": info["file"], "section": sec.group(1) if sec else ".text", **_accesses(info["body"])}
            entry["tu_index"] = index
            entry["initcalls"] = {fn: lvl for lvl, fn in re.findall(r'\.initcall(\w+?)\.init[^;]*?=\s*([A-Za-z_]\w*)\s*;', ptext)}
            entry["initcalls"].update({fn: lvl for fn, lvl in re.findall(r'__initcall__\w*?_(\w+?)(\d+s?)\b', ptext) if fn in index and fn not in entry["initcalls"]})
            missing = [f for f in spec.get("functions", []) if f not in entry.get("functions", {})]
            if missing:
                tops = _top_level_functions(ptext)
                entry["callers"] = {f: sorted(g for g, body in tops.items() if g != f and re.search(r"\b" + re.escape(f) + r"\s*\(", body))
                                    for f in missing}
        dumps = sorted(p for p in (build / Path(stem).parent).glob(Path(stem).name + ".*cfg") if p.stat().st_mtime >= started - 1)
        if dumps:
            ctext = dumps[-1].read_text(errors="replace")
            entry["cfg_dump"] = {"name": dumps[-1].name, "sha256": _sha_bytes(dumps[-1].read_bytes())}
            entry["cfg_records"] = {f: _cfg_record(ctext, f) for f in spec.get("functions", [])}
        if spec.get("optimized_functions"):
            # An unchanged command does not recompile, so the newest dump (not one newer than this run) is used.
            opt = sorted(p for p in (build / Path(stem).parent).glob(Path(stem).name + ".*optimized"))
            if opt:
                otext = opt[-1].read_text(errors="replace")
                entry["optimized_dump"] = {"name": opt[-1].name, "sha256": _sha_bytes(opt[-1].read_bytes())}
                entry["optimized_records"] = {f: _cfg_record(otext, f) for f in spec["optimized_functions"]}
        if spec.get("macro_values") and done.returncode == 0:
            traced_macros = entry.get("macros") or {}
            # A name the -dD trace shows is never defined cannot be a macro value; skip its full-TU probe compile.
            entry["macro_values"] = {m: ({"answered": False, "reason": "not_a_macro_in_trace"}
                                         if m in traced_macros and not traced_macros[m]["defined"]
                                         else _probe_value(build, stem, src / path, m, cross)) for m in spec["macro_values"]}
        files[path] = entry
    bundle = {"schema": BUNDLE_SCHEMA, "spec": dict(spec), "revision": rev, "build_profile": profile,
              "config_sha256": _sha_bytes(config_text.encode()), "config": config, "files": files, "commands": log}
    (out / "bundle.json").write_text(json.dumps(bundle, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"revision": rev, "files": {p: {k: (len(v) if isinstance(v, dict) else v) for k, v in e.items()
                                           if k in ("build_returncode", "functions", "bodies", "cfg_records")} for p, e in files.items()}}


TREE_SCHEMA = "kernel_tree_fact_bundle_v1"


def _int_value(text: str) -> int | None:
    t = text.strip()
    while t.startswith("(") and t.endswith(")"):
        t = t[1:-1].strip()
    t = re.sub(r"(?i)(?<=[0-9a-f])(?:ul|lu|ull|llu|u|l|ll)$", "", t)
    try:
        return int(t, 0)
    except ValueError:
        return None


def collect_tree(spec: Mapping[str, Any], out: Path) -> dict[str, Any]:
    """Per-architecture source-tree facts for one revision (no cross compiler needed)."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    rev = subprocess.run(["git", "-C", REPO, "rev-parse", spec["revision"]], capture_output=True, text=True).stdout.strip()
    src = CACHE / rev / "linux"
    if not src.exists():
        src.mkdir(parents=True)
        archive = subprocess.run(["git", "-C", REPO, "archive", rev], capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(src)], input=archive, check=True)
    arches = sorted(p.name for p in (src / "arch").iterdir() if p.is_dir() and (p / "Kconfig").exists())
    if spec.get("arches") not in (None, "all"):
        arches = [a for a in arches if a in spec["arches"]]
    facts: dict[str, Any] = {}
    for a in arches:
        kconfig = (src / "arch" / a / "Kconfig").read_text(errors="replace")
        selects = {s: [l.strip() for l in kconfig.splitlines() if re.match(r"\s*select\s+" + re.escape(s) + r"\b", l)]
                   for s in spec.get("kconfig_symbols", [])}
        uapi = {}
        for req in spec.get("uapi", []):
            header = req["header"]
            own = src / "arch" / a / "include/uapi" / header
            include = header if own.exists() else header.replace("asm/", "asm-generic/", 1)
            tu = '#include <%s>\n' % include
            done = subprocess.run(["gcc", "-E", "-dM", "-nostdinc", "-I", str(src / "arch" / a / "include/uapi"),
                                   "-I", str(src / "include/uapi"), "-x", "c", "-"], input=tu.encode(), capture_output=True)
            macros = {}
            if done.returncode == 0:
                defs = {}
                for line in done.stdout.decode(errors="replace").splitlines():
                    m = re.match(r"#define\s+([A-Za-z_]\w*)(?:\s+(.*))?$", line)
                    if m:
                        defs[m.group(1)] = (m.group(2) or "").strip()
                for name in req.get("macros", []):
                    macros[name] = {"defined": name in defs, "text": defs.get(name), "value": _int_value(defs[name]) if name in defs else None}
            uapi[header] = {"own_header": own.exists(), "generic_fallback": not own.exists(), "returncode": done.returncode,
                            "stderr_tail": done.stderr.decode(errors="replace")[-400:], "macros": macros}
        facts[a] = {"kconfig_selects": selects, "uapi": uapi}
    deps: dict[str, list[str]] = {}
    for sym in spec.get("config_symbols", []):
        lines: list[str] = []
        for kf in src.rglob("Kconfig*"):
            if not kf.is_file():
                continue
            text = kf.read_text(errors="replace")
            for block in re.finditer(r"(?ms)^(?:menu)?config\s+" + re.escape(sym) + r"\s*\n(.*?)(?=^\S)", text):
                lines += [l.strip() for l in block.group(1).splitlines() if l.strip().startswith("depends on")]
        deps[sym] = lines
    bundle = {"schema": TREE_SCHEMA, "spec": dict(spec), "revision": rev, "arches": arches, "facts": facts, "kconfig_deps": deps}
    (out / "tree_bundle.json").write_text(json.dumps(bundle, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"revision": rev, "arches": len(arches),
            "uapi_ok": {h: sum(1 for a in arches if facts[a]["uapi"][h]["returncode"] == 0) for h in [r["header"] for r in spec.get("uapi", [])]}}


def tree_query(tree: Mapping[str, Any], arch: str, q: Mapping[str, Any]) -> tuple[bool, Any]:
    f = tree["facts"].get(arch)
    if f is None:
        return False, "arch_not_in_tree_bundle"
    kind = q.get("kind")
    if kind == "kconfig_selects":
        sel = f["kconfig_selects"].get(q["symbol"])
        return (True, bool(sel)) if sel is not None else (False, "symbol_not_collected")
    if kind in ("uapi_defined", "uapi_value"):
        u = f["uapi"].get(q["header"])
        if u is None or u["returncode"] != 0:
            return False, "uapi_preprocess_failed" if u else "header_not_collected"
        m = u["macros"].get(q["macro"])
        if m is None:
            return False, "macro_not_collected"
        if kind == "uapi_defined":
            return True, m["defined"]
        return (True, m["value"]) if m["value"] is not None else (False, "value_not_integer_or_undefined")
    return False, "unsupported_tree_query"


def _functions(bundle: Mapping[str, Any]) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for entry in bundle["files"].values():
        merged.update(entry.get("functions", {}))
    return merged


def query(bundle: Mapping[str, Any], q: Mapping[str, Any]) -> tuple[bool, Any]:
    """Return (answered, value). Unanswerable queries return (False, reason)."""
    kind = q.get("kind")
    if kind not in QUERY_KINDS:
        return False, "unsupported_query_kind"
    funcs = _functions(bundle)
    if kind == "constant":
        return True, q["value"]
    if kind == "build_ok":
        entry = bundle["files"].get(q["file"])
        return (True, entry.get("build_returncode") == 0) if entry else (False, "file_not_built")
    if kind == "config":
        opt = q["option"]
        return (True, bundle["config"][opt]) if opt in bundle["config"] else (True, False) if q.get("absent_is_false") else (False, "option_absent")
    if kind == "defined":
        return True, q["function"] in funcs
    if kind in ("macro_defined", "macro_from_arch"):
        for entry in bundle["files"].values():
            rec = (entry.get("macros") or {}).get(q["macro"])
            if rec is not None:
                if kind == "macro_defined":
                    return True, rec["defined"]
                return True, bool(rec["defined"] and (rec["origin"] or "").startswith("arch/"))
        return False, "macro_not_traced"
    if kind == "macro_value":
        for entry in bundle["files"].values():
            rec = (entry.get("macro_values") or {}).get(q["macro"])
            if rec is not None:
                return (True, rec["value"]) if rec.get("answered") else (False, rec.get("reason", "probe_failed"))
        return False, "macro_value_not_probed"
    if kind == "returns_only_zero":
        for entry in bundle["files"].values():
            rec = (entry.get("optimized_records") or {}).get(q["function"])
            if rec:
                return True, _returns_only_zero(rec)
        return False, "no_optimized_record"
    if kind == "object_defines_token":
        pattern = re.compile(r"(?:^|_)" + re.escape(q["token"]) + r"(?:_|$)")
        for entry in bundle["files"].values():
            if "defined_symbols" in entry:
                return True, any(pattern.search(s) for s in entry["defined_symbols"])
        return False, "object_not_built"
    if kind == "references":
        lines = funcs.get(q["function"])
        if lines is None:
            return False, "function_not_in_object"
        sym = re.escape(q["symbol"])
        return True, any(re.search(r"R_\w+\s+" + sym + r"(?:[+-]0x[0-9a-f]+)?$", l) for l in lines)
    index: dict[str, dict[str, Any]] = {}
    initcalls: dict[str, str] = {}
    for entry in bundle["files"].values():
        index.update(entry.get("tu_index") or {})
        initcalls.update(entry.get("initcalls") or {})
    obj = q.get("object")
    keys = {obj, "." + obj.lstrip(".")} if isinstance(obj, str) else set()
    in_init = lambda f: index[f]["section"].startswith(INIT_SECTIONS)
    if kind in ("writes", "reads", "escapes"):
        if q["function"] not in index:
            return False, "function_not_indexed"
        return True, bool(keys & set(index[q["function"]][kind]))
    if kind == "in_init":
        return (True, in_init(q["function"])) if q["function"] in index else (False, "function_not_indexed")
    if kind == "initcall_level":
        return (True, initcalls[q["function"]]) if q["function"] in initcalls else (False, "no_initcall_found")
    if kind == "calls":
        if q["function"] not in index:
            return False, "function_not_indexed"
        return True, q["callee"] in index[q["function"]]["calls"]
    if kind == "reachable":
        if q["function"] not in index:
            return False, "function_not_indexed"
        seen, todo = set(), [q["function"]]
        while todo:
            f = todo.pop()
            if f in seen or f not in index:
                continue
            seen.add(f)
            if q["callee"] in index[f]["calls"]:
                return True, True
            todo.extend(index[f]["calls"])
        return True, False
    if kind in ("writers_count", "all_writers_in_init", "any_reader_outside_init"):
        writers = [f for f, v in index.items() if keys & set(v["writes"])]
        readers = [f for f, v in index.items() if keys & set(v["reads"])]
        if kind == "writers_count":
            return True, len(writers)
        if kind == "all_writers_in_init":
            return (True, all(in_init(f) for f in writers)) if writers else (False, "no_writers_in_index")
        return (True, any(not in_init(f) for f in readers)) if readers else (False, "no_readers_in_index")
    if kind == "may_reference":
        sym = re.escape(q["symbol"])
        hit = lambda lines: any(re.search(r"R_\w+\s+" + sym + r"(?:[+-]0x[0-9a-f]+)?$", l) for l in lines)
        if q["function"] in funcs:
            return True, hit(funcs[q["function"]])
        callers = [c for entry in bundle["files"].values() for c in (entry.get("callers") or {}).get(q["function"], [])]
        if not callers:
            return False, "inlined_without_known_callers"
        if any(c in funcs and hit(funcs[c]) for c in callers):
            return True, True
        if all(c in funcs for c in callers):
            return True, False
        return False, "callers_not_all_in_object"
    if kind == "expansion_contains":
        for entry in bundle["files"].values():
            body = (entry.get("bodies") or {}).get(q["function"])
            if body is not None:
                return True, q["text"] in body
        return False, "body_not_extracted"
    if kind == "direct_write":
        from .gimple_write_effects import analyze_write_effects
        for path, entry in bundle["files"].items():
            record = (entry.get("cfg_records") or {}).get(q["function"])
            if record:
                doc = {"id": "%s:%s" % (path, q["function"]), "path": path, "revision": bundle["revision"], "text": record}
                status = analyze_write_effects(doc, function=q["function"], target=q["target"], real_kernel=True)["status"]
                if status == "direct_write_observed":
                    return True, True
                if status == "no_direct_write_observed":
                    return True, False
                return False, "analyzer:" + status
        return False, "cfg_record_not_extracted"
    return False, "unreachable"


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["collect", "collect-tree"])
    p.add_argument("--spec", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    fn = collect if a.command == "collect" else collect_tree
    print(json.dumps(fn(json.loads(a.spec.read_text(encoding="utf-8")), a.out), ensure_ascii=False))


if __name__ == "__main__":
    main()
