"""Shared helpers for the counterpart pilot (criteria.md): git access, the reference pool, answer parsing and paths."""
from pathlib import Path
import json
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'mech_state_size_checker_20261101'))
sys.path.insert(0, str(ROOT / 'cross_arch_sample_set_20261102'))
import checker as CK  # noqa: E402  (git, functions, END)
from collect import TRAILER  # noqa: E402

OUTER = HERE.parents[3]
CALLS = OUTER / '模型调用测试' / '2026-11-02' / 'counterpart_pilot_20261102'
W_START, W_END = '2025-01-01', '2025-07-01'
REF_ARCHES = ('arch/arm64', 'arch/x86', 'arch/loongarch')


def git(*args):
    return CK.git(*args)


def message(sha, limit=60):
    lines = [l for l in git('log', '-1', '--format=%B', sha).splitlines() if not TRAILER.match(l.strip())]
    return '\n'.join(lines[:limit]).strip()


def parse_answer(d):
    """The last JSON object in final.md, or None."""
    p = Path(d) / 'final.md'
    if not p.exists():
        return None
    text = p.read_text(encoding='utf-8', errors='replace')
    for m in reversed(list(re.finditer(r'\{[^{}]*\}', text, re.S))):
        try:
            return json.loads(m.group(0))
        except ValueError:
            continue
    return None
