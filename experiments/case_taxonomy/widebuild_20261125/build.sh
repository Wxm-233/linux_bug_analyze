#!/bin/bash
# widebuild criteria 二.1/二.2: five builds (kbuild), compile databases and allyesconfig, into /root/work/layerbound5. WSL, root.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
KB="python3 $REPO/tools/kbuild/kbuild.py"
W=/root/work/layerbound5; mkdir -p $W
HERE=$REPO/experiments/case_taxonomy/widebuild_20261125; mkdir -p $HERE/logs
declare -A PROF=([riscv]=wide [x86_64]=wide [arm64]=widemte [arm]=widearm [powerpc]=wide)
for a in riscv x86_64 arm64 arm powerpc; do
  p=${PROF[$a]}
  echo "== $(date +%T) build $a $p"
  if $KB get df2908090cda $a $p > $HERE/logs/img_$a.txt 2> $HERE/logs/kbuild_$a.log; then
    echo "   ok $(cat $HERE/logs/img_$a.txt)"
  else
    echo "   FAIL rc=$? (see logs/kbuild_$a.log)"; tail -5 $HERE/logs/kbuild_$a.log
  fi
  t=/root/work/kbuild/trees/df2908090cda_${a}_${p}
  python3 $t/src/scripts/clang-tools/gen_compile_commands.py -d $t/out -o $W/cc_$a.json 2> $HERE/logs/gencc_$a.log
  echo "   cc entries $(python3 -c "import json;print(len(json.load(open('$W/cc_$a.json'))))" 2>/dev/null)"
  cp $t/out/.config $HERE/logs/config_$a.txt 2>/dev/null
  echo "   disk free $(df -h / | tail -1 | awk '{print $4}')"
done
for a in riscv arm64 x86_64 arm powerpc; do
  ka=$a; [ $a = x86_64 ] && ka=x86
  o=$W/avail_$a; rm -rf $o; mkdir -p $o
  make -C /root/repos/linux O=$o ARCH=$ka LLVM=1 allyesconfig > $o/log.txt 2>&1 || { echo "allyes FAIL $a"; tail -3 $o/log.txt; }
  echo "allyes $a symbols $(grep -cE '^(CONFIG_|# CONFIG_)' $o/.config)"
done
cd /root/repos/linux && git status -s | head -3; echo "== $(date +%T) done"
