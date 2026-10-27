"""Bounded compiler-normal CFG facts; no runtime, alias or contract proof.

Accepted syntax is the observed GCC early-CFG record, with explicit successor
and loop metadata. Physical block adjacency is never an edge source.
"""
from __future__ import annotations
import hashlib
import re

from .gimple_local_flow import ASM_START, ScanError, _asm_end, _classify, _pure, _units, need

LOCATION = re.compile(r"\[([^\]\r\n]+):(\d+):(\d+)(?: discrim (\d+))?\]")
BB = re.compile(r"(?m)^[ \t]*<bb (\d+)>[ \t]*:[ \t]*\r?$")
BRANCH = re.compile(r"if\s*\((.*)\)\s*goto <bb (\d+)>;\s*else\s+goto <bb (\d+)>;")
GOTO = re.compile(r"goto <bb (\d+)>;")


def _view(text):
    mask, spans, locations, asms = list(text), [], [], {}
    index = 0
    def hide(start, stop, kind):
        spans.append({"kind": kind, "start_offset": start, "end_offset": stop, "raw": text[start:stop]})
        for at in range(start, stop):
            if mask[at] not in "\r\n": mask[at] = " "
    while index < len(text):
        start = index
        if text.startswith("/*", index):
            stop = text.find("*/", index + 2); need(stop >= 0, "unterminated_comment")
            index = stop + 2; hide(start, index, "comment"); continue
        if text.startswith("//", index):
            stop = text.find("\n", index + 2); index = len(text) if stop < 0 else stop
            hide(start, index, "comment"); continue
        loc = LOCATION.match(text, index)
        if loc:
            locations.append({"start_offset": index, "end_offset": loc.end(), "path": loc[1],
                              "line": int(loc[2]), "column": int(loc[3]),
                              "discriminator": int(loc[4]) if loc[4] else None})
            index = loc.end(); hide(start, index, "source_annotation"); continue
        if text.startswith("[INV]", index):
            index += 5; hide(start, index, "compiler_annotation"); continue
        if ASM_START.match(text, index) and (index == 0 or not (text[index - 1].isalnum() or text[index - 1] == "_")):
            index = _asm_end(text, start); asms[start] = index; hide(start, index, "asm"); continue
        if text[index] in {'"', "'"}:
            quote = text[index]; index += 1
            while index < len(text):
                need(text[index] not in "\r\n", "multiline_literal_outside_asm")
                if text[index] == "\\":
                    need(index + 1 < len(text), "unterminated_literal_escape"); index += 2
                elif text[index] == quote: index += 1; break
                else: index += 1
            else: raise ScanError("unterminated_literal")
            hide(start, index, "quoted_literal"); continue
        index += 1
    return "".join(mask), spans, locations, asms


def _metadata(prefix):
    function, declared_count, successors, loops, current = None, None, {}, {}, None
    for number, raw in enumerate(prefix.splitlines(), 1):
        line = raw.strip()
        if not line or line == ";;": continue
        match = re.fullmatch(r";; Function ([A-Za-z_]\w*) \([^\r\n]*\)", line)
        if match:
            need(function is None, "multiple_function_records"); function = match[1]; continue
        match = re.fullmatch(r";; (\d+) loops found", line)
        if match:
            need(declared_count is None, "duplicate_loop_count"); declared_count = int(match[1]); continue
        match = re.fullmatch(r";;\s+(\d+) succs \{\s*([\d\s]*)\}", line)
        if match:
            block, values = int(match[1]), [int(v) for v in match[2].split()]
            need(block not in successors and len(values) == len(set(values)), "duplicate_successor_record_or_target")
            successors[block] = {"targets": values, "dump_line": number, "raw": raw}; continue
        match = re.fullmatch(r";; Loop (\d+)", line)
        if match:
            current = int(match[1]); need(current not in loops, "duplicate_loop_id")
            loops[current] = {"id": current, "metadata_start_line": number}; continue
        match = re.fullmatch(r";;\s+header (\d+), (?:latch (\d+)|multiple latches: ([\d ]+))", line)
        if match:
            need(current is not None and "header" not in loops[current], "loop_header_without_unique_loop")
            loops[current].update(header=int(match[1]), latches=[int(match[2])] if match[2] else [int(v) for v in match[3].split()]); continue
        match = re.fullmatch(r";;\s+depth (\d+), outer (-?\d+)", line)
        if match:
            need(current is not None and "depth" not in loops[current], "loop_depth_without_unique_loop")
            loops[current].update(depth=int(match[1]), outer=int(match[2])); continue
        match = re.fullmatch(r";;\s+nodes: ([\d ]+)", line)
        if match:
            need(current is not None and "nodes" not in loops[current], "loop_nodes_without_unique_loop")
            loops[current]["nodes"] = [int(v) for v in match[1].split()]; continue
        raise ScanError("unsupported_metadata_line:" + str(number))
    need(function is not None and declared_count is not None and len(loops) == declared_count, "missing_function_or_loop_metadata")
    return function, successors, loops


def _locations(text, mask, locations, start, end, asms):
    found = []
    for loc in locations:
        if not start <= loc["start_offset"] < end: continue
        left = text.rfind("\n", 0, loc["start_offset"]) + 1
        right = text.find("\n", loc["end_offset"])
        if right < 0: right = len(text)
        if mask[max(left, start):min(right, end)].strip() or any(loc["end_offset"] <= at < right for at in asms if start <= at < end):
            found.append({key: loc[key] for key in ("path", "line", "column", "discriminator")})
    return found


def _events(text, mask, spans, locations, asms, start, end, block):
    raw = text[start:end]
    local_asms = {left - start: right - start for left, right in asms.items() if start <= left < end}
    units = _units(raw, mask[start:end], local_asms)
    events = []
    for number, (left, right, forced) in enumerate(units, 1):
        left += start; right += start
        code = " ".join(mask[left:right].split())
        quoted = any(span["kind"] == "quoted_literal" and left <= span["start_offset"] < right for span in spans)
        if not code and forced != "asm" and not quoted: continue  # retained lexical trivia, not a statement
        if quoted: forced = "opaque"
        branch, goto = BRANCH.fullmatch(code), GOTO.fullmatch(code)
        if forced:
            event = {"kind": forced, "defines": [], "uses": [], "barrier": True}
        elif branch and _pure(branch[1]):
            event = {"kind": "branch", "condition": branch[1], "targets": [{"branch": "true", "block": int(branch[2])}, {"branch": "false", "block": int(branch[3])}], "defines": [], "uses": [], "barrier": True}
        elif goto:
            event = {"kind": "goto", "targets": [{"branch": "unconditional", "block": int(goto[1])}], "defines": [], "uses": [], "barrier": True}
        else: event = _classify(code)
        need(event["kind"] != "opaque" or not re.search(r"\b(?:if|switch|goto|return)\b", code), "unsupported_control_statement")
        event.update(id="B" + str(block) + "S" + str(number), block=block, code=code, raw=text[left:right],
                     start_offset=left, end_offset=right, dump_line_start=text.count("\n", 0, left) + 1,
                     dump_line_end=text.count("\n", 0, right - 1) + 1,
                     source_locations=_locations(text, mask, locations, left, right, asms))
        events.append(event)
    return events


def _shape(event):
    kind = event.get("kind")
    if kind == "branch": return kind, re.sub(r"\s+", "", event.get("condition", ""))
    if kind == "goto": return kind,
    if kind == "asm":
        raw = event.get("raw", "")
        found = ASM_START.search(raw)
        if not found: return None
        try: stop = _asm_end(raw, found.start())
        except ScanError: return None
        return kind, hashlib.sha256(raw[found.start():stop].encode("utf-8")).hexdigest()
    if kind in {"opaque", "scope", "try", "finally", "function", "declaration"}: return None
    code = event.get("code")
    return (kind, re.sub(r"\s+", "", code)) if isinstance(code, str) and code else None


def _coordinates(event):
    return frozenset((loc.get("path"), loc.get("line"), loc.get("column")) for loc in event.get("source_locations", []) if isinstance(loc, dict))


def _full_coordinates(event):
    return frozenset((loc.get("path"), loc.get("line"), loc.get("column"), loc.get("discriminator")) for loc in event.get("source_locations", []) if isinstance(loc, dict))


def _bindings(document, local, events):
    bindings = []
    if local is None: return bindings
    need(isinstance(local, dict) and isinstance(local.get("events"), list), "invalid_local_analysis")
    same = local.get("document") == document.get("id")
    for original in local["events"]:
        need(isinstance(original, dict), "invalid_local_event")
        shape, coords = _shape(original), _coordinates(original)
        candidates = [event for event in events if shape is not None and coords and _coordinates(event) == coords and _shape(event) == shape] if same else []
        prior_matches = [event for event in local["events"] if isinstance(event, dict) and shape is not None and coords and _coordinates(event) == coords and _shape(event) == shape]
        bound = {"local_event": original.get("id"), "kind": original.get("kind"), "status": "insufficient", "cfg_event": None, "block": None,
                 "reason": "different_document_identity" if not same else "missing_supported_shape_or_exact_locus" if not shape or not coords else "no_exact_shape_locus_match" if not candidates else "ambiguous_shape_locus_match"}
        if candidates and len(prior_matches) != 1:
            bound["reason"] = "ambiguous_old_shape_locus_match"
        elif len(candidates) == 1:
            if _full_coordinates(original) != _full_coordinates(candidates[0]):
                bound["reason"] = "insufficient_discriminator_not_comparable"
            else:
                bound.update(status="unique", reason="exact_locus_and_normalized_shape", cfg_event=candidates[0]["id"], block=candidates[0]["block"])
        bindings.append(bound)
    return bindings


def _linear_prefix(start, source, blocks):
    chain, seen, current = [], set(), start
    while current in blocks and current != source and current not in seen:
        seen.add(current); chain.append(current)
        block = blocks[current]
        if any(event["kind"] == "opaque" for event in block["events"]): return chain, "opaque_block"
        targets = block["compiler_successors"]
        if len(targets) != 1: return chain, "nonlinear_or_terminal_block"
        current = targets[0]
    return chain, "source_revisit" if current == source else "cycle" if current in seen else "virtual_exit"


def _relations(blocks, loops):
    relations, arms = [], []
    for block in blocks.values():
        branch = block.get("terminator")
        if not branch or branch["kind"] != "branch": continue
        paths = {arm["branch"]: _linear_prefix(arm["block"], block["id"], blocks) for arm in branch["targets"]}
        true, false = paths["true"][0], paths["false"][0]
        common = [node for node in true if node in false]
        join = common[0] if common else None
        prefixes = {name: path[:path.index(join)] if join in path else path for name, (path, _) in paths.items()}
        arms.append({"branch_event": branch["id"], "block": block["id"], "condition": branch["condition"],
                     "linear_join": join, "prefixes": prefixes, "stop_reasons": {name: stop for name, (_, stop) in paths.items()},
                     "semantics": "compiler normal single-successor prefixes before a common block; not postdomination or must-return"})
        if join is not None:
            for name, prefix in prefixes.items():
                for node in prefix:
                    for event in blocks[node]["events"]:
                        if event["kind"] == "store":
                            relations.append({"kind": "branch_to_store", "branch_event": branch["id"], "branch_block": block["id"], "arm": name,
                                              "store_event": event["id"], "store_block": node, "linear_join": join, "arm_prefix": prefix,
                                              "scope": "single-successor arm prefix before join and before source re-evaluation"})
                        if event["kind"] == "asm":
                            relations.append({"kind": "branch_arm_asm_rejoins", "branch_event": branch["id"], "arm": name,
                                              "asm_event": event["id"], "asm_block": node, "linear_join": join, "arm_prefix": prefix,
                                              "asm_returns_proved": False})
        for loop in loops:
            if loop["id"] == 0 or block["id"] not in loop["nodes"]: continue
            for arm in branch["targets"]:
                if arm["block"] not in loop["nodes"]:
                    target = blocks.get(arm["block"])
                    relations.append({"kind": "branch_arm_exits_loop", "branch_event": branch["id"], "branch_block": block["id"],
                                      "arm": arm["branch"], "target_block": arm["block"], "loop": loop["id"],
                                      "target_assignments": [e["id"] for e in target["events"] if e["kind"] == "scalar_assign"] if target else [],
                                      "target_successors": target["compiler_successors"] if target else [],
                                      "scope": "reported loop membership and direct compiler successor only; no witness semantics"})
    for block in blocks.values():
        for event in block["events"]:
            if event["kind"] == "asm": relations.append({"kind": "asm_normal_successors", "asm_event": event["id"], "asm_block": block["id"],
                                                        "successors": block["compiler_successors"], "asm_returns_proved": False})
    return relations, arms


def analyze_cfg(document, local_analysis=None):
    result = {"status": "insufficient_cfg_input", "document": document.get("id"), "path": document.get("path"), "revision": document.get("revision"),
              "source_sha256": None, "blocks": [], "edges": [], "branch_polarity": [], "loops": [], "event_bindings": [],
              "relations": [], "branch_arms": [], "unknowns": [], "runtime_reachability_proved": False,
              "asm_or_call_must_return_proved": False, "alias_or_contract_proved": False}
    try:
        text = document.get("text"); need(isinstance(text, str), "missing_text")
        result["source_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        mask, spans, locations, asms = _view(text)
        headers = list(BB.finditer(mask)); need(headers, "no_body_blocks")
        signature = re.search(r"(?m)^([^;{}\r\n]+?)\s*\{", mask[:headers[0].start()])
        need(signature is not None, "missing_function_body_opening")
        function, successors, loop_map = _metadata(text[:signature.start()])
        need(re.search(r"\b" + re.escape(function) + r"\s*\([^;{}]*\)\s*$", signature[1]) is not None, "function_signature_mismatch")
        opening = signature.end() - 1
        last = len(mask.rstrip()) - 1
        need(last > headers[-1].end() and mask[last] == "}", "missing_unique_function_closing")
        need(mask[opening:last + 1].count("{") == mask[opening:last + 1].count("}"), "unbalanced_function_braces")
        prefix = mask[opening + 1:headers[0].start()]
        for left, right, forced in _units(prefix, prefix, {}):
            need(forced is None and _classify(" ".join(prefix[left:right].split()))["kind"] == "declaration", "unsupported_preblock_statement")
        block_map, all_events = {}, []
        for index, header in enumerate(headers):
            block = int(header[1]); need(block >= 2 and block not in block_map, "duplicate_or_virtual_body_block")
            start, end = header.end(), headers[index + 1].start() if index + 1 < len(headers) else last
            events = _events(text, mask, spans, locations, asms, start, end, block)
            controls = [event for event in events if event["kind"] in {"branch", "goto", "return"}]
            need(len(controls) <= 1 and (not controls or events[-1]["id"] == controls[0]["id"]), "nonterminal_or_multiple_control_statements")
            block_map[block] = {"id": block, "header_line": text.count("\n", 0, header.start()) + 1, "start_offset": start, "end_offset": end,
                                "events": events, "terminator": controls[0] if controls else None}
            all_events.extend(events)
        need(set(successors) == set(block_map), "body_successor_key_mismatch")
        need(len(block_map) <= 256, "block_budget_exceeded")
        for block in block_map.values():
            targets = successors[block["id"]]["targets"]
            need(all(target in block_map or target == 1 for target in targets), "unknown_successor_target")
            block["compiler_successors"] = targets
            block["successor_metadata"] = successors[block["id"]]
            terminal = block["terminator"]
            if terminal and terminal["kind"] in {"branch", "goto"}:
                explicit = [row["block"] for row in terminal["targets"]]
                need(len(explicit) == len(set(explicit)) and set(explicit) == set(targets), "explicit_successors_disagree")
                if terminal["kind"] == "branch":
                    result["branch_polarity"].append({"event": terminal["id"], "block": block["id"], "condition": terminal["condition"], "targets": terminal["targets"], "source": "explicit_polarity_agrees_with_successor_metadata"})
            elif terminal and terminal["kind"] == "return": need(targets == [1], "return_exit_disagrees")
            else: need(len(targets) <= 1, "multiple_successors_without_supported_branch")
        nodes = set(block_map) | {0, 1}
        need(0 in loop_map, "missing_synthetic_outer_loop")
        for loop in loop_map.values():
            need(set(loop) >= {"id", "header", "latches", "depth", "outer", "nodes"}, "incomplete_loop_metadata")
            members = set(loop["nodes"])
            need(len(members) == len(loop["nodes"]) and members <= nodes and loop["header"] in members and set(loop["latches"]) <= members, "invalid_loop_membership")
            if loop["id"] == 0:
                need(loop["header"] == 0 and loop["latches"] == [1] and loop["depth"] == 0 and loop["outer"] == -1 and members == nodes, "invalid_synthetic_loop")
            else:
                parent = loop_map.get(loop["outer"])
                need(parent is not None and loop["depth"] == parent["depth"] + 1 and members <= set(parent["nodes"]) and members <= set(block_map), "invalid_loop_parent")
                need(loop["latches"] and len(loop["latches"]) == len(set(loop["latches"])) and all(loop["header"] in successors[latch]["targets"] for latch in loop["latches"]), "loop_latch_edge_missing")
            loop["exit_edges"] = [{"source": source, "target": target} for source in sorted(members & set(block_map)) for target in successors[source]["targets"] if target not in members]
        edges = [{"source": block, "target": target, "metadata_line": record["dump_line"], "origin": "compiler_successor_metadata", "normal_graph_only": True}
                 for block, record in successors.items() for target in record["targets"]]
        loops = list(loop_map.values())
        relations, arms = _relations(block_map, loops)
        bindings = _bindings(document, local_analysis, all_events)
        unknowns = [{"event": event["id"], "kind": event["kind"], "reason": "opaque_or_effect_semantics_not_established"} for event in all_events if event["kind"] in {"asm", "opaque", "call", "clobber"}]
        result.update(status="compiler_normal_graph_facts", function=function, blocks=list(block_map.values()), edges=edges, loops=loops,
                      event_bindings=bindings, relations=relations, branch_arms=arms, unknowns=unknowns, lexical_spans=spans,
                      local_analysis_source_sha256=local_analysis.get("source_sha256") if isinstance(local_analysis, dict) else None,
                      cross_ir_identity_assumption="caller verifies same profile/revision/config/preprocessed input; module matches exact locus and normalized syntax only")
    except (ScanError, ValueError, TypeError, KeyError, AttributeError, IndexError) as exc:
        result["unknowns"].append({"reason": str(exc)})
        result["branch_polarity"] = []
    return result
