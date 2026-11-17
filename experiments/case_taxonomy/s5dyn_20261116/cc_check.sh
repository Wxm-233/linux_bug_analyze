cd /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/s5dyn_20261116
for cc in aarch64-linux-gnu riscv64-linux-gnu x86_64-linux-gnu; do
  ${cc}-gcc -static -O2 -Wall -pthread -o /tmp/s4_$cc s5.c 2>/tmp/s4_$cc.err; echo "$cc rc=$?"; grep -v "defined but not used\|In function\|^ *|\|^\s*[0-9]* |" /tmp/s4_$cc.err | head -3
done
rm -f /tmp/s4_*
