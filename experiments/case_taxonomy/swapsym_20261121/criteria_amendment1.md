# 判据修订 1：扩到更多架构（swapsym_20261121）

2026-11-21，Claude。用户：“扩到更多架构”。写于生成变体和运行之前。原判据第二～五节（合成函数、输入域、义务、对账与门槛）不变，只扩大构建范围、补充编译参数的取法。

## 一、新增构建（全部是只生成头文件的配置变体，加一个 mm/memory.o 单文件编译）

| 名称 | ARCH | 配置 | 预期的交换项实现 |
|---|---|---|---|
| ppc64le | powerpc | powernv_defconfig | book3s/64 |
| ppc64e | powerpc | corenet64_smp_defconfig | nohash/64 |
| ppc32s | powerpc | pmac32_defconfig | book3s/32 |
| ppc44x | powerpc | ppc44x_defconfig | nohash/32（44x 用 64 位页表项） |
| ppc8xx | powerpc | mpc885_ads_defconfig | nohash/32（32 位页表项） |
| s390 | s390 | defconfig | s390 |
| loongarch | loongarch | defconfig | loongarch |
| mips32 | mips | malta_defconfig | pgtable-32 |
| mips32xpa | mips | maltaup_xpa_defconfig | pgtable-32，XPA（64 位物理地址） |
| mips64 | mips | 64r6el_defconfig | pgtable-64 |
| arm | arm | multi_v7_defconfig | 两级页表 |
| arm_lpae | arm | multi_v7_defconfig + ARM_LPAE | 三级页表（LPAE） |
| hexagon | hexagon | defconfig | hexagon |
| um | um | defconfig（SUBARCH=x86_64） | um |
| sparc64 | sparc | sparc64_defconfig | sparc64 |

- 每个变体：`make O=/root/work/swapsym/cfg_<名称> ARCH=… LLVM=1 <配置>`，需要时 `scripts/config` 改选项、`olddefconfig`，然后 `make prepare` 和 `make mm/memory.o`。编译参数取自 `mm/.memory.o.cmd` 的 `savedcmd`（截到第一个 `;` 为止）。
- 任何一步失败（clang 不支持该架构、配置不可用、头文件报错）就记“构建不可用”及原因，不换配置去凑。允许的唯一补救：配置名在该版本不存在时，换成同一实现的另一个现成配置，并在 README 里写明。
- 变体只在 WSL `/root/work/swapsym/` 下，做完记录体积，结论写完后删除目标文件，只留 `.config`、日志和生成的头文件。

## 二、判定

- 与原判据相同：O1、O2、O3、探测值对账，每个构建 6 组具体输入 + 3 个常量与 clang 对账，一处不一致就不给该构建下结论。
- 32 位 / 64 位按 `.config` 的 `CONFIG_64BIT` 定 `long` 的宽度。
- 任一构建出现“违反”时，必须给出域内的具体 (t, o)，并由 clang 对同一输入折叠出的结果复现；再读该架构源码说明原因，判断是否已知、是否有公共使用者受影响。“未知”和“不支持”逐条写原因，不当作成立。
- 另记每个构建上 `debug_vm_pgtable.c:1229` 取到的值是否等于“探测值 - 1”（原生测试是否退化）。

## 三、其他

- 不运行内核；不改旧目录；不调用模型。
- 统计行：模型调用 0；构建：头文件变体最多 15 个（每个只编译 mm/memory.o 一个文件）。
