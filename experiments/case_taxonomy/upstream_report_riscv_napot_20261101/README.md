# 上游报告草稿：RISC-V NAPOT大页不在内存的表项只清一部分（未发送）

用户于2026-11-01要求查重并起草报告。本目录只保存**草稿**。发送须由用户本人用自己的邮件账户完成：纯文本、不带附件，可用`git send-email`或邮件客户端。发送前请核对正文并填写署名`<name>`。

缺陷本身的验证见`../riscv_napot_clear_verify_20261101/README.md`。

## 文件

| 文件 | 说明 | SHA |
| --- | --- | --- |
| `riscv_napot_nonpresent_clear.txt` | 英文报告邮件草稿（含收件人、分析、复现程序、建议改法） | `f249b060…` |
| `reproducer.c` | 精简后的复现程序，与邮件中嵌入的代码逐字一致（只差文件头注释） | `32bab792…` |
| `check_reproducer.sh` | 在原版与对照内核上运行复现程序 | `6f7f5d30…` |
| `logs/base.log`、`logs/patched.log` | 复现程序的运行输出 | `87e9e21c…`、`70f6295d…` |

**复现程序已在两个内核上实测**：
- 原版内核：第1页正常，第2到16页SIGBUS，`FAIL: 15 of 16`，退出码1；
- 对照内核：16页都正常，`PASS`，退出码0。

邮件中的建议改法与验证轮的`control.patch`逐字一致（已用程序核对）。

## 查重结果

| 查了什么 | 结果 |
| --- | --- |
| 主线（GitHub镜像，master `cbbddb6b08cc`，2026-10-31） | `arch/riscv/mm/hugetlbpage.c`在终点版本之后**没有新提交**，问题仍在 |
| RISC-V邮件列表patchwork，2025-03以来，搜`napot`、`huge_pte_clear`、`hugetlb` | **没有修这个问题的补丁**。改动这个文件的进行中补丁有3组，见下表 |
| mm邮件列表patchwork，搜`napot`、`pte_napot`、`riscv hugetlb` | 只有同样的几组补丁，没有新的 |
| lore.kernel.org | 自动访问和命令行访问都返回403，**没能检索**。没有尝试绕过 |
| 网页搜索 | 工具本次报错，不可用 |

改动这个文件的进行中补丁：

| 补丁系列 | 作者 | 状态 | 与本问题的关系 |
| --- | --- | --- | --- |
| Merge arm64/riscv hugetlbfs contpte support v5（2025-03） | Alexandre Ghiti | 一年多未合入 | 改用公共函数、按大小处理，**会顺带修掉**这个问题 |
| riscv: add Svnapot-based contiguous PTE support v1（2026-04） | yunhui cui | 新提交 | 4/7只改了函数名，**保留门槛** |
| riscv: add Svnapot PTE folding support v2（2026-07） | yunhui cui | 新提交 | 02/15**保留门槛**，而且把个数改回从表项内容推，**不会修掉**；所以邮件也抄送了作者 |

## 发送前须用户处理

- **再查一次lore**：请在<https://lore.kernel.org/all/>搜`pte_napot huge_pte_clear`、`napot non-present`、`riscv hugetlb huge_ptep_get_and_clear`，确认没有人报告过。本轮没能检索lore。
- **收件人**：由`scripts/get_maintainer.pl`得出（`arch/riscv/mm/hugetlbpage.c`与`mm/hugetlb.c`）。另加arm64修复的作者Ryan Roberts，以及进行中补丁的作者yunhui cui。Alexandre Ghiti在MAINTAINERS中的地址是`alex@ghiti.fr`，与他旧提交中的rivosinc地址不同，邮件用的是前者。
- **邮件性质**：写成缺陷报告，附建议改法。不是带`Signed-off-by`的正式补丁：签署补丁需要用户本人同意开发者原创声明（DCO）。若维护者希望直接提交补丁，可由用户再决定。
- **署名**：`<name>`待填；草稿中不含用户邮箱，未代发。
- **文字来源**：草稿是Claude起草的，不是用户原话；发出即公开，并会被归档。
- **措辞已注明的边界**：只测了中毒标记，迁移项没有构造；没有在真实硬件上运行；建议改法只经过本复现与验证轮的场景检查。

本目录不是研究实验，不增加确认缺陷数；若上游确认或修复，再按回复更新进展文档。
