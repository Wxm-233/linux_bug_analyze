source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd $REPO/experiments/case_taxonomy/effzero_20261120
mkdir -p /root/work/effzero dev
rev=$(git -C /root/repos/linux rev-parse "$1")
/usr/bin/time -v python3 effzero.py run "$1" dev/$2.json > dev/$2.log 2>&1
echo "rc=$? $2" >> dev/$2.log
