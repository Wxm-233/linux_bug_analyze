"""One authorized public-source review, separate from the frozen Claude rounds.

Final message content only; no hidden reasoning retained or treated as an answer.
No automatic retries. A recorded attempt cannot be silently resumed/replaced.
"""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
import time
import tomllib
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROFILE = ROOT / "analysis_out/kimi-k3-main/settings.toml"
PACKET = HERE / "model_source_packet.json"
LEDGER = HERE / "kimi_ledger.json"
PLAN = HERE / "kimi_plan.json"
PRIOR_RESEARCH = 285901
CONNECTIVITY = 193
TOTAL_LIMIT = 1_000_000
MAX_OUTPUT = 24576

TASK = """请仅根据附件中的旧版Linux源码和配置片段，深入分析cpu_smt_mask在CPU启动公共消费路径上的隐含契约，并给出可供检查工具使用的候选检查卡。
这是已读历史案例的机制开发，不是独立检测或盲测。你没有收到修复补丁、实际运行、研究者反例或期望答案；不要猜测这些材料的结果。
请围绕架构差异来源→公共接口→共同消费→为何某架构可能暴露而另一架构未暴露组织分析，不把一般C错误直接当跨架构机制。沿实参/形参、初始化对象、配置和提供者路径逐段核对，区分取指针与读取集合内容。
请重点说明：
1. 从公共消费者及接口用途可以提出哪些必要条件？哪些是分支条件、可观察告警、建议性防御策略，哪些无法从这些片段推出？不要把必要条件说成充分正确性，也不要把无WARN等同正确。逐行核对两个循环是否处理当前CPU、单成员分支实际检查了什么、leader的初始状态与存在条件。
2. x86和s390分别怎样准备该状态、准备资格是什么、共同消费的期限在哪里？CPU尚未online是否本身就能判为违规？说明配置宏、非SMT情形与对象身份依据。静态为零、一次update或函数中的先后关系不能替代整个启动路径及其他writer证明。
3. 若设计检查卡，写出适用范围、条件、证据来源、可检查位置和缺证据时的拒判规则；哪些需要补初始化/调用顺序/运行时点/并发证据？不得虚构精确观测值、其他writer已排除或完整控制流。
4. 哪些对照最能区分错误检查与有依据的检查？提出有限的逻辑反例，不把构造输入声称为真实架构可达或新增缺陷。
用中文写充分但聚焦的分析，允许明确保留不确定或反对候选。引用用DOC_ID:L起始-L结束，引用实际给出的行号；不限制引用数量或强制JSON，不因格式重试。文档行号核验只说明引用可定位，不证明语义正确。
"""


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare():
    base = HERE.parent
    old = json.loads((base / "state_context_binding_20261015/source_packet.json").read_text(encoding="utf-8-sig"))
    extra = json.loads((base / "claude_contract_resume_20261015/source_additions.json").read_text(encoding="utf-8-sig"))
    docs = old["original_source_request"]["documents"] + old["supplemental_documents"] + extra["documents"]
    assert len(docs) == len({d["id"] for d in docs}) == 41
    # All text is public Linux code or bounded nonsecret configuration excerpts.
    for doc in docs:
        assert doc["kind"] in {"source", "configuration"}
        assert not re.search(r"\bsk-[A-Za-z0-9_-]{12,}", doc["text"])
        if doc["kind"] == "source":
            # Original documents inherit the original request's revision.
            assert doc.get("revision", old["original_source_request"]["revision"]) == old["revision"]
        numbers = [int(line.split(":", 1)[0]) for line in doc["text"].splitlines()]
        assert numbers == list(range(doc["start_line"], doc["end_line"] + 1)), doc["id"]
    packet = {
        "revision": old["revision"],
        "purpose": "Known-case public-source-only mechanism review; not independent detection",
        "not_supplied": ["fix patch", "runtime logs", "probe inputs or results", "researcher candidate card", "previous model candidates", "credentials"],
        "documents": docs,
    }
    text = json.dumps(packet, ensure_ascii=False, indent=2) + "\n"
    if PACKET.exists():
        assert PACKET.read_text(encoding="utf-8") == text, "Prepared payload changed"
    else:
        PACKET.write_text(text, encoding="utf-8")
    payload = {"model": "Kimi-K3", "messages": [{"role": "user", "content": TASK + "\n" + text}], "max_tokens": MAX_OUTPUT, "stream": False}
    wire = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    # Conservative local reservation; not provider token accounting or confirmed spend.
    reserve = len(wire) + MAX_OUTPUT
    plan = {
        "id": "kimi_source_contract_once",
        "endpoint": "https://llmapi.isrc.ac.cn/v1/chat/completions",
        "model": "Kimi-K3", "documents": len(docs),
        "source_lines": sum(len(d["text"].splitlines()) for d in docs),
        "payload_sha256": hashlib.sha256(wire).hexdigest(),
        "payload_utf8_bytes": len(wire), "max_output_tokens": MAX_OUTPUT,
        "prior_research_conservative": PRIOR_RESEARCH, "prior_connectivity_known": CONNECTIVITY,
        "this_unknown_reservation": reserve, "total_budget": TOTAL_LIMIT,
        "maximum_conservative_after_attempt": PRIOR_RESEARCH + CONNECTIVITY + reserve,
        "automatic_retries": 0, "timeout_seconds": 480,
        "credential_in_payload_or_repository": False,
        "new_cases": 0, "independent_validation": False,
    }
    assert plan["maximum_conservative_after_attempt"] <= TOTAL_LIMIT
    if PLAN.exists():
        assert json.loads(PLAN.read_text(encoding="utf-8")) == plan, "Plan changed"
    else:
        dump(PLAN, plan)
    return payload, plan


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()
    payload, plan = prepare()
    if not args.run:
        print(json.dumps({"mode": "dry_run_no_network", **plan}, ensure_ascii=False))
        return
    if LEDGER.exists():
        print(json.dumps({"status": "attempt_already_recorded_never_auto_repeat"}))
        return
    settings = tomllib.loads(PROFILE.read_text(encoding="utf-8-sig"))["openai"]
    assert settings["model"] == payload["model"]
    assert settings["base_url"].rstrip("/") + "/chat/completions" == plan["endpoint"]
    key_path = Path(settings["api_key_file"])
    assert key_path.is_absolute() and not key_path.is_relative_to(ROOT)
    key = key_path.read_text(encoding="utf-8").strip()
    assert key
    def safe(value):
        return re.sub(r"\bsk-[A-Za-z0-9_-]{12,}", "[REDACTED]", str(value).replace(key, "[REDACTED]"))
    ledger = {**plan, "status": "started", "started_at": datetime.now(timezone.utc).isoformat(), "reservation_kept": True}
    # Exclusive creation protects against duplicate local invocations.
    with LEDGER.open("x", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)
        f.write("\n")
    started = time.monotonic()
    try:
        req = urllib.request.Request(plan["endpoint"], data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), headers={"Content-Type": "application/json", "Authorization": "Bearer " + key}, method="POST")
        opener = urllib.request.build_opener(NoRedirect)
        try:
            with opener.open(req, timeout=480) as response:
                status, body = response.status, response.read()
        except urllib.error.HTTPError as e:
            status, body = e.code, e.read()
        ledger["http_status"] = status
        data = json.loads(body)
        choices = data.get("choices") or []
        choice = choices[0] if len(choices) == 1 else {}
        final = (choice.get("message") or {}).get("content")
        final = safe(final) if isinstance(final, str) else ""
        usage = {k: v for k, v in (data.get("usage") or {}).items() if k in ("prompt_tokens", "completion_tokens", "total_tokens") and type(v) is int}
        ledger.update(model_returned=data.get("model"), finish_reason=choice.get("finish_reason"), usage=usage, final_characters=len(final))
        if data.get("error"):
            ledger["provider_error"] = safe(json.dumps(data["error"], ensure_ascii=False))[:500]
        if final:
            (HERE / "kimi_final.md").write_text(final, encoding="utf-8")
            ledger["final_sha256"] = hashlib.sha256(final.encode()).hexdigest()
        valid = 200 <= status < 300 and data.get("model") == payload["model"] and choice.get("finish_reason") == "stop" and bool(final.strip())
        ledger["status"] = "final_received_requires_semantic_review" if valid else "no_complete_matching_final"
        if type(usage.get("total_tokens")) is int and usage["total_tokens"] >= 0:
            ledger["reservation_kept"] = False
            ledger["conservative_accounted_this_attempt"] = usage["total_tokens"]
        # Provider raw body may contain nonfinal reasoning: never archive it as evidence.
    except Exception as error:
        ledger.update(status="request_error_no_auto_retry", error_type=type(error).__name__)
    ledger.setdefault("conservative_accounted_this_attempt", plan["this_unknown_reservation"])
    ledger["conservative_total_including_connection"] = PRIOR_RESEARCH + CONNECTIVITY + ledger["conservative_accounted_this_attempt"]
    ledger["elapsed_seconds"] = round(time.monotonic() - started, 3)
    dump(LEDGER, ledger)
    print(json.dumps(ledger, ensure_ascii=False))


if __name__ == "__main__":
    main()
