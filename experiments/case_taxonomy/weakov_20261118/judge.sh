source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
# poc_criteria 二: each image 3 runs with Codex's run_poc.sh; logs kept for manual check
H=$REPO/experiments/case_taxonomy/weakov_20261118
OUT=/root/work/weakov/judge_${1:-r1}
mkdir -p $OUT
IMG=/root/work/kbuild/images
: > $H/judge_${1:-r1}.txt
for tag in bug fix; do
  if [ $tag = bug ]; then K=$IMG/df2908090cda_arm64_acpihp_weakov-W1.img; else K=$IMG/df2908090cda_arm64_acpihp_-.img; fi
  for i in 1 2 3; do
    v=$(bash $H/poc/run_poc.sh $K $OUT/${tag}_$i.log 2>&1 | grep -a "^VERDICT" | tail -1)
    echo "$tag $i $v" | tee -a $H/judge_${1:-r1}.txt
  done
done
