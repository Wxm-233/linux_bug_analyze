# Restore one holdout candidate for later static work, without building (added 2026-11-11). Runs in WSL.
#   bash restore_cand.sh <group> [pre|fix] [<dest>]
# Puts back, at the same paths the kept compile databases point to (default dest /root/work/heldout_run/<group>):
#   src/                 git archive of the parent revision (with `fix`: the fix diff applied, not printed)
#   b_la/ b_arm64/ b_x86/  skeletons from keep/<group>/skel_*.tar.xz (.config, generated headers/sources, .cmd files)
#   compile_commands.json  = keep/<group>/cc_b_la.json (cc_b_arm64.json / cc_b_x86.json stay in keep/<group>/)
# The skeletons have no object files: enough for the static pipeline (extract3, macro_values, layouts, ...), not for
# an incremental `make`. Kernel images, vmlinux and System.map are in /root/work/heldout_run/kernels/<group>/.
# A dest other than the default breaks the absolute paths in the compile databases; use it only for inspection.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
g=$1; mode=${2:-pre}; KP=/root/work/heldout_run/keep/$g; W=${3:-/root/work/heldout_run/$g}
[ -f $KP/revs.txt ] || { echo "no keep/$g"; exit 1; }
read parent fix < $KP/revs.txt
[ -e $W/src ] && { echo "$W/src exists; remove it first"; exit 1; }
mkdir -p $W/src
git -C $KSRC archive --format=tar $parent | tar -x -C $W/src
if [ "$mode" = fix ]; then git -C $KSRC diff --binary $parent $fix | (cd $W/src && git apply --whitespace=nowarn); fi
for b in b_la b_arm64 b_x86; do
  [ -f $KP/skel_$b.tar.xz ] || continue
  mkdir -p $W/$b; xz -dc -T0 $KP/skel_$b.tar.xz | tar -x -C $W/$b
done
cp $KP/cc_b_la.json $W/compile_commands.json
echo "restored $g ($mode, $parent) to $W: $(du -sh $W | cut -f1)"
