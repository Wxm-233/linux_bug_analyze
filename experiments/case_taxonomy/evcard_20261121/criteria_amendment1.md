# 判据修订 1：已审记录补上 README 和审查材料（evcard_20261121）

2026-11-21，Claude。**写于第一次生成证据卡之后、卡片核对和审查之前。** 我看了两个榜单前 12 条的位置和卡片摘要，没有逐条审查。

## 原因

判据第一节只把文件名含 `review/judg/label/adjudic/verdict/audit` 的文件当作审查记录。第一次运行后，池里留下了我明知审过的项：

- EZ 13 条里有 11 条：`effzero_20261120/review/claude_labels.json` 只写了函数名、没写文件路径，文件路径在 `review/packets.md` 里；
- CTX 2 条（`kernel/debug/gdbstub.c` 的 `flush_icache_range`、`mm/util.c` 的 `flush_dcache_page`）：结论写在 `ctxeff3_20261118/README.md` 里；
- XA 1 条（powerpc `pudp_huge_get_and_clear_full`）：结论写在 `xvatom2_20261119/README.md` 里。

astra 第一周的原意是：“遇到评审者认识的项即时标记，主结果排除并按原榜顺延”。判据漏写了这一条。

## 修改

1. 审查记录的范围加上：各轮目录下的 `README.md`，以及文件名含 `packet` 的文件（本目录、`sealed*`、封存集文件仍除外）。判断规则不变：文件路径和函数名同时出现在同一个文件里。
2. 审查时如果遇到我认得、以前审过的项，当场标记为已审，从主比较里去掉，由该榜的下一条顺延；标记写进 `claude_review.json`。
3. 我核对过：WK 的 5 条（arm、mips `free_initmem`，powerpc `vma_mmu_pagesize`，x86 `set_swbp`，Xen `paddr_vmcoreinfo_note`）在 `weakov2_20261118` 里只列出、没有审查，按规则留在池里。

其余不变。
