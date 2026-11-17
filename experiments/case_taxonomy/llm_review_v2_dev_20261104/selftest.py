"""Self-test of factcheck2.check (config type, plus one inherited type) on claims with known answers, and a print of
the program facts for a few development items. WSL (git); no model. Output: selftest.log (stdout)."""
from pathlib import Path
import json
import factcheck2 as F2
from facts import facts

HERE = Path(__file__).resolve().parent
CASES = [  # (claim, rev, expected status)
    ({'type': 'config', 'arch': 'loongarch', 'symbol': 'ARCH_SUPPORTS_RT', 'selected': True}, 'v6.13', 'ok'),
    ({'type': 'config', 'arch': 'loongarch', 'symbol': 'ARCH_SUPPORTS_RT', 'selected': True}, 'v6.12', 'mismatch'),
    ({'type': 'config', 'arch': 'loongarch', 'symbol': 'ARCH_SUPPORTS_RT', 'selected': False}, 'v6.1', 'ok'),
    ({'type': 'config', 'arch': 'x86', 'symbol': 'HAVE_NOINSTR_VALIDATION', 'selected': True}, 'v6.6', 'ok'),
    ({'type': 'config', 'arch': 'loongarch', 'symbol': 'HAVE_NOINSTR_VALIDATION', 'selected': True}, 'v6.6', 'mismatch'),
    ({'type': 'config', 'arch': 'loongarch', 'symbol': 'rt', 'selected': True}, 'v6.6', 'unverifiable'),
    ({'type': 'calls', 'file': 'arch/loongarch/kernel/setup.c', 'function': 'setup_arch', 'callee': 'parse_early_param',
      'present': True}, 'v6.1', 'ok'),
]


def main():
    bad = 0
    for claim, rev, want in CASES:
        got = F2.check(claim, rev)
        bad += got[0] != want
        print('OK ' if got[0] == want else 'BAD', rev, json.dumps(claim, ensure_ascii=False), '->', got)
    print('selftest failures:', bad)
    rows = {r['cand']: r for r in json.loads((HERE / 'labels3.json').read_text(encoding='utf-8'))['rows']}
    for k in (3, 8, 27, 28, 45, 46, 49, 51):
        print(f'--- {k} {rows[k]["snapshot"]} {rows[k]["rule"]} {rows[k]["name"]} [{rows[k]["label3"]}]')
        for f in facts(rows[k], 'loongarch'):
            print(' ', f['id'], f['text'])


if __name__ == '__main__':
    main()
