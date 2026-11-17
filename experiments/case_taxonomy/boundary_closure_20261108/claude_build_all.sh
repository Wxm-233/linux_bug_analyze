# Claude 2026-11-08: 按 claude_commands.md 第 1、2 节构建新配置。
# rv64_bpf 已验证，直接 build；其余 15 个先 prepare，只有打印 "olddefconfig verified" / "already prepared and verified" 才 build。
# 某个配置 prepare 不生效或 build 失败时记录下来，不重试，继续下一个（各配置互相独立）。
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
C="$REPO/experiments/case_taxonomy/boundary_closure_20261108/config.sh"
LOG="$REPO/experiments/case_taxonomy/boundary_closure_20261108/claude_build_all.log"
echo "start $(date '+%F %T')" >> "$LOG"
build() {
    local name=$1 t0=$(date +%s)
    if out=$(bash "$C" "$name" build --jobs 20 2>&1); then
        echo "$name BUILD OK $(( $(date +%s) - t0 ))s: $(echo "$out" | tail -n 1)" | tee -a "$LOG"
    else
        echo "$name BUILD FAILED $(( $(date +%s) - t0 ))s: $(echo "$out" | tail -n 5 | tr '\n' ' ')" | tee -a "$LOG"
    fi
}
build rv64_bpf
for name in rv32_abi rv32_nommu rv64_kexec rv64_trace rv64_mm rv64_pagealloc rv64_kasan rv64_kfence rv64_ptdump rv64_rvmon rv64_kcfi rv64_scs rv64_mlx5 arm64_bpf x86_64_bpf; do
    out=$(bash "$C" "$name" prepare 2>&1)
    if echo "$out" | grep -qE 'olddefconfig verified|already prepared and verified'; then
        echo "$name PREPARE OK" | tee -a "$LOG"
        build "$name"
    else
        echo "$name PREPARE NOT EFFECTIVE: $(echo "$out" | tail -n 5 | tr '\n' ' ')" | tee -a "$LOG"
    fi
done
echo "end $(date '+%F %T')" | tee -a "$LOG"
