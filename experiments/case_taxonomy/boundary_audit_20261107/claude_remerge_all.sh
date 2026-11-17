# Claude 2026-11-07: 依次对三个架构反复运行 GPT 写的 claude_remerge_batch.sh，直到各自打印 complete，再运行 report_revised.py。
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
A="$REPO/experiments/case_taxonomy/boundary_audit_20261107"
for arch in riscv arm64 x86_64; do
    for i in $(seq 1 200); do
        out=$(bash "$A/claude_remerge_batch.sh" "$arch" 128 2>&1 | tail -n 3)
        echo "[$arch #$i $(date +%H:%M:%S)] $out" | tail -n 1
        if echo "$out" | grep -qw complete; then
            echo "$arch complete"
            break
        fi
        if [ "$i" = 200 ]; then echo "$arch did not complete"; exit 1; fi
    done
done
bash "$A/run.sh" report_revised.py
