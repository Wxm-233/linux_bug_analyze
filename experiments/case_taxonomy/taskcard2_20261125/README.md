# 任务单第二版：改进到达路径的入口和观测点（taskcard2_20261125）

2026-11-25，Claude。用户：“改进入口和观测点”。承接第 6 轮 `taskcard_20261125`，当时 T3 3/7、T4 2/7 没过。

- **判据**：`criteria.md`，写于实现和运行之前，没有修订。
- **只读未改**：第 6 轮的文件和调用图缓存。
  - **与判据写法的出入**：判据第一句写的是“复制 `taskcard.py` 再改，保留 diff”。实际做法是 `taskcard2.py` 只读导入第一版，运行时替换其中的 `reach`、`entry_kind` 两个函数，再加上观测点“后果处”和 CTX 的差分对照。效果相同，所以没有生成 diff。
- **验证集**：3 个第 6 轮没用过的动态实验，标准答案写在实现之前：
  - H `s5dyn`；
  - I `lpaeinv`（它的入口不算独立检验，原因见判据）；
  - J `s8dyn`。

## 结论

**开发集上明显变好；但在验证集上，到达路径和观测点都没过，说明这一版的改进有一部分是照着开发集调出来的。**

| 关口 | 结果 | 要求 |
|---|---|---|
| V1 触发配置（H、I、J） | **3/3** | 必须满足 |
| V2 对照构建（H、I、J） | **3/3**，其中 J 用了新加的 CTX 差分对照：出错 riscv、正常含 x86_64 | 必须满足 |
| V3 到达路径（H、J） | **不过，0/2**；I 单独报告，也没过 | 必须满足 |
| V4 观测点（H、I、J 共 4 个） | **不过，2/4**：H 的 `mm/internal.h:420`、J 的 `smp_call_function_many_cond` 对上了 | 至少 3 个 |
| D1 开发集不退步 | T1、T2 仍是 7/7 | 必须满足 |
| D2 开发集 T3、T4 | T3 **7/7**（第 6 轮 3/7），T4 **6/7**（第 6 轮 2/7） | 只报告 |
| N 噪声（主表 224 份的平均） | 入口 29.7 个（第 6 轮最多 20）；观测点：附近 17.3 个，后果处 21.1 个 | 只报告 |

## 开发集上做对了什么

| 行 | 第 6 轮 | 第二版 |
|---|---|---|
| B、C 回收 | 入口排第 276、224；`get_swap_device` 没找到 | `memory_reclaim` 列出来了（回调：`cftype memory_files.write`）；`get_swap_device` 的 `Bad swap file entry` 在“后果处：交换项解码点”里 |
| D DAX | `handle_mm_fault` 不在路径上 | 回调前补上分发者，路径从 `handle_mm_fault —经 vm_operations_struct.fault 分发→` 开始 |
| E shmem | 入口排第 159；`xas_split_alloc` 没找到 | `shmem_fault` 列出来了；`xas_split_alloc` 在“后果处：ORD 上限的执行处”里，条件是 `xa_shift + 2 * XA_CHUNK_SHIFT <= order` |
| F arm LPAE | 入口排第 329；两个告警都没找到 | `split_huge_pages_write` 列出来了；`leafops.h:400`（`softleaf_migration_sync`）在“后果处”里；`softleaf_entry_wait_on_locked` 仍没找到 |

但有两点要说清楚：
- **D 的路径来得容易**：只要有任何一个缺页回调，分发者就会补上 `handle_mm_fault`。这次命中的回调是 `tegra_bo_fault`，不是实验里的 `ext4_dax_huge_fault`。
- **“交换项解码点”这一节，对所有页表类的行都是同一份**：参数类型为 `softleaf_t` 或 `swp_entry_t` 的 100 个函数里的告警，按报错类优先排，取前 30。它确实包含了 B、C、F 的观测点，但不是针对哪一行算出来的，信息量低。验证集里没有一行需要这条规则，所以它只在开发集上有结果。

## 验证集为什么没过（`diag_val.json`）

| 行 | 没过的关口 | 原因 |
|---|---|---|
| H | V3 | `memory_reclaim` 搜到了，但在 747 个回调里按距离排第 26（距离 10），而前 15 个回调的距离都只有 7～9。**“各取前 15”在新案例上就不够了。** `folio_pte_batch_flags` 是 `mm/internal.h` 里的小函数，从拆页、mprotect、fork 复制、回收都能走到；离它近的入口很多，实验用的回收入口偏远 |
| J | V3 | 这一行来自 df 原表，主表里没有，因此没有边界记录当证据。生成器退回到用钩子函数 `__kernel_map_pages` 作消费者，而它在 5 个构建里都没编入（`DEBUG_PAGEALLOC` 没开），不在调用图里，所以一个入口也没有。调用点函数 `debug_pagealloc_unmap_pages` 其实在图里。**这是第一版就有的缺口**：CTX 行的消费者应该取特征里写的调用点函数 |
| I | V3、V4 | 公共代码不直接调用 `pmd_mkinvalid`，它是经 `pmdp_invalidate` 的通用实现被引出来的（第 3 轮讲过）。任务单的 EC 消费者只取“接口相同”的直接调用者，结果是空的，入口和观测点也就都是空的。如果改用这一行的证据链（`clear_soft_dirty_pmd`、`debug_vm_pgtable` 等），`debug_vm_pgtable` 就在入口里。**这也是第一版就有的缺口** |

H 暴露的是**规则本身的问题**：只按距离挑入口，挑不出“能造出前置状态”的那个入口。I、J 暴露的是**两处实现缺口**，开发集里没有碰到。按判据，验证集上不再改规则，所以照实记为不过。

## 下一步（要另开一轮，并用新的验证案例）

1. **补两处实现缺口**：
   - EC 的消费者，加上把接口引进来的那几条边界记录，和第 3 轮 EC 证据的取法一样；
   - CTX 行的消费者，取特征里写的调用点函数。
2. **入口按“能不能造出前置状态”来挑**：路径上要有能产生前置状态的函数，比如 device-exclusive 要经 `make_device_exclusive`，uffd-wp 要经 userfaultfd。这类入口优先，其余再按距离。
3. **“后果处”改成按行算**：只取与这一行的前置状态种类相关的解码点，比如迁移项取 `softleaf_*migration*`，device-exclusive 取交换项解码，而不是对所有页表类的行都给同一份。
4. **验证案例不够**：现有的动态实验基本都用掉了。要做真正独立的检验，得等新的动态实验，或者在新线索的动态验证里事先生成任务单，再拿实验结果去比。

## 文件

- **判据**：`criteria.md`、`criteria_sha256.txt`
- **代码**：
  - `taskcard2.py`；
  - `diag2.py`：验证集未过原因的诊断。
- **结果**：
  - `cards/<序号>.json`：主表 224 份，加上 J 那 1 份（序号 10201）；
  - `cards_gold.json`：A～J；
  - `result.json`；
  - `diag_val.json`；
  - 日志 `logs/`。
