"""Program checks for one E1 call: delivery completeness, JSON shape, and citation binding of every
provider/consumer reference to the files and line numbers actually present in the prompt.
Semantic correctness is not judged here (researcher review after the output is saved)."""
from pathlib import Path
import json
import re
import sys

FIELDS = {"interface", "provider", "consumer", "requirement", "conditions", "risk", "confidence"}


def prompt_files(prompt: str) -> dict[str, int]:
    files, current, last = {}, None, 0
    for line in prompt.splitlines():
        m = re.match(r"^=== FILE: (.+) ===$", line)
        if m:
            if current:
                files[current] = last
            current, last = m.group(1), 0
            continue
        n = re.match(r"^\s*(\d+)  ", line)
        if current and n:
            last = int(n.group(1))
    if current:
        files[current] = last
    return files


def extract_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])


def check(call_dir: Path) -> dict:
    receipt = json.loads((call_dir / "receipt.json").read_text(encoding="utf-8"))
    out = {"dir": call_dir.name, "delivery": receipt.get("status"), "finish_reasons": receipt.get("finish_reasons"),
           "elapsed_seconds": receipt.get("elapsed_seconds"), "usage": receipt.get("usage")}
    if receipt.get("status") != "complete_final_received":
        out["result"] = "delivery_insufficient"
        return out
    files = prompt_files((call_dir / "prompt.md").read_text(encoding="utf-8"))
    try:
        obj = extract_json((call_dir / "final.md").read_text(encoding="utf-8"))
    except (ValueError, json.JSONDecodeError) as exc:
        out["result"] = "json_unparsable"
        out["error"] = str(exc)[:200]
        return out
    cands = obj.get("candidates")
    shape_ok = isinstance(obj.get("involves_provider_consumer_interface"), bool) and isinstance(cands, list) and len(cands) <= 5
    rows = []
    for c in cands if isinstance(cands, list) else []:
        refs = []
        for role in ("provider", "consumer"):
            r = c.get(role) if isinstance(c, dict) else None
            ok = isinstance(r, dict) and r.get("file") in files and type(r.get("line")) is int and 1 <= r["line"] <= files[r["file"]]
            refs.append({"role": role, "file": (r or {}).get("file"), "line": (r or {}).get("line"), "bound": ok})
        rows.append({"fields_complete": isinstance(c, dict) and FIELDS <= set(c),
                     "confidence_valid": isinstance(c, dict) and c.get("confidence") in ("low", "medium", "high"), "references": refs})
    out.update(result="checked", shape_ok=shape_ok, involves=obj.get("involves_provider_consumer_interface"),
               candidates=len(rows), references=sum(len(r["references"]) for r in rows),
               references_bound=sum(x["bound"] for r in rows for x in r["references"]),
               fields_complete=sum(r["fields_complete"] for r in rows), rows=rows, prompt_files=len(files))
    return out


if __name__ == "__main__":
    results = [check(Path(p)) for p in sys.argv[1:]]
    print(json.dumps(results, ensure_ascii=False, indent=1))
