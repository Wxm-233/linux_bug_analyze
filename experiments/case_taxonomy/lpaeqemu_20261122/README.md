# QEMU 动态验证 arm LPAE 迁移项页帧号截断（lpaeqemu_20261122，第六轮）

2026-11-22，Claude。用户：“QEMU 验证 arm LPAE”。对象是第五轮（`pfnswap_20261121`）的候选。判据 `criteria.md`（2f9f3daf…）、修订 1 `criteria_amendment1.md`，都写于构建和运行之前。

## 结论

**确认。** 在 `df2908090cda` 的 arm LPAE 内核上（`multi_v7_defconfig` + LPAE，默认 flatmem），只要物理地址 64GB 以上有内存，这些页一参与迁移就会出错，出错方式与上游 2022 年修过的 x86 PAE 问题（`630dc25e43da`）相同：
- 拆分大页时，内核用迁移项临时替换页表项，迁移项里的页帧号被截掉高位（实测 0x1000a00 → 0xa00）；
- 拆分结束时对不上原来的页，**迁移项残留在页表里**；
- 之后读 `/proc/self/pagemap`、或者进程访问这些页，内核都按截断后的页帧号找页，触发 `include/linux/leafops.h:400` 的断言 `VM_WARN_ON_ONCE(!folio_test_locked(folio))`（使用迁移项时对应的页必须已加锁）。进程在 `migration_entry_wait` 里**永久卡死**，那块内存也再拿不回来。不开 `DEBUG_VM` 时没有任何告警，只会无声地卡死。

对照组（同一内核、同一程序，第二段内存放在 32GB，页帧号 < 2^24）一切正常。

**适用范围**：这里证明的是“内核在这种内存布局下会出错”。现实中有没有 ARM LPAE 平台在 64GB 以上放内存，仍然没找到（第五轮）。另外，开 sparsemem 时 arm 的 `MAX_PHYSMEM_BITS` 是 36，64GB 以上的内存根本不会被使用，所以问题只出在 flatmem（`multi_v7_defconfig` 的默认值）。

## 一、做法

- 内核：`multi_v7_defconfig` + `ARM_LPAE` + `VMSPLIT_2G` + THP + `DEBUG_FS` + `DEBUG_VM`，flatmem（`kernel_nohighpte.config`；另加 `EXPERT` 并关 `HIGHPTE`，原因见第三节）。只改配置，没改源码。构建 291 秒。
- QEMU 8.2：`-M virt,highmem=on -cpu cortex-a15 -m 64G`，内存后端是 64G 的稀疏文件（实际只占 387M～643M，跑完已删）。
- 内核参数 `mem=1G@0x40000000 mem=512M@<第二段>`：实验组第二段在 `0x1000000000`（64GB），对照组在 `0x800000000`（32GB）。启动日志里两组的 `System RAM` 和 `HighMem` 范围都与设定一致。
- `/init`（`init.c`，clang 编译，不依赖 libc，直接发系统调用）：挂载 proc/sys/debugfs，THP 设为 always，映射 8MB 匿名内存、对齐 2MB、`MADV_HUGEPAGE`，逐页写入可校验的内容；读 pagemap 和 kpageflags；向 `/sys/kernel/debug/split_huge_pages` 写 `<pid>,<起始>,<结束>` 强制拆分；再读 pagemap；逐页校验；关机。每一步之前先打印标记。

## 二、结果（`logs/run_nohighpte_ctrl.log`、`logs/run_nohighpte_test.log`）

| | 对照组（32GB） | 实验组（64GB） |
|---|---|---|
| 拆分前页帧号 | 0x800a00（< 2^24） | 0x1000a00（≥ 2^24） |
| 拆分前是否大页 | 是（kpageflags THP 位为 1，连续 512 页） | 是 |
| 拆分后 pagemap | 存在、页帧号不变、已不是大页 | **不存在，变成交换类条目**（`0x600000000001401e` 等） |
| 内核告警 | 无 | 读 pagemap 时：`WARNING: include/linux/leafops.h:400 at softleaf_to_page`（调用栈 `pagemap_read`→`pagemap_pmd_range`→`softleaf_to_page`） |
| 内容校验 | 1024 页全部正确 | 访问第一页即触发 `WARNING ... at softleaf_entry_wait_on_locked`（调用栈 `do_DataAbort`→`handle_mm_fault`→`do_swap_page`→`migration_entry_wait`），然后进程卡死 |
| 结束 | 正常关机 | 300 秒超时 |

残留条目的解码：pagemap 的交换项格式是低 5 位类型、往上是偏移。`0x1401e` 的类型是 30，即 `SWP_MIGRATION_WRITE`（这个配置下 `MAX_SWAPFILES` 是 28，三种迁移类型是 28～30）；偏移是 0xa00，正好是真实页帧号 0x1000a00 的低 24 位。第 1、511、512、1023 页的条目也一样，都是真实页帧号截掉高位后的值。这与第五轮逐位求值的预测（arm_lpae 从第 24 位开始丢失）完全一致。

## 三、过程中遇到的问题

1. **4GB 以上的用户页卡死（与本缺陷无关，单独记录）**。第一版内核（`kernel_base.config`，`HIGHPTE=y`）在“第二段内存只在 4GB 以上”的任何布局下，`/init` 一启动就卡住，包括页帧号远小于 2^24 的 4GB 布局。只有低端内存、3GB、5GB 连续内存（用户页实际落在 4GB 以下）都正常。卡住时从 QEMU 监视器读寄存器，PC 反复在 `handle_mm_fault`→`flush_tlb_page`，偶尔在 `arm_copy_to_user`，出错地址是用户栈顶：exec 时内核写用户栈，缺页处理后再访问又缺页，形成死循环。按修订 1 关掉 `HIGHPTE`（需要先开 `EXPERT`，否则这个选项不可见、强制为 y）后，4GB 布局正常，用户页确实在 4GB 以上（页帧号 0x100a00）。所以这个卡死与“用户页表页放在 4GB 以上”有关。是 QEMU 的问题还是内核的问题，本轮没有追；它发生在任何迁移之前，不影响上面的结论。
2. **`/dev/console` 缺失**：第一次 initramfs 里没有 `/dev/console`，`/init` 的输出全丢了，补上设备节点后正常。
3. **误操作（已恢复）**：为了检查 `/init` 程序本身，我在 WSL 里用用户态模拟器 `qemu-arm` 直接运行了它。用户态模拟器会把系统调用转给 WSL 自己的内核，所以程序以 root 身份在 WSL 上执行了：挂载（返回“已挂载”，没有重复挂载）、把 WSL 的 THP 设成 `always`、拆分自己进程的大页、调用关机（没有生效，WSL 从 09:35 起一直在运行）。WSL 内核默认是 `madvise`（`/proc/config.gz` 中 `TRANSPARENT_HUGEPAGE_MADVISE=y`），已改回 `madvise`。以后测试 guest 用的程序，只在 QEMU 系统模拟里运行。

## 四、意义

- 第五轮的静态结论（arm LPAE 的交换项编码只能保持 24 位页帧号，而 `SWP_PFN_BITS` 是 26）在真实内核代码路径上被证实，后果与上游已修的 x86 PAE 问题相同：迁移项残留、进程卡死。
- 2022 年的修复只改了公共层的 `SWP_PFN_BITS`，没有核对架构编码的容量；这个缺口在 arm LPAE（flatmem）上还在，本地最新主线 `65e4fd942f72` 也没改。mips32 XPA（23 位，32GB 以上）是同类情况，本轮没有验证（QEMU malta 放不了高端内存）。
- 可能的修法（没写补丁）：让 `SWP_PFN_BITS` 不超过架构交换项偏移的位数；或者在启动时发现 `max_pfn` 超过编码容量就告警，并且不使用超出部分的内存。

## 五、文件

- `criteria.md`、`criteria_amendment1.md`、`criteria_sha256.txt`
- `build.sh`（`TAG`、`EXTRA_CFG` 可选）、`kernel_base.config`、`kernel_nohighpte.config`、`logs/build.log`、`logs/build_nohighpte.log`、`logs/config_check.txt`
- `init.c`、`mkinit.sh`、`run.sh`（`K=<内核> run.sh test|ctrl`）、`probe_boot.sh`、`probe_regs.sh`
- 日志：`logs/run_nohighpte_test.log`、`logs/run_nohighpte_ctrl.log`（正式结果）；`logs/run_base_*.log`、`logs/probe_base_*.log`、`logs/probe_nohighpte_hi4g.log`、`logs/probe_regs*.txt|log`（诊断）
- WSL `/root/work/lpaeqemu/keep/`：`base/`、`nohighpte/`（各含 zImage、`.config`、`System.map`）、`init.cpio`，共 40M；构建目录和内存镜像都已删除

统计：模型调用 0；构建：arm LPAE 内核 3 次（第 2 次没关掉 `HIGHPTE`，作废）；QEMU 运行：正式 2 次，诊断 9 次。未联网，未对外报告。2026-11-22 用户要求登记，已登记为 `../../confirmed_bugs.md` B-2026-11-22-1。

## 复核后的更正（2026-11-22，`swaprev_20261122`）

Codex 审查本实验后的总评是“基本确认（有可补的漏洞）”，我同意以下几点，结论措辞据此收窄：
- “进程永久卡死”“那块内存再也拿不回来”应改为：**300 秒内没有完成**（退出码 124）；没有测量等待时长，也没有检查内存能否回收。
- “不开 `DEBUG_VM` 时只会无声卡死”是推断，**没有测过**。
- 日志没有直接记录清除迁移项时的匹配结果，也没有拆分后的原始页表项；“`remove_migration_ptes()` 对不上”是根据源码和 pagemap 输出推出来的。
- 对照组把第二段内存从 64GB 挪到 32GB，同时也改变了 flatmem `mem_map` 的跨度和 QEMU 访问的物理地址，不是只改页帧号。更硬的对照：同一次运行、同一段内存跨过 64GB，比较 2^24 两侧的页；同时逐步记录拆分前页帧号、编码往返值、清除时的比较结果和最终页表项。
- 结论只适用于关闭 `HIGHPTE` 的内核（交换项编码宏与 `HIGHPTE` 无关，静态结论不受影响）。
- 另：mips32 XPA 应为 16K 页、截断从 128GB 开始，在 Malta 配置上不可达（第四节“mips32 XPA（23 位，32GB 以上）是同类情况”一句作废）。
