# 表示写出 v4：已读开发回放与整数表达式边界（2026-09-30）

本轮补的是此前严格诊断中暴露的**对象宏表达式来源**缺口。`representation_producer_v3.py` 及其旧结果保持冻结，新增 `representation_producer_v4.py`；没有读取新的留出目标或修复补丁，没有网络、付费模型、完整驱动构建或设备运行。

## 新规则与证据要求

规则版本为 `representation-producer-v4.0`。沿用 v3 的有界字段/写点定位，新表达式路线只在已解析的 `__le16/32/64`、`__be16/32/64`（含 aligned 类型）目标成员上工作。源文件内、写点之前定义的对象宏可递归解析；同时计算 ILP32 与 LP64 的 C 整数类型、位宽、移位条件和值域。只有两个模型均可建立非负且可装入目标位宽的主机整数来源，才继续判断是否缺少显式表示转换。

候选输出保存宏定义原文与文件行号、两个模型的结果、目标声明及接口线索，并提出“在该写点将主机整数编码为目标端序类型”的条件检查。声明提供的是该**局部字段的表示依据**；指针参数、调用或复合赋值不证明硬件首次消费，也不直接证明缺陷。输出中的 `normal` 只说明局部赋值满足所支持的表示检查。

规则保守拒判冲突/条件宏、`#undef`、先使用后定义、头文件宏可见性、循环宏、不完整括号的复合对象宏、同名声明的作用域歧义、未知函数、无法证明的缩窄和负值区间、无效移位、丢失高位及有符号算术溢出。每个表达式最多 128 token，每条展开链最多 16 层，整个证明最多 128 次宏展开、2048 展开 token。`BIT/BIT_ULL` 的通常内核定义作为**明确标记的模型假设**用于类型对照和既有转换站点，不能据此产生新增候选；源文件存在同名定义或生命周期时拒判。

v4 同时缩窄了 v3 的范围：不从相邻端序字段推断未标注 alias 槽的端序；头文件宏、signed 全值域与部分已知读取函数表达式会转为 `insufficient`。因此，本次是特定缺口的开发修正，不是 v3 所有能力的覆盖超集，更不能只以候选数变化声称整体检出能力提升。

## 已读开发结果

| 输入 | candidate / normal / insufficient | 目标结论 |
| --- | --- | --- |
| hisi_sas `1dc39ed6` 父版 | 1 / 15 / 38 | `prep_ata_v3_hw:1494` 的 `hdr->dw0 |= CMD_HDR_FORCE_PHY_MSK` 为候选 |
| hisi_sas `47e66bec` 修复版 | 0 / 16 / 38 | 同写点增加 `cpu_to_le32()` 后为局部 normal |
| dw_mmc `40dfdd8d` 父版 | 0 / 5 / 6 | 32 位描述符 `__le32 des0` 的 FD 写已有转换，为局部 normal |
| dw_mmc `541fe77c` 重构版 | 0 / 5 / 6 | 32 位分支对应写仍为局部 normal；64 位描述符的 `u32 des0` 无端序类型依据，不提出统一转换 |

hisi_sas 的宏链为 `CMD_HDR_FORCE_PHY_MSK = (0x1U << CMD_HDR_FORCE_PHY_OFF)`、`CMD_HDR_FORCE_PHY_OFF = 17`；两个模型均得到 unsigned 32 位精确值 131072，位移可定义、目标 `__le32` 位宽可容纳，存储字节在大小端主机间不相同。此前 v3 找到位置却 `insufficient`，本次 v4 可以形成有依据的写点候选。这个案例已读且已知补丁，属于开发回放，不能重新计入独立阳性检出。

dw_mmc 的反例说明同名字段和相似补丁行不能替代格式依据：32 位描述符明确声明 `__le32`，64 位格式这里声明 `u32`。v4 不自动把两种格式合并，也不凭对照补丁把 64 位分支定为端序错误。缺少格式/硬件权威证据仍须进一步复核。

## 离线与编译器对照

`representation_producer_v4_test.py` 的 **25 项离线测试全部通过**。测试包含：宏链、C 常量类型和优先级、word-size 差异、非法位移、signed 溢出、`INT_MIN / -1` 与 `% -1`、按位不变常量、配置冲突、生命周期/先后顺序、作用域阴影、错误转换、未标注格式、展开预算和不支持语法。独立只读审计另复跑 10 个合成场景与 5 个数值边界，均满足保守预期；这些都不是留出集准确率。

固定 12 个可定义表达式与 GCC 13.3 对照，两个模型的**值、位宽和有符号性均一致**。LP64 使用编译后运行；ILP32 缺少 32 位 libc 头，因此改用不依赖 libc 的 `-m32 -fsyntax-only` 和 36 个 `_Static_assert`，属于编译契约验证，没有宣称 32 位程序实际运行。原始诊断与结果保存在 `representation_v4_gcc_development.json`。

## 命令与冻结依赖

在 Windows 本目录可执行：

```powershell
wsl -d Ubuntu -- python3 /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/representation_producer_v4_test.py
wsl -d Ubuntu -- python3 /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/representation_v4_development_run.py --linux-dir /root/repos/linux --out-dir /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy
```

检查单个父版的入口：

```bash
python3 representation_producer_v4.py --linux-dir /root/repos/linux --revision <commit> --source <C-file> --output <new-output.json>
```

2026-09-30 开发完成时 SHA-256：

| 文件 | SHA-256 |
| --- | --- |
| `representation_producer_v4.py` | `2c57d2c54e96d0926cc3c5a25529f1de0d83f3fc0144368e3189ccf8886ec7b4` |
| v3 只读依赖 | `ef9e292fe414ab597931d161bb10fdf35a8fd22b1cde6df3a91b05417ce91a9c` |
| `endian_consumer_single_revision.py` 只读依赖 | `71e50604221ff0b68ac44039ca64606253e32e6b0a136206aea768e329bd467c` |
| v4 离线测试 | `73d9290fba0b7bf4244388513bf361b07dcd9ea2324cfc9cc674551ac6eb64b7` |
| 开发回放 runner | `9695037b9caa052fcd71407f42e30a814f22acb901a4cce2cddfb3fee06c7e05` |

各开发原始结果的哈希、输入父/修复提交及汇总见 `representation_v4_development_manifest.json`。新留出选样和运行由独立执行者处理；开发者未接触其新目标材料。

## 尚未完成的边界

仍未证明真实设备消费格式、配置分支可达性、完整预处理器语义、跨函数首次消费者和运行时行为。新路线是否能在未读同机制阳性上自动提出同类检查，必须等待先冻结再解封的独立试验；本文件中的开发结果不回答该问题。
