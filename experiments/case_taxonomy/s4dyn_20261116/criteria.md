# 判据：动态验证新疑点 S4（B-2 的 MGLRU 变体）（s4dyn_20261116）

2026-11-16，Claude。用户：“动态验证 S4”。本文件在构建、运行之前写定，SHA 存入 `criteria_sha256.txt`；预测写在 `predictions.json`，同时记 SHA。

## 一、疑点

`xvlift_20261116` 的提升候选第 4 名，两人都判“可能”：

- `folio_referenced_one`（`mm/rmap.c`）在 `lru_gen_enabled() && !lru_gen_switching() && pvmw.pte` 时走 `lru_gen_look_around(&pvmw, nr)`（982-984 行），不查 present；
- `pvmw.pte` 可以是 device-exclusive 项；
- `lru_gen_look_around` 调用 `test_and_clear_young_ptes_notify`，在 arm64 上走到 `__ptep_test_and_clear_young`，无条件写回 `pte_mkold`，清掉 AF（第 10 位），把 device-exclusive 的交换类型 30 改成 14。

B-2（p1dyn 的 S2）走的是另一个分支（`clear_flush_young_ptes_notify`），当时的内核关了 MGLRU。p1dyn 的修复变异 F2 只守住了那个分支。

## 二、内核（写死）

1. kbuild 新配置档 **`mglru`** = `dyn` + `LRU_GEN=y` + `LRU_GEN_ENABLED=y`。版本 `df2908090cda`。
2. 修复变异：
   - **F4**（新，`tools/kbuild/mutations/s4dyn.json`）：只在 MGLRU 分支里加 `if (!pte_present(ptep_get(pvmw.pte))) referenced++; else`，再调 `lru_gen_look_around`；
   - **F2**（复用 `p1dyn.json`）：只守经典分支。
3. 镜像：arm64 的 plain、F2、F4；x86_64、riscv 的 plain（对照）。只改 `.c` 的变异在同一棵树上增量构建。

## 三、测试（写死）

测试程序 `s4.c` 由 p1dyn 的 `pdyn.c` 改来：只保留 S2（64 页 device-exclusive → cgroup `memory.reclaim` 三次 → 看 pagemap 交换类型、CPU 读回内容、30 秒看门狗）。另加一项：从内核命令行读 `s4mglru=1|0`，在测试前往 `/sys/kernel/mm/lru_gen/enabled` 写 `y` 或 `n`，再把读回的值记下来。QEMU 参数、NUMA、zram 与 p1dyn 相同。

运行矩阵：
- arm64 × {plain, F2, F4} × MGLRU {开, 关} × 3 次；
- x86_64、riscv 的 plain × MGLRU 开 × 3 次；

共 24 次。

## 四、判定（写死，沿用 p1dyn 对 S2 的定义）

- **有效**：device-exclusive 设置成功（ioctl 返回 0，并且回收前 pagemap 有交换项或检查返回 -EPERM），并且读回的 MGLRU 状态与要求一致（开：非 0；关：0）。
- **异常**：回收后出现 0、30 以外的交换类型；或有页内容不对、SIGBUS；或看门狗超时；或内核日志有 `Bad swap`、`BUG`、`WARNING`、`Oops`。
- 每格（内核 × MGLRU 模式）的结论：有效次数中异常 ≥2 记“复现”；异常 0 记“不复现”；其余记“不稳定”；有效次数 <2 记“无效”。
- 另外记录回收后的类型分布，用来区分“页被换出到 zram（类型 0）”和“页没被回收、仍是 30”。

## 五、S4 成立的条件（写死）

同时满足：
1. arm64 plain、MGLRU 开：复现；
2. arm64 F2、MGLRU 开：复现（守住经典分支消不掉，说明不是 B-2 那条路）；
3. arm64 F4、MGLRU 开：不复现（守住 MGLRU 分支就消掉）。

满足就报告给用户，由用户决定是否记为确认缺陷。另外 4 格（arm64 三种内核关 MGLRU、x86_64 与 riscv 开 MGLRU）只用来核对预测，不影响 S4 是否成立。

## 六、规则

- 不安装、不联网、不调用大模型；只读 `/root/repos/linux`，变异只打在 kbuild 构建树里。
- 不对外报告。
- 新构建只留可复用的部分，其余删掉。
- 统计行：模型调用 0；Codex 调用 0；构建按实际；新确认缺陷由用户决定；新疑点按实际。
