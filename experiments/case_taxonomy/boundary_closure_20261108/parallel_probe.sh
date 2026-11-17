source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -Eeuo pipefail
cd "$REPO"
export PYTHONDONTWRITEBYTECODE=1
python3 --version
free -m
test -x /usr/bin/time
ps -eo pid,ppid,rss,comm --sort=-rss | head -n 16 || true
