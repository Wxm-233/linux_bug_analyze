# 配置覆盖六组对照：执行前静态 oracle

状态：`pre_execution_static_oracle`。保存时间：2026-10-11 06:35:11 UTC。

本预期仅独立读取四份冻结源码并推理生成，未读取本轮 inputs/runner，也未执行历史函数、Git、make、模型或真实 Kconfig。六组输入中，用户 base 仅有 CPU_BIG_ENDIAN 一个符号；合成输出显式给出 CPU_BIG_ENDIAN，其余四项均保留 provider 的 y 值。

| row ID | provider CPU | user CPU | output CPU | 合并后 request CPU | 合并前 arch/base 冲突 | request subset output |
|---|---|---|---|---|---|---|
| parent_user_y_output_y | 缺省 | y | y | y | [] | true |
| parent_user_n_output_n | 缺省 | n | n | n | [] | true |
| parent_user_n_output_y | 缺省 | n | y | n | [] | false |
| revision_user_y_output_y | y | y | y | y | [] | true |
| revision_user_n_output_n | y | n | n | n | [(CPU_BIG_ENDIAN: y, n)] | true |
| revision_user_n_output_y | y | n | y | n | [(CPU_BIG_ENDIAN: y, n)] | false |

所有合并请求均有五项：PPC64、CPU_BIG_ENDIAN、SERIAL_8250、SERIAL_8250_CONSOLE、HVC_CONSOLE；CPU 值见表，其他四项为 y。此处冲突列表定义为合并前 `arch.conflicting_options(base)` 的诊断结果，真实 `make_arch_config` 未调用它，也未因这些差异抛错。JSON 的 request_entries 是键值集合预期，不要求序列顺序。

## 用户改写字段的原值与新值

提交 provider 的 CPU 原值为 y。当用户 base 写 n 时，合并请求改为 n；在其他项一致的合成输出中，新值 n 能通过 subset，原值 y 不能通过 subset。原值与新值都能被解析，本预期只断言 subset 接受情况，不断言真实 olddefconfig 能产出任何一项。提交 user=y 的写入没有改变值，原/用户值均是 y。父 provider 未包含此字段，用户值是新增请求，原 provider CPU 值不适用。

因此 revision_user_n_output_n 的 true 只表示“合并请求与显式合成输出一致”；revision_user_n_output_y 的 false 只表示“合并请求 n 与显式输出 y 不一致”。y→n 的覆盖本身并不当然构成缺陷，真实环境硬性约束未知。

## 原文行号与依据

以下路径均相对本工作区根 `D:/homework/software/linux_bug_analyze`。

- 父 provider：`linux_bug_analyze/experiments/case_taxonomy/config_mode_transfer_scope_20261011/raw/01_09ea_parent_powerpc.py` 第 4–8 行是完整 kconfig 字符串，第 5–8 行有四项 y，CPU_BIG_ENDIAN 不在其中。
- 提交 provider：`linux_bug_analyze/experiments/case_taxonomy/config_mode_transfer_scope_20261011/raw/02_09ea_revision_powerpc.py` 第 4–9 行是完整 kconfig 字符串，第 6 行精确原文为 `CONFIG_CPU_BIG_ENDIAN=y`。
- 合并调用顺序：`linux_bug_analyze/experiments/case_taxonomy/kunit_config_binding_20261011/raw/02_kunit_kernel.py` 第 115–118 行：

```python
115: def make_arch_config(self, base_kunitconfig: kunit_config.Kconfig) -> kunit_config.Kconfig:
116:     kconfig = kunit_config.parse_from_string(self._kconfig)
117:     kconfig.merge_in_entries(base_kunitconfig)
118:     return kconfig
```

- 覆盖规则：`linux_bug_analyze/experiments/case_taxonomy/kunit_config_binding_20261011/raw/03_kunit_config.py` 第 72–74 行：

```python
72: def merge_in_entries(self, other: 'Kconfig') -> None:
73:     for name, value in other._entries.items():
74:         self._entries[name] = value
```

- 冲突规则：同一 `03_kunit_config.py` 第 63–70 行，关键原文：

```python
65: for name, value in self._entries.items():
66:     b = other._entries.get(name)
67:     if b and value != b:
68:         pair = (KconfigEntry(name, value), KconfigEntry(name, b))
69:         diff.append(pair)
```

其中 n 是非空字符串，满足第 67 行的 `b` 条件；父 provider 中该键不存在，遍历 arch 时没有 CPU 同名项。

- subset 规则：同一 `03_kunit_config.py` 第 52–61 行：

```python
53: for name, value in self._entries.items():
54:     b = other._entries.get(name)
55:     if b is None:
56:         if value == 'n':
57:             continue
58:         return False
59:     if value != b:
60:         return False
61: return True
```

本轮输出显式含 CPU，故走第 59–60 行的值相等检查。第 55–57 行允许请求 n 对应缺省输出的分支不属于这六组。

- parse 规则：同一 `03_kunit_config.py` 第 14、95–98 行解析赋值并保留值字符串；第 13、100–103 行将 `# CONFIG_CPU_BIG_ENDIAN is not set` 解析为 n。第 97 行为 `kconfig.add_entry(match.group(1), match.group(2))`，第 102 行为 `kconfig.add_entry(empty_match.group(1), 'n')`。因此 literal `CONFIG_CPU_BIG_ENDIAN=n` 与 is-not-set 形式均给出 n。
- 校验绑定：`02_kunit_kernel.py` 第 300 行将 arch/base 合并结果赋给 `self._kconfig`，第 301–302 行写入并调用 olddefconfig，第 306 行调用 validate；第 280–284 行读配置并对 `self._kconfig` 调用 subset。因此这里的预期以合并后请求为比较左侧。

JSON 保存上述四个冻结源文件的 SHA-256，以及明确可预期字段和原文关键行。真实配置可达性、硬性约束、独立缺陷认定与更广泛结论均不在此 oracle 范围内。

