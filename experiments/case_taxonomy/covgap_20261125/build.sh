#!/bin/bash
# covgap criteria 一.2/一.3 step 1: five builds with the new profiles, compile databases, .config copies, into /root/work/covgap. WSL, root.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
KB="python3 $REPO/tools/kbuild/kbuild.py"
W=/root/work/covgap; mkdir -p $W
HERE=$REPO/experiments/case_taxonomy/covgap_20261125; mkdir -p $HERE/logs
declare -A PROF=([riscv]=wide2 [x86_64]=wide2 [arm64]=widemte2 [arm]=widearm2 [powerpc]=wide2)
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
# allyesconfig trees are reused from round 9 (layerbound5/avail_*), linked into $W
for a in riscv arm64 x86_64 arm powerpc; do [ -e $W/avail_$a ] || ln -s /root/work/layerbound5/avail_$a $W/avail_$a; done
cd /root/repos/linux && git status -s | head -3; echo "== $(date +%T) done"
