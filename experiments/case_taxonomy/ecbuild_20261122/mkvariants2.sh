#!/bin/bash
# ecbuild criteria 二: header-only variants of the 20 builds at any revision, with the old-tree fixes. WSL root.
#   bash mkvariants2.sh <rev>   -> /root/work/ecver/<rev12>/{src,cfg_<build>,status.txt}
# Changes against ecrecall_20261122/mkvariants.sh:
#   1. CROSS_COMPILE=<triple>- and LLVM_IAS=1 (old trees derive clang's --target from CROSS_COMPILE); a shim directory on PATH gives
#      <triple>-ld for triples without GNU binutils, and LD is a wrapper of ld.lld that drops -fPIC (s390 vdso passes it to LD);
#   2. identity options checked after olddefconfig, one known old-Kconfig dependency fixed (X86_PAE <- HIGHMEM64G), else "config mismatch".
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
REV=$(git -C $KSRC rev-parse --short=12 "$1")
W=/root/work/ecver/$REV
SHIM=/root/work/ecver/shim
mkdir -p $W $SHIM
cat > $SHIM/ld.lld-wrap <<'EOS'
#!/bin/bash
a=(); for x in "$@"; do [ "$x" = -fPIC ] || a+=("$x"); done
exec ld.lld "${a[@]}"
EOS
chmod +x $SHIM/ld.lld-wrap
for t in powerpc64le-linux-gnu powerpc64-linux-gnu powerpc-linux-gnu arm-linux-gnueabi hexagon-linux-musl mips64el-linux-gnuabi64 mipsel-linux-gnu; do
  command -v $t-ld >/dev/null 2>&1 && [ ! -L $SHIM/$t-ld ] || ln -sf $SHIM/ld.lld-wrap $SHIM/$t-ld
done
export PATH=$SHIM:$PATH
if [ ! -f $W/src/Makefile ]; then rm -rf $W/src; mkdir -p $W/src; git -C $KSRC archive $REV | tar -x -C $W/src; fi
declare -A CFG=( [riscv64]=/root/work/boundary_build/riscv_defconfig [rv32_abi]=/root/work/boundary_build/closure_20261108_rv32_abi
  [x86_64]=/root/work/boundary_build/x86_64_defconfig [i386]=/root/work/wtrange/i386 [arm64]=/root/work/boundary_build/arm64_defconfig )
declare -A ARCHOF=( [riscv64]=riscv [rv32_abi]=riscv [x86_64]=x86 [i386]=i386 [i386_pae]=i386 [arm64]=arm64 [ppc64le]=powerpc
  [ppc64le_hash]=powerpc [ppc64e]=powerpc [ppc32s]=powerpc [ppc44x]=powerpc [ppc8xx]=powerpc [s390]=s390 [loongarch]=loongarch
  [mips32]=mips [mips32xpa]=mips [mips64]=mips [arm]=arm [arm_lpae]=arm [hexagon]=hexagon )
declare -A CROSS=( [riscv64]=riscv64-linux-gnu- [rv32_abi]=riscv64-linux-gnu- [x86_64]= [i386]= [i386_pae]= [arm64]=aarch64-linux-gnu-
  [ppc64le]=powerpc64le-linux-gnu- [ppc64le_hash]=powerpc64le-linux-gnu- [ppc64e]=powerpc64-linux-gnu- [ppc32s]=powerpc-linux-gnu-
  [ppc44x]=powerpc-linux-gnu- [ppc8xx]=powerpc-linux-gnu- [s390]=s390x-linux-gnu- [loongarch]=loongarch64-linux-gnu-
  [mips32]=mips-linux-gnu- [mips32xpa]=mips-linux-gnu- [mips64]=mips64el-linux-gnuabi64- [arm]=arm-linux-gnueabi-
  [arm_lpae]=arm-linux-gnueabi- [hexagon]=hexagon-linux-musl- )
declare -A IDENT=( [i386_pae]="X86_PAE" [arm_lpae]="ARM_LPAE" [mips32xpa]="XPA" [ppc44x]="44x" [ppc8xx]="PPC_8xx" [ppc64e]="PPC_BOOK3E_64 64BIT"
  [ppc32s]="PPC_BOOK3S_32" [ppc64le]="PPC_BOOK3S_64 64BIT" [ppc64le_hash]="PPC_BOOK3S_64 64BIT !PPC_RADIX_MMU" [rv32_abi]="32BIT"
  [riscv64]="64BIT" [x86_64]="64BIT" [arm64]="64BIT" [s390]="64BIT" [loongarch]="64BIT" [mips64]="64BIT" [i386]="!64BIT" [mips32]="32BIT" )
BUILDS="riscv64 rv32_abi x86_64 i386 i386_pae arm64 ppc64le ppc64le_hash ppc64e ppc32s ppc44x ppc8xx s390 loongarch mips32 mips32xpa mips64 arm arm_lpae hexagon"
ident_ok() {   # $1 config file, rest: options ("!X" = must be off)
  f=$1; shift
  for o in "$@"; do
    if [ "${o:0:1}" = "!" ]; then grep -q "^CONFIG_${o:1}=y" $f && return 1
    else grep -q "^CONFIG_$o=y" $f || return 1; fi
  done
  return 0
}
one() {
  b=$1; a=${ARCHOF[$b]}; src=${CFG[$b]:-/root/work/swapsym/cfg_$b}
  out=$W/cfg_$b; rm -rf $out; mkdir -p $out
  srcarch=$a; [ $a = i386 ] && srcarch=x86
  if [ ! -d $W/src/arch/$srcarch ]; then echo "$b skip: no arch/$srcarch at $REV"; rm -rf $out; return; fi
  cp $src/.config $out/.config
  cd $W/src
  IAS=1; [ $b = s390 ] && IAS=0            # amendment 1: GNU as for s390 (old inline asm)
  MK="make O=$out ARCH=$a LLVM=1 LLVM_IAS=$IAS CROSS_COMPILE=${CROSS[$b]} LD=$SHIM/ld.lld-wrap"
  MK="$MK KCFLAGS=-Wno-error=implicit-function-declaration"   # amendment 1
  if ! $MK olddefconfig > $out/config.log 2>&1; then echo "$b fail: olddefconfig $(grep -m1 -E 'error|Error' $out/config.log | cut -c1-200)"; return; fi
  if ! ident_ok $out/.config ${IDENT[$b]}; then
    if [ $b = i386_pae ]; then scripts/config --file $out/.config -e HIGHMEM64G -e X86_PAE; $MK olddefconfig >> $out/config.log 2>&1; fi
    if ! ident_ok $out/.config ${IDENT[$b]}; then echo "$b mismatch: identity options ${IDENT[$b]} not satisfied after olddefconfig"; return; fi
    echo "$b note: identity fixed (HIGHMEM64G)" >> $out/config.log
  fi
  if ! $MK -j5 prepare > $out/prepare.log 2>&1; then echo "$b fail: prepare $(grep -m1 -E 'error:|Error [0-9]' $out/prepare.log | cut -c1-200)"; return; fi
  if ! $MK -j5 mm/memory.o > $out/memory.log 2>&1; then echo "$b fail: memory.o $(grep -m1 -E 'error:|Error [0-9]' $out/memory.log | cut -c1-200)"; return; fi
  find $out -type f \( -name '*.o' -o -name '*.d' -o -name '*.a' -o -name '*.tmp' -o -name 'modules.order' -o -name '*.symvers' \) -delete
  find $out -type f -name '.*.cmd' ! -path "$out/mm/.memory.o.cmd" -delete
  find $out/scripts $out/tools -type f -exec sh -c 'head -c4 "$1" | grep -q "ELF" && rm -f "$1"' _ {} \; 2>/dev/null
  find $out -type d -empty -delete
  echo "$b ok $(du -sh $out | cut -f1) $(grep -q 'identity fixed' $out/config.log 2>/dev/null && echo '(identity fixed)')"
}
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
