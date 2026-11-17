# Trees and facts for effdep5 (criteria 二; same trees as effdep criteria 三). Runs in WSL.
#   bash prep.sh cur            facts of the current version, riscv / arm64 / x86_64 (existing full builds)
#   bash prep.sh samples        pre-fix riscv partial builds of the 12 samples -> facts, fix functions; trees removed
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
R=$REPO/experiments/case_taxonomy/effdep5_dev_20261113; C2=$REPO/experiments/case_taxonomy/checks2_xarch_20261109
W=/root/work/effdep5; F=$W/facts; mkdir -p $F $W/src $W/build
LOG=$R/prep.log
COMMON="kernel/ mm/ lib/ init/ drivers/irqchip/ drivers/perf/ drivers/acpi/ drivers/clocksource/ drivers/iommu/ drivers/cpuidle/ drivers/firmware/"
if [ "$1" = cur ]; then
  ARCHS="${2:-riscv}"   # e.g.  bash prep.sh cur riscv
  for a in $ARCHS; do
    d=$a; [ $a = x86 ] && d=x86_64
    t0=$(date +%s)
    python3 $R/effdep5_extract.py /root/work/boundary_build/${d}_defconfig/compile_commands.json $KSRC $F/CUR_$d.json.gz \
      --jobs 16 --scope arch/$a/ $COMMON > $W/extract_CUR_$d.log 2>&1
    echo "CUR_$d extract $(( $(date +%s)-t0 ))s $(tail -1 $W/extract_CUR_$d.log)" | tee -a $LOG
  done
  exit 0
fi
# samples: id:fix-commit[:extra configs comma separated]
SAMPLES="X1:5bebe8de1926 A274:7e4cb63d61a7:ACPI B485:a60b990798eb:PCI_MSI A025:b8b2711336f0 A032:46e714c729c8 A043:3951f6add519
A243:e3573f739e3d A254:bc7b086a4552 A310:61119394631f A380:a216e24fc947:KVM A387:5eb6d68fe24d:KVM
X2:9fd154ba926b"   # effdep5: X1 first
for spec in $SAMPLES; do
  IFS=: read id fix extra <<< "$spec"
  [ -f $F/${id}_pre.json.gz ] && { echo "$id done before" | tee -a $LOG; continue; }
  parent=$(git -C $KSRC rev-parse --short=12 $fix^); S=$W/src/$id; B=$W/build/$id
  t0=$(date +%s)
  rm -rf $S $B; mkdir -p $S
  git -C $KSRC archive --format=tar $parent | tar -x -C $S
  dirs="arch/riscv/ $COMMON"
  for f in $(git -C $KSRC diff --name-only $parent $fix | grep '\.c$'); do
    d=$(dirname $f)/; case " $dirs " in *" ${d%%/*}/"*) ;; esac
    skip=0; for s in $dirs; do case $d in $s*) skip=1;; esac; done; [ $skip = 0 ] && dirs="$dirs $d"
  done
  if bash $C2/build_partial.sh $S $B "$dirs" ${extra//,/ } > $W/build_$id.log 2>&1; then
    python3 $R/effdep5_extract.py $B/compile_commands.json $S $F/${id}_pre.json.gz --jobs 16 > $W/extract_$id.log 2>&1
    echo "$id parent $parent build+extract OK $(( $(date +%s)-t0 ))s $(tail -1 $W/extract_$id.log | cut -c1-120)" | tee -a $LOG
  else
    echo "$id parent $parent BUILD FAILED $(( $(date +%s)-t0 ))s: $(cat $B/failed.txt 2>/dev/null | tail -3 | tr '\n' ' ' | cut -c1-300)" | tee -a $LOG
  fi
  # functions changed by the fix (hunk header context and macro names on changed lines), criteria 八.1
  git -C $KSRC diff -U0 $parent $fix | python3 -c "
import re,sys,json
names=set(); files=[]
for l in sys.stdin:
    if l.startswith('+++ b/'): files.append(l[6:].strip())
    m=re.match(r'^@@ [^@]* @@ (.*)', l)
    if m:
        ids=re.findall(r'([A-Za-z_]\w*)\s*\(', m.group(1))
        if ids: names.add(ids[-1] if not m.group(1).lstrip().startswith('#define') else ids[0])
    m2=re.match(r'^[-+]\s*#\s*define\s+([A-Za-z_]\w*)', l)
    if m2: names.add(m2.group(1))
json.dump({'id':'$id','fix':'$fix','parent':'$parent','files':files,'functions':sorted(names)},open('$F/${id}_fix.json','w'))
print('$id fix functions', sorted(names))" | tee -a $LOG
  rm -rf $S $B
done
echo "samples end $(date '+%F %T') $(du -sh $W | cut -f1)" | tee -a $LOG
