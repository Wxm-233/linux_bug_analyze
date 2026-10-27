# 条件性字段检查生成器：开发接口与限制

`contract_assertion_generator.py` 提供两个入口：

```python
result = build_plan(report, files)
for program in result["programs"]:
    c_source = emit_c(program)
```

`report` 必须能由冻结的 `structured_hci_single_revision.analyze_files` 在 `files` 上逐项复算。文件清单、哈希、行号、原文、来源字段、端序声明和复制链均纳入比较；已有 Git blob 时另按 Git blob 算法与输入字节核对。该核对证明输入与报告一致，不替代从 Git 仓库验证某个提交的 provenance。

输出包含 `status`、`programs` 和 `rejections`。每个发送点独立分组；生成失败有明确原因，不以局部字段的成功掩盖其他缺失字段。仅接受全字段都是直接固定宽 `__le/__be16/32/64` 标量的完整载荷结构，后缀只支持 `;` 或 `__packed;`。布局宏在所读文件内重定义、任一所读文件中的 pragma 上下文、数组、位域、嵌套成员、非端序字段、缺少字段、重复赋值、地址逸出、字段来源不足等均拒判。重复引用同一源成员也拒判，保证每个字段测试的输入独立。

## 生成内容

actual producer 是独立 C 函数，保留已经逐项核对的原源码字段赋值；不会先根据字段模式制造正确 encode，再用同一模式验证自己。目标载荷保留实际完整结构声明，来源结构只投影被引用且类型已核对的字段。`compiler_binding_contract` 记录 actual 函数、局部对象、结构体标签、来源指针及字段类型，供真实编译器在生成单元中核对绑定。

读端以字段的宽度及端序独立解释原样复制的 bytes；同时从输入数值独立算 schema expected bytes，比较 `decode_schema(P_actual(value)) == value` 和字节是否相同。字段偏移由真实编译器的 `offsetof` 给出。C 输出每行 JSON，包括 `actual_bytes`、`expected_bytes`、`decoded`、`expected_value`、`offset` 和 `width`，便于 Python 另行复核，不能只相信生成 C 的 `pass`。

每个字段两组不对称数值及 zero 控制。变体是 `actual`、`reference` 和逐字段 `partial_<field>`：reference 为全部字段显式转换；partial 故意保留一个字段原样主机存储，其余转换。后两者是合成控制，并非声称上游存在这些补丁。测试值保存于 program 的 `test_values`。

`emit_c` 会从 program 保留的 `validated_inputs` 重新生成计划并比较；篡改计划中的字段、赋值、布局或测试内容会被拒绝。调用者若需要精简展示清单，可另存不含大段输入的摘要，不能将其代替可验证的完整 program 传给 emit。

## 适用边界

这里执行的是条件性缩小翻译单元，未执行完整内核路径或真实设备。明确的 stubs 包括固定宽度 typedef、正常端序转换、`__packed` 和基于已证明复制链的 `memcpy`。C typedef 保留宽度，未保留 Sparse 的 bitwise 类型限制；来源结构原布局、配置和指针入口不执行。

测试向源字段注入主机数值属于显式假设，不证明实际运行值域或该字段未被其他路径编码。当前版本的端序字段声明属于局部 schema，不能凭空升级为外部控制器/opcode 的最终契约。即使投影测试失败，也仅表明这些假设下的表示关系不成立；同样，投影通过不证明真实硬件正确。

## 开发验证

17 项离线测试覆盖真实来源验证、报告/头文件/计划篡改拒绝、完整字段保护、布局、别名与重复来源边界，并跨三种宽度和两种端序试验通用形状。两字段合成程序已使用 GCC 的 `-std=c11 -Wall -Wextra -Werror -O0` 实际编译，x86 运行产生 1 条布局记录和 48 条字段检查记录。已读历史案例、大端编译与独立 Python oracle 由主任务单独运行；本开发说明不将合成结果记作新增独立样本。
