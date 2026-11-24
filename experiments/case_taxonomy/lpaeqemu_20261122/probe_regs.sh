#!/bin/bash
# lpaeqemu diagnosis: boot the hanging layout, then read CPU registers from the QEMU monitor a few times
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
R=$REPO/experiments/case_taxonomy/lpaeqemu_20261122
W=/root/work/lpaeqemu
sock=$W/mon.sock; rm -f $sock
qemu-system-arm -M virt,highmem=on -cpu cortex-a15 -smp 1 -m 4G -kernel $W/keep/${K:-base}/zImage -initrd $W/keep/init.cpio \
  -append "console=ttyAMA0 panic=-1 rdinit=/init mem=1G@0x40000000 mem=512M@0x100000000" \
  -monitor unix:$sock,server,nowait -nographic -no-reboot > $R/logs/probe_regs_boot.log 2>&1 &
q=$!
sleep 45
python3 - "$sock" > $R/logs/probe_regs.txt <<'PY'
import socket, sys, time
s = socket.socket(socket.AF_UNIX); s.connect(sys.argv[1]); s.settimeout(2)
def cmd(c):
    s.sendall((c + "\n").encode()); time.sleep(1.0); out = b""
    try:
        while True:
            d = s.recv(65536)
            if not d: break
            out += d
    except Exception: pass
    return out.decode(errors="replace")
cmd("")
for i in range(4):
    print("=== sample", i); print(cmd("info registers")); time.sleep(2)
cmd("quit")
PY
wait $q 2>/dev/null
grep -E "^R0[0-9]|R15|PSR" $R/logs/probe_regs.txt | head -20
