#!/bin/bash
# usage: run_poc.sh <arm64 kernel Image> <serial log path>
# Builds the two SSDTs and the guest init, boots QEMU virt (UEFI + ACPI), prints one VERDICT line.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -u
K=$1; LOG=$2
HERE=$(cd "$(dirname "$0")" && pwd)
PKG=/root/work/weakov/pkg/root
W=/root/work/weakov/poc_work
mkdir -p $W "$(dirname "$LOG")"
B=$(mktemp -d $W/b.XXXXXX)

$PKG/usr/bin/iasl -p $B/ssdt_eject $HERE/ssdt_eject.asl > $B/iasl1.log 2>&1 || { cat $B/iasl1.log; echo "VERDICT: ERROR iasl ssdt_eject"; exit 1; }
$PKG/usr/bin/iasl -p $B/ssdt_readd $HERE/ssdt_readd.asl > $B/iasl2.log 2>&1 || { cat $B/iasl2.log; echo "VERDICT: ERROR iasl ssdt_readd"; exit 1; }
aarch64-linux-gnu-gcc -static -O2 -o $B/init $HERE/init.c || { echo "VERDICT: ERROR gcc"; exit 1; }

# initrd = [uncompressed cpio with kernel/firmware/acpi/*.aml for the table upgrade] + [rootfs cpio]
mkdir -p $B/t/kernel/firmware/acpi $B/r/proc $B/r/sys $B/r/dev $B/r/tmp
cp $B/ssdt_eject.aml $B/t/kernel/firmware/acpi/
cp $B/init $B/r/init; cp $B/ssdt_readd.aml $B/r/
(cd $B/t && find . | cpio -o -H newc --quiet) > $B/tables.cpio
(cd $B/r && find . | cpio -o -H newc --quiet) > $B/root.cpio
cat $B/tables.cpio $B/root.cpio > $B/initrd.cpio

timeout 400 qemu-system-aarch64 -M virt -cpu max -smp 4 -m 2G -accel tcg,thread=single -nographic -no-reboot \
    -bios $PKG/usr/share/qemu-efi-aarch64/QEMU_EFI.fd -kernel "$K" -initrd $B/initrd.cpio \
    -append "console=ttyAMA0 acpi=force rdinit=/init loglevel=7" > "$LOG" 2>&1 < /dev/null
rc=$?
rm -rf $B
tr -d '\r' < "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"

g() { grep -a "$1" "$LOG" | tail -1; }
ae=$(g "WK: AFTER_EJECT"); ad=$(g "WK: AFTER_ADD"); aa=$(g "WK: AFTER_ONLINE"); ow=$(g "WK: online write ret=")
# evidence that the re-add notification really re-enumerated the CPU (else the re-add check means nothing)
rescan=no
if echo "$ad" | grep -q "phys=yes" || awk '/WK: eject write/{f=1} f && /CPU1 has been hot-added/{x=1} END{exit !x}' "$LOG"; then rescan=yes; fi
kw=$(grep -a -c -E "WARNING:|BUG:|Call trace:|duplicate filename|kobject_add_internal failed" "$LOG")
if grep -aqE "Table Upgrade: install \[SSDT- *WKOV- *CPUEJ\]" "$LOG"; then :; else echo "VERDICT: ERROR SSDT not installed (rc=$rc)"; exit 0; fi
if [ -z "$ae" ] || grep -aq "WK: ERROR" "$LOG"; then echo "VERDICT: ERROR eject not reached/completed (rc=$rc) $(g 'WK: ERROR')"; exit 0; fi
if echo "$ae" | grep -q "cpu1_sysfs=present"; then
    echo "VERDICT: TRIGGERED stale sysfs device after eject [$ae] add=[$aa] kernel_warnings=$kw"; exit 0
fi
if ! grep -aq "WK: DONE" "$LOG"; then echo "VERDICT: TRIGGERED re-add hangs (no DONE, rc=$rc) [$ae]"; exit 0; fi
if [ $rescan = no ]; then echo "VERDICT: ERROR re-add notification did not re-enumerate the CPU [$ad]"; exit 0; fi
if [ "$kw" -gt 0 ] || ! echo "$aa" | grep -q "cpu1_sysfs=present online=1"; then
    echo "VERDICT: TRIGGERED re-add failed [$aa] [$ow] kernel_warnings=$kw"; exit 0
fi
echo "VERDICT: NOT_TRIGGERED sysfs device removed and CPU came back [$ae] [$aa]"
