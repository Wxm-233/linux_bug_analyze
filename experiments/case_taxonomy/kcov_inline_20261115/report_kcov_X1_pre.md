# 流水线报告（实测覆盖）：X1 修复前（覆盖：X1 修复前 KCOV 内核，展开内联）

静态候选 7 个：动态确认 0，测过没事 0，部分架构测到 1，转人工 6；模板违反却无对应候选 2 项。

## 一、动态确认

（无）

## 二、测过没事（所有架构都有模板实际执行到，性质都成立）

（无）

## 三、只在部分架构上测到

- `post_alloc_hook` 调用 `tag_clear_highpage`（mm/page_alloc.c:1828），规则 R1；arm64：执行到它的模板 Z3；arm64（开 MTE）：执行到它的模板 Z3；riscv：执行到它的模板 无；x86_64：执行到它的模板 无

## 四、转人工

- `kvm_get_dirty_log_protect` 调用 `kvm_arch_sync_dirty_log`（virt/kvm/kvm_main.c:2254），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `kvm_clear_dirty_log_protect` 调用 `kvm_arch_sync_dirty_log`（virt/kvm/kvm_main.c:2376），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `__irq_set_trigger` 调用 `mask_irq`（kernel/irq/manage.c:922），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `ring_buffer_read_page` 调用 `local_set`（kernel/trace/ring_buffer.c:6702），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `move_ptes` 调用 `pte_none`（mm/mremap.c:263），规则 无；资源在内核内部，需要 ACTOR 或调试内核（另：被模板 Z9 执行到过，但规则不对应）
- `check_stack_read_fixed_off` 调用 `verbose`（kernel/bpf/verifier.c:5445），规则 无；资源在内核内部，需要 ACTOR 或调试内核

## 五、模板违反却没有对应的静态候选

- riscv：Z3
- x86_64：Z3
