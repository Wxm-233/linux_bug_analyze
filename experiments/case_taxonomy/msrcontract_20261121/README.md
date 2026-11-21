# 用 KVM 抽出的 MSR 约定表检查宿主机 MSR 访问（msrcontract_20261121）

2026-11-21，Claude。用户：“试外部约定表”。承接 `capcheck_20261121`（多数写法推断 0/19，诊断显示约定不在代码统计里）。属于实现一致性检查。

- 判据 `criteria.md`（18ae91fb…），写于实现和运行之前。没有修订。
- 统计行：模型调用 0；构建 0。

## 结论

**约定表质量不足，按判据第四节第 1 条结项。** 抽样 15 项里只有 10 项正确（门槛 ≥ 12）。没有做设计侧覆盖、晚期回放和当前版本扫描。

## 思路

KVM 替虚拟机模拟 MSR 时，会先检查虚拟机有没有对应的 CPUID 特性，没有就拒绝访问。所以 KVM 的代码里有大量“`case MSR_X:` → `guest_cpu_cap_has(vcpu, X86_FEATURE_Y)`”这样的写法，看起来正好是一张“访问 MSR_X 需要特性 Y”的约定表，而且和宿主机里访问 MSR 的代码相互独立。

## 抽出的表（`msrcheck.py table`，`table_aebb72744764.json`）

从 v7.4-rc3 的 `arch/x86/kvm/` 抽出 **47 项**。规则：
- 取每个 `case MSR_X:` 分支里的特性判断；
- 分支里调用的辅助函数（如 `guest_has_spec_ctrl_msr()`）展开一层；
- 同一 MSR 出现在多个分支时取并集。

其中 8 项对应的特性超过 3 个。

## 质量核对（`table_sample.json` → `table_judgement.json`，SHA 32f62ea2…）

按种子抽 15 项逐项判断：

| 判断 | 项数 | 例子 |
|---|---|---|
| 正确 | 10 | SPEC_CTRL ← SPEC_CTRL/AMD_IBRS/AMD_SSBD…；XSS ← XSAVES；S_CET ← IBT/SHSTK；TSC_AUX ← RDTSCP/RDPID；DS_AREA ← DS |
| **KVM 自己的模拟条件，不是硬件要求** | 3 | TSX_CTRL ← RTM（应看 ARCH_CAPABILITIES 的 TSX_CTRL 位）；MISC_ENABLE ← SSE3（KVM 处理 MWAIT 位用的）；AMD64_DE_CFG ← LFENCE_RDTSC |
| **共享分支被整体并集，约束失效** | 2 | F15H_IC_CFG 并进了 5 个无关特性；PERF_CAPABILITIES 并进了 15 个，“之一即可”等于没有约束 |

## 看出的几点

1. **KVM 的检查回答的是另一个问题**：KVM 关心的是“虚拟机该不该看到这个 MSR”，其中掺着它自己的模拟策略（比如只在虚拟机有 RTM 时才模拟 TSX_CTRL），并不是硬件上“访问这个 MSR 需要什么”。拿它当宿主机的约定，大约三分之一是错的。
2. **词法抽取的分支边界不可靠**：KVM 里常有一大串 `case` 共享同一段代码（比如“这些 MSR 都要检查 PDCM”），按“同一分支里出现的特性都算”就会把无关特性并进来。要修就得做语义级的数据流，代价和风险都超出这一步。
3. **就算表是对的，覆盖面也很窄**：设计侧 19 个根因里和 MSR 有关的只有 M5、M14、M15、M18 四个，其中 M14 的 MSR（0x620）KVM 不模拟，M18 的问题在 MSR 的某一位上。这张表对“能力前置条件”这一族的帮助本来就有限。

## 三次尝试的共同结论

| 轮次 | 做法 | 结果 | 卡在哪 |
|---|---|---|---|
| `abisupply` | 兼容 ABI 宽度（约定可从代码读出） | 样本不足（晚期 1 个根因） | 缺陷太少 |
| `capcheck` | 能力前置条件，从全树多数写法推断约定 | 开发 0/19 | 约定不在代码统计里 |
| `msrcontract` | 能力前置条件，从 KVM 抽约定表 | 表质量 10/15 | 现成的机器可读约定不可靠 |

“约定从哪来”仍然是核心障碍。剩下的路要么是**人工整理约定表**（照手册写 MSR、指令和特性的对应关系；工作量大，而且我看过设计样本，写表时难免带偏，需要由别人或在不看样本的前提下写），要么**重新规划方向**。

## 文件

- `criteria.md`、`criteria_sha256.txt`
- `msrcheck.py`（约定表抽取、抽样、检查；检查部分没运行）、`py.sh`
- `table_aebb72744764.json`（抽出的表）、`table_sample.json`、`table_judgement.json`、`table_judgement_sha256.txt`
