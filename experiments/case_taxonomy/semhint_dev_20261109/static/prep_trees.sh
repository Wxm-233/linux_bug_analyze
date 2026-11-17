# Restore source trees at the paths recorded in the builds' .cmd files and write the riscv compile databases
# (criteria 4.1). Pre-fix tree: fix^ at /root/work/difftest/src/<ID>_pre; the two references share one fix tree
# (/root/work/semhint/src/<ID>_fix) via symlinks src/<ID>_ref_{arm64,x86_64}.
#   prep_trees.sh <ID>...      -> /root/work/semhint/cc/<ID>_pre.json
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
declare -A FIX=([A101]=2116988d5372 [A310]=61119394631f [A171]=890ba5be6335 [A181]=1046791390af [B467]=c625154993d0)
S=/root/work/difftest/src; W=/root/work/semhint; mkdir -p $S $W/src $W/cc
for id in "$@"; do
  c=${FIX[$id]}
  [ -f $S/${id}_pre/Makefile ] || { mkdir -p $S/${id}_pre; git -C $KSRC archive "$c^" | tar -x -C $S/${id}_pre; }
  [ -f $W/src/${id}_fix/Makefile ] || { mkdir -p $W/src/${id}_fix; git -C $KSRC archive "$c" | tar -x -C $W/src/${id}_fix; }
  for a in arm64 x86_64; do [ -e $S/${id}_ref_$a ] || ln -s $W/src/${id}_fix $S/${id}_ref_$a; done
  (cd $S/${id}_pre && python3 scripts/clang-tools/gen_compile_commands.py -d /root/work/difftest/build/${id}_pre -o $W/cc/${id}_pre.json)
  echo "$id pre=$(git -C $KSRC rev-parse --short "$c^") entries=$(python3 -c "import json;print(len(json.load(open('$W/cc/${id}_pre.json'))))")"
done
df -h / | tail -1
