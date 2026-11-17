source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
free -m
ps -eo pid,ppid,etime,pcpu,rss,args --sort=-rss | head -18
