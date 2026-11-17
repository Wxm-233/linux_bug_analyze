# 事后补充分析：考虑 KCOV 盲区（不替代判据结果）

KCOV 看不到两类函数：被内联的（没有独立符号），和定义在关掉插桩的文件里的（如 `mm/page_alloc.c`）。判据规定的流水线把它们一律当成“没执行”。这里做两件事：

1. 混合归因：某个架构上，候选的函数和接口都看不到时，退回用手写表；看得到时用实测覆盖。
2. 候选可达性分三类：执行到 / 看得到但没执行到 / 看不到。

## 混合归因

| 树 | 动态确认 | 测过没事 | 部分架构测到 | 转人工 | 模板违反却无候选 |
|---|---|---|---|---|---|
| X1 修复前 | 1 | 0 | 0 | 6 | 0 |
| X1 修复后 | 0 | 1 | 0 | 6 | 0 |
| 当前版本 | 0 | 0 | 0 | 6 | 0 |

- X1 修复前：`post_alloc_hook` / `tag_clear_highpage` → confirmed；arm64（实测）：Z3；arm64（开 MTE）（实测）：Z3；riscv（手写表兜底）：Z2、Z3、Z4、Z7，违反 Z3；x86_64（手写表兜底）：Z2、Z3、Z4、Z7，违反 Z3
- X1 修复后：`post_alloc_hook` / `tag_clear_highpage` → passed；arm64（实测）：Z3；arm64（开 MTE）（实测）：Z3；riscv（手写表兜底）：Z2、Z3、Z4、Z7；x86_64（手写表兜底）：Z2、Z3、Z4、Z7

## 候选可达性（当前版本 KCOV 内核，四个架构配置合并）

| 候选集 | 个数 | 执行到 | 看得到但没执行到 | 看不到 |
|---|---|---|---|---|
| effdep5_32 | 32 | 0 | 26 | 6 |
| effdep7_6 | 6 | 0 | 3 | 3 |

### effdep5_32

- `acpi_os_read_memory`（接口 `acpi_os_ioremap`）：observable_not_executed
- `acpi_os_write_memory`（接口 `acpi_os_ioremap`）：observable_not_executed
- `hugetlb_fault`（接口 `update_mmu_cache`）：observable_not_executed
- `hugetlb_fault`（接口 `update_mmu_cache_range`）：observable_not_executed
- `do_swap_page`（接口 `pte_modify`）：observable_not_executed
- `hugetlb_fault`（接口 `set_huge_pte_at`）：observable_not_executed
- `__irq_set_trigger`（接口 `mask_irq`）：observable_not_executed
- `memtest`（接口 `__va`）：observable_not_executed
- `do_swap_page`（接口 `pte_same`）：observable_not_executed
- `handler_chain`（接口 `handler`）：observable_not_executed
- `ring_buffer_read_page`（接口 `local_set`）：observable_not_executed
- `move_ptes`（接口 `pte_none`）：not_observable
- `string_get_size`（接口 `do_div`）：observable_not_executed
- `do_swap_page`（接口 `ptep_get`）：observable_not_executed
- `mincore_pte_range`（接口 `ptep_get`）：observable_not_executed
- `move_ptes`（接口 `ptep_get`）：not_observable
- `trace_pid_list_is_set`（接口 `cpu_relax`）：observable_not_executed
- `_vm_unmap_aliases`（接口 `max`）：observable_not_executed
- `__ftrace_event_enable_disable`（接口 `set_bit`）：observable_not_executed
- `acpi_init_properties`（接口 `strcmp`）：observable_not_executed
- `audit_add_to_parent`（接口 `strcmp`）：not_observable
- `enable_instances`（接口 `strcmp`）：observable_not_executed
- `audit_data_to_entry`（接口 `pr_warn`）：observable_not_executed
- `cgroup_addrm_files`（接口 `pr_warn`）：observable_not_executed
- `enable_instances`（接口 `pr_warn`）：observable_not_executed
- `bpf_core_calc_relo_insn`（接口 `pr_warn`）：observable_not_executed
- `migrate_pages`（接口 `memset`）：observable_not_executed
- `_vm_unmap_aliases`（接口 `min`）：observable_not_executed
- `print_instance`（接口 `verbose`）：not_observable
- `arg_track_log`（接口 `verbose`）：not_observable
- `propagate_precision`（接口 `verbose`）：observable_not_executed
- `try_charge_memcg`（接口 `get_current`）：not_observable

### effdep7_6

- `__irq_set_trigger`（接口 `mask_irq`）：observable_not_executed
- `ring_buffer_read_page`（接口 `local_set`）：observable_not_executed
- `move_ptes`（接口 `pte_none`）：not_observable
- `print_instance`（接口 `verbose`）：not_observable
- `arg_track_log`（接口 `verbose`）：not_observable
- `propagate_precision`（接口 `verbose`）：observable_not_executed

