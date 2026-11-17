# 判据：效果依赖线横向扩展到交换项专用接口和修改接口（xvdom_20261116）

2026-11-16，Claude。用户：“按横纵两面拓展”，并补充“贴合文档、保持分流（三类检查加效果依赖）、别太偏离”。总设计见 `design.md` 第四节第 1 步。本文件在写代码、跑任何统计之前写定，SHA 存入 `criteria_sha256.txt`。

## 一、问题

P1 只检查了一个方向：present 专用的读接口（`pte_dirty`、`pmd_young` 等）被用在非 present 项上。还有两个方向没查：

- **反方向**：只对交换格式项有定义的接口（`pte_swp_soft_dirty`、`pte_swp_exclusive`、`pte_swp_uffd`、`pmd_swp_*`）被用在 present 项或空项上；
- **修改接口**：`pte_mkdirty`、`pte_wrprotect`、`pte_mkuffd` 这类修改接口被用在非 present 项或空项上；`pte_swp_mkuffd` 这类交换项修改接口被用在 present 项或空项上。各架构的位布局不同，用错了就会把项改坏（`pte_mkold` 改坏 device-exclusive 就是 B-2）。

## 二、横向：编码探针扩展（写死）

沿用 `encrank_20261115/probe.py` 的做法：8 个架构，用各自的头文件和编译选项编成 LLVM IR（`-O2`），读折叠后的常量。工作目录复用 WSL `/root/work/encprobe/`，不构建内核。

### 输入类

PTE：

- encrank 原有的 8 类非 present 项，以及 4 种修饰（plain、软脏、exclusive、uffd）；
- **空项** `__pte(0)`；
- **present 项**：基础值 `pfn_pte(P, PAGE_READONLY)`，以及分别加上下列修饰之一的变体：`pte_mkdirty`、`pte_mkyoung`、`pte_mkwrite_novma`、`pte_mkspecial`、`pte_mksoft_dirty`、`pte_mkuffd`，还有全部加上的 `all`。
  - 另加 protnone 变体 `pte_modify(基础值, PAGE_NONE)`。
  - 在某个架构或配置下编不过的变体，记为不可用。

PMD：

- 原有的迁移项、device-private 项，以及修饰（plain、软脏、uffd）；
- 空项 `__pmd(0)`；
- present 大页 `pmd_mkhuge(pfn_pmd(P, PAGE_READONLY))`，修饰同 PTE（用 pmd 版本的函数）。

### 接口组

| 组 | 接口 | 定义域 | 在哪些输入类上探 | “出错”的定义 |
|---|---|---|---|---|
| R（P1 原有） | encrank 的受限读接口 | present | 原有各类，加空项 | 同 encrank（布尔读出 1；`pfn` 不等于 P） |
| S 交换项读 | `pte_swp_soft_dirty`、`pte_swp_exclusive`、`pte_swp_uffd`、`pmd_swp_soft_dirty`、`pmd_swp_uffd` | 非 present 且非空 | present 各变体、空项 | 读出 1 |
| MG 通用修改 | `pte_`/`pmd_` 的 `mkold`（原有）、`mkyoung`、`mkdirty`、`mkclean`、`wrprotect`、`mkwrite_novma`、`mksoft_dirty`、`clear_soft_dirty`、`mkuffd`、`clear_uffd`、`mkspecial` | present | 非 present 各类、空项 | 修改后的值不等于原值（改坏） |
| MS 交换项修改 | `pte_swp_mksoft_dirty`、`pte_swp_clear_soft_dirty`、`pte_swp_mkexclusive`、`pte_swp_clear_exclusive`、`pte_swp_mkuffd`、`pte_swp_clear_uffd`，以及对应的 `pmd_swp_*` | 非 present 且非空 | present 各变体、空项 | 改坏 |

**自检**：S、MS 在交换项上探一遍，用来核对探针本身是对的。S 在“加了对应位的交换项”上应读出 1；MS 的 mk 再接 clear 应还原成原值。

**每个接口的特征**同 encrank：出错架构集合 M、有结果的架构集合；“部分架构出错”记为 partial，partial 且 x86_64 不在 M 里记为 latent，出错架构数记为 n。

## 三、纵向：调用点与守卫（写死）

只读导入 `reachgap_20261116/reachgap.py`（正式版 F1～F7 加 G1、G2），不改旧文件。

1. **范围**：同 reach 系列，扫描范围内 S、MG、MS 三组接口的全部调用点。R 组就是 reachgap 的结果，本轮只按新编码表重排，不重新过滤。
2. **MG 组**：定义域是 present，过滤用 reachgap 的 classify，即 F1～F7、F1s，一项不改。
3. **S、MS 组**：定义域是“非 present 且非空”（记作 NP）。调用点对象 x 满足下列任一条，就判 **F1n**：
   - 同时有 `pte_present(x)`（或 `pmd_present`）为假，和 `pte_none(x)`（或 `pmd_none`）为假的事实；
   - 有 `softleaf_is_K(x)` 为真的事实，K 是 none 以外任何一种；或有 `softleaf_is_none(x)` 为假的事实；
   - 有 `pte_is_marker`、`pte_is_uffd_wp_marker`、`pte_is_uffd_marker`、`pmd_is_migration_entry`、`pmd_is_device_private_entry`、`pmd_is_valid_softleaf` 之一对 x 为真的事实。

   `softleaf_is_*(e)` 的对象 e 如果是 `softleaf_from_pte(x)` / `softleaf_from_pmd(x)` 的结果（直接嵌套，或经局部变量赋值，分析器已有的布尔别名机制），把对象换成 x。依据是 `include/linux/leafops.h`：这两个函数对 present 项和空项返回 none。

   其余过滤沿用：
   - F3（本地构造的值）；
   - F4（内核页表）；
   - F6（测试代码）；
   - F7（死分支）。

   F2、F5 是按名字里的 “present” 判断的，只适用于 present 定义域，S、MS 组不用。
4. **候选**：没被过滤、并且所用接口在横向上至少有一个架构出错的调用点。接口在所有架构上都不出错的，不进候选，单独计数。
5. **排序**：同 encrank 的规则（partial、latent、出错架构数），按新编码表的特征算。

## 四、评估（写死）

1. **探针核对**：
   - encrank 原有的输入类和接口，新探针的结果必须和 `encrank_20261115/encoding.json` 逐格相同；
   - 第二节的自检必须全部通过（不可用的除外）。
2. **自测**：沿用 reachgap 的全部自测，另加下面几条，必须全部正确：
   - `if (!pte_present(e) && !pte_none(e)) pte_swp_uffd(e)` → F1n；
   - `if (pte_present(e)) … else pte_swp_uffd(e)` → 不滤（没排除空项）；
   - `softleaf_t s = softleaf_from_pte(e); if (softleaf_is_swap(s)) pte_swp_exclusive(e)` → F1n；
   - `if (softleaf_is_migration(softleaf_from_pte(e))) pte_swp_soft_dirty(e)` → F1n；
   - `if (pte_is_uffd_wp_marker(e)) pte_swp_uffd(e)` → F1n；
   - `if (pte_present(e)) pte_mkdirty(e)` → F1（MG 组）；
   - 没有守卫的 `pte_swp_mkuffd(e)` → 不滤。
3. **当前版本**（HEAD `df2908090cda`）：
   - 报告三组的调用点数、各过滤项的条数、候选数；
   - 报告 R 组按新编码表重排后三个已确认缺陷的名次。
4. **审候选**：候选不超过 30 条就全审，否则审前 30 条。
   - 我和 Codex（gpt-6.1-sol，max）各自独立判断“可能 / 不可能 / 说不清”；Codex 看不到我的判断；
   - 两人都判“可能”或有分歧的，读源码裁定；
   - 裁定“可能”的记为新疑点，动态验证另起一轮。
5. **召回**：
   - R 组保持 reachgap 的 15 个样本，本轮不重跑过滤，名次变化单独报告；
   - S、MS、MG 组：在 `v5.10..df2908090cda` 里找修复提交（带 `Fixes:` 标签，或标题含 fix），条件是改动的行里含有三组接口的调用，并且新增了 present、none、softleaf 判断，或改换了接口；
   - 逐个读，确认属于“接口用错了项”的，作为召回样本；在样本修复前的版本上跑本轮分析器，看修复位置是否进入候选；
   - 找不到样本就写明“召回无法评估”。

## 五、参考线（不是通过条件）

- 探针核对和自测全部正确（**必须**）；
- S、MG、MS 三组里，至少有一个接口是 partial（横向确实存在跨架构差异）；
- 候选不超过 60 条；
- 召回样本（如果有）全部进入候选。

## 六、规则

- 不安装、不联网、不构建内核（只编译探针）、不调用大模型（Codex 盲判除外）；只读 `/root/repos/linux`。
- 只读导入旧轮次的代码，不改旧轮次文件；不对外报告。
- 统计行：模型调用 0；Codex 调用按实际；构建 0；新确认缺陷 0；新疑点按实际写。
