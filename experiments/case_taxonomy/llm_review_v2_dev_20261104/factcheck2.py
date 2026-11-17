"""Claim check of criteria.md sections 2-3: the four claim types of llm_review_factcheck_20261103/factcheck.py
(imported, unchanged) plus `config` (whether the architecture's Kconfig selects a symbol at the snapshot), and the
acceptance of a not_issue verdict (at least one refute entry that is a matching claim or a given program fact).
WSL (git)."""
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'llm_review_factcheck_20261103'))
sys.path.insert(0, str(HERE))
import factcheck as F  # noqa: E402
from facts import kconfig_selects  # noqa: E402


def check(claim, rev):
    if isinstance(claim, dict) and claim.get('type') == 'config':
        arch, sym, want = str(claim.get('arch', '')).strip(), str(claim.get('symbol', '')).strip(), F.truth(claim.get('selected'))
        if not re.fullmatch(r'[a-z0-9]+', arch) or not re.fullmatch(r'[A-Z0-9_]+', sym) or want is None:
            return 'unverifiable', '缺少arch、symbol或selected'
        hits = kconfig_selects(rev, arch, sym)
        return ('ok' if bool(hits) == want else 'mismatch',
                f'该版本arch/{arch}的Kconfig中{"有" if hits else "没有"}“select {sym}”')
    return F.check(claim, rev)


def refute_ok(answer, results, fact_ids):
    """(accepted, why) for a not_issue answer: some refute entry is a claim index whose check is ok, or a fact id."""
    refs = answer.get('refute') or []
    if not isinstance(refs, list):
        refs = [refs]
    good = []
    for r in refs:
        if isinstance(r, str) and r.strip().upper() in fact_ids:
            good.append(r.strip().upper())
        elif isinstance(r, int) or (isinstance(r, str) and r.strip().isdigit()):
            k = int(r)
            if 0 <= k < len(results) and results[k]['status'] == 'ok':
                good.append(f'claims[{k}]')
    if good:
        return True, '相符的依据：' + '、'.join(good)
    return False, ('refute为空' if not refs else f'refute中的{refs}都不是核对相符的事实声明或程序事实编号')
