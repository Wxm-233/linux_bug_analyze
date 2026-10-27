#!/usr/bin/env python3
"""Bounded Claude development continuation; proposals are not detector verdicts.

Use --dry-run before --run. Dry runs neither resolve credentials nor import the
API client. A started ledger entry is never automatically called again.
The root agent must complete the independent offline audit/replay before --run.
Changed material, model and protocol make this a development continuation,
not a fair GPT-versus-Claude comparison. The prior stopped ledger is read only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
SETTINGS = PROJECT / "analysis_out/claude-main/settings.toml"
LEDGER = HERE / "model_ledger.json"
LOCK = HERE / ".model_runner.lock"
SCOPES = {"local_candidate", "cross_arch_candidate", "insufficient"}
AUTHORITY = {"existing_requirement", "policy_proposal", "insufficient"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def decode_json(text: str) -> Any:
    return json.loads(text, object_pairs_hook=unique_object)


def encoded(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def redact(value: Any, key: str) -> Any:
    if isinstance(value, str):
        return value.replace(key, "[REDACTED]") if key else value
    if isinstance(value, list):
        return [redact(item, key) for item in value]
    if isinstance(value, dict):
        return {redact(name, key): redact(item, key) for name, item in value.items()}
    return value


def atomic_json(path: Path, value: Any, key: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    data = encoded(redact(value, key))
    with temporary.open("wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def local_path(relative: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError("Manifest paths must be relative")
    path = (HERE / relative).resolve()
    if not path.is_relative_to(HERE):
        raise ValueError("Manifest path leaves the experiment directory")
    return path


def positive_integer(value: Any, name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def document_lines(document: dict[str, Any]) -> dict[int, str]:
    first = positive_integer(document.get("start_line"), "start_line")
    last = positive_integer(document.get("end_line"), "end_line")
    if last < first or not isinstance(document.get("text"), str):
        raise ValueError("Invalid document range/text")
    lines: dict[int, str] = {}
    for line in document["text"].splitlines():
        match = re.fullmatch(r"\s*(\d+): ?(.*)", line)
        if not match:
            raise ValueError("Document text requires 'original_line: text' numbering")
        number = int(match[1])
        if number in lines:
            raise ValueError("Duplicate original line number")
        lines[number] = match[2]
    if list(lines) != list(range(first, last + 1)):
        raise ValueError("Document line numbers must match the complete declared range")
    for field in ("id", "kind", "path"):
        if not isinstance(document.get(field), str) or not document[field]:
            raise ValueError(f"Document {field} missing")
    return lines


def load_carryover(manifest: dict[str, Any], limits: dict[str, int]) -> dict[str, Any]:
    """Read only the explicitly allowed prior ledger, never its other files."""
    carryover = manifest.get("carryover")
    if not isinstance(carryover, dict):
        raise ValueError("Continuation requires explicit prior-ledger budget carryover")
    relative = "../arch_witness_checks_20261014/model_ledger.json"
    if carryover.get("ledger") != relative:
        raise ValueError("Unexpected carryover ledger; only the frozen prior round is permitted")
    prior_path = (HERE / relative).resolve()
    expected_path = (HERE.parent / "arch_witness_checks_20261014/model_ledger.json").resolve()
    if prior_path != expected_path or not prior_path.is_relative_to(PROJECT):
        raise ValueError("Carryover ledger resolved outside its exact allowed path")
    raw = prior_path.read_bytes()
    expected_sha = carryover.get("sha256")
    if not isinstance(expected_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha) or digest(raw) != expected_sha:
        raise ValueError("Prior ledger SHA mismatch")
    prior = decode_json(raw.decode("utf-8-sig"))
    if not isinstance(prior, dict) or not isinstance(prior.get("stop_reason"), str) or not prior["stop_reason"]:
        raise ValueError("Prior ledger must retain its existing stop reason")
    entries = prior.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Prior ledger has no accounted request entries")
    accounted = 0
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("status") not in {"started", "finished"}:
            raise ValueError("Invalid prior ledger entry state")
        charge = entry.get("charged_tokens")
        if type(charge) is not int or charge < 0:
            raise ValueError("Invalid prior ledger charge")
        if entry["status"] == "started" or entry.get("usage_known") is False:
            if charge != entry.get("reserved_tokens"):
                raise ValueError("Unknown prior usage must retain its complete reservation charge")
        accounted += charge
    if type(carryover.get("accounted_tokens")) is not int or carryover["accounted_tokens"] != 52358 or accounted != 52358:
        raise ValueError("Prior accounted usage must equal the frozen 52358 tokens")
    if type(carryover.get("overall_budget_tokens")) is not int or carryover["overall_budget_tokens"] != 80000:
        raise ValueError("The original overall 80000-token budget must remain unchanged")
    if accounted + limits["max_total_tokens"] > carryover["overall_budget_tokens"]:
        raise ValueError("Continuation plus prior charges exceeds the original overall budget")
    return {"ledger": relative, "sha256": expected_sha, "accounted_tokens": accounted,
            "overall_budget_tokens": 80000, "prior_stop_reason": prior["stop_reason"]}


def prepare() -> dict[str, Any]:
    raw_manifest = (HERE / "manifest.json").read_bytes()
    manifest = decode_json(raw_manifest.decode("utf-8-sig"))
    limits = {name: positive_integer(manifest.get(name), name) for name in (
        "max_requests", "max_total_tokens", "max_output_tokens", "hidden_input_reserve_tokens"
    )}
    if limits["max_requests"] > 2 or limits["max_total_tokens"] > 27642 or limits["max_output_tokens"] > 2000:
        raise ValueError("Manifest exceeds continuation's 2 call / 27642 token / 2000 output limits")
    if limits["hidden_input_reserve_tokens"] < 8192:
        raise ValueError("Hidden input reserve must be at least 8192")
    carryover = load_carryover(manifest, limits)
    protocol = (HERE / "protocol_pre.md").read_bytes()
    prompt_bytes = (HERE / "system_prompt.txt").read_bytes()
    prompt = prompt_bytes.decode("utf-8-sig")
    if not protocol.strip() or not prompt.strip():
        raise ValueError("Protocol and system prompt must be prepared before calls")
    settings_bytes = SETTINGS.read_bytes()
    settings = tomllib.loads(settings_bytes.decode("utf-8-sig"))
    api = settings["openai"]
    if api.get("model") != "AWS-Claude-Sonnet-5":
        raise ValueError("Expected the separate AWS-Claude-Sonnet-5 configuration")
    if "reasoning_effort" in api or "thinking" in api:
        raise ValueError("Claude configuration must omit reasoning_effort and thinking")
    if api.get("base_url", "").rstrip("/") != "https://llmapi.isrc.ac.cn/v1":
        raise ValueError("Unexpected API endpoint")
    if "api_key" in api or "api_key" in settings:
        raise ValueError("Inline credentials are not allowed")
    key_path = Path(api["api_key_file"])
    if not key_path.is_absolute() or key_path.resolve().is_relative_to(PROJECT):
        raise ValueError("Credential must be an absolute path outside the repository")
    rows = manifest.get("requests")
    if not isinstance(rows, list) or not rows or len(rows) > limits["max_requests"]:
        raise ValueError("Invalid request count")
    requests: list[dict[str, Any]] = []
    ids: set[str] = set()
    for row in rows:
        identity = row.get("id")
        if not isinstance(identity, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", identity) or identity in ids:
            raise ValueError("Request IDs must be unique safe filenames")
        if identity not in {"startup_target_pair", "startup_target_ablated"}:
            raise ValueError("Only the two frozen startup development views are permitted")
        ids.add(identity)
        raw = local_path(row["relative_path"]).read_bytes()
        if digest(raw) != row["sha256"]:
            raise ValueError(f"Request fingerprint mismatch: {identity}")
        request = decode_json(raw.decode("utf-8-sig"))
        if request.get("id") != identity:
            raise ValueError("Request ID differs from manifest")
        for field in ("unit", "view", "revision"):
            if not isinstance(request.get(field), str) or not request[field]:
                raise ValueError(f"Request {field} missing")
        documents = request.get("documents")
        if not isinstance(documents, list) or not documents:
            raise ValueError("Requests need source documents")
        documents_by_id: dict[str, dict[str, Any]] = {}
        for doc in documents:
            lines = document_lines(doc)
            if doc["id"] in documents_by_id:
                raise ValueError("Duplicate document ID")
            documents_by_id[doc["id"]] = {"document": doc, "lines": lines}
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(request, ensure_ascii=False, separators=(",", ":"))},
        ]
        message_bytes = sum(len(message["content"].encode("utf-8")) for message in messages)
        reserve = message_bytes + limits["hidden_input_reserve_tokens"] + limits["max_output_tokens"] + 512
        requests.append({"id": identity, "sha256": row["sha256"], "messages": messages,
                         "documents": documents_by_id, "reserve": reserve, "message_bytes": message_bytes,
                         "unit": request["unit"], "view": request["view"], "revision": request["revision"]})
    fingerprint_inputs = {
        "manifest_sha256": digest(raw_manifest), "protocol_sha256": digest(protocol),
        "runner_sha256": digest(Path(__file__).read_bytes()),
        "system_prompt_sha256": digest(prompt_bytes), "settings_sha256": digest(settings_bytes),
        "parameters": {"model": api["model"], "base_url": api["base_url"], "temperature": 0.2,
                       "max_tokens": limits["max_output_tokens"], "stream": False,
                       "timeout_seconds": 180, "max_retries": 0, "format_retries": 0},
        "carryover": carryover, "limits": limits, "requests": [{"id": req["id"], "sha256": req["sha256"]} for req in requests],
    }
    return {"limits": limits, "carryover": carryover, "requests": requests, "api": api, "key_path": key_path,
            "fingerprint_inputs": fingerprint_inputs, "fingerprint": digest(encoded(fingerprint_inputs))}


def load_ledger(prepared: dict[str, Any]) -> dict[str, Any]:
    if not LEDGER.exists():
        return {"schema_version": 1, "created_at": now(), "fingerprint": prepared["fingerprint"],
                "fingerprint_inputs": prepared["fingerprint_inputs"], "entries": [], "stop_reason": None}
    ledger = decode_json(LEDGER.read_text(encoding="utf-8-sig"))
    if ledger.get("fingerprint") != prepared["fingerprint"]:
        raise ValueError("Experiment/configuration fingerprint changed; refusing to resume")
    if ledger.get("fingerprint_inputs") != prepared["fingerprint_inputs"]:
        raise ValueError("Ledger fingerprint inputs changed")
    request_map = {req["id"]: req for req in prepared["requests"]}
    seen: set[str] = set()
    entries = ledger.get("entries")
    if not isinstance(entries, list) or len(entries) > prepared["limits"]["max_requests"]:
        raise ValueError("Invalid ledger entries/count")
    if [entry.get("id") for entry in entries] != [req["id"] for req in prepared["requests"][:len(entries)]]:
        raise ValueError("Ledger request sequence changed")
    for entry in entries:
        identity = entry.get("id")
        if identity in seen or identity not in request_map or entry.get("request_sha256") != request_map[identity]["sha256"]:
            raise ValueError("Invalid ledger request binding")
        if entry.get("status") not in ("started", "finished"):
            raise ValueError("Unknown ledger status")
        if type(entry.get("charged_tokens")) is not int or entry["charged_tokens"] < 0:
            raise ValueError("Invalid ledger token charge")
        if entry.get("reserved_tokens") != request_map[identity]["reserve"]:
            raise ValueError("Ledger reservation changed")
        if entry["status"] == "started" and entry["charged_tokens"] != entry["reserved_tokens"]:
            raise ValueError("Interrupted calls must retain the full reservation charge")
        if entry["status"] == "finished":
            for field in ("response", "proposal", "failure"):
                artifact = entry.get(field)
                if artifact:
                    if digest(local_path(artifact["path"]).read_bytes()) != artifact["sha256"]:
                        raise ValueError(f"Completed artifact changed: {identity}/{field}")
            raw = decode_json(local_path(entry["response"]["path"]).read_text(encoding="utf-8")) if entry.get("response") else None
            actual_usage = raw.get("usage") if isinstance(raw, dict) else None
            total = actual_usage.get("total_tokens") if isinstance(actual_usage, dict) else None
            usage_known = type(total) is int and total >= 0
            expected_charge = total if usage_known else entry["reserved_tokens"]
            if entry.get("usage") != actual_usage or entry.get("usage_known") is not usage_known or entry["charged_tokens"] != expected_charge:
                raise ValueError("Ledger usage/charge differs from preserved response")
            if isinstance(raw, dict) and entry.get("response_model") != raw.get("model"):
                raise ValueError("Ledger response model differs from preserved response")
            requires_stop = not usage_known or expected_charge > entry["reserved_tokens"] or (
                isinstance(raw, dict) and raw.get("model") != prepared["api"]["model"]
            )
            if requires_stop and not ledger.get("stop_reason"):
                raise ValueError("Mandatory stop reason was removed from ledger")
        seen.add(identity)
    if charged(ledger) > prepared["limits"]["max_total_tokens"] and not ledger.get("stop_reason"):
        raise ValueError("Over-budget ledger lacks stop reason")
    return ledger


def parse_proposal(content: str, documents: dict[str, dict[str, Any]]) -> dict[str, Any]:
    body = content.strip()
    fence = re.fullmatch(r"```(?:json)?\s*\n([\s\S]*?)\n```", body)
    if fence:
        body = fence[1]
    proposal = decode_json(body)
    if not isinstance(proposal, dict) or proposal.get("scope") not in SCOPES:
        raise ValueError("Invalid proposal scope")
    if not isinstance(proposal.get("findings"), list) or not isinstance(proposal.get("unknown"), list):
        raise ValueError("Proposal findings/unknown must be lists")
    if len(proposal["findings"]) > 3:
        raise ValueError("Proposal permits at most 3 findings")
    if not all(isinstance(item, str) for item in proposal["unknown"]):
        raise ValueError("Proposal unknown must contain strings")
    for finding in proposal["findings"]:
        if not isinstance(finding, dict):
            raise ValueError("Finding must be an object")
        for field in ("title", "contract", "architecture_difference", "propagation", "exposure_difference", "check_candidate"):
            if not isinstance(finding.get(field), str) or not finding[field].strip():
                raise ValueError(f"Finding {field} must be a nonempty string")
        if finding.get("authority_status") not in AUTHORITY:
            raise ValueError("Invalid authority status")
        if not isinstance(finding.get("unknown"), list) or not all(isinstance(item, str) for item in finding["unknown"]):
            raise ValueError("Finding unknown must be a list of strings")
        references = finding.get("evidence")
        if not isinstance(references, list) or not 1 <= len(references) <= 8:
            raise ValueError("Each finding requires 1 to 8 evidence references")
        extracted = []
        for reference in references:
            if not isinstance(reference, dict) or reference.get("document") not in documents:
                raise ValueError("Unknown evidence document")
            start = positive_integer(reference.get("start_line"), "evidence start_line")
            end = positive_integer(reference.get("end_line"), "evidence end_line")
            doc = documents[reference["document"]]
            if end < start or start < doc["document"]["start_line"] or end > doc["document"]["end_line"]:
                raise ValueError("Evidence range outside supplied source")
            extracted.append({"document": reference["document"], "path": doc["document"]["path"],
                              "start_line": start, "end_line": end,
                              "source_text": "\n".join(f"{number}: {doc['lines'][number]}" for number in range(start, end + 1))})
        finding["program_extracted_evidence"] = extracted
    return proposal


def artifact(path: Path, value: Any, key: str) -> dict[str, str]:
    atomic_json(path, value, key)
    return {"path": path.relative_to(HERE).as_posix(), "sha256": digest(path.read_bytes())}


def charged(ledger: dict[str, Any]) -> int:
    return sum(entry["charged_tokens"] for entry in ledger["entries"])


def dry_run(prepared: dict[str, Any], ledger: dict[str, Any]) -> None:
    used = charged(ledger)
    seen = {entry["id"] for entry in ledger["entries"]}
    count = len(seen)
    rows = []
    planned_stop = False
    for req in prepared["requests"]:
        if req["id"] in seen:
            state = "already_started_never_repeat"
        elif ledger.get("stop_reason"):
            state = "stopped_ledger"
        elif planned_stop:
            state = "planned_stop_after_budget_block"
        elif count >= prepared["limits"]["max_requests"] or used + req["reserve"] > prepared["limits"]["max_total_tokens"]:
            state = "budget_blocked"
            planned_stop = True
        else:
            state = "budget_feasible_under_reservation_only"
            used += req["reserve"]
            count += 1
        rows.append({"id": req["id"], "reserved_tokens": req["reserve"], "message_bytes": req["message_bytes"], "state": state})
    print(json.dumps({"dry_run": True, "credential_read": False, "api_calls": 0,
                      "planning_mode": "full_reservation_no_usage_release", "all_requests_guaranteed": False,
                      "fingerprint": prepared["fingerprint"], "charged_tokens": charged(ledger),
                      "planning_charge": used, "carryover_accounted_tokens": prepared["carryover"]["accounted_tokens"],
                      "overall_charged_tokens": prepared["carryover"]["accounted_tokens"] + charged(ledger),
                      "overall_planning_charge": prepared["carryover"]["accounted_tokens"] + used, "requests": rows}, ensure_ascii=False))


def run(prepared: dict[str, Any], ledger: dict[str, Any]) -> None:
    if ledger.get("stop_reason"):
        print(json.dumps({"status": "stopped", "reason": ledger["stop_reason"]}))
        return
    seen = {entry["id"] for entry in ledger["entries"]}
    key = ""
    client = None
    try:
        for req in prepared["requests"]:
            if req["id"] in seen:
                continue
            if len(ledger["entries"]) >= prepared["limits"]["max_requests"] or charged(ledger) + req["reserve"] > prepared["limits"]["max_total_tokens"]:
                ledger["stop_reason"] = "budget_reservation_blocked"
                atomic_json(LEDGER, ledger, key)
                print(json.dumps({"status": "stopped", "reason": ledger["stop_reason"], "id": req["id"]}))
                break
            if client is None:
                # Deliberately read only the configured external key file;
                # never resolve environment credentials or repository defaults.
                key = prepared["key_path"].read_text(encoding="utf-8").strip()
                if not key:
                    raise ValueError("External credential file is empty")
                sys.path.insert(0, str(PROJECT))
                from linux_bug_analyze.llm import create_openai_client
                client = create_openai_client(key, prepared["api"]["base_url"]).with_options(timeout=180, max_retries=0)
            entry = {"id": req["id"], "request_sha256": req["sha256"], "status": "started",
                     "unit": req["unit"], "view": req["view"], "revision": req["revision"],
                     "started_at": now(), "reserved_tokens": req["reserve"], "charged_tokens": req["reserve"],
                     "usage_known": False, "usage": None, "outcome": "started_unknown"}
            ledger["entries"].append(entry)
            atomic_json(LEDGER, ledger, key)  # Durable receipt BEFORE sending.
            started = time.monotonic()
            response = None
            failures = []
            try:
                response = client.chat.completions.create(
                    model=prepared["api"]["model"], messages=req["messages"], temperature=0.2,
                    max_tokens=prepared["limits"]["max_output_tokens"], stream=False,
                )
            except Exception as exc:
                failures.append({"kind": "transport", "type": type(exc).__name__, "message": str(exc)})
            entry["elapsed_seconds"] = round(time.monotonic() - started, 3)
            entry["finished_at"] = now()
            if response is not None:
                raw = response.model_dump(mode="json")
                entry["response"] = artifact(HERE / "responses" / f"{req['id']}.json", raw, key)
                usage = raw.get("usage")
                entry["usage"] = redact(usage, key)
                total = usage.get("total_tokens") if isinstance(usage, dict) else None
                if type(total) is int and total >= 0:
                    entry["usage_known"] = True
                    entry["charged_tokens"] = total
                entry["response_model"] = raw.get("model")
                choices = raw.get("choices") or []
                entry["finish_reason"] = choices[0].get("finish_reason") if len(choices) == 1 else None
                if raw.get("model") != prepared["api"]["model"]:
                    failures.append({"kind": "response_model", "message": "Response model does not match configured model"})
                if len(choices) != 1 or entry["finish_reason"] != "stop":
                    failures.append({"kind": "completion", "message": "Expected exactly one choice with finish_reason=stop"})
                if not failures:
                    try:
                        content = choices[0].get("message", {}).get("content")
                        if not isinstance(content, str):
                            raise ValueError("Response content is not text")
                        proposal = parse_proposal(content, req["documents"])
                        entry["proposal"] = artifact(HERE / "proposals" / f"{req['id']}.json", proposal, key)
                    except Exception as exc:
                        failures.append({"kind": "format_or_evidence", "type": type(exc).__name__, "message": str(exc)})
            if failures:
                entry["failure"] = artifact(HERE / "failures" / f"{req['id']}.json", failures, key)
            entry["status"] = "finished"
            entry["outcome"] = "failed" if failures else "proposal_recorded_not_quality_verified"
            if not entry["usage_known"]:
                ledger["stop_reason"] = "usage_unknown_no_further_calls"
            elif entry.get("response_model") != prepared["api"]["model"]:
                ledger["stop_reason"] = "response_model_mismatch"
            elif entry["charged_tokens"] > entry["reserved_tokens"]:
                ledger["stop_reason"] = "reported_usage_exceeded_reservation"
            elif charged(ledger) > prepared["limits"]["max_total_tokens"]:
                ledger["stop_reason"] = "reported_usage_exceeded_total_budget"
            atomic_json(LEDGER, ledger, key)
            print(json.dumps(redact({"id": req["id"], "status": entry["outcome"],
                                     "charged_tokens": entry["charged_tokens"], "usage_known": entry["usage_known"],
                                     "overall_charged_tokens": prepared["carryover"]["accounted_tokens"] + charged(ledger),
                                     "elapsed_seconds": entry["elapsed_seconds"], "stop_reason": ledger["stop_reason"]}, key)), flush=True)
            if ledger["stop_reason"]:
                break
    except Exception as exc:
        # An unexpected post-send processing failure leaves the durable entry
        # started and fully charged. Resume will not duplicate that call.
        error = {"status": "runner_error", "type": type(exc).__name__, "message": str(exc), "time": now()}
        try:
            ledger["stop_reason"] = "runner_processing_error_review_required"
            ledger["runner_error"] = artifact(HERE / "runner_error.json", error, key)
            atomic_json(LEDGER, ledger, key)
        except OSError:
            pass
        print(json.dumps(redact(error, key)), file=sys.stderr)
        raise SystemExit(1) from None
    finally:
        if client is not None:
            client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        prepared = prepare()
        dry_run(prepared, load_ledger(prepared))
        return
    # Refuse concurrent runners and stale locks rather than guessing whether a
    # previous process might still be inside an external request.
    fd = os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(json.dumps({"pid": os.getpid(), "started_at": now()}))
            stream.flush()
            os.fsync(stream.fileno())
        prepared = prepare()
        run(prepared, load_ledger(prepared))
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "preparation_error", "type": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        raise SystemExit(1) from None
