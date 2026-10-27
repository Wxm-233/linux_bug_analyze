"""Explicit output-format instructions for one raw-parent material group.

This module does not read source bodies, resolve C, call a model, or validate
source provenance. The caller still has to bind the packet's original bytes.
"""
from __future__ import annotations

import json
import re


SCHEMA = "n25_contract_candidates_v1"
EXAMPLE_ID = "__FORMAT_ONLY__"
EXAMPLE_TEXT = "void format_worker(void)\n{\n  prepare();\n  consume();\n}\n"


def _identity(packet):
    if not isinstance(packet, dict) or packet.get("schema") != SCHEMA:
        raise ValueError("packet_schema_mismatch")
    parents = packet.get("case_parents")
    if not isinstance(parents, dict) or len(parents) != 1:
        raise ValueError("single_case_parent_required")
    case, parent = next(iter(parents.items()))
    if not (isinstance(case, str) and re.fullmatch(r"[A-Za-z0-9_-]+", case)
            and isinstance(parent, str) and re.fullmatch(r"[0-9a-f]{40}", parent)):
        raise ValueError("case_parent_malformed")
    docs = packet.get("documents")
    if not isinstance(docs, list) or not docs or len(docs) > 8:
        raise ValueError("documents_missing_or_oversized")
    ids = []
    group = case + "_parent"
    for doc in docs:
        if not (isinstance(doc, dict) and isinstance(doc.get("id"), str) and doc["id"].strip()
                and doc["id"] != EXAMPLE_ID and doc.get("case") == case
                and doc.get("parent") == doc.get("revision") == parent
                and doc.get("profile") == group and doc.get("kind") == "raw_source_file"):
            raise ValueError("material_identity_mismatch")
        ids.append(doc["id"])
    if len(set(ids)) != len(ids):
        raise ValueError("document_id_ambiguous")
    return group, ids


def schema_description(packet):
    """Return a fresh format description, without changing the input packet.

    The synthetic document is deliberately outside the real allowed IDs. It
    illustrates syntax only; its claims must not be copied into real analysis.
    """
    group, ids = _identity(packet)
    evidence = {"document": EXAMPLE_ID, "start_line": 3, "end_line": 4}
    output = {
        "schema": SCHEMA,
        "requirements": [{"id": "R1", "statement": "仅合成格式示例，不是待分析源码的要求",
                          "basis": "hypothesis", "applicability": ["仅格式示例"],
                          "evidence": [dict(evidence)], "unproved": ["调用顺序不证明效果"]}],
        "architecture_paths": [{"profile": group, "requirement_id": "R1",
                                "provider_object": "仅合成示例", "eligibility": "未知",
                                "deadline": "未知", "assessment": "insufficient",
                                "evidence": [dict(evidence)], "unproved": ["没有架构或配置证明"]}],
        "local_checks": [{"id": "L1", "kind": "lexical_call_order", "profile": group,
                          "document": EXAMPLE_ID, "function": "format_worker",
                          "first": {"callee": "prepare", "line": 3},
                          "second": {"callee": "consume", "line": 4}, "expected": "before",
                          "evidence": [dict(evidence)]}],
        "recommended_checks": [{"id": "T1", "requirement_id": "R1", "predicate": "仅格式占位",
                                "placement": "未知", "evidence": [dict(evidence)],
                                "facts_needed": ["仍需实际源码语义"], "status": "insufficient"}],
        "limits": ["仅格式演示；不是配置、控制流、效果或缺陷证明"],
    }
    return {
        "schema": SCHEMA, "required_material_group": group, "allowed_document_ids": ids,
        "material_group_is_architecture_or_configuration_proof": False,
        "evidence_exact_keys": ["document", "start_line", "end_line"],
        "evidence_coordinate_rule": "start_line/end_line为非bool整数，按完整文档1起始行号，1<=start<=end<=文档行数，end-start+1<=24",
        "evidence_example": {"document": ids[0], "start_line": 1, "end_line": 1},
        "bounds": {"requirements": 3, "architecture_paths": 6, "local_checks": 6},
        "synthetic_example": {"warning": "此文档不是任务材料，真实回答严禁引用其ID、函数或结论",
                              "document": {"id": EXAMPLE_ID, "profile": group, "text": EXAMPLE_TEXT},
                              "output": output},
    }


def render_schema_instructions(packet):
    description = schema_description(packet)
    return ("输出一个完整JSON对象，顶层必须恰含schema、requirements、architecture_paths、local_checks、recommended_checks、limits。\n"
            "本任务profile必须逐字使用下方required_material_group，不能输出CASE_parent或解释性后缀；它只表示材料身份。\n"
            "evidence每项恰含document/start_line/end_line，行号必须为整数且每段最多24行；不接受lines字符串。\n"
            "实际引文document必须来自allowed_document_ids；无充分材料可留空候选列表，不补造事实。\n"
            "局部项只支持同一完整函数内独立调用语句；if条件、赋值右侧、嵌套调用或未知C形式不要强填。"
            "即使调用顺序成立，也不能推导配置合法、控制流、对象效果或准备完成。\n"
            "下方synthetic_example仅展示完整字段；其专用文档ID不属于实际材料，不得抄作分析。\n"
            + json.dumps(description, ensure_ascii=False, indent=2))
