# 动态验证新疑点 3（s3dyn_20261116）

2026-11-16，Claude。用户：“动态验证疑点 3”。判据见 `criteria.md`，预测见 `predictions.json`（两者的 SHA 在 `criteria_sha256.txt`，都在构建和运行之前写定，本轮没有修订）。

统计行：模型调用 0；Codex 调用 0；构建 2；新确认缺陷 **1**（用户 11-16 确认，登记为 `experiments/confirmed_bugs.md` 的 B-2026-11-16-1）；新疑点 0。

## 一句话结论

**疑点 3 复现，归因成立，预测全部命中。** 在当前版本（`df2908090cda`，7.3.0-rc2）的 x86_64 上，对 ext4 DAX 文件的共享映射注册 userfaultfd 异步写保护后：

- **写**还没映射进来的页，进程收到 **SIGBUS**，内核报 `WARNING: mm/memory.c:2495 at insert_page_into_pte_locked`（3/3）；
- **读**这样的页，进程卡在缺页里**无限重试**：20 秒内约 350 万次缺页，没有进展（3/3）。

只改一处的修复变异 F3（把非 present 项当成空项处理），上面四种情况全部恢复正常（3/3）。对照组（不注册 uffd 的 DAX 文件、注册了 uffd 的 shmem 文件）在两个内核上全部正常。

## 缺陷是什么（说人话）

userfaultfd 的写保护可以作用在还没映射的位置上。做法是在页表里放一个“uffd-wp 标记”：它不是真正的页表项，只记“这里被写保护过”，属于非 present 项。

进程访问这一页时，内核走正常的缺页流程，最后由 DAX 把持久内存里的页插进页表，函数是 `insert_page_into_pte_locked()`。这个函数默认“页表项不为空，就是已经映射了某个页”：

```c
if (!pte_none(pteval)) {
        if (!mkwrite)
                return -EBUSY;                         /* 读：当成“别人已经映射好了”，让进程重试 */
        if (pte_pfn(pteval) != page_to_pfn(page)) {    /* 写：对标记读页框号，读出无意义的值 */
                WARN_ON_ONCE(!is_zero_pfn(pte_pfn(pteval)));
                return -EFAULT;                        /* → SIGBUS */
        }
```

- 写的时候，`pte_pfn` 从标记里读出的不是页框号，和 DAX 页对不上，于是报 WARN、返回错误，进程收到 SIGBUS；
- 读的时候，函数以为别人已经映射好了，返回 `-EBUSY`，缺页处理据此告诉进程“重试”。但标记没有被替换，进程每次重试都再次缺页，永远没有进展。

页表项不 present 时调用只对 present 项有定义的接口 `pte_pfn`，这正是 P1 那一类问题。不过它在所有架构上都会出错，属于公共层漏查 present 的一般性缺陷，不是典型的跨架构缺陷。

## 怎么测的

- **内核**：kbuild 新增 `dax` 配置档：`plain` 加上 userfaultfd、uffd-wp 标记、ZONE_DEVICE、FS_DAX、旧式持久内存驱动。只构建 x86_64，plain 和 F3 两个镜像共用 4 分 50 秒，F3 是增量编译，19 秒。构建后核对，13 个选项全部是 y。
- **环境**：QEMU x86_64 TCG，启动参数 `memmap=256M!512M`，把一段内存当作持久内存，出现 `/dev/pmem0`。宿主机上做好 32M 的 ext4 镜像，测试程序 `/init`（`s3.c`）把它写进 `/dev/pmem0`，再以 `-o dax=always` 挂载，并用 `statx` 确认测试文件确实是 DAX。
- **用例**：每个用例在独立子进程里做，20 秒没结束就算卡住。访问之前先读 `/proc/self/pagemap`，确认目标页的 uffd-wp 位是 1（标记已经装上），而且这一页不 present。

## 结果（`judge_main.txt`，每个内核 3 次，全部有效）

| 用例 | 内容 | plain | F3 | 预测 |
|---|---|---|---|---|
| C1 | DAX，不注册 uffd，读写已分配页和空洞页 | OK ×3 | OK ×3 | OK |
| C2 | shmem，注册 uffd 异步写保护，读写 | OK ×3 | OK ×3 | OK |
| **T1** | DAX＋uffd 写保护，**写**已分配页 | **SIGBUS ×3** | OK ×3 | 命中 |
| **T2** | DAX＋uffd 写保护，**写**空洞页 | **SIGBUS ×3** | OK ×3 | 命中 |
| **T3** | DAX＋uffd 写保护，**读**已分配页 | **卡住 ×3**（20 秒内 343 万～372 万次缺页） | OK ×3 | 命中 |
| **T4** | DAX＋uffd 写保护，**读**空洞页 | **卡住 ×3**（362 万～384 万次缺页） | OK ×3 | 命中 |
| WARN | `mm/memory.c:2495 insert_page_into_pte_locked` | 3/3 | 0/3 | 命中 |

T1～T4 访问前，pagemap 的 uffd-wp 位都是 1，present 位都是 0（3/3），说明前提成立。

WARN 的调用栈和静态推出的路径一致：

```
insert_page ← vmf_insert_page_mkwrite ← dax_fault_iter ← dax_iomap_fault
  ← ext4_dax_huge_fault ← do_pte_missing ← handle_mm_fault ← do_user_addr_fault
```

冒烟运行（`judge_smoke.txt`，各 1 次）结果相同。

## 判定

- **主判定（对应静态报告的 2494～2495 行）**：复现。plain 上 T1、T2 都是 3/3 SIGBUS，F3 上都是 3/3 OK。
- **附带判定（读路径）**：同一根因的第二种后果成立。plain 上 T3、T4 都是 3/3 卡住，F3 上都是 3/3 OK。
- 参考线全部达到：两个内核 × 3 次全部有效、主判定复现、plain 上出现 WARN。

## 影响和说明

- **谁会碰到**：在 DAX 文件（持久内存上的 ext4/xfs）的共享映射上用 uffd 异步写保护做脏页跟踪的程序。例如用 `PAGEMAP_SCAN` 或 `UFFDIO_WRITEPROTECT` 做增量检查点、热迁移的工具。写一个还没访问过的页，进程会被 SIGBUS 杀掉；读这样的页，进程会卡死，但还能被杀掉。
- **它是怎么被找到的**：P1 和契约挖掘给出受限接口的调用点 → 可达性过滤（reach、reachf4、reachf1）→ 编码表排序（第 25～28 名）→ 我和 Codex 两人盲判，裁定为“可能”。最初我判的是“不可能”，因为漏了 uffd 标记这种非 present 项；Codex 给出了这条路径。所以这是静态候选第二次经动态测试确认，第一次是 p1dyn。
- **F3 不是正确的修法**：它把标记直接覆盖掉，写保护状态就丢了。上游正确的修法大概应该在插页时识别 uffd-wp 标记，并保留写保护语义。
- **上游是否已修不知道**：没联网。只在本地记录，不对外报告。
- **同形态的另一处没测**：`mm/memory.c:2824-2825` 的 `insert_pfn()`，可达候选第 28、29 名，写法相同。它走的是按页框号插入的路径，比如 `vmf_insert_pfn_mkwrite`，本轮没有覆盖。

## 空间

- 新构建树 `/root/work/kbuild/trees/df2908090cda_x86_64_dax` 占 2.9G，比判据估计的 1～2G 大，按判据保留，以后在这一档上做变异只需增量编译；
- 两个镜像各 15M，已登记在 kbuild；
- initramfs 临时目录 `/root/work/s3dyn` 已删；WSL 剩余 97G。

## 文件

- `criteria.md`、`predictions.json`、`criteria_sha256.txt`；
- `build.sh`、`build.log`、`kernels/`（构建日志）；kbuild 改动：`tools/kbuild/profiles.json` 新增 `dax` 档，`tools/kbuild/mutations/s3dyn.json`（F3）；
- `s3.c`（测试程序）、`run.sh`、`run_main.log`、`runs/{smoke,main}/`（串口日志）；
- `judge.py`、`judge_{smoke,main}.{json,txt}`、`stats.json`。

## 下一步建议

1. ~~由用户决定是否记为已确认缺陷~~：用户 11-16 确认，已登记为 B-2026-11-16-1（只在本地记录）；
2. 用同样的环境测 `insert_pfn()` 那一处（找一条走 `vmf_insert_pfn_mkwrite` 的路径），以及 PMD 级的 `vmf_insert_folio_pmd` 遇到 PMD 级标记的情况；
3. 回到静态分析：给分析器加返回值摘要，P1 受限接口清单由编码表生成。
