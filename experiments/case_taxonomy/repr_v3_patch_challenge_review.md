# 表示 v3 的补丁形状选例诊断：选样错误与真实规则拒判

日期：2026-09-28。前两批仅按标题、路径选出的未读源码留出，在复核后没有足够的同形状阳性。本诊断单独使用**修复补丁的语法形状**预选少量提交，再把每条的**父版单文件**交给完全冻结的 v3 检查器。它回答解析器在已知修复形状附近是否有迁移能力；因为选例已经看了修复差异，**不能称盲测发现、总体准确率或缺陷检出率**。v3 脚本 SHA-256 始终为 `ef9e292fe414ab597931d161bb10fdf35a8fd22b1cde6df3a91b05417ce91a9c`，本轮未改写脚本或前两批结果。

## 第一轮：过宽的同文件配对条件

[事前协议](repr_v3_patch_challenge_protocol_pre.md) SHA `d14375aed8aafec1ee911314c2f5c1411c0d8bdbccbd600d6ba5e38ec59077b0` 固定了 300 条 Git 匹配上限、首三条不同驱动目录、选例脚本 SHA `733467097ea442e25429608249afce60d070c974213d7c2bebdc86d835cb2269` 与运行脚本 SHA `fd9e59d02020462aa8dbac4aa447026ed71692f3fd91cf444285aebd25a7bb81`。第一次规则只要求同一 C 文件的补丁出现新增 `|= cpu_to_le/be*()` 和删除的 `|=`；它**没有要求同一左值和右值**。按固定 Git 顺序检查 57 条匹配后得到[选样 JSON](repr_v3_patch_challenge_selection.json) SHA `b5063a6d4c22bf093d28c2f52aee1177cea514acb88e73fc1351010c2bfd4727`。对三条父版旧源码的 JSON 和哈希先写入[原始清单](repr_v3_patch_challenge_raw_manifest_pre_review.json) SHA `0987f23beff238a99a40b43bfa818576ce743b274ea0e366f8198ee6568e3d37`，之后才人工读补丁。

| 选中提交 | 冻结旧版 `candidate / normal / insufficient` | 补丁复核 |
|---|---:|---|
| `eae6460f` USB cdnsp | 0 / 9 / 20 | 原位置 `|= cpu_to_le32(LINK_TOGGLE)` **早已正确转换**；修订把它移到另一初始化函数，并同时调整丢失控制器上下文后的初始化顺序。不是“新增缺失转换”的案例。 |
| `f99d3b4b` ARM SMMU SVA | 0 / 0 / 0 | 原有 HA/HD 位操作已使用 `cpu_to_le64()`，修订移动这些操作并新增 HAFT 能力分支；零站点反映本规则不解析该处声明/语法，不能说整项正常。 |
| `d11c05dd` ibmvfc | 0 / 1 / 147 | SCSI 路径原本已有转换，修订加入 NVMe/FC 登录分支并移动既有逻辑；不是同一位置的未转换写入。局部 `normal` 不代表整项正确。 |

这三条说明**选例条件自身误配**，不能拿三个零候选当三个同机制漏报，更不能据此改写先前独立留出的状态。原始文件为 `repr_v3_patch_challenge_eae6460f_raw.json`、`repr_v3_patch_challenge_f99d3b4b_raw.json`、`repr_v3_patch_challenge_d11c05dd_raw.json`，各自 SHA 在冻结清单中。没有凭结果替换这三条。

## 第二轮：只接受同左值、同右值的完整补丁行

另起[严格协议](repr_v3_patch_challenge_strict_protocol_pre.md) SHA `0859c67826921a0a0b58b3915f7553e3121af729af6dd93dab7fc7e4c9527ebd`，冻结新的选例脚本 SHA `f0e4635a4fc14f1e368fcdc3b52cfc8901f5f2d23b966c242d0323e959e83c37`，但**不改 v3 检查器**。仅接受同一文件完整 `-lhs |= rhs;` 与 `+lhs |= cpu_to_le/be16/32/64(rhs);`、去空白后 lhs/rhs 相同的补丁，最多查 600 条 Git 匹配、选两个不同驱动目录。检查 292 条后得到[严格选样](repr_v3_patch_challenge_strict_selection.json) SHA `443252dd11899af0f04b0a7f8f760b8c3686d4fcd98c00bdca0f66287fa6a195`；父版运行结果与哈希先保存在[严格原始清单](repr_v3_strict_challenge/repr_v3_patch_challenge_raw_manifest_pre_review.json) SHA `2ddd4802c474e9a8cddbd3067c957bfd4f21ad054e7e6bb195bd056d46f64f35`，随后才做因果复核。

| 提交 | 冻结旧版 `candidate / normal / insufficient` | 对应目标的人工复核 |
|---|---:|---|
| `47e66bec` hisi_sas | 0 / 8 / 46 | 旧版 `hisi_sas_v3_hw.c:1494` 为 `hdr->dw0 |= CMD_HDR_FORCE_PHY_MSK`，新增加 `cpu_to_le32()`。旧版 `hisi_sas.h:507` 将 `dw0` 声明为 `__le32`，同文件宏 `CMD_HDR_FORCE_PHY_MSK` 是 `0x1U << CMD_HDR_FORCE_PHY_OFF`。冻结 v3 **准确定位目标位置和端序字段，但状态为 `insufficient`**，因为只证明 `BIT(n)` 形式，不解析这条移位宏的主机值来源；因此是一个真正同类写出修订上的规则漏报/证据不足，不是命中。提交自身报告 sparse 告警；本轮未运行 sparse 或硬件。 |
| `541fe77c` dw_mmc | 0 / 7 / 4 | 补丁把原有 32 位和 64 位描述符准备函数合并，再按 `is_64bit` 区分：旧 32 位路径的 `des0 |= cpu_to_le32(...)` 已正确转换；旧 64 位描述符有未转换写入，新版该分支仍保留未转换，而 32 位分支继续转换。严格文本配对来自两个旧函数与新条件分支的重排，**不能把 64 位分支直接判成同一端序缺陷**。冻结检查器在旧 32 位转换站点给出局部 `normal`，并未对整项给出结论。 |

严格选例比首轮更接近目标，但同左值/右值仍不能代替**分支适用条件和描述符格式权威**。可成立的自动候选至少要从单旧版追到：目标字段的 `__le/__be` 声明、掩码宏的表达式类型/值域、生成或提交该描述符的路径，以及模式分支。hisi_sas 表明宏表达式数据流是当前具体缺口；dw_mmc 表明如果不区分 32/64 模式，强行要求一律转换会制造误报。以上均是源码与补丁复核，不是完整驱动构建或设备执行。

本轮最终仍是：**开发回放能找到已读语法，标题留出未提供同形阳性，补丁知情严格诊断的一条真正未转换实例被定位但拒判**。因此已有脚本能自动缩小部分检查位置，尚不能自动给出可靠的“应该添加哪项检查”。下一版若继续，先在开发集实现有界宏表达式求值及分支/描述符类型约束，再冻结新的同形、正常和范围外样本；不能把本轮 hisi_sas 重新算作独立留出。此轮在两条严格目标后按协议停机，没有追加搜索、付费模型调用或全量筛选。
