# 判据：QEMU 验证 arm LPAE `pmd_mkinvalid` 不满足通用约定（lpaeinv_20261122）

2026-11-22，Claude。用户：“先用 QEMU 验证”。对象是第三轮编码一致性引擎的新线索（`ecnoise_20261122` 第三节）：arm LPAE 上 `pmd_present/pmd_leaf(pmd_mkinvalid(pmd_mkhuge(x)))` 为假，而 `mm/debug_vm_pgtable.c:913-930` 要求为真。写于构建和运行之前。

## 一、要回答的两个问题

- **Q1 约定（动态）**：让 arm LPAE 跑公共层自己的自测 `debug_vm_pgtable`（arm 平时不选 `ARCH_HAS_DEBUG_VM_PGTABLE`，所以从不运行），第 928～930 行三条断言各自是否报警。预期（静态）：928（`pmd_trans_huge`）不报，929（`pmd_present`）、930（`pmd_leaf`）报。
- **Q2 后果**：THP 拆分的失效窗口里，并发的缺页、远程读（GUP）、pagemap 读、拆分和合并交错进行时，能否观察到可见的错误。

## 二、内核

- 源码：`git archive df2908090cda` 导出到 `/root/work/lpaeinv/src`（不动 `/root/repos/linux` 工作树）。
- 配置：与第六轮 `nohighpte` 相同（`multi_v7_defconfig` + `ARM_LPAE` + `VMSPLIT_2G` + THP（always）+ `DEBUG_FS` + `DEBUG_VM`，`EXPERT`，关 `HIGHPTE`），另开 `DEBUG_VM_PGTABLE`。
- 唯一的源码改动：`arch/arm/Kconfig` 加 `select ARCH_HAS_DEBUG_VM_PGTABLE if ARM_LPAE`（只为让自测能编进来）。如果自测在 arm 上编译不过，改为加一个只含第 924～930 行同样断言的 `late_initcall` 测试文件，并记录原因。
- 对照内核（只在 Q2 出现异常时构建）：在上面的基础上让失效后的 PMD 仍判为在场（`pmd_mkinvalid` 改为置一个软件位而不是清有效位，`pmd_present`/`pmd_leaf` 认这个软件位），用来判断异常是否归因于本问题。这只是实验用的变异，不是补丁。

## 三、Q2 的测试程序（独立写法、直接发系统调用，与第六轮相同）

QEMU `virt`，`-smp 2`（两个 vCPU 才有真正的并发），内存 1GB。`/init` fork 出：

- **A 拥有者**：映射 8MB 匿名内存（2MB 对齐、`MADV_HUGEPAGE`），每个 4K 页写入可校验的值（页号 ^ 常数），之后只读不写；循环：`MADV_COLLAPSE` 重新合并 → 逐页校验 → 对其中一个 2MB 段做一次跨边界的 `mprotect` 再改回（锁内拆分）。
- **B 拆分者**：循环向 `/sys/kernel/debug/split_huge_pages` 写 A 的区间。
- **C 远程读者**：循环 `process_vm_readv` 读 A 的整个区间并校验；读 `/proc/A/pagemap`，检查区间内每页都“在场、不是交换项”。
- 运行固定时长（120 秒），结束时由 `/init` 汇总并关机；外层 `timeout` 300 秒。

**异常**（任一即算）：A 或 C 校验不符；`process_vm_readv` 返回错误或短读；pagemap 报区间内某页不在场或是交换项；控制台出现 `WARNING`、`BUG`、`Oops`、`bad pmd`；超时或进程卡死。

**覆盖要求**：`/proc/vmstat` 的 `thp_split_pmd` 增量 ≥ 1000，且 `MADV_COLLAPSE` 成功次数 ≥ 1000，否则窗口没被充分触发，Q2 记“不足以判断”。

## 四、判定

- Q1：929、930 报警即“约定违反在运行时得到确认”；不报则静态结论有误，回到第三轮复查。
- Q2：
  - **观察到后果**：实验内核出现异常，对照内核在同样测试下不出现；
  - **未观察到后果**：实验内核 0 异常且满足覆盖要求；
  - **不确定**：异常在对照内核上也出现，或覆盖不足。
- Q2 只能说明“这些路径上看没看到”，不能证明没有后果；结论措辞照此限定。

## 五、其他

不读封存材料；不对外报告；构建完只留 zImage、`.config`、`System.map`、日志，删掉源码副本和构建目录；不用用户态 `qemu-arm` 运行 guest 程序。
