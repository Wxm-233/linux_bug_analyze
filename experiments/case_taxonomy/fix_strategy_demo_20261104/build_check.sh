#!/bin/bash
# Checks 1 and 2 of criteria.md section 2: every patch applies to df2908090cda on its own; the touched RISC-V and MIPS
# objects build before and after the patches (warnings compared). WSL; no model calls.
cd "$(dirname "$0")" || exit 1
WT=/root/fixdemo_wt; OUT=$PWD/build; mkdir -p $OUT
FINAL=$(git -C $WT rev-parse HEAD)
git -C $WT checkout -q --detach df2908090cda
for p in patches/D*.patch; do git -C $WT apply --check $PWD/$p && echo "apply $p ok" || echo "apply $p FAIL"; done > $OUT/apply.log
RV="arch/riscv/mm/hugetlbpage.o arch/riscv/kernel/machine_kexec.o arch/riscv/kernel/smp.o arch/riscv/kvm/gstage.o arch/riscv/kvm/mmu.o arch/riscv/kvm/vcpu_pmu.o"
MP="arch/mips/kernel/setup.o arch/mips/kvm/vz.o"
cfg() {  # $1 arch dir, $2 make args
  make -C $WT O=/root/fixdemo_build/$1 $2 $3 > $OUT/$1_config.log 2>&1
  $WT/scripts/config --file /root/fixdemo_build/$1/.config $4
  make -C $WT O=/root/fixdemo_build/$1 $2 olddefconfig >> $OUT/$1_config.log 2>&1
}
cfg riscv "ARCH=riscv CROSS_COMPILE=riscv64-linux-gnu-" defconfig "-e KVM -e KEXEC_FILE -e HOTPLUG_CPU -e HUGETLBFS -e RISCV_ISA_SVNAPOT"
cfg mips "ARCH=mips CROSS_COMPILE=mips-linux-gnu-" malta_kvm_defconfig "-e JUMP_LABEL -e KVM"
for stage in base patched; do
  [ $stage = patched ] && git -C $WT checkout -q --detach $FINAL
  make -C $WT O=/root/fixdemo_build/riscv ARCH=riscv CROSS_COMPILE=riscv64-linux-gnu- -j8 $RV > $OUT/riscv_$stage.log 2>&1; echo "riscv $stage exit $?"
  make -C $WT O=/root/fixdemo_build/mips ARCH=mips CROSS_COMPILE=mips-linux-gnu- -j8 $MP > $OUT/mips_$stage.log 2>&1; echo "mips $stage exit $?"
done
grep -E "^CONFIG_(KVM|KEXEC_FILE|HOTPLUG_CPU|HUGETLBFS|RISCV_ISA_SVNAPOT|JUMP_LABEL|64BIT|KVM_MIPS_VZ|CPU_MIPSR[26])=" /root/fixdemo_build/riscv/.config /root/fixdemo_build/mips/.config
