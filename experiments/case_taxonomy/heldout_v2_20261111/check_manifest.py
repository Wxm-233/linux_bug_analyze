"""Check the frozen method files against method_manifest.json (criteria 二).  python check_manifest.py"""
import hashlib, json, sys
from pathlib import Path
CT = Path(__file__).resolve().parent.parent
m = json.loads((Path(__file__).resolve().parent / "method_manifest.json").read_text())
bad = [f for f, h in m.items() if hashlib.sha256((CT / f).read_bytes()).hexdigest() != h]
print("manifest", "OK" if not bad else "CHANGED: " + ", ".join(bad), f"({len(m)} files)")
sys.exit(1 if bad else 0)
