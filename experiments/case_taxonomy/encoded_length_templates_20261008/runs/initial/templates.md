# 由保存事实生成的有条件检查模板

这是数学域中的审阅关系，不是C断言/补丁；所有适用条件均未证，完整长度未知。

## probes:raw_be16_plus_macro

保存输入位置：`/probes/0/result`。状态：`records`。

关系：`count@after_assignment == U_be16(item->len@assignment_bytes) + 4`。

上游局部表示：`candidate`；完整长度未证。显式加项不是完整长度契约。

首个可见词法消费：`skb_tailroom`，不证明执行顺序。

以下条件均需进一步确认：

- actual_declaration_binding：The annotated declaration must actually bind in this version/configuration.
- field_semantic_unit：The unsigned decoded field must denote the relevant count; its unit is not proved by an endian annotation.
- explicit_component_meaning：The observed additive terms must have the required units and meaning; their presence does not prove completeness.
- complete_length_formula：A versioned producer/layout/consumer contract must establish every required component.
- assignment_snapshot_valid：The referenced object and its bytes must be valid at the original assignment.
- conversion_binding：The conversion spelling must bind to the expected implementation.
- consumer_binding：The API spelling and argument role must bind to the actual host-count consumer.
- count_type_representability：The mathematical decoded sum must fit the actual count type on the target configuration.
- c_arithmetic_and_conversion：C promotions, overflow, narrowing and assignment conversions must preserve the proposed mathematical value.
- consumer_value_stability：The actual count used by each selected consumer must still equal the assignment snapshot.
- control_flow_and_reachability：The assignment and consumer must execute in the required order; lexical order alone does not prove it.
- external_contract_applicability：Any external authority must apply to this implementation and version.

## probes:matching_decode_plus_header

保存输入位置：`/probes/1/result`。状态：`records`。

关系：`count@after_assignment == U_be16(item->len@assignment_bytes) + 4`。

上游局部表示：`normal`；完整长度未证。显式加项不是完整长度契约。

首个可见词法消费：`memcpy`，不证明执行顺序。

以下条件均需进一步确认：

- actual_declaration_binding：The annotated declaration must actually bind in this version/configuration.
- field_semantic_unit：The unsigned decoded field must denote the relevant count; its unit is not proved by an endian annotation.
- explicit_component_meaning：The observed additive terms must have the required units and meaning; their presence does not prove completeness.
- complete_length_formula：A versioned producer/layout/consumer contract must establish every required component.
- assignment_snapshot_valid：The referenced object and its bytes must be valid at the original assignment.
- conversion_binding：The conversion spelling must bind to the expected implementation.
- consumer_binding：The API spelling and argument role must bind to the actual host-count consumer.
- count_type_representability：The mathematical decoded sum must fit the actual count type on the target configuration.
- c_arithmetic_and_conversion：C promotions, overflow, narrowing and assignment conversions must preserve the proposed mathematical value.
- consumer_value_stability：The actual count used by each selected consumer must still equal the assignment snapshot.
- control_flow_and_reachability：The assignment and consumer must execute in the required order; lexical order alone does not prove it.
- external_contract_applicability：Any external authority must apply to this implementation and version.

## probes:matching_decode_without_header

保存输入位置：`/probes/2/result`。状态：`records`。

关系：`count@after_assignment == U_be16(item->len@assignment_bytes)`。

上游局部表示：`normal`；完整长度未证。显式加项不是完整长度契约。

首个可见词法消费：`memcpy`，不证明执行顺序。

以下条件均需进一步确认：

- actual_declaration_binding：The annotated declaration must actually bind in this version/configuration.
- field_semantic_unit：The unsigned decoded field must denote the relevant count; its unit is not proved by an endian annotation.
- explicit_component_meaning：The observed additive terms must have the required units and meaning; their presence does not prove completeness.
- complete_length_formula：A versioned producer/layout/consumer contract must establish every required component.
- assignment_snapshot_valid：The referenced object and its bytes must be valid at the original assignment.
- conversion_binding：The conversion spelling must bind to the expected implementation.
- consumer_binding：The API spelling and argument role must bind to the actual host-count consumer.
- count_type_representability：The mathematical decoded sum must fit the actual count type on the target configuration.
- c_arithmetic_and_conversion：C promotions, overflow, narrowing and assignment conversions must preserve the proposed mathematical value.
- consumer_value_stability：The actual count used by each selected consumer must still equal the assignment snapshot.
- control_flow_and_reachability：The assignment and consumer must execute in the required order; lexical order alone does not prove it.
- external_contract_applicability：Any external authority must apply to this implementation and version.

## probes:raw_le32_plus_literal

保存输入位置：`/probes/3/result`。状态：`records`。

关系：`count@after_assignment == U_le32(item->len@assignment_bytes) + 8`。

上游局部表示：`candidate`；完整长度未证。显式加项不是完整长度契约。

首个可见词法消费：`skb_put`，不证明执行顺序。

以下条件均需进一步确认：

- actual_declaration_binding：The annotated declaration must actually bind in this version/configuration.
- field_semantic_unit：The unsigned decoded field must denote the relevant count; its unit is not proved by an endian annotation.
- explicit_component_meaning：The observed additive terms must have the required units and meaning; their presence does not prove completeness.
- complete_length_formula：A versioned producer/layout/consumer contract must establish every required component.
- assignment_snapshot_valid：The referenced object and its bytes must be valid at the original assignment.
- conversion_binding：The conversion spelling must bind to the expected implementation.
- consumer_binding：The API spelling and argument role must bind to the actual host-count consumer.
- count_type_representability：The mathematical decoded sum must fit the actual count type on the target configuration.
- c_arithmetic_and_conversion：C promotions, overflow, narrowing and assignment conversions must preserve the proposed mathematical value.
- consumer_value_stability：The actual count used by each selected consumer must still equal the assignment snapshot.
- control_flow_and_reachability：The assignment and consumer must execute in the required order; lexical order alone does not prove it.
- external_contract_applicability：Any external authority must apply to this implementation and version.

## probes:wrong_decode_width

保存输入位置：`/probes/4/result`。状态：`records`。

拒生成：decode direction/width does not match source field。

## probes:helper_macro_override

保存输入位置：`/probes/5/result`。状态：`records`。

拒生成：local macro define/undef overrides object, type, helper or consumer。

## probes:declaration_wrong_revision

保存输入位置：`/probes/6/result`。状态：`insufficient`。

declaration inputs absent or mixed revisions

## probes:local_multiple_assignments

保存输入位置：`/probes/7/result`。状态：`records`。

拒生成：local has multiple/compound writes。

拒生成：local has multiple/compound writes。

## probes:conditional_assignment

保存输入位置：`/probes/8/result`。状态：`records`。

拒生成：conditional/nested-block assignment unsupported。

## probes:consumer_macro_override

保存输入位置：`/probes/9/result`。状态：`records`。

拒生成：local macro define/undef overrides object, type, helper or consumer。

## probes:encoded_bytes_copied_unchanged

保存输入位置：`/probes/10/result`。状态：`no_eligible_assignment`。

no upstream eligible assignment; no function correctness judgment

## probes:object_pointer_rebinding

保存输入位置：`/probes/11/result`。状态：`records`。

拒生成：structure pointer rebound/modified。

## development:parent

保存输入位置：`/development/0/result`。状态：`records`。

关系：`data_len@after_assignment == U_be16(tag->tag_len@assignment_bytes) + 4`。

上游局部表示：`candidate`；完整长度未证。显式加项不是完整长度契约。

首个可见词法消费：`skb_tailroom`，不证明执行顺序。

以下条件均需进一步确认：

- actual_declaration_binding：The annotated declaration must actually bind in this version/configuration.
- field_semantic_unit：The unsigned decoded field must denote the relevant count; its unit is not proved by an endian annotation.
- explicit_component_meaning：The observed additive terms must have the required units and meaning; their presence does not prove completeness.
- complete_length_formula：A versioned producer/layout/consumer contract must establish every required component.
- assignment_snapshot_valid：The referenced object and its bytes must be valid at the original assignment.
- conversion_binding：The conversion spelling must bind to the expected implementation.
- consumer_binding：The API spelling and argument role must bind to the actual host-count consumer.
- count_type_representability：The mathematical decoded sum must fit the actual count type on the target configuration.
- c_arithmetic_and_conversion：C promotions, overflow, narrowing and assignment conversions must preserve the proposed mathematical value.
- consumer_value_stability：The actual count used by each selected consumer must still equal the assignment snapshot.
- control_flow_and_reachability：The assignment and consumer must execute in the required order; lexical order alone does not prove it.
- external_contract_applicability：Any external authority must apply to this implementation and version.

## development:fixed

保存输入位置：`/development/1/result`。状态：`records`。

关系：`data_len@after_assignment == U_be16(tag->tag_len@assignment_bytes) + 4`。

上游局部表示：`normal`；完整长度未证。显式加项不是完整长度契约。

首个可见词法消费：`skb_tailroom`，不证明执行顺序。

以下条件均需进一步确认：

- actual_declaration_binding：The annotated declaration must actually bind in this version/configuration.
- field_semantic_unit：The unsigned decoded field must denote the relevant count; its unit is not proved by an endian annotation.
- explicit_component_meaning：The observed additive terms must have the required units and meaning; their presence does not prove completeness.
- complete_length_formula：A versioned producer/layout/consumer contract must establish every required component.
- assignment_snapshot_valid：The referenced object and its bytes must be valid at the original assignment.
- conversion_binding：The conversion spelling must bind to the expected implementation.
- consumer_binding：The API spelling and argument role must bind to the actual host-count consumer.
- count_type_representability：The mathematical decoded sum must fit the actual count type on the target configuration.
- c_arithmetic_and_conversion：C promotions, overflow, narrowing and assignment conversions must preserve the proposed mathematical value.
- consumer_value_stability：The actual count used by each selected consumer must still equal the assignment snapshot.
- control_flow_and_reachability：The assignment and consumer must execute in the required order; lexical order alone does not prove it.
- external_contract_applicability：Any external authority must apply to this implementation and version.

