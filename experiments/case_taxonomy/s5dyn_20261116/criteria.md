# 判据：动态验证新疑点 S5（调试构建下 folio_pte_batch 拿到 device-exclusive 项）（s5dyn_20261116）

2026-11-16，Claude。用户：“验证 S5”。本文件和 `predictions.json` 在构建、运行之前写定，SHA 存入 `criteria_sha256.txt`。

## 一、疑点

`xvlift_20261116` 提升候选第 15 条，裁定为“可能（仅调试构建）”：

- `folio_referenced_one`（`mm/rmap.c:969-975`）只查 `pvmw.pte && folio_test_large(folio)`，就把 `ptep_get(pvmw.pte)` 交给 `folio_pte_batch()` → `folio_pte_batch_flags()`；
- 后者要求 present：`mm/internal.h:420` 是 `VM_WARN_ON_FOLIO(!pte_present(pte), folio)`，`:422` 是 `VM_WARN_ON_FOLIO(page_folio(pfn_to_page(pte_pfn(pte))) != folio, folio)`；
- `make_device_exclusive()` 用 `FOLL_SPLIT_PMD`，只拆 PMD 映射、不拆 folio，所以大页 folio 的某个 PTE 可以是 device-exclusive；
- 预期开 `CONFIG_DEBUG_VM` 时，回收会在 420 行报 WARNING（各架构都会）。x86_64 的 `pte_pfn` 对交换项按 L1TF 规则取反，读出的 pfn 是错的，422 行还会对它取 `struct page`，可能再报一次 WARNING，或者访问到没有映射的地址。

## 二、内核（写死）

1. kbuild 新配置档 **`dbgvm`** = `dyn` + `DEBUG_KERNEL=y` + `DEBUG_VM=y`（MGLRU 仍关，与 `dyn` 相同）。版本 `df2908090cda`，三个架构。
2. 修复变异 **F5**（`tools/kbuild/mutations/s5dyn.json`）：第 969 行的条件改为 `pvmw.pte && folio_test_large(folio) && pte_present(ptep_get(pvmw.pte))`，只对 present 项做批处理。
3. 镜像：三个架构各 `dbgvm` plain、`dbgvm` F5；对照用现有的 `dyn` plain（不开 DEBUG_VM），x86_64、riscv 各一个，不重新构建。

## 三、测试（写死）

测试程序 `s5.c` 由 s4dyn 的 `s4.c` 改来，S2 改成下面的 **S5**：

1. 运行时把 `/sys/kernel/mm/transparent_hugepage/enabled` 设为 `always`；
2. 映射 2MB 对齐的 2MB 匿名区域，`MADV_HUGEPAGE`，逐页写入已知内容；从 `/proc/self/smaps` 读 `AnonHugePages`，确认是 THP；
3. 用 HMM 测试模块把第 8～15 页（共 8 页）设成 device-exclusive。这一步会把 PMD 拆成 PTE，但不拆 folio；
4. 记录“folio 仍是大页”的证据：用 pagemap 和 `/proc/kpageflags` 看第 0 页（present）的 COMPOUND_HEAD/TAIL、THP 标志；
5. cgroup v2 `memory.reclaim` 三次；记录回收前后第 8～15 页的 pagemap 交换类型；之后由 CPU 读回全部 512 页，核对内容，30 秒看门狗。

运行矩阵（各 3 次）：
- `dbgvm`：x86_64、riscv、arm64 各 plain、F5；
- `dyn`：x86_64、riscv 各 plain；

共 24 次。冒烟测试另跑，不计入。

## 四、判定（写死）

- **有效**：确认是 THP（`AnonHugePages` ≥ 2048 kB），device-exclusive 设置成功（ioctl 返回 0，并且回收前第 8～15 页 pagemap 显示交换项），回收前 folio 仍是大页（kpageflags 显示 THP 或 COMPOUND）。
- **异常（S5）**：测试阶段（从 S5 开始之后）的内核日志里，有位于 `mm/internal.h:420` 或 `:422` 的 WARNING，或有 Oops、`Unable to handle`、`BUG:`。
- 另外分别记录：回收后的交换类型分布、内容错误、SIGBUS、看门狗超时。这些对应 B-2，不计入 S5。
- 每格的结论：有效次数中异常 ≥2 记“复现”；异常 0 记“不复现”；其余记“不稳定”；有效次数 <2 记“无效”。

## 五、S5 成立的条件（写死）

同时满足：
1. `dbgvm` plain：x86_64、riscv 都“复现”；
2. `dbgvm` F5：x86_64、riscv 都“不复现”；
3. `dyn` plain（无 DEBUG_VM）：x86_64、riscv 都“不复现”（说明只影响调试构建）。

arm64 的两格只用来核对预测：arm64 同时会触发 B-2 改坏项。

## 六、规则

- 不安装、不联网、不调用大模型；只读 `/root/repos/linux`，变异只打在构建树里；不对外报告。
- 新构建树只留可复用的部分。
- 统计行按实际写。
