# N2.10 冻结后独立方法审查（2026-10-18）

本审查在方法冻结和首轮执行之后读取 `method_baseline.json`、`challenge_results.json`、独立挑战的索引/有限源码、`native_validation.json` 和 `linux_replay.json`。未修改冻结方法、测试、执行器、挑战或结果。已按登记的相对路径独立重算 9 个方法文件摘要，均与 baseline 相同；独立 oracle manifest 摘要和结果文件记载的 baseline/manifest 摘要也一致。摘要只能核对文件身份，不能单独证明挑战在认知上独立。

**真实结果是覆盖失败。** 挑战预登记 9 个源码，其中 6 个标为支持范围。6 个均返回 `insufficient/check_not_search_object_and_witness_linked`；3726 个参考输入全部记为 `skipped_source_insufficient`，实际 `evaluated=0`，返回值及检查观察均没有一次程序对照。因此 `return_mismatches=0`、`check_observation_mismatches=0` 不能解释成正确或成功。独立参考本身在 6 个源码上以 GCC C11 编译，并完成 3726 次原生 C 返回值与独立 Python 返回值一致性核对；这只校验参考返回，`check_observations` 仍是 Python 参考字段，方法没有触达它们。

六个源码使用同一合法形状：搜索循环中先声明并初始化局部标量，例如 `int earlier_relation = parent[entry];`，随后以 `if (earlier_relation == entry)` 选择首次见证；消费循环从 `parent[inspected_unit]` 检查。协议允许循环局部纯别名，但冻结方法只对候选条件做表面 `array_reads`，没有将 `earlier_relation` 追溯到 `parent[entry]`，所以与消费条件的直接数组名交集为空，触发上述保守门槛。这是结构/数据流覆盖不足，不是注释或 CRLF 的解析失败，也没有错误地把不支持输入判为已证。K0/K1 的早退出口与 K2–K5 的检查前后、跳过成员和首见证哨兵路径均未进入求值；后四个源码的 Python 参考共含 3258 条检查观察，此轮一条也未与程序比较。不能把这个共同失败当六个独立机制故障或六次语义误判。

3 个负控均返回不足：Z0 的直接原因是 `unsupported_search_control_or_write`，所以不能宣称已单独触到“可变循环界”的专门守卫；Z1 为 `monotone_flag_only_conditional_set_one`，Z2 为 `unsupported_statement:While`。这些结果支持保守拒绝，但未补足正例覆盖。旧 Linux D05/D10 仍在已保存的配置/仪器化区域上 `ordinary_C_parse_unsupported: Invalid expression`；这不是新内核运行，亦不证明真实 Linux 自动抽取已可用。

本轮冻结结果应固定保留。若继续推进，应作为**新版本/新协议**处理局部标量来源追溯及对象身份，并用未参与规则修改的新挑战重新评估；不能修改本轮方法后重跑同一挑战再将它记为原来的独立成绩。即便未来普通 C 组件可用，架构提供者、配置资格、首次消费期限和规范权威仍需分层证据，不由此组件的返回值或局部观察自动推出。
