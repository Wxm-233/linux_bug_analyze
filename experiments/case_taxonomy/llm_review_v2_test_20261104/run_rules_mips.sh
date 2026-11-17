#!/bin/bash
# criteria_amendment1.md: equivalence self-test (rules_la.py and rules_mips.py on LoongArch v6.12 under
# PYTHONHASHSEED 0 and 1, identical per seed), then rules_mips.py for MIPS on every release snapshot v6.1..v7.2
# under PYTHONHASHSEED=0, 8 at a time; existing outputs are skipped, so it can be rerun. WSL; no model calls.
cd "$(dirname "$0")" || exit 1
printf '%s\n' "la 0" "la 1" "mips 0" "mips 1" | xargs -P 4 -L 1 sh -c '
  out=selftest/seed$1_rules_$0_loongarch_v6.12.json
  test -f $out && exit 0
  if [ $0 = la ]; then f=../llm_review_expand_20261103/rules_la.py; else f=rules_mips.py; fi
  PYTHONHASHSEED=$1 python3 -B $f loongarch v6.12 $out > ${out%.json}.log 2>&1'
python3 - <<'PY' || exit 1
import json
ok = True
old = json.load(open('../llm_review_expand_20261103/flags_la/flags_v6.12.json'))['flags']
for s in (0, 1):
    a = json.load(open(f'selftest/seed{s}_rules_la_loongarch_v6.12.json'))['flags']
    b = json.load(open(f'selftest/seed{s}_rules_mips_loongarch_v6.12.json'))['flags']
    same = a == b
    ok &= same
    print(f'seed {s}: rules_la {len(a)}, rules_mips {len(b)}, identical={same}; vs old file {len(old)}:',
          'extra', [f['name'] for f in a if f not in old], 'missing', [f['name'] for f in old if f not in a])
raise SystemExit(0 if ok else 1)
PY
printf '%s\n' v6.1 v6.2 v6.3 v6.4 v6.5 v6.6 v6.7 v6.8 v6.9 v6.10 v6.11 v6.12 v6.13 v6.14 v6.15 v6.16 v6.17 v6.18 v6.19 v7.0 v7.1 v7.2 |
  xargs -P 8 -I{} sh -c 'test -f flags_mips/flags_{}.json && { echo skip {}; exit 0; }; PYTHONHASHSEED=0 python3 -B rules_mips.py mips {} flags_mips/flags_{}.json > flags_mips/run_{}.log 2>&1; echo done {} $?'
