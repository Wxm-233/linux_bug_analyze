# Default run script from 2026-11-11 on (WSL). Runs one case set on the kernels listed in a config, 3 times each.
# No architecture or kernel name is hard-coded.
#   bash run.sh <kernels.json>
# Config fields used here (paths relative to the config file):
#   "group": tag;  "logs": directory for the gz logs;
#   "cases_txt": pattern of the per-architecture or per-kernel case list; {arch} and {name} are substituted;
#   "kernels": [{"name", "arch", "image"}]   image = kernel image inside WSL
# Executor and initramfs are those of the earlier rounds (read-only); the initramfs script is the copy in
# heldout_prep_20261110/harness, identical to mix_dev_20261110/harness except for an added loongarch branch. QEMU invocation: harness/run_qemu.sh here
# (kernel command line loglevel=5 instead of quiet). Kernel warnings: python warnings.py <logs dir>.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
CT=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy
cfg=$(realpath -e -- "$1") || exit 2
tag=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['group'])" "$cfg")
W=/root/work/difftest_tools/$tag.$$
mkdir -p $W/runs $W/initramfs
python3 - "$cfg" > $W/k.txt <<'PY'
import json, os, sys
c = json.load(open(sys.argv[1])); b = os.path.dirname(sys.argv[1])
print(os.path.normpath(os.path.join(b, c["logs"])))
for k in c["kernels"]:
    txt = c["cases_txt"].replace("{arch}", k["arch"]).replace("{name}", k["name"])
    print(k["name"], k["arch"], k["image"], os.path.normpath(os.path.join(b, txt)))
PY
out=$(head -1 $W/k.txt); : > $W/jobs.txt
tail -n +2 $W/k.txt | while read name arch img txt; do
  key=$(echo "$txt" | md5sum | cut -c1-12)          # kernels sharing a list share an initramfs
  [ -f $W/initramfs/$key.cpio ] || bash $CT/heldout_prep_20261110/harness/mk_initramfs.sh $arch $txt $W/initramfs/$key.cpio >/dev/null || exit 1
  for i in 1 2 3; do echo "$arch $img $W/initramfs/$key.cpio $W/runs/$name.run$i.log" >> $W/jobs.txt; done
done || exit 1
echo "jobs: $(wc -l < $W/jobs.txt)  start $(date +%T)"
# QUIET=1 uses the old invocation (kernel command line "quiet"); default shows warning-level kernel messages
Q=$CT/difftest_tools_20261111/harness/run_qemu.sh; [ "${QUIET:-0}" = 1 ] && Q=$CT/casemodel_dev_20261110/harness/run_qemu.sh
xargs -P ${PAR:-10} -L 1 bash $Q < $W/jobs.txt > $W/xargs.log 2>&1
echo "done $(date +%T)  ok=$(grep -c 'exit=0' $W/xargs.log) of $(wc -l < $W/jobs.txt)"
mkdir -p "$out"
for f in $W/runs/*.log; do grep -aq '^@@SH END' $f || echo "INCOMPLETE $f"; gzip -c $f > "$out/$(basename $f).gz"; done
rm -rf $W
