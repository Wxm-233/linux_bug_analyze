# layerbound amendment 1.1: compile databases for the three mglru kbuild trees (written outside the trees)
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
for a in riscv arm64 x86_64; do
  t=/root/work/kbuild/trees/df2908090cda_${a}_mglru
  python3 $t/src/scripts/clang-tools/gen_compile_commands.py -d $t/out -o /root/work/layerbound/cc_$a.json
  echo "$a entries $(python3 -c "import json;print(len(json.load(open('/root/work/layerbound/cc_$a.json'))))")"
done
