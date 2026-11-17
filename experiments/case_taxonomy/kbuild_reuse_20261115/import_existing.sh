# kbuild_reuse criteria 二.8: register existing images (copies; originals untouched). WSL.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
KB="python3 $REPO/tools/kbuild/kbuild.py"
P=/root/work/proprules/kernels; KP=/root/work/kcov_pa/kernels; X=/root/work/x1loop/kernels
FIX=5bebe8de1926; PRE=$(git -C $KSRC rev-parse --short=12 $FIX^)
echo "x1 pre=$PRE fix=$FIX"
for a in riscv x86_64 arm64; do
  $KB import df2908090cda $a plain - $P/${a}_head.img --config $P/${a}_head.config --note "proprules_20261114 HEAD"
  $KB import df2908090cda $a kcov - $KP/${a}_head.img --config $KP/${a}_head.config --vmlinux $KP/${a}_head.vmlinux --note "kcov_pa_20261115 head"
  $KB import e7c375b18160 $a kcov - $KP/${a}_x1pre.img --config $KP/${a}_x1pre.config --vmlinux $KP/${a}_x1pre.vmlinux --note "kcov_pa_20261115 x1pre"
  $KB import $PRE $a plain - $X/${a}_pre.img --config $X/${a}_pre.config --note "x1loop_20261114 pre"
  $KB import $FIX $a plain - $X/${a}_fix.img --config $X/${a}_fix.config --note "x1loop_20261114 fix"
done
$KB list | wc -l
