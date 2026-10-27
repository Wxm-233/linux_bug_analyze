# 独立源码形状审阅：第一轮

2026-10-08。本轮只审阅新 `interface_facts_20261008` 提取器；不修改主工具、开发输出、旧冻结或旧源码。未重跑旧 CLI、已读源码回放、模型、WSL、编译或设备。合成输入用于语法边界审计，不算内核新样本、独立案例或泛化准确率。

执行命令：`python -B linux_bug_analyze/experiments/case_taxonomy/interface_facts_20261008/audit_source_shape/probe.py`，cwd `D:\homework\software\linux_bug_analyze`，退出码 0。27 项输入、完整实际输出及异常在 `probe_output.json`。探针执行保存的 `extractor_snapshot.py`，SHA-256 为 `c8891f6a4cf8cf1cc8720d3f8d9021fa93edcc2b5483d10ab13eb3860c5924a3`；执行后当前主工具与快照 SHA 相同。旧 consumer 仅提供 import 的词法 helper，未执行其 CLI。`-B` 禁止生成 pycache。

探针 SHA-256 `9f43a936164d7ce7d1d5905a5372accdd8f7cb64804790b07a2d4a49816a83c0`；输出 SHA-256 `de9821bf092379c8aaf815340eab50f6b0edf582e23ed66b8184ca34bef3adaa`。

## 已正确处理的边界

- 两个逻辑 atom 的相同字段分别为 normal/candidate；同一 atom 的两个相同 occurrence 分别 insufficient，不被单次转换覆盖。
- opaque 指针 shadow 被 `bind_object` 拒绝；opaque 来源变量 shadow 被 initializer 拒绝。
- 固定直接标量 sizeof 为 not_value_read；数组/VLA 字段声明无法绑定，抛 ValueError，未认证非求值。
- 普通 `reg = 1` 被拒绝；ifdef/ifndef 调用值域被拒绝。
- API 参数、局部变量、宏形式的 selector shadow 被拒绝；跨修订 helper 被拒绝。
- 普通 `u64` bitfield 保持 unknown 外部表示/insufficient；匹配 LE helper 输出保留 `helper_implementation_proven=false`、actual_selected_ring_flags=unknown 和 runtime_fault_proven=false。

## 需要修复或明确降低声明的边界

1. **括号后的来源写入漏判，能破坏零调用推导。** 快照 309–310 行只识别裸 `reg` 的赋值/递增/address escape。`(reg) = 1;` 和 `++(reg);` 在 `.reg = reg` 前执行，实际输出仍 candidate 且 `source_parameter_unchanged_in_supported_body=true`，同时可见调用域为 `[0]`。这不是单纯少报：把该 domain 合并为当前初始化零值将错误。建议对参数周围括号或受限 token 写入模式保守拒判，再允许报告 unchanged。

2. **opaque 数组对象 shadow 逃过绑定。** 快照 115 行 opaque 检查 lookahead 未含 `[`。`typedef struct host opaque_t; ... { opaque_t p[2]; if (p->flags & MASK) {} }` 合法地使内层 `p->flags` 指向 host 的 `u32 flags`，工具仍绑定外层 `struct disk *p` 的 `__le32 flags` 并输出 candidate。建议任何含目标名字的疑似声明覆盖数组后缀，解析不了就拒判。

3. **bitfield helper 宽度没有核对。** 快照 381 行只比较 endian，`__le32 tl` 与 `le64_get_bits(p->tl, MASK)` 输出 normal。有限规则不应把 32/64 宽度不一致认证为正常。建议核对声明宽度=64，否则 insufficient。这个探针不依赖 helper 实现是否真实转换。

4. **API helper 的 pattern presence 不是格式权威。** 快照 353 行只要求同名 case 内存在一次 LE 赋值。LE 赋值紧接 `*s = __cpu_to_be16(c)` 覆盖，或者 `switch(UTF16_BIG_ENDIAN)` 中不可达 LE case，均输出 API normal 和 local_helper_implementation format=le16。`whole_encoder_certified=false` 有帮助，但不能把整个输出缓冲格式表述成机器已证。建议严格匹配已支持的 `switch(endian)` 和完整 case 分支、拒绝该分支第二次写入/复杂控制；或明确把 normal_scope 改为 selector/片段形状，保留输出格式语义未知。

5. **本地转换/helper 宏覆盖仍可 normal。** `#define le32_to_cpu(x) (x)` 下 scalar_reads normal；`#define le64_get_bits(v,m) (v)` 下 bitfield_read normal。后者已保存 helper_implementation_proven=false，但 scalar_reads 的理由直接宣称 conversion before mask。API 已实现类似 override 拒判，可复用到所支持 helper 名。包含文件里的未展开宏仍是局限，不应写机器已证明转换实现。

6. **未求值外层上下文没有建模。** GNU `sizeof(({ if (p->flags == 0) {} 1; }))` 中 if 被 scalar_reads 提取并标 evaluated_if_reached。直接固定 scalar sizeof 与复杂/VLA sizeof 的测试没有涵盖这种包围关系。建议拒绝含 sizeof/typeof statement-expression 的所选函数，或显式声明 runtime_operation 仅是未检查外层上下文的源代码形状。该问题不影响目前四项简单目标，但协议“复杂未求值表达式保持不足”需相符。

7. **initializer normal 未校验来源类型/宽度。** 额外探针 `probe_additional.py` 使用同一快照，运行命令 `python -B .../audit_source_shape/probe_additional.py` 退出 0，完整结果保存在 `probe_additional_output.json`。来源参数分别为 `__le32`、`__be32`、`u64`、`u32`，目标 `__le32`、RHS `cpu_to_le32(reg)`，四项均输出 normal。已编码的小端参数再次编码可能改变大端字节表示；与转换宽度不同的普通来源也未证明范围或合法性。normal 分支应同 candidate 分支一样只在支持的同宽原生 `uN` 来源时成立，或降为仅转换拼写事实并将类型语义不足独立保存。

8. **多声明符后续名字的对象 shadow 漏判。** `probe_shadow_extra.py` 同快照运行退出 0，实际输出在 `probe_shadow_extra_output.json`。内层 `struct host *q, *p;` 中第二个声明符 `p` 遮蔽外层 disk 指针，实际 host.flags=u32，但输出 candidate 的 carrier 仍为外层 disk.flags=__le32。建议保守拒判目标名字出现在无法绑定的多声明符声明中。无须宣称支持完整 C 声明语法；但不能把未识别 shadow 当绑定已证。

## 可作为明确局限保留的现象

- 初始化 `.reg = cpu_to_le32(reg)` 后 `msg.reg = 1; handoff(&msg)`，工具把**该初始化站点**标 normal。这可成立，但不认证实际 handoff。建议新增 `handoff_value_certified=false` / `target_object_after_initializer_untracked=true`，避免下游把 initializer normal 误读成 payload normal。
- bitfield 正确提取后 `tag = 0; switch(tag)` 仍 `local_switch_reference=true`。字段名已表明只是局部文本引用；只要报告不称“提取结果实际分派已证明”，可作为保留局限。增加 `result_dataflow_proven=false` 会更清楚。

审阅结论：第一轮已有有效的 occurrence、类型未知、固定 scalar sizeof、同版和 selector 遮蔽约束，但还不能据上述 unsupported 输入给强 normal/unchanged 结论。已把复现和源码 hash 发给根任务；修复后应另存最终轮输出，保留本轮记录。未据开发初轮 results.json 对四项结果下最终结论。
