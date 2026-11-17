# Claude 2026-11-07: x86_64 的扫描与分阶段合并，一次跑完（不在 Codex 中运行，没有单条命令时限）。
# 只调用 GPT 写好的 batch.sh，与 riscv、arm64 用的是同一套程序和参数。
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
B="$REPO/experiments/case_taxonomy/boundary_enum_20261106/batch.sh"
until python3 -B "$REPO/experiments/case_taxonomy/boundary_enum_20261106/enumerate.py" status x86_64 | grep -q '3022/3022 cached'; do
    bash "$B" scan x86_64 --jobs 16 --limit 1024 | tail -n 3
done
python3 -B "$REPO/experiments/case_taxonomy/boundary_enum_20261106/enumerate.py" status x86_64
for i in $(seq 1 30); do
    out=$(bash "$B" merge-staged x86_64 1024 | tail -n 2)
    echo "$out"
    if echo "$out" | grep -qE 'merged [0-9]+ symbols|already complete'; then
        echo "x86_64 done"
        exit 0
    fi
done
echo "merge did not finish within 30 rounds"
exit 1
