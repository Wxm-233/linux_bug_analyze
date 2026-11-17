# Collect + reduce one build with the extended archbound (criteria section 2).
#   collect_build.sh <tag> <build dir> <arch dir name> <out dir> [kernel source root] [extra_dir/ ...]
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
tag=$1; bdir=$2; adir=$3; out=$4; kroot=${5:-/root/repos/linux}; shift 5 2>/dev/null || shift $#
HERE=$REPO/experiments/case_taxonomy/checks2_xarch_20261109
BIN=/root/work/checks2/archbound_ext/archbound
mkdir -p $out/cdb_$tag
[ -f $out/facts_$tag.json.gz ] && { echo "$tag already collected"; exit 0; }
python3 $HERE/nomd.py $bdir/compile_commands.json $out/cdb_$tag/compile_commands.json
KROOT=$kroot python3 $HERE/scope_list.py $bdir/compile_commands.json $adir $out/scope_$tag.txt "$@"
t0=$(date +%s)
/usr/bin/time -v $BIN collect -p $out/cdb_$tag/compile_commands.json --root $kroot --arch $tag -j 4 \
   --out $out/facts_$tag.json $(cat $out/scope_$tag.txt) > $out/collect_$tag.log 2>&1
rc=$?
echo "$tag collect exit=$rc secs=$(( $(date +%s)-t0 )) maxrss_kb=$(grep 'Maximum resident' $out/collect_$tag.log | awk '{print $NF}') $(grep '^\[collect\]' $out/collect_$tag.log)"
[ $rc -eq 0 ] || exit $rc
python3 -B $HERE/xcmp.py reduce $out/facts_$tag.json $out/facts_$tag.json.gz && rm -f $out/facts_$tag.json
