# N2.14：可复用输入与最小配对边界

本次仅检查既有JSON、少量既有解析/验收代码的实际字段，没有新增模型调用、源码、编译、运行或通用分析器。以下SHA是本次读取时的身份记录，不是新增事前冻结。当前材料是同一已读案例的开发证据。

## 1. 非观测公共消费者：可以直接接结构事实

`gimple_cfg_contract_20261019/program_results.json` 顶层为 `documents[]`，每项有 `id`、`binding_sha256`、`same_input_config_as_local_facts`、`local_source_sha256` 和 `analysis`。`analysis` 实际可用字段为：

| 字段 | 可以复用的内容 | 不提供的结论 |
|---|---|---|
| `blocks[].{id,events,terminator,compiler_successors,successor_metadata}` | 原kind语句、源位置、BB及编译器正常后继 | 真实路径可达、调用或asm必返回 |
| `edges[].{source,target,metadata_line,origin}` | 显示succs形成的正常图边 | 根据文本邻接推边、异常路径穷尽 |
| `branch_polarity[].{event,block,condition,targets}` | 显式true/false与succs一致 | 条件实际真假、条件正确性 |
| `loops[].{id,header,latches,nodes,exit_edges}` | 编译器报告循环成员与直接退出 | helper实际遍历域、存在/全称义务 |
| `relations[]` | `branch_to_store`、`branch_arm_exits_loop`、`branch_arm_asm_rejoins`、`asm_normal_successors` | 自动推导语义见证、锁用途或接口规范 |
| `event_bindings[]` | 只有`status=unique`可定位旧局部事实；有`local_event/cfg_event/block/reason` | 将discriminator不可比或歧义项强接 |

`results_summary.json/profiles[].bound_local_dependencies[]` 已保存旧局部依赖的双端CFG事件/BB。两配置各25条双端绑定，均在同BB；这是旧同region may-use链的定位，不能成为新的跨BB值传播。缺完整discriminator可比性的旧分支，保持不足，但CFG本身的显式分支仍可作为新的结构证据。

当前两配置都是父版 `88b604263f3d6eedae0b1c2c3bbd602d1e2e8775`。例如两份结果都有条件store `B17S9 true → B18S1`，join为19；搜索循环直接出口为`B9S9 true → BB10`，目标赋值为`B10S1`。这些ID必须随profile、CFG原文SHA、源码位置一起引用，不可跨文件只因ID相同就当同一对象。BB9退出循环的语义和BB17写入的用途仍需外部审核。

同目录 `old_s390.consumer_binding.json` / `old_x86.consumer_binding.json` 有 `profile/arch/revision/source_i.{path,sha256}/config.{path,sha256}`。与提供者配对应比较这些实际身份，不能只按`old_s390`标签拼接。

## 2. s390提供者：可以接条件效果，不能接实际效果

`preparation_effects_20261017/results.json/results[]` 每项具有：

```text
profile, revision, path_index
guard_alternatives[]: expression, taken, line, column
path_status, endpoint
trace: status, events[] {summary, definition_sha256, args, source_call{line,column}}
under_explicit_assumptions: status, postcondition, target_membership,
                            assumed_premises, premises_proved, runtime_effects_proved
without_proven_or_assumed_premises: 同结构
actual_branch_selected, consumer_deadline_content
```

两版各有三条路径：path 1为资格接受且non-HW，条件后置状态为`["target"]`；path 2为资格拒绝，条件后置状态为`[]`；path 0进入HW循环的`unsupported For`，不能用前缀补成出口效果。旧资格是`!cpu_online(cpu)`，修复资格是`!cpumask_test_cpu(cpu, &cpu_setup_mask)`。`guard_alternatives[].taken`枚举静态路径，不是实测分支。

四项可计算后置状态均依赖7项未证明前提：`distinct_nonoverlapping_storage/equal_logical_domains/legal_member_indices/no_interference_during_trace/source_bound_selected_trace/summarized_calls_return_normally/valid_storage`。不提供前提时6条全部不足。所有路径的 `actual_branch_selected` 和 `consumer_deadline_content` 均为`unknown`。

`trace.events[].args`中的`target/scratch/dst`是研究者选择的角色，不是程序已证明的物理对象。`trace.binding_origin`明确为人工角色与源码声明核对，`physical_pointer_identity=not_proved`。因此可以在显式前提下算“逻辑target是否属于输出集合”，不能把target自动解释为公共消费者正在启动的CPU，也不能把函数出口集合自动当首次消费集合。

`primitive_summaries.json[profile][API]`含 `operation/context{profile,revision,logical_bits}/definition_sha256/review_id/review_origin/references`，是审核的可信语义摘要。其定义和 `.config/.i/autoconf.h` 身份见 `primitive_evidence.json/profiles[].bound_inputs/definitions`；可与提供者packet的同一路径SHA比对。`logical_bits=4`不等于实际可达CPU数或`nr_cpu_ids`。

`candidate_card.json`明确 `updater_reaches_starting_target/final_link_or_runtime_address_identity/initial_common_use_and_stability=unknown`，`whole_contract=insufficient`，不应由新薄匹配器覆盖。

## 3. 同配置与对象绑定：静态身份可接，运行对象未知

`provider_consumer_binding_20261017/{old_s390,fixed_s390}.json`有：

```text
profile, arch, revision, artifact_stage='original non-instrumented object build'
effective_config, selected_artifacts[]{path,sha256}
functions_by_translation_unit[tu][name]: sha256, expected_source,
 name_location/definition_location, line_map, text, evidence_layer
global_declaration_excerpts[tu][], object_evidence[obj]{symbols,relocations,scope}
object_link_checks
final_link_identity, runtime_address_identity, target_iteration_reached,
helper_effects_proved, content_at_consumption, whole_contract
```

旧s390消费者的`.config` SHA为`205e9f6702e53c01ecc8ccb4b27e7911b4c679e38144885780be0595db92f4e9`，`core.i`为`7d744900a3b3cbbb357cb427675b4bf986305bfae61d4916617587082d547e10`，与本轮CFG binding一致。修复s390是另一个revision；`.config`为`d2ef114b2837f4a30ae56f9f88e74e77e6c58b91a0498d3bd2a31e6207bc63b3`，`core.i`为`0a10c04e8e458349f6952a4f1603f6146cec9e9f1a2f7c5d021c1c3a815dc2e4`。当前没有fixed CFG，不能把old CFG静默改标签用于fixed。即使两版`core.o`字节相同，也不能替代每一层输入及要求适用性核对。

可复用cpu_topology定义/引用/重定位，及fixed cpu_setup_mask的定义/引用/重定位；这些是ET_REL对象关系，不是最终链接地址、同一运行对象或动态目标覆盖。packet仍写明 `runtime_address_identity/target_iteration_reached/content_at_consumption=unknown` 和 `helper_effects_proved=false`。本组没有x86同等级条件效果，x86 effect必须不足，不能复制s390结果或runtime值。

## 4. 带观测运行：单独复用，不能灌入非观测CFG

`s390_arch_contract_20261013/runtime/profiles/<profile>/build.json`有 `profile/arch/revision/source_instrumented=true/image_sha256/initrd_sha256/config_sha256/release/effective_required`；`boot.json`有 `profile/receipt/observations`。`observations.events[]`保留 `phase,line,cpu,current,seq,online,mask,self,weight`等；`lock_snapshot`另有`locks/rq_self/printed_after_unlock`。`line`是原boot日志行，不是C源码行。

可单独回放CPU1的同阶段序列及mask/self/lock等窄观察。`prepared_known=0,prepared=-1`表示未提供资格信息，不表示资格为假。`observations.contract`含按old/fixed设定的验收期望，不应作为新匹配器的发现依据；应引用原events、基础身份/顺序检查和observer来源。`foundation.mask_stable_before_consumer`只比较5个离散观察点，不证明整个区间稳定，也不是全局第一次真实内容读取。

四格运行配置SHA分别为：

| profile | runtime config SHA |
|---|---|
| old_s390 | `ba935721b43a3187db05c24b74f5694180be0e816368efbc0155a507ace1f11e` |
| fixed_s390 | `a2b50968b902ea79606c0b566f7b151a10497d53f83ecb5231fcbe2de4253a1e` |
| old_x86 | `a9264c98fd293799f8a3aced3642bd3bc8e5def1ed6f12884f96056695aba318` |
| fixed_x86 | `819f6b7a2762e9cb00b05307f7677934a10ab353bc1a4dbf64990607d3bc15bb` |

这些运行具有观测源码且配置摘要与非观测构建不同，不能只凭相同git revision或少量开关就认作本轮CFG的实际值。两CPU普通启动观察也不扩大为真实SMT、热插拔或并发覆盖。

## 5. 最小配对与四栏建议

优先形成一条同版本old_s390“静态公共条件＋静态提供者路径”的条件匹配，旁列old_x86公共CFG作为同用途结构对照；x86没有静态效果就明确不足。fixed_s390仅复用其独立条件效果和源码身份，公共要求跨版本适用性需另行审核，不伪装成fixed CFG证据。历史四格runtime单列已读观察，不参与静态条件真值计算。

| 栏 | 本轮可自动接 | 必须保留的unknown或审核输入 |
|---|---|---|
| qualification | 已有guard表达式、分支枚举、profile/revision | 真实目标资格、与公共适用条件等价性；不能把guard资格当消费者是否适用 |
| effect | 完整terminal路径＋审核摘要＋显式前提的逻辑集合后置状态 | HW frontier、实际选择路径、真实指针/对象及运行效果 |
| target | 配置/源文件/函数/对象符号身份的精确匹配 | `target`角色是否就是启动CPU、实际迭代到目标、最终地址同一 |
| deadline | 可引用已审核用途与现有外层时序作为有来源的输入 | 本组packet的函数出口并非首次内容消费；到达、稳定性和并发仍不足 |

输出`conditional_conflict/conditionally_compatible/unknown`须写清是**某项要求在所列前提下的比较**；任一关键target/deadline缺口不能升级为真实violation或完整兼容。self成员要求需要锁用途与同对象证据，不能仅由“后面有target条件store”推出。无需为本项再扩CFG或helper树。

## 关键packet身份（本次读取）

| 相对 `experiments/case_taxonomy/` 的路径 | SHA-256 |
|---|---|
| gimple_cfg_contract_20261019/program_results.json | `eaa3ba68ed5d00cff53c8f5d2d4898bc50025f5ec0436a18d3f89ed99f85b006` |
| gimple_cfg_contract_20261019/results_summary.json | `e53fb492ed8c56a58421d9e0d25c068a50996b054eb92901590c8edd8a90bf66` |
| preparation_effects_20261017/results.json | `0f818f69f36bc2c9910ef3110f4a5ca290e684e93741bf7e228d12d0834a6f15` |
| preparation_effects_20261017/candidate_card.json | `4692bd486127b1385659465da162e3dc88a2bd2e1343e68313eac08e2b6faf87` |
| preparation_effects_20261017/primitive_summaries.json | `babc595d8121376df4b0ad35e69495a5f64b9cc088f21ed600d94d1a81bf1d9b` |
| provider_consumer_binding_20261017/old_s390.json | `bbec5c2e4290c9931de209f3e2749f79e8757a6205668d1473bc1d4ed26c711a` |
| provider_consumer_binding_20261017/fixed_s390.json | `6581b915df24046795b899c5f4db0653f97c6098cc839a872f3f9da3d9513b53` |
| s390_arch_contract_20261013/runtime/verification.json | `58f395ceb27365a4f6677d50d81b3d3e5ffd59c003029ea596875aa17061bf87` |

运行原始log SHA已在`runtime/verification.json/profiles[]/log_sha256`逐格保存，并与本次读取的四份日志摘要一致。重新采用运行证据时仍需绑定同profile的build/boot/observer与原日志，不能只引用汇总PASS。
