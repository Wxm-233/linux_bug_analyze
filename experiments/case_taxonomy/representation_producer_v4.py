"""Bounded single-revision endian-write review leads, version 4.

Unlike v3, the new macro route proves C integer width, shift safety and value
range in both ILP32 and LP64 models. Only explicitly endian-typed destination
members qualify. This is a local source lead, not hardware/consumer proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import representation_producer_v3 as v3

VERSION = "representation-producer-v4.0"
MAX_TOKENS = 128
MAX_MACRO_DEPTH = 16
MAX_TOTAL_TOKENS = 2048
MAX_EXPANSIONS = 128
TOKEN = re.compile(r"\s*(0[xX][0-9a-fA-F]+[uUlL]*|0[0-7]*[uUlL]*|[1-9][0-9]*[uUlL]*|[A-Za-z_]\w*|<<|>>|[()~+*/%&|^,-])")
PRECEDENCE = {"|": 1, "^": 2, "&": 3, "<<": 4, ">>": 4,
              "+": 5, "-": 5, "*": 6, "/": 6, "%": 6}


class Unproven(ValueError):
    """A bounded proof deliberately does not establish this expression."""


@dataclass(frozen=True)
class Integer:
    bits: int
    unsigned: bool
    low: int
    high: int
    rank: int  # int=1, long=2, long long=3; important on ILP32.

    @property
    def exact(self) -> int | None:
        return self.low if self.low == self.high else None

    @property
    def limits(self) -> tuple[int, int]:
        return ((0, (1 << self.bits) - 1) if self.unsigned else
                (-(1 << (self.bits - 1)), (1 << (self.bits - 1)) - 1))

    def record(self) -> dict:
        return {"bits": self.bits, "unsigned": self.unsigned,
                "rank": self.rank, "minimum": self.low, "maximum": self.high,
                "exact_value": self.exact}


def checked(bits: int, unsigned: bool, low: int, high: int,
            rank: int, *, allow_exact_unsigned_wrap: bool = False) -> Integer:
    value = Integer(bits, unsigned, low, high, rank)
    lower, upper = value.limits
    if allow_exact_unsigned_wrap and unsigned and low == high:
        low &= upper
        return Integer(bits, unsigned, low, low, rank)
    if low < lower or high > upper or low > high:
        raise Unproven("arithmetic overflow, narrowing, or unsupported wrapped interval")
    return value


def literal(token: str, long_bits: int) -> Integer:
    match = re.fullmatch(r"(0[xX][0-9a-fA-F]+|0[0-7]*|[1-9][0-9]*)([uUlL]*)", token)
    if match is None:
        raise Unproven("invalid integer token")
    number, suffix = match.groups()
    suffix = suffix.lower()
    if suffix not in {"", "u", "l", "ul", "lu", "ll", "ull", "llu"}:
        raise Unproven("invalid C integer suffix")
    base = 16 if number.lower().startswith("0x") else (8 if number.startswith("0") else 10)
    value = int(number, base)
    ranks = [(1, 32), (2, long_bits), (3, 64)]
    if "ll" in suffix:
        ranks = ranks[2:]
    elif "l" in suffix:
        ranks = ranks[1:]
    for rank, bits in ranks:
        unsigned_options = ([True] if "u" in suffix else
                            [False] if base == 10 else [False, True])
        for unsigned in unsigned_options:
            maximum = (1 << bits) - 1 if unsigned else (1 << (bits - 1)) - 1
            if value <= maximum:
                return Integer(bits, unsigned, value, value, rank)
    raise Unproven("integer constant exceeds supported 64-bit C types")


def scalar_integer(name: str, long_bits: int) -> Integer:
    name = " ".join(name.split())
    found = re.fullmatch(r"([us])(8|16|32|64)", name)
    if found:
        unsigned, bits = found.group(1) == "u", int(found.group(2))
        rank = 3 if bits == 64 else 1
    elif name in {"unsigned int", "int"}:
        unsigned, bits, rank = name.startswith("unsigned"), 32, 1
    elif name in {"unsigned long", "long"}:
        unsigned, bits, rank = name.startswith("unsigned"), long_bits, 2
    else:
        raise Unproven("scalar type is not a proven fixed-width host integer")
    low = 0 if unsigned else -(1 << (bits - 1))
    high = (1 << bits) - 1 if unsigned else (1 << (bits - 1)) - 1
    return Integer(bits, unsigned, low, high, rank)


def promote(value: Integer) -> Integer:
    if value.bits < 32:
        return Integer(32, False, value.low, value.high, 1)
    return value


def usual(a: Integer, b: Integer) -> tuple[Integer, Integer, tuple[int, bool, int]]:
    a, b = promote(a), promote(b)
    if a.unsigned == b.unsigned:
        chosen = max((a, b), key=lambda v: v.rank)
        target = chosen.bits, chosen.unsigned, chosen.rank
    else:
        unsigned, signed = (a, b) if a.unsigned else (b, a)
        if unsigned.rank >= signed.rank:
            target = unsigned.bits, True, unsigned.rank
        elif signed.bits > unsigned.bits:
            target = signed.bits, False, signed.rank
        else:
            target = signed.bits, True, signed.rank
    converted = []
    for value in (a, b):
        bits, is_unsigned, rank = target
        if is_unsigned and value.low < 0:
            if value.exact is None:
                raise Unproven("negative signed range converted to unsigned")
            exact = value.exact & ((1 << bits) - 1)
            value = Integer(bits, True, exact, exact, rank)
        else:
            value = checked(bits, is_unsigned, value.low, value.high, rank)
        converted.append(value)
    return converted[0], converted[1], target


def binary(op: str, a: Integer, b: Integer) -> Integer:
    if op in {"<<", ">>"}:
        a, b = promote(a), promote(b)
        if b.exact is None or not 0 <= b.exact < a.bits:
            raise Unproven("shift count is not a proven nonnegative value below operand width")
        if a.low < 0:
            raise Unproven("negative signed shift operand is implementation-defined or undefined")
        factor = 1 << b.exact
        low, high = ((a.low * factor, a.high * factor) if op == "<<" else
                     (a.low // factor, a.high // factor))
        # Avoid declaring normal when unsigned shift silently loses high bits.
        return checked(a.bits, a.unsigned, low, high, a.rank)
    a, b, (bits, unsigned, rank) = usual(a, b)
    exact_a, exact_b = a.exact, b.exact
    if exact_a is not None and exact_b is not None:
        if op in {"/", "%"} and exact_b == 0:
            raise Unproven("division by zero")
        if op == "+": value = exact_a + exact_b
        elif op == "-": value = exact_a - exact_b
        elif op == "*": value = exact_a * exact_b
        elif op in {"/", "%"}:
            if not unsigned and exact_a == -(1 << (bits - 1)) and exact_b == -1:
                raise Unproven("signed division quotient overflows, including remainder operation")
            quotient = abs(exact_a) // abs(exact_b)
            quotient = -quotient if (exact_a < 0) != (exact_b < 0) else quotient
            value = quotient if op == "/" else exact_a - quotient * exact_b
        elif op == "|": value = exact_a | exact_b
        elif op == "&": value = exact_a & exact_b
        elif op == "^": value = exact_a ^ exact_b
        else: raise Unproven("unsupported binary operator")
        return checked(bits, unsigned, value, value, rank,
                       allow_exact_unsigned_wrap=True)
    if op == "+": low, high = a.low + b.low, a.high + b.high
    elif op == "-": low, high = a.low - b.high, a.high - b.low
    elif op == "*":
        products = [a.low * b.low, a.low * b.high, a.high * b.low, a.high * b.high]
        low, high = min(products), max(products)
    elif op in {"|", "^", "&"} and a.low >= 0 and b.low >= 0:
        low = 0
        high = min(a.high, b.high) if op == "&" else ((1 << max(a.high, b.high).bit_length()) - 1)
    else:
        raise Unproven("nonconstant operation has no supported bounded value range")
    return checked(bits, unsigned, low, high, rank)


def macro_definitions(files: dict[str, str]) -> tuple[dict[str, dict], dict[str, str]]:
    """Object macros only; conflicting or conditionally defined names are refused."""
    collected: dict[str, list[dict]] = {}
    unsafe_names: dict[str, str] = {}
    for path, source in files.items():
        clean = v3.mask_comments_and_literals(source)
        lines = clean.splitlines()
        conditional_depth = 0
        index = 0
        while index < len(lines):
            line = lines[index]
            at = index + 1
            while line.rstrip().endswith("\\") and index + 1 < len(lines):
                line = line.rstrip()[:-1] + " " + lines[index + 1]
                index += 1
            if re.match(r"\s*#\s*(?:if|ifdef|ifndef)\b", line):
                conditional_depth += 1
            elif re.match(r"\s*#\s*endif\b", line):
                conditional_depth = max(0, conditional_depth - 1)
            undefined = re.match(r"\s*#\s*undef\s+([A-Za-z_]\w*)", line)
            if undefined:
                unsafe_names[undefined.group(1)] = "macro has an undef/redefinition lifecycle"
            found = re.match(r"\s*#\s*define\s+([A-Za-z_]\w*)(.*)$", line)
            if found and found.group(2).startswith("("):
                unsafe_names[found.group(1)] = "function macro is not a proven built-in implementation"
            elif found:
                collected.setdefault(found.group(1), []).append({
                    "expression": found.group(2).strip(), "file": path,
                    "line": at, "conditional": conditional_depth > 0})
            index += 1
    macros, refused = {}, dict(unsafe_names)
    for name, entries in collected.items():
        if name in unsafe_names:
            continue
        if any(item["conditional"] for item in entries):
            refused[name] = "conditional macro definition requires build-condition proof"
        elif len({item["expression"] for item in entries}) != 1:
            refused[name] = "conflicting macro definitions"
        else:
            macros[name] = {**entries[0], "definitions": entries}
    return macros, refused


class Expression:
    def __init__(self, text: str, long_bits: int, macros: dict,
                 refused: dict, scalars: dict | None = None, chain: tuple = (),
                 evidence: dict | None = None, budget: dict | None = None):
        self.long_bits, self.macros, self.refused = long_bits, macros, refused
        self.scalars, self.chain = scalars or {}, chain
        self.evidence = {} if evidence is None else evidence
        self.budget = {"tokens": 0, "expansions": 0} if budget is None else budget
        if len(text) > 4096 or len(chain) > MAX_MACRO_DEPTH:
            raise Unproven("expression/macro expansion budget exceeded")
        self.tokens, offset = [], 0
        while offset < len(text.strip()):
            match = TOKEN.match(text.strip(), offset)
            if match is None:
                raise Unproven("unsupported C expression token")
            self.tokens.append(match.group(1))
            self.budget["tokens"] += 1
            offset = match.end()
            if len(self.tokens) > MAX_TOKENS:
                raise Unproven("token budget exceeded")
            if self.budget["tokens"] > MAX_TOTAL_TOKENS:
                raise Unproven("total expanded token budget exceeded")
        self.position = 0

    def peek(self) -> str | None:
        return self.tokens[self.position] if self.position < len(self.tokens) else None

    def take(self) -> str:
        result = self.peek()
        if result is None:
            raise Unproven("unexpected expression end")
        self.position += 1
        return result

    def expect(self, token: str) -> None:
        if self.take() != token:
            raise Unproven("unbalanced or unsupported expression")

    def parse(self, minimum: int = 0) -> Integer:
        token = self.take()
        if token in {"~", "+", "-"}:
            value = promote(self.parse(7))
            if token == "+": left = value
            elif value.exact is not None:
                result = ~value.exact if token == "~" else -value.exact
                left = checked(value.bits, value.unsigned, result, result, value.rank,
                               allow_exact_unsigned_wrap=True)
            elif token == "-":
                left = checked(value.bits, value.unsigned, -value.high, -value.low, value.rank)
            elif value.unsigned:
                limit = (1 << value.bits) - 1
                left = Integer(value.bits, True, limit ^ value.high, limit ^ value.low, value.rank)
            else:
                raise Unproven("nonconstant signed complement unsupported")
        elif token == "(":
            # Only explicit fixed-width scalar casts; no pointer or force casts.
            if (self.peek() and re.fullmatch(r"[us](?:8|16|32|64)", self.peek()) and
                    self.position + 1 < len(self.tokens) and self.tokens[self.position + 1] == ")"):
                target = scalar_integer(self.take(), self.long_bits)
                self.expect(")")
                value = self.parse(7)
                left = checked(target.bits, target.unsigned, value.low, value.high, target.rank)
            else:
                left = self.parse()
                self.expect(")")
        elif token[0].isdigit():
            left = literal(token, self.long_bits)
        elif re.fullmatch(v3.IDENT, token):
            if self.peek() == "(":
                self.take()
                argument = self.parse()
                self.expect(")")
                if token not in {"BIT", "BIT_ULL"}:
                    raise Unproven("function-like macro/call requires separate semantic proof")
                if token in self.macros or token in self.refused:
                    raise Unproven("local definition shadows the assumed BIT/BIT_ULL implementation")
                base = Integer(self.long_bits if token == "BIT" else 64,
                               True, 1, 1, 2 if token == "BIT" else 3)
                left = binary("<<", base, argument)
            elif token in self.refused:
                raise Unproven(f"{token}: {self.refused[token]}")
            elif token in self.macros:
                if token in self.chain:
                    raise Unproven("cyclic macro expansion")
                self.budget["expansions"] += 1
                if self.budget["expansions"] > MAX_EXPANSIONS:
                    raise Unproven("total macro expansion budget exceeded")
                macro = self.macros[token]
                replacement = macro["expression"]
                atomic = bool(re.fullmatch(r"(?:[A-Za-z_]\w*|0[xX][0-9a-fA-F]+[uUlL]*|[0-9]+[uUlL]*)", replacement))
                parenthesized = (replacement.startswith("(") and
                    v3.closing_delimiter(replacement, 0, "(", ")") == len(replacement) - 1)
                known_call = bool(re.fullmatch(r"BIT(?:_ULL)?\s*\([^()]*\)", replacement))
                if not (atomic or parenthesized or known_call):
                    raise Unproven("unparenthesized compound macro substitution precedence is unsupported")
                self.evidence[token] = {"file": macro["file"], "line": macro["line"],
                                        "expression": macro["expression"]}
                parser = Expression(replacement, self.long_bits, self.macros,
                                    self.refused, {}, self.chain + (token,), self.evidence, self.budget)
                left = parser.evaluate()
            elif token in self.scalars:
                left = scalar_integer(self.scalars[token], self.long_bits)
            else:
                raise Unproven(f"{token}: no established host integer definition")
        else:
            raise Unproven("unsupported expression")
        while self.peek() in PRECEDENCE and PRECEDENCE[self.peek()] >= minimum:
            operator = self.take()
            right = self.parse(PRECEDENCE[operator] + 1)
            left = binary(operator, left, right)
        return left

    def evaluate(self) -> Integer:
        value = self.parse()
        if self.peek() is not None:
            raise Unproven("remaining unsupported expression syntax")
        return value


def prove_expression(text: str, macros: dict, refused: dict,
                     scalars: dict | None = None) -> dict:
    models = []
    evidence = {}
    for name, long_bits in (("ILP32", 32), ("LP64", 64)):
        try:
            parser = Expression(text.strip(), long_bits, macros, refused, scalars,
                                evidence=evidence)
            models.append({"model": name, "status": "proven", **parser.evaluate().record()})
        except (Unproven, ValueError, OverflowError, RecursionError) as exc:
            models.append({"model": name, "status": "insufficient", "reason": str(exc)})
    return {"models": models, "macro_evidence": evidence,
            "status": "proven" if all(m["status"] == "proven" for m in models) else "insufficient"}


def byte_invariant(proof: dict, bits: int) -> bool:
    if proof["status"] != "proven":
        return False
    for model in proof["models"]:
        value = model["exact_value"]
        if value is None or not 0 <= value < (1 << bits):
            return False
        little = value.to_bytes(bits // 8, "little")
        if little != little[::-1]:
            return False
    return True


def function_context(source: str, line: int) -> tuple[dict, set, str]:
    clean = v3.mask_comments_and_literals(source)
    offset = sum(len(item) for item in source.splitlines(keepends=True)[:line - 1])
    # A reported site line can contain preceding code. Restrict declarations to
    # completed lines and reject duplicate scalar declarations conservatively.
    for function in v3.FUNCTION_OPEN.finditer(clean):
        opening = function.end() - 1
        closing = v3.closing_delimiter(clean, opening, "{", "}")
        if function.group(1) in v3.CONTROL or closing is None:
            continue
        if v3.line_number(source, opening) <= line <= v3.line_number(source, closing):
            prefix = function.group(2) + ";" + clean[opening + 1:max(opening + 1, offset)]
            types: dict[str, list[str]] = {}
            for item in v3.HOST_DECL.finditer(prefix):
                types.setdefault(item.group("name"), []).append(" ".join(item.group("type").split()))
            scalars = {name: values[0] if len(values) == 1 else "__ambiguous_declarations"
                       for name, values in types.items()}
            pointers = {item.group("name") for item in v3.OBJECT_DECL.finditer(function.group(2))
                        if item.group("pointer")}
            return scalars, pointers, prefix
    return {}, set(), ""


def analyze_text(source: str, source_path: str = "<synthetic>",
                 declaration_files: dict[str, str] | None = None) -> dict:
    files = declaration_files or {source_path: source}
    report = v3.analyze_text(source, source_path, files)
    macros, refused = macro_definitions(files)
    for item in report["findings"]:
        item["v3_local_status"] = item["status"]
        target = item["destination_type"].replace("__aligned_", "__")
        typed = re.fullmatch(r"__(le|be)(16|32|64)", target)
        if typed is None:
            item["status"] = "insufficient"
            item["reason"] = "v4 requires an explicit endian type on the target; adjacent fields do not establish this slot's contract"
            continue
        kind, width = typed.groups()
        bits = int(width)
        scalars, pointers, prefix = function_context(source, item["line"])
        object_declarations = [entry for entry in v3.OBJECT_DECL.finditer(prefix)
                               if entry.group("name") == item["object"]]
        if len(object_declarations) != 1:
            item["status"], item["reason"] = "insufficient", "object declaration scope/shadowing is ambiguous"
            continue
        if item["object"] in pointers and not item["interface_evidence"]:
            item["interface_evidence"].append({"kind": "pointer_parameter", "name": item["object"],
                "note": "caller visibility lead only; not proof of hardware consumption"})
        rhs = item["rhs"].strip()
        conversion = re.fullmatch(rf"cpu_to_{kind}{width}\s*\((.*)\)", rhs, re.S)
        text = conversion.group(1) if conversion else rhs
        visible_macros, local_refused = {}, dict(refused)
        for name, definition in macros.items():
            if any(entry["file"] != source_path for entry in definition["definitions"]):
                local_refused[name] = "header macro visibility/preprocessor ordering not established by v4"
            elif any(entry["file"] == source_path and entry["line"] >= item["line"]
                   for entry in definition["definitions"]):
                local_refused[name] = "same-source macro definition is not established before the write"
            else:
                visible_macros[name] = definition
        proof = prove_expression(text, visible_macros, local_refused, scalars)
        item["expression_proof"] = proof
        item["proposed_check"] = None
        fits = proof["status"] == "proven" and all(
            m["minimum"] >= 0 and m["maximum"] < (1 << bits) for m in proof["models"])
        builtin_assumption = bool(re.search(r"\bBIT(?:_ULL)?\s*\(", text)) or any(
            re.search(r"\bBIT(?:_ULL)?\s*\(", record["expression"])
            for record in proof["macro_evidence"].values())
        proof["bit_model_assumption"] = builtin_assumption
        if fits:
            if conversion:
                item["status"], item["reason"] = "normal", "proven host integer expression explicitly converted to declared endian type at this site"
            elif byte_invariant(proof, bits):
                item["status"], item["reason"] = "normal", "proven exact value stores identical bytes in either byte order at this site"
            elif builtin_assumption:
                item["status"], item["reason"] = "insufficient", "BIT/BIT_ULL semantics are a model assumption here, not independently established source authority for a new candidate"
            elif item["interface_evidence"] or item["assignment_kind"] == "or_assignment":
                item["status"], item["reason"] = "candidate", "proven host-valued integer expression reaches explicitly endian-typed field without conversion"
                item["proposed_check"] = {
                    "kind": "representation_at_write", "condition": f"encode host integer as {target} before this {item['assignment_kind']}",
                    "conversion_shape": f"cpu_to_{kind}{width}(expression)",
                    "authority": "same-revision explicit destination type declaration",
                    "limits": "review lead only; descriptor mode, first consumer and runtime device contract still require review"}
            else:
                item["status"], item["reason"] = "insufficient", "host expression established but no supported object interface lead"
        elif proof["status"] == "proven":
            item["status"], item["reason"] = "insufficient", "host expression value range can be negative or exceed destination width"
        elif item["status"] in {"candidate", "normal"}:
            # Retain same-representation copy, not an unproven host expression.
            if (item.get("source_type") == target and not conversion and
                    re.fullmatch(v3.IDENT, rhs) and scalars.get(rhs) == target and
                    rhs not in visible_macros and rhs not in local_refused):
                item["status"], item["reason"] = "normal", "same explicit representation type copied locally"
            else:
                item["status"], item["reason"] = "insufficient", "v4 integer proof failed; see model-specific proof reasons"
    counts = Counter(item["status"] for item in report["findings"])
    report["counts"] = {status: counts[status] for status in ("candidate", "normal", "insufficient")}
    report["rule_version"] = VERSION
    report["scope"] = (
        "Bounded source triage: explicit __le/__be destination, supported object write grammar, "
        "source-local object macros before the write and integer expressions safe under both ILP32/LP64. Conditional/header macros, "
        "unknown calls, ambiguous declarations, unproven narrowing and alias-slot authority refused. "
        "BIT/BIT_ULL built-in semantics are an explicit model assumption and cannot create new candidates. "
        "No first-consumer, full preprocessing, path feasibility or hardware execution proof.")
    report["macro_refusals"] = refused
    return report


def analyze_revision(linux_dir: Path, revision: str, source_path: str) -> dict:
    files, skipped = v3.source_tree(linux_dir, revision, source_path)
    if source_path not in files:
        raise FileNotFoundError(f"source absent at revision {revision}: {source_path}")
    for path, contents in list(files.items()):
        for include in v3.QUOTED_INCLUDE.finditer(contents):
            child = v3.local_include_path(path, include.group(1))
            if child is None or child in files or len(files) >= 64:
                continue
            child_source = v3.git_file(linux_dir, revision, child)
            if child_source is None:
                skipped.append(f"unavailable third-edge include: {child}")
            else:
                files[child] = child_source
    for include in v3.UAPI_DIRECT_INCLUDE.finditer(files[source_path]):
        child = "include/uapi/" + include.group(1)
        if ".." in include.group(1).split("/") or child in files or len(files) >= 72:
            continue
        contents = v3.git_file(linux_dir, revision, child)
        if contents is None:
            skipped.append(f"unavailable direct UAPI include: {child}")
        else:
            files[child] = contents
    report = analyze_text(files[source_path], source_path, files)
    report["revision"] = revision
    report["files_read"] = [{"path": path, "sha256": v3.sha256(contents)} for path, contents in files.items()]
    report["include_notes"] = skipped
    report["implementation_sha256"] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (Path(__file__), Path(v3.__file__), Path(__file__).with_name("endian_consumer_single_revision.py"))}
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linux-dir", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = analyze_revision(args.linux_dir, args.revision, args.source)
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
