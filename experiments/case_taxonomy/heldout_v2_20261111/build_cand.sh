# Builds for one holdout candidate (criteria 四). Runs in WSL.  Stages run in the order given:
#   bash build_cand.sh <group> <parent> <fix> <stage>...
#   src     export the parent revision (git archive; the repository work tree is not touched)
#   la      LoongArch 64-bit defconfig, LLVM=1            -> b_la/   (pre-fix kernel)
#   cc      compile_commands.json of b_la
#   arm64   arm64 defconfig                                  -> b_arm64/
#   x86     x86_64_defconfig                                 -> b_x86/
#   save    copy the three pre-fix images and .config to kernels/<group>/
#   fix     apply `git diff parent fix` to the exported tree (not read), rebuild b_la incrementally, save as *_fix
#   keep    (added 2026-11-11, before the run) keep what later work needs without rebuilding, in keep/<group>/:
#           compile databases of the three build trees and each tree minus objects and images ("skeleton": .config,
#           generated headers and sources, .cmd files) -> restore_cand.sh rebuilds a tree the static pipeline can use
#   clean   remove the source copy and all build trees (images, vmlinux, configs stay in kernels/<group>/, keep/<group>/)
# Each stage appends "<stage> OK|FAILED <seconds>s ..." to logs/<group>.build.log in this directory.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
g=$1; parent=$2; fix=$3; shift 3
R=$REPO/experiments/case_taxonomy/heldout_v2_20261111
W=/root/work/heldout_run/$g; S=$W/src; K=/root/work/heldout_run/kernels/$g; p=$(echo $g | tr A-Z a-z)
mkdir -p $W $K $R/logs; LOG=$R/logs/$g.build.log
# 2026-11-11 infrastructure fix: from 2025 on the default LoongArch target also makes vmlinuz.efi compressed with zstd,
# which is not installed here (L04, L05 failed on it). Build the targets the test uses instead of `all`: the image
# booted (vmlinux.efi, unchanged) and the modules; only the compressed boot image is no longer made.
LA_TARGETS="vmlinux.efi modules"
rec() { echo "$1 $2 $3s ${4:-}" | tee -a $LOG; }
mk() { local o=$1 a=$2; shift 2; make -C $S O=$W/$o ARCH=$a LLVM=1 "$@"; }
for st in "$@"; do
  t0=$(date +%s)
  case $st in
    src)  rm -rf $S; mkdir -p $S
          if git -C $KSRC archive --format=tar $parent | tar -x -C $S; then rec src OK $(( $(date +%s)-t0 )) "$parent $(du -sh $S | cut -f1)"; else rec src FAILED $(( $(date +%s)-t0 )); exit 1; fi ;;
    la)   mkdir -p $W/b_la
          # amendment 1: the 64-bit default config of that revision (loongson3_defconfig before 2025-12)
          dc=loongson64_defconfig; [ -f $S/arch/loongarch/configs/$dc ] || dc=loongson3_defconfig
          echo "defconfig $dc" > $W/b_la.cfg.log
          mk b_la loongarch $dc >> $W/b_la.cfg.log 2>&1 && mk b_la loongarch -j20 $LA_TARGETS > $W/b_la.log 2>&1 \
            && [ -f $W/b_la/arch/loongarch/boot/vmlinux.efi ] && rec la OK $(( $(date +%s)-t0 )) "$dc" \
            || { rec la FAILED $(( $(date +%s)-t0 )) "$(grep -a -m3 'error' $W/b_la.log | tr '\n' ' ' | cut -c1-400)"; exit 1; } ;;
    cc)   (cd $S && python3 scripts/clang-tools/gen_compile_commands.py -d $W/b_la -o $W/compile_commands.json) > $W/cc.log 2>&1 \
            && rec cc OK $(( $(date +%s)-t0 )) "$(python3 -c "import json;print(len(json.load(open('$W/compile_commands.json'))))") units" \
            || { rec cc FAILED $(( $(date +%s)-t0 )); exit 1; } ;;
    arm64) mkdir -p $W/b_arm64; mk b_arm64 arm64 defconfig > $W/b_arm64.cfg.log 2>&1 && mk b_arm64 arm64 -j20 Image > $W/b_arm64.log 2>&1 \
            && rec arm64 OK $(( $(date +%s)-t0 )) || { rec arm64 FAILED $(( $(date +%s)-t0 )) "$(grep -a -m3 'error' $W/b_arm64.log | tr '\n' ' ' | cut -c1-400)"; exit 1; } ;;
    x86)  mkdir -p $W/b_x86; mk b_x86 x86_64 x86_64_defconfig > $W/b_x86.cfg.log 2>&1 && mk b_x86 x86_64 -j20 bzImage > $W/b_x86.log 2>&1 \
            && rec x86 OK $(( $(date +%s)-t0 )) || { rec x86 FAILED $(( $(date +%s)-t0 )) "$(grep -a -m3 'error' $W/b_x86.log | tr '\n' ' ' | cut -c1-400)"; exit 1; } ;;
    save) cp $W/b_la/arch/loongarch/boot/vmlinux.efi $K/${p}_pre.efi; cp $W/b_la/.config $K/${p}_pre.config
          cp $W/b_la/vmlinux $K/${p}_pre.vmlinux; cp $W/b_la/System.map $K/${p}_pre.System.map
          [ -d $W/b_arm64 ] && { cp $W/b_arm64/arch/arm64/boot/Image $K/${p}_ref_arm64.Image; cp $W/b_arm64/.config $K/${p}_ref_arm64.config
                                 cp $W/b_arm64/vmlinux $K/${p}_ref_arm64.vmlinux; cp $W/b_arm64/System.map $K/${p}_ref_arm64.System.map; }
          [ -d $W/b_x86 ] && { cp $W/b_x86/arch/x86/boot/bzImage $K/${p}_ref_x86_64.bzImage; cp $W/b_x86/.config $K/${p}_ref_x86_64.config
                               cp $W/b_x86/vmlinux $K/${p}_ref_x86_64.vmlinux; cp $W/b_x86/System.map $K/${p}_ref_x86_64.System.map; }
          rec save OK $(( $(date +%s)-t0 )) "$(ls $K | tr '\n' ' ')" ;;
    fix)  git -C $KSRC diff --binary $parent $fix > $W/fix.diff
          if (cd $S && git apply --whitespace=nowarn $W/fix.diff) > $W/fix_apply.log 2>&1 && mk b_la loongarch -j20 $LA_TARGETS > $W/b_la_fix.log 2>&1 \
             && cp $W/b_la/arch/loongarch/boot/vmlinux.efi $K/${p}_fix.efi && cp $W/b_la/.config $K/${p}_fix.config              && cp $W/b_la/vmlinux $K/${p}_fix.vmlinux && cp $W/b_la/System.map $K/${p}_fix.System.map; then
            rec fix OK $(( $(date +%s)-t0 )) "files=$(grep -c '^diff --git' $W/fix.diff) rebuilt=$(grep -c ' CC ' $W/b_la_fix.log)"
          else rec fix FAILED $(( $(date +%s)-t0 )) "$(tail -3 $W/fix_apply.log $W/b_la_fix.log | tr '\n' ' ' | cut -c1-400)"; exit 1; fi
          rm -f $W/fix.diff ;;
    keep) KP=/root/work/heldout_run/keep/$g; mkdir -p $KP; echo "$parent $fix" > $KP/revs.txt; ok=1
          for b in b_la b_arm64 b_x86; do
            [ -d $W/$b ] || continue
            (cd $S && python3 scripts/clang-tools/gen_compile_commands.py -d $W/$b -o $KP/cc_$b.json) >> $W/keep.log 2>&1 || ok=0
            tar -C $W/$b --exclude='*.o' --exclude='*.a' --exclude='*.ko' --exclude='vmlinux*' --exclude='.tmp_*'                 --exclude='*.efi' --exclude='Image*' --exclude='bzImage' --exclude='*.bin' --exclude='*.elf'                 --exclude='*.gz' --exclude='*.xz' --exclude='*.zst' --exclude='*.lz4' --exclude='*.lzo' --exclude='*.lzma'                 -cf - . 2>> $W/keep.log | xz -T0 -3 > $KP/skel_$b.tar.xz || ok=0
          done
          [ $ok = 1 ] && rec keep OK $(( $(date +%s)-t0 )) "$(du -sh $KP | cut -f1) $(ls $KP | tr '
' ' ')"             || { rec keep FAILED $(( $(date +%s)-t0 )) "$(tail -3 $W/keep.log | tr '
' ' ')"; exit 1; } ;;
    clean) rm -rf $W; rec clean OK $(( $(date +%s)-t0 )) "$(du -sh $K | cut -f1)" ;;
    *) echo "unknown stage $st"; exit 2 ;;
  esac
done
