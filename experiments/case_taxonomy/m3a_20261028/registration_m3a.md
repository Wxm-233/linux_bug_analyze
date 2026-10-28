# 方法版本M3a登记：Kbuild适用性事实（实现与回归前写定）

2026-10-28。用户批准“Register M3a”。基于M3（`m3_20261028/registration_m3.md`，回归s04不符、未冻结）。**M3a是在看到M3的s04回归结果（sparc64/s390上未参与构建的libstub文件产生观察）之后写定的；die、shmem、s04只作回归用例。**

## 改动（只增加一项适用性事实，其余同M3）

- **`kbuild_selected(file)`**：判定消费者文件在该上下文的`.config`下是否会被Kbuild构建。对`d/f.c`（目标`f.o`）：
  1. 在`d/Makefile`（若有`d/Kbuild`一并读取）中按行（合并续行）收集赋值`obj-y`、`obj-m`、`lib-y`、`obj-$(CONFIG_X)`、`lib-$(CONFIG_X)`，以及复合对象的`foo-y`、`foo-objs`、`foo-$(CONFIG_X)`。
  2. `f.o`出现在`obj-…`/`lib-…`中：条件为`y`/`m`或`CONFIG_X`取值为`y`/`m`时选中；出现在复合对象`foo`的部件列表中：该部件条件成立且`foo.o`本身（递归）被选中时选中。多条赋值任一成立即选中。
  3. 目录`d`本身须被选中：在父目录`Makefile`中以`obj-…`或`subdir-…`加入`basename(d)/`，条件同上，递归至顶层；顶层目录（路径只有一级，如`mm`、`kernel`、`drivers`）视为选中。
  4. 只在Makefile条件块（`ifeq`/`ifneq`/`ifdef`/`ifndef`…`endif`）内出现的赋值、或找不到任何赋值时，结果为**未知**（事实不可答）。
- **契约**：所有F1/F1d/F2/F3实例的scope由恒真改为`kbuild_selected`（适用条件角色）。未选中→不适用；未知→事实不可得。关系不变。

不改：F1b、F1d、F2b＋M2a门控、F3、执行器的追踪失败记录与按文件构建、判定与追踪上下文、主线标注、复核(a)—(d)、报告指标、M3选样修正。不调用模型。

## 回归与事先预期（冻结前，不符则停止、不改规则）

依据写定前读到的三处Makefile：`drivers/base/Makefile`中`topology.o`在`obj-y`续行内；`mm/Makefile`中`shmem.o`在`obj-y`内；`drivers/firmware/efi/libstub/Makefile`中`string.o`为`lib-$(CONFIG_EFI_GENERIC_STUB)`，目录为`subdir-$(CONFIG_EFI_STUB) += libstub`，上层`obj-y += efi/`、`obj-y += firmware/`，均不在条件块内。

- die：所有上下文选中，结果同M3：只在父版报11、只在修复版报0、两版都报6（全部主线已解决）。
- shmem：所有上下文选中，结果同M3：1 / 0 / 0。
- s04：arm64、arm64 64K选中（`EFI_STUB`、`EFI_GENERIC_STUB`为y），F3 `__HAVE_ARCH_STRNCMP`只在父版报恰为这两格；x86_64与x86_64无SMP不选中（x86不用通用stub）、s390与sparc64不选中，均判不适用；riscv不判违反（选中则无该宏而满足，未选中则不适用）；只在修复版报0；两版都报0（M3中s390的`strstr`观察消失）。

全部符合后写`method_freeze_v3a.json`（方法文件、执行器、两份登记与回归结果的SHA、工具链版本），之后经用户同意再处理阶段B或补足样本。
