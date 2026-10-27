# SPARC64真实编译对象：possible计数与IRQ栈循环的位宽界

2026-10-27。用户批准安装`gcc-sparc64-linux-gnu`，并以sparc64 defconfig真实编译父/修复版对象核对循环界。本轮把[上一轮宿主投影](../sparc_identity_chain_20261027/README.md)的cpumask位宽前提提升到**实际编译对象层**。没有链接vmlinux、启动内核或调用模型。

## 工具与构建

- apt安装：`gcc-sparc64-linux-gnu 4:13.2.1-2ubuntu1`（实际`sparc64-linux-gnu-gcc 13.3.0`）、`binutils-sparc64-linux-gnu 2.42`，收据`toolchain_install_receipt.txt`。这是WSL系统环境的持久变更。
- 父版`95706e71…`、修复`98937707…`分别`git archive`到`/root/.cache/linux-bug-analyze/sparc-identity-objects-20261027/{parent,fixed}/linux`，独立out-of-tree构建。
- 每版两种配置：`sparc64_defconfig`原样（实测`CONFIG_NR_CPUS=4096`、SMP=y、64BIT=y、DEBUG_PER_CPU_MAPS未开）；对照为同defconfig改`NR_CPUS=64`（Kconfig合法范围2..4096）后olddefconfig。
- 4个变体各编译`prom_64/setup_64/smp_64`的`.o`和`.i`，全部首次成功（9—16秒）。日志仅有sparc常见的`#warning syscall clone3 not implemented`。对象、配置、`.cmd`及SHA256SUMS在`attempt1/`。

## 对象层事实（`analysis/`保存逐函数反汇编）

`alloc_irqstack_bootmem`没有独立符号，已被内联进`setup_arch`；`record_one_cpu`因作为回调取址而保留独立符号。

| 变体 | IRQ栈循环（setup_arch内） | possible计数 |
| --- | --- | --- |
| 父版 4096 | `ld [nr_cpu_ids],%o1`→`_find_next_bit(__cpu_possible_mask,…)`，出口比较`nr_cpu_ids` | `smp_fill_in_cpu_possible_map`：`__bitmap_weight`，size取`nr_cpu_ids` |
| 父版 64 | 常数`0x40`单字扫描+`__ffs`，不读`nr_cpu_ids` | `__arch_hweight64`全字计数 |
| 修复 4096 | 同父版4096 | `record_one_cpu`：`ld [nr_cpu_ids],%o1`→`call __bitmap_weight`（延迟槽`%o0=__cpu_possible_mask`），再与`nr_cpu_ids`比较后`set_bit` |
| 修复 64 | 同父版64 | `record_one_cpu`：`ldx`读possible首字→`__arch_hweight64`，再与`nr_cpu_ids`比较 |

循环体对每个cpu调两次`memblock_alloc_try_nid`，以`cpu<<3`为偏移`stx`到`softirq_stack`/`hardirq_stack`。`.i`展开同样显示：默认配置循环为`find_next_bit(…, (nr_cpu_ids), i), i < (nr_cpu_ids)`，64对照为`((unsigned int)64)`。父版`smp_64.o`含`smp_fill_in_cpu_possible_map`且`record_one_cpu`不读`nr_cpu_ids`；修复版相反。

## 判定与控制

`check_objects.py`对4变体判O1（IRQ栈循环界）、O2（possible计数宽度）、O3（`.i`展开）、O4（版本差异），共16项，全部与配置一致：4096为`runtime_nr_cpu_ids`，64为`constant_64`。7项篡改控制全部拒判为不足：删除循环内`nr_cpu_ids`重定位、删除IRQ栈存储、计数helper换成hweight64、默认对象贴64标签、64对象冒充4096、父版冒充修复版、`.i`界换常数。

**首版判定器失败已保留：**attempt1用“IRQ栈基址重定位±20行内”定位循环，父版两变体O1判为不足。原因是编译器把父版循环轮转——先跳到底部测试再执行循环体，基址装载与find-bit调用相距约40行。对象没有变化；attempt2改为以“首个IRQ栈基址重定位到最后一次分配后15行”为循环区间，并要求区间内恰有一个界构造，修复版结果不变、父版转为与配置一致。原脚本和结果为`check_objects_attempt1.py`、`object_results_attempt1.json`；最终为`check_objects.py`、`object_results.json`。

## 对候选的意义

上一轮投影中的两条前提，现在已由真实sparc64编译对象确认：在默认`NR_CPUS=4096`配置下，修复版`record_one_cpu`的possible计数只数运行时`nr_cpu_ids`以内的位，`setup_arch`中的IRQ栈分配循环也以运行时`nr_cpu_ids`为界。`nr_cpus=L`在`setup_arch`开头就已生效，且早于这两处执行，所以L以外的稀疏cpuid不计数、也分不到IRQ栈，这一点在对象层面成立。小NR_CPUS配置编译出的是常数宽度，不受这一影响。

仍未证明：多CPU稀疏cpuid SPARC64真实启动时会进入possible、被拉上线并在第一次硬中断时用到NULL栈（QEMU sparc64只支持1 CPU）；这种配置在真实机器上是否常见；上游是否已有报告。候选仍**未确认、未外报**。对象层只证明编译后代码采用哪个位宽分支，不是运行观察。

## 统计

1次apt安装（工具链），2份源码归档，4个配置×3对象+3预处理单元，16项对象判定、7项控制；首版判定器1次规则过窄失败保留。0 vmlinux/启动/模型调用，新确认Linux缺陷0，独立正例/正常0/0。
