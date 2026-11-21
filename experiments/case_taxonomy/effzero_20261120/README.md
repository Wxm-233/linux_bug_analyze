# 效果依赖版实现一致性检查：清零效果族 E-ZERO（effzero_20261120）

2026-11-20，Claude。用户：“开始写检查”。gpt-6.2-astra 规划（`plan_20261120/astra_plan.md`）第 6～8 天。模板只用 `effsupply_20261120` 的设计侧材料；晚期 4 个根因由评分者保管，我没读。

- 判据 `criteria.md`（75a05200…），写于任何实现和运行之前。
- 修订 1（26cb1e6e…，X1 父版本第一次运行后）：ops 成员调用要能确定结构体类型；实现自己写了内容的对象不算“不清零”；E2 的“接口确实清零”改为“至少一条路径清零”。
- 修订 2（03d0e413…，开发重跑中途）：请求位收窄（不含 `GPIOF_INIT_HIGH` 这类）；E1 报不清零的来源函数，命中也按来源函数算；E3/E2 穿过最多 2 层包装找实现组；E3 补上 R1。
- 不改定义的实现修正 4 条，记在 `devlog.md`。代码在扫当前版本前冻结（`frozen_sha256.txt`）。
- 统计行：Codex 调用 1（盲审，周额度 67% → 68%）；其他模型调用 0；构建 0；新确认缺陷 0；**新疑点 2**（强）+ 1（弱）。

## 检查做什么

同一个接口有多个实现（各架构的同名定义，或同一种 ops 表里的同一个成员）。分三种写法：
- **E1 返回值形**：多数实现在所有正常返回路径上都把返回的新内存清零，少数实现有正常返回路径不清零，就报这几个少数实现。
- **E2 调用方委托形**：调用方调了接口之后，马上把自己的“还要清零”开关置为假，而接口的某些实现根本不清零（X1 那一种）。
- **E3 请求标志形**：调用方传了清零请求位，接口的某个实现在用到请求位之前就正常返回了（K1 那一种）。

做法是纯词法分析，不编译：按语句树逐条走路径，记录对象的来源（分配函数、是否带 `__GFP_ZERO`，宏也展开）和清零动作，再按名字在全树迭代出函数摘要。全树一次 7～11 分钟，峰值 2～3.7 GB。

## 设计侧回归（`devcheck.py`，门槛：6 个里命中 ≥ 4，三个反例都不报）

| 样本 | 结果 | 说明 |
|---|---|---|
| D1 arm64 DMA 分配不总清零 | **命中** | 报出 arm64 `__dma_alloc`，来源函数 `__alloc_from_pool`，正是修复改的函数 |
| D3 公共层去掉 `__GFP_ZERO`（arc、s390 不清零） | **命中** | `s390_dma_alloc`。另外 s390 的 `pgd_alloc` 也按“说明点名的架构”算了命中，那是评分规则的漏洞，与 DMA 无关 |
| D4 arm64 IOMMU 连续分配 | 漏 | 被报函数本身判对了，但当年 `dma_map_ops.alloc` 组里不清零和判不了的实现太多，凑不成多数 |
| D5 通用 remap 分配器 | 漏 | 各架构实现多经过 `ioremap_nocache` 等地址转换，分析器判为未知，同样凑不成多数 |
| X1 零页清零被跳过 | **命中** | 排第 1，`post_alloc_hook`，指出通用 `tag_clear_highpage` 是空实现 |
| K1 KASAN HW_TAGS 提前返回 | **命中** | `__kasan_unpoison_vmalloc` |
| 反例 C1、C3、C4 | 都没报 | C2、D2（`copy_from_user`）不在三种写法内，属模板覆盖缺口 |

**4/6，反例 0：门槛通过。**

## 当前版本 df2908090cda（`runcur.py` → `cur/`）

| | E-ZERO（本检查） | 按早期补丁写法匹配 | 八项检查基线 |
|---|---|---|---|
| 候选 | **13**（E1 11、E3 2；7 个组） | 105（P1 1、P4 3、P5 101） | 938（728 个文件+函数） |
| 有架构证据 | 9 | — | — |
| 被报文件在至少一个 defconfig 里编入 | 5 | — | — |
| 与基线重叠 | 0 | 0 | — |
| 两个新方法之间重叠 | 0 | 0 | — |

E-ZERO 的 13 条都是基线之外的新增。“前 20 条”的预算覆盖了全部 13 条。

### 两人审查（`review/`）

我先判，写进 `claude_labels.json`；Codex 盲判（`codex_labels.json`、`codex_notes.md`），没看我的结论。**一致 10/13，κ = 0.54**；裁定见 `adjudication.json`。

| 序 | 被报实现 | 我 | Codex | 裁定 |
|---|---|---|---|---|
| 1 | arm32 `arm_iommu_alloc_attrs`（来源 `__alloc_from_pool`） | 确认 | 可能 | **可能（强）** |
| 2 | powerpc `ps3_alloc_coherent` | 排除 | 排除 | 排除：局部 `flag \|= __GFP_ZERO` 没跟踪 |
| 3 | powerpc `ibmebus_alloc_coherent` | 可能 | 证据不足 | **可能（弱）** |
| 4 | Xen `xen_grant_dma_alloc` | 确认 | 证据不足 | **可能（强）** |
| 5 | `dma_direct_alloc`（不建内核映射的路径） | 证据不足 | 证据不足 | 证据不足：显式去掉 `__GFP_ZERO`，像是有意的 |
| 6 | `dl_seq_start` | 排除 | 排除 | `*bucket = …` 写入没认出 |
| 7 | arm64 `pgd_alloc` | 排除 | 排除 | `gfp = GFP_PGTABLE_USER` 局部变量里的常量没跟踪 |
| 8、9 | sh、sparc64 `pgd_alloc` | 排除 | 排除 | slab 构造函数清零 |
| 10 | `dma_pool_alloc`（E3） | 排除 | 排除 | `want_init_on_alloc()` 在内部测了请求位 |
| 11 | `mem_dump_obj`（E3） | 排除 | 排除 | 把 `ZERO_SIZE_PTR` 当成了请求位 |
| 12、13 | DRM 格式数组、`mptscsih_info` | 排除 | 排除 | 内容按计数或终止符写满 |

**两条强疑点**：
- **arm32 原子池不清零**：
  - 2018 年的 `518a2f1925c3`（“dma-mapping: zero memory returned from dma_alloc_*”）定下了“DMA 分配器返回的内存要能映射给用户态，所以分配时必须清零”。
  - arm32 非一致性设备的原子分配（`GFP_ATOMIC`）走 `__alloc_from_pool`，从自己的原子池取块；块在 `__free_from_pool` 里只还给池、不清零，下次分配拿到的是上一个使用者的内容。IOMMU 路径和普通路径（`pool_allocator`，成员调用，检查没报到）都是这样。
  - arm64 在 2015 年因完全相同的问题修过（`6829e274a623`，即 D1），通用池 `kernel/dma/pool.c` 第 318 行也会清零。
- **Xen grant DMA 分配不清零**：
  - `xen_grant_dma_alloc` 是 2022 年新加的（`d6aca3504c7d`），用 `alloc_pages_exact(…, gfp)` 分配，不清零；`dma_alloc_attrs` 也不会补上 `__GFP_ZERO`。
  - 这些页随后通过授权共享给后端域，virtio 分割环分配后也不自己清零。这组 ops 本来就是为了限制后端能看到的内存而加的。

分歧原因：Codex 没找到 `518a2f1925c3`，只引了 2018 年更早的 `e89f5b370153`（那时说这条约定“没写进文档”）；它也指出这几条都没做端到端验证。所以裁定从严，记为“可能”，不记确认。

## 结论

1. **检查写成了**：设计侧 4/6 命中、反例 0；当前版本报 13 条，规模适合人工审，全部是八项检查之外的新增。
2. **当前版本有 2 条证据链完整的强疑点**：请求或约定、违反的路径、使用者三段都能由第二人核查。规划第 9～10 天的第二条继续线是“当前版本至少 2 条有完整效果依赖证据”，从证据完整这一点看达到了。但两人裁定都是“可能”，不是确认，这一点要如实说明。
3. **误报的主要原因**（13 条里 9 条排除）：局部变量里的标志和常量没跟踪（2 条）；slab 构造函数清零（2 条）；解引用写入、按计数写入没认出（3 条）；清零请求藏在辅助判断函数里（1 条）；`ZERO_SIZE_PTR` 被当成请求位（1 条）。都能修，但冻结后不再改，留给下一轮。
4. **对照**：“按早期补丁写法匹配”报 105 条，P5 那 101 条是噪声；我粗看了 P1、P4 的 4 条，都不是问题。它和本检查、基线都没有重叠。我没做两人审，只是粗看。

## 下一步

1. **第 9～10 天，晚期回放**（由评分者做，我不看内容）：在 4 个晚期独立根因各自的修复前版本上，跑冻结版 `effzero.py`、对照和八项基线，由评分者判严格命中；继续线是“新增严格命中至少 2 个不同根因”。
2. **两条强疑点的后续**：先查上游邮件列表和更新的主线有没有人报过或修过；arm32 原子池可以在 QEMU 上用一个原子分配的小模块验证“再分配拿到旧内容”。是否上报由用户决定。

## 文件

- 判据：`criteria.md`、`criteria_amendment1.md`、`criteria_amendment2.md`、`criteria_sha256.txt`、`frozen_sha256.txt`、`devlog.md`
- 检查：`effzero.py`（`selftest` / `facts` / `run`）、`patchmatch.py`（对照二）、`debug.py`（开发用）、`runone.sh`、`rundev.sh`、`runcur.sh`、`runcur.py`、`py.sh`
- 开发回归：`devcheck.py`、`devcheck.json`、`dev/`（6 个父版本的候选和日志）
- 当前版本：`cur/effzero.json`、`cur/patchmatch.json`、`cur/summary.json`、`cur/runcur.log`
- 审查：`review/packets.md`、`review/top20.json`、`review/claude_labels.json`、`review/codex_prompt.md`、`review/codex_labels.json`、`review/codex_notes.md`、`review/adjudication.json`
- 第一阶段缓存在 WSL `/root/work/effzero/`（每个版本 33～63 MB，共 319 MB）
