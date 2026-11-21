# 线性映射地址检查（linmap_20261119）

2026-11-19，Claude。用户：“按漏报补规则”。依据 `h2miss_20261119`，规则 A：只认线性映射地址的接口，被用在了不在线性映射里的地址上（类型一致性检查 · 地址类别）。

- 判据 `criteria.md`（2801436f…），两份修订都写在看到 zswap 开发样本失败之后，所以 zswap 只算开发结果：
  - 修订 1：同一函数内跟踪字段访问路径（`a->b`）；
  - 修订 2：只在同一层重新赋值时撤销标记（goto 跳过外层赋值的情况）。
- 统计行：Codex 调用 1 次（盲判 80 条，周额度 58% → 61%）；其他模型调用 0；构建 0。

## 做法（`linmap.py`）

- **接收者**：`virt_to_phys`、`__pa`、`virt_to_page`、`virt_to_pfn`、`virt_to_folio`、`virt_to_head_page` 的第 1 个参数，`sg_init_one`、`sg_set_buf` 的缓冲区参数。
- **来源**：
  - 镜像符号（`extern char X[]`）；
  - 同一函数里由 vmalloc、vmap、kmap、ioremap、memremap 调用赋值的变量或字段路径；
  - 来源函数（返回值摘要，含同一子系统内的 ops 回调），迭代到不再新增。
- **守卫**：同一函数里，变量出现在 `virt_addr_valid`、`is_vmalloc_addr` 等函数的参数里，就不报。
- **范围**：不在 `arch/` 下的全部 `.c` 文件，不编译。一个版本约 2.5 分钟，内存约 1 GB。
- **受影响架构**：从源码机械推出。
  - 镜像符号：自己定义 `__pa_symbol` 的架构（arm、arm64、csky、mips、riscv、x86）；
  - kmap：定义了 HIGHMEM 的架构；
  - vmalloc、ioremap：全部架构。

## 结果

| 检验 | 结果 | 参考线 |
|---|---|---|
| 自测 | 13/13 | — |
| 开发样本（修订 2 之后） | 4/4：btf 修复前报出 `virt_to_phys(__start_BTF)`、修复后不报；zswap 修复前报出 `sg_init_one(src)`，链路 `zpool_map_handle → ->map → zs_zpool_map → zs_map_object → kmap_atomic`，修复后不报 | — |
| 当前版本候选 | 5 条（memremap/ioremap 4、经来源函数 1），**还没两人审** | 可能 ≥ 20% |
| **独立召回** | **0/25** | ≥ 50%，**未达** |

### 独立召回样本

- 从内核历史里机械挖出 80 个提交：删掉的行用了接收者，加上的行换成了 `__pa_symbol`、`vmalloc_to_page`、`virt_addr_valid` 等。
- 挖的时候按提交号排除了新评测集两个集合和开发样本（150 个 id）。
- 我和 Codex 盲判：80 条里 74 条一致，κ = 0.846；6 条分歧由我裁定（`adjudication.json`）。最后“是”25 条。

### 0/25 的原因（按样本标题和补丁归类）

1. **地址从参数或结构体字段传进来**（约 18 个）：缓冲区是调用方传进来的，或者是别处 `dma_alloc_coherent`、vmalloc 后存进结构体字段的。现在的规则只看同一函数里的赋值和返回值摘要，看不到“调用方传进来一个 vmalloc 或栈地址”。例子：bcachefs 加密路径的栈缓冲区、SMB3 的 `buf`、dm-verity 的 bufio 数据、ttm 的 `d_page->vaddr`。
2. **镜像符号的形式更多**（6 个）：函数名（`cpu_resume`）、带长度的数组（`kasan_zero_page[PAGE_SIZE]`）、全局结构体取地址（`&vmcoreinfo_note`）、由镜像符号赋值的局部变量（`textlow = _stext`）、静态的 `pgdat`。现在只认 `extern char X[]`。
3. 另有 1 个（kasan `virt_to_page(addr)`）的地址同样是参数传入。

**结论**：这条规则在开发样本上能跑通、当前版本候选很少（噪声低），但覆盖的形态太窄，独立召回为 0。要提高召回需要：
- **参数流**：函数的参数流到接收者，就看调用方传进来的是不是映射地址；
- **把 `dma_alloc_coherent` 也算作来源**：在 arm64 等非一致性 DMA 的架构上，它可能返回 vmalloc 区的重映射地址，这本身就是跨架构差异；
- **放宽镜像符号的形式**：全局对象取地址、函数名、任意类型的全局数组。

## 文件

- `criteria.md`、`criteria_amendment1.md`、`criteria_amendment2.md`、`criteria_sha256.txt`
- `linmap.py`、`run.sh`、`dev.json`、`dev*.log`、`head.json`
- `mine.py`、`mined.json`、`packets/`、`claude_labels.json`、`codex_labels.json`、`codex_label_prompt.md`、`adjudication.json`
- `recall.py`、`recall.json`、`recall_runall.log`
- WSL 缓存：`/root/work/commitmode_cache/LM/`
