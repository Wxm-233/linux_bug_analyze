source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
case "${1:-}" in
  show|grep) exec git -C /root/repos/linux --no-pager "$@" ;;
  *) printf '%s\n' 'Only read-only git show/grep queries are permitted.' >&2; exit 2 ;;
esac
