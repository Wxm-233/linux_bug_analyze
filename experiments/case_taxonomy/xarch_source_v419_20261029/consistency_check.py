"""Post-hoc consistency check (README.md): reproduce the xarch_source_20261029 amended pairs from the v4.19 run.
The registered check required both ends inside v5.15..df2908090cda, but the earlier construction lets source B seeds predate v5.15;
this check uses the earlier construction instead. WSL; writes consistency_check.json and prints it.
"""
from pathlib import Path
import json
import subprocess

HERE = Path(__file__).resolve().parent
C = HERE.parent


def main():
    target = HERE / 'consistency_check.json'
    if target.exists():
        raise SystemExit('preserve')
    new = json.loads((HERE / 'xarch_pairs_v419.json').read_text())['final']
    old = json.loads((C / 'xarch_source_20261029' / 'xarch_pairs_amended.json').read_text())['final']
    rng = set(subprocess.run(['git', '-C', '/root/repos/linux', 'rev-list', 'v5.15..df2908090cda'], capture_output=True, text=True).stdout.split())
    key = lambda f: (f['source'], f['seed'], f['target'])
    sub = [f for f in new if f['target'] in rng and (f['source'] == 'B' or f['seed'] in rng)]
    ok, sk = {key(f) for f in old}, {key(f) for f in sub}
    clean_old = {key(f): f['clean'] for f in old}
    out = {'old_final': len(old), 'repro_subset': len(sub), 'same_set': ok == sk, 'only_old': len(ok - sk), 'only_new': len(sk - ok),
           'old_B_pairs_with_seed_before_v5_15': sum(1 for f in old if f['source'] == 'B' and f['seed'] not in rng),
           'repro_clean_distinct_targets_since_1027': len({f['target'] for f in sub if f['clean_since_1027']}),
           'old_amended_clean_distinct_targets': len({f['target'] for f in old if f['clean']}),
           'clean_flag_mismatch': sum(1 for f in sub if key(f) in clean_old and clean_old[key(f)] != f['clean_since_1027'])}
    target.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(out))


if __name__ == '__main__':
    main()
