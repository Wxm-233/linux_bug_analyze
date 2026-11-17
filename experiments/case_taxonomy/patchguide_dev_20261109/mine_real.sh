# criteria 3.1: counterpart fix patches (x86, arm64) since 2019-01-01
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
mkdir -p /root/work/pgdev
cd $REPO/experiments/case_taxonomy/patchguide_dev_20261109
python3 -B mine_patches.py mine /root/repos/linux 2019-01-01 /root/work/pgdev/patches_x86_arm64.json.gz arch/x86 arch/arm64
