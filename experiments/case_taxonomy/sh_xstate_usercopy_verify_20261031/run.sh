#!/bin/bash
# Build the sh kernels and initramfs lists of plan.md and run the three groups under qemu-system-sh4 -M r2d.
# WSL. Logs go to logs/ next to this script; build trees under /root/sh_verify.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
SRC=/root/.cache/linux-bug-analyze/kernel-facts/df2908090cda368b01ff43709f51890076c56157/linux
W=/root/sh_verify
mkdir -p "$W" "$HERE/logs"
CC=sh4-linux-gnu-gcc
$CC -static -O1 -o "$W/fpsig" "$HERE/fpsig.c"
$CC -static -O1 -DNO_FP -o "$W/nofp" "$HERE/fpsig.c"
for v in fpsig nofp; do
	printf 'dir /dev 755 0 0\nnod /dev/console 600 0 0 c 5 1\nfile /init %s 755 0 0\n' "$W/$v" > "$W/list_$v"
done

build() {  # $1 build dir name, $2 hardened usercopy (y/n), $3 initramfs list, $4 output image name
	local O="$W/$1"
	local MK=(make -C "$SRC" O="$O" ARCH=sh CROSS_COMPILE=sh4-linux-gnu- -j12)
	if [ ! -f "$O/.config" ]; then
		"${MK[@]}" rts7751r2dplus_defconfig > "$HERE/logs/$1.defconfig.log" 2>&1
	fi
	local CFG=("$SRC/scripts/config" --file "$O/.config" -e BLK_DEV_INITRD -e SLUB --set-str INITRAMFS_SOURCE "$3")
	if [ "$2" = y ]; then CFG+=(-e HARDENED_USERCOPY); else CFG+=(-d HARDENED_USERCOPY); fi
	"${CFG[@]}"
	"${MK[@]}" olddefconfig > /dev/null 2>&1
	"${MK[@]}" zImage > "$HERE/logs/$4.build.log" 2>&1
	cp "$O/arch/sh/boot/zImage" "$W/$4.zImage"
	grep -E '^(CONFIG_HARDENED_USERCOPY|CONFIG_SLUB|CONFIG_SH_FPU|CONFIG_CPU_SH4|CONFIG_INITRAMFS_SOURCE)=|HARDENED_USERCOPY is not set' "$O/.config" > "$HERE/logs/$4.config.txt"
}

build build_hu y "$W/list_fpsig" experiment
build build_hu y "$W/list_nofp" control1
build build_nohu n "$W/list_fpsig" control2

for g in experiment control1 control2; do
	timeout 120 qemu-system-sh4 -M r2d -kernel "$W/$g.zImage" \
		-append "console=ttySC1,115200 noiotrap panic=-1" \
		-serial null -serial stdio -display none -no-reboot -monitor none < /dev/null > "$HERE/logs/$g.console.log" 2>&1 || true
	echo "== $g"; grep -a -E 'FPSIG|usercopy|Kernel panic|BUG|Oops|kernel BUG' "$HERE/logs/$g.console.log" | head -12
done
