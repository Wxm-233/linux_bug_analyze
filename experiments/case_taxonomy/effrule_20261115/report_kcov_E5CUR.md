# 流水线报告（实测覆盖）：当前版本 effdep5 32 个候选（新映射：最近效果）

静态候选 32 个：动态确认 0，测过没事 2，部分架构测到 0，转人工 30；模板违反却无对应候选 0 项。

## 一、动态确认

（无）

## 二、测过没事（所有架构都有模板实际执行到，性质都成立）

- `move_ptes` 调用 `pte_none`（mm/mremap.c:267），规则 R4；arm64：执行到它的模板 P1、P2；riscv：执行到它的模板 P1、P2；x86_64：执行到它的模板 P1、P2
- `move_ptes` 调用 `ptep_get`（mm/mremap.c:267），规则 R4；arm64：执行到它的模板 P1、P2；riscv：执行到它的模板 P1、P2；x86_64：执行到它的模板 P1、P2

## 三、只在部分架构上测到

（无）

## 四、转人工

- `acpi_os_read_memory` 调用 `acpi_os_ioremap`（drivers/acpi/osl.c:758），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `acpi_os_write_memory` 调用 `acpi_os_ioremap`（drivers/acpi/osl.c:789），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `hugetlb_fault` 调用 `update_mmu_cache`（mm/hugetlb.c:6132），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `hugetlb_fault` 调用 `update_mmu_cache_range`（mm/hugetlb.c:6132），规则 无；资源在内核内部，需要 ACTOR 或调试内核（另：被模板 I1、P1、P2、T1、T2、T3、Z1、Z2、Z3、Z4、Z5、Z6、Z7、Z8、Z9 执行到过，但规则不对应）
- `do_swap_page` 调用 `pte_modify`（mm/memory.c:5175），规则 R4；arm64：执行到它的模板 无；riscv：执行到它的模板 无；x86_64：执行到它的模板 无；规则 R4 对上了，但没有任何模板实际执行到 `do_swap_page` 或 `pte_modify`（另：被模板 T2 执行到过，但规则不对应）
- `hugetlb_fault` 调用 `set_huge_pte_at`（mm/hugetlb.c:6130），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `__irq_set_trigger` 调用 `mask_irq`（kernel/irq/manage.c:944），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `memtest` 调用 `__va`（mm/memtest.c:48），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `do_swap_page` 调用 `pte_same`（mm/memory.c:5042），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `handler_chain` 调用 `handler`（kernel/events/uprobes.c:2562），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `ring_buffer_read_page` 调用 `local_set`（kernel/trace/ring_buffer.c:7304），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `string_get_size` 调用 `do_div`（lib/string_helpers.c:98），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `do_swap_page` 调用 `ptep_get`（mm/memory.c:5042），规则 无；资源在内核内部，需要 ACTOR 或调试内核（另：被模板 I1、P1、P2、T1、T2、T3、Z1、Z2、Z3、Z4、Z5、Z6、Z7、Z8、Z9 执行到过，但规则不对应）
- `mincore_pte_range` 调用 `ptep_get`（mm/mincore.c:185），规则 无；资源在内核内部，需要 ACTOR 或调试内核（另：被模板 I1、P1、P2、T1、T2、T3、Z1、Z2、Z3、Z4、Z5、Z6、Z7、Z8、Z9 执行到过，但规则不对应）
- `trace_pid_list_is_set` 调用 `cpu_relax`（kernel/trace/pid_list.c:143），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `_vm_unmap_aliases` 调用 `max`（mm/vmalloc.c:2998），规则 R2；arm64：执行到它的模板 无；riscv：执行到它的模板 无；x86_64：执行到它的模板 无；规则 R2 对上了，但没有任何模板实际执行到 `_vm_unmap_aliases` 或 `max`
- `__ftrace_event_enable_disable` 调用 `set_bit`（kernel/trace/trace_events.c:895），规则 无；资源在内核内部，需要 ACTOR 或调试内核（另：被模板 I1、P1、P2、T1、T2、T3、Z1、Z2、Z3、Z4、Z5、Z6、Z7、Z8、Z9 执行到过，但规则不对应）
- `acpi_init_properties` 调用 `strcmp`（drivers/acpi/property.c:603），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `audit_add_to_parent` 调用 `strcmp`（kernel/audit_watch.c:378），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `enable_instances` 调用 `strcmp`（kernel/trace/trace.c:9716），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `audit_data_to_entry` 调用 `pr_warn`（kernel/auditfilter.c:536），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `cgroup_addrm_files` 调用 `pr_warn`（kernel/cgroup/cgroup.c:4575），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `enable_instances` 调用 `pr_warn`（kernel/trace/trace.c:9744），规则 R3；arm64：执行到它的模板 无；riscv：执行到它的模板 无；x86_64：执行到它的模板 无；规则 R3 对上了，但没有任何模板实际执行到 `enable_instances` 或 `pr_warn`
- `bpf_core_calc_relo_insn` 调用 `pr_warn`（tools/lib/bpf/relo_core.c:1349），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `migrate_pages` 调用 `memset`（mm/migrate.c:2114），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `_vm_unmap_aliases` 调用 `min`（mm/vmalloc.c:2997），规则 R2；arm64：执行到它的模板 无；riscv：执行到它的模板 无；x86_64：执行到它的模板 无；规则 R2 对上了，但没有任何模板实际执行到 `_vm_unmap_aliases` 或 `min`
- `print_instance` 调用 `verbose`（kernel/bpf/liveness.c:507），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `arg_track_log` 调用 `verbose`（kernel/bpf/liveness.c:1042），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `propagate_precision` 调用 `verbose`（kernel/bpf/states.c:1038），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `try_charge_memcg` 调用 `get_current`（mm/memcontrol.c:2710），规则 无；资源在内核内部，需要 ACTOR 或调试内核（另：被模板 I1、P1、P2、T1、T2、T3、Z1、Z2、Z3、Z4、Z5、Z6、Z7、Z8、Z9 执行到过，但规则不对应）

## 五、模板违反却没有对应的静态候选

（无）
