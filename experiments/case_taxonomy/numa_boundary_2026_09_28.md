# NUMA compat 位图边界复核（2026-09-28）

## 结论与证据等级

此前的“followup 版本 4/32 不一致”不能按四个内核问题统计。`bits=96` 的零尾和非零尾两组源于试验以 `bits` 分配，却向入口传 `maxnode=bits+1`；按实际参数和 32 位 `unsigned long` 取整，缓冲区应为 16 字节，修正后分别成功和 `EINVAL`。`bits=65, maxnode=66` 的两组即使按 32 位 ABI 分配 12 字节仍返回 `EFAULT`；提供 16 字节后分别成功和 `EINVAL`。[2026-09-21 原始对照数据](../../analysis_out/numa-boundary-review-20260921/results.json)保留，不重写旧矩阵。

本轮增加一个真正的静态 i386 进程探针，在当前 WSL 内核容量边界重现同构现象：调用 `set_mempolicy(MPOL_BIND, ..., maxnode=1026)` 时，132 字节缓冲区放在可读页末返回 `EFAULT`；补足至 136 字节且额外 4 字节为零可成功；只把该额外字设为 1 则返回 `EINVAL`。这说明额外字既可能引起触页失败，也能影响判断。它是**受测版本和配置上的接口范围分歧证据**，尚未被确认为应提交的内核缺陷，更不涉及可利用性结论。

## 接口权威、历史源码与计算

[Linux `set_mempolicy(2)` 手册的 DESCRIPTION](https://man7.org/linux/man-pages/man2/set_mempolicy.2.html)称用户位图按 `unsigned long` 的单位取整，内核只使用 `maxnode` 范围的位；ERRORS 将指定范围不可访问列为 `EFAULT`。这里以真正 i386 进程的 32 位 `unsigned long` 计算：`ceil(1026 / 32) * 4 = 132` 字节。手册对于“最多 `maxnode` 位”与代码中的 `--maxnode` 还存在表述差异，不能仅凭一句手册给所有历史版本下正式裁定；然而第 34 个 32 位字覆盖 bit 1056 起，不在两种解释任一者的 `maxnode=1026` 范围内。

本地 Linux Git 的 `e130242dc351`（2021-09-08）说明 compat 位图有不同字宽布局，并明确提到页末 64 位读取的问题；其 `mm/mempolicy.c:1365-1421` 新增共享 `get_bitmap/get_nodes`，`kernel/compat.c:193-220` 的 `compat_get_bitmap` 以 32 位字成对转换。`000eca5d044d`（2022-07-03）将 `get_nodes` 的尾部指针从 `nmask[maxnode / BITS_PER_LONG]` 改为 `nmask[(maxnode - 1) / BITS_PER_LONG]`，提交说明只将此项表述为越界索引修正。本地 Linux Git HEAD `df2908090cda`（Linux 7.3-rc2，2026-09-06）的 `mm/mempolicy.c:1637-1693` 仍保留该指针公式和 `get_bitmap(..., bits)` 调用，`kernel/compat.c:193-220` 仍按 32 位字转换。**本地 HEAD 不是正在运行的 WSL 内核源码**；以下实测用以独立确认该类行为，不把源码与运行版本当成逐字一致。

边界位宽可直接从函数链解释。`get_nodes` 先做 `--maxnode`，超过 `MAX_NUMNODES` 时每轮令 `bits=min(maxnode, 64)`，然后以 64 位本机 `unsigned long *` 计算偏移，再由 compat 路径的 `compat_get_bitmap(..., 64)` 连续读取两个 32 位字。对于受测 `MAX_NUMNODES=1024`、入口 `maxnode=1026`，起点是 `(1025-1)/64 * 8 = 128` 字节，读取到字节 135；按 32 位用户字宽取整的位图止于字节 131。64 节点的历史切片中同一计算是从偏移 8 读至 15，而入口 `maxnode=66` 的 32 位取整存储止于 11。由于 `get_nodes` 随后以 `if (t) return -EINVAL` 检查整枚读出的本机字，额外字还可改变结果。

## 本轮最小实测及正常对照

探针源码：[numa_padding_probe.c](numa_padding_probe.c)。它复用 [compat_start.S](../numa_entry/compat_start.S) 编成静态 i386 ELF；调用前先查询允许节点，输入位图设置该节点，随后在一个可读页末摆放缓冲区，下一页设为 `PROT_NONE`。每个用例结束后恢复本进程的默认策略。环境：`6.18.33.2-microsoft-standard-WSL2`，`CONFIG_NUMA=y`、`CONFIG_NODES_SHIFT=10`、`CONFIG_IA32_EMULATION=y`，允许的首个节点为 0。输出：[results.jsonl](../../analysis_out/numa-padding-20260928/results.jsonl)。

| `maxnode` | 可读字节 | 第 34 个 32 位字 | `set_mempolicy` 结果 | 区分作用 |
|---:|---:|---:|---:|---|
| 1026 | 132 | 不可访问 | `-EFAULT` (`-14`) | 32 位 ABI 取整长度下的页末输入 |
| 1026 | 136 | 0 | 0 | 只增加额外零字即可成功 |
| 1026 | 136 | 1 | `-EINVAL` (`-22`) | **同一声明范围**，仅范围外额外字改变判断 |
| 1057 | 136 | 1 | `-EINVAL` (`-22`) | 额外字在此对照中落入声明范围，作为正常拒绝对照 |

构建与复现（需同类内核配置；不在其他容量上直接套用预期）：

```bash
gcc -m32 -nostdlib -static -fno-builtin -fno-pie -no-pie \
  -fno-stack-protector -O2 -Wall -Wextra -Werror \
  experiments/case_taxonomy/numa_padding_probe.c \
  experiments/numa_entry/compat_start.S -o probe32
./probe32
```

程序以退出码 77–82 报告环境和运行前提不满足。本轮 4 行结果按 `[-14, 0, -22, -22]` 独立解析核对，探针退出码 0；`file` 确认为静态 32 位 i386 ELF。没有修改内核或长期系统配置，也没有重跑付费筛选。

## 仍未知及对自动检查的意义

- 2021/2022 历史切片是旧 `set_mempolicy` 转换入口加 2022 `get_nodes` 单项回放，并非启动完整历史内核；当前实测只覆盖 WSL 的 x86 compat/i386、单个允许节点，没有证明其他架构、真实多节点或各稳定分支的行为。
- 当前运行内核的确切构建源码未与本地 Git HEAD 逐字对应；手册与 `--maxnode` 的边界文字也需让 NUMA/ABI 维护者核对。应以接口文本、目标版本源码、真实调用者需要和配置共同裁定，暂不把“多读 4 字节”扩写成独立安全问题或通用修复方案。
- 自动检查可以把 **用户 ABI 字宽、实际传入的 `maxnode`、架构内核字宽、`MAX_NUMNODES` 和每次拷贝的起点/长度** 联立，计算读取上界是否超过调用者已声明的 ABI 存储上界；当超界时生成带源码行号和边界输入的复核候选。还必须有页末不可访问、额外零字和额外非零字三类对照，避免仅以测试 harness 的一个 `EFAULT` 推断内核问题。这个检查尚未实现为通用静态分析，也未验证新接口上的误报率。

## 文件指纹

| 文件 | SHA-256 |
|---|---|
| `experiments/case_taxonomy/numa_padding_probe.c` | `a242a502c646c3f11805f3d8f225bc0a4d2d1b942f7cf4663ac53ece425151b9` |
| `experiments/numa_entry/compat_start.S` | `d6337c5c77fd806473c6b2a3137a5417fbd1a5b6bd91f604a4ca5dd7e6d730bf` |
| `analysis_out/numa-padding-20260928/results.jsonl` | `c23fb1231d6541dfe34ca4535da4d0218da7db0ecb8556e9fee2dc21806c233c` |
| `analysis_out/numa-entry-20260915-v2/followup/harness.c` | `9c0f8a5698915b124a251f5e26c2df04f14626434d4f9f87087a450ff43f7cf4` |
| `analysis_out/numa-boundary-review-20260921/results.json` | `50bbf1386e48c4fcff5ec6b2ee4048eaf99747c4b7ab8170be2002c8e04a4df6` |
