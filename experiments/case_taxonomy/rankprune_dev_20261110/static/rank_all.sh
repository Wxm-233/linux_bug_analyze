source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/rankprune_dev_20261110/static
python3 rank.py --selftest || exit 1
python3 rank.py A101 A310 A171 A181 B467 CUR
