# 表示写出规则 v3：复合位操作与 UAPI 数组的有界验证

日期：2026-09-28。上一轮 v2 的未读源码留出为零候选，详情见[v2 报告](final_synthesis_repr_v2_review.md)。本轮只修补两个可由旧版源码独立核对的语法：已解析端序字段上的 `|=`，以及直接包含的 UAPI 头内 `__aligned_le64` 数组写入。gs_usb 的显式零值用作局部正常语义检查；lpfc 位域没有纳入规则。本轮不作模型调用、全量扫描或硬件验证。

## 开发与冻结

新[检查器](representation_producer_v3.py)在单一 Git 历史版本中读取输入 C 文件、最多三层带引号本地 include，以及该 C 文件直接声明的 `<uapi/linux/...>`，不会按后续补丁反向搜索头文件。`struct __packed NAME` 被解析为明确结构；`BIT(n)` 只在 n 小于目标位宽且定义唯一时作为主机位掩码线索；`readq_relaxed()` 按返回主机 `u64` 处理。输出 `candidate` 仍是待审源码位置，不能自行证明协议、设备可达性或实际故障。

已读开发案例的目标行回放：

| 已读案例 | 旧版目标 | 修复目标 | 特别限制 |
|---|---|---|---|
| dw-axi-dmac `89aba9c` | 第 1129 行 1 个候选 | 对应 1 个局部正常 | 旧式 `__le32 ctl_hi |= BIT(31)`，修复对掩码加 `cpu_to_le32()`；还需确认 DMA 描述符实际消费 |
| Tegra241 `41f0200` | 第 305 行 1 个候选 | 对应 1 个局部正常 | UAPI `__aligned_le64[2]` 有明确小端事件 ABI 注释；此处只查源码链 |
| gs_usb `ef488e4` | 零值赋值局部正常 | 对应局部正常 | `GS_CAN_MODE_RESET = 0`，两版存储字节相同，修复改善端序类型一致性 |

六份开发原始 JSON：[dw 旧](representation_v3_dw_old_development.json)、[dw 修复](representation_v3_dw_fixed_development.json)、[Tegra 旧](representation_v3_tegra_old_development.json)、[Tegra 修复](representation_v3_tegra_fixed_development.json)、[gs_usb 旧](representation_v3_gs_old_development.json)、[gs_usb 修复](representation_v3_gs_fixed_development.json)。这些结果都来自已读案例，不能算独立验证。v3/v2/最早规则各 12/7/8 项离线测试通过。脚本 SHA-256 `ef9e292fe414ab597931d161bb10fdf35a8fd22b1cde6df3a91b05417ce91a9c`，测试 SHA-256 `ef1277839bb3dfa4731b7e50c4d50236208ea6b20051a264eda0b60d11f6e282`；开发 JSON 的逐文件哈希在[预注册协议](repr_v3_protocol_pre.json)中。检查器和协议在留出运行后没有回写。

新的[元数据选样清单](repr_v3_selection_pre.json)按标题、日期、父 SHA 和改动路径固定四个候选及一个范围对照；`0493e739` 虽是未读修订，却与先前一项范围对照共用 C 文件，所以只可称**修订层面的未读留出**。接着[协议](repr_v3_protocol_pre.json)冻结输入、代码和判准。五份旧版原始 JSON 全部保存并计算 SHA-256 后，才查看输出和对应修复补丁；[预复核清单](repr_v3_raw_manifest_pre_review.json)保留大小与哈希。文件中的时间字段为辅助记录，操作顺序还由文件落盘及指纹核对支撑。零命中后没有换样或放宽规则。

## 新留出结果

| 修复提交与旧版输入 | candidate / normal / insufficient | 补丁复核后的解释 |
|---|---:|---|
| SMMU `0493e739` | 0 / 0 / 6 | 目标是 `unused_update.data[0] = entry->data[0] & (~STRTAB_STE_0_V)`；修复给求反掩码加 `cpu_to_le64()`。这是端序位掩码混用，但运算是普通赋值内的按位 AND，超出 v3 限定的 `|=`。六处不足是别的局部站点。 |
| GIC ITS `2bbdfcc5` | 0 / 0 / 0 | 修复给命令块添加 `u64`/`__le64` 匿名 union 双视图，再把 `cpu_to_le64()` 结果写入新 `raw_cmd_le[]`。旧版目标写入 `u64 raw_cmd[]`，更接近类型别名/注解问题；不能当显式端序字段旧版漏检。 |
| MD cluster `82697ccf` | 0 / 2 / 19 | 目标修复是读取 `__le64 sync_size` 后加 `le64_to_cpu()`，属**消费侧**。两个局部正常站点与目标修复无关，不能称该提交正常。 |
| CQHCI `0aae2c73` | 0 / 0 / 0 | 一处为裸指针 `*attr = host expression`，另一处为 `*task_desc |= data` 且修复调整局部指针类型；两者都绕开结构字段路径。它们仍提示主机表示与小端表示的边界，但不是本轮预注册的结构字段复合位操作或 UAPI 数组形状。 |
| rtw89 范围对照 `355f3884` | 0 / 6 / 227 | 旧版从字节流 mask 调用 `le32_encode_bits()` 写 H2C 字段，修复把 mask 声明改为 `__le32` 后直接赋值。目标四处在原始输出中为 `insufficient`；六处局部正常属于别的站点，不能把此对照说成整文件无问题。 |

原始结果：[SMMU](representation_v3_holdout_smmu_0493_raw.json)、[GIC](representation_v3_holdout_gic_2bbd_raw.json)、[MD](representation_v3_holdout_md_8269_raw.json)、[CQHCI](representation_v3_holdout_cqhci_0aae_raw.json)、[rtw89](representation_v3_holdout_rtw89_scope_raw.json)。其 SHA-256 分别为 `2163a367a849a467e5b2fd8e764dc710817b148dd084364d2f110383e3fce155`、`bad216742e3caaac06274d5fe6cc3978bc9aa33ff1c2669eda0c1c5277163e0f`、`b895440e944b86fd61772769894351abe97d16214a322a03b7038e87c05382dc`、`3d653ea33d6eb87647d3ac33cda873f09e3b644d262fde7e71c7d76433f5cb77`、`e0ab97d7c0e5db23bf94683df5a5ff39fcc5f7d8001b0ba640b9023134c61f2f`。

结果是**四个标题候选零自动候选**，且标题实际混入读端转换、类型别名、普通按位表达式和裸指针写入，不能把它们视作四条同形状真阳性，也不能据此算总体召回率。v3 对两条开发案例恢复了目标检查位置，却尚未在新的同形状、未读源码案例上验证迁移。下一步若继续改检测器，应先积累由专家确认的字段/ABI 契约与多种写入语法的独立样本，考虑使用 C 语法树及稀疏类型信息，避免每遇一种表达式就追加孤立正则。保留预算和拒判规则，另行冻结留出后再比较；不宜把本轮局部命中说成普适自动检测。
