# Linux Bug Analyze

用静态分析加动态验证，检测 Linux 内核里的**跨架构缺陷**。

**跨架构缺陷**指的是：公共代码（`mm/`、`fs/`、`kernel/` 等）依赖了架构接口的某种性质，这个性质在一些架构上成立，在另一些架构上不成立，于是同一段公共代码只在部分架构上出错。例如：
- 对非 present 的页表项调用 `pmd_dirty()`，各架构的编码不同，结果也不同；
- arm64 64K 页上 `HPAGE_PMD_ORDER` 等于 13，超过了页缓存上限 11；
- `unsigned long` 在 32 位架构上只有 32 位。

检查分为三类：**类型一致性检查**、**实现一致性检查**、**调用上下文检查**。检测过程不使用大模型。目前的结果和确认的缺陷见 [experiments/README.md](experiments/README.md) 和 [experiments/confirmed_bugs.md](experiments/confirmed_bugs.md)。

## 工作流程

```
挖样本 → 静态检查 → 可达性过滤 → 两人审查 → 动态验证 → 核对上游、报告
                │
                └→ 提交级模式：比较一个提交前后两个版本的候选，只报新引入的
```

1. **挖样本**：从历史修复里筛出“公共代码依赖架构接口效果”的修复，经两人标注，作为样本和分类。
2. **静态检查**：每类依赖写一条检查线，在历史样本上量召回，在当前内核上产出候选。
3. **可达性过滤**：去掉走不到的候选，要求召回不降。
4. **两人审查**：Claude 和 Codex 分别盲判候选，算一致率，再统一裁定。
5. **动态验证**：对疑点构建“修复变异”和“对照变异”两种内核，在 QEMU 里复现，按性质判断对错。
6. **核对上游、报告**：确认主线和 mm 树都没修、邮件列表上也没人报过，再由作者本人发补丁或缺陷报告。

每轮实验先写判据（`criteria.md`）并记录 SHA，然后才统计。判据要改，只能另写修订文件。

## 环境

所有分析都在 WSL（Ubuntu）里以 root 运行，需要：
- 内核源码 git 仓库，放在 `/root/repos/linux`（只读使用）；
- Python 3.10 或更高版本、LLVM 18；
- 动态验证还需要 QEMU 和各架构的交叉编译工具。

每个脚本运行前都要先加载环境：

```bash
source tools/wsl_env.sh
```

它会清理 PATH，并设置 `REPO`、`KSRC` 等目录变量。

## 怎么使用

每条检查线是 `experiments/case_taxonomy/` 下的一个目录，用法相同：

```bash
cd experiments/case_taxonomy/<检查线目录>
python3 <脚本>.py selftest   # 自测
python3 <脚本>.py head       # 检查当前内核，输出 head.json
python3 <脚本>.py recall     # 在历史样本上量召回，输出 recall.json
```

各检查线的正式版：

| 检查线 | 目录 / 脚本 | 查什么 |
|---|---|---|
| 受限接口（P1）＋可达性过滤 | `reachgap_20261116/reachgap.py` | 受限接口调用前有没有 present 守卫 |
| 横纵两面 | `xvdom_20261116/xvdom.py` | 8 个架构的真实编码，以及公共代码有没有守卫 |
| 接口提升 | `xvlift_20261116/xvlift.py` | 参数没守卫的辅助函数，逐层查它的调用者 |
| 阶数族 | `orddom_20261116/orddom.py` | 页大小派生的阶数有没有先夹到页缓存上限 |
| 位宽截断 | `widthtrunc3_20261117/widthtrunc3.py` | 32 位架构上的窄化、移位溢出、掩码截断 |
| TLB/缓存钩子 | `tlbhook_20261117/tlbhook.py` | 建映射或改页之后，有没有调用刷新钩子 |

**提交级模式**：检查一个提交有没有引入新的跨架构问题。

```bash
cd experiments/case_taxonomy/commitmode_20261117
python3 commitmode.py check <commit>   # 结果写到 report/<commit>.json，并在终端打印新引入的候选
```

**内核构建**：动态验证要用的内核镜像，统一用 kbuild 获取。已经构建过的组合直接复用，不会重复构建。

```bash
python3 tools/kbuild/kbuild.py get <rev> <arch> <profile> [--mut 变异文件:名字]   # 输出镜像路径
python3 tools/kbuild/kbuild.py list                                             # 列出已登记的镜像
```

## 其他说明

- 本项目由 Claude Code 和 GPT（Codex）轮流推进，各自的工作说明分别在 `CLAUDE.md` 和 `AGENTS.md`。
- 超过 2MB 的中间产物不入库，已写在 `.gitignore` 里，需要时用各轮的脚本重新生成。
- `linux_bug_analyze/` 包里是旧方向的大模型初筛工具，说明见提交 `4c87905` 的 README。
