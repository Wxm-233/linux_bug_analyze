# 复核判据：最新主线、修复副作用、x86 对照（rvpud_20261124 第二阶段）

2026-11-24，Claude。用户：“登记一下吧，另外你再确认一下这个是不是真的有问题，真有问题的话我们可以发邮件了”。写于第二阶段任何构建和运行之前。第一阶段（`criteria.md`，df2908090cda）结论为“复现”。

## 一、要回答的三个问题

1. **最新主线上还在不在**：本地最新主线 `65e4fd942f72`（v7.4-rc3-406，2026-11-19）。联网核对过，v7.4-rc4、linux-next、riscv 树的相关头文件与它一致。
2. **修复对不对、有没有副作用**：修复 F（`pud_leaf` 只看 `_PAGE_LEAF`）在开调试的内核上是否引起新的告警。
3. **是不是 riscv 独有**：x86_64 在同一程序下表现是否正确（x86 已由 `144bb0aee33a` 修过）。

## 二、内核

新配置档 `pfnmapdbg` = `pfnmap` + `DEBUG_KERNEL`、`DEBUG_VM`、`DEBUG_VM_PGTABLE`、`PAGE_TABLE_CHECK`、`PAGE_TABLE_CHECK_ENFORCED`。三个镜像：

- R0：`65e4fd942f72 riscv pfnmapdbg`（原内核）
- RF：同上 + 变异 `rvpud.json:F`（预检同第一阶段）
- X0：`65e4fd942f72 x86_64 pfnmapdbg`（原内核）

QEMU 与第一阶段相同；x86_64 用 `-M q35 -cpu max`，`console=ttyS0`。触发程序 `rvpud.c` 不变（x86 用 x86_64 交叉编译器）。

## 三、试验（每项 3 次）

| 编号 | 内核 | 模式 | 预测 |
|---|---|---|---|
| M1 | R0 | A（PROT_NONE→munmap） | 出现 `bad pud` |
| M2 | R0 | C（PROT_READ→munmap） | 不出现 |
| M3 | R0 | D（PROT_NONE→RW→访问） | 内核崩溃（Oops/panic），没有 `@@END 0` |
| M4 | RF | A | 不出现 `bad pud`，正常结束 |
| M5 | RF | D | 不崩溃，子进程读回 0x5a5a、写入成功，正常结束 |
| M6 | X0 | A | 不出现 `bad pud`，正常结束 |
| M7 | X0 | D | 不崩溃，子进程读回 0x5a5a，正常结束 |

每次运行的前提核对同 `criteria.md` 第三节（`order = 18 ... 0x100`；x86 的 PUD 也是 order 18）。没有这一行，该次不可评。

**副作用检查（RF 的每次运行都看）**：开机时 `debug_vm_pgtable` 自测不能有 WARNING/BUG；整个运行中不能出现 `WARNING:`、`BUG:`、`page_table_check` 报错、`Oops`。R0 的 M1、M2 运行中也看这几项，作为基线（M3 的崩溃除外）。

## 四、结论怎么下

- **问题确认**：M1 3/3 出现 `bad pud`；M3 3/3 崩溃；M2 0/3；三项都可评。
- **修复成立**：M4、M5 各 3/3 正常、0 `bad pud`、0 崩溃，且 RF 没有基线之外的新告警。
- **x86 对照成立**：M6、M7 各 3/3 正常。若 x86 的前提核对不过（例如 x86 没建成 PUD 映射），记为“x86 对照不可评”，不影响前两项。
- 三项都成立，才建议发邮件；否则如实报告哪一项不成立。
