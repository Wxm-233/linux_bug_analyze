# 判据：编码感知的架构定向与排序（encrank_20261115）

2026-11-15，Claude。用户：“做编码感知排序”（规划第 2 步）。本文件在写探针、配置任何架构、做任何统计之前写定，SHA 存入 `criteria_sha256.txt`。

## 一、要回答的问题

P1 检查和契约挖掘都能报出“没查 present 就用受限接口”的位置，但排不出轻重：两个已确认缺陷在契约挖掘的 186 条偏离里排在第 94、145 名。缺陷会不会出现、出现在哪个架构，取决于各架构把非 present 项的哪几位放在哪里。p1dyn 里我手算过 6 项，对了 5 项。

本轮回答：
1. 能不能用各架构真实的头文件，**自动**算出“受限接口在每个架构上对每种非 present 项读出什么”？
2. 用它排序，能不能把真缺陷提到前面？

## 二、编码表（写死）

**架构**：x86_64、arm64、riscv、loongarch、powerpc（64 位小端）、s390、arm（32 位）、mips（64 位），共 8 个，都是 clang 18 支持的内核目标。

每个架构用 `defconfig`，再打开 `SWAP, MIGRATION, NUMA, COMPACTION, TRANSPARENT_HUGEPAGE, MEMORY_HOTPLUG, MEMORY_HOTREMOVE, ZONE_DEVICE, DEVICE_PRIVATE, USERFAULTFD, CHECKPOINT_RESTORE, MEM_SOFT_DIRTY`。打不开的项就算了（`olddefconfig` 决定），如实记录。然后做 `modules_prepare`，放在 WSL `/root/work/encprobe/<架构>/`，源码用 kbuild 的纯净源码，只读。某个架构配置或 `modules_prepare` 失败，就记为不可用，不换编译器重试。

**非 present 项**（页框号统一取 P = 0x12345）：
- PTE 级：
  - 交换项（类型 0、偏移 P）；
  - 迁移项：读、读独占、写；
  - device-private：读、写；
  - device-exclusive；
  - uffd-wp 标记。

  每种再各做三个变体：加 `pte_swp_mksoft_dirty`、加 `pte_swp_mkexclusive`、加 `pte_swp_mkuffd_wp`。
- PMD 级：迁移项（读、读独占、写）、device-private（读、写），用 `swp_entry_to_pmd` 构造；变体加 `pmd_swp_mksoft_dirty`、`pmd_swp_mkuffd_wp`。

**受限接口**：同 P1 检查的清单中 `pte_`、`pmd_` 的部分；另加两个“改写”探针：`pte_mkold`、`pmd_mkold` 是否改变了项的值（对应“清访问位”会不会把项改坏）。

**探针**：每个“接口 × 项”写成一个函数，返回 `!!接口(项)`。页框号类接口返回“读出的页框号是否等于 P”。改写探针返回“改写后的值是否不同”。每个接口单独一个文件，用该架构的内核编译选项编成 LLVM IR（`-O2`），从 `ret i32 常量` 读结果。不能折叠成常量的，记为“未知”；编译失败的（该架构没有这个接口或这个变体），记为“不可用”。

**读错**：
- 标志类接口对任何非 present 项返回 1；
- 页框号类接口读出的不是 P（只对带页框号的项算）；
- 改写探针返回 1（意味着“清访问位”会改坏这种项）。

**接口的跨架构特征**（PTE 级看全部 PTE 项，PMD 级只看 PMD 项）：
- 读错的架构集合 M；
- “**部分读错**”：M 非空，且不包含全部可用架构；
- “**潜伏**”：部分读错，并且 x86_64 不在 M 里。

## 三、排序（写死）

对契约挖掘（`contract_20261115/head.json`）的 186 条偏离，和 P1 检查（`p1check_20261115/head.json`）的 249 条报告，各自按下面的键排序：
1. 是否潜伏（是在前）；
2. 是否部分读错（是在前）；
3. 读错的架构数（多在前）；
4. 原来的顺序（契约比例、调用点数；P1 按来源分级 O1 > O2 > O3）；
5. 文件、行号。

一条偏离或报告涉及几个接口时，取最靠前的那个。偏离的接口不在受限清单里，三项特征都按“否、0”算。

## 四、评估（写死）

1. **编码表对不对**：
   - 和 p1dyn 的 6 项实测逐项对照：S1 写迁移项 PMD，arm64 young=1、dirty=0，riscv young=0、dirty=1，x86_64 young=0、dirty=1；S2 device-exclusive PTE，arm64 的 `pte_mkold` 会改变值，riscv、x86_64 的 `pte_young`=0 且不改变；
   - 能否解释 P1 样本出错的架构：`26e7888a0c89`（loongarch 的 `pmd_leaf` 对交换项或迁移项 PMD 读成 1）、`43e7f189769c`（x86_64 的 `pmd_write` 对带软脏的 device-private PMD 读成 1）、`bd1f2b2ace84`/`65529295607f`（x86_64 的 `pte_write` 对带软脏的 device-exclusive 读成 1）、`3faa3ebc89c1`（arm64 的 `pte_mkold` 改变 device-exclusive 项）。
2. **排序效果**：两个已确认缺陷的位置（`fs/proc/task_mmu.c:1129`、`include/linux/pgtable.h:534`）在新排序里的名次，分别在契约偏离和 P1 报告两个列表里报告。
3. **新的前 30 条**：契约偏离和 P1 报告在新排序下的前 30 条去重合并，扣掉以前已经审过的（P1 的 O1 前 30 条、契约的前 30 条）。对剩下的，我和 Codex 盲判，裁定“可能”的条数。

## 五、参考线（不是通过条件）

- p1dyn 的 6 项实测全部对上；5 个 P1 样本的出错架构至少解释 4 个；
- 两个已确认缺陷的位置，在两个列表里都进前 10 名；
- 新审的条目里，裁定“可能”的至少 2 条。

## 六、规则

不安装、不联网、不调用大模型（Codex 第二标注人除外）；只读 `/root/repos/linux` 和 kbuild 纯净源码；不做完整内核构建，只做 `defconfig` 加 `modules_prepare`；结束后只保留 `/root/work/encprobe/` 下每个架构的配置和生成的头文件，删掉中间产物，并记下占用的空间；不对外报告。统计行：模型调用 0；Codex 调用 N；构建 0（准备 8 次）；新确认缺陷 0；新疑点按实际写。
