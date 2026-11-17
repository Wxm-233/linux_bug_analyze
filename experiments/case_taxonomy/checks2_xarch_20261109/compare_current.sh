# Current version: riscv vs x86_64, arm64 (criteria sections 3 and 6) -> flags_current.json
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
H=$REPO/experiments/case_taxonomy/checks2_xarch_20261109; O=/root/work/checks2/current; P=$REPO/experiments/case_taxonomy/boundary_audit_20261107/revised
python3 -B $H/xcmp.py compare --target $O/facts_riscv.json.gz --counter x86=$O/facts_x86.json.gz --counter arm64=$O/facts_arm64.json.gz \
  $(for f in $P/*/*/symbols_runtime_*.json; do echo --pool $f; done) --out $H/flags_current.json
