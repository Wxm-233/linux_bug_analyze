# 判据：页表函数的 .c 定义纳入求值（ecsrc_20261123）

2026-11-23，Claude。用户：“OK，接下来接着进行待办事项吧”。待办第 1 项（交接文档“四”的待办块）：上一轮 `ecpud_20261123` 发现 powerpc book3s64 的 `pfn_pmd`、`pfn_pud`、`pmd_modify`、`pud_modify` 在头文件里只有 `extern` 声明，定义在 `arch/powerpc/mm/book3s64/pgtable.c`，求值器拿不到函数体，ppc64le/ppc64le_hash 的 PMD、PUD 级组合全部“求不出”，v6.11（`4dd7724f02ab`）上 PUD 级只有 2 个可比构建。写于实现之前，此前只做了只读查询（git grep）。

## 一、诊断（只读）

- df2908090cda 与 4dd7724f02ab 上，book3s64 头文件里 `extern` 声明、`.c` 里定义的页表值函数：`pfn_pmd`、`pfn_pud`、`pmd_modify`、`pud_modify`（都在 `arch/powerpc/mm/book3s64/pgtable.c`，函数体是纯数值运算），另有 `pmdp_invalidate`、`pudp_invalidate`、`*_set_access_flags` 等带 vma 或指针参数的函数（EC 的角色分类不用它们）。
- 其他架构 `arch/*/mm/*.c` 里返回 `pte_t/pmd_t/pud_t` 的定义：riscv、x86 的 `pte_mkwrite(pte, vma)`、`pmd_mkwrite(pmd, vma)`、`p?dp_invalidate`、`pmdp_collapse_flush` 等，都带 vma 参数，预计不进入 EC 的组合。

## 二、修改（基础设施；判定规则不变 = 第三轮 EC + 第五轮规则 4、5，上一轮 `ec7.py` 的三项修改保留）

**.c 定义补全**：加载函数体时，对仍然没有函数体、名字是页表接口形式（`pfn_p*`、`p{te,md,ud}_*`、`__p{te,md,ud}_*`）的被调用函数，在该构建源码的 `arch/<架构>/` 下所有 `.c` 文件里按文本找“返回类型 + 函数名 + (”开头的定义；找到唯一一个文件时，用该构建 `mm/memory.o` 的同一套编译参数编译这个 `.c` 文件，取出该函数（以及它调用、头文件里没有的同文件函数）的语法树。找到多个文件或编译失败，就不补，照旧“求不出”。不手写函数名单。

## 三、运行

- 代码 `ec8.py` = `ec7.py` + 上面一项；缓存 `/root/work/ec_cache/v8`，重新表决 `/root/work/ec_cache/r8`。
- **df**：21 个构建全部重新挖掘（看这项修改对每个构建的影响）。
- **9 个父版本**：只重新挖掘 df 上行为发生变化的构建，其余复用 `v7`；若 df 上变化的不止 powerpc，如实报告并相应扩大。
- 源码副本按需重新导出，用完即删；每次构建后报告剩余空间。

## 四、门槛与报告

- **G1 补全生效**：df 和 v6.11 上，ppc64le 的 `pfn_pmd>pmd_mkhuge`、`pfn_pud>pud_mkhuge` 组合中至少一部分有确定行为；v6.11 的 PUD 级可比构建 ≥3。达不到就如实报告，不再扩展。
- **G2 影响范围**：报告 df 上每个构建补到了哪些函数、行为变化条数；预期只有 ppc64le、ppc64le_hash 变化。
- **G3 开发集召回**：9 个样本，父版本法，命中定义同第五轮（不改，`fba88ede6a31` 那类不计）。重点看 `144bb0aee33a`（x86 `pud_leaf`）。仍是开发集。
- **G4 df 噪声**：与上一轮 df 的 22 行比较，新增行不超过 30 行时，我先封存结论，再请 Codex 新会话盲审，报告一致率与 κ；超过 30 行只报告分类统计。
- **G5 整版扫描**：`scan9.py` = scan3 的 8 个引擎 + 本轮 EC；8 个旧引擎条数不变，报告整表行数。

## 五、其他

不新装软件包、不联网；不运行内核；不读封存材料。ppc64le 与 ppc64le_hash 在已能求值的接口上行为相同（上一轮核对过），powerpc 在 PMD/PUD 级可能投两张同样的票；按现行“每个构建一票”的规则不改，结果里单独说明这一点对表决的影响。
