# 26 条新增报告的独立盲判

我只按本次任务授权读取父目录的 `review_new.txt`、`criteria.md`、`criteria_amendment1.md`、`table.md`，以及固定提交 `df2908090cda` 的内核源码；未读取第一标注人的结果、实验 README 或外层交接与进度文件。没有调用其他模型，没有构建、安装、联网或运行内核。本次按特别要求追加 `experiments/codex_worklog.md`，不更新外层文档；本目录原有 `prompt.md` 未修改。

正式输出为 `codex_new.json`：可能 1 条（第 6 条），不可能 25 条，说不清 0 条。这里的“可能”严格保留题设的**非 present 项可达且接口读值与编码表所定口径不符**这一含义，不能直接折算为新确认的功能缺陷；第 6 条的保守退出尤其需要在裁定时注意。

## 第 6 条：确实可达软件项，但退出可能正是所需行为

我找到的具体路径不需要假设页表损坏或调用者违约，也不需要已经迁移成功的源页：

1. 使用启用 `TEST_HMM`、`DEVICE_PRIVATE`、THP 及 PMD 软件项支持的配置。`lib/Kconfig.debug:3325` 没有限制测试驱动只能用于 x86；LoongArch 的 `arch/loongarch/Kconfig:15` 和 PowerPC 的 `arch/powerpc/platforms/Kconfig.cputype:110` 提供相关 PMD 支持。
2. 建立覆盖完整 PMD、适合 THP 的匿名 VMA，页表暂为空。线程 A 对其中未按 PMD 对齐的单页提交 `HMM_DMIRROR_MIGRATE_TO_DEV`；`dmirror_fops_unlocked_ioctl` 的分流位于 `lib/test_hmm.c:1642`，`dmirror_migrate_to_device:1320` 仅持 mmap 读锁。
3. A 的 `migrate_vma_setup` 经 `migrate_vma_collect_hole` 给这个空洞记录 `MIGRATE_PFN_MIGRATE`，没有有效源 PFN，也没有 compound 标记（`mm/migrate_device.c:45-70`）。对空 PMD 调用 `pte_hole` 不创建 PTE 页表，见 `mm/pagewalk.c:131-139`。在 A 收集完后、插页前暂停其调度即可；此处没有需要人为破坏的锁。
4. 线程 B 对同一 VMA 的整个对齐 PMD 范围执行迁移至设备。它可以收集 compound 空洞并成功分配 compound 设备目标；`dmirror_migrate_alloc_and_copy` 依据源标记选择分配粒度（`lib/test_hmm.c:853、874、924-929`）。`migrate_vma_insert_huge_pmd_page` 在 PMD 锁下检查槽位为空，构造 device-private 项并在 `mm/migrate_device.c:849、891` 安装。
5. A 恢复后仍持有自己的单页空洞记录与非 compound 目标；`__migrate_device_pages:1131-1166` 进入 `migrate_vma_insert_page`。1010 行的大页目标分支不成立，1018 行非空检查成立，1019 行 `pmd_trans_huge` 对软件项为假，于是执行 1023 行。
6. LoongArch 的 `__swp_entry_to_pmd` 明确加入 `_PAGE_HUGE`（`arch/loongarch/include/asm/pgtable.h:346`），`pmd_leaf:645` 只检查这个位，`pmd_trans_huge:519` 则还要求 present。PowerPC 的软件 PMD 转换加入 `_PAGE_PTE`（`arch/powerpc/include/asm/book3s/64/pgtable.h:657-660`），`pmd_leaf:270` 检查该位，而 `pmd_trans_huge:1215` 先拒绝非 present 项。因此两者都可出现 leaf=1、trans_huge=0、present=0。

此路径中的非 present 项是 **device-private PMD**。设备测试驱动没有围绕迁移 ioctl 持有 `dmirror->mutex`，其 notifier 对同 owner 的 `MMU_NOTIFY_MIGRATE` 直接放行，其他通知也只在回调内部短暂持锁（`lib/test_hmm.c:322-345`），不能用该锁排除上述并发。Nouveau 的现有迁移入口也体现了仅持 mmap 读锁执行迁移的用法，但本判断无需依赖真实 GPU 硬件。

直接后果是 1024 行 `goto abort`，1106 行清掉 A 的 `MIGRATE_PFN_MIGRATE`。**B 已经占据了该地址，A 此时本来就不应覆盖它；所以我没有证明多丢了一次本应成功的迁移、权限错误或数据损坏。** 即便改为明确检查非 present，或让后面的 `pte_offset_map_lock` 拒绝非 present PMD，也会放弃插页。正式 JSON 依据用户给定的“接口读错”条件记为“可能”，不是“确认新缺陷”；若后续裁定要求整体行为也必须出错，这条不能仅凭现有证据计入。动态复现与功能影响验证均为 `null`。

## 容易混淆的排除依据

- 第 1、17、20、23、26 条：检查主要在调用者或上一级分流，不能把被调函数未出现 `pte_present` 等同于软件项可达。设备独占项恢复后形成的 PTE 也须与恢复前的项区分。
- 第 2、3、4、10、11 条：访问的是内核 vmemmap、KASAN shadow 或 vmalloc 页表。物理页可能另有用户映射，不代表内核别名会安装用户页的软件项。第 10 条还必须区分 `__weak` 通用实现和 PowerPC 的强定义。
- 第 5 条：我检索了整个固定提交中两个 apply 接口的调用者。标出架构上现有使用是内核映射；使用用户 mm 的 i915 明确 `depends on X86 && PCI`，SGX 属 x86，Xen 配置入口位于 arm、arm64、x86。空 PMD 也可能被检查，但其编码不含这里的叶子位，不能把“非 present”简单等同于“已测软件项”。
- 第 8、9 条：区分有 VMA 的用户遍历和无 VMA 的内核/调试遍历；通用函数能接收 mm 参数，不代表标出架构已有转储任意用户 mm 的调用者。第 8 条的整个 `leaf || !present` 结果还会屏蔽非 present 项的叶子误分类，不会据此下钻页表。
- 第 12 条：`is_present` 是同一份 PMD 的检查结果，并经 `&&` 短路阻止实际调用，不是一个无关布尔量。
- 第 13 条：非匿名 VMA 的迁移 PMD 已单独处理，特殊 PFN 大页更早返回。文件 VMA 的 COW 在 `mm/memory.c:6390-6418` 拆 PMD 后按 PTE 处理；`mm/migrate_device.c:1211-1224` 限制向 device-private/coherent 迁移的页面类型，空洞大页插入也要求匿名 VMA。不能任意在文件大页分支假设 device-private PMD。
- 第 14、25 条：读取的是 `pmdp_invalidate` 返回的旧值。通用实现见 `mm/pgtable-generic.c:201-207`，PowerPC 见 `arch/powerpc/mm/book3s64/pgtable.c:155-165`，s390 见 `arch/s390/include/asm/pgtable.h:1789-1801` 与 `arch/s390/mm/pgtable.c:239-248`。
- 第 15、24 条：`pte_access_permitted` 隐含 present 检查，且后续读同一局部 PTE。第 18 条的 `pte_user_accessible_page` 同样是架构头文件中明确可查的检查。
- 第 16 条：walker 不过滤每个非 present PTE，因此不能只看 walker 就排除；真正的依据是实际调用者限定为 vmwgfx 的 TTM 共享设备映射（`drivers/gpu/drm/ttm/ttm_bo_vm.c:490-511`），以及驱动的架构范围（`drivers/gpu/drm/vmwgfx/Kconfig:2-9`）。没有把这个接口的安全性泛化到任意未来调用者。
- 第 19 条：`page_vma_mapped_walk` 在 HugeTLB 锁下通过 `check_pte` 检查，并且当前迁移扫描不带 `PVMW_MIGRATION`。能在普通映射中出现的 device-private/device-exclusive 项不构成 HugeTLB 项的反例。
- 第 21、22 条：测试使用普通映射构造器，不接触用户实际页表；`PAGE_NONE` 在这里也属于 Linux 逻辑 present，不能用硬件“不允许访问”推导交换编码可达。

## 第 26 条的调用者复核范围

我同时追踪了 `vm_normal_folio` 包装及未在同函数检查 present 的辅助函数：

| 调用组 | 固定提交中的依据 |
|---|---|
| proc smaps、clear_refs、pagemap、numa_maps | `fs/proc/task_mmu.c:1059、1722、1813、2034、2454、3381`；`pte_is_pinned` 只在 present 分支调用 |
| DAMON | `mm/damon/vaddr.c:422、675、837` |
| GUP | `mm/gup.c:816`；`get_gate_page:1066` 的例外是固定 gate 映射 |
| HMM | `mm/hmm.c:259-308` 在到达 320 行前把软件项分流出去 |
| khugepaged | `mm/khugepaged.c:713、1663、1937、1999` |
| KSM | `mm/ksm.c:638、2576`；迁移项使用独立转换 |
| madvise、mempolicy、mlock | `mm/madvise.c:482、698-711`；`mm/mempolicy.c:717-722`；`mm/mlock.c:386` |
| mprotect | `mm/mprotect.c:357` 的 present 分支；`can_change_private_pte_writable` 的调用者使用该分支或 fault/restoration 构造的 present 值 |
| mremap | `move_ptes:286` 仅在 present 分支调用 `mremap_folio_pte_batch`，后者才在 190 行调用 `vm_normal_folio` |
| copy、zap、写缺页、NUMA/RWP fault | `mm/memory.c:1377-1403、1962、6560-6582`；交换恢复在 `5199、5224` 更新并安装新的 PTE，独占恢复在 `955` 重建普通映射 |
| 设备迁移收集 | `mm/migrate_device.c:293-336` 分流软件项后，344 行处理 present 项 |
| folio_walk | `mm/pagewalk.c:1007` 的 present 分支 |
| userfaultfd | `mm/userfaultfd.c:1292、1589-1618`，后者还在锁下核对原 PTE 未变 |

上述是对当前调用者的静态审查，不是给 `vm_normal_page` 添加了它自身并不存在的 present 检查，也不是对未来新增调用者作保证。

## 复核方式与局限

本目录 `criteria.md` 在逐条完整源码核对前写定，哈希见 `criteria_sha256.txt`。读取脚本第一行按项目要求 source `tools/wsl_env.sh`，仅对 `/root/repos/linux` 执行固定提交的 `git show` 与 `git grep`，不切分支、不修改源码。输出和所有新增辅助文件均在本目录。

示例命令：

```text
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/encrank_20261115/codex_blind/read_kernel.sh mm/migrate_device.c:976-1028 lib/test_hmm.c:1291-1349
```

含 `|` 的正则通过 PowerShell 转为 UTF-8 Base64 后传给脚本 `--grep64`，避免 WSL 参数转换误把正则当作 shell 管道。第一次未编码的多分支正则出现 `command not found`，已修正并完整重跑；这是查询命令的引用错误，不是源码分析或构建失败。

不可能的结论均针对这 26 条所报的路径和标出架构，不代表全内核不存在相似问题。没有配置、编译或启动任何架构，逐架构构建验证、动态复现、与第一标注人的一致性、最终功能缺陷确认数均为 `null`。

交付检查见 `validation.json`：JSON 可按严格 UTF-8 解析，恰有 26 项，编号与 `review_new.txt` 的 26 个位置逐项一致，字段恰为 `k/loc/verdict/why`，每条理由为两三句，判据 SHA256 未变化。该文件同时保存四份允许输入及正式 JSON 的 SHA256；这些检查只验证交付文件的完整性，不代替源码判断或动态验证。
