#!/usr/bin/env python3
"""Three deliberately separate Claude stages; final Markdown only, no JSON grader.

--dry-run never reads credentials/imports an API client. --run-next sends at most
one request. Finished/started stages are never automatically repeated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
SETTINGS = PROJECT / "analysis_out/claude-main-expanded/settings.toml"
LEDGER, LOCK = HERE / "model_ledger.json", HERE / ".deep_review.lock"
STAGES = ("analysis", "critique", "synthesis")
MAX_OUTPUT, TIMEOUT, OVERALL, NEW_BUDGET = 24576, 600, 1000000, 866297
HIDDEN_RESERVE, ENVELOPE_RESERVE = 8192, 512
PRIOR = (
    ("../arch_witness_checks_20261014/model_ledger.json", 52358, "usage_unknown_no_further_calls"),
    ("../arch_witness_claude_20261014/model_ledger.json", 10956, "budget_reservation_blocked"),
    ("../arch_witness_claude_20261014/expanded_output/model_ledger.json", 29333, None),
    ("../arch_witness_claude_20261014/compact_final/model_ledger.json", 18305, None),
    ("../state_predicate_extract_20261015/model_ledger.json", 22751, None),
)


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key: " + key)
        result[key] = value
    return result


def decode(raw):
    return json.loads(raw, object_pairs_hook=unique)


def redact(value, key):
    if isinstance(value, str):
        return value.replace(key, "[REDACTED]") if key else value
    if isinstance(value, list):
        return [redact(item, key) for item in value]
    if isinstance(value, dict):
        return {redact(name, key): redact(item, key) for name, item in value.items()}
    return value


def atomic_bytes(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def atomic_json(path, value, key=""):
    atomic_bytes(path, encoded(redact(value, key)))


def artifact(path, value, key="", markdown=False):
    data = redact(value, key).encode("utf-8") if markdown else encoded(redact(value, key))
    atomic_bytes(path, data)
    return {"path": path.relative_to(HERE).as_posix(), "sha256": digest(data)}


def local(relative):
    path = (HERE / relative).resolve()
    if not path.is_relative_to(HERE):
        raise ValueError("Stage artifact leaves experiment directory")
    return path


def charge_from_usage(usage, reserve):
    total = usage.get("total_tokens") if isinstance(usage, dict) else None
    known = type(total) is int and total >= 0
    return known, total if known else reserve


def prior_accounting():
    rows, total, unknown = [], 0, 0
    for relative, expected, stop in PRIOR:
        path = (HERE / relative).resolve()
        if not path.is_relative_to(PROJECT):
            raise ValueError("Prior ledger outside project")
        raw = path.read_bytes()
        ledger = decode(raw.decode("utf-8-sig"))
        if ledger.get("stop_reason") != stop or "stop_reason" not in ledger:
            raise ValueError("Prior stop state changed: " + relative)
        entries = ledger.get("entries")
        if not isinstance(entries, list) or not entries:
            raise ValueError("Prior entries missing")
        charged = 0
        for entry in entries:
            if entry.get("status") not in ("started", "finished") or type(entry.get("usage_known")) is not bool:
                raise ValueError("Invalid prior state")
            known, amount = charge_from_usage(entry.get("usage"), entry.get("reserved_tokens"))
            if entry["status"] == "started":
                known, amount = False, entry.get("reserved_tokens")
            if type(amount) is not int or amount < 0 or entry["charged_tokens"] != amount \
                    or (entry["status"] == "finished" and entry["usage_known"] is not known):
                raise ValueError("Prior charge is inconsistent")
            charged += amount
            if not known:
                unknown += amount
        if charged != expected:
            raise ValueError("Prior charge changed: " + relative)
        if stop is None:
            planned = ledger.get("fingerprint_inputs", {}).get("requests", [])
            if len(entries) != 2 or [entry["id"] for entry in entries] != [row["id"] for row in planned] \
                    or any(entry["status"] != "finished" for entry in entries):
                raise ValueError("Prior round not exhausted")
        total += charged
        rows.append({"path": relative, "sha256": digest(raw), "charged_tokens": charged, "stop_reason": stop})
    if total != 133703 or unknown != 28202 or total + NEW_BUDGET != OVERALL:
        raise ValueError("Prior cumulative accounting changed")
    return {"ledgers": rows, "charged_tokens": total, "unknown_usage_reserved_tokens": unknown}


def prepare():
    prior = prior_accounting()
    paths = [Path(__file__), HERE / "test_deep_review_runner.py", HERE / "source_packet.json"] \
        + [HERE / "prompts" / ("stage_" + stage + ".txt") for stage in STAGES]
    file_hashes = {}
    for path in paths:
        raw = path.read_bytes()
        if not raw.strip():
            raise ValueError("Empty required input: " + path.name)
        file_hashes[path.relative_to(HERE).as_posix()] = digest(raw)
    packet = decode((HERE / "source_packet.json").read_text(encoding="utf-8-sig"))
    encoded(packet)  # Reject nonfinite JSON constants; no interpretation of case content.
    prompts = {stage: (HERE / "prompts" / ("stage_" + stage + ".txt")).read_text(encoding="utf-8-sig") for stage in STAGES}
    settings = tomllib.loads(SETTINGS.read_text(encoding="utf-8-sig"))
    api = settings["openai"]
    if "api_key" in api or "api_key" in settings:
        raise ValueError("Inline credentials are forbidden")
    if api.get("model") != "AWS-Claude-Sonnet-5" or api.get("base_url", "").rstrip("/") != "https://llmapi.isrc.ac.cn/v1":
        raise ValueError("Unexpected Claude endpoint/model")
    key_path = Path(api["api_key_file"])
    if not key_path.is_absolute() or key_path.resolve().is_relative_to(PROJECT):
        raise ValueError("Credential path must be absolute and outside repository")
    parameters = {"model": api["model"], "base_url": api["base_url"], "max_tokens": MAX_OUTPUT,
                  "temperature": 0.2, "timeout_seconds": TIMEOUT, "stream": False,
                  "sdk_max_retries": 0, "format_retries": 0, "max_requests": 3,
                  "new_budget": NEW_BUDGET, "overall_budget": OVERALL,
                  "hidden_input_reserve": HIDDEN_RESERVE, "envelope_reserve": ENVELOPE_RESERVE}
    bindings = {"files": file_hashes, "prior": prior, "parameters": parameters,
                "credential_file": str(key_path)}
    return {"packet": packet, "prompts": prompts, "key_path": key_path, "parameters": parameters,
            "bindings": bindings, "fingerprint": digest(encoded(bindings)), "prior": prior}


def load_ledger(prepared):
    if not LEDGER.exists():
        return {"schema_version": 1, "created_at": now(), "fingerprint": prepared["fingerprint"],
                "fingerprint_inputs": prepared["bindings"], "entries": [], "stop_reason": None}
    ledger = decode(LEDGER.read_text(encoding="utf-8-sig"))
    if ledger.get("fingerprint") != prepared["fingerprint"] or ledger.get("fingerprint_inputs") != prepared["bindings"]:
        raise ValueError("Bound inputs changed; do not resume this frozen round")
    entries = ledger.get("entries")
    if not isinstance(entries, list) or len(entries) > 3 or [row.get("stage") for row in entries] != list(STAGES[:len(entries)]):
        raise ValueError("Invalid stage order/count")
    for entry in entries:
        if entry.get("status") not in ("started", "finished"):
            raise ValueError("Invalid entry state")
        for field in ("reserved_tokens", "charged_tokens"):
            if type(entry.get(field)) is not int or entry[field] < 0:
                raise ValueError("Invalid entry charge/reservation")
        if entry["status"] == "started":
            if entry["charged_tokens"] != entry["reserved_tokens"] or entry.get("usage_known") is not False:
                raise ValueError("Interrupted request must retain full unknown reservation")
        else:
            known, amount = charge_from_usage(entry.get("usage"), entry["reserved_tokens"])
            if entry.get("usage_known") is not known or entry["charged_tokens"] != amount:
                raise ValueError("Finished usage charge inconsistent")
        for field in ("request", "response", "final_markdown"):
            item = entry.get(field)
            if item and digest(local(item["path"]).read_bytes()) != item["sha256"]:
                raise ValueError("Stage artifact changed: " + field)
    return ledger


def charged(ledger):
    return sum(entry["charged_tokens"] for entry in ledger["entries"])


def next_request(prepared, ledger):
    if ledger.get("stop_reason"):
        return None, "stopped:" + ledger["stop_reason"]
    entries = ledger["entries"]
    if any(entry["status"] == "started" for entry in entries):
        return None, "started_request_never_repeat"
    if any(entry.get("outcome") != "complete_final_markdown" for entry in entries):
        return None, "incomplete_prior_final_no_automatic_retry"
    if len(entries) == 3:
        return None, "all_three_stages_finished"
    stage = STAGES[len(entries)]
    preceding = {}
    for entry in entries:
        item = entry["final_markdown"]
        preceding[entry["stage"]] = local(item["path"]).read_text(encoding="utf-8")
    body = {"source_packet": prepared["packet"]}
    if preceding:
        body["prior_final_outputs"] = preceding
    messages = [{"role": "system", "content": prepared["prompts"][stage]},
                {"role": "user", "content": json.dumps(body, ensure_ascii=False, separators=(",", ":"), allow_nan=False)}]
    size = sum(len(row["content"].encode("utf-8")) for row in messages)
    reserve = size + MAX_OUTPUT + HIDDEN_RESERVE + ENVELOPE_RESERVE
    if charged(ledger) + reserve > NEW_BUDGET:
        return None, "budget_reservation_blocked"
    return {"stage": stage, "messages": messages, "message_bytes": size, "reserved_tokens": reserve}, "ready"


def final_output(raw, expected_model):
    """Select only final content/metadata; never inspect thinking/reasoning fields."""
    choices = raw.get("choices") or []
    choice = choices[0] if len(choices) == 1 else {}
    message = choice.get("message") or {}
    content = message.get("content")
    complete = len(choices) == 1 and choice.get("finish_reason") == "stop" \
        and raw.get("model") == expected_model and isinstance(content, str) and bool(content.strip())
    return content if isinstance(content, str) else None, choice.get("finish_reason"), complete


def run_next(prepared, ledger):
    request, state = next_request(prepared, ledger)
    if request is None:
        print(json.dumps({"status": state, "api_calls": 0}))
        return
    key, client, entry = "", None, None
    try:
        key = prepared["key_path"].read_text(encoding="utf-8").strip()
        if not key:
            raise ValueError("External credential file is empty")
        sys.path.insert(0, str(PROJECT))
        from linux_bug_analyze.llm import create_openai_client
        p = prepared["parameters"]
        client = create_openai_client(key, p["base_url"]).with_options(timeout=TIMEOUT, max_retries=0)
        entry = {"stage": request["stage"], "status": "started", "started_at": now(),
                 "reserved_tokens": request["reserved_tokens"], "charged_tokens": request["reserved_tokens"],
                 "usage_known": False, "usage": None, "message_bytes": request["message_bytes"],
                 "outcome": "started_unknown"}
        entry["request"] = artifact(HERE / "requests" / (request["stage"] + ".json"),
                                     {"messages": request["messages"], "parameters": p}, key)
        ledger["entries"].append(entry)
        atomic_json(LEDGER, ledger, key)  # Durable full charge BEFORE network request.
        started = time.monotonic()
        response = client.chat.completions.create(model=p["model"], messages=request["messages"],
            temperature=p["temperature"], max_tokens=MAX_OUTPUT, stream=False)
        raw = response.model_dump(mode="json")
        entry["elapsed_seconds"] = round(time.monotonic() - started, 3)
        entry["response"] = artifact(HERE / "responses" / (request["stage"] + ".json"), raw, key)
        entry["response_model"] = raw.get("model")
        entry["usage"] = redact(raw.get("usage"), key)
        entry["usage_known"], entry["charged_tokens"] = charge_from_usage(entry["usage"], entry["reserved_tokens"])
        content, finish, complete = final_output(raw, p["model"])
        entry["finish_reason"] = finish
        if content is not None:
            suffix = ".md" if complete else ".incomplete.md"
            entry["final_markdown"] = artifact(HERE / "final" / (request["stage"] + suffix), content, key, markdown=True)
        entry.update(status="finished", finished_at=now(), outcome="complete_final_markdown" if complete else "incomplete_final")
        if not entry["usage_known"]:
            ledger["stop_reason"] = "usage_unknown_no_further_calls"
        elif raw.get("model") != p["model"]:
            ledger["stop_reason"] = "response_model_mismatch"
        elif entry["charged_tokens"] > entry["reserved_tokens"] or charged(ledger) > NEW_BUDGET:
            ledger["stop_reason"] = "reported_usage_exceeded_reservation_or_budget"
        elif not complete:
            ledger["stop_reason"] = "incomplete_final_no_automatic_retry"
        atomic_json(LEDGER, ledger, key)
        print(json.dumps({"stage": request["stage"], "outcome": entry["outcome"], "finish_reason": finish,
            "usage_known": entry["usage_known"], "charged_tokens": entry["charged_tokens"],
            "overall_charged_tokens": 133703 + charged(ledger), "elapsed_seconds": entry["elapsed_seconds"],
            "stop_reason": ledger["stop_reason"]}), flush=True)
    except Exception as exc:
        error = redact({"type": type(exc).__name__, "message": str(exc)}, key)
        if entry is not None:
            entry["elapsed_seconds"] = round(time.monotonic() - started, 3) if "started" in locals() else 0
            if entry["status"] == "started":
                if entry.get("usage") is not None:
                    entry["observed_usage_before_processing_failure"] = entry["usage"]
                entry.update(charged_tokens=entry["reserved_tokens"], usage_known=False, usage=None)
            entry["error"] = error
            ledger["stop_reason"] = "unknown_or_processing_failure_review_required"
            atomic_json(LEDGER, ledger, key)
        print(json.dumps({"status": "runner_error", **error}), file=sys.stderr)
        raise SystemExit(1) from None
    finally:
        if client is not None:
            client.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--run-next", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        prepared = prepare()
        ledger = load_ledger(prepared)
        request, state = next_request(prepared, ledger)
        print(json.dumps({"dry_run": True, "credential_read": False, "api_calls": 0,
            "state": state, "next_stage": request["stage"] if request else None,
            "reserved_tokens": request["reserved_tokens"] if request else None,
            "carryover_charged_tokens": 133703, "prior_unknown_usage_reserved_tokens": 28202,
            "stage_charged_tokens": charged(ledger), "overall_cap": OVERALL,
            "stage_cap": NEW_BUDGET, "max_output_tokens": MAX_OUTPUT,
            "future_stage_reservations": "recomputed after final Markdown is reviewed; not guaranteed",
            "fingerprint": prepared["fingerprint"]}), flush=True)
        return
    fd = os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(json.dumps({"pid": os.getpid(), "started_at": now()}))
            stream.flush()
            os.fsync(stream.fileno())
        prepared = prepare()
        run_next(prepared, load_ledger(prepared))
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "preparation_error", "type": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        raise SystemExit(1) from None
