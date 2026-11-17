# 环境安装记录（用户 2026-11-10 同意后进行）

判据第四节写的是“本轮不安装软件、不联网”，第三之二节写明安装方案交用户决定。用户看过方案后回复“同意安装和下载”，于是我做了下面两件事。这不是判据修订，只是记录来源，方便复现。

1. **编译器和 C 库**（WSL，Ubuntu 24.04 官方源，apt）：`gcc-14-loongarch64-linux-gnu` 14.2.0-4ubuntu2~24.04cross1、`libc6-dev-loong64-cross` 2.39-0ubuntu8.2cross1（glibc 2.39，与另外三个架构的交叉 C 库同版本）。命令：`loongarch64-linux-gnu-gcc-14`。
2. **固件**：Debian 13 官方源的 `qemu-efi-loongarch64_2025.02-8+deb13u1_all.deb`，SHA256 `2a1bd3b00413af313d6105f38bda3f8156be514f5026f3ec29ba8e81b68f0633`，与 Debian 的 `Packages` 索引一致。只用 `dpkg-deb -x` 解包到 `/root/work/heldout/fw`，没有安装进系统。

## QEMU 8.2 上的用法

- 8.2 的 LoongArch `virt` 机器没有 pflash，`-bios` 窗口只有 4MiB；固件文件 16MiB，但实际数据不到 2MiB。取前 4MiB 存为 `/root/work/heldout/boot/QEMU_EFI_4M.fd`，用 `-bios` 加载；
- 内核用 `-kernel arch/loongarch/boot/vmlinux.efi`（由固件加载），`-initrd`、`-append` 照常；
- 内存至少 1G（另外三个架构仍是 512M，这是一处无法消除的环境差异）；
- 控制台 `console=ttyS0,115200`。

## 验证

- `boot_test/boot_fw_kernel.sh`：最小 init 打印 `@@LA BOOT OK` 并正常关机，约 4 秒；
- `harness/selftest_la.sh`：执行器 v2（glibc 静态链接，加载地址 0x400000）在当前版本 LoongArch 内核上跑 casemodel 轮的 19 个自测用例（用 riscv 的用例文件，两者都用通用调用号）：19 个都有结果，18 个与 riscv 的记录逐字段相同，剩下 1 个是 `getpid()`，进程号 85 对 46，属于预期内的差别；无 `harness_error`，taint 未变。日志 `harness/selftest_la.log`。
