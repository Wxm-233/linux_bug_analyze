"""Enumerate C boundary uses in the frozen LLVM build matrix."""

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import ctypes
from dataclasses import dataclass
from functools import lru_cache
import gzip
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time

from clang import cindex

HERE = Path(__file__).resolve().parent
ARCHES = ("riscv", "arm64", "x86_64")
DETAIL_RECORD = cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD

K = cindex.CursorKind
DECL_KINDS = {
    K.FUNCTION_DECL.value: "function",
    K.VAR_DECL.value: "object",
    K.MACRO_DEFINITION.value: "macro",
    K.ENUM_CONSTANT_DECL.value: "enum_constant",
    K.TYPEDEF_DECL.value: "typedef",
    K.STRUCT_DECL.value: "struct",
    K.UNION_DECL.value: "union",
}
EXTERNAL_LINKAGE = (cindex.LinkageKind.EXTERNAL, cindex.LinkageKind.UNIQUE_EXTERNAL)
WRAPPERS = {K.UNEXPOSED_EXPR.value, K.PAREN_EXPR.value}
ARRAY_TYPES = {
    cindex.TypeKind.CONSTANTARRAY,
    cindex.TypeKind.INCOMPLETEARRAY,
    cindex.TypeKind.VARIABLEARRAY,
}


def command(argv, cwd=None):
    return subprocess.run(
        argv, cwd=cwd, check=True, text=True, encoding="utf-8", capture_output=True
    ).stdout


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def json_line(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n"


def atomic_text(path, write):
    """Publish only closed, complete outputs, including per-unit cache files."""
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
        pending = Path(temporary.name)
    try:
        open_text = gzip.open if path.suffix == ".gz" else open
        with open_text(pending, "wt", encoding="utf-8", newline="\n") as stream:
            write(stream)
        pending.replace(path)
    finally:
        pending.unlink(missing_ok=True)


def save_json(path, value):
    atomic_text(path, lambda stream: stream.write(json_line(value)))


def load_json(path):
    open_text = gzip.open if path.suffix == ".gz" else open
    with open_text(path, "rt", encoding="utf-8") as stream:
        return json.load(stream)


@dataclass(frozen=True)
class Entry:
    number: int
    directory: Path
    source: Path
    output: Path
    args: tuple

    @property
    def is_c(self):
        return self.source.suffix == ".c"

    @property
    def is_asm(self):
        return self.source.suffix == ".S"


def load_entries(database):
    entries = []
    for number, row in enumerate(load_json(database)):
        directory = Path(row["directory"]).resolve()
        source = (directory / row["file"]).resolve()
        argv = row.get("arguments") or shlex.split(row["command"])
        if Path(argv[0]).name not in ("clang", "clang-18"):
            raise ValueError(f"Unexpected compiler in entry {number}: {argv[0]}")
        output = (directory / argv[argv.index("-o") + 1]).resolve()
        entries.append(Entry(number, directory, source, output, tuple(argv[1:])))
    return entries


def parse_args(entry):
    """Keep semantic flags. Remove the input repeated by Index.parse and build actions."""
    args = []
    tokens = iter(entry.args)
    inputs = 0
    for arg in tokens:
        if arg in {"-o", "-MF", "-MT", "-MQ", "-MJ", "-Xassembler"}:
            next(tokens)
        elif arg in {"-c", "-MD", "-MMD", "-MP", "-pipe"} or arg.startswith(
            ("-Wp,-MMD,", "-Wp,-MD,", "-Wa,")
        ):
            continue
        elif (
            not arg.startswith("-") and arg.endswith(entry.source.suffix)
            and (entry.directory / arg).resolve() == entry.source
        ):
            inputs += 1
        else:
            args.append(arg)
    if inputs != 1:
        raise ValueError(f"Expected one input in compile command for {entry.source}, found {inputs}")
    return args


class Paths:
    def __init__(self, source, build):
        self.source = str(source)
        self.build = str(build)

    @lru_cache(maxsize=32768)
    def name(self, path, directory=""):
        path = os.path.normpath(os.path.join(directory, path))
        for root, prefix in ((self.build, "@build/"), (self.source, "")):
            if path.startswith(root + "/"):
                return sys.intern(prefix + path[len(root) + 1:])
        return None

    def location(self, cursor, directory):
        loc = cursor.location
        file = loc.file
        if file is None or loc.line == 0:
            return None
        path = self.name(file.name, directory)
        return (path, loc.line, loc.column) if path is not None else None


@lru_cache(maxsize=65536)
def layer(path):
    relative = path.removeprefix("@build/")
    if relative.startswith("arch/"):
        return "arch"
    if relative.startswith("include/asm-generic/"):
        return "asm_generic"
    return "public"


def direction(user_path, definition_path):
    user, provider = layer(user_path), layer(definition_path)
    if user == "arch" and provider != "arch":
        return "arch_to_public"
    if user != "arch" and provider == "arch" or user == "public" and provider == "asm_generic":
        return "public_to_arch"
    return None


@dataclass(frozen=True, slots=True)
class Symbol:
    kind: str
    name: str
    usr: str
    at: tuple
    defined: bool
    external: bool
    link_name: str

    def row(self):
        return (self.kind, self.name, self.usr, self.at, self.defined, self.external, self.link_name)

    @classmethod
    def from_row(cls, row):
        kind, name, usr, at, defined, external, link_name = row
        return cls(kind, name, usr, (sys.intern(at[0]), at[1], at[2]), defined, external, link_name)


def operator_spelling(family):
    get_kind = getattr(cindex.conf.lib, f"clang_getCursor{family}OperatorKind")
    get_kind.argtypes = [cindex.Cursor]
    get_kind.restype = ctypes.c_int
    spelling = getattr(cindex.conf.lib, f"clang_get{family}OperatorKindSpelling")
    spelling.argtypes = [ctypes.c_int]
    spelling.restype = cindex._CXString
    spelling.errcheck = cindex._CXString.from_result
    return lambda cursor: spelling(get_kind(cursor))


def operand(cursor):
    return next(cursor.get_children(), None)


def unwrapped(cursor, wrappers=WRAPPERS):
    while cursor is not None and cursor._kind_id in wrappers:
        cursor = operand(cursor)
    return cursor


def CursorKey(cursor):
    """Hashable source occurrence identity, independent of traversal wrappers."""
    loc = cursor.location
    extent = cursor.extent
    return (cursor._kind_id, cursor.get_usr(),
            loc.file.name if loc.file else None, loc.offset,
            extent.start.offset, extent.end.offset)


def is_definition(cursor):
    # libclang does not call C tentative definitions definitions. File-scope
    # non-extern object declarations still allocate storage at TU end.
    return cursor.is_definition() or (
        cursor._kind_id == K.VAR_DECL.value
        and cursor.semantic_parent.kind == K.TRANSLATION_UNIT
        and cursor.storage_class != cindex.StorageClass.EXTERN
    )


class Collector:
    def __init__(self, paths, directory, binary_spelling, unary_spelling):
        self.paths = paths
        self.directory = str(directory)
        self.binary_spelling = binary_spelling
        self.unary_spelling = unary_spelling
        self.symbols = {}
        self.declarations = {}
        self.definitions = set()
        self.references = set()
        self.actions = {}
        self.direct_callees = set()
        self.unresolved = Counter()
        self.examples = []
        self.indirect_calls = 0
        self.visible_macros = 0
        self.owner = None
        self.failure = None

    def symbol(self, decl):
        key = CursorKey(decl)
        if key in self.declarations:
            return self.declarations[key]
        kind = DECL_KINDS.get(decl._kind_id)
        external = kind in ("function", "object") and decl.linkage in EXTERNAL_LINKAGE
        if kind == "object" and not external and decl.semantic_parent.kind != K.TRANSLATION_UNIT:
            return None
        definition = decl.get_definition()
        if definition is None and (kind in ("macro", "enum_constant") or is_definition(decl)):
            definition = decl
        chosen = definition or decl
        name = chosen.spelling
        at = self.paths.location(chosen, self.directory)
        record = None
        if name and at is not None:
            record = Symbol(
                kind, name, chosen.get_usr(), at, definition is not None, external,
                (chosen.mangled_name or name) if external else "",
            )
        self.declarations[key] = record
        return record

    def intern(self, symbol):
        return self.symbols.setdefault(symbol, len(self.symbols))

    def missing(self, reason, name, at):
        self.unresolved[reason] += 1
        if len(self.examples) < 12:
            self.examples.append([reason, name, at])

    def reference(self, cursor, decl, action):
        if decl is not None and decl._kind_id not in DECL_KINDS:
            return
        at = self.paths.location(cursor, self.directory)
        if at is None:
            return
        if decl is None:
            self.missing("no_referenced_cursor", cursor.spelling, at)
            return
        symbol = self.symbol(decl)
        if symbol is None:
            if decl._kind_id != K.VAR_DECL.value or decl.linkage in EXTERNAL_LINKAGE:
                self.missing("no_project_location_or_name", decl.spelling, at)
            return
        if (
            symbol.defined and not symbol.external and action != "call"
            and direction(at[0], symbol.at[0]) is None
        ):
            return
        owner = self.intern(self.owner) if action == "call" and self.owner else None
        self.references.add((at, action, self.intern(symbol), owner))

    def mark_lvalue(self, cursor, action):
        cursor = unwrapped(cursor)
        if cursor is None:
            return
        kind = cursor._kind_id
        if kind == K.DECL_REF_EXPR.value:
            self.actions[CursorKey(cursor)] = action
        elif kind == K.MEMBER_REF_EXPR.value:
            base = unwrapped(operand(cursor))
            if base is not None and base.type.get_canonical().kind != cindex.TypeKind.POINTER:
                self.mark_lvalue(base, action)
        elif kind == K.ARRAY_SUBSCRIPT_EXPR.value:
            for child in cursor.get_children():
                base = unwrapped(child)
                if base is not None and base.type.get_canonical().kind in ARRAY_TYPES:
                    self.mark_lvalue(base, action)
                    break

    def record_call(self, cursor):
        decl = cursor.referenced
        if decl is None or decl._kind_id != K.FUNCTION_DECL.value:
            self.indirect_calls += 1
            return
        callee = unwrapped(operand(cursor), WRAPPERS | {K.CSTYLE_CAST_EXPR.value})
        if callee is not None and callee._kind_id == K.DECL_REF_EXPR.value:
            self.direct_callees.add(CursorKey(callee))
        self.reference(cursor, decl, "call")

    def visit(self, cursor, parent, _):
        # libclang's visitor performs recursion in C. Only materialize relevant cursors.
        kind = cursor._kind_id
        try:
            if kind == K.FUNCTION_DECL.value:
                cursor._tu = self.tu
                if cursor.is_definition():
                    owner = self.symbol(cursor)
                    if owner is not None and owner.external:
                        self.definitions.add(self.intern(owner))
                    previous, self.owner = self.owner, owner
                    cindex.conf.lib.clang_visitChildren(cursor, self.visitor, None)
                    self.owner = previous
                    return 0 if self.failure else 1  # break or continue without revisiting children
            elif kind == K.VAR_DECL.value:
                cursor._tu = self.tu
                if cursor.linkage in EXTERNAL_LINKAGE and is_definition(cursor):
                    symbol = self.symbol(cursor)
                    if symbol is not None:
                        self.definitions.add(self.intern(symbol))
            elif kind == K.CALL_EXPR.value:
                cursor._tu = self.tu
                self.record_call(cursor)
            elif kind == K.DECL_REF_EXPR.value:
                if CursorKey(cursor) not in self.direct_callees:
                    cursor._tu = self.tu
                    decl = cursor.referenced
                    action = self.actions.pop(CursorKey(cursor), "read")
                    if decl is not None and decl._kind_id == K.FUNCTION_DECL.value:
                        action = "address"
                    self.reference(cursor, decl, action)
                else:
                    self.direct_callees.discard(CursorKey(cursor))
            elif kind == K.TYPE_REF.value:
                cursor._tu = self.tu
                self.reference(cursor, cursor.referenced, "type")
            elif kind == K.MEMBER_REF_EXPR.value:
                cursor._tu = self.tu
                field = cursor.referenced
                if field is not None and field._kind_id == K.FIELD_DECL.value:
                    record = field.semantic_parent
                    while record is not None and record._kind_id in DECL_KINDS and not record.spelling:
                        record = record.semantic_parent
                    if record is not None and record._kind_id in (K.STRUCT_DECL.value, K.UNION_DECL.value):
                        self.reference(cursor, record, "type")
            elif kind == K.MACRO_INSTANTIATION.value:
                cursor._tu = self.tu
                self.visible_macros += 1
                self.reference(cursor, cursor.referenced, "macro_expand")
            elif kind == K.BINARY_OPERATOR.value:
                if self.binary_spelling(cursor) == "=":
                    cursor._tu = self.tu
                    self.mark_lvalue(operand(cursor), "write")
            elif kind == K.COMPOUND_ASSIGNMENT_OPERATOR.value:
                cursor._tu = self.tu
                self.mark_lvalue(operand(cursor), "read_write")
            elif kind == K.UNARY_OPERATOR.value:
                spelling = self.unary_spelling(cursor)
                if spelling in ("&", "++", "--"):
                    cursor._tu = self.tu
                    self.mark_lvalue(operand(cursor), "address" if spelling == "&" else "read_write")
        except Exception as error:
            # ctypes would otherwise print and swallow an exception from the callback.
            self.failure = error
            return 0
        return 2  # recurse

    def collect(self, tu):
        self.tu = tu
        self.visitor = cindex.callbacks["cursor_visit"](self.visit)
        try:
            cindex.conf.lib.clang_visitChildren(tu.cursor, self.visitor, None)
            if self.failure is not None:
                raise self.failure
        finally:
            self.visitor = None
            self.tu = None
        return {
            "symbols": [symbol.row() for symbol in self.symbols],
            "definitions": sorted(self.definitions),
            "refs": sorted(self.references, key=lambda row: (row[:3], row[3] or -1)),
            "unresolved": dict(self.unresolved),
            "unresolved_examples": self.examples,
            "indirect_calls": self.indirect_calls,
            "visible_macros": self.visible_macros,
        }


def parse_unit(entry, paths, index, binary_spelling, unary_spelling):
    os.chdir(entry.directory)
    args = parse_args(entry)
    try:
        tu = index.parse(str(entry.source), args=args, options=DETAIL_RECORD)
    except cindex.TranslationUnitLoadError as error:
        return {"status": "load_error", "diagnostics": [str(error)]}
    diagnostics = Counter()
    errors = []
    for item in tu.diagnostics:
        diagnostics[item.severity] += 1
        if item.severity >= cindex.Diagnostic.Error and len(errors) < 32:
            errors.append(str(item))
    if errors:
        return {"status": "diagnostic_error", "severity_counts": dict(diagnostics), "diagnostics": errors}
    result = Collector(paths, entry.directory, binary_spelling, unary_spelling).collect(tu)
    return {"status": "ok", "severity_counts": dict(diagnostics), **result}


@dataclass
class Build:
    arch: str
    source: Path
    output: Path
    entries: list
    cache: Path
    inputs: dict

    def unit_path(self, entry):
        return self.cache / f"{entry.number:05d}.json.gz"


def kernel_build(arch):
    source = Path(os.environ["KSRC"]).resolve()
    base = Path(os.environ["KBUILD"]).resolve()
    output = base / f"{arch}_defconfig"
    head = command(["git", "-C", source, "rev-parse", "HEAD"]).strip()
    source_status = command(["git", "--no-optional-locks", "-C", source, "status", "--porcelain=v1"])
    if source_status or head != (base / "source_head.txt").read_text().strip():
        raise ValueError("The kernel tree differs from the build inputs")
    if (base / "completed.txt").read_text().strip() != "success" or (
        output / "status.txt"
    ).read_text().strip() != "success":
        raise ValueError(f"Missing successful build marker for {arch}")
    config_sha = sha256(output / ".config")
    if config_sha != (output / "config.sha256").read_text().split()[0]:
        raise ValueError(f"Configuration differs from the build for {arch}")
    criteria_sha = sha256(HERE / "criteria.md")
    if criteria_sha != (HERE / "criteria_sha256.txt").read_text().split()[0]:
        raise ValueError("The frozen criteria digest has changed")
    database = output / "compile_commands.json"
    header_hashes = {
        str(path.relative_to(output)): sha256(path)
        for path in sorted(output.rglob("*.h"))
        if path.is_file()
    }
    inputs = {
        "arch": arch,
        "kernel_head": head,
        "source": str(source),
        "output": str(output),
        "config_sha256": config_sha,
        "compile_commands_sha256": sha256(database),
        "generated_headers_sha256": digest(header_hashes),
        "enumerate_sha256": sha256(Path(__file__)),
        "criteria_sha256": criteria_sha,
        "amendment_sha256": sha256(HERE / "criteria_amendment1.md"),
        "clang": command(["clang", "--version"]).strip(),
        "cindex_sha256": sha256(Path(cindex.__file__)),
        "libclang": cindex.conf.lib._name,
    }
    if inputs["clang"] != (base / "clang_version.txt").read_text().strip():
        raise ValueError("clang version differs from the compiler used for the build")
    cache = base / "enumeration" / arch / digest(inputs)
    return Build(arch, source, output, load_entries(database), cache, inputs)


def init_worker(source, output, cache):
    global WORKER
    WORKER = (
        Paths(source, output), cindex.Index.create(),
        operator_spelling("Binary"), operator_spelling("Unary"), cache,
    )


def scan_entry(entry):
    paths, index, binary, unary, cache = WORKER
    result = parse_unit(entry, paths, index, binary, unary)
    save_json(cache / f"{entry.number:05d}.json.gz", result)
    return entry.number, result["status"], result.get("diagnostics", [])[:1]


def scan(build, jobs, limit):
    build.cache.mkdir(parents=True, exist_ok=True)
    save_json(build.cache / "inputs.json", build.inputs)
    units = [entry for entry in build.entries if entry.is_c]
    pending = [entry for entry in units if not build.unit_path(entry).is_file()]
    batch = pending[:limit]
    completed_before = len(units) - len(pending)
    print(
        f"{build.arch}: {completed_before}/{len(units)} cached, {len(batch)} in this batch, "
        f"cache={build.cache}", flush=True,
    )
    if not batch:
        return
    statuses = Counter()
    started = time.monotonic()
    with ProcessPoolExecutor(
        max_workers=min(jobs, len(batch)), mp_context=multiprocessing.get_context("fork"),
        initializer=init_worker, initargs=(build.source, build.output, build.cache),
    ) as pool:
        for future in as_completed([pool.submit(scan_entry, entry) for entry in batch]):
            number, status, diagnostics = future.result()
            statuses[status] += 1
            if status != "ok" and statuses[status] <= 3:
                print(f"  unit {number}: {status}: {diagnostics}", flush=True)
            done = sum(statuses.values())
            if done % 64 == 0 or done == len(batch):
                seconds = time.monotonic() - started
                print(
                    f"  {completed_before + done}/{len(units)}: batch {dict(statuses)} ({seconds:.1f}s)",
                    flush=True,
                )


STRONG_NM = frozenset("ABCDGIRSTiu")
WEAK_NM = frozenset("WV")
UNDEFINED_NM = frozenset("Uwv")


def read_nm(files, directory):
    for first in range(0, len(files), 128):
        argv = [
            "llvm-nm", "--format=posix", "--print-file-name", "--extern-only",
            *files[first:first + 128],
        ]
        for line in command(argv, cwd=directory).splitlines():
            if not line.strip():
                continue
            filename, sep, fields = line.partition(":")
            tokens = fields.split()
            if not sep or len(tokens) < 2 or len(tokens[1]) != 1:
                raise ValueError(f"Unrecognized llvm-nm line: {line!r}")
            yield filename, tokens[0], tokens[1]


def object_evidence(build, paths):
    """Resolve unique archive members against binding in the final linked ELF."""
    entries = {str(entry.output.relative_to(build.output)): entry for entry in build.entries}
    archive = {
        os.path.relpath(build.output / name, build.output)
        for name in command(["llvm-ar", "t", "vmlinux.a"], cwd=build.output).splitlines()
        if name
    }
    providers = defaultdict(set)
    undefined = set()
    for obj, name, code in read_nm(sorted(archive | entries.keys()), build.output):
        if obj in archive and (code in STRONG_NM or code in WEAK_NM):
            providers[name].add((obj, code))
        if obj in entries and entries[obj].is_asm and code in UNDEFINED_NM:
            undefined.add((obj, name, code))
    final = defaultdict(set)
    for _, name, code in read_nm(["vmlinux"], build.output):
        final[name].add(code)

    def source(obj):
        if obj not in entries:
            return None
        return paths.name(str(entries[obj].source))

    def origin(obj, code):
        return {"object": obj, "source": source(obj), "nm_type": code}

    def selected(name):
        candidates = providers[name]
        strong = sorted(item for item in candidates if item[1] in STRONG_NM)
        if len(strong) == 1 and final[name] & STRONG_NM:
            return strong[0]
        weak = sorted(item for item in candidates if item[1] in WEAK_NM)
        if not strong and len(weak) == 1 and final[name] & WEAK_NM:
            return weak[0]
        return None

    weak_overrides = {}
    for name, candidates in sorted(providers.items()):
        public_weak = [
            origin(obj, code) for obj, code in sorted(candidates)
            if code in WEAK_NM and source(obj) is not None and layer(source(obj)) == "public"
        ]
        if not public_weak:
            continue
        chosen = selected(name)
        if (
            chosen is not None and chosen[1] in STRONG_NM
            and source(chosen[0]) is not None and layer(source(chosen[0])) == "arch"
        ):
            weak_overrides[name] = {
                "symbol": name, "weak": public_weak, "strong": origin(*chosen),
                "linked_nm_types": sorted(final[name]),
            }

    boundaries = []
    unresolved = []
    same_layer = 0
    for obj, name, code in sorted(undefined):
        consumer = origin(obj, code)
        chosen = selected(name) if obj in archive else None
        if chosen is None or source(chosen[0]) is None or consumer["source"] is None:
            unresolved.append({
                "symbol": name, "use": consumer,
                "reason": "outside_vmlinux_archive" if obj not in archive else "no_unique_provider",
            })
            continue
        provider = origin(*chosen)
        cross = direction(consumer["source"], provider["source"])
        if cross is None:
            same_layer += 1
        else:
            boundaries.append({
                "symbol": name, "use": consumer, "definition": provider, "direction": cross,
                "linked_nm_types": sorted(final[name]),
            })
    return {
        "archive_objects": len(archive),
        "archive_objects_without_compile_entry": len(archive - entries.keys()),
        "objects_scanned": len(archive | entries.keys()),
        "asm_undefined_references": len(undefined),
        "asm_same_layer": same_layer,
        "asm_boundaries": boundaries,
        "asm_unresolved": unresolved,
        "weak_overrides": weak_overrides,
    }, archive


def symbol_json(symbol):
    return {
        "name": symbol.name,
        "kind": symbol.kind,
        "usr": symbol.usr,
        "definition": location_json(symbol.at),
        "definition_layer": layer(symbol.at[0]),
    }


def location_json(at):
    return {"file": at[0], "line": at[1], "column": at[2]}


def save_lines(path, rows):
    def write(stream):
        for row in rows:
            stream.write(json_line(row))

    atomic_text(path, write)


def unit_records(build, entries):
    for entry in entries:
        yield entry, load_json(build.unit_path(entry))


def resolve(symbol, linked, definitions, by_object, weak_overrides):
    if linked and symbol.external and symbol.link_name in weak_overrides:
        provider = weak_overrides[symbol.link_name]["strong"]["object"]
        candidates = by_object.get((provider, symbol.kind, symbol.link_name), ())
        if len(candidates) == 1:
            return next(iter(candidates)), None
        return None, "weak_winner_without_unique_ast_definition"
    if symbol.defined:
        return symbol, None
    candidates = definitions.get((symbol.kind, symbol.usr), {}) if symbol.external and symbol.usr else {}
    if linked:
        candidates = {candidate for candidate, in_core in candidates.items() if in_core}
    if len(candidates) == 1:
        return next(iter(candidates)), None
    return None, "ambiguous_definition" if candidates else "definition_not_found"


class BoundaryPoints:
    def __init__(self):
        self.points = {}
        self.symbol_ids = {}

    def add(self, at, action, symbol, cross, unit):
        key = (symbol, cross)
        number = self.symbol_ids.setdefault(key, len(self.symbol_ids))
        evidence = self.points.setdefault((at, action, number), [])
        if not evidence or evidence[-1] != unit:
            evidence.append(unit)

    def emit(self, output, arch):
        symbols = list(self.symbol_ids)
        uses = Counter()
        point_counts = defaultdict(Counter)
        symbol_sets = defaultdict(lambda: defaultdict(set))
        actions = Counter()

        def points():
            for (at, action, number), units in sorted(self.points.items()):
                symbol, cross = symbols[number]
                top = at[0].removeprefix("@build/").split("/", 1)[0]
                uses[number] += 1
                actions[action] += 1
                for category, value in (
                    ("kind", symbol.kind), ("direction", cross),
                    ("subsystem", top if "/" in at[0].removeprefix("@build/") else "(root)"),
                ):
                    point_counts[category][value] += 1
                    symbol_sets[category][value].add(number)
                yield {
                    "use": location_json(at), "action": action, "symbol_id": number,
                    "direction": cross, "units": units,
                }

        save_lines(output / f"boundary_{arch}.jsonl.gz", points())
        if sum(uses.values()) != len(self.points) or len(uses) != len(symbols):
            raise ValueError("Boundary symbol and point totals are inconsistent")
        save_json(output / f"symbols_{arch}.json", [
            {"id": number, "direction": cross, "points": uses[number], **symbol_json(symbol)}
            for number, (symbol, cross) in enumerate(symbols)
        ])
        summary = {
            f"by_{category}": {
                value: {"symbols": len(symbol_sets[category][value]), "points": count}
                for value, count in sorted(point_counts[category].items())
            }
            for category in ("kind", "direction", "subsystem")
        }
        return {
            "symbols": len(symbols), "points": len(self.points),
            "by_action": dict(sorted(actions.items())), **summary,
        }


def merge(build, output):
    entries = [entry for entry in build.entries if entry.is_c]
    pending = [entry for entry in entries if not build.unit_path(entry).is_file()]
    if pending:
        raise ValueError(f"{build.arch}: {len(pending)} C entries have no recorded status")
    paths = Paths(build.source, build.output)
    objects, archive = object_evidence(build, paths)
    print(f"{build.arch}: nm scanned {objects['objects_scanned']} objects", flush=True)
    definitions = defaultdict(dict)
    by_object = defaultdict(set)
    statuses = Counter()
    for entry, result in unit_records(build, entries):
        statuses[result["status"]] += 1
        if result["status"] != "ok":
            continue
        obj = str(entry.output.relative_to(build.output))
        for number in result["definitions"]:
            symbol = Symbol.from_row(result["symbols"][number])
            candidates = definitions[(symbol.kind, symbol.usr)]
            candidates[symbol] = obj in archive or candidates.get(symbol, False)
            by_object[(obj, symbol.kind, symbol.link_name)].add(symbol)
    if not statuses["ok"]:
        raise ValueError(f"{build.arch}: no C entry parsed successfully")
    print(f"{build.arch}: collected definitions from {statuses['ok']} C entries", flush=True)

    points = BoundaryPoints()
    calls = {}
    units = []
    missing = Counter()
    missing_units = 0
    visible_macros = 0
    indirect_calls = 0
    for entry, result in unit_records(build, entries):
        obj = str(entry.output.relative_to(build.output))
        unit = {
            "id": entry.number, "source": paths.name(str(entry.source)), "object": obj,
            "status": result["status"], "severity_counts": result.get("severity_counts"),
            "diagnostics": result.get("diagnostics", []), "unresolved": None,
        }
        units.append(unit)
        if result["status"] != "ok":
            continue
        local = [Symbol.from_row(row) for row in result["symbols"]]
        resolved = {}
        counts = Counter(result["unresolved"])
        examples = result["unresolved_examples"]
        visible_macros += result["visible_macros"]
        indirect_calls += result["indirect_calls"]
        for at, action, number, owner in result["refs"]:
            at = (sys.intern(at[0]), at[1], at[2])
            if number not in resolved:
                resolved[number] = resolve(
                    local[number], obj in archive, definitions, by_object, objects["weak_overrides"],
                )
            target, reason = resolved[number]
            if target is None:
                counts[reason] += 1
                if len(examples) < 20:
                    examples.append([reason, local[number].name, at])
                continue
            if owner is not None:
                calls.setdefault((local[owner], target), (at, entry.number))
            cross = direction(at[0], target.at[0])
            if cross is not None:
                points.add(at, action, target, cross, entry.number)
        unit["unresolved"] = dict(counts)
        unit["unresolved_examples"] = examples
        unit["visible_macros"] = result["visible_macros"]
        unit["indirect_calls"] = result["indirect_calls"]
        missing.update(counts)
        missing_units += bool(counts)

    print(f"{build.arch}: writing {len(points.points)} points and {len(calls)} call relations", flush=True)
    summary = points.emit(output, build.arch)
    save_json(output / f"units_{build.arch}.json.gz", units)
    save_json(output / f"object_evidence_{build.arch}.json.gz", objects)
    save_lines(output / f"direct_calls_{build.arch}.jsonl.gz", (
        {
            "caller": symbol_json(caller), "callee": symbol_json(callee),
            "example_use": location_json(at), "unit": unit,
        }
        for (caller, callee), (at, unit) in calls.items()
    ))
    summary.update({
        "inputs": build.inputs,
        "compile_commands_entries": len(build.entries),
        "c_units": len(entries),
        "parsed_units": statuses["ok"],
        "parse_failed_units": len(entries) - statuses["ok"],
        "unit_statuses": dict(statuses),
        "units_with_unresolved_refs": missing_units,
        "unresolved_refs": sum(missing.values()),
        "unresolved_by_reason": dict(sorted(missing.items())),
        "visible_macro_instantiations": visible_macros,
        "nested_macro_expansions_not_exposed": None,
        "indirect_calls_without_target_resolution": indirect_calls,
        "direct_call_relations": len(calls),
        "object_evidence": {
            "objects_scanned": objects["objects_scanned"],
            "weak_overrides": len(objects["weak_overrides"]),
            "asm_boundary_refs": len(objects["asm_boundaries"]),
            "asm_unresolved_refs": len(objects["asm_unresolved"]),
            "asm_undefined_refs": objects["asm_undefined_references"],
        },
    })
    save_json(output / f"result_{build.arch}.json", summary)
    return summary


def positive(text):
    value = int(text)
    if value <= 0:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="task", required=True)
    scanning = sub.add_parser("scan")
    scanning.add_argument("arch", choices=ARCHES)
    scanning.add_argument("--jobs", type=positive, default=12)
    scanning.add_argument("--limit", type=positive, default=512)
    merging = sub.add_parser("merge")
    merging.add_argument("arch", choices=ARCHES)
    status = sub.add_parser("status")
    status.add_argument("arch", choices=ARCHES)
    args = parser.parse_args()
    build = kernel_build(args.arch)
    if args.task == "scan":
        scan(build, args.jobs, args.limit)
    elif args.task == "merge":
        print(json.dumps(merge(build, HERE), ensure_ascii=False))
    else:
        units = [entry for entry in build.entries if entry.is_c]
        cached = [entry for entry in units if build.unit_path(entry).is_file()]
        counts = Counter(result["status"] for _, result in unit_records(build, cached))
        print(f"{args.arch}: {len(cached)}/{len(units)} cached, {dict(counts)}, cache={build.cache}")


if __name__ == "__main__":
    main()
