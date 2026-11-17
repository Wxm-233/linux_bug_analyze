# 第二标注人独立核查备注

日期：2026-11-16。源码版本固定为 `df2908090cda`，通过本目录 `read_source.sh show/grep64` 读取提交中的文件，没有采用工作树 HEAD 的内容。

结果：23 条中，可能 3 条（4、5、15），不可能 20 条，说不清 0 条。每条的正式结论在 `codex.json`。这里的“可能”是源码路径判断，不是已完成运行复现。

本次按用户指定白名单读取 `review.txt`、两份判据、`xvdom_20261116/table2.md`、本目录的源码读取脚本及内核源码；没有打开其他标注人的判断文件、其他轮次的判断/README、主文件夹交接文档或进度日志。结束时仅向 `experiments/codex_worklog.md` 追加记录，不读取其旧内容。未构建、未运行内核、未联网、未安装软件、未调用其他模型。

判据原文件 SHA256：

- `criteria.md`：`504e6708e96ae5c0f8bdb8d803c2770c745a816639966ba4e059d6f97f2fa066`
- `criteria_amendment1.md`：`d6574f7f5fe172a38d0dbe5dc2d084e2ba40dfd1be71ffb774ea09550e3d72bf`

## 第 4、5 条：普通 LRU folio 上的 device-exclusive PTE

这里需要区分 device-private 页和 device-exclusive 项。前者指向 ZONE_DEVICE 内存；后者可指向普通匿名 folio，不能用“设备页不在 LRU”来排除。

可达链的源码依据：

1. `drivers/gpu/drm/nouveau/nouveau_svm.c:613` 调用 `make_device_exclusive`，并在 644-645 释放 folio 锁和引用。
2. `mm/rmap.c:2846-2865` 的调用约定支持普通匿名非 hugetlb folio；PMD 大页先改成 PTE 映射，不要求拆分 folio。`2951-2956` 用 PFN 构造并安装 device-exclusive 项，未移除其反向映射。
3. `mm/vmscan.c:874` 和 `2115` 在 LRU 回收中调用 `folio_referenced`。`mm/rmap.c:922` 使用无 `PVMW_MIGRATION` 的遍历，`mm/page_vma_mapped.c:125-135` 明确认可 device-exclusive 项。
4. 小 folio 无需经过大 folio 批处理，`nr=1`。MGLRU 开启时进入 `mm/vmscan.c:4279`，关闭时进入 `mm/rmap.c:986`。取一个未退出、未锁定内存的普通进程即可避开无关的退出/mm/VM_LOCKED 分支。

arm64 的实际实现：

- `arch/arm64/include/asm/pgtable.h:1862-1869` 覆盖 `test_and_clear_young_ptes`；`1891-1898` 覆盖 `clear_flush_young_ptes`。单项且没有 contig 位时进入 `__ptep_test_and_clear_young` 或 `__ptep_clear_flush_young`。
- `CONFIG_ARM64_CONTPTE=n` 时，`1968-1971` 直接绑定架构单项实现；外面的批量循环仍会调用它，不会转而使用通用的 pte_young 守卫实现。
- `1306-1319` 的 `__ptep_test_and_clear_young` 对输入执行 `pte_mkold` 并用 `cmpxchg_relaxed` 写回，没有 present 检查；flush 版本在 `1325` 调用同一实现。
- `arch/arm64/include/asm/pgtable-hwdef.h:170` 的 `PTE_AF` 是位 10；`arch/arm64/include/asm/pgtable.h:1515-1536` 的交换类型位于 6-10。依据 `include/linux/swap.h:50-111`，device-exclusive 类型是 30（PTE marker 类型是 31），清位 10 后变为 14，落入普通交换类型范围。
- 结果不是单纯误报“近期访问”：页表内保存的类型已经改变。`mm/memory.c:4901-4954` 后续按软件叶类型分流时会失去 device-exclusive 恢复路径，并将 PFN 当成普通交换偏移处理，可能因无有效交换设备/槽位失败，也可能访问错误的交换内容。

也检查了其他实际实现：RISC-V 在 `arch/riscv/mm/pgtable.c:32-37` 直接测试并清 `_PAGE_ACCESSED_OFFSET`；s390 在 `arch/s390/include/asm/pgtable.h:1200-1214` 通过 `ptep_xchg_direct` 写回 `pte_mkold`。正式判断用 arm64 已闭合的例子，不把通用实现的表现当作这些架构的实际行为。

## 第 15 条：判定所依赖的具体配置

首项副本和后续扫描项必须分别判断。第 2 条所列的三个读操作受 MERGE 参数控制、在 flags=0 时不执行；第 15 条的 `pte_pfn(*ptentp)` 则在首项上执行，且 `mm/rmap.c:969-974` 没有在调用 `folio_pte_batch` 前排除 device-exclusive 项。

`make_device_exclusive` 允许大匿名 folio，仅将 PMD 映射拆为 PTE 映射后改一个 PTE。可以保留一个刚分配、原本独占可写的大 folio，将首 PTE 转换为 device-exclusive，再在驱动释放锁后由回收取得该 folio，因而无需假定设备私有 folio进入 LRU，也无需假定先发生了页表损坏。

本条足以判“可能”的后果明确限于下列配置：

- x86_64，4K 基页，`CONFIG_DEBUG_VM=y`、`CONFIG_SPARSEMEM_VMEMMAP=y`，默认非致命 WARN，且存在相应物理内存洞。
- `arch/x86/include/asm/pgtable_64.h:231-237` 把交换偏移取反后放入位 9-58；`arch/x86/include/asm/pgtable.h:256-260` 却按 present 的 PFN 位提取。结合 `arch/x86/include/asm/pgtable-invert.h:16-24`，device-exclusive 偏移中保存的 PFN `P` 会被读成 `P >> 3`。
- 例如真实 PFN `P=0x200000`（物理地址 8 GiB），误读 PFN 为 `0x40000`（物理地址 1 GiB）。若后者所在范围是未填充 vmemmap 的内存洞，`pfn_to_page` 得到的地址没有映射。
- `mm/internal.h:420` 的 present 警告不是 return；继续到 `422` 会计算 `page_folio(pfn_to_page(pte_pfn(pte)))`。`include/linux/mmdebug.h:70-77` 在 DEBUG_VM 下实际求值，`include/asm-generic/memory_model.h:43-46` 直接加 vmemmap 基址，`include/linux/page-flags.h:224-226,300-302` 再读取该地址的 `compound_info`，从而触发内核页故障。

这不是对任意非调试配置都崩溃的断言。没有制作启动镜像或进行运行复现，具体机器是否有此内存洞也未测量。

另做过一项独立的源码编码算术核对，用 JavaScript BigInt 计算 x86_64 的交换编码、PFN 推进及 `__pte_batch_clear_ignored(flags=0)`，没有执行内核代码：首项 PFN `0x1000` 被 `pte_pfn` 读成 `0x200`，folio 末端 `0x1004` 减该误读值为 `0xe04`；后续 PFN `0x1008、0x1010、0x1018` 的 device-exclusive 项依次能与错误的 present-PFN 推进期望值匹配。三次归一化比较均为真，原始首项值为 `0xf7ffffffffdffe00`，三个期望值分别为 `0xf3ffffffffdfe600、0xf3ffffffffdfd600、0xf3ffffffffdfc600`。它说明不能仅从“通常返回 1”推出批处理安全；但没有验证能形成该完整映射布局的用户操作序列，普通配置下的最终回收后果不作为本条正式判断依据。

## 其余排除依据的关键核对点

- **1、2、3**：上层 present 检查、MERGE 参数和 `nr=1` 的执行条件需要跨层跟踪。arm64 的单项取清覆盖实现也检查过，不能仅凭通用循环下结论。
- **6、7**：`pmd[i]` 与 `pmd+i` 是同一对象；锁内 `pmd_present(pmd[i])` 已明确排除定义域外输入。第 6 条对非叶 PMD 清 young 是架构特意支持的场景。
- **8、9**：首项与已知交换项的完整相等比较构成隐含类型守卫，后续扫描项也先比较再推进 expected；报告中的第 2 个参数实际上是按值的 `pte`。
- **10**：PMD device-private 路径确实存在，不能笼统说遍历只返回 present。但是 `folio_referenced` 的全部实际调用来自 LRU 回收，ZONE_DEVICE folio 不在 LRU；`mm/migrate_device.c:601-602,1329-1330` 也明确保留这一约定。普通 LRU folio 的 device-exclusive 转换只在 PTE 层发生，迁移项在此遍历模式下被拒绝。
- **11、18**：GUP 在 PMD 锁内再次检查 present/leaf；不是只依赖无锁的初次检查。
- **12、19**：`include/linux/huge_mm.h:589-592` 的 `thp_migration_supported()` 在本版本就是 `CONFIG_ARCH_HAS_PMD_SOFTLEAVES`，所以 `change_huge_pmd:2714` 的分流能覆盖存在的软件叶 PMD。NUMA/RWP 两条路径则在锁内与已确认 present 的原项比较。
- **13**：swapoff 在重新取锁后可能看到 present 项，不能用之前的无锁 swap 检查排除。安全性来自只处理临时副本、保留 present 判别位且只做与目标交换项的完整比较；原页表没有被写坏。arm/loongarch 的 exclusive 位分别为 7、13/23，均不等于它们的 present 判别位。
- **14、16、17、20、22**：逐一检查了 mprotect、NUMA/RWP、device-exclusive 恢复和换入后的写保护入口；新恢复的 present 项不能与恢复前的交换项混为一谈。PROT_NONE 在这里仍是 present 类。
- **21、23**：需要追踪调用约定，PFN 相等检查本身不是通用的 present 证明。当前更新旧映射的相应插入路径服务 DAX/特殊驱动映射；`include/linux/mm.h:593-595` 将 MIXEDMAP/PFNMAP 列入 VM_SPECIAL，`mm/userfaultfd.c:2205-2206` 和 `mm/madvise.c:1055-1067` 分别拒绝其 UFFD/guard 注册；DAX 内存失败路径 `mm/memory-failure.c:1728-1747` 走取消映射。普通插页的 mkwrite=false 会在更新旧项前退出，其余 maybe_pmd_mkwrite 调用传入新构造的映射或锁内验证的 present 巨大页。

未验证项：没有构建、启动或动态触发以上三条路径；没有测量任何内存布局、发生概率或性能；没有与其他标注人的结论对比。
