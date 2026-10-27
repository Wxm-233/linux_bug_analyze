"""Conditional finite-set effects of externally reviewed primitive summaries.

Input is an explicit, externally bound trace, not C. This module neither proves
the summaries/premises nor selects a real branch or establishes runtime values.
"""
import re
from .contract_protocol import _same


PREMISES = frozenset({"valid_storage", "legal_member_indices", "equal_logical_domains",
                      "distinct_nonoverlapping_storage", "source_bound_selected_trace",
                      "no_interference_during_trace", "summarized_calls_return_normally"})
ARITY = {"clear": 1, "add": 2, "copy": 2, "test": 2}


def interpret_set_trace(trace, registry, context, *, objects, members, output,
                        target, assumptions=frozenset(), initial=None):
    """Derive a local postcondition ONLY under explicitly assumed premises.

    Caller must bind IR operands and primitive summaries to actual source.
    Initial values, when supplied, are also conditional inputs. Even a complete
    result never certifies applicability, reachability or a consumer deadline.
    """
    result = {"status": "insufficient", "postcondition": None, "target_membership": None,
              "test_results": [], "reasons": [], "whole_contract": "insufficient",
              "premises_proved": False, "runtime_effects_proved": False,
              "source_binding_proved_by_this_module": False,
              "deadline_content": "unknown"}
    try:
        def require(value, message):
            if not value:
                raise ValueError(message)
        def identifier(value):
            return isinstance(value, str) and bool(re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", value))
        require(isinstance(context, dict) and identifier(context.get("revision"))
                and identifier(context.get("profile"))
                and type(context.get("logical_bits")) is int and 0 < context["logical_bits"] <= 65536,
                "invalid explicit context/domain")
        require(isinstance(assumptions, (set, frozenset)) and all(isinstance(x, str) for x in assumptions),
                "premises must be explicitly declared")
        result["assumed_premises"] = sorted(assumptions)
        require(PREMISES <= assumptions, "unresolved premises: " + ", ".join(sorted(PREMISES - assumptions)))
        require(isinstance(trace, dict) and trace.get("status") == "structural_terminal",
                "unsupported/incomplete path; no prefix-to-exit promotion")
        require(isinstance(objects, list) and isinstance(members, list)
                and 0 < len(objects) <= 16 and 0 < len(members) <= 16
                and all(identifier(x) for x in objects + members), "invalid abstract symbols")
        require(len(set(objects)) == len(objects) and len(set(members)) == len(members)
                and not set(objects) & set(members), "duplicate/ambiguous symbol domains")
        require(output in objects and target in members, "output/target is not declared")
        events = trace.get("events")
        require(isinstance(events, list) and 0 < len(events) <= 32 and isinstance(registry, dict),
                "invalid bounded trace/summary registry")
        require(initial is None or isinstance(initial, dict), "invalid initial-state input")
        states, written, tests = {}, set(), []
        for obj, values in (initial or {}).items():
            require(obj in objects and isinstance(values, list) and all(v in members for v in values)
                    and len(set(values)) == len(values), "invalid conditional initial contents")
            states[obj] = set(values)
        for event in events:
            require(isinstance(event, dict), "malformed trace event")
            summary = registry.get(event.get("summary"))
            require(isinstance(summary, dict) and summary.get("review_origin") == "researcher_review",
                    "missing external semantic review")
            require(_same(summary.get("context"), context), "summary context/version/domain mismatch")
            digest = summary.get("definition_sha256")
            require(isinstance(digest, str) and bool(re.fullmatch(r"[0-9a-f]{64}", digest))
                    and event.get("definition_sha256") == digest, "primitive definition identity mismatch")
            require(identifier(summary.get("review_id")) and isinstance(summary.get("references"), list)
                    and bool(summary["references"]), "summary lacks external review references")
            operation, args = summary.get("operation"), event.get("args")
            require(operation in ARITY and isinstance(args, list) and len(args) == ARITY[operation]
                    and all(identifier(a) for a in args), "unsupported operation/arguments")
            if operation == "clear":
                require(args[0] in objects, "clear requires an object")
                states[args[0]] = set()
                written.add(args[0])
            elif operation in {"add", "test"}:
                member, obj = args
                require(member in members and obj in objects and obj in states,
                        "member/object unknown or input contents unavailable")
                if operation == "add":
                    states[obj].add(member)
                    written.add(obj)
                else:
                    tests.append({"member": member, "object": obj, "truth": member in states[obj]})
            else:
                dst, src = args
                require(dst in objects and src in objects and src in states, "copy source/object unknown")
                require(dst != src, "alias case outside the nonoverlap summary")
                states[dst] = set(states[src])
                written.add(dst)
        require(output in written and output in states, "selected output was not established by this trace")
        result.update(status="conditional_postcondition", postcondition=sorted(states[output]),
                      target_membership=target in states[output], test_results=tests)
        result["reasons"].append("Conditional logical-domain effect under reviewed summaries and assumed premises; not a runtime observation.")
    except (ValueError, TypeError, KeyError) as error:
        result["reasons"].append(str(error))
    return result
