"""Boundary items (criteria 4.1): public_to_arch symbols of the current riscv revised pool, by name.
    python boundary_names.py -> boundary_names.json {"macro": [...], "nonmacro": [...]}"""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
POOL = HERE.parents[1] / "boundary_audit_20261107/revised/riscv/599f727262c4c58505ab7bffe6c9d847266bce553a250c175ada47226232805d/symbols_runtime_riscv.json"
syms = json.loads(POOL.read_text())
out = {"source": str(POOL.relative_to(HERE.parents[1])), "macro": set(), "nonmacro": set(), "kind": {}}
for s in syms:
    if s["direction"] != "public_to_arch":
        continue
    if s["kind"] in ("macro", "function", "object", "enum_constant"):
        out["kind"].setdefault(s["name"], s["kind"])
    if s["kind"] == "macro":
        out["macro"].add(s["name"])
    elif s["kind"] in ("function", "object", "enum_constant"):
        out["nonmacro"].add(s["name"])
for k in ("macro", "nonmacro"):
    out[k] = sorted(out[k])
(HERE / "boundary_names.json").write_text(json.dumps(out, indent=0))
print({k: len(v) for k, v in out.items() if k != "source"})
from collections import Counter; print(Counter(out["kind"].values()))
for n in ["NR_syscalls", "TASK_SIZE_MAX", "TASK_SIZE", "access_ok", "__access_ok", "arch_get_mmap_end", "put_user", "__put_user", "PAGE_SIZE", "STACK_TOP_MAX"]:
    print(n, n in out["macro"], n in out["nonmacro"])
