"""Lexical regions and source coordinates from existing GCC preprocessing.

This is not a C parser, control-flow analysis or macro-expansion reconstructor.
It retains compiler text unchanged; unsupported/missing provenance is an error.
"""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
import hashlib
import re


class EvidenceError(ValueError):
    pass


@dataclass(frozen=True)
class Token:
    value: str
    start: int
    end: int
    top_level: bool


_QUOTED = re.compile(r'''"(?:\\[\s\S]|[^"\\])*"|'(?:\\[\s\S]|[^'\\])*' ''', re.X)
_WORD = re.compile(r"[A-Za-z_][A-Za-z_0-9]*|[0-9]+")
_MARKER = re.compile(r'#\s*(?:line\s+)?(\d+)\s+"((?:\\.|[^"\\])*)"((?:\s+\d+)*)\s*')


def _filename(value):
    def unescape(match):
        if match[1] not in {'\\', '"'}:
            raise EvidenceError("unsupported filename escape in line marker")
        return match[1]
    return re.sub(r'\\(.)', unescape, value)


def _lex(text):
    tokens, pairs, directives, stack = [], {}, {}, []
    pos, size = 0, len(text)
    while pos < size:
        char = text[pos]
        if char.isspace():
            pos += 1
            continue
        if text.startswith("/*", pos):
            end = text.find("*/", pos + 2)
            if end < 0:
                raise EvidenceError("unterminated block comment")
            pos = end + 2
            continue
        if text.startswith("//", pos):
            end = text.find("\n", pos)
            pos = size if end < 0 else end
            continue
        if char == "#":
            line_start = text.rfind("\n", 0, pos) + 1
            if text[line_start:pos].strip():
                raise EvidenceError("unexpected preprocessor token outside a directive")
            end = text.find("\n", pos)
            end = size if end < 0 else end
            raw = text[pos:end].rstrip("\r")
            match = _MARKER.fullmatch(raw)
            if match:
                directives[line_start] = {
                    "kind": "line_marker", "line": int(match[1]),
                    "path": _filename(match[2]), "flags": [int(v) for v in match[3].split()],
                }
            elif re.fullmatch(r'#\s*pragma(?:\s+.*)?', raw):
                directives[line_start] = {"kind": "pragma", "text": raw}
            else:
                raise EvidenceError("unprocessed or unsupported preprocessor directive")
            pos = end
            continue
        quoted = _QUOTED.match(text, pos) if char in {'"', "'"} else None
        if char in {'"', "'"} and quoted is None:
            raise EvidenceError("unterminated quoted literal")
        word = None if quoted else _WORD.match(text, pos)
        end = quoted.end() if quoted else word.end() if word else pos + 1
        token = Token(text[pos:end], pos, end, not stack)
        index = len(tokens)
        tokens.append(token)
        if not quoted:
            if char in "({[":
                stack.append((char, index))
            elif char in ")}]":
                if not stack or stack[-1][0] != {")": "(", "}": "{", "]": "["}[char]:
                    raise EvidenceError("unbalanced delimiters in preprocessing")
                _, opening = stack.pop()
                pairs[opening] = index
        pos = end
    if stack:
        raise EvidenceError("truncated preprocessing: unclosed delimiter")
    return tokens, pairs, directives


def extract_definitions(text: str, names: dict[str, str], *, allow_declarations=()) -> dict:
    """Select unique lexical definitions by name AND expected source suffix.

    Names explicitly listed in allow_declarations may return a declaration ONLY
    when there is no definition; its region_kind/evidence layer says so. Default
    selection remains strict. GCC markers map the following line, with flags
    retained, not interpreted
    as a proof of include dependencies or expansion provenance. No compiler text
    is removed from an extracted region, including pragmas and internal markers.
    """
    if "\\\n" in text or "\\\r\n" in text:
        raise EvidenceError("line-spliced input is outside this lexer")
    if not names or any(not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", n) for n in names):
        raise EvidenceError("invalid definition selector")
    if not set(allow_declarations) <= set(names):
        raise EvidenceError("declaration policy has unselected names")
    tokens, pairs, directives = _lex(text)
    openings = {closing: opening for opening, closing in pairs.items()}
    starts = [0] + [m.end() for m in re.finditer("\n", text)]
    origins, path, source_line = [], None, None
    for physical, start in enumerate(starts, 1):
        directive = directives.get(start)
        if directive and directive["kind"] == "line_marker":
            origins.append({"physical_line": physical, "marker": directive})
            path, source_line = directive["path"], directive["line"]
        else:
            origins.append({"physical_line": physical, "path": path, "line": source_line,
                            **({"directive": directive} if directive else {})})
            if source_line is not None:
                source_line += 1

    def location(offset):
        index = bisect_right(starts, offset) - 1
        # Line markers do not encode original source columns.
        return {**origins[index], "preprocessed_column": offset - starts[index] + 1}

    found = {n: [] for n in names}
    declarations = {n: [] for n in names}
    declaration_start = 0
    for index, token in enumerate(tokens):
        if token.top_level and token.value in names and index + 1 < len(tokens) and tokens[index + 1].value == "(":
            closing = pairs[index + 1]
            next_token = closing + 1
            # GNU attributes may appear after the parameter list; retain them.
            while (next_token + 1 < len(tokens) and tokens[next_token].value in {"__attribute__", "__attribute"}
                   and tokens[next_token + 1].value == "("):
                next_token = pairs[next_token + 1] + 1
            is_definition = next_token < len(tokens) and tokens[next_token].value == "{"
            is_declaration = (token.value in allow_declarations and next_token < len(tokens)
                              and tokens[next_token].value == ";")
            if is_definition or is_declaration:
                origin = location(token.start)
                expected = names[token.value].replace("\\", "/")
                actual = (origin.get("path") or "").replace("\\", "/")
                absolute_selector = expected.startswith("/") or bool(re.match(r"^[A-Za-z]:/", expected))
                if actual != expected and (absolute_selector or not actual.endswith("/" + expected)):
                    continue
                end_index = pairs[next_token] if is_definition else next_token
                selected = tokens[declaration_start:end_index + 1]
                for part in selected:
                    point = location(part.start)
                    if not point.get("path") or not isinstance(point.get("line"), int) or point["line"] < 1:
                        raise EvidenceError("definition has missing or nonpositive source coordinates")
                begin, end = selected[0].start, tokens[end_index].end
                first_line = location(begin)["physical_line"]
                last_line = location(end - 1)["physical_line"]
                raw = text[begin:end]
                symbols = {}
                mapped_sources = set()
                for part in selected:
                    mapped_sources.add(location(part.start)["path"])
                    if re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", part.value):
                        symbols.setdefault(part.value, []).append(location(part.start))
                collection = found if is_definition else declarations
                collection[token.value].append({
                    "name": token.value, "expected_source": expected, "text": raw,
                    "region_kind": "definition" if is_definition else "declaration_only",
                    "source_selector_match": "absolute_name_location" if absolute_selector else "suffix_name_location",
                    "mapped_token_sources": sorted(mapped_sources),
                    "all_token_paths_match_name_location": mapped_sources == {origin["path"]},
                    "sha256": hashlib.sha256(raw.encode()).hexdigest(),
                    "start_offset": begin, "end_offset": end,
                    "offset_unit": "Unicode code points in decoded compiler text",
                    "utf8_byte_start": len(text[:begin].encode()),
                    "utf8_byte_end": len(text[:end].encode()),
                    "physical_start_line": first_line, "physical_end_line": last_line,
                    "name_location": origin,
                    **({"definition_location": origin} if is_definition else {"declaration_location": origin}),
                    "line_map": origins[first_line - 1:last_line], "identifiers": symbols,
                    "evidence_layer": "lexical_region_in_existing_configured_preprocessing" if is_definition
                                      else "external_declaration_in_configured_preprocessing_no_body",
                    "control_flow_proved": False, "runtime_content_proved": False,
                })
        if token.value == ";" and token.top_level:
            declaration_start = index + 1
        elif token.value == "}":
            # Do not discard an inline aggregate return type before its function
            # name. Ordinary function bodies follow a closing parameter/attribute
            # parenthesis; aggregate declarations wait for their semicolon.
            opening = openings[index]
            if (opening > 0 and tokens[opening - 1].value == ")"
                    and (index + 1 == len(tokens) or tokens[index + 1].top_level)):
                declaration_start = index + 1
    result = {}
    for name, matches in found.items():
        if not matches and name in allow_declarations:
            matches = declarations[name]
        if len(matches) != 1:
            raise EvidenceError(f"expected one definition for {name} in {names[name]}, found {len(matches)}")
        result[name] = matches[0]
    return result
