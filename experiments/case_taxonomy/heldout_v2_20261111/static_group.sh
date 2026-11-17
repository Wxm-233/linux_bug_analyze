# Frozen static pipeline for one LoongArch group (criteria 二, 四). Runs in WSL.
#   bash static_group.sh <group> <compile_commands.json> [<patch cutoff, unix seconds>] [<source root>]
# Build directories come from data/builds.json ("loongarch" -> group -> {loongarch, arm64, x86_64}).
# Output: static/<group>/{facts.json.gz, base_values.json, values.json, layouts.json, vocab.json, hints_<group>.json,
#         ranking_<group>.json, times.txt}
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
g=$1; cc=$2; cutoff=${3:-}; root=${4:-$KSRC}   # root: the source tree the compile database points to (fix 2026-11-11)
R=$REPO/experiments/case_taxonomy/heldout_v2_20261111
P=$REPO/experiments/case_taxonomy/heldout_prep_20261110/pipeline
O=$R/static/$g; mkdir -p $O
export PYTHONPATH=$P TARGET=loongarch BOUNDARY_POOL=none PYTHONDONTWRITEBYTECODE=1 PIPELINE_BUILDS=$R/data/builds.json
python3 $R/check_manifest.py
t() { local s=$(date +%s); "$@"; echo "$(basename $2 .py) $(( $(date +%s) - s ))s" >> $O/times.txt; }
: > $O/times.txt
t python3 $R/static/extract3.py $cc $root $O/facts.json.gz --jobs 16 > $O/extract.log 2>&1
python3 -c "import gzip,json,sys; n=len(json.load(gzip.open('$O/facts.json.gz','rt'))['functions']); print('functions',n); sys.exit(0 if n else 1)"  # guard: an empty extraction is an error
t python3 $P/macro_values.py $g $O/facts.json.gz --out $O/base_values.json > $O/macro_values.log 2>&1
t python3 $P/macro_values2.py $g $O/facts.json.gz --base-values $O/base_values.json --out $O/values.json > $O/macro_values2.log 2>&1
t python3 $P/layouts.py $g $O/facts.json.gz --out $O/layouts.json > $O/layouts.log 2>&1
t python3 $P/vocab.py $g --facts $O/facts.json.gz --values $O/values.json --out $O/vocab.json > $O/vocab.log 2>&1
extra=""; [ -n "$cutoff" ] && extra="--patch-cutoff $cutoff"
t python3 $P/rank.py $g --facts $O/facts.json.gz --values $O/values.json --out-dir $O \
   --nr-tables $R/data/nr_tables.json --version-tables $R/data/version_tables.json \
   --kernel-keys $R/data/kernel_keys.json $extra > $O/rank.log 2>&1
cat $O/times.txt
tail -n 2 $O/extract.log $O/layouts.log $O/vocab.log $O/rank.log
