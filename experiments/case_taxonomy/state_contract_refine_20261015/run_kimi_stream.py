"""One explicit streaming amendment after HTTP 504; original attempt preserved."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import re
import time
import tomllib
import urllib.error
import urllib.request
import run_kimi_review as base

HERE = Path(__file__).resolve().parent
LEDGER = HERE / "kimi_stream_ledger.json"
FINAL = HERE / "kimi_stream_final.md"


def read_final_sse(lines):
    """Read standard single-data-line Chat Completions events, final content only."""
    parts, models, usage, finish = [], set(), {}, None
    events, done = 0, False
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith(b":") or line.startswith(b"event:"):
            continue
        if not line.startswith(b"data:"):
            raise ValueError("Unsupported SSE framing")
        data = line[5:].strip()
        if data == b"[DONE]":
            done = True
            break
        item = json.loads(data)
        if item.get("error"):
            raise ValueError("Provider stream error")
        events += 1
        if item.get("model"):
            models.add(item["model"])
        if isinstance(item.get("usage"), dict):
            usage.update({k: v for k, v in item["usage"].items() if k in ("prompt_tokens", "completion_tokens", "total_tokens") and type(v) is int})
        for choice in item.get("choices") or []:
            if choice.get("index", 0) != 0:
                raise ValueError("Unexpected choice index")
            text = (choice.get("delta") or {}).get("content")
            if isinstance(text, str):
                parts.append(text)
            if choice.get("finish_reason") is not None:
                finish = choice["finish_reason"]
    return {"final": "".join(parts), "models_returned": sorted(models), "usage": usage,
            "finish_reason": finish, "done_received": done, "events": events}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    payload, old_plan = base.prepare()
    previous = json.loads(base.LEDGER.read_text(encoding="utf-8"))
    assert previous.get("http_status") == 504 and previous.get("reservation_kept") is True
    payload.update(stream=True, stream_options={"include_usage": True})
    wire = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    prior = previous["conservative_total_including_connection"]
    reserve = len(wire) + base.MAX_OUTPUT
    plan = {"id": "kimi_same_source_stream_amendment_once", "reason": "original nonstream HTTP 504 without final or usage; preserve original unknown reservation",
            "endpoint": old_plan["endpoint"], "model": "Kimi-K3", "source_packet": base.PACKET.name,
            "payload_sha256": hashlib.sha256(wire).hexdigest(), "payload_utf8_bytes": len(wire),
            "stream": True, "max_output_tokens": base.MAX_OUTPUT, "automatic_retries": 0,
            "prior_conservative_including_connection": prior, "this_unknown_reservation": reserve,
            "total_budget": base.TOTAL_LIMIT, "maximum_conservative_after_attempt": prior + reserve}
    assert plan["maximum_conservative_after_attempt"] <= base.TOTAL_LIMIT
    plan_file = HERE / "kimi_stream_plan.json"
    if plan_file.exists():
        assert json.loads(plan_file.read_text(encoding="utf-8")) == plan
    else:
        base.dump(plan_file, plan)
    if not args.run:
        print(json.dumps({"mode": "dry_run_no_network", **plan})); return
    if LEDGER.exists():
        print(json.dumps({"status": "stream_attempt_recorded_never_auto_repeat"})); return
    config = tomllib.loads(base.PROFILE.read_text(encoding="utf-8-sig"))["openai"]
    assert config["model"] == plan["model"] and config["base_url"].rstrip("/") + "/chat/completions" == plan["endpoint"]
    key_path = Path(config["api_key_file"])
    assert key_path.is_absolute() and not key_path.is_relative_to(base.ROOT)
    key = key_path.read_text(encoding="utf-8").strip()
    assert key
    record = {**plan, "status": "started", "started_at": datetime.now(timezone.utc).isoformat(), "reservation_kept": True}
    with LEDGER.open("x", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
        f.write("\n")
    start = time.monotonic()
    try:
        req = urllib.request.Request(plan["endpoint"], data=wire, headers={"Content-Type": "application/json", "Authorization": "Bearer " + key}, method="POST")
        opener = urllib.request.build_opener(base.NoRedirect)
        try:
            with opener.open(req, timeout=480) as response:
                record["http_status"] = response.status
                output = read_final_sse(response)
                final = re.sub(r"\bsk-[A-Za-z0-9_-]{12,}", "[REDACTED]", output.pop("final").replace(key, "[REDACTED]"))
                record.update(output, final_characters=len(final))
                if final:
                    FINAL.write_text(final, encoding="utf-8")
                    record["final_sha256"] = hashlib.sha256(final.encode()).hexdigest()
                complete = output["done_received"] and output["finish_reason"] == "stop" and output["models_returned"] == [plan["model"]] and bool(final.strip())
                record["status"] = "final_received_requires_semantic_review" if complete else "no_complete_matching_final"
                used = output["usage"].get("total_tokens")
                if output["done_received"] and type(used) is int and used >= 0:
                    record.update(reservation_kept=False, conservative_accounted_this_attempt=used)
        except urllib.error.HTTPError as error:
            record.update(http_status=error.code, status="http_error_no_auto_retry")
    except Exception as error:
        record.update(status="stream_error_no_auto_retry", error_type=type(error).__name__)
    record.setdefault("conservative_accounted_this_attempt", reserve)
    record["conservative_total_including_connection"] = prior + record["conservative_accounted_this_attempt"]
    record["elapsed_seconds"] = round(time.monotonic() - start, 3)
    base.dump(LEDGER, record)
    print(json.dumps(record, ensure_ascii=False))


if __name__ == "__main__":
    main()
