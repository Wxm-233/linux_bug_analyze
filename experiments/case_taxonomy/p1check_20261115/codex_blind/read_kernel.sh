source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
export GIT_OPTIONAL_LOCKS=0
mode="$1"
shift
case "$mode" in
    show)
        git --no-pager -C /root/repos/linux show "df2908090cda:$1" | nl -ba | sed -n "$2"
        ;;
    grep64)
        pattern="$(printf '%s' "$1" | base64 -d)"
        shift
        git --no-pager -C /root/repos/linux grep -n -E "$pattern" df2908090cda -- "$@"
        ;;
    *) exit 2 ;;
esac
