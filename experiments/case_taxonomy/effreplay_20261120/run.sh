source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd $REPO/experiments/case_taxonomy/effreplay_20261120
mkdir -p sealed_replay
python3 replay.py run > sealed_replay/replay.log 2>&1
echo "rc=$?" > replay_rc.txt
