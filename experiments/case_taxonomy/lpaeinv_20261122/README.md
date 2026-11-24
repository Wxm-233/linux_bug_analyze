# QEMU 验证 arm LPAE `pmd_mkinvalid` 不满足通用约定（lpaeinv_20261122）

2026-11-22，Claude。用户：“先用 QEMU 验证”。对象是编码一致性引擎第三轮（`ecnoise_20261122` 第三节）的新线索。判据 `criteria.md`（adca0fbb…），修订 1（pagemap 口径，写于第一次运行前）、修订 2（加长时间，写于第一次运行后、第二次运行前）。

## 结论

- **Q1 约定违反：在运行时确认。**让 arm LPAE 跑公共层自测 `debug_vm_pgtable`，启动时 `mm/debug_vm_pgtable.c:929`（`pmd_present(pmd_mkinvalid(pmd_mkhuge(pmd)))`）和 `:930`（`pmd_leaf(...)`）都报 WARNING，`:928`（`pmd_trans_huge`）不报。两次启动结果相同，自测的其余检查没有报警。与静态结论逐条一致。
- **Q2 后果：没有观察到。**THP 拆分与并发缺页、远程读（GUP）、pagemap 读、重新合并交错跑 480 秒，PMD 拆分 8332 次、`MADV_COLLAPSE` 成功 1229 次（覆盖要求都满足），**0 异常**：拥有者和远程读者的逐页校验都对，`process_vm_readv` 没有一次出错或短读，pagemap 没有出现“既不在场也不是交换项”的条目，压力期间控制台没有任何告警。
- **怎么理解**：这是一个确定存在、但目前看不出危害的约定违反。arm 的 `pmd_trans_huge` 在失效后仍为真，而现在的公共代码在拆分窗口里读到“不在场”的 PMD 时，大多只是让调用者重试（缺页返回 0、GUP 走 `no_page_table`、`__pte_offset_map` 不映射），或者先查 `pmd_trans_huge` 再加锁。2012 年 x86 修这条约定时要解决的竞争（`027ef6c87853`），在现在的代码路径上没有复现出来。Q2 只说明测过的这些路径上没看到问题，不能证明没有后果。
- **影响**：如果 arm LPAE 启用公共自测（`ARCH_HAS_DEBUG_VM_PGTABLE`），这两条断言会失败；arm64（`b65399f6111b`）、loongarch（`ddc1729b07cc`）都已按这条约定改过。适合当作“语义不一致、自测会失败”的低危问题，而不是会导致数据错误的缺陷。未登记、未对外报告。

## 一、做法

- 内核：第六轮 `nohighpte` 配置（`multi_v7_defconfig` + LPAE + VMSPLIT_2G + THP always + DEBUG_FS + DEBUG_VM，EXPERT，关 HIGHPTE）+ `DEBUG_VM_PGTABLE`。源码用 `git archive df2908090cda` 导出，唯一改动是 `arch/arm/Kconfig` 加 `select ARCH_HAS_DEBUG_VM_PGTABLE if ARM_LPAE`（`logs/kconfig_inv.txt`），自测在 arm 上直接编译通过。构建 278 秒（`build.sh`、`logs/build_inv.log`、`kernel_inv.config`）。
- QEMU 8.2：`-M virt -cpu cortex-a15 -smp 2 -m 1G`（两个 vCPU，拆分和读取真正并发）。
- `/init`（`init.c`，独立写法、直接发系统调用）fork 出三个进程：A 拥有 8MB THP 区域（4 个大页），每页写可校验的值后只读，循环“`MADV_COLLAPSE` → 逐页校验 → 跨 2MB 边界 `mprotect` 再改回”；B 循环向 `/sys/kernel/debug/split_huge_pages` 写 A 的区间；C 循环 `process_vm_readv` 读整个区间并校验、读 `/proc/A/pagemap` 分类计数。

## 二、结果

| | 第一次（120 秒，`logs/run_inv_run1.log`） | 第二次（480 秒，`logs/run_inv_run2.log`，正式） |
|---|---|---|
| 启动自测 | 929、930 报 WARNING；928 不报 | 同左 |
| `thp_split_pmd` 增量 | 2140 | 8332 |
| `MADV_COLLAPSE` 成功 / 失败 | 327 / 1326（未达 1000，记“不足以判断”） | 1229 / 5508 |
| B 拆分写入 | 51900（全部成功） | 224189（全部成功） |
| A 校验轮数 / 错页 | 1653 / 0 | 6737 / 0 |
| C 远程读轮数 / 短读 / 错页 | 3143 / 0 / 0 | 12498 / 0 / 0 |
| pagemap：空洞 / 交换类（迁移项，正常） | 0 / 133918 | 0 / 439395 |
| 压力期间告警 | 无 | 无 |

`MADV_COLLAPSE` 失败多，是因为 B 一直在拆分；`thp_collapse_alloc` 增量（2589、10086）说明合并确实在反复发生。实验内核没有异常，按判据不构建对照内核。

## 三、对第三轮结论的影响

第三轮把这条裁定为“完整线索”（静态）。现在：约定违反在运行时确认；后果在测过的路径上没有观察到。建议把它定为**低危的约定违反**（公共自测在 arm 上会失败、语义与其他架构不一致），是否登记、是否上报由用户定；上报前要联网查 lore 有没有人提过。

## 四、文件

- `criteria.md`、`criteria_amendment1.md`、`criteria_amendment2.md`、`criteria_sha256.txt`
- `build.sh`、`kernel_inv.config`、`logs/build_inv.log`、`logs/config_check_inv.txt`、`logs/kconfig_inv.txt`
- `init.c`、`mkinit.sh`、`run.sh`（`K=inv bash run.sh <tag>`）
- `logs/run_inv_run1.log`、`logs/run_inv_run2.log`
- WSL `/root/work/lpaeinv/keep/`：`inv/`（zImage、`.config`、`System.map`）、`init.cpio`，共约 20M；源码副本和构建目录已删

统计：模型调用 0；构建 1 次（arm LPAE + DEBUG_VM_PGTABLE）；QEMU 运行 2 次；没有联网，未对外报告。

2026-11-22 用户要求登记为低危，已登记为 `../../confirmed_bugs.md` B-2026-11-22-2。
