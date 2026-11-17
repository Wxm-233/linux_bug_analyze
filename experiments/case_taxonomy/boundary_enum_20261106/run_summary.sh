# Claude 2026-11-07: 三个架构都合并完后，运行 GPT 写好的汇总与报告脚本。
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
cd "$REPO/experiments/case_taxonomy/boundary_enum_20261106"
ls -la result_riscv.json result_arm64.json result_x86_64.json
python3 -B summarize.py
python3 -B report.py
ls -la stats.json sample_hits.json README.md 2>&1
