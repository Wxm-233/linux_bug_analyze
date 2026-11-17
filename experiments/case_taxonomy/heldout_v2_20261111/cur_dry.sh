# Dry run of the frozen v2 pipeline on the current-version LoongArch kernel (no known defect). Runs in WSL.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
R=$REPO/experiments/case_taxonomy/heldout_v2_20261111; T=$REPO/experiments/case_taxonomy/difftest_tools_20261111
cd $R; export PYTHONDONTWRITEBYTECODE=1
echo "$(date '+%F %T') CUR dry run start" | tee -a logs/batch.log
bash static_group.sh CUR $REPO/experiments/case_taxonomy/heldout_prep_20261110/pipeline/smoke/compile_commands_loongarch.json | tail -3
python3 prep_ws.py CUR
TARGET=loongarch python3 static/fieldvocab2.py static/CUR/facts.json.gz ws/CUR/diverse_dev_20261110/gen/layouts_CUR.json ws/CUR/fieldvocab.json
python3 gen_holdout2.py ws/CUR CUR $(cat ws/CUR/S.txt) ws/CUR/fieldvocab.json --slot-name loongarch | grep -v "^CUR U \|^CUR cases [0-9]* {" | cut -c1-200
python3 - <<'PY'
import json
K="/root/work/boundary_build"
json.dump({"group":"CUR","cases":"ws/CUR/run/cases.json","cases_txt":"ws/CUR/run/cases_{name}.txt","logs":"runs/CUR","out":"cmp/CUR",
  "volatile":"../stability_dev_20261111/volatile.json",
  "kernels":[{"name":"cur_loongarch","arch":"loongarch","image":"/root/work/heldout/build/cur_loongarch/arch/loongarch/boot/vmlinux.efi"},
             {"name":"cur_arm64","arch":"arm64","image":f"{K}/arm64_defconfig/arch/arm64/boot/Image"},
             {"name":"cur_x86_64","arch":"x86_64","image":f"{K}/x86_64_defconfig/arch/x86/boot/bzImage"}]},open("kernels_CUR.json","w"),indent=1)
PY
PAR=12 bash $T/run.sh $R/kernels_CUR.json
python3 $T/compare.py kernels_CUR.json
python3 $T/warnings.py runs/CUR | head -12
echo "$(date '+%F %T') CUR dry run done" | tee -a logs/batch.log
