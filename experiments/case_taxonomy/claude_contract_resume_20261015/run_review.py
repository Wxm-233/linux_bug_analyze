#!/usr/bin/env python3
"""Explicit, one-request HTTP continuation. Dry runs never read credentials.

Raw responses are preserved with credentials redacted. Only final content and
transport metadata are interpreted; reasoning fields are never selected.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
SETTINGS = PROJECT / "analysis_out/claude-main-expanded/settings.toml"
LEDGER, LOCK = HERE / "model_ledger.json", HERE / ".review.lock"
MODEL, BASE_URL = "AWS-Claude-Sonnet-5", "https://llmapi.isrc.ac.cn/v1"
OVERALL, CARRY, UNKNOWN, NEW = 1000000, 221927, 98466, 778073
HIDDEN, ENVELOPE = 8192, 512
PRIOR = (
    ("../arch_witness_checks_20261014/model_ledger.json", 52358,
     "0a18453de6ecb5bc0513cc47c601557a53b3d46be1475e4c64f83a4addb25405"),
    ("../arch_witness_claude_20261014/model_ledger.json", 10956,
     "4e95f4a0400f8f8ab6f14fb0ee305084f73b56505feaabe95d5a3b36ed6fe018"),
    ("../arch_witness_claude_20261014/expanded_output/model_ledger.json", 29333,
     "39d8f756abffdd214a84f98f0b4d08502ce1eff76ba4cbcdff3cd7fc0e998efb"),
    ("../arch_witness_claude_20261014/compact_final/model_ledger.json", 18305,
     "b254ace9fe445117e6f6db547580b6c30f4f888920aa5ec6a8c0d1584a5ce092"),
    ("../state_predicate_extract_20261015/model_ledger.json", 22751,
     "cd3c6d9732760c5cf2c91f96e6a308f8270e00160dfaa10b90f742ab0af75b0e"),
    ("../state_context_binding_20261015/model_ledger.json", 70264,
     "d7b3f72e03c0f24407b103eba034cf80188e4edd510659c5ab796fe9895b640a"),
    ("../state_context_binding_20261015/stream_model_ledger.json", 17960,
     "aa12579d1044eb2db3b5e6bb1c3cfb1f96d3976e92cf4e15e52717d80c32cae3"),
)


def now():
    return datetime.now(timezone.utc).isoformat()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def redact(raw, key=""):
    if isinstance(raw, str):
        if key:
            raw = raw.replace(key, "[REDACTED]")
        return re.sub(r"\bsk-[A-Za-z0-9_-]{12,}", "[REDACTED_KEY]", raw)
    if isinstance(raw, bytes):
        if key:
            raw = raw.replace(key.encode("utf-8"), b"[REDACTED]")
        return re.sub(rb"\bsk-[A-Za-z0-9_-]{12,}", b"[REDACTED_KEY]", raw)
    if isinstance(raw, list):
        return [redact(v, key) for v in raw]
    if isinstance(raw, dict):
        return {redact(k, key): redact(v, key) for k, v in raw.items()}
    return raw


def atomic(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("wb") as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def local(relative):
    if not isinstance(relative, str):
        raise ValueError("Artifact path must be text")
    p = (HERE / relative).resolve()
    if not p.is_relative_to(HERE):
        raise ValueError("Artifact path leaves current stage")
    return p


def artifact(relative, raw, key=""):
    raw = redact(raw, key)
    atomic(local(relative), raw)
    return {"path": relative, "sha256": digest(raw)}


def charge(usage, reserve):
    total = usage.get("total_tokens") if isinstance(usage, dict) else None
    known = type(total) is int and total >= 0
    if known:
        parts = [usage.get(k) for k in ("prompt_tokens", "completion_tokens")]
        if all(type(x) is int and x >= 0 for x in parts) and sum(parts) != total:
            known = False
    return known, total if known else reserve


def prior_accounting():
    rows, total, unknown = [], 0, 0
    for rel, expected, sha in PRIOR:
        path = (HERE / rel).resolve()
        if not path.is_relative_to(PROJECT):
            raise ValueError("Prior ledger outside project")
        raw = path.read_bytes()
        if digest(raw) != sha:
            raise ValueError("Prior ledger SHA changed: " + rel)
        entries = json.loads(raw.decode("utf-8-sig")).get("entries")
        if not isinstance(entries, list) or not entries:
            raise ValueError("Prior entries missing")
        subtotal = 0
        for e in entries:
            if e.get("status") not in ("started", "finished"):
                raise ValueError("Prior entry state invalid")
            reserve = e.get("reserved_tokens")
            if type(reserve) is not int or reserve < 0:
                raise ValueError("Prior reserve invalid")
            known, amount = charge(e.get("usage"), reserve)
            if e["status"] == "started":
                known, amount = False, reserve
            if e.get("usage_known") is not known or e.get("charged_tokens") != amount:
                raise ValueError("Prior usage charge inconsistent")
            subtotal += amount
            unknown += 0 if known else amount
        if subtotal != expected:
            raise ValueError("Prior amount changed: " + rel)
        total += subtotal
        rows.append({"path": rel, "sha256": sha, "charged_tokens": subtotal})
    if (total, unknown, total + NEW) != (CARRY, UNKNOWN, OVERALL):
        raise ValueError("Prior aggregate changed")
    return {"ledgers": rows, "charged_tokens": total, "unknown_reserved_tokens": unknown}


def prepare():
    prior = prior_accounting()
    plan = json.loads(local("plan.json").read_text(encoding="utf-8-sig"))
    if plan.get("overall_budget_tokens") != OVERALL:
        raise ValueError("Overall budget must remain one million")
    requests = plan.get("requests")
    if not isinstance(requests, list) or not requests:
        raise ValueError("No predeclared requests")
    paths = [Path(__file__), local("test_run_review.py"), local("plan.json")]
    seen = []
    for r in requests:
        name = r.get("id")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", name) or name in seen:
            raise ValueError("Request ID invalid/duplicate")
        deps = r.get("depends_on_previous_final", [])
        if not isinstance(deps, list) or len(set(deps)) != len(deps) or any(x not in seen for x in deps):
            raise ValueError("Dependency must name an earlier request")
        for key in ("prompt_file", "material_file"):
            p = local(r[key])
            if not p.read_bytes().strip():
                raise ValueError("Empty declared input: " + key)
            paths.append(p)
        if type(r.get("max_tokens")) is not int or not 1 <= r["max_tokens"] <= 131072:
            raise ValueError("Invalid output allowance")
        if type(r.get("stream")) is not bool or type(r.get("timeout_seconds")) is not int \
                or not 1 <= r["timeout_seconds"] <= 1800:
            raise ValueError("Invalid transport parameters")
        seen.append(name)
    # The config is read, but the external credential file is not opened here.
    config = tomllib.loads(SETTINGS.read_text(encoding="utf-8-sig"))
    api = config["openai"]
    if "api_key" in config or "api_key" in api:
        raise ValueError("Inline credentials forbidden")
    if api.get("model") != MODEL or api.get("base_url", "").rstrip("/") != BASE_URL:
        raise ValueError("Unexpected endpoint/model")
    key_path = Path(api["api_key_file"])
    if not key_path.is_absolute() or key_path.resolve().is_relative_to(PROJECT):
        raise ValueError("Credential path must be external and absolute")
    files = {p.relative_to(HERE).as_posix(): digest(p.read_bytes()) for p in paths}
    bindings = {"files": files, "prior": prior, "configuration": {
        "settings_path": str(SETTINGS), "settings_sha256": digest(SETTINGS.read_bytes()),
        "model": MODEL, "base_url": BASE_URL, "credential_file": str(key_path)},
        "budget": {"overall": OVERALL, "carry": CARRY, "new": NEW,
                   "hidden_reserve": HIDDEN, "envelope_reserve": ENVELOPE}}
    return {"plan": plan, "bindings": bindings, "fingerprint": digest(encoded(bindings)), "key_path": key_path}


def load_ledger(prepared):
    if not LEDGER.exists():
        return {"schema_version": 1, "created_at": now(), "fingerprint": prepared["fingerprint"],
                "fingerprint_inputs": prepared["bindings"], "entries": [], "stop_reason": None}
    ledger = json.loads(LEDGER.read_text(encoding="utf-8-sig"))
    if ledger.get("fingerprint") != prepared["fingerprint"] or ledger.get("fingerprint_inputs") != prepared["bindings"]:
        raise ValueError("Bound inputs changed after round began")
    valid = {r["id"] for r in prepared["plan"]["requests"]}
    seen = set()
    for e in ledger["entries"]:
        if e.get("id") not in valid or e["id"] in seen or e.get("status") not in ("started", "finished"):
            raise ValueError("Ledger request state invalid")
        seen.add(e["id"])
        reserve = e.get("reserved_tokens")
        if type(reserve) is not int or reserve < 0:
            raise ValueError("Ledger reserve invalid")
        known, amount = charge(e.get("usage"), reserve)
        if e["status"] == "started":
            known, amount = False, reserve
        if e.get("usage_known") is not known or e.get("charged_tokens") != amount:
            raise ValueError("Ledger usage charge inconsistent")
        for name in ("request", "raw_http_body", "response_headers", "final_text"):
            a = e.get(name)
            if a and digest(local(a["path"]).read_bytes()) != a["sha256"]:
                raise ValueError("Ledger artifact changed: " + name)
    return ledger


def charged(ledger):
    return sum(e["charged_tokens"] for e in ledger["entries"])


def request_for(prepared, ledger, request_id):
    rows = {r["id"]: r for r in prepared["plan"]["requests"]}
    if request_id not in rows:
        return None, "unknown_request_id"
    if ledger.get("stop_reason"):
        return None, "ledger_budget_or_integrity_stop"
    if any(e["id"] == request_id for e in ledger["entries"]):
        return None, "already_started_never_repeat"
    r = rows[request_id]
    messages = [{"role": "system", "content": local(r["prompt_file"]).read_text(encoding="utf-8-sig")},
                {"role": "user", "content": local(r["material_file"]).read_text(encoding="utf-8-sig")}]
    entries = {e["id"]: e for e in ledger["entries"]}
    for dep in r.get("depends_on_previous_final", []):
        e = entries.get(dep)
        if not e or e.get("status") != "finished" or e.get("outcome") != "complete_final" \
                or e.get("response_model") != MODEL or e.get("finish_reason") != "stop" or not e.get("final_text"):
            return None, "dependency_has_no_complete_final:" + dep
        text = local(e["final_text"]["path"]).read_text(encoding="utf-8")
        if not text.strip():
            return None, "dependency_has_empty_final:" + dep
        messages.append({"role": "user", "content": "Previously finalized output (" + dep + "):\n" + text})
    size = sum(len(m["content"].encode("utf-8")) for m in messages)
    reserve = size + r["max_tokens"] + HIDDEN + ENVELOPE
    if CARRY + charged(ledger) + reserve > OVERALL:
        return None, "budget_reservation_blocked"
    return {**r, "messages": messages, "message_bytes": size, "reserved_tokens": reserve}, "ready"


def select_json(raw):
    choices = raw.get("choices") or []
    choice = choices[0] if len(choices) == 1 and isinstance(choices[0], dict) else {}
    message = choice.get("message") or {}
    content = message.get("content")
    return {"content": content if isinstance(content, str) else "", "finish_reason": choice.get("finish_reason"),
            "model": raw.get("model"), "usage": raw.get("usage"), "single_choice": len(choices) == 1,
            "transport_complete": True}


def select_sse(raw):
    # Parse only the final output channel and metadata. Other delta keys are ignored.
    pieces, models, finishes, usage, done, indices = [], set(), [], None, False, set()
    events = re.split(r"\r?\n\r?\n", raw.decode("utf-8-sig"))
    for event in events:
        data = "\n".join(line[5:].lstrip(" ") for line in event.splitlines() if line.startswith("data:"))
        if not data:
            continue
        if data.strip() == "[DONE]":
            done = True
            continue
        row = json.loads(data)
        if isinstance(row.get("model"), str):
            models.add(row["model"])
        if row.get("usage") is not None:
            usage = row["usage"]
        for choice in row.get("choices") or []:
            indices.add(choice.get("index", 0))
            if choice.get("index", 0) != 0:
                continue
            value = (choice.get("delta") or {}).get("content")
            if isinstance(value, str):
                pieces.append(value)
            if choice.get("finish_reason") is not None:
                finishes.append(choice["finish_reason"])
    return {"content": "".join(pieces), "finish_reason": finishes[-1] if len(finishes) == 1 else None,
            "model": next(iter(models)) if len(models) == 1 else None, "usage": usage,
            "single_choice": indices <= {0}, "transport_complete": done}


def outcome(selected, http_status):
    if not 200 <= http_status < 300:
        return "http_error"
    if selected["model"] != MODEL:
        return "incomplete_model_mismatch"
    if not selected["content"].strip():
        return "incomplete_empty_final"
    if selected["finish_reason"] != "stop":
        return "incomplete_finish_reason"
    if not selected["transport_complete"] or not selected["single_choice"]:
        return "incomplete_transport_or_choices"
    return "complete_final"


def safe_headers(headers, key):
    # Preserve response headers except credential-bearing cookies/authentication.
    return {k: redact(v, key) for k, v in headers.items()
            if k.lower() not in {"authorization", "proxy-authorization", "set-cookie", "cookie", "x-api-key"}}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never resend an Authorization header to a redirect destination."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class StdlibResponse:
    def __init__(self, opener, request, timeout):
        self.opener, self.request, self.timeout = opener, request, timeout
        self.response = None

    def __enter__(self):
        try:
            self.response = self.opener.open(self.request, timeout=self.timeout)
        except urllib.error.HTTPError as exc:
            # HTTPError is also a readable response. Preserve its original body.
            self.response = exc
        self.status_code = self.response.getcode()
        self.headers = self.response.headers
        return self

    def iter_bytes(self):
        while True:
            chunk = self.response.read(65536)
            if not chunk:
                break
            yield chunk

    def __exit__(self, *unused):
        if self.response is not None:
            self.response.close()
        return False


class StdlibClient:
    """Minimal injectable client interface; standard library, zero retries."""

    def __init__(self, timeout, follow_redirects=False):
        if follow_redirects:
            raise ValueError("Redirects forbidden")
        self.timeout = timeout
        self.opener = urllib.request.build_opener(NoRedirect())

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        return False

    def stream(self, method, url, json, headers):
        request = urllib.request.Request(url, data=encoded(json), headers=headers, method=method)
        return StdlibResponse(self.opener, request, self.timeout)


def perform(prepared, ledger, request, client_factory=None, key_loader=None):
    """One network attempt, after durable request/precharge. Injectable for offline tests."""
    key = ""
    entry = None
    phase = "credential_read"
    started = time.monotonic()
    try:
        key = (key_loader or (lambda p: p.read_text(encoding="utf-8")))(prepared["key_path"]).strip()
        if not key:
            raise ValueError("External credential file empty")
        phase = "transport_prepare"
        if client_factory is None:
            client_factory = StdlibClient
        payload = {"model": MODEL, "messages": request["messages"], "max_tokens": request["max_tokens"],
                   "temperature": 0.2, "stream": request["stream"]}
        if request["stream"]:
            payload["stream_options"] = {"include_usage": True}
        entry = {"id": request["id"], "status": "started", "started_at": now(), "usage_known": False,
                 "usage": None, "reserved_tokens": request["reserved_tokens"],
                 "charged_tokens": request["reserved_tokens"], "message_bytes": request["message_bytes"],
                 "outcome": "started_unknown"}
        entry["request"] = artifact("requests/" + request["id"] + ".json", encoded(payload), key)
        ledger["entries"].append(entry)
        atomic(LEDGER, encoded(redact(ledger, key)))
        chunks = []
        phase = "transport_request"
        # Standard urllib performs one attempt; redirects are disabled.
        with client_factory(timeout=request["timeout_seconds"], follow_redirects=False) as client:
            with client.stream("POST", BASE_URL + "/chat/completions", json=payload,
                               headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"}) as response:
                entry["http_status"] = response.status_code
                entry["response_headers"] = artifact("responses/" + request["id"] + ".headers.json",
                                                        encoded(safe_headers(response.headers, key)), key)
                try:
                    for chunk in response.iter_bytes():
                        chunks.append(chunk)
                finally:
                    entry["raw_http_body"] = artifact("responses/" + request["id"] + ".body",
                                                       b"".join(chunks), key)
        raw = b"".join(chunks)
        phase = "response_parse"
        selected = select_sse(raw) if request["stream"] else select_json(json.loads(raw))
        entry.update(status="finished", finished_at=now(), response_model=selected["model"],
                     finish_reason=selected["finish_reason"], usage=redact(selected["usage"], key),
                     outcome=outcome(selected, entry["http_status"]), final_characters=len(selected["content"]))
        entry["usage_known"], entry["charged_tokens"] = charge(entry["usage"], entry["reserved_tokens"])
        if selected["content"]:
            entry["final_text"] = artifact("final/" + request["id"] + ".md", selected["content"].encode("utf-8"), key)
        if entry["charged_tokens"] > entry["reserved_tokens"] or CARRY + charged(ledger) > OVERALL:
            ledger["stop_reason"] = "usage_exceeded_reservation_or_budget"
    except Exception as exc:
        # Do not print the exception text: a remote error could echo a credential/body.
        if entry is None:
            return {"id": request["id"], "status": "preflight_error", "phase": phase,
                    "error_type": type(exc).__name__, "api_calls": 0}
        entry["error_type"] = type(exc).__name__
        entry["error_phase"] = phase
        entry["outcome"] = "transport_or_processing_error"
        # A failure stays started, charged at its full unknown reserve. No retry.
        entry.update(status="started", usage=None, usage_known=False, charged_tokens=entry["reserved_tokens"])
    finally:
        if entry is not None:
            entry["elapsed_seconds"] = round(time.monotonic() - started, 3)
            atomic(LEDGER, encoded(redact(ledger, key)))
    return {"id": entry["id"], "status": entry["status"], "outcome": entry["outcome"],
            "model": entry.get("response_model"), "final_characters": entry.get("final_characters", 0),
            "usage_known": entry["usage_known"], "charged_tokens": entry["charged_tokens"],
            "overall_charged_tokens": CARRY + charged(ledger), "elapsed_seconds": entry["elapsed_seconds"],
            "http_status": entry.get("http_status"), "error_type": entry.get("error_type"),
            "phase": entry.get("error_phase")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--run", metavar="ID")
    args = parser.parse_args()
    if args.dry_run:
        p = prepare()
        ledger = load_ledger(p)
        states = []
        for r in p["plan"]["requests"]:
            request, status = request_for(p, ledger, r["id"])
            states.append({"id": r["id"], "state": status,
                           "reserved_tokens": request["reserved_tokens"] if request else None})
        print(json.dumps({"dry_run": True, "credential_read": False, "api_calls": 0,
                          "carryover_charged_tokens": CARRY, "carryover_unknown_reserved_tokens": UNKNOWN,
                          "overall_charged_tokens": CARRY + charged(ledger), "overall_cap": OVERALL,
                          "requests": states}))
        return
    fd = os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps({"pid": os.getpid(), "started_at": now()}))
            f.flush()
            os.fsync(f.fileno())
        p = prepare()
        ledger = load_ledger(p)
        request, status = request_for(p, ledger, args.run)
        print(json.dumps(perform(p, ledger, request) if request else {"id": args.run, "status": status, "api_calls": 0}))
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"status": "runner_error", "error_type": type(exc).__name__}), file=sys.stderr)
        raise SystemExit(1) from None
