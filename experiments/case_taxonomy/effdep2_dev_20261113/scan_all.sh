cd /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/effdep2_dev_20261113
for f in /root/work/effdep/facts/*_fix.json; do
  id=$(basename $f _fix.json); p=$(python3 -c "import json,sys;print(json.load(open('$f'))['parent'])")
  python3 archscan.py $p /root/work/effdep2/scan_$id.json.gz
done
ls -la /root/work/effdep2
