#!/bin/bash
# ecrecall amendment 1 / criteria 三.1: header-only variants of the 20 builds at any revision. WSL root.
#   bash mkvariants.sh <rev>       -> /root/work/ecver/<rev12>/{src,cfg_<build>,status.txt}
# Each build reuses its df2908090cda .config (olddefconfig at <rev>), then make prepare + mm/memory.o; only .config, generated
# headers and mm/.memory.o.cmd are kept. The source copy (git archive) stays until the EC runs on this revision are done.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
REV=$(git -C $KSRC rev-parse --short=12 "$1")
W=/root/work/ecver/$REV
mkdir -p $W
if [ ! -f $W/src/Makefile ]; then rm -rf $W/src; mkdir -p $W/src; git -C $KSRC archive $REV | tar -x -C $W/src; fi
declare -A CFG=( [riscv64]=/root/work/boundary_build/riscv_defconfig [rv32_abi]=/root/work/boundary_build/closure_20261108_rv32_abi
  [x86_64]=/root/work/boundary_build/x86_64_defconfig [i386]=/root/work/wtrange/i386 [arm64]=/root/work/boundary_build/arm64_defconfig )
declare -A ARCHOF=( [riscv64]=riscv [rv32_abi]=riscv [x86_64]=x86 [i386]=i386 [i386_pae]=i386 [arm64]=arm64 [ppc64le]=powerpc
  [ppc64le_hash]=powerpc [ppc64e]=powerpc [ppc32s]=powerpc [ppc44x]=powerpc [ppc8xx]=powerpc [s390]=s390 [loongarch]=loongarch
  [mips32]=mips [mips32xpa]=mips [mips64]=mips [arm]=arm [arm_lpae]=arm [hexagon]=hexagon )
BUILDS="riscv64 rv32_abi x86_64 i386 i386_pae arm64 ppc64le ppc64le_hash ppc64e ppc32s ppc44x ppc8xx s390 loongarch mips32 mips32xpa mips64 arm arm_lpae hexagon"
one() {
  b=$1; a=${ARCHOF[$b]}; src=${CFG[$b]:-/root/work/swapsym/cfg_$b}
  out=$W/cfg_$b; rm -rf $out; mkdir -p $out
  srcarch=$a; [ $a = i386 ] && srcarch=x86
  if [ ! -d $W/src/arch/$srcarch ]; then echo "$b skip: no arch/$srcarch at $REV"; rm -rf $out; return; fi
  cp $src/.config $out/.config
  cd $W/src
  if ! make O=$out ARCH=$a LLVM=1 olddefconfig > $out/config.log 2>&1; then echo "$b fail: olddefconfig $(tail -1 $out/config.log)"; return; fi
  if ! make O=$out ARCH=$a LLVM=1 -j5 prepare > $out/prepare.log 2>&1; then echo "$b fail: prepare $(grep -m1 -iE 'error' $out/prepare.log | cut -c1-200)"; return; fi
  if ! make O=$out ARCH=$a LLVM=1 -j5 mm/memory.o > $out/memory.log 2>&1; then echo "$b fail: memory.o $(grep -m1 -iE 'error' $out/memory.log | cut -c1-200)"; return; fi
  find $out -type f \( -name '*.o' -o -name '*.d' -o -name '*.a' -o -name '*.tmp' -o -name 'modules.order' -o -name '*.symvers' \) -delete
  find $out -type f -name '.*.cmd' ! -path "$out/mm/.memory.o.cmd" -delete
  find $out/scripts $out/tools -type f -exec sh -c 'head -c4 "$1" | grep -q "ELF" && rm -f "$1"' _ {} \; 2>/dev/null
  find $out -type d -empty -delete
  echo "$b ok $(du -sh $out | cut -f1)"
}
export -f one; export W REV
start=$(date +%s)
: > $W/status.txt
for b in $BUILDS; do
  while [ $(jobs -r | wc -l) -ge 4 ]; do sleep 2; done
  ( one $b >> $W/status.txt ) &
done
wait
echo "secs $(( $(date +%s) - start ))" >> $W/status.txt
sort $W/status.txt
du -sh $W/src $W
