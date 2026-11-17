cd /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/effdep6_dev_20261113
mkdir -p /root/work/effdep6
python3 archscan.py HEAD /root/work/effdep6/scan_CUR.json.gz
for f in /root/work/effdep5/facts/*_fix.json; do
  id=$(basename $f _fix.json); p=$(python3 -c "import json,sys;print(json.load(open('$f'))['parent'])")
  python3 archscan.py $p /root/work/effdep6/scan_$id.json.gz
done
python3 - <<'P'
import gzip,json
d=json.load(gzip.open('/root/work/effdep6/scan_X1.json.gz','rt'))
for n in ('tag_clear_highpage','pte_modify'):
    print(n, {a:v[:8] for a,v in d['calls'].get(n,{}).items() if a in ('arm64','x86','riscv','s390')})
P
du -sh /root/work/effdep6
