# 独立源码形状审阅：最终轮

2026-10-08。最终审阅对象为 `interface_fact_extractor.py` SHA-256 `45f2daf253aa03e229df30a2f7c93d266711886a0c1e887b7fb57162cf24b715`，对应保存的 `extractor_after_case_guard_snapshot.py`。执行前后当前主工具 SHA 相同。首轮快照、探针、输出和 `review_initial.md` 均保留，不覆盖旧冻结、旧工具或旧源码；本审阅未编辑主工具、运行开发回放、模型、WSL、编译或设备。

**结论：首轮发现的八类语法/绑定问题，在本轮相同32项合成输入中均已拒判或收紧正常结论范围，未发现本轮输入上的残余阻断。该结论仅是有界独立审阅结果，不认证任意C语法、完整配置、完整表示语义、内核安全或泛化准确率。**

## 执行及原始输出

命令 `python -B linux_bug_analyze/experiments/case_taxonomy/interface_facts_20261008/audit_source_shape/rerun_after_case_guard.py`，cwd `D:\homework\software\linux_bug_analyze`，退出0。该入口按顺序在 Python `3.14.4` / `C:\Program Files\Python314\python.exe` 运行三个 `-B` 探针脚本，退出码全部0。执行命令、完整stdout/stderr、代码/输出/旧词法依赖SHA和执行前后提取器SHA在 `after_case_guard_execution.json`。

- `probe_after_case_guard_output.json`：首轮相同27项合成输入及完整输出。
- `probe_additional_after_case_guard_output.json`：首轮相同4项来源类型输入。
- `probe_shadow_extra_after_case_guard_output.json`：首轮相同1项多声明符shadow输入。

拒判可通过返回 insufficient 或抛 ValueError 表达；最终探针记录该异常，根开发入口的 guarded 包装把相应 ValueError 转为 insufficient。32是合成输入数，不是32个内核案例或32个确认缺陷。

中间轮 `d2018bd4...` 快照及 `final_execution.json` 亦保留。中间轮第三个旧探针包装未捕获工具预期的 shadow 拒判 ValueError，因此脚本退出1；原stderr完整保存，随后 `probe_shadow_final_guarded.py` 在同一输入上记录拒判输出。最终轮复用守护包装，三个脚本均退出0。这个包装修正未修改工具或合成输入。

## 复核结果

| 审阅边界 | 最终实际输出及含义 |
| --- | --- |
| 重复 occurrence | 跨atom的相同字段为 normal/candidate；同atom两个字段occurrence均 insufficient，单次转换没有覆盖第二次读取。 |
| opaque pointer/array/multi-declarator shadow | 均抛ValueError；不再把内层host.flags绑定到外层disk.__le32字段。 |
| 来源参数写入 | `reg=1`、`(reg)=1`、`++(reg)` 均 insufficient；不能将可见caller `[0]` 跨越来源写入推为当前初始化零值。 |
| 来源类型和宽度 | `__le32`/`__be32`/`u64` 来源配 `cpu_to_le32(reg)` 均 insufficient；匹配u32来源仍为局部normal。 |
| sizeof | 固定直接标量为 not_value_read；VLA/数组字段不能绑定；GNU sizeof statement-expression中的if被拒绝，未被标运行求值。 |
| API selector及同版 | 参数/局部变量/宏selector shadow均 insufficient；跨修订helper抛ValueError。 |
| API helper误匹配 | LE赋值之后BE覆盖、constant-switch不可达LE case、缺完整签名/三分支/encoder转发的简化helper均 insufficient。首轮`api_selector_baseline`使用的简化helper缺严格实现形状，最终insufficient符合收窄范围，并非真实NLS回放的结论。 |
| 转换/helper宏覆盖 | scalar转换被宏覆盖时ValueError；bitfield helper被宏覆盖时 insufficient。包含文件未完整预处理仍不被机器认证。 |
| bitfield宽度及外部格式 | __le32字段配le64_get_bits为 insufficient；普通u64无外部表示权威仍 insufficient；匹配__le64/le64_get_bits为normal，仅字段位宽/helper名字形状。 |
| target或tag随后重写 | 初始化站点仍可normal，但handoff_value_certified=false；tag后续switch仍是局部文本引用，result_dataflow_proven=false。正常范围不宣称实际消费值。 |
| 硬件swap | 符号引用仅为源码证据；actual_selected_ring_flags=unknown，symbol_presence_proves_activation=false。 |

## 必须保留的解释范围

1. 标签只评价预先选定的局部操作，不等于整个条件、函数、payload、encoder或设备正确。
2. `bitfield normal_scope=field_width_and_helper_name_only`，`helper_implementation_proven=false`，结果数据流未证；后续switch文本和swap符号不能升级成运行分派或补偿模式证明。
3. `API normal_scope=explicit_selector_and_supported_local_helper_shape`，`whole_encoder_certified=false`、`encoder_dataflow_certified=false`、完整预处理语义未证；本轮仅核严格本地helper形状与转发引用。
4. 初始化normal限于该赋值站点，handoff值未证。调用域是当前保存文件的可见直接引用事实，运行到达性未知；未来/生成/树外来源不被推导。
5. 同revision元数据约束防止借用修复版声明解释父版；源码内容完整性由根runner的manifest/SHA/blob验证，不能把同版及哈希完整性解释为外部格式规范认证。
6. 不宣称完整C前端、完整预处理、CFG/别名/值域闭包或未知输入检测。未处理的语法形状仍需独立拒判或明确不足，不能依据本轮合成拒判把任意复杂输入认证为安全。

最终审阅没有读取新Git样本或更改冻结输入，没有新增确认案例、泛化检出率、设备故障真值或独立外部规范认证。
