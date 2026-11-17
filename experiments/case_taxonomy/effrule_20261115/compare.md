# 新旧映射对比（同样的覆盖和判错输入）

- 当前版本 effdep7 6 个候选（新映射：最近效果）：新 {'confirmed': 0, 'passed': 1, 'partly_checked': 0, 'manual': 5}；旧 {'confirmed': 0, 'passed': 1, 'partly_checked': 0, 'manual': 5}；模板违反无候选：新 []，旧 []
- 当前版本 effdep5 32 个候选（新映射：最近效果）：新 {'confirmed': 0, 'passed': 2, 'partly_checked': 0, 'manual': 30}；旧 {'confirmed': 0, 'passed': 2, 'partly_checked': 2, 'manual': 28}；模板违反无候选：新 []，旧 []
  - `do_swap_page` / `pte_modify`（mm/memory.c:5175）：旧 R1/manual → 新 R4/manual
  - `do_swap_page` / `pte_same`（mm/memory.c:5042）：旧 R1/manual → 新 无/manual
  - `do_swap_page` / `ptep_get`（mm/memory.c:5042）：旧 R1/partly_checked → 新 无/manual
  - `mincore_pte_range` / `ptep_get`（mm/mincore.c:185）：旧 R1/partly_checked → 新 无/manual
  - `_vm_unmap_aliases` / `max`（mm/vmalloc.c:2998）：旧 无/manual → 新 R2/manual
  - `_vm_unmap_aliases` / `min`（mm/vmalloc.c:2997）：旧 无/manual → 新 R2/manual
- X1 修复前（新映射：最近效果）：新 {'confirmed': 1, 'passed': 0, 'partly_checked': 0, 'manual': 6}；旧 {'confirmed': 1, 'passed': 0, 'partly_checked': 0, 'manual': 6}；模板违反无候选：新 []，旧 []
  - `kvm_get_dirty_log_protect` / `kvm_arch_sync_dirty_log`（virt/kvm/kvm_main.c:2254）：旧 无/manual → 新 R2/manual
  - `kvm_clear_dirty_log_protect` / `kvm_arch_sync_dirty_log`（virt/kvm/kvm_main.c:2376）：旧 无/manual → 新 R2/manual
- X1 修复后（新映射：最近效果）：新 {'confirmed': 0, 'passed': 1, 'partly_checked': 0, 'manual': 6}；旧 {'confirmed': 0, 'passed': 1, 'partly_checked': 0, 'manual': 6}；模板违反无候选：新 []，旧 []
  - `kvm_get_dirty_log_protect` / `kvm_arch_sync_dirty_log`（virt/kvm/kvm_main.c:2254）：旧 无/manual → 新 R2/manual
  - `kvm_clear_dirty_log_protect` / `kvm_arch_sync_dirty_log`（virt/kvm/kvm_main.c:2376）：旧 无/manual → 新 R2/manual

X1（post_alloc_hook）：修复前 R1/confirmed，修复后 R1/passed；move_ptes（effdep7 当前版本）：R4/passed

## 规则对上但没有模板执行到（缺模板）

- E5CUR：`do_swap_page` / `pte_modify` → R4（mm/memory.c:5175）
- E5CUR：`_vm_unmap_aliases` / `max` → R2（mm/vmalloc.c:2998）
- E5CUR：`enable_instances` / `pr_warn` → R3（kernel/trace/trace.c:9744）
- E5CUR：`_vm_unmap_aliases` / `min` → R2（mm/vmalloc.c:2997）
