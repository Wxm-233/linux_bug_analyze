# 静态统计：旧映射（r4_rule）与新映射（最近效果）

- A025：2 个；旧 {'None': 1, 'R1': 1}；新 {'None': 1, 'R1': 1}；规则变了 0
- A032：2 个；旧 {'None': 1, 'R1': 1}；新 {'None': 1, 'R1': 1}；规则变了 0
- A043：3 个；旧 {'None': 2, 'R1': 1}；新 {'None': 2, 'R1': 1}；规则变了 0
- A243：7 个；旧 {'None': 6, 'R4': 1}；新 {'None': 6, 'R4': 1}；规则变了 0
- A254：7 个；旧 {'None': 6, 'R4': 1}；新 {'None': 6, 'R4': 1}；规则变了 0
- A274：7 个；旧 {'None': 6, 'R4': 1}；新 {'None': 6, 'R4': 1}；规则变了 0
- A310：5 个；旧 {'None': 4, 'R1': 1}；新 {'None': 2, 'R1': 1, 'R2': 2}；规则变了 2
- A380：4 个；旧 {'None': 3, 'R4': 1}；新 {'None': 3, 'R4': 1}；规则变了 0
- A387：7 个；旧 {'None': 6, 'R4': 1}；新 {'None': 6, 'R4': 1}；规则变了 0
- B485：6 个；旧 {'None': 4, 'R1': 1, 'R3': 1}；新 {'None': 3, 'R1': 1, 'R2': 2}；规则变了 3
- CUR_riscv：6 个；旧 {'None': 5, 'R4': 1}；新 {'None': 5, 'R4': 1}；规则变了 0
- X1：7 个；旧 {'None': 5, 'R1': 1, 'R4': 1}；新 {'None': 3, 'R1': 1, 'R2': 2, 'R4': 1}；规则变了 2
- X2：5 个；旧 {'None': 4, 'R1': 1}；新 {'None': 2, 'R1': 1, 'R2': 2}；规则变了 2
- E5_CUR_riscv：32 个；旧 {'None': 25, 'R1': 4, 'R3': 1, 'R4': 2}；新 {'None': 26, 'R2': 2, 'R3': 1, 'R4': 3}；规则变了 6

effdep7 13 棵树合计：旧 {'None': 53, 'R1': 7, 'R3': 1, 'R4': 7}；新 {'None': 46, 'R1': 7, 'R2': 8, 'R4': 7}

## 规则变了的候选

1. `kvm_get_dirty_log_protect` / `kvm_arch_sync_dirty_log`（virt/kvm/kvm_main.c:2226），跳过 `kvm_flush_remote_tlbs_memslot`：无 → R2；最近效果层 0，命中 {'tlb_flush': ['kvm_flush_remote_tlbs_memslot']}；出现在 A310, B485, X1, X2
2. `kvm_clear_dirty_log_protect` / `kvm_arch_sync_dirty_log`（virt/kvm/kvm_main.c:2348），跳过 `kvm_flush_remote_tlbs_memslot`：无 → R2；最近效果层 0，命中 {'tlb_flush': ['kvm_flush_remote_tlbs_memslot']}；出现在 A310, B485, X1, X2
3. `convert_ctx_accesses` / `verbose`（kernel/bpf/verifier.c:19927），跳过 `bpf_patch_insn_data`：R3 → 无；最近效果层 None，命中 无；出现在 B485
4. `do_swap_page` / `pte_modify`（mm/memory.c:5175），跳过 `do_wp_page`：R1 → R4；最近效果层 1，命中 {'tlb_flush': ['flush_tlb_page', 'mm_tlb_flush_pending'], 'pte_write': ['set_pte_at', 'set_ptes']}，同层另有 R2；出现在 E5_CUR_riscv
5. `do_swap_page` / `pte_same`（mm/memory.c:5042），跳过 `swap_cache_del_folio`：R1 → 无；最近效果层 None，命中 无；出现在 E5_CUR_riscv
6. `do_swap_page` / `ptep_get`（mm/memory.c:5042），跳过 `swap_cache_del_folio`：R1 → 无；最近效果层 None，命中 无；出现在 E5_CUR_riscv
7. `mincore_pte_range` / `ptep_get`（mm/mincore.c:185），跳过 `pte_is_marker`：R1 → 无；最近效果层 None，命中 无；出现在 E5_CUR_riscv
8. `_vm_unmap_aliases` / `max`（mm/vmalloc.c:2998），跳过 `flush_tlb_kernel_range`：无 → R2；最近效果层 0，命中 {'tlb_flush': ['flush_tlb_kernel_range']}；出现在 E5_CUR_riscv
9. `_vm_unmap_aliases` / `min`（mm/vmalloc.c:2997），跳过 `flush_tlb_kernel_range`：无 → R2；最近效果层 0，命中 {'tlb_flush': ['flush_tlb_kernel_range']}；出现在 E5_CUR_riscv
