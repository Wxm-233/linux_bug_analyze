# kbuild：可复用的内核构建

2026-11-15，Claude。设计和验收见 `experiments/case_taxonomy/kbuild_reuse_20261115/`。在 WSL 里以 root 运行。

## 为什么要有它

以前每轮实验各写一个 `build.sh`：每次从零解压、从零编译，结束就删掉构建目录。一天构建将近 30 次，编译时间累计约两小时。

kbuild 做了四件事：

1. 构建目录长期保留，变异只做增量编译；
2. 每个镜像都登记在清单里，已有的就直接复用；
3. 配置固定成两档；
4. 打上变异后，先预检一下是否真的生效，再做完整构建。

## 用法

```bash
KB="python3 /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/kbuild/kbuild.py"

# 取镜像：登记表里有就直接返回路径，没有才构建
$KB get df2908090cda riscv plain
$KB get df2908090cda riscv kcov                      # kcov 档同时保留 vmlinux
$KB get df2908090cda x86_64 plain --mut r4.json:R4a  # 带变异（mutations/r4.json 里的 R4a）

# 登记已有镜像（只复制，不动原文件）
$KB import <提交号> <架构> <配置档> <变异或-> <镜像> --config <.config> [--vmlinux <vmlinux>] --note "来源"

# 列出全部镜像
$KB list
```

`get` 的标准输出只有一行镜像路径，日志写到标准错误，所以脚本里可以写 `IMG=$($KB get ...)`。

- 退出码：0 成功；2 变异没打上（锚点不唯一）；3 预检失败；4 构建失败。
- `--tag T`：同一组合另建一个镜像（例如验收时强制重建）。
- `--force`：忽略登记表，重新构建并覆盖原来的登记。

## 配置档（`profiles.json`）

| 档 | 内容 | 用途 |
|---|---|---|
| `plain` | defconfig + `TRANSPARENT_HUGEPAGE` | 判错 |
| `kcov` | `plain` + `KCOV`、`DEBUG_FS`、调试信息（`DEBUG_INFO_REDUCED`）+ 打开 `page_alloc.o` 插桩 | 只记覆盖（KCOV 内核会改变内核行为，不要用它判错） |
| `dyn` | `plain` + NUMA、THP 迁移、HMM 测试模块（`TEST_HMM`）、memcg、zram 交换，关 MGLRU（11-15 加，`p1dyn_20261115` 用） | 需要迁移、device-exclusive、回收的动态测试。riscv 的 defconfig 关了 `RUNTIME_TESTING_MENU`，要补开它，`TEST_HMM` 才能开上（已在 riscv 树里补好） |
| `dax` | `plain` + userfaultfd、`PTE_MARKER_UFFD_WP`、ZONE_DEVICE、`FS_DAX`、旧式持久内存（`LIBNVDIMM`、`BLK_DEV_PMEM`、`X86_PMEM_LEGACY`）（11-16 加，`s3dyn_20261116` 用，只建了 x86_64） | DAX＋userfaultfd 的动态测试。QEMU 启动参数加 `memmap=256M!512M` 得到 `/dev/pmem0` |
| `mglru` | `dyn` + MGLRU（`LRU_GEN`、`LRU_GEN_ENABLED`）（11-16 加，`s4dyn_20261116` 用，三架构） | 需要 MGLRU 回收路径的动态测试；运行时可写 `/sys/kernel/mm/lru_gen/enabled` 开关 |
| `dbgvm` | `dyn` + `DEBUG_KERNEL`、`DEBUG_VM`（11-16 加，`s5dyn_20261116` 用，三架构） | 需要 `VM_WARN_ON_*` 等调试断言生效的动态测试 |
| `pg64k` | arm64 defconfig + 64K 页 + THP + zram（11-16 加，`s6dyn_20261116` 用，只有 arm64） | 64K 页相关的动态测试。QEMU 要用 `-cpu cortex-a72`（`-cpu max` 进不了 `/init`），内存给 4G 才有空闲的 512MB 连续块 |
| `wide` | `mglru` + `ZSWAP`（11-25 加，`widebuild_20261125` 用，riscv、x86_64、powerpc） | 5 架构分层与边界 |
| `widearm` | `wide` + `ARM_LPAE`、`HIGHMEM`（arm，multi_v7） | 同上；arm 上 NUMA、内存热插拔、ZONE_DEVICE、HMM 开不上 |
| `widemte` | `wide` + `ARM64_MTE`、`KASAN`、`KASAN_HW_TAGS`（arm64） | 同上 |
| `wide2`、`widemte2`、`widearm2` | 对应原档 + `USERFAULTFD`、`PTE_MARKER_UFFD_WP`、`DAMON`（vaddr/paddr/sysfs）、`PAGE_TABLE_CHECK`（+`STRICT_DEVMEM`）、`DEBUG_VM`、`DEBUG_VM_PGTABLE`（11-25 加，`covgap_20261125` 用） | 5 架构边界的正式构建（之后的轮次都用它）；arm 上没有 uffd-wp、PAGE_TABLE_CHECK、DEBUG_VM_PGTABLE，powerpc 上没有 uffd-wp、PAGE_TABLE_CHECK |

11-25 起支持 `arm`（multi_v7_defconfig，出 zImage）和 `powerpc`（ppc64le_defconfig，只编 vmlinux，镜像登记为 vmlinux）。

## 变异（`mutations/*.json`）

格式如下：

```json
{"变异名": {"架构": {
   "edits": [{"file": "相对源码根的路径", "anchor": "必须恰好出现一次的原文",
              "insert_before": "插在锚点前的内容"  或  "new": "替换锚点的内容",
              "region_start": "可选：只在这个函数里找锚点"}],
   "precheck": {"obj": "mm/xxx.o", "regex": "正则", "absent": true/false,
                "region_start": "可选：只在预处理结果的这个函数里找"}}}}
```

预检会把 `obj` 对应的 `.c` 预处理成 `.i`，然后在里面找正则：
- `absent: false` 时，必须找到；
- `absent: true` 时，必须找不到。

例子：R4 检查的是 `move_ptes` 里不再出现 `pte = (pte);`，也就是默认的 `move_pte` 没有生效。

## 目录（WSL `/root/work/kbuild/`）

- `pristine/<提交号>/`：纯净源码，每个版本解压一次，只读。
- `trees/<提交号>_<架构>_<配置档>/`：
  - `src/`：硬链接副本；
  - `out/`：构建目录，长期保留；
  - 每次构建、预检的日志也放在这里。
- `images/`：镜像、`.config`、`vmlinux`。
- `registry.json`：登记表。

## 注意

- **改 `src/` 里的文件只能“先删再写”**，绝不能原地改写，否则会改到纯净源码和其他构建树（它们是硬链接）。kbuild 自己就是这样做的；手工改时也要遵守。
- **变异构建结束后会自动还原。** 还原时写的是新文件，修改时间更新，所以下次构建会重新编译受影响的目标，不会留下带变异的旧目标文件。
- **改头文件的变异**（如 `pgtable.h`）会重新编译约 2000 个文件，一次约 3 分钟；**只改 `.c` 的变异**通常在 1 分钟内。
- **同一棵构建树同时只能跑一个构建**（用 `flock` 保证）。不同构建树可以并行，但会抢 CPU。
