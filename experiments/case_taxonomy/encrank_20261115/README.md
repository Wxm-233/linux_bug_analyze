# 编码感知的架构定向与排序（encrank_20261115）

2026-11-15，Claude。用户：“做编码感知排序”（规划第 2 步）。判据：`criteria.md`；修订 1 `criteria_amendment1.md`，当前版本改了 uffd 函数名、删了 devmap。SHA 在 `criteria_sha256.txt`。

统计行：模型调用 0；Codex 调用 1；构建 0（8 个架构各做一次 `defconfig` 加 `modules_prepare`）；新确认缺陷 0；新疑点 0。

## 一句话结论

**编码表做成了，而且很准**：用 8 个架构真实的内核头文件，自动算出“受限接口对各种非 present 项读出什么”，和 p1dyn 的实测 10/10 一致，5 个 P1 历史样本出错的架构 5/5 都解释得了。

用它排序：
- B-2 的位置在两个列表里都升到了**第 1 名**（原来分别是第 94、第 6 名）；
- B-1 从第 145 名升到第 17 名（契约偏离），在 P1 报告里是第 12 名，参考线要求前 10，没达到；
- 新排进前列、以前没审过的 26 条，两人审下来**没有新的“可能”**，大多是内核页表，或调用者已经保证了 present。

## 怎么做的（说人话）

页表项不在内存里时，里面的位是另一套编码，不同架构把访问位、脏位、可写位放在不同位置，所以同一个 `pmd_young()`，在 arm64 上可能读成 1，在 x86 上读成 0。以前是我手算，这次让编译器来算：

1. 8 个架构（x86_64、arm64、riscv、loongarch、powerpc、s390、arm、mips）各做一次 `defconfig` 加 `modules_prepare`，打开交换、迁移、THP、device-private、uffd、软脏等选项。每个架构不到 20 秒，一共只占 46M。
2. 自动生成探针：构造 8 种非 present 项（交换项、三种迁移项、两种 device-private、device-exclusive、uffd 标记），以及它们带软脏、带 exclusive、带 uffd 位的变体。对每个受限接口调用一次，再加“`*_mkold` 会不会改变这个项”。
3. 用各架构自己的内核编译选项编成 LLVM IR（`-O2`），常量会折叠成 `ret i32 0/1`，直接读出结果。每个架构 84 个探针文件，全部架构 45 秒跑完。

## 结果

### 1. 编码表（`table.md`、`encoding.json`、`validation.md`）

| 检验 | 结果 |
|---|---|
| p1dyn 实测（S1：arm64 young=1/dirty=0，riscv young=0/dirty=1，x86_64 young=0/dirty=1；S2：arm64 `pte_mkold` 改坏 device-exclusive，riscv/x86_64 不读错、不改坏） | **10/10**，包括我手算时预测错的 x86_64 脏位 |
| `26e7888a0c89`：loongarch 的 `pmd_leaf` 把迁移项 PMD 读成大页 | 对（另外算出 powerpc 也会） |
| `43e7f189769c`：x86_64 的 `pmd_write` 把带软脏的 device-private PMD 读成可写 | 对 |
| `bd1f2b2ace84`、`65529295607f`：x86_64 的 `pte_write`/`pte_dirty` 把带软脏的 device-exclusive 读错 | 对（另外算出 s390、powerpc 也会） |
| `3faa3ebc89c1`：arm64 的 `pte_mkold` 改坏 device-exclusive | 对 |

跨架构读错表的要点（只列“部分架构读错”的）：

- **只在 x86_64 以外读错（潜伏）**：
  - `pmd_leaf`：loongarch、powerpc；
  - `pmd_young`：arm64、s390；
  - `pte_young`：arm64、riscv、s390。riscv 上是因为 exclusive 标记和访问位是同一位；
  - `pte_mkold`：arm64、riscv、s390，会改坏项；
  - `pmd_mkold`：arm64、s390；
  - `pte_special`、`pmd_special`：riscv（还有 s390）；
  - `pmd_soft_dirty`：powerpc、s390。
- **x86_64 也读错**：`pmd_dirty`、`pte_dirty`、`pte_write`、`pmd_write`、`pte_uffd`、`pte_soft_dirty` 等。

### 2. 排序（`ranking.json`）

| 位置 | 契约偏离（186 条） | P1 报告（249 条） |
|---|---|---|
| B-2 `include/linux/pgtable.h:534`（`pte_young`） | 94 → **1** | 6 → **1** |
| B-1 `fs/proc/task_mmu.c:1129`（`pmd_young`/`pmd_dirty`） | 145 → **17** | 1 → **12** |

说明：P1 报告原来的顺序是“来源分级 + 文件名”，B-1 原来排第 1 名，只是因为 `fs/` 按字母排在最前面，不是因为排序判断出它危险。

B-1 没进前 10 的原因：
- 它用的 `pmd_young` 只在 2 个架构上读错；
- 排在它前面的，是在 3、4 个架构上读错的 `pte_young`、`pte_write`、`pmd_leaf` 的大量调用点，而其中多数调用点其实拿不到非 present 项。

### 3. 新前 30 条（我和 Codex 盲判，`new_adjudication.json`）

两个列表的新前 30 条合并去重后共 38 条，其中 12 条以前审过，剩 26 条要审。两人原始一致率 88%，裁定后 **可能 0**。不可能的原因分三类：

- 内核页表（vmemmap、KASAN shadow、vmalloc、ptdump），不会出现交换项或迁移项，9 条；
- 调用者或上文已经保证 present（批处理 present 项的函数、`pte_access_permitted` 之后、`is_present` 参数等），检查器不跨函数，看不到；
- 读错不影响结果，例如 `pmd_leaf(x) || !pmd_present(x)` 两边都一样。

值得记下的一条：Codex 在 `mm/migrate_device.c:1023` 找到一条经 `test_hmm` 并发插入 device-private PMD 的路径。在这条路径上，loongarch、powerpc 的 `pmd_leaf` 确实会误判，但后果是“放弃插页”，其他架构走另一条分支也放弃，所以不算错误后果。

## 看出的几点

1. **编码表是可靠的跨架构预言器。** 它不需要构建内核、不需要运行，就能说清“这处没守卫的调用会在哪些架构上、遇到哪种项时出错、怎么出错”。这正是师兄说的“架构差异只用来定位和定向”。5 个历史样本和 2 个新缺陷的出错架构，它全部算对。
2. **排序的瓶颈从“分不出轻重”变成了“分不出可达性”。** 编码表能告诉你“如果拿到非 present 项会怎样”，但很多调用点根本拿不到：内核页表、调用者已守卫、按约定只传 present 项。这正是检查器不跨函数、不区分内核页表和用户页表造成的。
3. **顺带发现**：P1 检查器的受限接口清单用的是旧名 `pte_uffd_wp`、`pte_devmap`，当前版本里叫 `pte_uffd`，devmap 已删掉。所以 P1 一直没检查过 `pte_uffd`，而编码表显示它在 x86_64 上会读错。

## 局限

- riscv 有 362 个值没能折叠成常量（riscv 的页表接口用了替换补丁等运行时机制），用到的关键值都拿到了；
- arm（32 位）和 mips 没有 THP 或 device-private，只有 PTE 级的部分结果；
- 只用了 `defconfig` 加几个选项，powerpc 只看了 64 位小端 book3s，其他配置下的编码可能不同；
- 新审的 26 条只是新排序下的前列，剩下的没审。

## 文件

- `criteria.md`、`criteria_amendment1.md`、`criteria_sha256.txt`；
- `prepare.sh`、`prepare.log`（8 个架构的准备）；`probe.py`、`run_probe.sh`（生成、编译、读探针）；`encoding.json`（全部探针值）；
- `analyze.py`、`table.{json,md}`、`validation.md`、`ranking.json`、`new_review.json`；
- `make_review.py`、`run_review.sh`、`review_new.txt`、`review_new_judgement.json`（我的判断）、`codex_blind/`（Codex 盲判）、`new_adjudication.json`、`stats.json`；
- WSL `/root/work/encprobe/`（46M，8 个架构的配置、生成的头文件和探针 IR，可复用）。

## 下一步建议

1. **补“可达性”过滤**，这是现在排序的主要误报来源：
   - 内核页表：调用点在 `pte_offset_kernel`、`init_mm`、vmemmap、vmalloc、KASAN 等路径上，就降权；
   - 跨函数：沿用契约挖掘里已经做好的入口事实，参数在所有调用点都有 present 守卫，就不报；布尔参数（如 `is_present`）也当作守卫；
   - 约定只传 present 项的函数（名字里带 `present`，或注释里写明），降权。

   做完再看 B-1 能否进前 10，前 30 里能否出现新的“可能”。
2. 把 P1 检查器的受限接口清单改成当前名字（`pte_uffd`、`pmd_uffd`），并直接用编码表决定“哪些接口受限”，不再手写。
