# 判据：线性映射地址检查（linmap_20261119）

2026-11-19，Claude。用户：“按漏报补规则”。依据 `h2miss_20261119` 的漏报分析，先做规则 A。写于任何实现和运行之前。

## 一、要找的问题

只对**线性映射地址**有意义的接口，被用在**不在线性映射里的地址**上。

- 线性映射：内核把物理内存整块映射到一段固定的虚拟地址，地址和物理地址之间只差一个常数。
- 内核镜像（代码、数据、链接符号）在 arm64 等架构上单独映射，不在线性映射里。
- vmalloc、vmap、ioremap、模块的地址在任何架构上都不在线性映射里。
- kmap 返回的地址，在有高端内存的 32 位架构上不在线性映射里。

x86_64 上 `__pa` 对内核镜像地址也能算对，所以这类写法在 x86 上测不出问题，到别的架构才出错。这属于类型一致性检查里的“地址类别”。

## 二、规则

1. **接收者**（只认线性映射地址），检查的是下面这个参数：
   - `virt_to_phys`、`__pa`、`virt_to_page`、`virt_to_pfn`、`virt_to_folio`、`virt_to_head_page` 的第 1 个参数；
   - `sg_init_one`、`sg_set_buf` 的第 2 个参数。
2. **来源**：接收者的参数（去掉括号、类型转换、`+ 偏移`、取下标后的取地址）属于下面任一种，就报出：
   - **镜像符号**：标识符在本文件或 `include/asm-generic/sections.h` 中声明为 `extern` 的字符数组（`extern char X[]` 一类）；
   - **映射来源的指针**：一个局部变量，在同一函数里被赋值为“映射来源调用”的结果，或者由这样的变量加偏移、做类型转换得到。映射来源调用包括：
     - vmalloc 一族：`vmalloc*`、`vzalloc*`、`__vmalloc*`、`vmalloc_user`、`vmalloc_32*`；
     - `vmap`、`vm_map_ram`；
     - kmap 一族：`kmap`、`kmap_atomic`、`kmap_local_page`、`kmap_local_folio`、`kmap_local_pfn`；
     - `ioremap*`、`memremap`；
     - **来源函数**（第 3 点）。
3. **来源函数**（返回值摘要）：
   - 一个函数如果有 `return` 语句直接返回映射来源调用的结果，或返回由它赋值的局部变量，它就是来源函数。反复迭代，直到不再新增。
   - 回调：形如 `…->成员(…)` 的调用，如果同一子系统（文件路径的前两级目录相同）里有 `.成员 = 函数` 的初始化，并且其中任一个函数是来源函数，这个调用就算映射来源调用。
4. **守卫**：同一函数里，接收者参数的变量（或它的来源变量）出现在 `virt_addr_valid`、`is_vmalloc_addr`、`is_vmalloc_or_module_addr`、`is_kmap_addr`、`PageHighMem` 的参数中，就不报。
5. **范围**：所有不在 `arch/` 下的 `.c` 文件（即公共代码，含 `drivers/`），去掉 `tools/`、`scripts/`、`samples/`、`Documentation/`、`usr/`。不编译，直接读该版本的 git 对象。
6. **受影响架构**（逐版本从源码机械推出）：
   - 镜像符号：`arch/<a>/include/asm/` 下自己 `#define __pa_symbol` 的架构；
   - vmalloc、vmap、ioremap：全部架构；
   - kmap：`arch/<a>/Kconfig*` 里定义了 `config HIGHMEM` 的架构。
7. 每条候选记录：文件、函数、行、接收者、参数文本、来源类别（镜像符号 / vmalloc / vmap / kmap / ioremap / 经来源函数，后者附调用链），以及受影响架构。签名不含行号：`LM|接收者|来源类别|参数文本`。

## 三、检验

1. **自测**：写小样例覆盖每种来源、守卫、回调和别名，全部通过才往下做。
2. **开发样本**（分析集的两个漏报）：
   - 2e2713ae1a05（btf）：修复前的版本在 `kernel/bpf/sysfs_btf.c` 的 `btf_sysfs_vmlinux_mmap` 报出 `virt_to_phys(__start_BTF)`，修复后不报；
   - 9c500835f279（zswap）：修复前的版本在 `mm/zswap.c` 的 `zswap_decompress` 报出 `sg_init_one` 的 `src`，修复后不报（修复加了 `virt_addr_valid(src)`）。
3. **当前版本**（df2908090cda）：报出全部候选。抽前 30 条（不足就全部），由我和 Codex（gpt-6.1-sol max）各自独立判断，算一致率，再由我裁定。参考线：“可能”至少占 20%。
4. **独立召回**：
   - 从内核历史里机械挖修复：改动不在 `arch/` 的 `.c` 文件，删掉的行含接收者，加上的行含 `__pa_symbol`、`lm_alias`、`vmalloc_to_page`、`vmalloc_to_pfn`、`is_vmalloc_addr`、`virt_addr_valid`、`kmap_to_page` 之一；
   - **按提交号去掉新评测集封存集和分析集里的修复**，去掉两个开发样本；
   - 由我和 Codex 各自独立判断是不是“线性映射接口用在了非线性映射地址上”；
   - 判为“是”的，在修复前的版本上运行，报到修复改动的函数才算召回。
   - 参考线：召回 ≥ 50%。
5. 做完以上几步，再决定是否接进整版扫描（新的分组版本），以及在封存集上只看汇总的复测。
