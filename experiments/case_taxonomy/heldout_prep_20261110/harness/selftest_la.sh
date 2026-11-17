# Executor v2 self-test on the current LoongArch kernel, using the riscv case file (both use asm-generic numbers),
# compared field by field with the stored riscv log of the casemodel self-test.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
P=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy
H=$P/heldout_prep_20261110/harness; S=$P/casemodel_dev_20261110/harness/selftest
W=/root/work/heldout/selftest; mkdir -p $W
bash $H/mk_initramfs.sh loongarch $S/selftest_cases_riscv.txt $W/la.cpio || exit 1
st=$(mktemp -d); (cd $st && cpio -id --quiet < $W/la.cpio && readelf -lW init | grep -m1 LOAD; file init | cut -c1-120); rm -rf $st
bash $H/run_qemu.sh loongarch /root/work/heldout/build/cur_loongarch/arch/loongarch/boot/vmlinux.efi $W/la.cpio $W/la.log
cp $W/la.log $H/selftest_la.log
python3 - $W/la.log $S/riscv.log <<'PY'
import json, sys
def load(p):
    r = {}
    for l in open(p, errors="replace"):
        if l.startswith('{"id"'):
            try: j = json.loads(l)
            except Exception: print("BAD", l[:80]); continue
            j.pop("t", None); r[j["id"]] = j
    return r
a, b = load(sys.argv[1]), load(sys.argv[2])
print("cases la", len(a), "riscv", len(b))
same = 0
for i in sorted(b):
    if a.get(i) == b[i]: same += 1
    else: print("DIFF", i, "\n  la   ", json.dumps(a.get(i))[:300], "\n  riscv", json.dumps(b[i])[:300])
print("same", same)
PY
grep -a -c '@@SH END' $W/la.log; grep -a -E 'harness_error|taint_changed' $W/la.log | head
