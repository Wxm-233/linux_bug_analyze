# 核实 evcard 的完整线索：x86 `amd_get_mmconfig_range()` 在 32 位非 PAE 内核上截断 MMCONFIG 基址（amdmmcfg_20261121）

2026-11-20 晚，Claude。（目录名里的 20261121 是当时把日期记错了，实际是 11-20。）用户：“核实 AMD 这条”。线索来自 `evcard_20261121`（新排序第 1 条完整线索，两人都判完整线索）。

- 这是对单条线索的事实核对：上游检索、配置事实、读代码。没有事先写判据，也没设去留门槛，**属于偏离项目惯例**，在此说明。用户已要求登记为 **B-2026-11-20-2**（`../../confirmed_bugs.md`），并决定验证不了就先不追；是否上报由用户决定。
- 统计行：模型调用 0；构建 0（只生成了一次 `i386_defconfig` 配置，没有编译）。

## 结论

**静态证据链完整，判为“可能（强）”；动态验证做不了；上游没查到有人报过或修过。** 影响面窄：只在“32 位非 PAE x86 内核 + 跑在 BIOS 把 MMCONFIG 基址放到 4G 以上的 AMD Fam10h 及以后机器”上出现。

## 证据

1. **截断**（`arch/x86/kernel/amd_nb.c:160-167`，`df2908090cda`）：
   - `base = msr & (FAM10H_MMIO_CONF_BASE_MASK << FAM10H_MMIO_CONF_BASE_SHIFT)`，掩码 `0xfffffff << 20`，即第 20～47 位，基址最多 48 位；
   - `res->start = base; res->end = base + (1ULL << (segn_busn_bits + 20)) - 1;`，赋值前不检查 `resource_size_t` 放不放得下。
2. **32 位默认配置就是这样**（`i386_defconfig.config`，用 `make ARCH=i386 i386_defconfig` 生成）：
   - `CONFIG_X86_32=y`；`CONFIG_X86_PAE`、`CONFIG_PHYS_ADDR_T_64BIT` 都没设，所以 `resource_size_t` 是 32 位；
   - `CONFIG_AMD_NB=y`、`CONFIG_PNP=y`、`CONFIG_PCI_MMCONFIG=y`，这个函数和两个使用者都会编进内核。
3. **两个使用者都拿截断后的值做事**：
   - `drivers/pnp/quirks.c:294` 起的 `quirk_amd_mmconfig_area()`（`#ifdef CONFIG_AMD_NB`，挂在 `PNP0c01` 上）：用 `mmconfig->start/end` 判断和 PNP 资源是否重叠，并 `pnp_add_mem_resource()` 补加保留区，范围会落在错误的低地址上；
   - `arch/x86/pci/amd_bus.c:212-274`（`postcore_initcall`，只要求 AMD/Hygon CPU 和北桥设备，没有 64 位限制）：用它从根总线的 MMIO 范围里扣除，并调整 MMIO 窗口，扣掉的也是错误的低地址范围。
4. **作者知道这个位宽问题**：同一个 `amd_bus.c` 第 54 行有 `cap_resource()`，第 317 行用它把其他范围限制在 `RESOURCE_SIZE_MAX` 以内；但 MMCONFIG 的范围在 `amd_get_mmconfig_range()` 里已经被截断，这个保护管不到。
5. **64 位上没问题**：64 位内核的 `resource_size_t` 是 64 位。值得一提的是，64 位内核在 BIOS 没开 MMCONFIG 时，会主动把它设到 4G 以上（`arch/x86/kernel/mmconf-fam10h_64.c`，只在 64 位上编译）。32 位内核不会这样做，所以 32 位上能不能触发，取决于 BIOS 把基址放在哪里。

## 上游

- 这个函数 2012 年由 `24d25dbfa63c`（“x86/PCI: amd: factor out MMCONFIG discovery”）分出，之后的改动都和位宽无关：EXPORT 改 GPL、Hygon 支持、2025 年改用 `rdmsr_safe()`（CVE-2025-21913）、MSR 函数改名。
- lore.kernel.org 按函数名和“mmconfig fam10h 32-bit PAE”检索：没有关于截断的报告或补丁。最近动这个文件的 Lin Wang 系列（2026-10，v9）也只涉及厂商判断。

## 为什么做不了动态验证

QEMU 既没有 AMD 北桥 PCI 设备（`amd_bus.c` 的 `hb_probes` 找不到就提前返回），也不提供 `MSR_FAM10H_MMIO_CONF_BASE`（`rdmsrq_safe` 失败后函数返回 NULL）。要演示只能改内核伪造这两样，那只能证明 C 语言的截断规则，不能说明真机上会不会触发。

## 可能的修法（没写补丁）

参照 `e820__reserve_resources()` 的写法（`if (end != (resource_size_t)end) continue;`），在 `amd_get_mmconfig_range()` 里，算出的范围放不进 `resource_size_t` 时返回 NULL。这样两个使用者都按“没有 MMCONFIG”处理，和 32 位内核本来就用不到 4G 以上 MMIO 的事实一致。

## 文件

- `hist.sh`、`cfg.sh`、`use.sh`、`run.sh`：核对用的命令
- `i386_defconfig.config`：生成的 32 位默认配置（证据）
