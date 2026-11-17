# 判据：动态验证新疑点 3（s3dyn_20261116）

2026-11-16，Claude。用户：“动态验证疑点 3”。本文件在构建内核、写测试程序、跑任何测试之前写定，SHA 存入 `criteria_sha256.txt`；预测另存 `predictions.json`（同时写定）。

## 一、疑点和静态依据

`mm/memory.c` 的 `insert_page_into_pte_locked()`（当前版本 `df2908090cda`）：

```c
pte_t pteval = ptep_get(pte);
if (!pte_none(pteval)) {
        if (!mkwrite)
                return -EBUSY;
        if (pte_pfn(pteval) != page_to_pfn(page)) {          /* 2494 */
                WARN_ON_ONCE(!is_zero_pfn(pte_pfn(pteval)));  /* 2495 */
                return -EFAULT;
        }
        ...
```

代码默认“非空就是已经映射的页”。我核实过的路径：
1. `vma_can_userfault()`：只开 WP 模式且是 `WP_ASYNC` 时允许任何内存类型；ext4 DAX 的 VMA 只带 `VM_HUGEPAGE`，不是 `VM_SPECIAL`；
2. `UFFDIO_WRITEPROTECT` 对未填充的位置：`change_pte_range()` 在 `pte_none` 时，若 `userfaultfd_wp_use_markers(vma)`（文件映射恒为真），装 uffd-wp 标记；
3. 访问这一页：`do_swap_page` → `handle_pte_marker` → `pte_marker_handle_uffd_wp` → `do_pte_missing` → ext4 DAX 缺页 → `dax_fault_iter()` / `dax_load_hole()` → `vmf_insert_page_mkwrite(vmf, page, write)` → `insert_page_into_pte_locked()`；
4. 这时页表项是标记（非 present、非空）：
   - 写（`mkwrite=true`）：对标记调 `pte_pfn`，和 DAX 页框号不等 → `WARN_ON_ONCE`、返回 `-EFAULT` → `VM_FAULT_SIGBUS`；
   - 读（`mkwrite=false`）：返回 `-EBUSY` → `VM_FAULT_NOPAGE` → 回到用户态重试，再次缺页，**推测会无限重试**（同一根因，但不是静态报告标出的那两行）。

这条在所有架构上都会出错，不是典型的跨架构缺陷。本轮只测 x86_64。

## 二、内核（kbuild，写死）

- 新增配置档 `dax`：`plain` 加 `USERFAULTFD`、`PTE_MARKER_UFFD_WP`、`MEMORY_HOTPLUG`、`MEMORY_HOTREMOVE`、`ZONE_DEVICE`、`FS_DAX`、`DAX`、`LIBNVDIMM`、`BLK_DEV_PMEM`、`X86_PMEM_LEGACY`、`EXT4_FS`、`DEVTMPFS`。不动已有的 `dyn` 档。构建后检查这些选项全部为 y，否则停下来写修订。
- 两个内核，都是 `df2908090cda` x86_64：
  - **plain**：不改代码；
  - **F3（修复变异，用于归因）**：`insert_page_into_pte_locked()` 里 `if (!pte_none(pteval)) {` 改成 `if (!pte_none(pteval) && pte_present(pteval)) {`，即把非 present 项当成空项处理。变异定义在 `tools/kbuild/mutations/s3dyn.json`，预检：`mm/memory.o` 预处理结果的该函数里出现 `pte_present(pteval)`。这个改法只用于归因，不声称是正确的上游修法（它会丢掉标记的写保护状态）。

## 三、环境（写死）

- QEMU x86_64，`-M q35 -cpu max -accel tcg -smp 2 -m 1024M`，启动参数加 `memmap=256M!512M`，把 512M～768M 当作旧式持久内存（e820 类型 12），出现 `/dev/pmem0`；
- 在宿主机上用 `mkfs.ext4 -b 4096` 做一个 32M 的 ext4 镜像，放进 initramfs；`/init` 是静态编译的测试程序，开机后挂 devtmpfs、proc，把镜像写进 `/dev/pmem0`，再以 `-o dax=always` 挂到 `/mnt`；
- 每个内核跑 3 次。

## 四、测试（写死，每个用例在独立子进程里做，父进程等 20 秒，超时就杀掉并记 HANG）

文件都是 16 页、`MAP_SHARED` 可读写映射。“已分配”的页事先用 `pwrite` 写过并 `fsync`；“空洞”的页由 `ftruncate` 扩出来，从未写过。uffd 用例：`userfaultfd()` → `UFFDIO_API`（`UFFD_FEATURE_WP_ASYNC`）→ `UFFDIO_REGISTER`（`MODE_WP`）→ `UFFDIO_WRITEPROTECT`（整个映射），然后从 `/proc/self/pagemap` 读目标页的第 57 位（uffd-wp），记下来作为“标记已装上”的证据，再访问。

| 编号 | 内容 |
|---|---|
| C0 | 环境：`/dev/pmem0` 存在、挂载成功、测试文件 `statx` 带 `STATX_ATTR_DAX` |
| C1 | DAX 文件、不注册 uffd：写已分配页、写空洞页、读已分配页、读空洞页 |
| C2 | memfd（shmem）文件、注册 uffd 异步写保护：写一页、读一页 |
| T1 | DAX＋uffd 写保护，**写**已分配页 |
| T2 | DAX＋uffd 写保护，**写**空洞页 |
| T3 | DAX＋uffd 写保护，**读**已分配页 |
| T4 | DAX＋uffd 写保护，**读**空洞页 |

每个用例的结果：`OK`（访问完成；写的再用 `pread` 核对内容）、`SIGBUS`、`SIGSEGV`、`HANG`、`ERR`（准备步骤失败，写明哪一步）。另外从串口日志里找 `WARNING` 且调用栈含 `insert_page_into_pte_locked` 的行。

## 五、判定（写死）

- **有效运行**：日志里有 `@@END`，C0 通过，C1、C2 全部 OK。
- **前提**：T1～T4 的 pagemap 第 57 位为 1。为 0 时该用例记“前提不成立”，不参与判定。
- **疑点 3 复现**（主判定，对应静态报告的 2494～2495 行）：plain 内核上 T1 或 T2 在至少 2/3 次有效运行里是 SIGBUS，**并且** F3 内核上同一用例在至少 2/3 次有效运行里是 OK。
- **不复现**：plain 上 T1、T2 在有效运行里都是 OK。
- 其余情况记“说不清”，写明原因。
- **读路径**（附带判定）：plain 上 T3/T4 是 HANG、F3 上是 OK，记为“同一根因的第二种后果”；不影响主判定。
- 如果环境或前提不成立（DAX 挂不上、uffd 注册失败、标记没装上），记“无法验证”，写修订说明后才能改环境。

## 六、参考线（不是通过条件）

- 两个内核 × 3 次全部有效；
- 主判定：复现；
- plain 上出现 `insert_page_into_pte_locked` 的 WARN。

## 七、空间

新构建树预计 1～2G。保留：两个镜像和 `.config`（登记在 kbuild 里）、构建树 `out/`（以后同一档的变异只做增量编译）。删掉：initramfs 临时目录。轮末报告 WSL 剩余空间。

## 八、规则

不安装、不联网、不调用大模型；只读 `/root/repos/linux`；不对外报告（结果只在本地记录）；只结束自己启动的 QEMU。统计行：模型调用 0；Codex 调用 0；构建 N；新确认缺陷按用户决定；新疑点按实际写。
