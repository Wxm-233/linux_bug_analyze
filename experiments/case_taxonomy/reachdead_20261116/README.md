# 参数常量导致的死分支过滤 F7（reachdead_20261116）

2026-11-16，Claude。用户：“加死分支过滤”。判据见 `criteria.md`（SHA 在 `criteria_sha256.txt`，本轮没有修订）。

统计行：模型调用 0；Codex 调用 0；构建 0；新确认缺陷 0；新疑点 0。

## 一句话结论

**参考线全部达到。** F7 在当前版本上只滤掉 2 条，正是目标 `insert_pfn()` 的 `mm/memory.c:2824`、`2825`，与 `s3pfn_20261116` 的人工结论一致。B-2026-11-16-1 所在的 `insert_page_into_pte_locked` 没被滤掉。可达候选从 61 条降到 **59** 条，召回仍 15/15，历史样本里没有一条被 F7 误滤。

## 做法（说人话）

有些受限接口调用写在 `if (p)` 分支里（或在 `if (!p) return;` 之后），p 是函数参数。如果在所有实际调用路径上 p 都是同一个常量，并且这个常量让分支不成立，这行代码就执行不到。

F7 的做法：

1. 在调用点处找到“参数 p 为真/为假”的事实；
2. 找出函数所有调用点上传给 p 的值：
   - 字面常量（`true`、`false`、`0`、`NULL` 等）直接取真假；
   - 如果传的是调用者自己的参数，就往上追一层；
   - 其他表达式算“未知”，不滤；
3. 调用者的范围：`.c` 文件里的 `static` 函数只看本文件；否则在全树里找这个函数名，出现在扫描范围外、被取地址、被导出，都算“未知”；
4. 全树没有任何使用的函数算“死函数”，它里面的调用不计入；
5. 所有可能的值都让分支不成立，才判 F7。

## 结果

| | reachgoto | **本轮** |
|---|---|---|
| 自测 | 32/32 | **37/37**（加 5 条） |
| F7 滤掉 | — | 2 |
| 可达候选 | 61 | **59** |
| B-2 / B-1 / B-2026-11-16-1 | 1 / 5 / 25 | 1 / 5 / 25 |
| 召回 | 15/15 | **15/15**（历史样本 0 条被 F7 滤掉） |

**F7 滤掉的 2 条**（`changes.json`、`check.json`）：`insert_pfn()` 里 `if (mkwrite)` 分支中的两次 `pte_pfn`。F7 追出来的链：

```
insert_pfn(…, mkwrite)
  ← vmf_insert_pfn_prot：传 false
  ← __vm_insert_mixed(…, mkwrite)
       ← vmf_insert_mixed：传 false
       ← vmf_insert_mixed_mkwrite：传 true，但全树没有任何使用、也没导出 → 死函数，不计
⇒ mkwrite 恒为 false，if (mkwrite) 执行不到
```

**按预期没滤掉的**：

- `insert_page_into_pte_locked`（B-2026-11-16-1）：`mkwrite` 来自 `insert_page`，再来自 `vmf_insert_page_mkwrite(…, write)`。后者被导出，又在扫描范围外由 `fs/dax.c` 调用，取值未知。正确，这正是已确认的缺陷路径。
- `insert_pmd`（`mm/huge_memory.c:1609`）：`write` 来自两个导出函数，取值未知。`s3pfn` 里排除它靠的是“DAX 页不迁移、PMD 级没有 uffd 标记”这类语义论证，F7 管不到。

## 对照参考线

| 参考线 | 结果 |
|---|---|
| 自测全部正确 | 达到（37/37） |
| `mm/memory.c:2824`、`2825` 被 F7 滤掉 | 达到 |
| F7 滤掉的都确实执行不到 | 达到（2/2） |
| 三个确认缺陷都不被滤掉，B-1、B-2 在前 10；召回 15/15 | 达到 |

## 看出的几点

1. F7 很保守：只要有一个调用者传的不是常量、在扫描范围外、或者函数被取地址，就不滤。当前版本只命中了 2 条，没有误滤。
2. “死函数”这一步是关键。没有它，`__vm_insert_mixed` 的 `mkwrite` 取值是 {false, true}，滤不掉 `insert_pfn`。死函数的判断依赖全树搜索，结论只对树内代码成立：树外模块理论上能调用非 static 的函数，但 `vmf_insert_mixed_mkwrite` 没有导出，树外模块也调用不了。
3. 召回耗时 28 分钟（reachgoto 21 分钟），多出来的是全树搜索。

## 局限

- 只认“裸参数”作条件（`if (p)`、`if (!p)`、`p && …`），`if (flags & X)`、`if (p == 2)` 这类认不出；
- 只追参数，不追局部变量和全局变量；
- 在宏里出现的使用一律算未知。

## 文件

- `criteria.md`、`criteria_sha256.txt`；`reachdead.py`（F7、自测、当前版本、召回）、`run.sh`；
- `head.json`、`head.log`、`changes.json`、`check.json`（我的核对）、`recall.json`、`recall.log`、`stats.json`。

**可达性过滤的正式版改为本目录的 `reachdead.py`**（依次只读导入 reachgoto → reachsum → reachf1 → reachf4 → reach → contract）。

## 下一步建议

1. 可达候选 59 条里，前 30 以外还没审过的条目，由我和 Codex 盲判，看还有没有新疑点；
2. P1 受限接口清单由编码表生成，去掉旧名字；
3. 召回已经接近半小时，可以把全树搜索的结果缓存下来，或者只在需要时才搜。
