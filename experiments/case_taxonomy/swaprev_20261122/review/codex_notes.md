# 交换项编解码独立复核

基准提交 `df2908090cda`。判据 SHA256 为 `e2a6bed9c5c4bbf1a1daa1b3e11855b18ba2fd457dc56b2255e15b606af66064`。依据为源树、提交差异及题包列出的八份配置。内核构建与运行次数均为 0。

## 公共表示

`include/linux/xarray.h:49` 给出机器字位数减一，`include/linux/swap.h:42` 给类型留 5 位。因此 32 位和 64 位构建的公共偏移分别有 26 和 58 位。未定义 MAX_PHYSMEM_BITS 时，`include/linux/swapops.h:35-43` 还用物理地址类型宽度减 PAGE_SHIFT 限制 PFN。前六项都是 FLATMEM；`include/linux/page-flags-layout.h:29-34` 对稀疏内存头的包含有条件。公共层在 `include/linux/swapops.h:89` 掩掉偏移字段之外的位。R1 至 R6 问的是 PFN，R6 的判断不能推广到任意 26 位偏移。各构建的普通交换类型均在 5 位内，架构类型字段均能容纳。

## 平台证据的边界

- R1 按题设接受架构说明作为合法输入的依据。40 位 LPAE 描述符支持的物理地址超出 24 位 PFN 的覆盖范围。FLATMEM 按起始页帧计算 mem_map 下标（`include/asm-generic/memory_model.h:18-20`），ARM 可以使用运行时的物理基址（`arch/arm/include/asm/memory.h:187-193,382`）。因此页帧的绝对编号可以较大，同时内存跨度较小。此结论没有指定已观测到该问题的实机。
- R2 的裁定限定为题包给出的 Malta 板。XPA 格式在 `arch/mips/include/asm/pgtable-32.h:153-155` 给出 40 位上限；单看该上限会忽略 Malta 的 DDR 映射。R3 的 36 位地址空间恰好用满 24 位 PFN。
- R4 的 48 位稀疏内存常量有 CONFIG_SPARSEMEM 守卫（`arch/mips/include/asm/sparsemem.h:4-17`）。页帧是否需要第 41 位取决于平台实际实现的物理地址空间和 RAM 布局。XKPHYS 字段宽度本身无法作实机证据。

## 两个原生测试

两份 defconfig 都关闭 CONFIG_DEBUG_VM_PGTABLE，结果描述测试体执行时的静态求值。LoongArch 配置启用了 ARCH_HAS_PMD_SOFTLEAVES 和透明大页，测试体另在 `mm/debug_vm_pgtable.c:828` 检查运行时大页支持。

R7 中 PROTNONE 位为 8，偏移从位 9 开始，最高 5 位保存类型，留下 50 位。`arch/x86/include/asm/pgtable.h:940,959` 对零 PTE 得出 none 为真、present 为假。生产函数返回可编码最大偏移加一。对照 a3a3e215c9c1 的父提交，测试原本直接解码；同次改动对生产函数保留了直接解码路径。

R8 的 48 位物理地址上限见 `arch/loongarch/include/asm/sparsemem.h:14`。扣除 14 位页内偏移，PFN 占位 0 至 33；即使保留 young、dirty，位号也仅到 35（`include/linux/swapops.h:63-65`）。`arch/loongarch/include/asm/pgtable-bits.h:35-45` 定义 HUGE 和 PRESENT_INVALID。`include/linux/leafops.h:98,652-657` 使 present PMD 无法通过有效性判断。2025-11-10 的 c0a80c2ce68d 同时引入全一迁移项和有效性断言。后来的 608c74559718 仅替换转换函数入口。
