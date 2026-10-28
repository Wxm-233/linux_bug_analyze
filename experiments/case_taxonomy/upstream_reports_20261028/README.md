# 上游报告草稿（2026-10-28，未发送）

用户于2026-10-28批准就SPARC与ACPI两项观察向上游报告。本目录只保存**草稿**；发送须由用户本人用自己的邮件账户完成（纯文本、不带附件，可用`git send-email`或邮件客户端），发送前请核对正文并填写署名。

| 草稿 | 收件人来源 | 证据 | 定性 |
| --- | --- | --- | --- |
| `sparc64_nr_cpus_irqstack.txt` | 主线v7.3-rc2 `scripts/get_maintainer.pl arch/sparc/kernel/prom_64.c` | `sparc_identity_chain_20261027`（源码投影）、`sparc_identity_objects_20261027`（真实sparc64对象） | 未在运行时验证（QEMU sparc64仅1 CPU、无多CPU硬件），写成提问 |
| `x86_acpi_legacy_hotplug_tcg.txt` | 同上，`arch/x86/kernel/acpi/boot.c` | `acpi_env_classification_20261027`（4环境实测＋QMP热插） | 可能是有意的支持范围，写成提问；建议方向未测试 |

## 发送前须用户处理

- **查重**：lore.kernel.org对自动抓取返回403，本轮未能检索是否已有相同报告或补丁。请先在<https://lore.kernel.org/all/>搜索`acpi_is_processor_usable`、`record_one_cpu nr_cpus`。
- 两项在主线v7.3-rc2（`df2908090cda`）源码与所测版本一致；ACPI未在v7.3-rc2上重跑，SPARC从未运行。
- 署名`<name>`待填；草稿不含邮箱，未代发。
- 两份草稿是Claude起草的文字，不是用户原话；发出即公开且会被归档。

本目录不是研究实验，不增加确认缺陷数；若上游确认，再按回复更新进展文档。
