# widthtrunc2 第二标注人盲判说明

日期：2026-11-17。只依据用户列出的 review.txt、criteria.md、上一轮 samples.md / widths.md、本目录的源码读取脚本，以及该脚本指定的只读内核源码进行判断。未读取其他标注、裁定、轮次 README、head.json、交接文档、进度日志或 confirmed_bugs.md；未调用其他模型、联网、安装或构建。

- 判据 SHA256（写入判断前取得）：`96ed2fef5b620aa3955b8c27833c778f69bf9e0fc0bfee5cd254e065ea96e4d9`。
- 内核源码版本：读取脚本固定的 `df2908090cda`，未读取轮次的 head.json。
- 结果：30 项，可能 12、不可能 15、说不清 3。
- 所有判断均为静态审查；动态触发、复现成功率和运行结果数字均为 `null`。

## 需保留的条件与判断边界

1. **2～4：CLST 不是无条件的 u64。** `fs/ntfs3/ntfs.h:73` 的类型分支和 `fs/ntfs3/Kconfig:18` 的依赖表明，32 位内核只能用 u32 CLST。`ntfs_fs.h:766`、`:768` 的读函数也确实接收 CLST。这三项排除的是报告声称的“窄位移结果转为 64 位”，不据此声称所有超大 NTFS 索引都不存在其他固定 u32 限制；上一轮 samples.md 本身已排除各架构相同的 u32 截断。

2. **6：统计对象不只实际 RAM。** `mm/util.c:959` 的 `__vm_enough_memory` 先计入承诺量，再在 OVERCOMMIT_ALWAYS 下直接允许；`:937` 返回跨进程汇总。4 KiB 页下 4 TiB 承诺量为 2^30 页，页数自身仍可表示，但转成 kB 时已需第 33 位。

3. **7：两条 offset 来源都受限。** `include/linux/xarray.h:49`、`swapops.h:28`、`:106` 给出 32 位时的 26 位 offset；`leafops.h:378` 的 PFN 提取仍先取 swp_offset。不能直接以物理地址可能很大推断本行移位溢出。

4. **9：编译与可执行不同。** 公共 arena.c 可编译，实际 map 创建却在 `arena.c:274` 按 JIT 支持拒绝。弱实现 `kernel/bpf/core.c:3300` 返回 false；支持函数所在的 x86、RISC-V 等 JIT 为 64 位路径，PowerPC 的实现显式检查 PPC64。

5. **11：单个高偏移探针可能被回退救回。** `uprobes.c:2473` 在推测查找返回 NULL 后走加锁路径，后者使用先扩宽再移位的 `vaddr_to_offset`。所以判“可能”的条件明确要求同一 inode 的低、高对应偏移均有探针；推测查找命中错误的低探针后不会回退。i386 可同时支持 UPROBES、SMP 和 PER_VMA_LOCK。

6. **12 与 13～14 不同。** 第一个低端块有完整 u64 相等检查，不能用高位恰好相同的低 32 位绕过。第二个块没有相等检查或范围裁剪；`drivers/of/fdt.c:1068` 用 u64 传入，通用弱实现 `:1175` 会拒绝超出 phys_addr_t 的起点，但 ARC 覆盖实现没有此检查。ARC 的 HIGHMEM 可独立启用；`arch/arc/mm/tlb.c:654`、`:663` 允许硬件有 PAE40 而配置未启用。13～14 的判断以这种配置仍收到高端 DT 块为条件，并不声称 PAE40=y 时也截断。

7. **15～17 的配置和值域证据。** `kernel/crash_reserve.c:350` 先拒绝 crash_size>=system_ram；ARM_LPAE 又选择 64 位 phys_addr_t。非零 idmap 别名在该树中由 Keystone 的 pv_fixup 写入，激活调用位于 `arch/arm/mm/mmu.c:1614` 开始的 ARM_PV_FIXUP 条件路径；此选项依赖 ARM_LPAE。resource_size_t 是 phys_addr_t 的别名，不能无条件视作 32 位。

8. **18 与 19～21 的可见信息不同。** 18 另有真正的 64 位 st_ino，低位兼容副本不使 inode 号信息消失。19～21 的时间字段没有 64 位副本，time64 秒数 0x100000001 会成为 1；`fs/ext4/ext4.h:898`、`:905` 的扩展时间戳可表示这种秒数。按用户本次“截断且结果出错”的定义判可能，同时明确这是既有 time32 ABI 的范围限制，不能将这三项宣传为新发现的内部计算缺陷；没有额外添加“全部 ABI 转换一律排除”的判据。

9. **22～23 的高位不参与所报操作。** `include/linux/dma-direct.h:57` 的 dma_range_map_min 返回 dma_addr_t，解释了 u64 临时量的实际值域。`arch/arm/mm/flush.c:38`、`asm/cacheflush.h:17` 和 `asm/shmparam.h:10` 则表明缓存颜色只依赖 4 个页面内的低位。

10. **25～29 不能按旧有的“LoongArch 仅有 64 位”印象判断。** 该版本 `arch/loongarch/Kconfig:226` 已有 32BIT，kernel/Makefile 将 mem.o、time.o 列为 obj-y；但 `asm/cpu-features.h:22` 在该模式把物理地址最高位设为 31。25～27 的 EFI 字段本身为 u64，导入路径中未找到高起点裁剪，数学上的截断和错误区间可以明确描述；尚缺可运行 LA32 启动图中实际出现这种描述的证据，也不能从地址接口的 32 位限制直接推导固件输入已被裁剪，故三项保留“说不清”。28 中 `cpu-probe.c:141` 无条件设置 CPUCFG 支持位，实际选择的 `calc_const_freq` 返回 unsigned int，这才是频率不超过 32 位的依据；最终全赋值点检查还发现了 SMBIOS 的 cpu_clock_freq 赋值，没有把它遗漏后错误地声称所有回退来源都有同样的值域保证。29 的 HUGETLB 开关链则只允许 64 位。

## 复查方式与未验证项

源码读取均使用现有脚本的 `show <文件> <起:止>` 和 `grep64 <正则的 base64> <内核路径>` 模式，由 PowerShell 前台调用 `wsl -u root -- bash .../codex_blind/read_source.sh ...`。脚本只对 `/root/repos/linux` 执行固定版本的 git show / git grep。

交付前只核验 JSON 的可解析性、30 个连续且唯一的编号、全部 loc 与 review.txt 的对应关系、三个合法 verdict、每项字段完整，以及判据哈希未改变。没有运行候选代码或制作触发文件；25～27 所需的 LA32/EFI 可达性证据仍未取得。下一步由主流程在盲判文件完成后统一裁定，本次不读取或生成 adjudication。
