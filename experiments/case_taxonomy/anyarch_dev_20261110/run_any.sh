# Run one case set on the kernels listed in a config file, 3 times each (anyarch criteria 二、四). No arch is hardcoded.
#   bash run_any.sh <kernels_<tag>.json>     logs -> /root/work/anyarch/runs/<tag>/ ; copied gz to <out>/ of the config
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
CT=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy
cfg=$(realpath -e -- "$1"); W=/root/work/anyarch
tag=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['group'])" "$cfg")
mkdir -p $W/runs/$tag $W/initramfs; jobs=$W/jobs.$$.txt; : > $jobs
python3 - "$cfg" > $W/k.$$.txt <<'PY'
import json,sys,os
c=json.load(open(sys.argv[1])); b=os.path.dirname(sys.argv[1])
for k in c["kernels"]:
    print(k["name"], k["arch"], k["image"], os.path.normpath(os.path.join(b, c["cases_txt"].replace("{arch}", k["arch"]))))
PY
while read name arch img txt; do
  [ -f $W/initramfs/${tag}_$arch.cpio ] || bash $CT/mix_dev_20261110/harness/mk_initramfs.sh $arch $txt $W/initramfs/${tag}_$arch.cpio >/dev/null || exit 1
  for i in 1 2 3; do echo "$arch $img $W/initramfs/${tag}_$arch.cpio $W/runs/$tag/$name.run$i.log" >> $jobs; done
done < $W/k.$$.txt
echo "jobs: $(wc -l < $jobs)  start $(date +%T)"
xargs -P ${PAR:-9} -L 1 bash $CT/casemodel_dev_20261110/harness/run_qemu.sh < $jobs
echo "done $(date +%T)"
out=$(python3 -c "import json,sys,os;c=json.load(open(sys.argv[1]));print(os.path.normpath(os.path.join(os.path.dirname(sys.argv[1]),c['logs'])))" "$cfg")
mkdir -p "$out"
for f in $W/runs/$tag/*.log; do grep -aq '^@@SH END' $f || echo "INCOMPLETE $f"; gzip -c $f > "$out/$(basename $f).gz"; done
rm -f $jobs $W/k.$$.txt $W/initramfs/${tag}_*.cpio
