"""Run only the frozen R7 rule (rules_la.py, via rules_mips.py for the MIPS constants) for one architecture at one
revision. WSL (git); no model. Usage: python3 r7only.py ARCH REV OUT.json"""
from pathlib import Path
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('rules_mips', HERE.parent / 'llm_review_v2_test_20261104' / 'rules_mips.py')
RM = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RM)
L = RM.L


def main():
    arch, rev, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    L.ARCH, L.SNAP, L.CFG = arch, rev, L.ARCHES[arch]
    L.MR.SNAP = rev
    flags = L.r7()
    out.write_text(json.dumps(flags, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    for f in flags:
        print(f['path'], f['name'], '|', f['reason'])


if __name__ == '__main__':
    main()
