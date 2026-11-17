#!/bin/bash
# Run reproducer.c as /init (via a small wrapper that powers off) on the base and patched kernels built by
# ../riscv_napot_clear_verify_20261101/build.sh. Logs go to logs/.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
W=/root/work/napot_verify
R=$W/repro_initramfs
mkdir -p "$HERE/logs" "$R/proc"
cat > "$W/repro_wrap.c" <<'C'
#include <stdio.h>
#include <sys/reboot.h>
#include <sys/wait.h>
#include <unistd.h>
int main(void)
{
	int st = 0;
	pid_t pid = fork();

	if (pid == 0) {
		execl("/reproducer", "reproducer", (char *)NULL);
		_exit(127);
	}
	waitpid(pid, &st, 0);
	printf("REPRO-EXIT %d\n", WEXITSTATUS(st));
	fflush(stdout);
	sync();
	reboot(RB_POWER_OFF);
	return 0;
}
C
riscv64-linux-gnu-gcc -static -O1 -Wall -I"$W/hdr/include" -o "$R/reproducer" "$HERE/reproducer.c"
riscv64-linux-gnu-gcc -static -O1 -Wall -o "$R/init" "$W/repro_wrap.c"
(cd "$R" && find . | cpio -o -H newc --quiet > "$W/repro.cpio")
sha256sum "$R/reproducer" "$W/repro.cpio"
for KIND in base patched; do
  timeout 600 qemu-system-riscv64 -machine virt -cpu rv64,svnapot=on -smp 2 -m 1G -nographic -no-reboot \
    -bios default -kernel "$W/out-$KIND/arch/riscv/boot/Image" -initrd "$W/repro.cpio" \
    -append "console=ttyS0 hugepagesz=64K hugepages=16 panic=-1 loglevel=1" > "$HERE/logs/$KIND.log" 2>&1 || true
  sed -i 's/\r$//' "$HERE/logs/$KIND.log"
  echo "== $KIND"; grep -a -E '^page|PASS|FAIL|REPRO-EXIT|perror|userfaultfd|mmap ' "$HERE/logs/$KIND.log" | tr '\n' ';'; echo
done
