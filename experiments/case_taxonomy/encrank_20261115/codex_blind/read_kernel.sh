source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
revision=df2908090cda
if [[ "${1:-}" == --grep || "${1:-}" == --grep64 ]]; then
    mode="$1"
    shift
    pattern="$1"
    shift
    if [[ "$mode" == --grep64 ]]; then
        pattern="$(printf '%s' "$pattern" | base64 -d)"
    fi
    git -C /root/repos/linux grep -n -E "$pattern" "$revision" -- "$@"
    exit
fi
for spec in "$@"; do
    path="${spec%%:*}"
    span="${spec#*:}"
    if [[ "$span" == "$spec" ]]; then
        printf '\n=== %s ===\n' "$path"
        git -C /root/repos/linux show "$revision:$path" | nl -ba
    else
        first="${span%-*}"
        last="${span#*-}"
        printf '\n=== %s:%s ===\n' "$path" "$span"
        git -C /root/repos/linux show "$revision:$path" | awk -v first="$first" -v last="$last" 'NR >= first && NR <= last {printf "%6d %s\n", NR, $0}'
    fi
done
