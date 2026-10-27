# 表示写出规则 v2：开发修复与未读源码留出

日期：2026-09-28。本轮修补旧规则在已读 idpf、fsl_raid 上的具体漏检语法，再用另一批只按标题和路径选出、尚未阅读源码的旧版检查迁移能力。这不是内核全量检测、真实设备测试或随机抽样。

## 先冻结，再解封

上一轮结果见[独立失效记录](final_synthesis_repr_validation.md)。新版[检查器](representation_producer_v2.py)增加数组/嵌套结构字段、局部标量与 `upper_32_bits()`/`lower_32_bits()` 来源，以及 `u8` 后接 `u8[3]` 且附近存在端序注解字段的 32 位强制转换写入。候选仍只是源码复核线索：指针参数只说明对象可能跨调用边界，不证明设备最终消费，也不自动决定应加哪一种转换。

先用已读 PWM、idpf、fsl_raid 及其修复版开发；新版 7 项、旧版 8 项离线测试通过。脚本 SHA-256 `11cc530b3a6c692ae5cdc733d2e2d5f2a2d8101c5a2ef007c7cafc04b3714d5f`，新版测试 SHA-256 `c211b1cc3439c782a9d9697a4d7c632f0cb0e486a27e4e55a6c1c6d545ae72bb`。三个已读案例的目标赋值如下：

| 开发案例 | 旧版目标 | 修复版目标 | 限制 |
|---|---|---|---|
| PWM | 1 处候选 | 对应 1 处局部正常 | 原规则已能找到，作为回归 |
| idpf | 宽写 1 处候选 | 对应 1 处局部正常 | 端序方向只由相邻字段提示，设备格式仍需人工确认 |
| fsl_raid | 6 处修复目标中 5 处候选 | 对应 5 处局部正常 | 第 6 处宏移位赋值在旧/修复版都为 `insufficient`，不能说覆盖全部目标 |

六份开发 JSON：[PWM 旧](representation_v2_pwm_development.json)、[PWM 修复](representation_v2_pwm_fixed_development.json)、[idpf 旧](representation_v2_idpf_development.json)、[idpf 修复](representation_v2_idpf_fixed_development.json)、[fsl_raid 旧](representation_v2_fsl_development.json)、[fsl_raid 修复](representation_v2_fsl_fixed_development.json)。精确指纹在[预注册协议](final_synthesis_repr_v2_protocol_pre.json)中。总计数包含同文件其他局部站点，不应把它们当独立案例。fsl_raid 第六处为 `desc->hwdesc.fmt32 = FSL_RE_FRAME_FORMAT << FSL_RE_HWDESC_FMT_SHIFT`；目标为 `__be32`，但规则未证明宏移位的静态来源，故谨慎拒判。

[元数据清单](final_synthesis_repr_v2_selection_pre.json)先固定四个不同驱动候选和一个范围对照，随后[预注册协议](final_synthesis_repr_v2_protocol_pre.json)冻结脚本、测试、输入和判准。五个旧版原始输出全部落盘并计算 SHA-256 后，才打开结果和修复补丁；大小与哈希保存在[预复核原始清单](final_synthesis_repr_v2_raw_manifest_pre_review.json)。清单时间字段不是唯一顺序证据；文件与哈希、脚本/协议指纹及操作记录共同界定顺序。未在零命中后替换目标或回写冻结规则。

## 留出结果与源码复核

| 旧版目标 | 原始 candidate / normal / insufficient | 补丁与旧版源码显示的实际关系 |
|---|---:|---|
| dw-axi-dmac `89aba9c` | 0 / 0 / 0 | `__le32 ctl_hi` 上的 `|= CH_CTL_H_LLI_VALID` 在修复中改为对掩码先 `cpu_to_le32()`；规则只处理普通 `=`，漏掉复合位操作。同文件另有“解码→改位→再编码”的正确写法作局部对照。 |
| CAN gs_usb `ef488e4` | 0 / 0 / 28 | 目标 `.mode = GS_CAN_MODE_RESET` 被定位，但常量来源未知，判不足。旧版枚举明确 `RESET = 0`，旧/新实际存储字节相同；补丁强调端序类型规范，不能当非零运行故障或规则漏检真阳性。其余 28 项是局部不足，不是 28 个缺陷。 |
| SCSI lpfc `9cefd6e` | 0 / 0 / 0 | 同一补丁既加读取侧 `be16_to_cpu()`，也加写入侧 `cpu_to_be16()`。旧版 `CommandResponse.bits` 在头文件中以 `uint32_t` 位域和“大端格式”注释描述，而非规则要求的显式 `__be16` 字段；需独立验证位域布局与语义。 |
| Tegra241 CMDQV `41f0200` | 0 / 0 / 0 | `readq_relaxed()` 主机值写入 `lvcmdq_err_map[i]`；修复加 `cpu_to_le64()`。字段在 `include/uapi/linux/iommufd.h` 为 `__aligned_le64[2]`，注释明确 128 位小端事件数据。读取器只追踪局部带引号 include，且类型语法不认 `__aligned_le64`，所以没有站点。 |
| SMMU 范围对照 `4455286` | 0 / 0 / 1 | 修复把两个局部变量从 `__le64` 改为主机端序 `u64`；真正写出时已有 `cpu_to_le64()`。补丁称无功能变化；当前结果不能解读为整文件正常。 |

五份原始 JSON：[dw-axi-dmac](representation_v2_holdout_dw_axi_raw.json)、[gs_usb](representation_v2_holdout_gs_usb_raw.json)、[lpfc](representation_v2_holdout_lpfc_raw.json)、[Tegra241](representation_v2_holdout_tegra241_raw.json)、[SMMU 对照](representation_v2_holdout_smmu_scope_raw.json)。SHA-256 分别为 `aed0edb8b2b9cdde43c2f94fecb31413033a21002aec9b5a97c067ace7290f3a`、`4dab6236922e55f52a2f470151f3374cd72dd766ace741a99adec4cc4f8251b8`、`2b4df22ca3662f071e922dc5993fdc0eaf396c5d7992f15f2f36ab6bd56b1dc3`、`a14e39909289d100da5d80125f1dc83f32cfc2150cfd46f9df3f2b6fcb0e60f8`、`d0c097a7f344f891fee2227429f4b53e23b9f412e2e61e6ed31224fe1d992bad`。

四个标题候选中零个自动候选。dw-axi-dmac 和 Tegra241 明确暴露同一宽层“主机表示写入指定端序”机制下的新语法/声明来源；gs_usb 是零值类型规范修订；lpfc 是位域与读写双向转换，不能直接等同于显式端序字段单写入。故开发案例两条找回，不代表规则已跨驱动泛化；也不能把四个标题候选当四条同机制真阳性计算召回率。本轮未执行硬件或完整驱动。

## 下一轮可检验的改进边界

有上限的 v3 可优先支持两种由旧版源码独立核实的形状：对已解析 `__le/__be` 字段的 `|=` 等复合位操作，要求掩码转换或明确的同端序来源；对数组写入，仅沿指定 include 图到达的 UAPI 声明，识别 `__aligned_le64` 并保留 ABI 注释/路径证据。对零值应先作保守常量折叠，识别“字节不变但类型不合”的局部正常，不能升成运行故障。lpfc 位域应另设研究子题。若做 v3，必须另选并冻结新的未读源码留出，本轮五项均只能转为开发/失效分析材料。
