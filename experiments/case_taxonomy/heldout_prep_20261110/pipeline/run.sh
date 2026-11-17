source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
while [ "$#" -gt 0 ]; do
    case "$1" in
        --target) export TARGET="$2"; shift 2 ;;
        --builds) export PIPELINE_BUILDS="$2"; shift 2 ;;
        --pool) export BOUNDARY_POOL="$2"; shift 2 ;;
        *) break ;;
    esac
done
if [ "$#" -eq 0 ]; then
    echo '用法: run.sh [--target riscv|loongarch] [--builds 配置.json] [--pool existing|none] 工具 [工具参数...]' >&2
    exit 2
fi
tool="${1%.py}"
shift
case "$tool" in
    extract3|hints4|macro_values|macro_values2|layouts|vocab|rank) ;;
    *) echo "未知工具: $tool" >&2; exit 2 ;;
esac
exec python3 "$REPO/experiments/case_taxonomy/heldout_prep_20261110/pipeline/$tool.py" "$@"
